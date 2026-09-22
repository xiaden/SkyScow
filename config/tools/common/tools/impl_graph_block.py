"""Manager blocking of implementation nodes."""
from __future__ import annotations
import json
from pathlib import Path
from ..helpers.implementation_graph import mutate_graph, node_map, output

def impl_graph_block(graph_id: str, node_ids: list[str], reason: str, claim_id: str | None = None, *, workspace_root: Path) -> dict:
    if not isinstance(reason, str) or not reason.strip(): return {"error": "invalid_block", "message": "reason is required"}
    try:
        def apply(graph):
            nodes = node_map(graph)
            for node_id in node_ids:
                node = nodes.get(node_id)
                if node is None: raise ValueError(f"unknown node: {node_id}")
                if node.get("status") == "ACTIVE" and node.get("claim", {}).get("id") != claim_id: raise ValueError(f"claim identity mismatch: {node_id}")
                if node.get("status") in {"COMPLETE", "SUPERSEDED"}: raise ValueError(f"cannot block terminal node: {node_id}")
            for node_id in node_ids:
                node = nodes[node_id]; node["status"] = "BLOCKED"; node["claim"] = None; node["blocker"] = reason
        graph, _, _ = mutate_graph(workspace_root, graph_id, apply)
        return output({"graph_id": graph_id, "blocked": node_ids, "state_revision": graph["state_revision"], "structure_revision": graph["structure_revision"]}, "Block Implementation Nodes")
    except (ValueError, OSError) as exc: return {"error": "block_failed", "message": str(exc)}

if __name__ == "__main__":
    args = json.loads(input()); print(json.dumps(impl_graph_block(args["graph_id"], args["node_ids"], args["reason"], args.get("claim_id"), workspace_root=Path(args["workspace_root"]))))
