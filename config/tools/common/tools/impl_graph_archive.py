"""Archive a terminal implementation graph after freshness checks."""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from ..helpers.implementation_graph import graph_digest, graph_path, locate_graph, read_graph, output, workspace_fingerprint


def impl_graph_archive(graph_id: str, graph_revision: int, graph_digest_value: str, workspace_fingerprint_value: str, *, workspace_root: Path) -> dict:
    try:
        graph, source, location = read_graph(workspace_root, graph_id)
        if location != "pending":
            return {"error": "already_archived", "message": "graph is already completed"}
        if graph.get("revision") != graph_revision:
            return {"error": "stale_revision", "message": "graph revision does not match"}
        if graph_digest(graph) != graph_digest_value:
            return {"error": "stale_digest", "message": "graph digest does not match"}
        if workspace_fingerprint(workspace_root) != workspace_fingerprint_value:
            return {"error": "stale_workspace", "message": "workspace fingerprint does not match"}
        required = [node for node in graph["nodes"] if node.get("status") != "SUPERSEDED"]
        if any(node.get("status") != "COMPLETE" for node in required):
            return {"error": "incomplete_graph", "message": "all required nodes must be complete"}
        if any(node.get("claim") is not None for node in graph["nodes"]):
            return {"error": "active_claims", "message": "active claims remain"}
        if graph.get("final_qa", {}).get("status") != "PASS":
            return {"error": "qa_required", "message": "current terminal QA PASS is required"}
        destination = graph_path(workspace_root, graph_id, completed=True)
        if destination.exists():
            return {"error": "already_exists", "message": "completed graph already exists"}
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        lock = source.with_name(".GRAPH.lock")
        if lock.exists():
            lock.unlink()
        return output({"graph_id": graph_id, "path": str(destination.relative_to(workspace_root)), "archived": True}, "Archive Implementation Graph")
    except (ValueError, OSError) as exc:
        return {"error": "archive_failed", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_archive(graph_id=args["graph_id"], graph_revision=args["graph_revision"], graph_digest_value=args["graph_digest"], workspace_fingerprint_value=args["workspace_fingerprint"], workspace_root=Path(args["workspace_root"]))))
