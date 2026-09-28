"""Tool implementation for adr_read — read and parse an existing ADR."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..helpers.adr_md import (
    ADR_PREFIX,
    ADR_REFERENCES_DIR,
    LEGACY_DECISIONS_DIR,
    find_adr_number,
    iter_adr_records,
    legacy_adr_records,
    parse_adr,
)


def _resolve_adr_path(name: str, workspace_root: Path) -> Path | None:
    """Resolve an ADR name to its file path.

    Accepts:
    - Full filename: "ADR-003-use-edges.md"
    - With prefix: "ADR-003-use-edges"
    - Number only: "003" or "3"
    - Slug: "ADR-003"
    """
    # Strip .md
    name = name.removesuffix(".md")

    # If purely numeric, locate that number across every status directory
    stripped = name.removeprefix(ADR_PREFIX)
    if stripped.isdigit():
        return find_adr_number(workspace_root, int(stripped))

    # Try exact filename across every status directory
    if not name.startswith(ADR_PREFIX):
        name = f"{ADR_PREFIX}{name}"
    target_name = f"{name}.md"
    for record in iter_adr_records(workspace_root):
        if record.name == target_name:
            return record

    return None


def adr_read(
    name: str,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    """Read and parse an Architecture Decision Record.

    Accepts number, slug, filename, or ADR-prefixed name.
    Returns structured ADR data on success.
    Returns {"error": "...", "message": "..."} on failure.
    """
    if not name.strip():
        return {"error": "invalid_name", "message": "Name cannot be empty"}

    # Reject path traversal
    if "/" in name or "\\" in name or ".." in name:
        return {"error": "invalid_name", "message": "Name must not contain path separators"}

    adr_path = _resolve_adr_path(name, workspace_root)
    if adr_path is None:
        if legacy_adr_records(workspace_root):
            return {
                "error": "migration_required",
                "message": (
                    f"Legacy ADR corpus found under '{LEGACY_DECISIONS_DIR}/' but no "
                    "canonical records exist. Run the governance_migrate tool before "
                    "reading or writing ADRs."
                ),
                "legacy_dir": LEGACY_DECISIONS_DIR,
                "searched": ADR_REFERENCES_DIR,
            }
        return {
            "error": "adr_not_found",
            "message": f"ADR not found: {name}",
            "searched": ADR_REFERENCES_DIR,
        }

    try:
        markdown = adr_path.read_text(encoding="utf-8")
        adr = parse_adr(markdown)
    except (ValueError, OSError) as exc:
        return {"error": "parse_error", "message": str(exc)}

    rel_path = str(adr_path.relative_to(workspace_root)).replace("\\", "/")
    import json as _json
    return {
        "output": _json.dumps({"number": adr.number, "title": adr.title, "status": adr.status,
                               "date": adr.date, "tags": adr.tags, "source_log": adr.source_log,
                               "sections": adr.sections, "path": rel_path}),
        "title": "Read ADR",
        "metadata": {"target": rel_path.split("/")[-1].replace(".md", "")},
    }


if __name__ == "__main__":
    import json
    import sys
    args = json.loads(sys.stdin.read())
    result = adr_read(
        name=args["name"],
        workspace_root=Path(args["workspace_root"]),
    )
    print(json.dumps(result))
