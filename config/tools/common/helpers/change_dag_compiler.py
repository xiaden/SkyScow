"""Deterministic Change DAG compiler shared by ``dag_preview`` and execution.

The compiler lowers the declarative DAG plus Execution State into concrete
per-file operations against the *live* repository. It never creates a projected
worktree and never writes; only :func:`apply_compiled` writes, and only through
the atomic per-file primitive in :mod:`change_dag_patch`.

Runtime lowering is segmented: it stops at the next unsatisfied run barrier and
resumes only after that run actually succeeds. Whole-DAG preflight instead uses
:func:`compile_whole_dag`, which simulates deterministic mechanical progression
through run barriers entirely in memory so ``executable`` reflects *all*
currently specified work rather than only the first executable segment.

Graph semantics are single-sourced from :mod:`change_dag`
(``execution_order``, ``derived_satisfaction``, reachability, node typing).
Failure is branch-local: a node is blocked only by a failure in a requirement
it actually depends on. A ``run`` node is ordered after its sibling
requirements under each direct semantic parent, so a failed sibling subtree
blocks it; sibling subtrees under a shared ancestor are independent branches
and never poison unrelated work.

Same-file edit nodes are frontier-aware. Every peer authored at the same
construction depth is interpreted against the *same* accepted lower-work state,
and only their non-overlapping changed spans are composed. Deeper accepted work
transforms the in-memory source that shallower work may intentionally consume;
numerical node IDs never become semantic causality.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import change_dag
from . import change_dag_patch
from . import change_dag_policy
from .change_dag_patch import (
    FilePatch,
    PatchContextError,
    PatchError,
    apply_file_patch,
    apply_patches,
    atomic_replace,
    detect_eol,
    normalize_eol,
    parse_unified_diff,
    read_text_preserving,
)

__all__ = [
    "CompiledOp",
    "Conflict",
    "Blocked",
    "compile_operations",
    "compile_whole_dag",
    "compile_lower_work",
    "lower_work_frontiers",
    "apply_compiled",
    "ready_run_nodes",
    "preflight",
    "node_present",
    "source_fingerprint",
    "summarize",
]

MECHANICAL_TYPES = ("create", "edit", "remove", "move")


@dataclass
class CompiledOp:
    nodes: list[str]
    op: str
    path: str
    from_path: str | None = None
    to_path: str | None = None
    content: str | None = None
    patches: list | None = None
    # Concrete compiled evidence: the raw lower-work patch text and the resulting
    # applied file content, so a bounded fresh context (and the Work Log) can see
    # exactly what was attempted rather than only node IDs and paths.
    patch_text: str | None = None
    applied: str | None = None
    # The accepted lower-work state an edit op's reconciled result was computed
    # against, set only when a frontier composed more than one peer. Application
    # then re-verifies that exact base instead of replaying peer patches in
    # numeric order (which would recreate a false peer dependency).
    base_text: str | None = None
    # Move nodes only: when true an existing destination is atomically replaced;
    # when false (default) an existing destination is a recoverable failure.
    overwrite: bool = False


@dataclass
class Conflict:
    path: str
    nodes: list[str]
    reason: str
    # "intra_dag" = deterministic conflict among this DAG's own authored work
    # (makes the DAG non-executable). "runtime" = applicability mismatch against
    # the current live repository (an ordinary recoverable terminal failure).
    scope: str = "intra_dag"


@dataclass
class Blocked:
    node_id: str
    reason: str


class _RepoView:
    """Read-only file access used by compilation.

    The default view reads the live repository. Whole-DAG preflight passes a
    simulated overlay so higher work is lowered against the *in-memory* result of
    accepted lower work, never a projected worktree and never a repository write.
    """

    def __init__(self, workspace_root: Path, overlay: dict[str, str] | None = None,
                 removed: set[str] | None = None) -> None:
        self._root = Path(workspace_root)
        self._overlay = overlay if overlay is not None else {}
        self._removed = removed if removed is not None else set()

    def is_dag_written(self, path: str) -> bool:
        """True when the simulated DAG has already written this path."""
        return path in self._overlay

    def is_dag_removed(self, path: str) -> bool:
        """True when the simulated DAG has already removed this path."""
        return path in self._removed

    def exists(self, path: str) -> bool:
        if path in self._overlay:
            return True
        if path in self._removed:
            return False
        return (self._root / path).exists()

    def is_file(self, path: str) -> bool:
        if path in self._overlay:
            return True
        if path in self._removed:
            return False
        return (self._root / path).is_file()

    def read(self, path: str) -> str:
        if path in self._overlay:
            return self._overlay[path]
        if path in self._removed:
            raise PatchError(f"path was removed by earlier DAG work: {path}")
        return read_text_preserving(self._root / path)

    def put(self, path: str, content: str) -> None:
        self._overlay[path] = content
        self._removed.discard(path)

    def delete(self, path: str) -> None:
        self._overlay.pop(path, None)
        self._removed.add(path)


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------
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
    """Return a branch-local failure reason, or ``None`` when progressable.

    Failure is branch-local: a node is blocked only by a failure on a semantic
    requirement path it actually depends on. A ``run`` node waits for the *other*
    requirements of each direct semantic parent, so a failure in one of those
    sibling subtrees genuinely blocks it. A mechanical node has no such
    dependency -- a sibling subtree under a shared ancestor is an independent
    branch -- so nothing here blocks it.
    """
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
    """Map a mechanical node to the unsatisfied run barrier that gates it.

    A ``run`` node is a satisfaction barrier at its semantic parent ``P``.
    Mechanical work that is *strictly shallower* than ``P`` and bubbles to an
    ancestor of ``P`` sits above that barrier and must not be applied until the
    run is satisfied. Mechanical work at the same depth as ``P`` (an independent
    sibling prerequisite) and work that feeds the run (below ``P``) still apply
    first, so unrelated branches keep progressing independently.

    Several barriers may share an ancestor. Gating is the existence of *any*
    applicable barrier, so the deepest barrier under each ancestor wins and a
    deeper unsatisfied barrier is never masked by a shallower one merely
    encountered first. Selection and the reported barrier are independent of
    node-map insertion order and deterministic under ties.
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
        # Satisfied work is immutable; failed work is an explicit recovery point
        # and must not be re-compiled/re-applied (that would never terminate).
        # Recovery is owned by dag_start(retry=true), which resets failed nodes.
        if state.get(node_id) in {"satisfied", "failed"}:
            continue
        barrier = gated.get(node_id)
        if barrier is not None:
            blocked.append(Blocked(node_id=node_id, reason=f"blocked by unsatisfied run barrier {barrier}"))
            continue
        # Mechanical work has no failure requirement: a sibling subtree under a
        # shared ancestor is an independent branch. Only run nodes are blocked by
        # a failure in a requirement they actually depend on.
        actionable.append(node_id)
    return actionable, blocked


