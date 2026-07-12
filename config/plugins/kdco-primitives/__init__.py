"""ComfyUI-KG-Bridge — Knowledge Graph extension for ComfyUI.

Makes ComfyUI the canonical data host for model compatibility metadata.
Scans model files (checkpoints, LoRAs, VAEs, ControlNets), computes SHA256
hashes, queries the CivitAI API for metadata, and builds a knowledge graph
exposed via REST API.

Usage:
    Install in ComfyUI/custom_nodes/comfyui-kg-bridge/
    Restart ComfyUI (or refresh)
    Query: GET http://localhost:8188/kg/status
    Rescan: POST http://localhost:8188/kg/rescan

Architecture:
    __init__.py      — Extension entry point, startup logic
    knowledge_graph.py  — Lightweight graph data model (no networkx)
    civitai_client.py   — CivitAI API client (public endpoints, stdlib only)
    model_scanner.py    — Model scanning, SHA256, KG population
    routes.py           — REST API route handlers

Requirements:
    - ComfyUI (any recent version)
    - Python 3.11+ (for hashlib.file_digest)
    - Internet access to civitai.com for hash lookups

All data is stored in comfyui-kg-bridge/data/:
    knowledge_graph.json  — Serialized knowledge graph
    hash_cache.json       — SHA256 cache (keyed by mtime+size)
"""

import logging
import os
import sys
from pathlib import Path

# ── Setup logging ────────────────────────────────────────────────────────
log = logging.getLogger("comfyui-kg-bridge")
log.setLevel(logging.INFO)

# Ensure we can import sibling modules
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from .knowledge_graph import KnowledgeGraph
from .civitai_client import CivitaiClient
from .model_scanner import ModelScanner
from .routes import KGState, create_routes

WEB_DIRECTORY = None

DATA_DIR = _THIS_DIR / "data"

# ── Global state ─────────────────────────────────────────────────────────
_kg: KnowledgeGraph
_civitai: CivitaiClient
_scanner: ModelScanner
_initialized = False


def _ensure_data_dir() -> None:
    """Create data directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _initialize() -> None:
    """One-time initialization of global state.

    Called from comfy_entrypoint() during ComfyUI extension loading.
    """
    global _kg, _civitai, _scanner, _initialized

    if _initialized:
        return

    _ensure_data_dir()

    # ── Load or create the knowledge graph ───────────────────────────────
    kg_path = DATA_DIR / "knowledge_graph.json"
    _kg = KnowledgeGraph.load_json(kg_path)
    log.info("KG loaded: %d nodes, %d edges", _kg.node_count(), _kg.edge_count())

    # ── Create CivitAI client ────────────────────────────────────────────
    _civitai = CivitaiClient()

    # ── Create scanner ───────────────────────────────────────────────────
    _scanner = ModelScanner(_kg, _civitai, DATA_DIR)

    # ── Register API routes ──────────────────────────────────────────────
    state = KGState(kg=_kg, civitai=_civitai, scanner=_scanner)
    create_routes(state)
    log.info("KG routes registered")

    _initialized = True

    # ── Startup scan check (non-blocking) ────────────────────────────────
    try:
        if _scanner.detect_changes():
            log.info("Model changes detected — starting background scan")
            _scanner.start_scan()
        else:
            log.info("No model changes since last scan")
    except Exception as e:
        log.warning("Startup change detection failed: %s — "
                     "run POST /kg/rescan manually", e)


# ── ComfyUI Extension Entry Point ────────────────────────────────────────

try:
    from comfy_api.latest import ComfyExtension, io

    class KGBridgeExtension(ComfyExtension):
        """ComfyUI extension — registers KG routes on load."""

        async def on_load(self) -> None:
            """Initialize KG on extension load."""
            _initialize()

        async def get_node_list(self) -> list[type[io.ComfyNode]]:
            return []  # No visual nodes

    async def comfy_entrypoint() -> KGBridgeExtension:
        return KGBridgeExtension()

except ImportError:
    # Fallback for older ComfyUI versions or testing outside ComfyUI
    log.warning("comfy_api not available — running outside ComfyUI?")
    _initialize()


# ── Direct execution (for debugging) ─────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing KG bridge initialization...")
    _initialize()
    print(f"KG: {_kg.node_count()} nodes, {_kg.edge_count()} edges")

    # Quick scan test
    print("Model changes detected:", _scanner.detect_changes())
    print("Hash cache entries:", len(_scanner.hash_cache.get_all_entries()))
    print("Done.")
