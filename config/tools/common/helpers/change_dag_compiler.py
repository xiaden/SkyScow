"""Deterministic Change DAG compiler shared by ``dag_preview`` and execution.

The compiler lowers the declarative DAG plus Execution State into concrete
per-file operations against the *live* repository. It never creates a projected
worktree and never writes; only :func:`apply_compiled` writes, and only through
the atomic per-file primitive in :mod:`change_dag_patch`.

Graph semantics are single-sourced from :mod:`change_dag`
(``execution_order``, ``derived_satisfaction``, reachability, node typing).
Failure is branch-local: a mechanical node is only *blocked* when a sibling
subtree has actually failed, which prevents harmless pending/unresolved
branches from stalling independent work.
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


@dataclass
class Conflict:
    path: str
    nodes: list[str]
    reason: str


@dataclass
class Blocked:
    node_id: str
    reason: str


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


def _blocked_reason(dag: Any, state: dict[str, str], node_id: str) -> str | None:
    """Return a branch-local blocked reason, or ``None`` when progressable."""
    ancestors = change_dag.ancestor_map(dag).get(node_id, set())
    path_set = set(ancestors) | {node_id}
    for ancestor in sorted(ancestors, key=change_dag._numeric_id):
        if change_dag.node_type(dag, ancestor) != change_dag.SEMANTIC_TYPE:
            continue
        for sibling in change_dag.direct_children(dag, ancestor):
            if sibling in path_set:
                continue
            if _subtree_failed(dag, state, sibling):
                return f"ancestor {ancestor} has failed sibling branch {sibling}"
    return None


def _actionable_mechanical(dag: Any, state: dict[str, str]) -> tuple[list[str], list[Blocked]]:
    reachable = change_dag.reachable_from_root(dag)
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
        reason = _blocked_reason(dag, state, node_id)
        if reason is not None:
            blocked.append(Blocked(node_id=node_id, reason=reason))
            continue
        actionable.append(node_id)
    return actionable, blocked


def _parse_edit_nodes(nodes_map: dict[str, dict], node_ids: list[str]) -> list[FilePatch]:
    parsed: list[FilePatch] = []
    for node_id in node_ids:
        parsed.extend(parse_unified_diff(nodes_map[node_id]["patch"]))
    return parsed


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------
def compile_operations(
    dag: dict, state: dict, workspace_root: Path
) -> tuple[list[CompiledOp], list[Conflict], list[Blocked]]:
    """Lower reachable mechanical work into per-path operations (no writes)."""
    effective_state = state if isinstance(state, dict) else {}
    workspace_root = Path(workspace_root)
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

    def add_conflict(path: str, nodes: list[str], reason: str) -> None:
        unique = sorted(set(nodes), key=order_key)
        conflicts.append(Conflict(path=path, nodes=unique, reason=reason))
        conflicted.update(unique)

    def group_ok(nodes: list[str]) -> bool:
        return not any(node_id in conflicted for node_id in nodes)

    # --- same-path create/edit/remove coordination ---
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
        if (workspace_root / path).exists():
            add_conflict(path, nodes, "compile_conflict: create target already exists")
    for path, nodes in edits.items():
        if path not in creates and not (workspace_root / path).is_file():
            add_conflict(path, nodes, "compile_conflict: edit target does not exist")

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
        if from_path not in creates and not (workspace_root / from_path).is_file():
            add_conflict(from_path, move_sources[from_path],
                         "compile_conflict: move source does not exist")
        if (workspace_root / to_path).exists():
            add_conflict(from_path, [node_id],
                         "compile_conflict: move destination already exists")
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
        if path in creates:
            base = nodes_map[creates[path][0]]["content"]
            try:
                parsed = _parse_edit_nodes(nodes_map, edit_nodes)
                content = apply_patches(base, parsed, path=path) if parsed else base
            except PatchContextError as exc:
                add_conflict(path, group, f"context_conflict: {exc.message}")
                continue
            except PatchError as exc:
                add_conflict(path, group, f"compile_conflict: malformed patch: {exc}")
                continue
            ops.append(CompiledOp(nodes=group, op="create", path=path, content=content))
        else:
            try:
                parsed = _parse_edit_nodes(nodes_map, edit_nodes)
            except PatchError as exc:
                add_conflict(path, group, f"compile_conflict: malformed patch: {exc}")
                continue
            try:
                live = read_text_preserving(workspace_root / path)
                apply_patches(live, parsed, path=path)
            except PatchContextError as exc:
                add_conflict(path, group, f"context_conflict: {exc.message}")
                continue
            except PatchError as exc:
                add_conflict(path, group, f"compile_conflict: cannot read target: {exc}")
                continue
            ops.append(CompiledOp(nodes=group, op="edit", path=path, patches=parsed))

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


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
def apply_compiled(ops: list[CompiledOp], workspace_root: Path) -> list[dict]:
    """Apply compiled ops atomically, re-verifying against current live state."""
    workspace_root = Path(workspace_root)
    results: list[dict] = []

    def failure(op: CompiledOp, error: str, message: str = "") -> dict:
        entry = {"path": op.path, "nodes": list(op.nodes), "ok": False,
                 "action": op.op, "error": error}
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
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "create"})
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
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "edit"})
        elif op.op == "remove":
            path = workspace_root / op.path
            try:
                if path.exists() or path.is_symlink():
                    path.unlink()
            except OSError as exc:
                results.append(failure(op, "io_error", str(exc)))
                continue
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "remove"})
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
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "move"})
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
    nodes_map = change_dag.node_map(dag)
    ready: list[str] = []
    for node_id in change_dag.execution_order(dag):
        if node_id not in reachable or change_dag.node_type(dag, node_id) != "run":
            continue
        if effective_state.get(node_id) == "satisfied":
            continue
        if effective_state.get(node_id) == "failed":
            continue
        parents = [
            candidate
            for candidate, node in nodes_map.items()
            if change_dag.node_type(dag, candidate) == change_dag.SEMANTIC_TYPE
            and node_id in change_dag.direct_children(dag, candidate)
        ]
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

    Unresolved semantic leaves, a dirty tree, and HEAD drift are not issues.
    A structural error, compile conflict, or live-context conflict makes the
    DAG non-executable. Blocked branch-local work is reported but is not itself
    a conflict.
    """
    issues: list[dict] = []
    try:
        structural = change_dag.structure_errors(dag)
    except Exception as exc:  # pragma: no cover - defensive
        structural = [f"structure check failed: {exc}"]
    if structural:
        for message in structural:
            issues.append({"kind": "structure", "message": message})
        return {"executable": False, "issues": issues, "conflicts": [], "blocked": []}

    try:
        ops, conflicts, blocked = compile_operations(dag, state, workspace_root)
    except Exception as exc:  # pragma: no cover - defensive
        issues.append({"kind": "compile_conflict", "message": f"compilation failed: {exc}"})
        return {"executable": False, "issues": issues, "conflicts": [], "blocked": []}

    for conflict in conflicts:
        kind = "context_conflict" if conflict.reason.startswith("context_conflict") else "compile_conflict"
        issues.append({
            "kind": kind,
            "path": conflict.path,
            "nodes": list(conflict.nodes),
            "message": conflict.reason,
        })

    return {
        "executable": not issues,
        "issues": issues,
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
