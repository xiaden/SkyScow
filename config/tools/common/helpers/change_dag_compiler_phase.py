"""Canonical phase/progression orchestration for the Change DAG compiler.

:func:`compile_phase` is the single authoritative next-step determination, and
:func:`_lower_progression` is the single shared simulation driver behind
:func:`compile_whole_dag` and :func:`compile_lower_work`. Execution, whole-DAG
preflight, and authoring projection all derive their work from these two
primitives; do not add a parallel derivation path.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from . import change_dag
from .change_dag_compiler_graph import lower_work_frontiers, ready_run_nodes
from .change_dag_compiler_lowering import _authored_shape_conflicts, compile_operations
from .change_dag_compiler_model import (
    Blocked,
    CompiledOp,
    Conflict,
    Phase,
    _RepoView,
    _finalize,
)
from .change_dag_patch import PatchError


def compile_phase(
    dag: dict,
    state: dict,
    workspace_root: Path,
    *,
    repo: "_RepoView | None" = None,
    include_nodes: set[str] | None = None,
) -> Phase:
    """Return the shared next mechanical phase and ready run frontier."""
    ops, conflicts, blocked = compile_operations(
        dag, state, workspace_root, repo=repo, include_nodes=include_nodes
    )
    projected = dict(state) if isinstance(state, dict) else {}
    for op in ops:
        for node_id in op.nodes:
            projected[node_id] = "satisfied"
    return Phase(
        ops=ops,
        conflicts=conflicts,
        blocked=blocked,
        ready_runs=ready_run_nodes(dag, projected, workspace_root),
    )


def _simulate_ops(repo: _RepoView, ops: list[CompiledOp], state: dict[str, str]) -> None:
    """Project a phase's ops onto the overlay and mark their nodes satisfied."""
    for op in ops:
        if op.op == "create":
            repo.put(op.path, op.content or "")
        elif op.op == "edit":
            repo.put(op.path, op.applied if op.applied is not None else "")
        elif op.op == "remove":
            repo.delete(op.path)
        elif op.op == "move":
            try:
                content: str | None = repo.read(op.from_path or "")
            except PatchError:
                content = None
            if op.to_path:
                repo.put(op.to_path, content if content is not None else "")
            repo.delete(op.from_path or "")
        for node_id in op.nodes:
            state[node_id] = "satisfied"


def _lower_progression(
    dag: dict,
    state: dict[str, str],
    workspace_root: Path,
    *,
    repo: _RepoView,
    advance_runs: bool,
    include_nodes: set[str] | None = None,
    conflicts: list[Conflict] | None = None,
) -> tuple[list[list[CompiledOp]], list[Conflict], list[Blocked]]:
    """Advance shared phases over an overlay until no work can progress.

    ``advance_runs`` controls whether ready run frontiers are simulated as
    satisfied; authoring context leaves them as execution boundaries.
    """
    phases: list[list[CompiledOp]] = []
    conflicts = list(conflicts or [])
    blocked: list[Blocked] = []
    seen = {(c.path, c.reason, tuple(c.nodes), c.scope) for c in conflicts}

    for _ in range(len(change_dag.node_map(dag)) + 2):
        phase = compile_phase(
            dag, state, workspace_root, repo=repo, include_nodes=include_nodes
        )
        for conflict in phase.conflicts:
            key = (conflict.path, conflict.reason, tuple(conflict.nodes), conflict.scope)
            if key not in seen:
                seen.add(key)
                conflicts.append(conflict)
        blocked = phase.blocked

        ready = phase.ready_runs if advance_runs else []
        # A run-only transition still advances the execution phase.
        progressed = bool(phase.ops or ready)
        if progressed:
            phases.append(phase.ops)
        if phase.ops:
            _simulate_ops(repo, phase.ops, state)
        for node_id in ready:
            state[node_id] = "satisfied"
        if not progressed:
            break

    return phases, conflicts, blocked


def compile_whole_dag(
    dag: dict, state: dict, workspace_root: Path
) -> tuple[list[list[CompiledOp]], list[Conflict], list[Blocked]]:
    """Lower all specified terminal work in memory for whole-DAG preflight.

    Runtime remains barrier-segmented; this simulation crosses ready run
    frontiers without executing them. It performs no writes or commands, keeps
    live drift as runtime evidence, and returns execution phases, conflicts, and
    remaining blocked work. Execution phase is distinct from construction depth.
    """
    effective_state = dict(state) if isinstance(state, dict) else {}
    overlay: dict[str, str] = {}
    removed: set[str] = set()
    repo = _RepoView(workspace_root, overlay, removed)

    # Detect authored defects before blocked progression hides them; state changes
    # here are private to the simulation.
    authored_conflicts = _authored_shape_conflicts(dag)
    for node_id in {node for conflict in authored_conflicts for node in conflict.nodes}:
        effective_state[node_id] = "failed"

    phases, conflicts, blocked = _lower_progression(
        dag, effective_state, workspace_root, repo=repo, advance_runs=True,
        conflicts=authored_conflicts,
    )
    _finalize(conflicts, blocked)
    return phases, conflicts, blocked