def _parse_edit_node_patch(node_id: str, node: dict, path: str) -> FilePatch:
    """Parse one edit node's patch and enforce the one-node/one-file contract.

    An edit node represents exactly one file operation, so its patch must contain
    exactly one ``FilePatch``. The parsed target is canonicalized with
    :func:`change_dag.canonical_path` -- the same lexical identity used to group
    paths during compilation -- and must equal ``path`` (the node's already
    canonicalized declared ``path``). ``a/``/``b/`` headers normalize to the bare
    path, so ``a/foo.py``/``b/foo.py``/``./foo.py`` all match a declared
    ``foo.py``; any other target (including unsupported special forms such as
    ``/dev/null``) is rejected. Raises :class:`PatchError` for malformed, empty,
    multi-file, or mismatched patches; the generic multi-file
    :func:`change_dag_patch.parse_unified_diff` is left unchanged for other
    callers.
    """
    patches = parse_unified_diff(node["patch"])
    if len(patches) != 1:
        raise PatchError(
            f"edit node {node_id} must describe exactly one file operation, but its "
            f"patch contains {len(patches)} file sections"
        )
    parsed = patches[0]
    try:
        target = change_dag.canonical_path(parsed.path)
    except ValueError as exc:
        raise PatchError(
            f"edit node {node_id} patch target {parsed.path!r} is not a usable "
            f"workspace-relative path: {exc}"
        ) from exc
    if target != path:
        raise PatchError(
            f"edit node {node_id} patch target {parsed.path!r} does not match "
            f"declared path {path!r}"
        )
    return parsed


def _parse_edit_nodes(
    nodes_map: dict[str, dict], node_ids: list[str], path: str
) -> tuple[list[FilePatch], list[str]]:
    parsed: list[FilePatch] = []
    owners: list[str] = []
    for node_id in node_ids:
        parsed.append(_parse_edit_node_patch(node_id, nodes_map[node_id], path))
        owners.append(node_id)
    return parsed, owners


