"""Mechanical lowering for the Change DAG compiler.

Lowers reachable mechanical work into coordinated per-path operations:
path canonicalization, create/edit/remove/move bucketing and collision
detection, move ordering / same-frontier move checks, authored-shape
compiler conflicts, and :func:`compile_operations`. It depends on the model,
graph gating, and edit reconciliation; it must not drive progression or write.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import change_dag
from . import change_dag_policy
from .change_dag_compiler_graph import _actionable_mechanical, _node_sort_key, _order_index
from .change_dag_compiler_model import (
    Blocked,
    CompiledOp,
    Conflict,
    MECHANICAL_TYPES,
    _RepoView,
    _finalize,
)
from .change_dag_compiler_reconcile import (
    _parse_edit_node_patch,
    _parse_edit_nodes,
    _reconcile_frontier_edits,
)
from .change_dag_patch import PatchError


def _canonical_node_path(node: dict, field: str) -> str | None:
    """Canonical workspace-relative identity for a node path field, or ``None``.

    ``None`` means the stored value cannot be represented consistently as a
    workspace-relative DAG path (reported as a deterministic conflict) rather
    than letting two spellings of one file compile independently.
    """
    try:
        return change_dag.canonical_path(node.get(field))
    except ValueError:
        return None


def compile_operations(
    dag: dict,
    state: dict,
    workspace_root: Path,
    *,
    repo: "_RepoView | None" = None,
    include_nodes: set[str] | None = None,
) -> tuple[list[CompiledOp], list[Conflict], list[Blocked]]:
    """Lower reachable mechanical work into coordinated per-path operations.

    Paths use canonical identity. ``repo`` supplies a live or simulated read-only
    view; ``include_nodes`` is reserved for frontier-bounded authoring preview and
    bypasses execution run-barrier gating.
    """
    effective_state = state if isinstance(state, dict) else {}
    workspace_root = Path(workspace_root)
    view = repo if repo is not None else _RepoView(workspace_root)
    order_index = _order_index(dag)
    order_key = _node_sort_key(order_index)
    depths = change_dag.derived_depth(dag)

    if include_nodes is None:
        mechanical, blocked = _actionable_mechanical(dag, effective_state)
    else:
        mechanical = [
            node_id
            for node_id in change_dag.execution_order(dag)
            if node_id in include_nodes
            and change_dag.node_type(dag, node_id) in MECHANICAL_TYPES
            and effective_state.get(node_id) not in {"satisfied", "failed"}
        ]
        blocked = []
    nodes_map = change_dag.node_map(dag)

    creates: dict[str, list[str]] = {}
    edits: dict[str, list[str]] = {}
    removes: dict[str, list[str]] = {}
    moves: list[tuple[str, str, str, bool]] = []
    invalid_paths: list[tuple[str, list[Any]]] = []
    buckets = {"create": creates, "edit": edits, "remove": removes}
    for node_id in mechanical:
        node = nodes_map[node_id]
        kind = node["type"]
        if kind == "move":
            from_path = _canonical_node_path(node, "from_path")
            to_path = _canonical_node_path(node, "to_path")
            if from_path is None or to_path is None:
                invalid_paths.append((node_id, [node.get("from_path"), node.get("to_path")]))
                continue
            moves.append((node_id, from_path, to_path, bool(node.get("overwrite", False))))
        else:
            path = _canonical_node_path(node, "path")
            if path is None:
                invalid_paths.append((node_id, [node.get("path")]))
                continue
            buckets[kind].setdefault(path, []).append(node_id)

    conflicts: list[Conflict] = []
    conflicted: set[str] = set()

    def add_conflict(path: str, nodes: list[str], reason: str, scope: str = "intra_dag") -> None:
        unique = sorted(set(nodes), key=order_key)
        conflicts.append(Conflict(path=path, nodes=unique, reason=reason, scope=scope))
        conflicted.update(unique)

    def group_ok(nodes: list[str]) -> bool:
        return not any(node_id in conflicted for node_id in nodes)

    for node_id, raw_paths in sorted(invalid_paths, key=lambda item: change_dag._numeric_id(item[0])):
        shown = ", ".join(repr(raw) for raw in raw_paths)
        add_conflict(shown, [node_id],
                     f"compile_conflict: path is not a usable workspace-relative path: {shown}")

    # --- same-path create/edit/remove coordination (intra-DAG) ---
    for path in sorted(set(creates) | set(edits) | set(removes)):
        if path in creates and path in removes:
            add_conflict(path, creates[path] + removes[path],
                         "compile_conflict: create and remove target the same path")
        if path in edits and path in removes:
            add_conflict(path, edits[path] + removes[path],
                         "compile_conflict: edit and remove target the same path")
    for path, nodes in creates.items():
        if len(nodes) > 1:
            add_conflict(path, nodes, "compile_conflict: multiple create nodes for the same path")
        if view.exists(path):
            if view.is_dag_written(path):
                add_conflict(path, nodes,
                             "compile_conflict: create target was already produced by earlier DAG work")
            else:
                add_conflict(path, nodes,
                             "runtime_context: create target already exists in the live repository",
                             scope="runtime")
    for path, nodes in edits.items():
        if path not in creates and not view.is_file(path):
            if view.is_dag_removed(path):
                add_conflict(path, nodes,
                             "compile_conflict: edit target was removed by earlier DAG work")
            else:
                add_conflict(path, nodes,
                             "runtime_context: edit target does not exist in the live repository",
                             scope="runtime")

    # --- move coordination ---
    move_sources: dict[str, list[str]] = {}
    move_dests: dict[str, list[str]] = {}
    for node_id, from_path, to_path, _overwrite in moves:
        move_sources.setdefault(from_path, []).append(node_id)
        move_dests.setdefault(to_path, []).append(node_id)

    # MOVE ordering is semantically significant (deeper construction first); the
    # one ordering is computed here and reused when emitting move ops below.
    ordered_moves = sorted(moves, key=lambda item: order_key(item[0]))

    # Two moves at the SAME construction frontier are both interpreted against
    # the same accepted lower-work base; neither may consume the other's output.
    # When one move's destination is another move's source, the final repository
    # state would depend only on which is emitted first (the numeric-id
    # tie-break), so the pair is an authored ambiguity: reject before any op is
    # emitted for either. DIFFERENT construction depths stay legal because the
    # move loop below orders deeper work first, letting a shallower move consume
    # a source freed by a deeper move. Paths are already canonicalized above.
    for left in range(len(ordered_moves)):
        left_id, left_from, left_to, _left_overwrite = ordered_moves[left]
        for right in range(left + 1, len(ordered_moves)):
            right_id, right_from, right_to, _right_overwrite = ordered_moves[right]
            if depths.get(left_id, 0) != depths.get(right_id, 0):
                continue
            if left_to == right_from:
                shared = left_to
            elif right_to == left_from:
                shared = right_to
            else:
                continue
            add_conflict(
                shared,
                [left_id, right_id],
                f"compile_conflict: same-frontier moves {left_id} and {right_id} "
                f"form an unorderable chain through {shared}",
            )

    for node_id, from_path, to_path, overwrite in moves:
        involved = [node_id]
        for collision in (edits.get(from_path), removes.get(from_path)):
            if collision:
                involved.extend(collision)
        if len(involved) > 1:
            add_conflict(from_path, involved,
                         "compile_conflict: move source is also edited/removed")
        if len(move_sources[from_path]) > 1:
            add_conflict(from_path, move_sources[from_path],
                         "compile_conflict: multiple moves share one source path")
        if from_path not in creates and not view.is_file(from_path):
            if view.is_dag_removed(from_path):
                add_conflict(from_path, move_sources[from_path],
                             "compile_conflict: move source was removed by earlier DAG work")
            else:
                add_conflict(from_path, move_sources[from_path],
                             "runtime_context: move source does not exist in the live repository",
                             scope="runtime")
        if view.is_dag_written(to_path):
            add_conflict(from_path, [node_id],
                         "compile_conflict: move destination was already produced by earlier DAG work")
        elif not overwrite and view.exists(to_path):
            # An overwriting move may legitimately replace a live destination;
            # content the DAG itself produced is still a deterministic conflict.
            add_conflict(from_path, [node_id],
                         "runtime_context: move destination already exists in the live repository",
                         scope="runtime")
        destination_clash = [
            other
            for other in (
                creates.get(to_path, [])
                + edits.get(to_path, [])
                + removes.get(to_path, [])
                + [candidate for candidate in move_dests.get(to_path, []) if candidate != node_id]
            )
            if other != node_id
        ]
        if destination_clash:
            add_conflict(from_path, [node_id, *destination_clash],
                         "compile_conflict: move destination collides with other work")

    ops: list[CompiledOp] = []
    move_ops: list[CompiledOp] = []

    # --- create / edit groups (create supplies the base content) ---
    for path in sorted(set(creates) | set(edits)):
        group = sorted(set(creates.get(path, []) + edits.get(path, [])), key=order_key)
        if not group_ok(group):
            continue
        edit_nodes = sorted(edits.get(path, []), key=order_key)
        patch_text = "".join(nodes_map[node]["patch"] for node in edit_nodes)
        if path in creates:
            if len(creates[path]) > 1:
                continue  # already reported as multiple creates for one path
            base = nodes_map[creates[path][0]]["content"]
            base_is_authored = True
        else:
            try:
                base = view.read(path)
            except PatchError as exc:
                add_conflict(path, group, f"runtime_context: cannot read target: {exc}",
                             scope="runtime")
                continue
            base_is_authored = view.is_dag_written(path)

        if not edit_nodes:
            ops.append(CompiledOp(nodes=group, op="create", path=path, content=base, applied=base))
            continue

        updated, problems = _reconcile_frontier_edits(
            base, edit_nodes, nodes_map, depths, path,
            base_is_authored=base_is_authored,
            base_nodes=list(creates.get(path, [])),
        )
        for problem_nodes, reason, scope in problems:
            add_conflict(path, problem_nodes, reason, scope=scope)
        if problems:
            continue

        try:
            parsed, _owners = _parse_edit_nodes(nodes_map, edit_nodes, path)
        except PatchError as exc:
            add_conflict(path, group, f"compile_conflict: malformed patch: {exc}")
            continue
        if path in creates:
            ops.append(CompiledOp(nodes=group, op="create", path=path, content=updated,
                                  patch_text=patch_text or None, applied=updated))
        else:
            ops.append(CompiledOp(nodes=group, op="edit", path=path, patches=parsed,
                                  patch_text=patch_text or None, applied=updated,
                                  base_text=base if len(edit_nodes) > 1 else None))

    # --- removes ---
    for path in sorted(removes):
        group = sorted(removes[path], key=order_key)
        if not group_ok(group):
            continue
        ops.append(CompiledOp(nodes=group, op="remove", path=path))

    # --- moves ---
    # MOVE ordering is semantically significant: a shallower move may consume a
    # destination freed by a deeper move's source, so moves are applied in
    # construction-depth order (deeper first) with a deterministic tie-break.
    # Filename/path sorting would silently reverse that dependency and execute a
    # contradictory order.
    for node_id, from_path, to_path, overwrite in ordered_moves:
        if node_id in conflicted:
            continue
        move_ops.append(CompiledOp(nodes=[node_id], op="move", path=from_path,
                                   from_path=from_path, to_path=to_path, overwrite=overwrite))

    rank = {"create": 0, "edit": 1, "remove": 3}
    ops.sort(key=lambda compiled: (compiled.path, rank.get(compiled.op, 9)))
    # A same-path create/edit/remove runs before a move that consumes it (a
    # create may supply a move source); moves keep their depth order among
    # themselves. No non-move operation can depend on a move's output: a move
    # destination colliding with other work is an explicit conflict.
    ops.extend(move_ops)

    _finalize(conflicts, blocked)
    return ops, conflicts, blocked


def _invalid_path_conflict(node_id: str, raw_paths: list[Any]) -> Conflict:
    shown = ", ".join(repr(raw) for raw in raw_paths)
    return Conflict(
        path=shown,
        nodes=[node_id],
        reason=f"compile_conflict: path is not a usable workspace-relative path: {shown}",
    )


def _authored_shape_conflicts(dag: Any) -> list[Conflict]:
    """Independently knowable authored defects, regardless of runtime progress.

    A run barrier that stays blocked in simulation must not hide malformed
    authored work above or beside it. This validates only a node's *authored*
    shape/syntax -- never live applicability, which stays ordinary recoverable
    runtime evidence -- and reuses the compiler's own parse/canonicalization
    entry points so there is a single implementation.
    """
    nodes = change_dag.node_map(dag)
    reachable = change_dag.reachable_from_root(dag)
    found: list[Conflict] = []
    for node_id in change_dag.execution_order(dag):
        if node_id not in reachable:
            continue
        kind = change_dag.node_type(dag, node_id)
        node = nodes[node_id]
        if kind == "run":
            allowed, reason = change_dag_policy.validate_run_command(node.get("command"))
            if not allowed:
                found.append(Conflict(
                    path=node_id,
                    nodes=[node_id],
                    reason=f"compile_conflict: run command rejected by policy: {reason}",
                ))
            continue
        if kind not in MECHANICAL_TYPES:
            continue
        if kind == "edit":
            path = _canonical_node_path(node, "path")
            if path is None:
                found.append(_invalid_path_conflict(node_id, [node.get("path")]))
                continue
            raw_patch = node.get("patch")
            if not isinstance(raw_patch, str) or not raw_patch:
                found.append(Conflict(
                    path=path,
                    nodes=[node_id],
                    reason="compile_conflict: malformed patch: patch must be a non-empty string",
                ))
                continue
            try:
                _parse_edit_node_patch(node_id, node, path)
            except PatchError as exc:
                found.append(Conflict(
                    path=path,
                    nodes=[node_id],
                    reason=f"compile_conflict: malformed patch: {exc}",
                ))
            continue
        if kind == "move":
            from_path = _canonical_node_path(node, "from_path")
            to_path = _canonical_node_path(node, "to_path")
            if from_path is None or to_path is None:
                found.append(_invalid_path_conflict(
                    node_id, [node.get("from_path"), node.get("to_path")]
                ))
            if "overwrite" in node and not isinstance(node.get("overwrite"), bool):
                found.append(Conflict(
                    path=from_path or node_id,
                    nodes=[node_id],
                    reason="compile_conflict: move overwrite must be a boolean",
                ))
            continue
        # create / remove
        path = _canonical_node_path(node, "path")
        if path is None:
            found.append(_invalid_path_conflict(node_id, [node.get("path")]))
        if kind == "create" and not isinstance(node.get("content"), str):
            found.append(Conflict(
                path=path or node_id,
                nodes=[node_id],
                reason="compile_conflict: create content must be a string",
            ))
    return found
