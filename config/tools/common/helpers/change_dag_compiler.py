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
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import change_dag
from . import change_dag_patch
from .change_dag_patch import (
    FilePatch,
    PatchContextError,
    PatchError,
    apply_patches,
    atomic_replace,
    parse_unified_diff,
    read_text_preserving,
)

__all__ = [
    "CompiledOp",
    "Conflict",
    "Blocked",
    "compile_operations",
    "compile_whole_dag",
    "apply_compiled",
    "ready_run_nodes",
    "preflight",
    "node_present",
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

    ancestor_barrier: dict[str, str] = {}
    barrier_depth: dict[str, int] = {}
    for node_id, node in nodes.items():
        if node.get("type") != "run" or satisfaction.get(node_id, False):
            continue
        for parent in parents.get(node_id, ()):
            parent_depth = depth.get(parent, 0)
            for ancestor in change_dag.ancestor_map(dag).get(parent, set()):
                if ancestor not in ancestor_barrier:
                    ancestor_barrier[ancestor] = node_id
                    barrier_depth[ancestor] = parent_depth
    if not ancestor_barrier:
        return {}

    gated: dict[str, str] = {}
    for node_id in nodes:
        if change_dag.node_type(dag, node_id) not in MECHANICAL_TYPES:
            continue
        if effective.get(node_id) in {"satisfied", "failed"}:
            continue
        node_depth = depth.get(node_id, 0)
        for parent in parents.get(node_id, ()):
            barrier = ancestor_barrier.get(parent)
            if barrier is not None and node_depth < barrier_depth.get(parent, 0):
                gated[node_id] = barrier
                break
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


def _parse_edit_nodes(
    nodes_map: dict[str, dict], node_ids: list[str]
) -> tuple[list[FilePatch], list[str]]:
    parsed: list[FilePatch] = []
    owners: list[str] = []
    for node_id in node_ids:
        node_patches = parse_unified_diff(nodes_map[node_id]["patch"])
        parsed.extend(node_patches)
        owners.extend([node_id] * len(node_patches))
    return parsed, owners


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------
def compile_operations(
    dag: dict,
    state: dict,
    workspace_root: Path,
    *,
    repo: "_RepoView | None" = None,
) -> tuple[list[CompiledOp], list[Conflict], list[Blocked]]:
    """Lower currently reachable mechanical work into per-path operations.

    ``repo`` defaults to a live read-only view of ``workspace_root``. Whole-DAG
    preflight passes a simulated overlay so higher work is lowered against the
    in-memory result of accepted lower work rather than the live files.
    """
    effective_state = state if isinstance(state, dict) else {}
    workspace_root = Path(workspace_root)
    view = repo if repo is not None else _RepoView(workspace_root)
    order_index = _order_index(dag)
    order_key = _node_sort_key(order_index)

    mechanical, blocked = _actionable_mechanical(dag, effective_state)
    nodes_map = change_dag.node_map(dag)

    creates: dict[str, list[str]] = {}
    edits: dict[str, list[str]] = {}
    removes: dict[str, list[str]] = {}
    moves: list[tuple[str, str, str]] = []
    for node_id in mechanical:
        node = nodes_map[node_id]
        kind = node["type"]
        if kind == "create":
            creates.setdefault(node["path"], []).append(node_id)
        elif kind == "edit":
            edits.setdefault(node["path"], []).append(node_id)
        elif kind == "remove":
            removes.setdefault(node["path"], []).append(node_id)
        elif kind == "move":
            moves.append((node_id, node["from_path"], node["to_path"]))

    conflicts: list[Conflict] = []
    conflicted: set[str] = set()

    def add_conflict(path: str, nodes: list[str], reason: str, scope: str = "intra_dag") -> None:
        unique = sorted(set(nodes), key=order_key)
        conflicts.append(Conflict(path=path, nodes=unique, reason=reason, scope=scope))
        conflicted.update(unique)

    def group_ok(nodes: list[str]) -> bool:
        return not any(node_id in conflicted for node_id in nodes)

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
    for node_id, from_path, to_path in moves:
        move_sources.setdefault(from_path, []).append(node_id)
        move_dests.setdefault(to_path, []).append(node_id)
    for node_id, from_path, to_path in moves:
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
        if view.exists(to_path):
            if view.is_dag_written(to_path):
                add_conflict(from_path, [node_id],
                             "compile_conflict: move destination was already produced by earlier DAG work")
            else:
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

    # --- create / edit groups (create supplies the base content) ---
    for path in sorted(set(creates) | set(edits)):
        group = sorted(set(creates.get(path, []) + edits.get(path, [])), key=order_key)
        if not group_ok(group):
            continue
        edit_nodes = sorted(edits.get(path, []), key=order_key)
        patch_text = "".join(nodes_map[node]["patch"] for node in edit_nodes)
        if path in creates:
            base = nodes_map[creates[path][0]]["content"]
            try:
                parsed, _owners = _parse_edit_nodes(nodes_map, edit_nodes)
                content = apply_patches(base, parsed, path=path) if parsed else base
            except PatchContextError as exc:
                add_conflict(path, group, f"context_conflict: {exc.message}")
                continue
            except PatchError as exc:
                add_conflict(path, group, f"compile_conflict: malformed patch: {exc}")
                continue
            ops.append(CompiledOp(nodes=group, op="create", path=path, content=content,
                                  patch_text=patch_text or None, applied=content))
        else:
            try:
                parsed, owners = _parse_edit_nodes(nodes_map, edit_nodes)
            except PatchError as exc:
                add_conflict(path, group, f"compile_conflict: malformed patch: {exc}")
                continue
            try:
                live = view.read(path)
                updated = apply_patches(live, parsed, path=path)
            except PatchContextError as exc:
                if exc.hunk_index == 0 and not view.is_dag_written(path):
                    # The first authored patch is checked against the live file;
                    # a mismatch here is ordinary recoverable live drift.
                    add_conflict(path, group, f"context_conflict: {exc.message}", scope="runtime")
                else:
                    failing = owners[exc.hunk_index]
                    prior = list(dict.fromkeys(owners[:exc.hunk_index]))
                    if view.is_dag_written(path) and not prior:
                        reason = (
                            f"context_conflict: {failing} does not apply to the content "
                            f"produced by earlier DAG work for {path}: {exc.message}"
                        )
                    else:
                        reason = (
                            f"context_conflict: {failing} does not apply after prior same-file "
                            f"DAG edit(s) {prior}: {exc.message}"
                        )
                    add_conflict(path, prior + [failing], reason)
                continue
            except PatchError as exc:
                add_conflict(path, group, f"runtime_context: cannot read target: {exc}", scope="runtime")
                continue
            ops.append(CompiledOp(nodes=group, op="edit", path=path, patches=parsed,
                                  patch_text=patch_text or None, applied=updated))

    # --- removes ---
    for path in sorted(removes):
        group = sorted(removes[path], key=order_key)
        if not group_ok(group):
            continue
        ops.append(CompiledOp(nodes=group, op="remove", path=path))

    # --- moves ---
    for node_id, from_path, to_path in sorted(moves, key=lambda item: (item[1], item[2])):
        if node_id in conflicted:
            continue
        ops.append(CompiledOp(nodes=[node_id], op="move", path=from_path,
                              from_path=from_path, to_path=to_path))

    rank = {"create": 0, "edit": 1, "move": 2, "remove": 3}
    ops.sort(key=lambda compiled: (compiled.path, rank.get(compiled.op, 9)))

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

    * compile the current segment against the simulated overlay;
    * fold accepted mechanical results into the overlay and mark their nodes
      satisfied;
    * assume every run barrier whose requirements are now met succeeds, then
      continue lowering the work that becomes reachable above it.

    No repository write, projected worktree, or command execution happens here.
    Live-repository applicability mismatches stay ``scope="runtime"``;
    contradictions against content the DAG itself produced are deterministic.
    Returns the per-segment ops, the deduplicated conflicts found across every
    segment, and the work still gated once progression stops.
    """
    effective_state = dict(state) if isinstance(state, dict) else {}
    overlay: dict[str, str] = {}
    removed: set[str] = set()
    repo = _RepoView(workspace_root, overlay, removed)

    segments: list[list[CompiledOp]] = []
    conflicts: list[Conflict] = []
    blocked: list[Blocked] = []
    seen: set[tuple] = set()

    limit = len(change_dag.node_map(dag)) + 2
    for _ in range(limit):
        segment_ops, segment_conflicts, blocked = compile_operations(
            dag, effective_state, workspace_root, repo=repo
        )
        for conflict in segment_conflicts:
            key = (conflict.path, conflict.reason, tuple(conflict.nodes), conflict.scope)
            if key not in seen:
                seen.add(key)
                conflicts.append(conflict)

        progressed = False
        if segment_ops:
            for op in segment_ops:
                _apply_simulated(repo, op)
                for node_id in op.nodes:
                    effective_state[node_id] = "satisfied"
            segments.append(segment_ops)
            progressed = True

        ready = [
            node_id
            for node_id in ready_run_nodes(dag, effective_state, workspace_root)
            if effective_state.get(node_id) != "satisfied"
        ]
        if ready:
            for node_id in ready:
                effective_state[node_id] = "satisfied"
            progressed = True

        if not progressed:
            break

    conflicts.sort(key=lambda conflict: (conflict.path, conflict.reason, conflict.nodes))
    blocked.sort(key=lambda entry: change_dag._numeric_id(entry.node_id))
    return segments, conflicts, blocked


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
            if destination.exists() or destination.is_symlink():
                results.append(failure(op, "context_mismatch"))
                continue
            try:
                data = source.read_bytes()
                atomic_replace(destination, data)
                source.unlink()
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
    """True when the patches' new-side lines are present and match in order."""
    text = change_dag_patch.normalize_eol(current)
    lines = text.split("\n")
    if text.endswith("\n"):
        lines = lines[:-1]
    offset = 0
    for file_patch in patches:
        for hunk in file_patch.hunks:
            position = hunk.new_start - 1 + offset
            for raw in hunk.lines:
                marker = raw[:1]
                content = raw[1:]
                if marker in (" ", "+"):
                    if position >= len(lines) or lines[position] != content:
                        return False
                    position += 1
            offset += hunk.new_count - hunk.old_count
    return True


def node_present(dag: dict, node_id: str, workspace_root: Path) -> str:
    """Classify a mechanical node against live state: present/absent/ambiguous."""
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
        return "present" if updated == current else "absent"
    if kind == "remove":
        path = workspace_root / str(node.get("path", ""))
        return "present" if not path.exists() else "absent"
    if kind == "move":
        source = workspace_root / str(node.get("from_path", ""))
        destination = workspace_root / str(node.get("to_path", ""))
        from_exists = source.exists()
        to_exists = destination.exists()
        if not from_exists and to_exists:
            return "present"
        if from_exists:
            return "absent"
        return "ambiguous"
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