def _changed_span(hunk) -> tuple[int, int, list[str]] | None:
    """Base-coordinate ``(start, end, new_lines)`` for the lines a hunk changes.

    Context lines only anchor a hunk and are excluded, so two same-frontier peers
    that merely share context are not mistaken for overlapping proposals.
    """
    changed = [index for index, raw in enumerate(hunk.lines) if raw[:1] in {"+", "-"}]
    if not changed:
        return None
    if hunk.old_count == 0:
        # A zero-old-count hunk is a pure insertion anchored *after* original line
        # ``old_start``; it occupies the empty base interval at 0-based index
        # ``old_start`` -- the same coordinate ``apply_file_patch`` inserts at.
        # Anchoring at ``old_start - 1`` would compose one line too high. Such a
        # hunk carries no context/removed lines, so every changed line is an
        # addition.
        anchor = hunk.old_start
        new_lines = [raw[1:] for raw in hunk.lines if raw[:1] == "+"]
        return anchor, anchor, new_lines
    first, last = changed[0], changed[-1]
    base_start = hunk.old_start - 1 + sum(
        1 for raw in hunk.lines[:first] if raw[:1] in {" ", "-"}
    )
    base_end = hunk.old_start - 1 + sum(
        1 for raw in hunk.lines[: last + 1] if raw[:1] in {" ", "-"}
    )
    new_lines = [raw[1:] for raw in hunk.lines[first : last + 1] if raw[:1] in {" ", "+"}]
    return base_start, base_end, new_lines


def _compose_replacements(base: str, replacements: list[tuple[int, int, list[str]]]) -> str:
    """Apply base-coordinate replacements simultaneously (descending, indices hold)."""
    eol = detect_eol(base)
    normalized = normalize_eol(base)
    trailing = normalized.endswith("\n")
    lines = normalized.split("\n")
    if trailing:
        lines = lines[:-1]
    for start, end, new_lines in sorted(
        replacements, key=lambda item: (item[0], item[1]), reverse=True
    ):
        lines[start:end] = new_lines
    result = "\n".join(lines)
    if trailing:
        result += "\n"
    if eol != "\n":
        result = result.replace("\n", eol)
    return result


def _spans_conflict(
    left: tuple[int, int, list[str]], right: tuple[int, int, list[str]]
) -> bool:
    """True when two base-coordinate replacements cannot be composed."""
    left_start, left_end, _left_lines = left
    right_start, right_end, _right_lines = right
    if left_start == left_end and right_start == right_end:
        # Two pure insertions at the same anchor have no defined order.
        return left_start == right_start
    return left_start < right_end and right_start < left_end


def _overlap_components(
    proposals: list[tuple[str, list[tuple[int, int, list[str]]]]],
) -> list[list[str]]:
    """Group peers whose changed spans overlap (one deterministic cluster each)."""
    adjacency: dict[int, set[int]] = {index: set() for index in range(len(proposals))}
    for left in range(len(proposals)):
        for right in range(left + 1, len(proposals)):
            if any(
                _spans_conflict(first, second)
                for first in proposals[left][1]
                for second in proposals[right][1]
            ):
                adjacency[left].add(right)
                adjacency[right].add(left)
    clusters: list[list[str]] = []
    visited: set[int] = set()
    for index in range(len(proposals)):
        if index in visited or not adjacency[index]:
            continue
        stack = [index]
        members: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            members.append(proposals[current][0])
            stack.extend(sorted(adjacency[current] - visited))
        clusters.append(sorted(members, key=change_dag._numeric_id))
    clusters.sort(key=lambda group: change_dag._numeric_id(group[0]))
    return clusters


