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
from .change_dag_patch import (
    PatchError,
    StructuredReplacementError,
    apply_patches,
    apply_structured_replacements,
    generate_unified_diff,
    parse_unified_diff,
)
from .change_dag_projection import projected_source

WORK_KINDS = ("create", "edit", "remove", "move", "run")

_ALLOWED_UPDATE_FIELDS: dict[str, set[str]] = {
    change_dag.SEMANTIC_TYPE: {"requirement"},
    "create": {"path", "content"},
    "edit": {"path", "replacements"},
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


def _projection(workspace_root: Path, slug: str, owner: str) -> tuple[Any, dict[str, Any] | None]:
    """Project the semantic owner's accepted base, or return an error payload."""
    source, error = projected_source(workspace_root, slug, owner)
    if source is None:
        return None, error or _error(
            "projection_failed", f"cannot project the accepted base for {owner}"
        )
    return source, None


def _base_content(source: Any, path: str) -> Any:
    """Accepted base content for ``path``.

    Returns the text (possibly empty), ``None`` when the path is absent from the
    accepted base, or a ``projection_failed`` payload when applicable lower work
    cannot be reproduced.
    """
    conflict = source.error(path)
    if conflict is not None:
        return conflict
    return source.content(path)


def _generated_edit_patch(base: str, source: str, replacements: Any, path: str) -> Any:
    """Generate one internal edit patch from structured replacements, or error.

    ``replacements`` apply to ``source`` -- the accepted base for a fresh edit,
    or the node's self-view for an update. The generated diff is always against
    ``base`` so a consolidated patch stays a single base-relative edit.
    """
    try:
        desired = apply_structured_replacements(source, replacements)
        return generate_unified_diff(base, desired, path)
    except StructuredReplacementError as exc:
        return _error(exc.code, exc.message)
    except PatchError as exc:
        return _error("edit_unrepresentable", str(exc))


def _producer_evidence(dag: dict[str, Any], source: Any, path: str) -> list[str]:
    """Terminal nodes that produce ``path`` but sit outside the accepted base.

    Diagnostic structure only. When a mutation fails because required base state
    is unavailable, the likeliest explanation is that another branch produces it,
    so naming those producer IDs lets a worker return a useful ``BLOCKED``
    result and lets the author spot a missing causal edge. Producer content is
    never exposed, and no dependency is added.
    """
    visible = set(source.lower_path_nodes.get(path, []))
    producers: list[str] = []
    for candidate, node in change_dag.node_map(dag).items():
        kind = node.get("type")
        if kind == "create" and node.get("path") == path:
            producers.append(candidate)
        elif kind == "move" and node.get("to_path") == path:
            producers.append(candidate)
    return sorted(
        (node_id for node_id in producers if node_id not in visible),
        key=change_dag._numeric_id,
    )


def _unavailable(code: str, message: str, dag: dict[str, Any], source: Any, path: str) -> dict[str, Any]:
    """An unavailable-base error, enriched with candidate producer IDs."""
    payload = _error(code, message)
    candidates = _producer_evidence(dag, source, path)
    if candidates:
        payload["candidate_producers"] = candidates
    return payload


def _validate_create(node: dict[str, Any], dag: dict[str, Any], source: Any) -> dict[str, Any] | None:
    """A create is authorable only when its target is absent from BASE."""
    path = node["path"]
    base = _base_content(source, path)
    if isinstance(base, dict):
        return base
    if base is not None:
        return _error(
            "create_target_exists",
            f"create target already exists in the accepted base: {path!r}",
        )
    return None


def _validate_remove(node: dict[str, Any], dag: dict[str, Any], source: Any) -> dict[str, Any] | None:
    """A remove is authorable only when its target is present in BASE."""
    path = node["path"]
    base = _base_content(source, path)
    if isinstance(base, dict):
        return base
    if base is None:
        return _unavailable(
            "remove_target_unavailable",
            f"remove target is absent from the accepted base: {path!r}",
            dag,
            source,
            path,
        )
    return None


def _validate_move(node: dict[str, Any], dag: dict[str, Any], source: Any) -> dict[str, Any] | None:
    """A move is authorable only when its whole resulting shape is.

    Source presence, destination non-production by accepted lower work, and
    destination collision under ``overwrite`` are all checked against BASE.
    """
    from_path = node["from_path"]
    to_path = node["to_path"]
    overwrite = bool(node.get("overwrite", False))
    source_text = _base_content(source, from_path)
    if isinstance(source_text, dict):
        return source_text
    if source_text is None:
        return _unavailable(
            "move_source_unavailable",
            f"move source is absent from the accepted base: {from_path!r}",
            dag,
            source,
            from_path,
        )
    destination = _base_content(source, to_path)
    if isinstance(destination, dict):
        return destination
    if to_path in source.overlay:
        return _error(
            "move_destination_conflict",
            f"move destination was produced by accepted lower DAG work: {to_path!r}",
        )
    if destination is not None and not overwrite:
        return _error(
            "move_destination_conflict",
            f"move destination already exists in the accepted base: {to_path!r}",
        )
    return None


def _validate_terminal(kind: str, node: dict[str, Any], dag: dict[str, Any], source: Any) -> dict[str, Any] | None:
    """Shared authorability check for create/remove/move (``edit`` uses a patch)."""
    if kind == "create":
        return _validate_create(node, dag, source)
    if kind == "remove":
        return _validate_remove(node, dag, source)
    if kind == "move":
        return _validate_move(node, dag, source)
    return None


def _self_view(base: str, existing: dict[str, Any], path: str) -> Any:
    """Replay an existing edit's persisted patch onto BASE, or return an error."""
    try:
        return apply_patches(base, parse_unified_diff(existing["patch"]), path=path)
    except PatchError as exc:
        return _error("edit_self_view_unavailable", str(exc))


def _resolve_edit_update(
    existing: dict[str, Any], provided: dict[str, Any], dag: dict[str, Any], source: Any
) -> tuple[str | None, dict[str, Any] | None]:
    """Resolve the resulting edit patch for an update, or return an error.

    Same-path replacements are interpreted against the node's SELF view (BASE
    plus this node's persisted edit) and consolidated into one BASE-relative
    patch, which preserves incremental authoring. Retargeting an edit to a
    different path is a fresh statement of intent: it requires replacements
    interpreted against the NEW path's BASE, and the old patch is never
    transplanted. Only one of the returned values is non-``None``.
    """
    old_path = existing.get("path")
    new_path = provided.get("path", old_path)
    replacements = provided.get("replacements")
    changed_path = new_path != old_path

    if changed_path and replacements is None:
        return None, _error(
            "edit_path_change_requires_replacements",
            "changing an edit node's path requires fresh structured replacements",
        )

    base = _base_content(source, new_path)
    if isinstance(base, dict):
        return None, base
    if base is None:
        return None, _unavailable(
            "edit_base_unavailable",
            f"no accepted base content for {new_path!r}",
            dag,
            source,
            new_path,
        )

    if changed_path:
        interpretation: Any = base
    else:
        if replacements is None:
            # Metadata-only update on the same path: keep the persisted patch.
            return existing.get("patch"), None
        interpretation = _self_view(base, existing, new_path)
        if isinstance(interpretation, dict):
            return None, interpretation

    generated = _generated_edit_patch(base, interpretation, replacements, new_path)
    if isinstance(generated, dict):
        return None, generated
    return generated, None


def _semantic_owner(dag: dict[str, Any], node_id: str) -> Any:
    """Return the single semantic parent of ``node_id``, or an error payload."""
    parents = [
        candidate
        for candidate, node in change_dag.node_map(dag).items()
        if node.get("type") == change_dag.SEMANTIC_TYPE
        and node_id in change_dag.direct_children(dag, candidate)
    ]
    if len(parents) != 1:
        return _error(
            "invalid_arguments",
            f"terminal node {node_id} must have exactly one semantic parent",
        )
    return parents[0]


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
            f"change dag {slug!r} is archived in {change_dag.ARCHIVED_DIR} and is immutable",
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
            refs = list(candidate_nodes[parent].get("requires", []))
            if new_id not in refs:
                refs.append(new_id)
            candidate_nodes[parent]["requires"] = refs
    else:
        candidate_nodes[new_id] = {
            "type": change_dag.SEMANTIC_TYPE,
            "requirement": requirement,
            "requires": list(selected),
        }
        chosen = set(selected)
        for parent in parents:
            rewired: list[str] = []
            for ref in candidate_nodes[parent].get("requires", []):
                if ref in chosen:
                    if new_id not in rewired:
                        rewired.append(new_id)
                else:
                    rewired.append(ref)
            if rewired:
                candidate_nodes[parent]["requires"] = rewired

    errors = change_dag.validate_dag(candidate)
    if errors:
        return _error("invalid_graph", "; ".join(errors), errors=errors)

    real_id = change_dag.allocate_node_id(dag, workspace_root, slug)
    if real_id != new_id:
        candidate_nodes[real_id] = candidate_nodes.pop(new_id)
        for node in candidate_nodes.values():
            refs = node.get("requires")
            if isinstance(refs, list) and new_id in refs:
                node["requires"] = [real_id if ref == new_id else ref for ref in refs]
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
    source: Any = None
    if kind in ("create", "edit", "remove", "move"):
        # Terminal authorability is proven locally against the semantic owner's
        # accepted base. Same-frontier peer proposals are deliberately invisible.
        if len(parents) != 1:
            return _error(
                "invalid_arguments",
                f"{kind} work requires exactly one semantic parent",
            )
        source, projection_error = _projection(workspace_root, slug, parents[0])
        if source is None:
            return projection_error
    if kind in ("create", "edit", "remove"):
        path = _canonical_path_field(fields.get("path"), "path")
        if isinstance(path, dict):
            return path
        node["path"] = path
        if kind == "create":
            node["content"] = fields.get("content")
        elif kind == "edit":
            base = _base_content(source, path)
            if isinstance(base, dict):
                return base
            if base is None:
                return _unavailable(
                    "edit_base_unavailable",
                    f"no accepted base content for {path!r}",
                    dag,
                    source,
                    path,
                )
            generated = _generated_edit_patch(base, base, fields.get("replacements"), path)
            if isinstance(generated, dict):
                return generated
            node["patch"] = generated
    elif kind == "move":
        from_path = _canonical_path_field(fields.get("from_path"), "from_path")
        if isinstance(from_path, dict):
            return from_path
        to_path = _canonical_path_field(fields.get("to_path"), "to_path")
        if isinstance(to_path, dict):
            return to_path
        overwrite = _bool_field(fields.get("overwrite"), "overwrite")
        if isinstance(overwrite, dict):
            return overwrite
        node["from_path"] = from_path
        node["to_path"] = to_path
        node["overwrite"] = overwrite
    elif kind == "run":
        command = fields.get("command")
        allowed, reason = change_dag_policy.validate_run_command(command)
        if not allowed:
            return _error("run_command_rejected", reason)
        node["command"] = list(command)
        node["exclusive"] = bool(fields.get("exclusive", False))

    # ``edit`` proves authorability by generating its patch; the other terminal
    # kinds share the update path's validator so add and update cannot diverge.
    if kind in ("create", "remove", "move"):
        failure = _validate_terminal(kind, node, dag, source)
        if failure is not None:
            return failure

    new_id = _peek_next_id(dag, workspace_root, slug)
    candidate = copy.deepcopy(dag)
    candidate_nodes = candidate["nodes"]
    candidate_nodes[new_id] = node
    for parent in parents:
        refs = list(candidate_nodes[parent].get("requires", []))
        if new_id not in refs:
            refs.append(new_id)
        candidate_nodes[parent]["requires"] = refs

    errors = change_dag.validate_dag(candidate)
    if errors:
        return _error("invalid_graph", "; ".join(errors), errors=errors)

    real_id = change_dag.allocate_node_id(dag, workspace_root, slug)
    if real_id != new_id:
        candidate_nodes[real_id] = candidate_nodes.pop(new_id)
        for entry in candidate_nodes.values():
            refs = entry.get("requires")
            if isinstance(refs, list) and new_id in refs:
                entry["requires"] = [real_id if ref == new_id else ref for ref in refs]
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

    if kind in ("create", "edit", "remove", "move"):
        # Every terminal mutation proves the RESULTING operation against the
        # semantic owner's accepted base before persistence -- the same check
        # ``add_work`` performs, so add and update cannot diverge.
        owner = _semantic_owner(dag, node_id)
        if isinstance(owner, dict):
            return owner
        source, projection_error = _projection(workspace_root, slug, owner)
        if source is None:
            return projection_error
        if kind == "edit":
            patch, failure = _resolve_edit_update(nodes[node_id], provided, dag, source)
            if failure is not None:
                return failure
            provided.pop("replacements", None)
            provided["patch"] = patch
        else:
            result = dict(nodes[node_id])
            result.update(provided)
            failure = _validate_terminal(kind, result, dag, source)
            if failure is not None:
                return failure

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
def set_decomposition_only(
    workspace_root: Path, slug: str, node_id: str, value: Any
) -> dict[str, Any]:
    """Declare or reopen whether a semantic node owns no direct terminal work.

    ``decomposition_only`` is persisted authoring intent, not runtime state. It is
    semantic-only: a terminal node can never be fully decomposed, so the setter
    rejects a non-semantic target. Setting ``true`` validates the structural
    invariant that the node directly requires at least one semantic child and no
    terminal child; setting ``false`` lets a worker reopen an earlier judgment
    and preserves the node's existing child structure.

    Like the other DAG mutations, the setter consults canonical node mutability:
    a semantic subtree whose required work is already runtime-satisfied is
    immutable, so every setter call against it is rejected.
    """
    workspace_root = Path(workspace_root)
    if not isinstance(value, bool):
        return _error("invalid_arguments", "value must be a boolean")
    dag, state, err = _mutation_context(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None

    if node_id == dag.get("root"):
        return _error(
            "root_immutable",
            "the root node is immutable; it is always decomposition_only",
        )
    nodes = change_dag.node_map(dag)
    if node_id not in nodes:
        return _error("unknown_node", f"node not found: {node_id}")
    if change_dag.node_type(dag, node_id) != change_dag.SEMANTIC_TYPE:
        return _error(
            "invalid_node",
            f"node {node_id} is not semantic; decomposition_only is semantic-only",
        )

    # decomposition_only is mutation authority, not an idempotent read/check: a
    # runtime-satisfied semantic subtree rejects every setter call, including
    # apparent no-ops. Reuse the canonical mutability rule rather than
    # duplicating its satisfaction logic here.
    mutable, reason = change_dag.mutability(dag, state, node_id)
    if not mutable:
        return _error("immutable_node", reason)

    candidate = copy.deepcopy(dag)
    candidate["nodes"][node_id]["decomposition_only"] = value
    errors = change_dag.validate_dag(candidate)
    if errors:
        return _error("invalid_graph", "; ".join(errors), errors=errors)

    _persist(candidate, workspace_root, slug)
    return change_dag.output(
        {"slug": slug, "node_id": node_id, "decomposition_only": value},
        "Set Decomposition Only",
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
        refs = node.get("requires")
        if not isinstance(refs, list):
            continue
        filtered = [ref for ref in refs if ref != node_id]
        if filtered:
            node["requires"] = filtered
        else:
            node.pop("requires", None)

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