def compile_lower_work(
    dag: dict, workspace_root: Path, boundary_depth: int, *, state: dict | None = None
) -> tuple[list[CompiledOp], list[Conflict], dict[str, str], set[str]]:
    """Lower work from strictly deeper construction frontiers into an overlay.

    Same-frontier and shallower work is excluded; run barriers do not gate this
    authoring view. Satisfied lower work is assumed present in the live source,
    while failed or unapplied work remains projectable. Returns operations,
    conflicts, written overlay content, and removed paths.
    """
    frontiers = lower_work_frontiers(dag)
    include = {
        node_id for node_id, frontier in frontiers.items() if frontier > boundary_depth
    }

    # Satisfied work is already represented in live content; do not replay it.
    effective_state: dict[str, str] = {
        node_id: node_state
        for node_id, node_state in (state.items() if isinstance(state, dict) else ())
        if node_state == "satisfied"
    }
    overlay: dict[str, str] = {}
    removed: set[str] = set()
    repo = _RepoView(workspace_root, overlay, removed)

    phases, conflicts, _blocked = _lower_progression(
        dag, effective_state, workspace_root, repo=repo, advance_runs=False,
        include_nodes=include,
    )
    ordered_ops = [op for phase in phases for op in phase]
    _finalize(conflicts, [])
    return ordered_ops, conflicts, overlay, removed


def preflight(
    dag: dict,
    state: dict,
    workspace_root: Path,
    *,
    compilation: tuple[list[Conflict], list[Blocked]] | None = None,
) -> dict:
    """Derived pre-execution conflict/applicability check.

    Only deterministic *intra-DAG* conflicts (structure errors, conflicting
    operations authored into this DAG, malformed patches, creates that collide
    with each other) make the DAG non-executable. Live-repository applicability
    mismatches — a patch that no longer applies because the repository drifted,
    an edit target another work item removed, a create target another work item
    created — are reported as ``runtime_failures`` and handled as ordinary
    recoverable terminal-node failures when reached. Unresolved semantic nodes
    ARE an admission blocker: ``executable`` also requires ``resolved``. A dirty
    tree, HEAD drift, and blocked branch-local work are not issues.

    ``executable`` is the aggregate admission/lint result: it is true only when
    the DAG is structurally valid, ``resolved``, and *all* currently specified
    work lowers deterministically — not merely the first execution segment before
    the next unsatisfied run barrier. A caller that has
    already compiled the DAG passes ``compilation`` to reuse that result, so
    preview and validation derive their report from one compilation, not two.
    """
    issues: list[dict] = []
    runtime_failures: list[dict] = []
    try:
        structural = change_dag.structure_errors(dag)
    except Exception as exc:  # pragma: no cover - defensive
        structural = [f"structure check failed: {exc}"]
    if structural:
        for message in structural:
            issues.append({"kind": "structure", "message": message})
        return {"executable": False, "issues": issues, "runtime_failures": [], "conflicts": [], "blocked": []}

    # Unresolved authoring state blocks execution, but it never short-circuits the
    # compiler analysis below: one pass reports every independently discoverable
    # admission reason together so the author can fix the DAG in fewer iterations.
    unresolved = change_dag.unresolved_semantic_nodes(dag)
    if unresolved:
        issues.append(
            {
                "kind": "unresolved",
                "nodes": unresolved,
                "message": "Change DAG contains unresolved semantic requirements",
            }
        )

    if compilation is None:
        try:
            _segments, conflicts, blocked = compile_whole_dag(dag, state, workspace_root)
        except Exception as exc:  # pragma: no cover - defensive
            issues.append({"kind": "compile_conflict", "message": f"compilation failed: {exc}"})
            return {"executable": False, "issues": issues, "runtime_failures": [], "conflicts": [], "blocked": []}
    else:
        conflicts, blocked = compilation

    for conflict in conflicts:
        entry = {
            "kind": "compile_conflict",
            "path": conflict.path,
            "nodes": list(conflict.nodes),
            "message": conflict.reason,
        }
        if conflict.scope == "runtime":
            # Live-repository applicability mismatch: not an admission blocker.
            entry["kind"] = "runtime_failure"
            runtime_failures.append(entry)
        else:
            entry["kind"] = "context_conflict" if conflict.reason.startswith("context_conflict") else "compile_conflict"
            issues.append(entry)

    return {
        "executable": not issues,
        "issues": issues,
        "runtime_failures": runtime_failures,
        "conflicts": [asdict(conflict) for conflict in conflicts],
        "blocked": [asdict(entry) for entry in blocked],
    }


def summarize(ops: list[CompiledOp], conflicts: list[Conflict], blocked: list[Blocked]) -> dict:
    """Compact deterministic summary used by preview/validate reporting."""
    return {
        "ops": len(ops),
        "conflicts": len(conflicts),
        "blocked": len(blocked),
        "paths": sorted({op.path for op in ops}),
        "nodes": sorted({node for op in ops for node in op.nodes}, key=change_dag._numeric_id),
        "conflict_paths": sorted({conflict.path for conflict in conflicts}),
        "blocked_nodes": sorted({entry.node_id for entry in blocked}, key=change_dag._numeric_id),
    }