def _reconcile_frontier_edits(
    base: str,
    edit_nodes: list[str],
    nodes_map: dict[str, dict],
    depths: dict[str, int],
    path: str,
    *,
    base_is_authored: bool,
    base_nodes: list[str] | None = None,
) -> tuple[str, list[tuple[list[str], str, str]]]:
    """Interpret same-frontier peer proposals against one base, then reconcile.

    Frontiers are the construction depths already used by ``execution_order``.
    Deeper frontiers are accepted first and transform ``base``; every peer of the
    *same* frontier is then interpreted against that identical accepted-lower
    state, never against a peer's output. Non-overlapping peer changes compose
    simultaneously, so numerical node IDs never become causality.

    ``base_is_authored`` marks a base produced by this DAG (a ``create`` content
    or an earlier segment's result) rather than the live repository, which is
    what separates a deterministic contradiction from ordinary live drift.
    Returns ``(reconciled_text, problems)`` where each problem is
    ``(nodes, reason, scope)``.
    """
    problems: list[tuple[list[str], str, str]] = []
    frontiers: dict[int, list[str]] = {}
    for node_id in edit_nodes:
        frontiers.setdefault(depths.get(node_id) or 0, []).append(node_id)

    def applies_to(text: str, peer: str) -> bool:
        """True when ``peer`` applies cleanly to ``text`` (parse + exact apply)."""
        try:
            file_patch = _parse_edit_node_patch(peer, nodes_map[peer], path)
            apply_file_patch(text, file_patch, path=path)
        except PatchError:
            return False
        return True

    current = base
    # Provenance of the content a failing hunk is compared against. ``base`` is
    # DAG-produced when it is a create's content or an earlier segment's result
    # (``base_is_authored``); deeper frontiers accepted inside this call also
    # transform ``current``. Only a failure attributable to such accepted
    # DAG-produced content is a deterministic contradiction -- a failure against
    # pure live content is ordinary recoverable drift, regardless of which hunk
    # failed. ``contributors`` names the accepted work reflected in ``current``.
    contributors: list[str] = list(base_nodes or [])
    transformed = False
    for depth in sorted(frontiers, reverse=True):
        before = len(problems)
        peers = frontiers[depth]
        applied: list[tuple[str, list[tuple[int, int, list[str]]]]] = []
        failed: list[tuple[str, Exception]] = []
        for peer in peers:
            try:
                parsed = [_parse_edit_node_patch(peer, nodes_map[peer], path)]
            except PatchError as exc:
                failed.append((peer, exc))
                continue
            probe = current
            try:
                for file_patch in parsed:
                    probe = apply_file_patch(probe, file_patch, path=path)
            except PatchError as exc:
                failed.append((peer, exc))
                continue
            spans: list[tuple[int, int, list[str]]] = []
            for file_patch in parsed:
                for hunk in file_patch.hunks:
                    span = _changed_span(hunk)
                    if span is not None:
                        spans.append(span)
            applied.append((peer, spans))

        if failed and applied:
            # A peer that fails against the shared accepted state but applies to
            # peer output is attempting a same-frontier dependency.
            peer_output = _compose_replacements(
                current, [span for _peer, spans in applied for span in spans]
            )
            resolved: set[str] = set()
            for peer, exc in failed:
                if not isinstance(exc, PatchContextError):
                    continue
                try:
                    probe = peer_output
                    for file_patch in [_parse_edit_node_patch(peer, nodes_map[peer], path)]:
                        probe = apply_file_patch(probe, file_patch, path=path)
                except PatchError:
                    continue
                problems.append((
                    [peer, *[other for other, _spans in applied]],
                    f"context_conflict: {peer} requires content produced by same-frontier "
                    f"peer work in {path}",
                    "intra_dag",
                ))
                resolved.add(peer)
            failed = [item for item in failed if item[0] not in resolved]

        for peer, exc in failed:
            if isinstance(exc, PatchContextError):
                # Intra-DAG only when the content the hunk failed against is
                # DAG-produced: the base itself is authored, or a deeper frontier
                # transformed ``current`` into content this peer cannot consume
                # while it still applies to the pristine base (so the
                # transformation caused the mismatch). A later hunk index alone
                # proves nothing about provenance.
                dag_produced = base_is_authored or (
                    transformed and applies_to(base, peer)
                )
                if not dag_produced:
                    problems.append(([peer], f"context_conflict: {exc.message}", "runtime"))
                    continue
                attribution = [peer, *contributors]
                if contributors:
                    message = (
                        f"context_conflict: {peer} does not apply to the content produced by "
                        f"{', '.join(contributors)} for {path}: {exc.message}"
                    )
                elif base_is_authored:
                    message = (
                        f"context_conflict: {peer} does not apply to the content produced by "
                        f"earlier DAG work for {path}: {exc.message}"
                    )
                else:  # pragma: no cover - dag_produced implies a contributor
                    message = (
                        f"context_conflict: {peer} does not apply to the accepted lower state "
                        f"for {path}: {exc.message}"
                    )
                problems.append((attribution, message, "intra_dag"))
            else:
                problems.append(([peer], f"compile_conflict: malformed patch: {exc}", "intra_dag"))

        for cluster in _overlap_components(applied):
            problems.append((
                cluster,
                f"context_conflict: same-frontier peers {cluster} modify overlapping "
                f"source in {path}",
                "intra_dag",
            ))

        if len(problems) == before and applied:
            current = _compose_replacements(
                current, [span for _peer, spans in applied for span in spans]
            )
            contributors.extend(peer for peer, _spans in applied)
            transformed = True
    return current, problems


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


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------
def compile_operations(
    dag: dict,
    state: dict,
    workspace_root: Path,
    *,
    repo: "_RepoView | None" = None,
    include_nodes: set[str] | None = None,
) -> tuple[list[CompiledOp], list[Conflict], list[Blocked]]:
    """Lower currently reachable mechanical work into per-path operations.

    Nodes are grouped by :func:`change_dag.canonical_path`, so spellings that
    name the same file (``foo.py``, ``./foo.py``, ``src/../foo.py``) coordinate
    as one path instead of compiling independently and colliding at application.

    ``repo`` defaults to a live read-only view of ``workspace_root``. Whole-DAG
    preflight passes a simulated overlay so higher work is lowered against the
    in-memory result of accepted lower work rather than the live files.

    ``include_nodes`` restricts lowering to an explicit mechanical node set and
    bypasses run-barrier gating. Only the construction-frontier authoring view
    (:func:`compile_lower_work`) uses it: a construction frontier is an
    authoring/context boundary, so execution run barriers never gate it.
    Runtime and preflight compilation leave it ``None``.
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

    conflicts.sort(key=lambda conflict: (conflict.path, conflict.reason, conflict.nodes))
    blocked.sort(key=lambda entry: change_dag._numeric_id(entry.node_id))
    return ops, conflicts, blocked


def _apply_simulated(repo: _RepoView, op: CompiledOp) -> None:
    """Apply a compiled op to the in-memory overlay; the repository is untouched."""
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


def compile_whole_dag(
    dag: dict, state: dict, workspace_root: Path
) -> tuple[list[list[CompiledOp]], list[Conflict], list[Blocked]]:
    """Deterministically lower *all* currently specified terminal work.

    Runtime compilation is segmented: it stops at the next unsatisfied run
    barrier and resumes only after that run actually succeeds, so a single
    state-aware pass only sees the first executable segment. Preflight must
    instead answer whether *all* currently specified work lowers without an
    internal compiler/patch contradiction, so this simulates deterministic
    mechanical progression entirely in memory:

    * compile the current execution phase against the simulated overlay;
    * fold accepted mechanical results into the overlay and mark their nodes
      satisfied;
    * assume every run barrier whose requirements are now met succeeds, then
      advance the execution phase and continue lowering the work that becomes
      reachable above it.

    No repository write, projected worktree, or command execution happens here.
    Live-repository applicability mismatches stay ``scope="runtime"``;
    contradictions against content the DAG itself produced are deterministic.
    Returns the per-execution-phase ops, including empty phases crossed only by
    simulated run frontiers, the deduplicated conflicts found across every
    phase, and the work still gated once progression stops. Execution phase is
    deliberately separate from construction depth/frontier.
    """
    effective_state = dict(state) if isinstance(state, dict) else {}
    overlay: dict[str, str] = {}
    removed: set[str] = set()
    repo = _RepoView(workspace_root, overlay, removed)

    # Validate authored shape/policy before lowering. Mark malformed terminals
    # failed only in this private simulation so compile_operations cannot crash
    # on missing fields or replay invalid work; the authored defects remain
    # deterministic conflicts and valid unrelated work can still be simulated.
    authored_conflicts = _authored_shape_conflicts(dag)
    authored_invalid = {node for conflict in authored_conflicts for node in conflict.nodes}
    for node_id in authored_invalid:
        effective_state[node_id] = "failed"

    execution_phases: list[list[CompiledOp]] = []
    conflicts: list[Conflict] = []
    blocked: list[Blocked] = []
    seen: set[tuple] = set()
    for conflict in authored_conflicts:
        key = (conflict.path, conflict.reason, tuple(conflict.nodes), conflict.scope)
        seen.add(key)
        conflicts.append(conflict)

    limit = len(change_dag.node_map(dag)) + 2
    for _ in range(limit):
        phase_ops, phase_conflicts, blocked = compile_operations(
            dag, effective_state, workspace_root, repo=repo
        )
        for conflict in phase_conflicts:
            key = (conflict.path, conflict.reason, tuple(conflict.nodes), conflict.scope)
            if key not in seen:
                seen.add(key)
                conflicts.append(conflict)

        if phase_ops:
            for op in phase_ops:
                _apply_simulated(repo, op)
                for node_id in op.nodes:
                    effective_state[node_id] = "satisfied"

        ready = [
            node_id
            for node_id in ready_run_nodes(dag, effective_state, workspace_root)
            if effective_state.get(node_id) != "satisfied"
        ]

        # Preserve a phase even when its only progress is crossing a run
        # frontier. Otherwise later mechanical work is incorrectly relabelled
        # as phase 0 when callers derive its phase from non-empty batches.
        progressed = bool(phase_ops or ready)
        if progressed:
            execution_phases.append(phase_ops)

        if ready:
            for node_id in ready:
                effective_state[node_id] = "satisfied"

        if not progressed:
            break

    conflicts.sort(key=lambda conflict: (conflict.path, conflict.reason, conflict.nodes))
    blocked.sort(key=lambda entry: change_dag._numeric_id(entry.node_id))
    return execution_phases, conflicts, blocked


def lower_work_frontiers(dag: Any) -> dict[str, int]:
    """Construction-frontier depth of every mechanical node.

    A mechanical node's frontier is the longest-path derived depth of the
    semantic node(s) it directly satisfies -- the construction layer that
    owned it. Deepest-frontier work is authored first, so same-frontier peers
    share a frontier depth regardless of numerical node ID or persistence order.
    Unparented mechanical nodes (unreachable or malformed) are omitted.
    """
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


def compile_lower_work(
    dag: dict, workspace_root: Path, boundary_depth: int, *, state: dict | None = None
) -> tuple[list[CompiledOp], list[Conflict], dict[str, str], set[str]]:
    """Lower mechanical work strictly below a construction frontier boundary.

    A construction frontier is an authoring/context boundary, deliberately
    distinct from a run barrier. Exact work authored for one frontier shares one
    accepted-lower-work base: for a semantic boundary at ``boundary_depth``,
    mechanical work whose own frontier (:func:`lower_work_frontiers`) is
    strictly deeper is accepted context, while work at the boundary's own depth
    -- the current node's own proposal and every same-frontier peer proposal --
    and shallower/future work are excluded. Longest-path depth, convergence, and
    shared descendants are preserved; a shared deeper node contributes once.

    Everything lowers deepest-frontier-first into an in-memory overlay. Run
    barriers never gate this view (they are execution boundaries), nothing is
    written, and no command runs. Returns ``(ops, conflicts, overlay, removed)``,
    where ``overlay`` maps written paths to their effective lower-work content
    and ``removed`` names paths lower work deleted.

    ``state`` (optional) is Execution State. Already-``satisfied`` lower work is
    represented in the live source and must not be re-projected; failed or
    not-yet-applied lower work remains legitimate accepted context. Callers that
    omit ``state`` keep the previous all-work projection behaviour.
    """
    nodes = change_dag.node_map(dag)
    frontiers = lower_work_frontiers(dag)
    include = {
        node_id for node_id, frontier in frontiers.items() if frontier > boundary_depth
    }

    # Seed already-satisfied lower work as accepted-but-applied: live content
    # already reflects it, so re-projecting it would duplicate its effect.
    effective_state: dict[str, str] = {
        node_id: node_state
        for node_id, node_state in (state.items() if isinstance(state, dict) else ())
        if node_state == "satisfied"
    }
    overlay: dict[str, str] = {}
    removed: set[str] = set()
    repo = _RepoView(workspace_root, overlay, removed)
    ordered_ops: list[CompiledOp] = []
    conflicts: list[Conflict] = []
    seen: set[tuple] = set()

    limit = len(nodes) + 2
    for _ in range(limit):
        ops, phase_conflicts, _blocked = compile_operations(
            dag, effective_state, workspace_root, repo=repo, include_nodes=include
        )
        for conflict in phase_conflicts:
            key = (conflict.path, conflict.reason, tuple(conflict.nodes), conflict.scope)
            if key not in seen:
                seen.add(key)
                conflicts.append(conflict)
        if not ops:
            break
        for op in ops:
            _apply_simulated(repo, op)
            ordered_ops.append(op)
            for node_id in op.nodes:
                effective_state[node_id] = "satisfied"

    conflicts.sort(key=lambda conflict: (conflict.path, conflict.reason, conflict.nodes))
    return ordered_ops, conflicts, overlay, removed


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
def apply_compiled(ops: list[CompiledOp], workspace_root: Path) -> list[dict]:
    """Apply compiled ops atomically, re-verifying against current live state."""
    workspace_root = Path(workspace_root)
    results: list[dict] = []

    def evidence(op: CompiledOp) -> dict:
        extra: dict = {}
        if op.patch_text is not None:
            extra["patch"] = op.patch_text
        if op.content is not None:
            extra["content"] = op.content
        if op.op == "move":
            extra["from_path"] = op.from_path
            extra["to_path"] = op.to_path
            extra["overwrite"] = bool(op.overwrite)
        return extra

    def failure(op: CompiledOp, error: str, message: str = "") -> dict:
        entry = {"path": op.path, "nodes": list(op.nodes), "ok": False,
                 "action": op.op, "error": error}
        entry.update(evidence(op))
        if message:
            entry["message"] = message
        return entry

    for op in ops:
        if op.op == "create":
            path = workspace_root / op.path
            if path.exists() or path.is_symlink():
                results.append(failure(op, "context_mismatch"))
                continue
            try:
                atomic_replace(path, (op.content or "").encode("utf-8"))
            except OSError as exc:
                results.append(failure(op, "io_error", str(exc)))
                continue
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "create", **evidence(op)})
        elif op.op == "edit":
            path = workspace_root / op.path
            if op.base_text is not None:
                # A reconciled frontier: re-verify the exact accepted base rather
                # than replaying peer patches in numeric order.
                try:
                    current = read_text_preserving(path)
                except PatchError:
                    results.append(failure(op, "context_mismatch"))
                    continue
                if current != op.base_text:
                    results.append(failure(op, "context_mismatch"))
                    continue
                updated = op.applied if op.applied is not None else current
            else:
                try:
                    current = read_text_preserving(path)
                    updated = apply_patches(current, op.patches or [], path=op.path)
                except PatchError:
                    results.append(failure(op, "context_mismatch"))
                    continue
            try:
                atomic_replace(path, updated.encode("utf-8"))
            except OSError as exc:
                results.append(failure(op, "io_error", str(exc)))
                continue
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "edit", **evidence(op)})
        elif op.op == "remove":
            path = workspace_root / op.path
            try:
                if path.exists() or path.is_symlink():
                    path.unlink()
            except OSError as exc:
                results.append(failure(op, "io_error", str(exc)))
                continue
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "remove", **evidence(op)})
        elif op.op == "move":
            source = workspace_root / (op.from_path or "")
            destination = workspace_root / (op.to_path or "")
            if not source.is_file():
                results.append(failure(op, "context_mismatch"))
                continue
            if not op.overwrite and (destination.exists() or destination.is_symlink()):
                results.append(failure(op, "context_mismatch"))
                continue
            try:
                # One native filesystem rename. No shell `mv`, no copy+unlink,
                # and no cross-filesystem emulation: if the filesystem cannot
                # perform the rename atomically the operation fails normally.
                if op.overwrite:
                    os.replace(source, destination)
                else:
                    os.rename(source, destination)
            except OSError as exc:
                results.append(failure(op, "io_error", str(exc)))
                continue
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "move", **evidence(op)})
    return results


# ---------------------------------------------------------------------------
# Run frontier
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
def preflight(dag: dict, state: dict, workspace_root: Path) -> dict:
    """Derived pre-execution conflict/applicability check.

    Only deterministic *intra-DAG* conflicts (structure errors, conflicting
    operations authored into this DAG, malformed patches, creates that collide
    with each other) make the DAG non-executable. Live-repository applicability
    mismatches — a patch that no longer applies because the repository drifted,
    an edit target another work item removed, a create target another work item
    created — are reported as ``runtime_failures`` and handled as ordinary
    recoverable terminal-node failures when reached. Unresolved semantic leaves,
    a dirty tree, HEAD drift, and blocked branch-local work are not issues.

    ``executable`` is answered by :func:`compile_whole_dag`: it reflects whether
    *all* currently specified work lowers deterministically, not merely the first
    execution segment before the next unsatisfied run barrier.
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

    try:
        _segments, conflicts, blocked = compile_whole_dag(dag, state, workspace_root)
    except Exception as exc:  # pragma: no cover - defensive
        issues.append({"kind": "compile_conflict", "message": f"compilation failed: {exc}"})
        return {"executable": False, "issues": issues, "runtime_failures": [], "conflicts": [], "blocked": []}

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


