"""Tool implementation for asr_read — read and parse an existing ASR."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..helpers.asr_md import (
    ASR_PREFIX,
    ASR_REFERENCES_DIR,
    LEGACY_REQUIREMENTS_DIR,
    find_asr_number,
    legacy_asr_records,
    parse_asr,
)


def _resolve_asr_path(name: str, workspace_root: Path) -> Path | None:
    """Resolve an ASR name to its file path.

    Accepts number-only variants such as "1", "0001", "ASR-0001", and
    "ASR-0001.md".
    """
    name = name.removesuffix(".md")

    stripped = name.removeprefix(ASR_PREFIX)
    if stripped.isdigit():
        return find_asr_number(workspace_root, int(stripped))

    return None


def asr_read(
    name: str,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    """Read and parse an Architecturally Significant Requirement.

    Accepts canonical number-based names such as "1", "0001", "ASR-0001",
    or "ASR-0001.md".
    Returns structured ASR data on success.
    Returns {"error": "...", "message": "..."} on failure.
    """
    if not name.strip():
        return {"error": "invalid_name", "message": "Name cannot be empty"}

    # Reject path traversal
    if "/" in name or "\\" in name or ".." in name:
        return {"error": "invalid_name", "message": "Name must not contain path separators"}

    asr_path = _resolve_asr_path(name, workspace_root)
    if asr_path is None:
        if legacy_asr_records(workspace_root):
            return {
                "error": "migration_required",
                "message": (
                    f"Legacy ASR corpus found under '{LEGACY_REQUIREMENTS_DIR}/' but "
                    "no canonical records exist. Run the governance_migrate tool "
                    "before reading or writing ASRs."
                ),
                "legacy_dir": LEGACY_REQUIREMENTS_DIR,
                "searched": ASR_REFERENCES_DIR,
            }
        return {
            "error": "asr_not_found",
            "message": f"ASR not found: {name}",
            "searched": ASR_REFERENCES_DIR,
        }

    rel_path = str(asr_path.relative_to(workspace_root)).replace("\\", "/")
    try:
        content = asr_path.read_text(encoding="utf-8")
        asr = parse_asr(content)
    except ValueError as e:
        return {"error": "parse_error", "message": str(e), "path": rel_path}

    import json as _json
    return {
        "output": _json.dumps({"number": asr.number, "priority": asr.priority, "status": asr.status,
                               "created": asr.created, "updated": asr.updated,
                               "requirement": asr.requirement, "notes": asr.notes, "path": rel_path}),
        "title": "Read ASR",
        "metadata": {"target": rel_path.split("/")[-1].replace(".md", "")},
    }


if __name__ == "__main__":
    import json
    import sys
    args = json.loads(sys.stdin.read())
    result = asr_read(
        name=args["name"],
        workspace_root=Path(args["workspace_root"]),
    )
    print(json.dumps(result))
