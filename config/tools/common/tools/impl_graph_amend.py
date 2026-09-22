"""Planner amendment of pending implementation topology."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from ..helpers.implementation_graph import mutate_graph, node_map, output, validate_graph

def impl_graph_amend(graph_id: str, nodes: list[dict[str, Any]] | None = None, remove_node_ids: list[str] | None = None, requirements: list[dict[str, Any]] | None = None, contracts: list[dict[str, Any]] | None = None, actor: str | None = None, *, workspace_root: Path) -> dict:
    try:
        def apply(graph):
            current = node_map(graph); remove = set(remove_node_ids or [])
            for node_id in remove:
                if current.get(node_id, {}).get("status") in {"ACTIVE", "COMPLETE"}: raise ValueError(f"cannot remove historical node: {node_id}")
            graph["nodes"] = [node for node in graph["nodes"] if node["id"] not in remove]
            if nodes:
                existing = {node["id"] for node in graph["nodes"]}
                if existing.intersection(node["id"] for node in nodes): raise ValueError("amendment cannot silently replace existing nodes")
                graph["nodes"].extend(nodes)
            if requirements is not None: graph["requirements"] = requirements
            if contracts is not None: graph["contracts"] = contracts
        graph, _, _ = mutate_graph(workspace_root, graph_id, apply)
        errors = validate_graph(graph, workspace_root)
        if errors: return {"error": "invalid_amendment", "message": "; ".join(errors[:8]), "errors": errors}
        return output({"graph_id": graph_id, "revision": graph["revision"], "amended": True}, "Amend Implementation Graph")
    except (ValueError, OSError) as exc: return {"error": "amend_failed", "message": str(exc)}

if __name__ == "__main__":
    args = json.loads(input()); print(json.dumps(impl_graph_amend(graph_id=args["graph_id"], nodes=args.get("nodes"), remove_node_ids=args.get("remove_node_ids"), requirements=args.get("requirements"), contracts=args.get("contracts"), actor=args.get("actor"), workspace_root=Path(args["workspace_root"]))))
