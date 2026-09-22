"""Atomically claim derived-ready implementation nodes."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from ..helpers.implementation_graph import derived_ready, mutate_graph, node_map, output

def impl_graph_claim(graph_id: str, node_ids: list[str], claim_id: str, worker: str | None = None, changed_files: list[str] | None = None, *, workspace_root: Path) -> dict[str, Any]:
    if not isinstance(node_ids, list) or not node_ids or not isinstance(claim_id, str) or not claim_id.strip():
        return {"error": "invalid_claim", "message": "node_ids and claim_id are required"}
    changed = set(changed_files or [])
    try:
        def apply(graph):
            nodes = node_map(graph); ready = {n["id"] for n in derived_ready(graph)}
            for node_id in node_ids:
                node = nodes.get(node_id)
                if node is None: raise ValueError(f"unknown node: {node_id}")
                if node_id not in ready: raise ValueError(f"node is not ready: {node_id}")
                if node.get("claim") is not None: raise ValueError(f"node already claimed: {node_id}")
                if changed and changed.intersection(set(node.get("changed_files", []))): raise ValueError(f"known write overlap: {node_id}")
            for node_id in node_ids:
                node = nodes[node_id]; node["status"] = "ACTIVE"; node["claim"] = {"id": claim_id, "worker": worker, "changed_files": sorted(changed)}
        graph, _, _ = mutate_graph(workspace_root, graph_id, apply)
        return output({"graph_id": graph_id, "claim_id": claim_id, "claimed": node_ids, "revision": graph["revision"]}, "Claim Implementation Nodes")
    except (ValueError, OSError) as exc:
        return {"error": "claim_failed", "message": str(exc)}

if __name__ == "__main__":
    args = json.loads(input()); print(json.dumps(impl_graph_claim(args["graph_id"], args["node_ids"], args["claim_id"], args.get("worker"), args.get("changed_files"), workspace_root=Path(args["workspace_root"]))))
