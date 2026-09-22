"""Archive a terminal implementation graph after independent freshness checks."""
from __future__ import annotations

import json
import fcntl
import os
import shutil
from pathlib import Path

from ..helpers.implementation_graph import graph_path, implementation_state_digest, read_graph, output, workspace_fingerprint


def impl_graph_archive(graph_id: str, *, workspace_root: Path) -> dict:
    try:
        graph, source, location = read_graph(workspace_root, graph_id)
        if location != "pending":
            return {"error": "already_archived", "message": "graph is already completed"}
        graph_revision = graph.get("state_revision")
        graph_digest_value = implementation_state_digest(graph)
        workspace_fingerprint_value = workspace_fingerprint(workspace_root)
        required = [node for node in graph["nodes"] if node.get("status") != "SUPERSEDED"]
        if any(node.get("status") != "COMPLETE" for node in required):
            return {"error": "incomplete_graph", "message": "all required nodes must be complete"}
        if any(node.get("claim") is not None for node in graph["nodes"]):
            return {"error": "active_claims", "message": "active claims remain"}
        qa = graph.get("final_qa", {})
        if qa.get("status") != "PASS" or qa.get("graph_revision") != graph_revision or qa.get("implementation_state_digest") != graph_digest_value or qa.get("workspace_fingerprint") != workspace_fingerprint_value:
            return {"error": "qa_required", "message": "current terminal QA evidence does not match graph and workspace"}
        destination_dir = workspace_root / "artifacts/implementation/completed" / graph_id
        source_dir = source.parent
        if destination_dir.exists():
            return {"error": "already_exists", "message": "completed graph already exists"}
        lock_path = source_dir / ".GRAPH.lock"
        with open(lock_path, "a", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            # Re-read while holding the same mutation lock so archive cannot race a state update.
            graph, source, location = read_graph(workspace_root, graph_id)
            if location != "pending":
                return {"error": "already_archived", "message": "graph is already completed"}
            graph_revision = graph.get("state_revision")
            graph_digest_value = implementation_state_digest(graph)
            workspace_fingerprint_value = workspace_fingerprint(workspace_root)
            required = [node for node in graph["nodes"] if node.get("status") != "SUPERSEDED"]
            qa = graph.get("final_qa", {})
            if any(node.get("status") != "COMPLETE" for node in required):
                return {"error": "incomplete_graph", "message": "all required nodes must be complete"}
            if any(node.get("claim") is not None for node in graph["nodes"]):
                return {"error": "active_claims", "message": "active claims remain"}
            if qa.get("status") != "PASS" or qa.get("graph_revision") != graph_revision or qa.get("implementation_state_digest") != graph_digest_value or qa.get("workspace_fingerprint") != workspace_fingerprint_value:
                return {"error": "qa_required", "message": "current terminal QA evidence does not match graph and workspace"}
            destination_dir.parent.mkdir(parents=True, exist_ok=True)
            if destination_dir.exists():
                return {"error": "already_exists", "message": "completed graph already exists"}
            os.replace(source_dir, destination_dir)
            try:
                (destination_dir / ".GRAPH.lock").unlink()
            except FileNotFoundError:
                pass
        return output({"graph_id": graph_id, "path": str((destination_dir / "GRAPH.json").relative_to(workspace_root)), "archived": True}, "Archive Implementation Graph")
    except (ValueError, OSError) as exc:
        return {"error": "archive_failed", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_archive(graph_id=args["graph_id"], workspace_root=Path(args["workspace_root"]))))
