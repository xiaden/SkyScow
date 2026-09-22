"""Release claimed implementation nodes with matching identity."""
from __future__ import annotations
import json
from pathlib import Path
from ..helpers.implementation_graph import mutate_graph, node_map, output

def impl_graph_release(graph_id: str, node_ids: list[str], claim_id: str, *, workspace_root: Path) -> dict:
    try:
        def apply(graph):
            nodes = node_map(graph)
            for node_id in node_ids:
                node = nodes.get(node_id)
                if node is None or node.get("status") != "ACTIVE" or node.get("claim", {}).get("id") != claim_id:
                    raise ValueError(f"claim identity mismatch: {node_id}")
            for node_id in node_ids:
                nodes[node_id]["status"] = "PENDING"; nodes[node_id]["claim"] = None
        graph, _, _ = mutate_graph(workspace_root, graph_id, apply)
        return output({"graph_id": graph_id, "released": node_ids, "state_revision": graph["state_revision"], "structure_revision": graph["structure_revision"]}, "Release Implementation Nodes")
    except (ValueError, OSError) as exc: return {"error": "release_failed", "message": str(exc)}

if __name__ == "__main__":
    args = json.loads(input()); print(json.dumps(impl_graph_release(args["graph_id"], args["node_ids"], args["claim_id"], workspace_root=Path(args["workspace_root"]))))