# ---------------------------------------------------------------------------
# Reconciliation and summary
# ---------------------------------------------------------------------------
def _already_applied(current: str, patches: list[FilePatch]) -> bool:
    """True only with exact proof that ``current`` is the patches' intended result.

    Interruption reconciliation must never conclude that an interrupted edit
    succeeded without proof, so the previous "no new-side lines matched" vacuous
    success is replaced by an exact region comparison:

    * Each hunk's *new side* (context ``' '`` and added ``'+'`` lines) must match
      ``current`` contiguously. Because the region is exactly the new side, a
      replaced/removed line cannot remain inside it.
    * The position of that region in the resulting file is the hunk's F4 target:
      ``old_start - 1`` plus the accumulated ``new_count - old_count`` delta of
      the earlier hunks for a hunk that removes or keeps content, and
      ``old_start`` plus that delta for a zero-``old_count`` insertion -- the same
      coordinate :func:`change_dag_patch.apply_file_patch` writes to. It is never
      ``new_start - 1`` plus that delta, which double-counts the delta when a
      patch already carries resulting-file starts.
    * A deletion-only hunk has no new-side line to anchor the proof, so it can
      never, by itself, make the patch "applied"; the file stays ambiguous.

    Partial application, an overlapping external edit, or a wrong coordinate all
    fail the exact comparison and therefore classify as ambiguous upstream.
    """
    text = change_dag_patch.normalize_eol(current)
    lines = text.split("\n")
    if text.endswith("\n"):
        lines = lines[:-1]
    offset = 0
    proven = False
    for file_patch in patches:
        for hunk in file_patch.hunks:
            position = (
                hunk.old_start + offset
                if hunk.old_count == 0
                else hunk.old_start - 1 + offset
            )
            new_lines = [raw[1:] for raw in hunk.lines if raw[:1] in (" ", "+")]
            if position < 0 or position + len(new_lines) > len(lines):
                return False
            if lines[position : position + len(new_lines)] != new_lines:
                return False
            if new_lines:
                proven = True
            elif any(raw[:1] == "-" for raw in hunk.lines):
                # No new-side line exists to prove the intended result, and the
                # removed content is gone from view: not provably applied.
                return False
            offset += hunk.new_count - hunk.old_count
    return proven


