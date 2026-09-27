"""Compiler-facing graph determinations.

Owns the DAG-shape questions the compiler asks before lowering: branch-local
failure propagation, semantic-parent lookup, run-barrier gating, actionable
mechanical work, ready-run determination, and construction-frontier
calculation. This module must not lower operations or reconcile edits.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import change_dag
from .change_dag_compiler_model import Blocked, MECHANICAL_TYPES


def _order_index(dag: Any) -> dict[str, int]:
    return {node_id: index for index, node_id in enumerate(change_dag.execution_order(dag))}


def _node_sort_key(order_index: dict[str, int]):
    def key(node_id: str):
        return (order_index.get(node_id, 1 << 30), change_dag._numeric_id(node_id))

    return key


def _subtree_failed(dag: Any, state: dict[str, str], node_id: str) -> bool:
    """True when the subtree rooted at ``node_id`` contains a failed terminal."""
    memo: dict[str, bool] = {}
    visiting: set[str] = set()

    def resolve(current: str) -> bool:
        if current in memo:
            return memo[current]
        if current in visiting:
            return False
        kind = change_dag.node_type(dag, current)
        if kind in change_dag.TERMINAL_TYPES:
            value = state.get(current) == "failed"
        elif kind == change_dag.SEMANTIC_TYPE:
            visiting.add(current)
            value = any(resolve(child) for child in change_dag.direct_children(dag, current))
            visiting.discard(current)
        else:
            value = False
        memo[current] = value
        return value

    return resolve(node_id)


def _semantic_parents(dag: Any, node_id: str) -> list[str]:
    """Direct semantic parents of ``node_id`` -- the nodes that require it."""
    return [
        candidate
        for candidate, node in change_dag.node_map(dag).items()
        if node.get("type") == change_dag.SEMANTIC_TYPE
        and node_id in change_dag.direct_children(dag, candidate)
    ]


def _blocked_reason(dag: Any, state: dict[str, str], node_id: str) -> str | None:
    """Return a failure reason only for a ``run`` node's required siblings."""
    if change_dag.node_type(dag, node_id) != "run":
        return None
    for parent in _semantic_parents(dag, node_id):
        for sibling in change_dag.direct_children(dag, parent):
            if sibling == node_id:
                continue
            if _subtree_failed(dag, state, sibling):
                return f"required sibling branch {sibling} of {parent} failed"
    return None


def _barrier_gated(dag: Any, state: dict[str, str]) -> dict[str, str]:
    """Map each mechanical node to its deepest applicable unsatisfied barrier.

    Work below or at a barrier parent's depth may progress; shallower work that
    bubbles through that parent waits. Selection is independent of node-map order.
    """
    nodes = change_dag.node_map(dag)
    effective = state if isinstance(state, dict) else {}
    satisfaction = change_dag.derived_satisfaction(dag, effective)
    depth = change_dag.derived_depth(dag)
    parents: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for node_id in nodes:
        for child in change_dag.direct_children(dag, node_id):
            if child in nodes:
                parents.setdefault(child, set()).add(node_id)

    ancestors = change_dag.ancestor_map(dag)
    order_index = _order_index(dag)

    def barrier_rank(run_id: str, parent_depth: int) -> tuple[int, int, int, str]:
        # Deepest barrier first; ties broken by execution order then numeric id.
        return (
            parent_depth,
            -order_index.get(run_id, 1 << 30),
            -change_dag._numeric_id(run_id),
            run_id,
        )

    # For every ancestor, the *deepest* unsatisfied barrier whose parent it
    # strictly contains. Using max (not first-wins) keeps a deeper barrier from
    # being masked by a shallower one encountered earlier in node-map order.
    best: dict[str, tuple[int, int, int, str]] = {}
    for run_id in change_dag.execution_order(dag):
        if change_dag.node_type(dag, run_id) != "run":
            continue
        if satisfaction.get(run_id, False):
            continue
        for parent in parents.get(run_id, ()):
            candidate = barrier_rank(run_id, depth.get(parent, 0))
            for ancestor in ancestors.get(parent, ()):
                current = best.get(ancestor)
                if current is None or candidate > current:
                    best[ancestor] = candidate
    if not best:
        return {}

    gated: dict[str, str] = {}
    for node_id in nodes:
        if change_dag.node_type(dag, node_id) not in MECHANICAL_TYPES:
            continue
        if effective.get(node_id) in {"satisfied", "failed"}:
            continue
        node_depth = depth.get(node_id, 0)
        chosen: tuple[int, int, int, str] | None = None
        for parent in parents.get(node_id, ()):
            candidate = best.get(parent)
            if candidate is not None and node_depth < candidate[0]:
                if chosen is None or candidate > chosen:
                    chosen = candidate
        if chosen is not None:
            gated[node_id] = chosen[3]
    return gated


