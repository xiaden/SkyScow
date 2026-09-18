"""Tool implementation for dd_archive — archive a completed design document."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from ..helpers.dd_md import (
    DD_FILENAME,
    DESIGNS_COMPLETED_DIR,
    DESIGNS_PENDING_DIR,
    dd_bundle_slug,
    parse_dd,
)

PLANS_PENDING_DIR = "artifacts/plans/pending"


def dd_archive(
    name: str,
    force: bool = False,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    """Complete and archive a pending Design Document bundle.

    Verifies all convention-linked plans are completed first, then records
    ``**Status:** Completed`` in ``DD.md`` before attempting to move the
    entire bundle to the completed designs directory. The status is
    authoritative: if the ordinary bundle move cannot complete, the completed
    DD may remain in its pending bundle location and can be retried.

    Returns {"archived": True, "path": "...", "linked_plans_completed": [...]} on success.
    Returns {"error": "...", "message": "..."} on validation or archival failure.
    """
    if not name.strip():
        return {"error": "invalid_name", "message": "Name cannot be empty"}

    # Reject path traversal
    if "/" in name or "\\" in name or ".." in name:
        return {
            "error": "invalid_name",
            "message": "Name must not contain path separators",
        }

    try:
        slug = dd_bundle_slug(name)
    except ValueError as exc:
        return {"error": "invalid_name", "message": str(exc)}

    source_dir = workspace_root / DESIGNS_PENDING_DIR / slug
    source = source_dir / DD_FILENAME
    if not source.exists():
        return {
            "error": "not_found",
            "message": f"Design document not found in pending: {slug}/{DD_FILENAME}",
        }

    # Validate DD is parseable
    try:
        markdown = source.read_text(encoding="utf-8")
        parse_dd(markdown)
    except (ValueError, OSError) as exc:
        return {"error": "parse_error", "message": str(exc)}

    # Check for linked plans still in pending
    pending_dir = workspace_root / PLANS_PENDING_DIR
    pending_plans: list[str] = []
    completed_plans: list[str] = []

    if pending_dir.exists():
        pattern = f"TASK-{slug}-*.md"
        pending_plans.extend(plan_file.name for plan_file in pending_dir.glob(pattern))

    if pending_plans:
        return {
            "error": "pending_plans",
            "message": (f"Cannot archive: {len(pending_plans)} linked plans still in pending"),
            "pending_plans": pending_plans,
        }

    # Check completed plans (for the report)
    completed_dir = workspace_root / "artifacts/plans/completed"
    if completed_dir.exists():
        pattern = f"TASK-{slug}-*.md"
        completed_plans.extend(plan_file.name for plan_file in completed_dir.glob(pattern))

    # Check the bundle README for linked plan names.
    parts_readme = source_dir / "README.md"
    if parts_readme.exists():
        try:
            readme_text = parts_readme.read_text(encoding="utf-8")
            # Find TASK references
            task_refs = re.findall(r"TASK-[\w-]+", readme_text)
            for ref in task_refs:
                ref_file = f"{ref}.md"
                if (pending_dir / ref_file).exists() and ref_file not in pending_plans:
                    pending_plans.append(ref_file)
        except OSError:
            pass

    if pending_plans:
        return {
            "error": "pending_plans",
            "message": (
                f"Cannot archive: {len(pending_plans)} linked plans "
                "still in pending (found via parts README)"
            ),
            "pending_plans": pending_plans,
        }

    dest_dir = workspace_root / DESIGNS_COMPLETED_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / slug
    if dest.exists() and not force:
        return {
            "error": "already_exists",
            "message": f"Completed design document already exists: {DESIGNS_COMPLETED_DIR}/{slug}",
        }

    # Update status only after a normal collision check. Force explicitly
    # authorizes replacing the existing completed bundle.
    updated_markdown = re.sub(
        r"^\*\*Status:\*\*\s+\S+",
        "**Status:** Completed",
        markdown,
        count=1,
        flags=re.MULTILINE,
    )
    source.write_text(updated_markdown, encoding="utf-8")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(source_dir), str(dest))

    import json as _json

    rel_path = f"{DESIGNS_COMPLETED_DIR}/{slug}/{DD_FILENAME}"
    return {
        "output": _json.dumps({"archived": True, "path": rel_path, "linked_plans_completed": completed_plans}),
        "title": "Archive DD",
        "metadata": {"target": f"DD-{slug}"},
    }


if __name__ == "__main__":
    import json
    import sys
    args = json.loads(sys.stdin.read())
    result = dd_archive(
        name=args["name"],
        force=args.get("force", False),
        workspace_root=Path(args["workspace_root"]),
    )
    print(json.dumps(result))
