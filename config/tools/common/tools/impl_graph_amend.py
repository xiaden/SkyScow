"""Apply bounded planner amendments to a pending implementation graph."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.implementation_graph import mutate_graph, node_map, output, validate_graph

_NODE_PATCH_FIELDS = frozenset({
    "title", "obligation", "depends_on", "satisfies", "acceptance",
    "consumes", "produces", "context_hints",
})
_CONTRACT_PATCH_FIELDS = frozenset({
    "description", "producer", "consumers", "external_source", "actual",
})


def _require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _add_unique(values: list[Any], value: Any, label: str) -> None:
    if value in values:
        raise ValueError(f"{label} already exists: {value}")
    values.append(value)


def _apply_operation(graph: dict[str, Any], operation: dict[str, Any], affected: set[str]) -> None:
    if not isinstance(operation, dict):
        raise ValueError("each amendment operation must be an object")
    op = _require_id(operation.get("op"), "operation op")
    nodes = node_map(graph)
    contracts = {item["id"]: item for item in graph["contracts"]}
    requirements = {item["id"]: item for item in graph["requirements"]}

    if op == "add_node":
        node = operation.get("node")
        if not isinstance(node, dict):
            raise ValueError("add_node requires node")
        node = dict(node)
        node_id = _require_id(node.get("id"), "node id")
        if node_id in nodes:
            raise ValueError(f"node already exists: {node_id}")
        node.update({
            "status": "PENDING", "depends_on": [], "satisfies": [],
            "acceptance": [], "consumes": [], "produces": [],
            "context_hints": {}, "claim": None, "evidence": [],
            "provenance": [], "blocker": None, "changed_files": [], "deviations": [],
        })
        if not isinstance(node.get("obligation"), str) or not node["obligation"].strip():
            raise ValueError("add_node requires a non-empty obligation")
        graph["nodes"].append(node)
        affected.add(node_id)
        return

    if op in {"update_pending_node", "remove_pending_node", "add_dependency", "remove_dependency", "map_requirement", "unmap_requirement"}:
        node_id = _require_id(operation.get("node_id"), "node_id")
        node = nodes.get(node_id)
        if node is None:
            raise ValueError(f"unknown node: {node_id}")
        if node.get("status") != "PENDING":
            raise ValueError(f"only pending nodes may be amended: {node_id}")
        affected.add(node_id)

        if op == "update_pending_node":
            patch = operation.get("patch")
            if not isinstance(patch, dict) or not patch:
                raise ValueError("update_pending_node requires a non-empty patch")
            unknown = set(patch) - _NODE_PATCH_FIELDS
            if unknown:
                raise ValueError(f"unsupported node patch fields: {sorted(unknown)}")
            node.update(patch)
            return
        if op == "remove_pending_node":
            if any(node_id in other.get("depends_on", []) for other in nodes.values() if other["id"] != node_id):
                raise ValueError(f"cannot remove node with dependents: {node_id}")
            graph["nodes"] = [item for item in graph["nodes"] if item["id"] != node_id]
            return
        if op in {"add_dependency", "remove_dependency"}:
            dependency = _require_id(operation.get("depends_on"), "depends_on")
            if dependency not in nodes:
                raise ValueError(f"unknown dependency: {dependency}")
            deps = node.setdefault("depends_on", [])
            if op == "add_dependency":
                _add_unique(deps, dependency, "dependency")
            elif dependency not in deps:
                raise ValueError(f"dependency does not exist: {dependency}")
            else:
                deps.remove(dependency)
            affected.add(dependency)
            return
        requirement_id = _require_id(operation.get("requirement_id"), "requirement_id")
        if requirement_id not in requirements:
            raise ValueError(f"unknown requirement: {requirement_id}")
        satisfies = node.setdefault("satisfies", [])
        if op == "map_requirement":
            _add_unique(satisfies, requirement_id, "requirement mapping")
        elif requirement_id not in satisfies:
            raise ValueError(f"requirement is not mapped: {requirement_id}")
        else:
            satisfies.remove(requirement_id)
        return

    if op in {"add_contract", "update_contract", "remove_unused_contract"}:
        if op == "add_contract":
            contract = operation.get("contract")
            if not isinstance(contract, dict):
                raise ValueError("add_contract requires contract")
            contract = dict(contract)
            contract_id = _require_id(contract.get("id"), "contract id")
            if contract_id in contracts:
                raise ValueError(f"contract already exists: {contract_id}")
            graph["contracts"].append(contract)
            affected.add(contract_id)
            return
        contract_id = _require_id(operation.get("contract_id"), "contract_id")
        contract = contracts.get(contract_id)
        if contract is None:
            raise ValueError(f"unknown contract: {contract_id}")
        affected.add(contract_id)
        if op == "update_contract":
            patch = operation.get("patch")
            if not isinstance(patch, dict) or not patch:
                raise ValueError("update_contract requires a non-empty patch")
            unknown = set(patch) - _CONTRACT_PATCH_FIELDS
            if unknown:
                raise ValueError(f"unsupported contract patch fields: {sorted(unknown)}")
            if "actual" in patch and "actual" in contract and contract["actual"] != patch["actual"]:
                raise ValueError("cannot rewrite materialized contract")
            contract.update(patch)
            return
        if any(contract_id in node.get("consumes", []) or contract_id in node.get("produces", []) for node in nodes.values()):
            raise ValueError(f"cannot remove used contract: {contract_id}")
        graph["contracts"] = [item for item in graph["contracts"] if item["id"] != contract_id]
        return

    raise ValueError(f"unsupported amendment operation: {op}")


def impl_graph_amend(
    graph_id: str,
    operations: list[dict[str, Any]] | None = None,
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
    bounded = list(operations or [])
    # Keep the original add/remove arguments as narrow compatibility aliases.
    bounded.extend({"op": "add_node", "node": node} for node in (nodes or []))
    bounded.extend({"op": "remove_pending_node", "node_id": node_id} for node_id in (remove_node_ids or []))
    if not bounded:
        return {"error": "invalid_amendment", "message": "operations are required"}
    try:
        def apply(graph):
            if any(node.get("status") == "ACTIVE" for node in node_map(graph).values()):
                raise ValueError("cannot amend while active claims exist")
            affected: set[str] = set()
            for operation in bounded:
                _apply_operation(graph, operation, affected)
            graph.setdefault("amendments", []).append({
                "actor": actor.strip(), "reason": reason.strip(),
                "operations": bounded, "affected_ids": sorted(affected),
            })

        graph, _, _ = mutate_graph(workspace_root, graph_id, apply, structural_change=True)
        errors = validate_graph(graph, workspace_root)
        if errors:
            return {"error": "invalid_amendment", "message": "; ".join(errors[:8]), "errors": errors}
        return output({
            "graph_id": graph_id,
            "structure_revision": graph["structure_revision"],
            "state_revision": graph["state_revision"],
            "amended": True,
        }, "Amend Implementation Graph")
    except (ValueError, OSError) as exc:
        return {"error": "amend_failed", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_amend(
        graph_id=args["graph_id"], operations=args.get("operations"), nodes=args.get("nodes"),
        remove_node_ids=args.get("remove_node_ids"), requirements=args.get("requirements"),
        contracts=args.get("contracts"), actor=args.get("actor"), reason=args.get("reason"),
        workspace_root=Path(args["workspace_root"]),
    )))
