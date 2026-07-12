"""Tool implementation for dd_read — read and parse an existing Design Document."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..helpers.dd_md import (
    DD_PREFIX,
    DESIGNS_COMPLETED_DIR,
    DESIGNS_PENDING_DIR,
    parse_dd,
)


def _resolve_dd_path(name: str, workspace_root: Path) -> tuple[Path | None, str]:
    """Resolve a DD name to its file path, searching pending then completed.

    Accepts:
    - Full filename: "DD-my-feature.md"
    - Slug only: "my-feature"
    - Partial: "DD-my-feature"

    Returns (path_or_none, location_label).
    """
    # Normalize name
    if name.endswith(".md"):
        name = name[:-3]
    if not name.startswith(DD_PREFIX):
        name = f"{DD_PREFIX}{name}"
    filename = f"{name}.md"

    pending = workspace_root / DESIGNS_PENDING_DIR / filename
    if pending.exists():
        return pending, "pending"

    completed = workspace_root / DESIGNS_COMPLETED_DIR / filename
    if completed.exists():
        return completed, "completed"

    return None, ""


def dd_read(
    name: str,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    """Read and parse a Design Document.

    Accepts slug, filename, or DD-prefixed name.
    Returns structured document data on success.
    Returns {"error": "...", "message": "..."} on failure.
    """
    if not name.strip():
        return {"error": "invalid_name", "message": "Name cannot be empty"}

    # Reject path traversal
    if "/" in name or "\\" in name or ".." in name:
        return {
            "error": "invalid_name",
            "message": "Name must not contain path separators",
        }

    dd_path, location = _resolve_dd_path(name, workspace_root)
    if dd_path is None:
        return {
            "error": "dd_not_found",
            "message": f"Design document not found: {name}",
            "searched": [DESIGNS_PENDING_DIR, DESIGNS_COMPLETED_DIR],
        }

    try:
        markdown = dd_path.read_text(encoding="utf-8")
        doc = parse_dd(markdown)
    except (ValueError, OSError) as exc:
        return {"error": "parse_error", "message": str(exc)}

    import json as _json

    rel_path = str(dd_path.relative_to(workspace_root)).replace("\\", "/")
    return {
        "output": _json.dumps({"title": doc.title, "status": doc.status, "author": doc.author,
                               "created": doc.created, "revised": doc.revised,
                               "related_documents": doc.related_documents, "sections": doc.sections,
                               "location": location, "path": rel_path}),
        "title": "Read DD",
        "metadata": {"target": rel_path.split("/")[-1].replace(".md", "")},
    }


if __name__ == "__main__":
    import json
    import sys
    args = json.loads(sys.stdin.read())
    result = dd_read(
        name=args["name"],
        workspace_root=Path(args["workspace_root"]),
    )
    print(json.dumps(result))
