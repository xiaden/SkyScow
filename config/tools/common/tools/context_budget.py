"""Measure supplied files and project worker/manager context budgets.

Production-hardened entry point for the ``context_budget`` MCP tool.

Contracts
---------
- **Generic file input.** ``files`` is a non-empty list of
  ``{path, start_line, end_line}`` objects. Optional ``graph_packet`` measures an
  ephemeral Change DAG worker-node or manager-review packet assembled from DAG
  node context; the packet identifies its Change DAG through the canonical
   ``dag_slug`` key; the legacy ``graph_id`` key is no longer accepted. Packets
   are never persisted. Unknown keys, invalid ranges, traversal attempts, and
   unreadable files are rejected.
- **Model metadata from frontmatter only.** Agent markdown files (path
  contains an ``agents`` segment and ends in ``.md``) contribute their
  frontmatter ``model:`` value through ``budget_policy.frontmatter_model``.
  Model selection is allowlisted with a deterministic ``DS_V4_F_0731``
  fallback (see ``budget_policy.select_tokenizer_model``).
- **Fixed policy.** All limits come from the shipped
  ``config/agent-context-budgets.yaml`` via ``budget_policy.load_policy``.
  Agent frontmatter is never consulted for policy.
- **Compact output.** Stable JSON keys, bounded titles and error messages,
  worker-limit projections, and normal/worst-case manager projections. Raw file
  contents, agent frontmatter bodies, and policy file text are never emitted.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from ..helpers.budget_policy import frontmatter_model, load_policy, select_tokenizer_model
from ..helpers.file_helpers import resolve_file_path
from ..helpers.tokenizer_helpers import (
    assemble_sections,
    load_tokenizers,
    read_subsection,
    weighted_tokens,
)

_ALLOWED_ENTRY_KEYS = frozenset({"path", "start_line", "end_line"})
_ALLOWED_PACKET_KEYS = frozenset({"kind", "dag_slug", "node_ids", "files", "request_context", "contracts", "acceptance", "worker_return_tokens", "qa_return_tokens"})
_MESSAGE_LIMIT = 300
_TITLE_LIMIT = 120


def _error(error: str, message: str) -> dict[str, str]:
    message = str(message)
    if len(message) > _MESSAGE_LIMIT:
        message = message[:_MESSAGE_LIMIT] + "..."
    return {"error": error, "message": message}


def _bounded_title(title: str) -> str:
    title = title.strip()
    if len(title) > _TITLE_LIMIT:
        return title[:_TITLE_LIMIT] + "..."
    return title


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 1:
        return None
    return value


def _has_dir_segment(resolved: Path, segment: str) -> bool:
    return segment in resolved.parts


def _is_agent_file(resolved: Path) -> bool:
    return resolved.suffix == ".md" and _has_dir_segment(resolved, "agents")


def _read_full(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _count_tokens(tokenizers: tuple[Any, Any], model: str, text: str) -> int:
    if model == "o200k":
        return len(tokenizers[0].encode(text, disallowed_special=()))
    return len(tokenizers[1].encode(text, add_special_tokens=False).ids)


def _build_planning(
    policy: dict[str, Any],
    weighted: int,
    phases: int,
    explicit_phases: bool,
    phases_detail: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute the derived worker-limit and manager projections and status from the fixed policy."""
    worker_limit = policy["worker_phase_limit"]
    operational_limit = policy["manager_operational_limit"]
    physical_limit = policy["physical_limit"]
    multiplier = policy["correction_multiplier"]

    overhead = (
        policy["phase_reread_tokens"]
        + policy["worker_return_tokens"]
        + policy["qa_return_tokens"]
    )
    minimum_phases = max(1, math.ceil(weighted / worker_limit))
    normal = weighted + phases * overhead
    worst = weighted + phases * overhead * multiplier
    minimum_plans = max(1, math.ceil(worst / operational_limit))

    if worst > physical_limit:
        status = "PHYSICAL_LIMIT_EXCEEDED"
    elif worst > operational_limit:
        status = "SPLIT_REQUIRED"
    else:
        status = "VALID"

    return {
        "phases": phases,
        "explicit_phases": explicit_phases,
        "phases_detail": phases_detail,
        "minimum_phases": minimum_phases,
        "minimum_plans": minimum_plans,
        "normal_manager_tokens": normal,
        "worst_case_manager_tokens": worst,
        "status": status,
    }


def _packet_sections(packet: dict[str, Any], workspace_root: Path) -> list[str] | dict[str, str]:
    if set(packet) - _ALLOWED_PACKET_KEYS:
        return _error("invalid_dag_packet", "graph_packet has unsupported keys")
    if packet.get("kind") not in {"worker_node", "manager_review"}:
        return _error("invalid_dag_packet", "kind must be worker_node or manager_review")
    sections = [json.dumps({key: packet.get(key) for key in ("dag_slug", "node_ids", "contracts", "acceptance") if key in packet}, sort_keys=True)]
    for entry in packet.get("files", []):
        if not isinstance(entry, dict):
            return _error("invalid_dag_packet", "packet files must be objects")
        path = entry.get("path"); start = _integer(entry.get("start_line")); end = _integer(entry.get("end_line"))
        if not isinstance(path, str) or start is None or end is None or end < start:
            return _error("invalid_dag_packet", "packet file ranges are invalid")
        resolved = resolve_file_path(path, workspace_root)
        if isinstance(resolved, dict):
            return _error("invalid_dag_packet", resolved.get("error", "invalid packet path"))
        try:
            sections.append(read_subsection(resolved, start, end))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return _error("invalid_dag_packet", str(exc))
    return sections