def _actionable_mechanical(dag: Any, state: dict[str, str]) -> tuple[list[str], list[Blocked]]:
    reachable = change_dag.reachable_from_root(dag)
    gated = _barrier_gated(dag, state)
    actionable: list[str] = []
    blocked: list[Blocked] = []
    for node_id in change_dag.execution_order(dag):
        if node_id not in reachable:
            continue
        if change_dag.node_type(dag, node_id) not in MECHANICAL_TYPES:
            continue
        # Terminal work is immutable until dag_start(retry=true) resets failures.
        if state.get(node_id) in {"satisfied", "failed"}:
            continue
        barrier = gated.get(node_id)
        if barrier is not None:
            blocked.append(Blocked(node_id=node_id, reason=f"blocked by unsatisfied run barrier {barrier}"))
            continue
        actionable.append(node_id)
    return actionable, blocked


def lower_work_frontiers(dag: Any) -> dict[str, int]:
    """Return each mechanical node's longest-path construction frontier."""
    depths = change_dag.derived_depth(dag)
    nodes = change_dag.node_map(dag)
    semantic_parents: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for node_id, node in nodes.items():
        if node.get("type") != change_dag.SEMANTIC_TYPE:
            continue
        for child in change_dag.direct_children(dag, node_id):
            semantic_parents.setdefault(child, []).append(node_id)
    frontiers: dict[str, int] = {}
    for node_id in nodes:
        if change_dag.node_type(dag, node_id) not in MECHANICAL_TYPES:
            continue
        parents = semantic_parents.get(node_id, [])
        if not parents:
            continue
        frontiers[node_id] = max(depths.get(parent, 0) for parent in parents)
    return frontiers


def ready_run_nodes(dag: dict, state: dict, workspace_root: Path) -> list[str]:
    """Return reachable, not-yet-satisfied ``run`` nodes ready to execute.

    A run is ready when every *other* child subtree of each semantic parent is
    satisfied and its own branch has no failed sibling. Independent run
    frontiers across separate branches may be ready simultaneously.
    """
    effective_state = state if isinstance(state, dict) else {}
    satisfaction = change_dag.derived_satisfaction(dag, effective_state)
    reachable = change_dag.reachable_from_root(dag)
    ready: list[str] = []
    for node_id in change_dag.execution_order(dag):
        if node_id not in reachable or change_dag.node_type(dag, node_id) != "run":
            continue
        if effective_state.get(node_id) == "satisfied":
            continue
        if effective_state.get(node_id) == "failed":
            continue
        parents = _semantic_parents(dag, node_id)
        if not parents:
            continue
        all_requirements_met = True
        for parent in parents:
            for sibling in change_dag.direct_children(dag, parent):
                if sibling == node_id:
                    continue
                if not satisfaction.get(sibling, False):
                    all_requirements_met = False
        if not all_requirements_met:
            continue
        if _blocked_reason(dag, effective_state, node_id) is not None:
            continue
        ready.append(node_id)
    return sorted(ready, key=change_dag._numeric_id)
