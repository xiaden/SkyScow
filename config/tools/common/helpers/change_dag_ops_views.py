"""Read-only preview, validation, and show projections for a Change DAG.

This module is a consumer of the Change DAG compiler; it must not recreate
compiler semantics. Whole-DAG preview performs exactly one
:func:`change_dag_compiler_phase.compile_whole_dag` and reuses that compilation when
calling ``preflight(..., compilation=(conflicts, blocked))`` -- it must never
derive a parallel compilation or report. Authoring-context preview uses
``compile_lower_work`` with the persisted state passed through. Preview run
readiness is the persisted-state ``ready_run_nodes(dag, state, workspace_root)``
question, which is intentionally distinct from ``Phase.ready_runs``. Standalone
validation may call ``preflight`` without a precomputed compilation, causing
exactly one whole-DAG compilation. Never writes, never runs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import change_dag
from . import change_dag_compiler_graph as compiler_graph
from . import change_dag_compiler_phase as compiler_phase
from .change_dag_ops_support import _error, _load, _numeric
from .change_dag_patch import PatchError, read_text_preserving


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


def _render_op(op: Any, *, phase: int | None = None) -> dict[str, Any]:
    rendered: dict[str, Any] = {
        "nodes": list(op.nodes),
        "op": op.op,
        "path": op.path,
        "from_path": op.from_path,
        "to_path": op.to_path,
    }
    if phase is not None:
        # RUN-BARRIER execution phase, never a construction frontier.
        rendered["segment"] = phase
        rendered["execution_phase"] = phase
    if op.op == "move":
        rendered["overwrite"] = bool(op.overwrite)
    if op.content is not None:
        rendered["content"] = op.content
    if op.patch_text is not None:
        rendered["patch"] = op.patch_text
    if op.applied is not None:
        rendered["applied"] = op.applied
    return rendered


def _read_live_source(workspace_root: Path, path: str) -> str | None:
    target = workspace_root / path
    if not target.is_file():
        return None
    try:
        return read_text_preserving(target)
    except (PatchError, OSError):
        return None


def _op_affects_path(op: Any, scope: str) -> bool:
    """Return whether a compiled operation affects the canonical path scope."""
    affected_paths = [op.path]
    if op.op == "move" and op.to_path is not None:
        affected_paths.append(op.to_path)
    return any(change_dag.canonical_path(path) == scope for path in affected_paths)


def _authoring_preview(
    dag: dict[str, Any], workspace_root: Path, slug: str, path: str, node_id: str,
    state: dict[str, str],
) -> dict[str, Any]:
    """Frontier-bounded authoring context for one semantic boundary and path.

    Answers "what effective content may an author working on ``node_id``
    legitimately use as accepted prior context for ``path``?": live source plus
    accepted lower DAG work whose construction frontier is strictly deeper than
    the boundary. Same-frontier peer proposals, the boundary node's own proposed
    work, and shallower/future work are excluded from the effective source; only
    a count of that excluded later work is reported. Never writes, never runs.
    """
    try:
        scope = change_dag.canonical_path(path)
    except ValueError as exc:
        return _error("invalid_path", f"path: {exc}")
    nodes = change_dag.node_map(dag)
    if node_id not in nodes:
        return _error("unknown_node", f"node not found: {node_id}")
    node_kind = change_dag.node_type(dag, node_id)
    if node_kind != change_dag.SEMANTIC_TYPE:
        return _error(
            "invalid_boundary_node",
            "authoring-context preview requires a semantic boundary node; "
            f"{node_id} is {node_kind!r}",
        )
    depths = change_dag.derived_depth(dag)
    if node_id not in depths:
        return _error(
            "invalid_boundary_node",
            f"boundary node is not reachable from the root: {node_id}",
        )
    boundary_depth = depths[node_id]

    ops, conflicts, overlay, removed = compiler_phase.compile_lower_work(
        dag, workspace_root, boundary_depth, state=state
    )
    # A move affects both spellings: it is visible from its source and target.
    scoped_ops = [
        op for op in ops if op.path == scope or (op.op == "move" and op.to_path == scope)
    ]
    contributing = sorted({node for op in scoped_ops for node in op.nodes}, key=_numeric)
    contributing_set = set(contributing)
    scoped_conflicts = [
        conflict
        for conflict in conflicts
        if conflict.path == scope or (set(conflict.nodes) & contributing_set)
    ]

    live_source = _read_live_source(workspace_root, scope)
    if scope in overlay:
        effective_source = overlay[scope]
    elif scope in removed:
        effective_source = None
    else:
        effective_source = live_source

    frontiers = compiler_graph.lower_work_frontiers(dag)
    frontier_counts = {
        "same_frontier_nodes": sum(1 for f in frontiers.values() if f == boundary_depth),
        "shallower_nodes": sum(1 for f in frontiers.values() if f < boundary_depth),
    }

    payload = {
        "slug": slug,
        "mode": "authoring_context",
        "path": scope,
        "node_id": node_id,
        "boundary_depth": boundary_depth,
        "frontier": boundary_depth,
        "live_present": live_source is not None,
        "live_source": live_source,
        "effective_source": effective_source,
        "ops": [_render_op(op) for op in scoped_ops],
        "contributing_nodes": contributing,
        "creates": [_render_op(op) for op in scoped_ops if op.op == "create"],
        "edits": [_render_op(op) for op in scoped_ops if op.op == "edit"],
        "moves": [_render_op(op) for op in scoped_ops if op.op == "move"],
        "removes": [_render_op(op) for op in scoped_ops if op.op == "remove"],
        "conflicts": [
            {"path": conflict.path, "nodes": list(conflict.nodes),
             "reason": conflict.reason, "scope": conflict.scope}
            for conflict in scoped_conflicts
        ],
        # Metadata only: later/same-frontier work content never enters the bounded
        # authoring context consumed by the author.
        "excluded_later_work": frontier_counts,
    }
    return change_dag.output(
        payload,
        "Preview Change DAG Authoring Context",
        {"slug": slug, "node_id": node_id, "path": scope},
    )


def preview(workspace_root: Path, slug: str, path: str | None = None, node_id: str | None = None) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    dag, state, _location, err = _load(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None and state is not None

    # path + semantic node_id = frontier-bounded AUTHORING CONTEXT view.
    if path is not None and node_id is not None:
        return _authoring_preview(dag, workspace_root, slug, path, node_id, state)

    # Preview and admission share one whole-DAG compilation result.
    execution_phases, conflicts, blocked = compiler_phase.compile_whole_dag(
        dag, state, workspace_root
    )
    # Flatten every deterministically lowerable execution phase. `segment` is
    # retained as a compatibility alias, but it means a RUN-BARRIER execution
    # segment, not a construction frontier or the count of non-empty batches.
    ops = [op for phase in execution_phases for op in phase]
    execution_phase = {
        id(op): index for index, phase in enumerate(execution_phases) for op in phase
    }
    pre = compiler_phase.preflight(
        dag, state, workspace_root, compilation=(conflicts, blocked)
    )
    ready = compiler_graph.ready_run_nodes(dag, state, workspace_root)
    depths = change_dag.derived_depth(dag)

    if node_id is not None:
        if node_id not in change_dag.node_map(dag):
            return _error("unknown_node", f"node not found: {node_id}")
        subgraph = _reachable_subgraph(dag, node_id) | {node_id}
        ops = [op for op in ops if set(op.nodes) & subgraph]
        conflicts = [conflict for conflict in conflicts if set(conflict.nodes) & subgraph]
        blocked = [entry for entry in blocked if entry.node_id in subgraph]
    elif path is not None:
        try:
            scope = change_dag.canonical_path(path)
        except ValueError as exc:
            return _error("invalid_path", f"path: {exc}")
        ops = [op for op in ops if _op_affects_path(op, scope)]
        conflicts = [conflict for conflict in conflicts if conflict.path == scope]
        blocked = []

    mode = "node" if node_id is not None else ("path" if path is not None else "whole_dag")
    payload = {
        "slug": slug,
        "mode": mode,
        "ops": [_render_op(op, phase=execution_phase.get(id(op), 0)) for op in ops],
        "conflicts": [
            {"path": conflict.path, "nodes": list(conflict.nodes), "reason": conflict.reason,
             "scope": conflict.scope}
            for conflict in conflicts
        ],
        "blocked": [{"node_id": entry.node_id, "reason": entry.reason} for entry in blocked],
        "run_barriers": ready,
        # Keep the old field as a compatibility alias; both fields describe
        # RUN-BARRIER execution phases, never construction frontiers.
        "simulated_segments": len(execution_phases),
        "simulated_execution_phases": len(execution_phases),
        "depths": depths,
        "executable": pre["executable"],
        "issues": pre["issues"],
        "runtime_failures": pre.get("runtime_failures", []),
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
    pre = compiler_phase.preflight(dag, state, workspace_root)
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
        "unresolved_semantic_nodes": change_dag.unresolved_semantic_nodes(dag),
        "issues": issues,
        "runtime_failures": pre.get("runtime_failures", []),
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
