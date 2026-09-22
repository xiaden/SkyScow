"""Manager acceptance of claimed implementation nodes with per-node results."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.implementation_graph import mutate_graph, node_map, output


def impl_graph_complete(
    graph_id: str,
    node_ids: list[str],
    claim_id: str,
    results: list[dict[str, Any]],
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    if not isinstance(node_ids, list) or not node_ids or len(set(node_ids)) != len(node_ids):
        return {"error": "invalid_completion", "message": "node_ids must be a non-empty unique array"}
    if not isinstance(results, list) or len(results) != len(node_ids):
        return {"error": "invalid_completion", "message": "exactly one result is required for each claimed node"}
    by_id = {result.get("node_id"): result for result in results if isinstance(result, dict)}
    if set(by_id) != set(node_ids):
        return {"error": "invalid_completion", "message": "results must contain exactly the claimed node IDs"}
    try:
        def apply(graph):
            nodes = node_map(graph)
            for node_id in node_ids:
                node = nodes.get(node_id)
                if node is None or node.get("status") != "ACTIVE" or node.get("claim", {}).get("id") != claim_id:
                    raise ValueError(f"claim identity mismatch: {node_id}")
            for node_id in node_ids:
                result = by_id[node_id]
                node = nodes[node_id]
                if not isinstance(result.get("evidence"), list):
                    raise ValueError(f"evidence must be an array: {node_id}")
                node["status"] = "COMPLETE"
                node["claim"] = None
                node["evidence"] = result["evidence"]
                node["changed_files"] = result.get("changed_files", [])
                node["provenance"] = result.get("provenance", [])
                node["deviations"] = result.get("deviations", [])
                node["actual_contracts"] = result.get("actual_contracts", [])
                node["completion_result"] = {key: value for key, value in result.items() if key != "node_id"}
                for contract_id, actual in (result.get("actual_contracts") or {}).items() if isinstance(result.get("actual_contracts"), dict) else []:
                    contract = next((item for item in graph["contracts"] if item.get("id") == contract_id), None)
                    if contract is None:
                        raise ValueError(f"unknown actual contract: {contract_id}")
                    if contract.get("producer") != node_id:
                        raise ValueError(f"node is not the producer of contract: {contract_id}")
                    if contract.get("actual") not in (None, actual) and contract.get("actual") != actual:
                        raise ValueError(f"contradictory materialization: {contract_id}")
                    contract["actual"] = actual

        graph, _, _ = mutate_graph(workspace_root, graph_id, apply)
        return output({"graph_id": graph_id, "completed": node_ids, "state_revision": graph["state_revision"]}, "Complete Implementation Nodes")
    except (ValueError, OSError) as exc:
        return {"error": "complete_failed", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_complete(
        graph_id=args["graph_id"], node_ids=args["node_ids"], claim_id=args["claim_id"],
        results=args["results"], workspace_root=Path(args["workspace_root"]),
    )))
