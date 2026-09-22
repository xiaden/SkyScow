"""Manager acceptance of claimed implementation nodes."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from ..helpers.implementation_graph import mutate_graph, node_map, output

def impl_graph_complete(graph_id: str, node_ids: list[str], claim_id: str, evidence: list[Any] | None = None, changed_files: list[str] | None = None, provenance: list[Any] | None = None, deviations: list[str] | None = None, actual_contracts: list[Any] | None = None, *, workspace_root: Path) -> dict:
    def apply(graph):
        nodes = node_map(graph)
        for node_id in node_ids:
            node = nodes.get(node_id)
            if node is None or node.get("status") != "ACTIVE" or node.get("claim", {}).get("id") != claim_id: raise ValueError(f"claim identity mismatch: {node_id}")
        for node_id in node_ids:
            node = nodes[node_id]; node["status"] = "COMPLETE"; node["claim"] = None; node["evidence"] = evidence or []; node["changed_files"] = changed_files or []; node["provenance"] = provenance or []; node["deviations"] = deviations or []; node["actual_contracts"] = actual_contracts or []
    try:
        graph, _, _ = mutate_graph(workspace_root, graph_id, apply)
        return output({"graph_id": graph_id, "completed": node_ids, "revision": graph["revision"]}, "Complete Implementation Nodes")
    except (ValueError, OSError) as exc: return {"error": "complete_failed", "message": str(exc)}

if __name__ == "__main__":
    args = json.loads(input()); print(json.dumps(impl_graph_complete(graph_id=args["graph_id"], node_ids=args["node_ids"], claim_id=args["claim_id"], evidence=args.get("evidence"), changed_files=args.get("changed_files"), provenance=args.get("provenance"), deviations=args.get("deviations"), actual_contracts=args.get("actual_contracts"), workspace_root=Path(args["workspace_root"]))))