def source_fingerprint(path: Path) -> dict[str, Any] | None:
    """Small content fingerprint of a move source, or ``None`` when unreadable.

    Operation-local recovery evidence only: it identifies the intended moved
    file across an interruption. It is not a provenance registry, snapshot
    store, or ownership record, and it never replaces the native rename.
    """
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    return {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def _move_outcome(node: dict, workspace_root: Path, fingerprint: dict | None, *, require_fingerprint: bool = False) -> str:
    """Conservatively classify an interrupted move from live path state."""
    source = workspace_root / str(node.get("from_path", ""))
    destination = workspace_root / str(node.get("to_path", ""))
    overwrite = bool(node.get("overwrite", False))
    from_exists = source.exists()
    to_exists = destination.exists() or destination.is_symlink()
    if from_exists and to_exists:
        # The source survived and something occupies the destination: nothing
        # here proves the rename happened.
        return "ambiguous"
    if from_exists:
        return "absent"
    if not to_exists:
        return "ambiguous"
    if fingerprint is not None:
        return "present" if source_fingerprint(destination) == fingerprint else "ambiguous"
    # Without recorded evidence, interruption reconciliation must not infer that
    # an occupied destination came from this move. The legacy node_present query
    # remains permissive for non-overwriting moves when no recovery evidence was
    # requested; the executor passes require_fingerprint=True during recovery.
    if require_fingerprint:
        return "ambiguous"
    return "ambiguous" if overwrite else "present"


def node_present(dag: dict, node_id: str, workspace_root: Path, *, fingerprint: dict | None = None, require_fingerprint: bool = False) -> str:
    """Classify a mechanical node against live state: present/absent/ambiguous.

    ``fingerprint`` is a move node's recorded pre-rename source fingerprint
    (see :func:`source_fingerprint`). When supplied, a destination only proves a
    move when its content matches, so reconciliation never claims a move merely
    because an unrelated file sits at the destination.
    """
    workspace_root = Path(workspace_root)
    node = change_dag.node_map(dag).get(node_id)
    if not isinstance(node, dict):
        return "ambiguous"
    kind = node.get("type")
    if kind == "create":
        path = workspace_root / str(node.get("path", ""))
        if not path.exists():
            return "absent"
        try:
            text = read_text_preserving(path)
        except PatchError:
            return "ambiguous"
        return "present" if text == node.get("content", "") else "ambiguous"
    if kind == "edit":
        path = workspace_root / str(node.get("path", ""))
        try:
            current = read_text_preserving(path)
            patches = parse_unified_diff(str(node.get("patch", "")))
        except PatchError:
            return "ambiguous"
        try:
            updated = apply_patches(current, patches, path=str(node.get("path", "")))
        except PatchContextError:
            return "present" if _already_applied(current, patches) else "ambiguous"
        except PatchError:
            return "ambiguous"
        if updated == current:
            return "present"
        if _already_applied(current, patches):
            # The new side is present, yet the patch still applies (an insertion
            # whose added content cannot be told apart from the pre-existing
            # file). It is neither provably applied nor provably safe to re-apply.
            return "ambiguous"
        return "absent"
    if kind == "remove":
        path = workspace_root / str(node.get("path", ""))
        return "present" if not path.exists() else "absent"
    if kind == "move":
        return _move_outcome(node, workspace_root, fingerprint, require_fingerprint=require_fingerprint)
    return "ambiguous"


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
