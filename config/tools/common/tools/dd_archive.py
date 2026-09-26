"""Archive a design document after linked Change DAG completion."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from ..helpers.change_dag import locate_dag
from ..helpers.dd_md import DD_FILENAME, DESIGNS_COMPLETED_DIR, DESIGNS_PENDING_DIR, dd_bundle_slug, parse_dd


_DAG_RELATED_PATH = re.compile(r"artifacts/change-dags/(?:pending|completed)/([^/]+)/DAG\.json")
_DAG_REFERENCE = re.compile(r"(?:dag_slug|dagSlug)\s*[:=]\s*[`\"']?([a-z0-9][a-z0-9-]*)|/([a-z0-9][a-z0-9-]*)/DAG\.json")
_PLAN_REFERENCE = re.compile(r"TASK-[A-Za-z0-9][A-Za-z0-9-]*(?:\.md)?")
_PREREQUISITE_HEADING = "approved prerequisite metadata"


def _linked_dag_slugs(doc: Any) -> list[str]:
    candidates: set[str] = set()
    for related in getattr(doc, "related_documents", []):
        path = related.get("path", "")
        match = _DAG_RELATED_PATH.search(path)
        if match:
            candidates.add(match.group(1))
    for heading, content in getattr(doc, "sections", {}).items():
        if heading.strip().lower() not in {"change dag", "change dags", "dag"}:
            continue
        for match in _DAG_REFERENCE.finditer(content):
            candidates.add(match.group(1) or match.group(2))
    return sorted(candidates)


def _declared_prerequisite(markdown: str, doc: Any) -> bool:
    if re.search(r"^\*\*Prerequisite disposition:\*\*", markdown, flags=re.MULTILINE):
        return True
    if any(heading.strip().lower() == _PREREQUISITE_HEADING for heading in getattr(doc, "sections", {})):
        return True
    return "accepted prerequisite for planning" in markdown.lower()


def _prerequisite_text(markdown: str, doc: Any) -> str:
    lines = markdown.splitlines()
    declared = [line for line in lines if re.match(r"^\*\*Prerequisite disposition:\*\*", line)]
    for heading, content in getattr(doc, "sections", {}).items():
        if heading.strip().lower() == _PREREQUISITE_HEADING:
            declared.append(content)
    return "\n".join(declared)


def _prerequisite_terminal(workspace_root: Path, slug: str, prerequisite_text: str, linked_dags: list[str]) -> tuple[bool, str]:
    if linked_dags and _DAG_REFERENCE.search(prerequisite_text):
        return True, ""
    references = set(_PLAN_REFERENCE.findall(prerequisite_text))
    completed_dir = workspace_root / "artifacts/plans/completed"
    if references:
        candidates = [reference if reference.endswith(".md") else f"{reference}.md" for reference in references]
    else:
        candidates = []
    if not candidates:
        # Fallback: a declared prerequisite that names no explicit artifact (e.g. the
        # capture-request-context DD says "only after the linked implementation plan is
        # complete") resolves against the DD's own bundled-plan convention
        # artifacts/plans/completed/TASK-{slug}-*.md. This is deliberately slug-scoped
        # and uses only the declared-prerequisite text passed in -- it is not a
        # whole-document scan, so historical TASK-*.md mentions cannot satisfy the gate.
        candidates = [f"TASK-{slug}-"]
    for candidate in candidates:
        if candidate.endswith("-"):
            if any(path.is_file() for path in completed_dir.glob(f"{candidate}*.md")):
                return True, ""
        elif (completed_dir / candidate).is_file():
            return True, ""
    return False, f"declared prerequisite is not completed: {', '.join(sorted(candidates))}"


def _dag_terminal(workspace_root: Path, dag_slug: str) -> tuple[bool, str]:
    _path, location = locate_dag(workspace_root, dag_slug)
    if location is None:
        return False, f"change dag not found: {dag_slug}"
    if location != "completed":
        return False, f"change dag is not archived: {dag_slug}"
    return True, ""


def dd_archive(name: str, force: bool = False, *, workspace_root: Path) -> dict[str, Any]:
    if not name.strip() or "/" in name or "\\" in name or ".." in name:
        return {"error": "invalid_name", "message": "Name must be a safe DD name"}
    try:
        slug = dd_bundle_slug(name)
    except ValueError as exc:
        return {"error": "invalid_name", "message": str(exc)}
    source_dir = workspace_root / DESIGNS_PENDING_DIR / slug
    source = source_dir / DD_FILENAME
    if not source.is_file():
        return {"error": "not_found", "message": f"Design document not found in pending: {slug}/{DD_FILENAME}"}
    try:
        markdown = source.read_text(encoding="utf-8")
        doc = parse_dd(markdown)
    except (ValueError, OSError) as exc:
        return {"error": "parse_error", "message": str(exc)}

    linked_dags = _linked_dag_slugs(doc)
    prerequisite_declared = _declared_prerequisite(markdown, doc)
    dag_errors = []
    for dag_slug in linked_dags:
        ok, message = _dag_terminal(workspace_root, dag_slug)
        if not ok:
            dag_errors.append(message)
    if dag_errors:
        return {"error": "linked_dags_incomplete", "message": "; ".join(dag_errors), "linked_dags": linked_dags}
    if prerequisite_declared:
        prerequisite_ok, prerequisite_message = _prerequisite_terminal(workspace_root, slug, _prerequisite_text(markdown, doc), linked_dags)
        if not prerequisite_ok:
            return {"error": "prerequisite_unsatisfied", "message": prerequisite_message, "linked_dags": linked_dags}

    dest = workspace_root / DESIGNS_COMPLETED_DIR / slug
    if dest.exists() and not force:
        return {"error": "already_exists", "message": f"Completed design document already exists: {DESIGNS_COMPLETED_DIR}/{slug}"}
    updated = re.sub(r"^\*\*Status:\*\*\s+\S+", "**Status:** Completed", markdown, count=1, flags=re.MULTILINE)
    source.write_text(updated, encoding="utf-8")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(source_dir), str(dest))
    return {"output": json.dumps({"archived": True, "path": f"{DESIGNS_COMPLETED_DIR}/{slug}/{DD_FILENAME}", "linked_dags": linked_dags}), "title": "Archive DD", "metadata": {"target": f"DD-{slug}"}}


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(dd_archive(args["name"], args.get("force", False), workspace_root=Path(args["workspace_root"]))))
