"""Tool implementation for asr_create — create a new Architecturally Significant Requirement."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from ..helpers.asr_md import (
    ASR,
    _unescape_literal_newlines,
    asr_status_dir,
    generate_asr,
    make_asr_filename,
    next_asr_number,
    today_iso,
    validate_priority,
    validate_status,
)
from ..helpers.governance_index import (
    GovernanceIndexError,
    rebuild_governance_indexes,
)


def asr_create(
    priority: int,
    requirement: str,
    notes: str = "",
    status: str = "Active",
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    """Create a new Architecturally Significant Requirement markdown file.

    Args:
        priority: Integer priority (lower = higher priority).
        requirement: The requirement statement text.
        notes: Optional context or rationale notes.
        status: One of 'Active', 'Archived', or 'Superseded by ASR-NNNN'.
        workspace_root: Absolute path to the workspace root.

    Returns:
        On success: {"path": str, "number": int, "markdown": str}
        On failure: {"error": str, "message": str}
    """
    err = validate_priority(priority)
    if err:
        return {"error": "invalid_priority", "message": err}

    requirement = requirement.strip()
    if not requirement:
        return {
            "error": "invalid_requirement",
            "message": "Requirement cannot be empty",
        }

    err = validate_status(status)
    if err:
        return {"error": "invalid_status", "message": err}

    requirement = _unescape_literal_newlines(requirement)
    notes = _unescape_literal_newlines(notes)

    target_dir = asr_status_dir(workspace_root, status)
    target_dir.mkdir(parents=True, exist_ok=True)

    number = next_asr_number(workspace_root)
    filename = make_asr_filename(number)
    target_path = target_dir / filename
    if target_path.exists():
        rel_existing = str(target_path.relative_to(workspace_root)).replace("\\", "/")
        return {
            "error": "already_exists",
            "message": f"ASR file already exists: {rel_existing}",
        }

    today = today_iso()
    asr = ASR(
        number=number,
        priority=priority,
        status=status,
        created=today,
        updated=today,
        requirement=requirement.strip(),
        notes=notes.strip(),
    )
    markdown = generate_asr(asr)
    target_path.write_text(markdown, encoding="utf-8")

    # Regenerate the governing index from the reference corpus. Fail closed:
    # withdraw the just-published record rather than leave a stale index.
    try:
        index_summary = rebuild_governance_indexes(workspace_root)
    except GovernanceIndexError as exc:
        with contextlib.suppress(OSError):
            target_path.unlink(missing_ok=True)
        return {"error": "index_rebuild_failed", "message": str(exc)}

    import json as _json

    rel_path = str(target_path.relative_to(workspace_root)).replace("\\", "/")
    return {
        "output": _json.dumps(
            {
                "path": rel_path,
                "number": number,
                "markdown": markdown,
                "index": index_summary,
            }
        ),
        "title": "Create ASR",
        "metadata": {"target": f"ASR-{number:04d}"},
    }


if __name__ == "__main__":
    import json
    import sys
    args = json.loads(sys.stdin.read())
    result = asr_create(
        priority=args["priority"],
        requirement=args["requirement"],
        notes=args.get("notes", ""),
        status=args.get("status", "Active"),
        workspace_root=Path(args["workspace_root"]),
    )
    print(json.dumps(result))
