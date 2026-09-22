"""Atomically claim a compatible ready frontier of implementation nodes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.implementation_graph import derived_ready, graph_structure_digest, mutate_graph, node_map, output


class StaleGraphViewError(ValueError):
    """The manager packet was built from an obsolete structural graph view."""


def _scope_set(values: list[str] | None) -> set[str] | None:
    if values is None:
        return None
    return {value for value in values if isinstance(value, str) and value.strip()}


def _overlap(left: set[str] | None, right: set[str] | None) -> bool:
    # Unknown scope is never evidence of safety when two claims could overlap.
    return left is None or right is None or bool(left & right)


def impl_graph_claim(
    graph_id: str,
    node_ids: list[str],
    claim_id: str,
    worker: str | None = None,
    changed_files: list[str] | None = None,
    write_scopes: list[str] | None = None,
    manager_session: str | None = None,
    expected_structure_revision: int | None = None,
    expected_structure_digest: str | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    if not isinstance(node_ids, list) or not node_ids or len(set(node_ids)) != len(node_ids):
        return {"error": "invalid_claim", "message": "node_ids must be a non-empty unique array"}
    if not isinstance(claim_id, str) or not claim_id.strip():
        return {"error": "invalid_claim", "message": "claim_id is required"}
    if not isinstance(manager_session, str) or not manager_session.strip():
        return {"error": "invalid_claim", "message": "manager_session is required"}
    if not isinstance(write_scopes, list) or not write_scopes or any(not isinstance(scope, str) or not scope.strip() for scope in write_scopes):
        return {"error": "invalid_claim", "message": "write_scopes are required and must be non-empty strings"}
    requested_scope = _scope_set(write_scopes)
    try:
        def apply(graph):
            if expected_structure_revision is not None and graph.get("structure_revision") != expected_structure_revision:
                raise StaleGraphViewError(
                    f"stale_graph_view: expected structure_revision {expected_structure_revision}, "
                    f"current is {graph.get('structure_revision')}"
                )
            if expected_structure_digest is not None and graph_structure_digest(graph) != expected_structure_digest:
                raise StaleGraphViewError("stale_graph_view: expected structure digest does not match current graph")
            nodes = node_map(graph)
            ready = {node["id"] for node in derived_ready(graph)}
            for node_id in node_ids:
                node = nodes.get(node_id)
                if node is None:
                    raise ValueError(f"unknown node: {node_id}")
                if node_id not in ready:
                    raise ValueError(f"node is not ready: {node_id}")
                if node.get("claim") is not None:
                    raise ValueError(f"node already claimed: {node_id}")

            # write_scopes describe the one worker packet, not each node in it.
            # Nodes in one packet are intentionally allowed to share the packet scope.
            seen_claims: set[str] = set()
            for node in nodes.values():
                claim = node.get("claim")
                if node.get("status") != "ACTIVE" or not isinstance(claim, dict):
                    continue
                existing_id = claim.get("id")
                if existing_id in seen_claims:
                    continue
                seen_claims.add(existing_id)
                active_scope = _scope_set(claim.get("write_scopes"))
                if _overlap(requested_scope, active_scope):
                    raise ValueError(f"known or unknown write overlap with active claim: {existing_id}")

            for node_id in node_ids:
                node = nodes[node_id]
                node["status"] = "ACTIVE"
                node["claim"] = {
                    "id": claim_id,
                    "worker": worker,
                    "manager_session": manager_session,
                    "write_scopes": sorted(requested_scope),
                    "changed_files": sorted(_scope_set(changed_files) or set()),
                }

        graph, _, _ = mutate_graph(workspace_root, graph_id, apply)
        return output({"graph_id": graph_id, "claim_id": claim_id, "claimed": node_ids, "state_revision": graph["state_revision"]}, "Claim Implementation Nodes")
    except StaleGraphViewError as exc:
        return {"error": "stale_graph_view", "message": str(exc)}
    except (ValueError, OSError) as exc:
        return {"error": "claim_failed", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_claim(
        args["graph_id"], args["node_ids"], args["claim_id"], args.get("worker"),
        args.get("changed_files"), args.get("write_scopes"), args.get("manager_session"),
        args.get("expected_structure_revision"), args.get("expected_structure_digest"), workspace_root=Path(args["workspace_root"]),
    )))
