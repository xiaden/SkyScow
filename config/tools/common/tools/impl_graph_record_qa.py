"""Record terminal QA bound to the current graph and workspace."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from ..helpers.implementation_graph import graph_digest, mutate_graph, output, read_graph, workspace_fingerprint


def impl_graph_record_qa(graph_id: str, status: str, evidence: Any, graph_revision: int, graph_digest_value: str, workspace_fingerprint_value: str, *, workspace_root: Path) -> dict:
    if status not in {"PASS", "FAIL"}:
        return {"error": "invalid_qa", "message": "status must be PASS or FAIL"}
    try:
        current, _, location = read_graph(workspace_root, graph_id)
        if location != "pending":
            return {"error": "completed_immutable", "message": "completed graphs are immutable"}
        if graph_revision != current.get("revision"):
            return {"error": "stale_revision", "message": "graph revision does not match"}
        if graph_digest_value != graph_digest(current):
            return {"error": "stale_digest", "message": "graph digest does not match"}
        actual_fingerprint = workspace_fingerprint(workspace_root)
        if workspace_fingerprint_value != actual_fingerprint:
            return {"error": "stale_workspace", "message": "workspace fingerprint does not match"}
        def apply(graph):
            if graph.get("revision") != graph_revision or graph_digest(graph) != graph_digest_value:
                raise ValueError("graph changed while recording QA")
            graph["final_qa"] = {"status": status, "graph_revision": graph_revision, "graph_digest": graph_digest_value, "workspace_fingerprint": actual_fingerprint, "evidence": evidence}
        graph, _, _ = mutate_graph(workspace_root, graph_id, apply, invalidate_qa=False, increment_revision=False)
        return output({"graph_id": graph_id, "status": status, "revision": graph["revision"]}, "Record Implementation Graph QA")
    except (ValueError, OSError) as exc:
        return {"error": "qa_record_failed", "message": str(exc)}

if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_record_qa(graph_id=args["graph_id"], status=args["status"], evidence=args.get("evidence"), graph_revision=args["graph_revision"], graph_digest_value=args["graph_digest"], workspace_fingerprint_value=args["workspace_fingerprint"], workspace_root=Path(args["workspace_root"]))))