def context_budget(files: list[dict[str, Any]] | None, workspace_root: Path, graph_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    """Measure supplied files and project worker/manager context budgets.

    Args:
        files: Non-empty list of ``{path, start_line, end_line}`` entries.
        workspace_root: Workspace root; all paths resolve inside it.
        graph_packet: Optional ephemeral Change DAG worker-node or
            manager-review packet (``kind`` is ``worker_node`` or
            ``manager_review``), measured in addition to ``files`` and never
            persisted.

    Returns:
        A compact JSON-serializable result, or a stable ``{error, message}``
        object. The ``planning`` section reports the derived worker-limit
        (``minimum_phases``) and manager (``minimum_plans``) projections and a
        policy ``status``; these are computed projections, not plan artifacts.
    """
    if files is None:
        files = []
    if not isinstance(files, list) or (not files and graph_packet is None):
        return _error("invalid_files", "files must be a non-empty array unless graph_packet is supplied")

    workspace_root = workspace_root.resolve()
    packet_sections = None
    if graph_packet is not None:
        packet_sections = _packet_sections(graph_packet, workspace_root)
        if isinstance(packet_sections, dict):
            return packet_sections
    policy, policy_diagnostics = load_policy(workspace_root)

    sections: list[str] = []
    resolved_paths: set[Path] = set()
    agent_models: list[str | None] = []

    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            return _error("invalid_file", f"files[{index}] must be an object")

        unsupported = set(entry) - _ALLOWED_ENTRY_KEYS
        if unsupported:
            return _error(
                "invalid_file",
                f"files[{index}] has unsupported keys: {sorted(unsupported)}",
            )

        file_path = entry.get("path")
        start_line = _integer(entry.get("start_line"))
        end_line = _integer(entry.get("end_line"))
        if not isinstance(file_path, str) or not file_path.strip():
            return _error("invalid_file", f"files[{index}].path must be non-empty")
        if start_line is None or end_line is None:
            return _error(
                "invalid_line_range",
                f"files[{index}] start_line and end_line must be positive integers",
            )
        if end_line < start_line:
            return _error(
                "invalid_line_range",
                f"files[{index}].end_line must be >= start_line",
            )

        resolved = resolve_file_path(file_path, workspace_root)
        if isinstance(resolved, dict):
            return _error("invalid_file", resolved.get("error", "Invalid file path"))
        resolved_paths.add(resolved)

        try:
            sections.append(read_subsection(resolved, start_line, end_line))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return _error("read_error", f"{file_path}: {exc}")

        if _is_agent_file(resolved):
            try:
                agent_models.append(frontmatter_model(_read_full(resolved)))
            except (OSError, UnicodeDecodeError):
                agent_models.append(None)

    if packet_sections:
        sections.extend(packet_sections)
    if not sections:
        return _error("invalid_dag_packet", "graph_packet must contain measurable context")
    source = assemble_sections(sections)
    model = select_tokenizer_model(agent_models)

    try:
        tokenizers = load_tokenizers()
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _error("tokenizer_error", str(exc))
    source_tokens = _count_tokens(tokenizers, model, source)
    weighted = weighted_tokens(source_tokens, len(sections), len(resolved_paths))

    # Worker-limit fallback: estimate worker phases from the measured context.
    phases = max(1, math.ceil(weighted / policy["worker_phase_limit"]))
    phases_detail: list[dict[str, Any]] = []

    planning = _build_planning(policy, weighted, phases, False, phases_detail)

    result = {
        "model": model,
        "measured": {
            "source_tokens": source_tokens,
            "weighted_tokens": weighted,
        },
        "planning": planning,
        "policy": {
            "source": policy_diagnostics["source"],
            "worker_phase_limit": policy["worker_phase_limit"],
            "manager_operational_limit": policy["manager_operational_limit"],
            "physical_limit": policy["physical_limit"],
            "worker_return_tokens": policy["worker_return_tokens"],
            "fixer_return_tokens": policy["fixer_return_tokens"],
            "qa_return_tokens": policy["qa_return_tokens"],
            "phase_reread_tokens": policy["phase_reread_tokens"],
            "correction_multiplier": policy["correction_multiplier"],
        },
    }
    if graph_packet is not None:
        result["packet"] = {
            "kind": graph_packet.get("kind"),
            "dag_slug": graph_packet.get("dag_slug"),
            "node_ids": graph_packet.get("node_ids", []),
            "ephemeral": True,
        }
    return result


if __name__ == "__main__":
    arguments = json.loads(input())
    result = context_budget(
        files=arguments.get("files"),
        workspace_root=Path(arguments["workspace_root"]),
        graph_packet=arguments.get("graph_packet"),
    )
    print(json.dumps(result, separators=(",", ":")))
