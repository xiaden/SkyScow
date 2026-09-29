"""Authorize the already-bound Fixer terminal mutation payload."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers import change_dag
from ..helpers.caller_identity import current_internal_metadata, set_caller_identity
from ..helpers.change_dag_ops_mutation import _semantic_owner, remove_node, update_node
from ..helpers.change_dag_ops_support import _error, _load


def dag_fixer_mutate(
    repair_ref: str,
    slug: str,
    semantic_node_id: str,
    operation: str,
    node_id: str,
    *,
    workspace_root: Path,
    **fields: Any,
) -> dict[str, Any]:
    internal = current_internal_metadata() or {}
    grant = internal.get("repair_grant")
    if not isinstance(grant, dict):
        return _error("unbound", "authorized repair grant is required")
    if grant.get("slug") != slug or grant.get("semantic_node_id") != semantic_node_id:
        return _error("scope_violation", "repair grant does not match this DAG boundary")
    allowed_nodes = grant.get("terminal_node_ids")
    allowed_paths = grant.get("paths")
    if not isinstance(allowed_nodes, list) or node_id not in allowed_nodes:
        return _error("scope_violation", "terminal node is outside grant")
    dag, _state, _location, error = _load(workspace_root, slug)
    if error is not None or dag is None:
        return error or _error("dag_not_found", "DAG not found")
    node = change_dag.node_map(dag).get(node_id)
    if not isinstance(node, dict) or node.get("type") not in change_dag.TERMINAL_TYPES:
        return _error("scope_violation", "Fixer may mutate existing terminal work only")
    owner = _semantic_owner(dag, node_id)
    if owner != semantic_node_id:
        return _error("scope_violation", "terminal node is outside semantic boundary")
    if operation == "remove":
        return remove_node(workspace_root, slug, node_id, allowed_node_ids=set(allowed_nodes))
    if operation != "update":
        return _error("scope_violation", "only terminal update/remove are allowed")
    provided = {key: value for key, value in fields.items() if value is not None}
    for key in ("path", "from_path", "to_path"):
        if key in provided and (not isinstance(allowed_paths, list) or provided[key] not in allowed_paths):
            return _error("scope_violation", f"{key} is outside grant")
    for key in change_dag.node_path_fields(str(node["type"])):
        if key in node and (not isinstance(allowed_paths, list) or node[key] not in allowed_paths):
            return _error("scope_violation", f"existing {key} is outside grant")
    return update_node(workspace_root, slug, node_id, **provided)


if __name__ == "__main__":
    args = json.loads(input())
    set_caller_identity(args)
    workspace_root = Path(args.pop("workspace_root"))
    args.pop("__skyscow_internal", None)
    print(json.dumps(dag_fixer_mutate(workspace_root=workspace_root, **args)))
