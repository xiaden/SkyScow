"""Planner amendments to pending implementation-graph topology."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.implementation_graph import mutate_graph, node_map, output, validate_graph


def impl_graph_amend(
    graph_id: str,
    nodes: list[dict[str, Any]] | None = None,
    remove_node_ids: list[str] | None = None,
    requirements: list[dict[str, Any]] | None = None,
    contracts: list[dict[str, Any]] | None = None,
    actor: str | None = None,
    reason: str | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    if not isinstance(actor, str) or not actor.strip() or not isinstance(reason, str) or not reason.strip():
        return {"error": "invalid_amendment", "message": "actor and reason are required"}
    if requirements is not None or contracts is not None:
        return {"error": "broad_replacement_forbidden", "message": "requirements and contracts arrays cannot be replaced wholesale"}
    try:
        def apply(graph):
            current = node_map(graph)
            if any(node.get("status") == "ACTIVE" for node in current.values()):
                raise ValueError("cannot amend while active claims exist")
            remove = set(remove_node_ids or [])
            for node_id in remove:
                if node_id not in current:
                    raise ValueError(f"unknown node: {node_id}")
                if current[node_id].get("status") in {"ACTIVE", "COMPLETE"}:
                    raise ValueError(f"cannot remove historical node: {node_id}")
            additions = nodes or []
            existing = set(current) - remove
            if existing.intersection(node.get("id") for node in additions):
                raise ValueError("amendment cannot silently replace existing nodes")
            for node in additions:
                if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"].strip():
                    raise ValueError("amendment nodes require non-empty ids")
                node.setdefault("status", "PENDING")
                node.setdefault("depends_on", [])
                node.setdefault("satisfies", [])
                node.setdefault("acceptance", [])
                node.setdefault("consumes", [])
                node.setdefault("produces", [])
            graph["nodes"] = [node for node in graph["nodes"] if node["id"] not in remove] + additions
            graph.setdefault("amendments", []).append({
                "actor": actor,
                "reason": reason,
                "affected_node_ids": sorted(remove | {node.get("id") for node in additions if node.get("id")}),
            })

        graph, _, _ = mutate_graph(workspace_root, graph_id, apply, structural_change=True)
        errors = validate_graph(graph, workspace_root)
        if errors:
            return {"error": "invalid_amendment", "message": "; ".join(errors[:8]), "errors": errors}
        return output({"graph_id": graph_id, "structure_revision": graph["structure_revision"], "state_revision": graph["state_revision"], "amended": True}, "Amend Implementation Graph")
    except (ValueError, OSError) as exc:
        return {"error": "amend_failed", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_amend(
        graph_id=args["graph_id"], nodes=args.get("nodes"), remove_node_ids=args.get("remove_node_ids"),
        requirements=args.get("requirements"), contracts=args.get("contracts"), actor=args.get("actor"),
        reason=args.get("reason"), workspace_root=Path(args["workspace_root"]),
    )))
