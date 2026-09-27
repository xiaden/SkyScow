"""Mutation of an existing persisted Change DAG.

Every mutating function follows the same discipline:

* read the DAG and Execution State;
* reject edits while the DAG is actively executing (running immutability);
* build the candidate in memory and validate it with :func:`change_dag.validate_dag`;
* persist atomically only after the candidate is valid.

Node IDs are never reused. The immutable work log is never rewritten here.
This module is the single owner of the graph mechanics the agent-facing tools
expose: canonical ID allocation, reference rewiring, reachability repair, and
reachability garbage collection. These functions share the same invariants
(pending DAG only, candidate-before-persist, canonical path identity,
state-dependent mutability, coordinated rewiring/GC) and are intentionally kept
as one cohesive reasoning unit.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from . import change_dag
from . import change_dag_control
from . import change_dag_policy
from .change_dag_ops_support import _error, _load, _locked_mutation, _numeric, _persist

WORK_KINDS = ("create", "edit", "remove", "move", "run")

_ALLOWED_UPDATE_FIELDS: dict[str, set[str]] = {
    change_dag.SEMANTIC_TYPE: {"requirement"},
    "create": {"path", "content"},
    "edit": {"path", "patch"},
    "remove": {"path"},
    "move": {"from_path", "to_path", "overwrite"},
    "run": {"command", "exclusive"},
}


def _canonical_path_field(raw: Any, field: str) -> Any:
    """Canonicalize a DAG path field, or return an ``invalid_path`` error payload.

    The DAG stores one canonical workspace-relative spelling per file so that
    path-coordinated compilation never sees two identities for one target.
    """
    try:
        return change_dag.canonical_path(raw)
    except ValueError as exc:
        return _error("invalid_path", f"{field}: {exc}")


def _bool_field(raw: Any, field: str) -> Any:
    """Return a strict boolean field value, or an ``invalid_field`` payload."""
    if raw is None:
        return False
    if not isinstance(raw, bool):
        return _error("invalid_field", f"{field} must be a boolean")
    return raw


def _peek_next_id(dag: dict[str, Any], workspace_root: Path, slug: str) -> str:
    """Return the ID the next allocation would produce, without persisting it."""
    current_max = 0
    for node_id in change_dag.node_map(dag):
        match = change_dag.NODE_ID_PATTERN.match(node_id)
        if match:
            current_max = max(current_max, int(node_id[1:]))
    seq_path = change_dag.bundle_dir(workspace_root, slug) / change_dag.NODE_SEQ_FILENAME
    try:
        persisted = int(seq_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        persisted = 0
    return f"N{max(current_max, persisted) + 1}"


def _running_error(workspace_root: Path, slug: str) -> dict[str, Any] | None:
    try:
        active = change_dag_control.active_dag(workspace_root)
    except Exception:  # pragma: no cover - defensive; control reads must never crash edits
        active = None
    if active == slug:
        return _error(
            "dag_running_immutable",
            f"change dag {slug!r} is currently executing and is immutable; "
            "call dag_stop or let execution fail before editing it",
        )
    return None


def _mutation_context(workspace_root: Path, slug: str) -> tuple[dict[str, Any] | None, dict[str, str] | None, dict[str, Any] | None]:
    dag, state, location, err = _load(workspace_root, slug)
    if err is not None:
        return None, None, err
    assert dag is not None and state is not None and location is not None
    if location != "pending":
        return None, None, _error(
            "dag_not_pending",
            f"change dag {slug!r} is archived in completed/ and is immutable",
        )
    running = _running_error(workspace_root, slug)
    if running is not None:
        return None, None, running
    return dag, state, None


def _id_list(value: Any, field: str) -> list[str] | dict[str, Any]:
    if not isinstance(value, list) or not value:
        return _error("invalid_arguments", f"{field} must be a non-empty array of node IDs")
    result: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry:
            return _error("invalid_arguments", f"{field} entries must be non-empty strings")
        result.append(entry)
    return result


@_locked_mutation
def add_requirement(
    workspace_root: Path,
    slug: str,
    requirement: Any,
    parent_ids: Any,
    child_ids: Any = None,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    dag, _state, err = _mutation_context(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None

    if not isinstance(requirement, str) or not requirement:
        return _error("invalid_requirement", "requirement must be a non-empty string")

    parents = _id_list(parent_ids, "parent_ids")
    if isinstance(parents, dict):
        return parents
    nodes = change_dag.node_map(dag)
    for parent in parents:
        if parent not in nodes:
            return _error("unknown_node", f"parent not found: {parent}")
        if change_dag.node_type(dag, parent) != change_dag.SEMANTIC_TYPE:
            return _error("invalid_parent", f"parent is not semantic: {parent}")

    selected: list[str] | None = None
    if child_ids is not None:
        selected = _id_list(child_ids, "child_ids")
        if isinstance(selected, dict):
            return selected
        union: set[str] = set()
        for parent in parents:
            union.update(change_dag.direct_children(dag, parent))
        for child in selected:
            if child not in nodes:
                return _error("unknown_node", f"child not found: {child}")
            if child not in union:
                return _error(
                    "invalid_child",
                    f"child {child} is not a current direct child of a supplied parent",
                )

    new_id = _peek_next_id(dag, workspace_root, slug)
    candidate = copy.deepcopy(dag)
    candidate_nodes = candidate["nodes"]
    if selected is None:
        candidate_nodes[new_id] = {"type": change_dag.SEMANTIC_TYPE, "requirement": requirement}
        for parent in parents:
            refs = list(candidate_nodes[parent].get("satisfied_by", []))
            if new_id not in refs:
                refs.append(new_id)
            candidate_nodes[parent]["satisfied_by"] = refs
    else:
        candidate_nodes[new_id] = {
            "type": change_dag.SEMANTIC_TYPE,
            "requirement": requirement,
            "satisfied_by": list(selected),
        }
        chosen = set(selected)
        for parent in parents:
            rewired: list[str] = []
            for ref in candidate_nodes[parent].get("satisfied_by", []):
                if ref in chosen:
                    if new_id not in rewired:
                        rewired.append(new_id)
                else:
                    rewired.append(ref)
            if rewired:
                candidate_nodes[parent]["satisfied_by"] = rewired

    errors = change_dag.validate_dag(candidate)
    if errors:
        return _error("invalid_graph", "; ".join(errors), errors=errors)

    real_id = change_dag.allocate_node_id(dag, workspace_root, slug)
    if real_id != new_id:
        candidate_nodes[real_id] = candidate_nodes.pop(new_id)
        for node in candidate_nodes.values():
            refs = node.get("satisfied_by")
            if isinstance(refs, list) and new_id in refs:
                node["satisfied_by"] = [real_id if ref == new_id else ref for ref in refs]
        if candidate.get("root") == new_id:
            candidate["root"] = real_id
    _persist(candidate, workspace_root, slug)
    return change_dag.output(
        {
            "slug": slug,
            "node_id": real_id,
            "requirement": requirement,
            "parents": parents,
            "children": selected or [],
        },
        "Add Requirement",
        {"slug": slug, "node_id": real_id},
    )


@_locked_mutation
def add_work(workspace_root: Path, slug: str, kind: str, parent_ids: Any, **fields: Any) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    if kind not in WORK_KINDS:
        return _error("invalid_kind", f"kind must be one of {', '.join(WORK_KINDS)}")
    dag, _state, err = _mutation_context(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None

    parents = _id_list(parent_ids, "parent_ids")
    if isinstance(parents, dict):
        return parents
    nodes = change_dag.node_map(dag)
    for parent in parents:
        if parent not in nodes:
            return _error("unknown_node", f"parent not found: {parent}")
        if change_dag.node_type(dag, parent) != change_dag.SEMANTIC_TYPE:
            return _error("invalid_parent", f"parent is not semantic: {parent}")

    node: dict[str, Any] = {"type": kind}
    if kind in ("create", "edit", "remove"):
        path = _canonical_path_field(fields.get("path"), "path")
        if isinstance(path, dict):
            return path
        node["path"] = path
        if kind == "create":
            node["content"] = fields.get("content")
        elif kind == "edit":
            node["patch"] = fields.get("patch")
    elif kind == "move":
        from_path = _canonical_path_field(fields.get("from_path"), "from_path")
        if isinstance(from_path, dict):
            return from_path
        to_path = _canonical_path_field(fields.get("to_path"), "to_path")
        if isinstance(to_path, dict):
            return to_path
        node["from_path"] = from_path
        node["to_path"] = to_path
        overwrite = _bool_field(fields.get("overwrite"), "overwrite")
        if isinstance(overwrite, dict):
            return overwrite
        node["overwrite"] = overwrite
    elif kind == "run":
        command = fields.get("command")
        allowed, reason = change_dag_policy.validate_run_command(command)
        if not allowed:
            return _error("run_command_rejected", reason)
        node["command"] = list(command)
        node["exclusive"] = bool(fields.get("exclusive", False))

    new_id = _peek_next_id(dag, workspace_root, slug)
    candidate = copy.deepcopy(dag)
    candidate_nodes = candidate["nodes"]
    candidate_nodes[new_id] = node
    for parent in parents:
        refs = list(candidate_nodes[parent].get("satisfied_by", []))
        if new_id not in refs:
            refs.append(new_id)
        candidate_nodes[parent]["satisfied_by"] = refs

    errors = change_dag.validate_dag(candidate)
    if errors:
        return _error("invalid_graph", "; ".join(errors), errors=errors)

    real_id = change_dag.allocate_node_id(dag, workspace_root, slug)
    if real_id != new_id:
        candidate_nodes[real_id] = candidate_nodes.pop(new_id)
        for entry in candidate_nodes.values():
            refs = entry.get("satisfied_by")
            if isinstance(refs, list) and new_id in refs:
                entry["satisfied_by"] = [real_id if ref == new_id else ref for ref in refs]
    _persist(candidate, workspace_root, slug)
    return change_dag.output(
        {"slug": slug, "node_id": real_id, "kind": kind, "parents": parents},
        "Add Work",
        {"slug": slug, "node_id": real_id, "kind": kind},
    )


@_locked_mutation
def update_node(workspace_root: Path, slug: str, node_id: str, **fields: Any) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    dag, state, err = _mutation_context(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None and state is not None

    nodes = change_dag.node_map(dag)
    if node_id not in nodes:
        return _error("unknown_node", f"node not found: {node_id}")
    kind = change_dag.node_type(dag, node_id)
    if kind is None:
        return _error("unknown_node", f"node has no type: {node_id}")

    mutable, reason = change_dag.mutability(dag, state, node_id)
    if not mutable:
        return _error("immutable_node", f"node {node_id} is not mutable: {reason}")

    allowed = _ALLOWED_UPDATE_FIELDS.get(kind, set())
    provided = {key: value for key, value in fields.items() if value is not None}
    if not provided:
        return _error("invalid_arguments", "at least one field must be supplied")
    for key in provided:
        if key not in allowed:
            return _error("invalid_field", f"field {key!r} is not valid for {kind} node")

    if kind == "run" and "command" in provided:
        command_allowed, command_reason = change_dag_policy.validate_run_command(provided["command"])
        if not command_allowed:
            return _error("run_command_rejected", command_reason)

    for field in change_dag.node_path_fields(kind):
        if field in provided:
            canonical = _canonical_path_field(provided[field], field)
            if isinstance(canonical, dict):
                return canonical
            provided[field] = canonical

    if "overwrite" in provided:
        overwrite = _bool_field(provided["overwrite"], "overwrite")
        if isinstance(overwrite, dict):
            return overwrite
        provided["overwrite"] = overwrite

    candidate = copy.deepcopy(dag)
    candidate["nodes"][node_id].update(provided)
    errors = change_dag.validate_dag(candidate)
    if errors:
        return _error("invalid_graph", "; ".join(errors), errors=errors)

    _persist(candidate, workspace_root, slug)
    return change_dag.output(
        {"slug": slug, "node_id": node_id, "node": candidate["nodes"][node_id]},
        "Update Node",
        {"slug": slug, "node_id": node_id},
    )


@_locked_mutation
def remove_node(workspace_root: Path, slug: str, node_id: str) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    dag, state, err = _mutation_context(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None and state is not None

    if node_id == dag.get("root"):
        return _error("root_immutable", "the root node cannot be removed")
    nodes = change_dag.node_map(dag)
    if node_id not in nodes:
        return _error("unknown_node", f"node not found: {node_id}")

    mutable, reason = change_dag.mutability(dag, state, node_id)
    if not mutable:
        return _error("immutable_node", f"node {node_id} is not mutable: {reason}")

    candidate = copy.deepcopy(dag)
    del candidate["nodes"][node_id]
    for node in candidate["nodes"].values():
        if node.get("type") != change_dag.SEMANTIC_TYPE:
            continue
        refs = node.get("satisfied_by")
        if not isinstance(refs, list):
            continue
        filtered = [ref for ref in refs if ref != node_id]
        if filtered:
            node["satisfied_by"] = filtered
        else:
            node.pop("satisfied_by", None)

    reachable = change_dag.reachable_from_root(candidate)
    stranded = sorted(
        (candidate_id for candidate_id in candidate["nodes"] if candidate_id not in reachable),
        key=_numeric,
    )
    for stranded_id in stranded:
        stranded_mutable, _ = change_dag.mutability(candidate, state, stranded_id)
        if not stranded_mutable:
            return _error(
                "remove_would_orphan",
                f"removal would strand immutable work at {stranded_id}; no change written",
            )

    for stranded_id in stranded:
        del candidate["nodes"][stranded_id]

    errors = change_dag.validate_dag(candidate)
    if errors:
        return _error("invalid_graph", "; ".join(errors), errors=errors)

    _persist(candidate, workspace_root, slug)
    removed = [node_id] + stranded
    return change_dag.output(
        {"slug": slug, "removed": removed, "gc": stranded},
        "Remove Node",
        {"slug": slug, "node_id": node_id},
    )
