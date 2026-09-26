"""Shared atomic mutation logic for the Change DAG tool surface.

Every mutating function follows the same discipline:

* read the DAG and Execution State;
* reject edits while the DAG is actively executing (running immutability);
* build the candidate in memory and validate it with :func:`change_dag.validate_dag`;
* persist atomically only after the candidate is valid.

Node IDs are never reused. The immutable work log is never rewritten here.
This module is the single owner of the graph mechanics the agent-facing tools
expose: canonical ID allocation, reference rewiring, reachability repair, and
reachability garbage collection.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from . import change_dag
from . import change_dag_compiler
from . import change_dag_control
from . import change_dag_policy
from . import change_dag_state

WORK_KINDS = ("create", "edit", "remove", "move", "run")

_ALLOWED_UPDATE_FIELDS: dict[str, set[str]] = {
    change_dag.SEMANTIC_TYPE: {"requirement"},
    "create": {"path", "content"},
    "edit": {"path", "patch"},
    "remove": {"path"},
    "move": {"from_path", "to_path"},
    "run": {"command", "exclusive"},
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {"error": code, "message": message}
    payload.update(extra)
    return payload


def _numeric(node_id: str) -> int:
    return change_dag._numeric_id(node_id)


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


def _load(workspace_root: Path, slug: str) -> tuple[dict[str, Any] | None, dict[str, str] | None, str | None, dict[str, Any] | None]:
    try:
        dag, _path, location = change_dag.read_dag(workspace_root, slug)
    except FileNotFoundError as exc:
        return None, None, None, _error("dag_not_found", str(exc))
    except ValueError as exc:
        return None, None, None, _error("dag_read_failed", str(exc))
    try:
        state = change_dag_state.read_state(workspace_root, slug, completed=(location == "completed"))
    except ValueError as exc:
        return None, None, None, _error("state_read_failed", str(exc))
    return dag, state, location, None


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


def _reachable_subgraph(dag: dict[str, Any], node_id: str) -> set[str]:
    found: set[str] = set()
    stack = list(change_dag.direct_children(dag, node_id))
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(change_dag.direct_children(dag, current))
    return found


def _persist(dag: dict[str, Any], workspace_root: Path, slug: str) -> None:
    change_dag.atomic_write_json(change_dag.dag_json_path(workspace_root, slug), dag)


# ---------------------------------------------------------------------------
# Semantic graph validation for creation (handle-space, before any allocation)
# ---------------------------------------------------------------------------
def _handle_cycle(root: str, nodes: dict[str, Any]) -> list[str] | None:
    color: dict[str, int] = {}
    path: list[str] = []

    def visit(handle: str) -> list[str] | None:
        color[handle] = 1
        path.append(handle)
        node = nodes.get(handle)
        refs = node.get("satisfied_by") if isinstance(node, dict) else None
        if isinstance(refs, list):
            for child in refs:
                if not isinstance(child, str) or child not in nodes:
                    continue
                state = color.get(child, 0)
                if state == 1:
                    return path[path.index(child):] + [child]
                if state == 0:
                    found = visit(child)
                    if found is not None:
                        return found
        color[handle] = 2
        path.pop()
        return None

    return visit(root)


def _bfs_order(root: str, nodes: dict[str, Any]) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()
    queue = [root]
    while queue:
        handle = queue.pop(0)
        if handle in seen or handle not in nodes:
            continue
        seen.add(handle)
        order.append(handle)
        node = nodes[handle]
        refs = node.get("satisfied_by") if isinstance(node, dict) else None
        if isinstance(refs, list):
            for child in sorted(ref for ref in refs if isinstance(ref, str)):
                if child not in seen:
                    queue.append(child)
    return order


def _validate_semantic_graph(semantic_graph: Any) -> tuple[list[str], list[str]]:
    if not isinstance(semantic_graph, dict):
        return ["semantic_graph must be an object"], []
    root = semantic_graph.get("root")
    nodes = semantic_graph.get("nodes")
    errors: list[str] = []
    if not isinstance(root, str) or not root:
        errors.append("root must be a non-empty handle")
    if not isinstance(nodes, dict) or not nodes:
        errors.append("nodes must be a non-empty object")
    if errors:
        return errors, []

    for handle, node in nodes.items():
        if not isinstance(handle, str) or not handle:
            errors.append(f"invalid handle: {handle!r}")
            continue
        if not isinstance(node, dict):
            errors.append(f"node {handle} must be an object")
            continue
        requirement = node.get("requirement")
        if not isinstance(requirement, str) or not requirement:
            errors.append(f"node {handle} requirement must be a non-empty string")
        for extra in sorted(set(node) - {"requirement", "satisfied_by"}):
            errors.append(f"node {handle} has unexpected field: {extra}")
        refs = node.get("satisfied_by")
        if refs is not None:
            if not isinstance(refs, list) or not refs:
                errors.append(f"node {handle} satisfied_by must be a non-empty array")
            else:
                for ref in refs:
                    if not isinstance(ref, str) or not ref:
                        errors.append(f"node {handle} satisfied_by entries must be non-empty strings")
                    elif ref not in nodes:
                        errors.append(f"node {handle} satisfied_by references missing handle: {ref}")
                if len(set(refs)) != len(refs):
                    errors.append(f"node {handle} satisfied_by entries must be unique")
    if errors:
        return errors, []
    assert isinstance(root, str)

    if root not in nodes:
        errors.append(f"root handle does not resolve: {root!r}")
        return errors, []

    reachable = set(_bfs_order(root, nodes))
    for handle in nodes:
        if handle not in reachable:
            errors.append(f"node {handle} is not reachable from root")
    if errors:
        return errors, []

    cycle = _handle_cycle(root, nodes)
    if cycle is not None:
        errors.append(f"satisfied_by path returns to an ancestor (cycle): {' -> '.join(cycle)}")
        return errors, []

    return [], _bfs_order(root, nodes)


# ---------------------------------------------------------------------------
# Public mutation surface
# ---------------------------------------------------------------------------
def create_dag(workspace_root: Path, slug: str, semantic_graph: Any) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    try:
        change_dag.bundle_dir(workspace_root, slug)
    except ValueError as exc:
        return _error("invalid_slug", str(exc))
    if (
        change_dag.dag_json_path(workspace_root, slug).exists()
        or change_dag.dag_json_path(workspace_root, slug, True).exists()
    ):
        return _error("already_exists", f"change dag already exists: {slug}")

    errors, order = _validate_semantic_graph(semantic_graph)
    if errors:
        return _error("invalid_semantic_graph", "; ".join(errors), errors=errors)

    nodes = semantic_graph["nodes"]
    root_handle = semantic_graph["root"]
    anchor = change_dag.resolve_anchor_commit(workspace_root)
    handles: dict[str, str] = {}
    ordering_dag: dict[str, Any] = {"slug": slug, "anchor_commit": anchor, "root": "", "nodes": {}}
    for handle in order:
        node_id = change_dag.allocate_node_id(ordering_dag, workspace_root, slug)
        handles[handle] = node_id
        ordering_dag["nodes"][node_id] = {"type": change_dag.SEMANTIC_TYPE}

    built: dict[str, Any] = {}
    for handle in order:
        node = nodes[handle]
        entry: dict[str, Any] = {"type": change_dag.SEMANTIC_TYPE, "requirement": node["requirement"]}
        refs = node.get("satisfied_by")
        if refs:
            entry["satisfied_by"] = [handles[ref] for ref in refs]
        built[handles[handle]] = entry

    dag = {"slug": slug, "anchor_commit": anchor, "root": handles[root_handle], "nodes": built}
    dag_errors = change_dag.validate_dag(dag)
    if dag_errors:
        return _error("invalid_dag", "; ".join(dag_errors), errors=dag_errors)

    _persist(dag, workspace_root, slug)
    change_dag_state.write_state(workspace_root, slug, {})
    work_log = change_dag.work_log_path(workspace_root, slug)
    work_log.parent.mkdir(parents=True, exist_ok=True)
    if not work_log.exists():
        work_log.write_text("", encoding="utf-8")

    return change_dag.output(
        {
            "slug": slug,
            "anchor_commit": anchor,
            "root_node_id": handles[root_handle],
            "node_ids_by_handle": handles,
        },
        "Create Change DAG",
    )


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
    if kind == "create":
        node["path"] = fields.get("path")
        node["content"] = fields.get("content")
    elif kind == "edit":
        node["path"] = fields.get("path")
        node["patch"] = fields.get("patch")
    elif kind == "remove":
        node["path"] = fields.get("path")
    elif kind == "move":
        node["from_path"] = fields.get("from_path")
        node["to_path"] = fields.get("to_path")
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


# ---------------------------------------------------------------------------
# Read-only surface
# ---------------------------------------------------------------------------
def preview(workspace_root: Path, slug: str, path: str | None = None, node_id: str | None = None) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    dag, state, _location, err = _load(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None and state is not None
    if path is not None and node_id is not None:
        return _error("invalid_scope", "use at most one of path or node_id")

    ops, conflicts, blocked = change_dag_compiler.compile_operations(dag, state, workspace_root)
    pre = change_dag_compiler.preflight(dag, state, workspace_root)
    ready = change_dag_compiler.ready_run_nodes(dag, state, workspace_root)
    depths = change_dag.derived_depth(dag)

    if node_id is not None:
        if node_id not in change_dag.node_map(dag):
            return _error("unknown_node", f"node not found: {node_id}")
        subgraph = _reachable_subgraph(dag, node_id) | {node_id}
        ops = [op for op in ops if set(op.nodes) & subgraph]
        conflicts = [conflict for conflict in conflicts if set(conflict.nodes) & subgraph]
        blocked = [entry for entry in blocked if entry.node_id in subgraph]
    elif path is not None:
        ops = [op for op in ops if op.path == path]
        conflicts = [conflict for conflict in conflicts if conflict.path == path]
        blocked = []

    payload = {
        "slug": slug,
        "ops": [
            {
                "nodes": list(op.nodes),
                "op": op.op,
                "path": op.path,
                "from_path": op.from_path,
                "to_path": op.to_path,
                **({"content": op.content} if op.content is not None else {}),
            }
            for op in ops
        ],
        "conflicts": [
            {"path": conflict.path, "nodes": list(conflict.nodes), "reason": conflict.reason}
            for conflict in conflicts
        ],
        "blocked": [{"node_id": entry.node_id, "reason": entry.reason} for entry in blocked],
        "run_barriers": ready,
        "depths": depths,
        "executable": pre["executable"],
        "issues": pre["issues"],
    }
    return change_dag.output(payload, "Preview Change DAG", {"slug": slug})


def validate(workspace_root: Path, slug: str) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    dag, state, _location, err = _load(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None and state is not None

    schema = change_dag.schema_errors(dag)
    structure = change_dag.structure_errors(dag)
    pre = change_dag_compiler.preflight(dag, state, workspace_root)
    issues: list[dict[str, Any]] = [{"kind": "schema", "message": message} for message in schema]
    issues.extend({"kind": "structure", "message": message} for message in structure)
    for issue in pre.get("issues", []):
        if issue.get("kind") == "structure":
            continue
        issues.append(issue)

    payload = {
        "slug": slug,
        "schema_valid": not schema,
        "executable": pre["executable"],
        "resolved": change_dag.is_resolved(dag),
        "issues": issues,
    }
    return change_dag.output(payload, "Validate Change DAG", {"slug": slug})


def show(
    workspace_root: Path,
    slug: str,
    node_id: str | None = None,
    include_ancestors: bool = False,
    include_descendants: bool = False,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    dag, _state, _location, err = _load(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None

    nodes = change_dag.node_map(dag)
    depths = change_dag.derived_depth(dag)
    selected = set(nodes)
    if node_id is not None:
        if node_id not in nodes:
            return _error("unknown_node", f"node not found: {node_id}")
        selected = {node_id}
        if include_ancestors:
            selected |= change_dag.ancestor_map(dag).get(node_id, set())
        if include_descendants:
            selected |= _reachable_subgraph(dag, node_id)

    ordered = sorted(selected, key=_numeric)

    def view(entry_id: str) -> dict[str, Any]:
        node = nodes[entry_id]
        rendered = {"id": entry_id, "type": node.get("type")}
        for key, value in node.items():
            if key != "type":
                rendered[key] = value
        if entry_id in depths:
            rendered["depth"] = depths[entry_id]
        return rendered

    payload = {
        "slug": slug,
        "root": dag.get("root"),
        "anchor_commit": dag.get("anchor_commit"),
        "nodes": [view(entry_id) for entry_id in ordered],
    }
    return change_dag.output(payload, "Show Change DAG", {"slug": slug})
