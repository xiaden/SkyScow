"""Record terminal QA bound to canonical graph state and workspace evidence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.implementation_graph import implementation_state_digest, mutate_graph, output, read_graph, workspace_fingerprint


def impl_graph_record_qa(graph_id: str, status: str, evidence: Any, *, workspace_root: Path) -> dict:
    if status not in {"PASS", "FAIL"}:
        return {"error": "invalid_qa", "message": "status must be PASS or FAIL"}
    try:
        current, _, location = read_graph(workspace_root, graph_id)
        if location != "pending":
            return {"error": "completed_immutable", "message": "completed graphs are immutable"}
        graph_revision = current.get("state_revision")
        actual_digest = implementation_state_digest(current)
        actual_fingerprint = workspace_fingerprint(workspace_root)

        def apply(graph):
            if graph.get("state_revision") != graph_revision or implementation_state_digest(graph) != actual_digest:
                raise ValueError("graph changed while recording QA")
            if workspace_fingerprint(workspace_root) != actual_fingerprint:
                raise ValueError("workspace changed while recording QA")
            graph["final_qa"] = {
                "status": status,
                "graph_revision": graph_revision,
                "implementation_state_digest": actual_digest,
                "workspace_fingerprint": actual_fingerprint,
                "evidence": evidence,
            }

        graph, _, _ = mutate_graph(workspace_root, graph_id, apply, invalidate_qa=False, increment_state=False)
        return output({"graph_id": graph_id, "status": status, "state_revision": graph["state_revision"], "implementation_state_digest": actual_digest}, "Record Implementation Graph QA")
    except (ValueError, OSError) as exc:
        return {"error": "qa_record_failed", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_record_qa(
        graph_id=args["graph_id"], status=args["status"], evidence=args.get("evidence"),
        workspace_root=Path(args["workspace_root"]),
    )))
