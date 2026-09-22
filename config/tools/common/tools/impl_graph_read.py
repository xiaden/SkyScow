"""Read bounded views of a persistent implementation graph."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.implementation_graph import output, read_graph


def _ready(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = {node["id"]: node for node in graph["nodes"]}
    return [node for node in graph["nodes"] if node.get("status") == "PENDING" and all(nodes.get(dep, {}).get("status") == "COMPLETE" for dep in node.get("depends_on", []))]


def _summary(graph: dict[str, Any]) -> dict[str, Any]:
    counts = {status: 0 for status in ("PENDING", "ACTIVE", "COMPLETE", "BLOCKED", "SUPERSEDED")}
    for node in graph["nodes"]:
        status = node.get("status", "PENDING")
        counts[status] = counts.get(status, 0) + 1
    ready = _ready(graph)
    return {"graph_id": graph["graph_id"], "title": graph["title"], "structure_revision": graph.get("structure_revision", 1), "state_revision": graph.get("state_revision", graph.get("revision", 1)), "revision": graph.get("revision", 1), "counts": counts, "ready": [node["id"] for node in ready], "final_qa": graph["final_qa"]}


def impl_graph_read(graph_id: str, view: str = "summary", node_ids: list[str] | None = None, requirement_id: str | None = None, contract_id: str | None = None, limit: int = 20, *, workspace_root: Path) -> dict[str, Any]:
    try:
        graph, path, location = read_graph(workspace_root, graph_id)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": "graph_read_failed", "message": str(exc)}
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        return {"error": "invalid_limit", "message": "limit must be a positive integer"}
    if view == "summary":
        payload: Any = _summary(graph)
    elif view in {"ready", "active", "blocked", "incomplete"}:
        nodes = graph["nodes"]
        if view == "ready":
            nodes = _ready(graph)
        elif view == "active":
            nodes = [node for node in nodes if node.get("status") == "ACTIVE"]
        elif view == "blocked":
            nodes = [node for node in nodes if node.get("status") == "BLOCKED"]
        else:
            nodes = [node for node in nodes if node.get("status") not in {"COMPLETE", "SUPERSEDED"}]
        payload = {"graph_id": graph_id, "nodes": nodes[:limit]}
    elif view == "node":
        wanted = set(node_ids or [])
        payload = {"graph_id": graph_id, "nodes": [node for node in graph["nodes"] if node["id"] in wanted][:limit]}
    elif view == "requirements":
        nodes = [node for node in graph["nodes"] if not requirement_id or requirement_id in node.get("satisfies", [])]
        payload = {"graph_id": graph_id, "requirements": graph["requirements"], "nodes": nodes[:limit]}
    elif view == "contracts":
        contracts = [contract for contract in graph["contracts"] if not contract_id or contract["id"] == contract_id]
        payload = {"graph_id": graph_id, "contracts": contracts[:limit]}
    elif view == "terminal":
        payload = {"graph_id": graph_id, "final_qa": graph["final_qa"], "summary": _summary(graph)}
    else:
        return {"error": "invalid_view", "message": "view must be summary, ready, active, blocked, incomplete, node, requirements, contracts, or terminal"}
    return output(payload, "Read Implementation Graph", {"graph_id": graph_id, "view": view, "location": location, "path": str(path.relative_to(workspace_root))})


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_read(graph_id=args["graph_id"], view=args.get("view", "summary"), node_ids=args.get("node_ids"), requirement_id=args.get("requirement_id"), contract_id=args.get("contract_id"), limit=args.get("limit", 20), workspace_root=Path(args["workspace_root"]))))
