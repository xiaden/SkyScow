"""Archive a design document with graph-native and explicit legacy paths."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from ..helpers.dd_md import DD_FILENAME, DESIGNS_COMPLETED_DIR, DESIGNS_PENDING_DIR, dd_bundle_slug, parse_dd
from ..helpers.implementation_graph import locate_graph, read_graph

PLANS_PENDING_DIR = "artifacts/plans/pending"
GRAPH_PENDING_DIR = "artifacts/implementation/pending"
GRAPH_COMPLETED_DIR = "artifacts/implementation/completed"


def _linked_graph_ids(doc: Any, slug: str) -> list[str]:
    candidates: list[str] = []
    for related in getattr(doc, "related_documents", []):
        path = related.get("path", "")
        match = re.search(r"artifacts/implementation/(?:pending|completed)/([^/]+)/GRAPH\.json", path)
        if match:
            candidates.append(match.group(1))
    for heading, content in getattr(doc, "sections", {}).items():
        for match in re.findall(r"(?:graph_id|graphId)\s*[:=]\s*[`\"']?([a-z0-9][a-z0-9-]*)", content):
            candidates.append(match)
        if heading.lower() in {"implementation graph", "implementation graphs", "graph"}:
            candidates.extend(re.findall(r"\b([a-z0-9][a-z0-9-]{1,})\b", content))
    return sorted({graph_id for graph_id in candidates if graph_id != slug})


def _graph_terminal(workspace_root: Path, graph_id: str) -> tuple[bool, str]:
    try:
        graph, _, location = read_graph(workspace_root, graph_id)
    except (FileNotFoundError, ValueError) as exc:
        return False, str(exc)
    if location != "completed":
        return False, f"graph is not archived: {graph_id}"
    qa = graph.get("final_qa", {})
    if qa.get("status") != "PASS":
        return False, f"graph has no terminal QA PASS: {graph_id}"
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

    linked_graphs = _linked_graph_ids(doc, slug)
    if linked_graphs:
        graph_errors = []
        for graph_id in linked_graphs:
            ok, message = _graph_terminal(workspace_root, graph_id)
            if not ok:
                graph_errors.append(message)
        if graph_errors:
            return {"error": "linked_graphs_incomplete", "message": "; ".join(graph_errors), "linked_graphs": linked_graphs}
    else:
        # Explicit legacy behavior: only DD-convention-linked plans block a legacy DD.
        pending_dir = workspace_root / PLANS_PENDING_DIR
        pending_plans = sorted(path.name for path in pending_dir.glob(f"TASK-{slug}-*.md")) if pending_dir.exists() else []
        found_via_readme = False
        if (source_dir / "README.md").is_file():
            refs = re.findall(r"TASK-[\w-]+", (source_dir / "README.md").read_text(encoding="utf-8"))
            readme_plans = [f"{ref}.md" for ref in refs if (pending_dir / f"{ref}.md").exists()]
            found_via_readme = bool(readme_plans)
            pending_plans.extend(readme_plans)
            pending_plans = sorted(set(pending_plans))
        if pending_plans:
            suffix = " (found via parts README)" if found_via_readme else ""
            return {"error": "pending_plans", "message": f"Cannot archive: {len(pending_plans)} linked legacy plans still in pending{suffix}", "pending_plans": pending_plans}

    dest = workspace_root / DESIGNS_COMPLETED_DIR / slug
    if dest.exists() and not force:
        return {"error": "already_exists", "message": f"Completed design document already exists: {DESIGNS_COMPLETED_DIR}/{slug}"}
    updated = re.sub(r"^\*\*Status:\*\*\s+\S+", "**Status:** Completed", markdown, count=1, flags=re.MULTILINE)
    source.write_text(updated, encoding="utf-8")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(source_dir), str(dest))
    return {"output": json.dumps({"archived": True, "path": f"{DESIGNS_COMPLETED_DIR}/{slug}/{DD_FILENAME}", "linked_graphs": linked_graphs}), "title": "Archive DD", "metadata": {"target": f"DD-{slug}"}}


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(dd_archive(args["name"], args.get("force", False), workspace_root=Path(args["workspace_root"]))))
