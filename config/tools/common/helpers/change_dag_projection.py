"""Scoped projected repository views for Change DAG worker tooling.

Two lenses share one facility:

``BASE`` (:func:`projected_source`) -- live repository content plus accepted
work from construction frontiers *strictly deeper* than the assigned semantic
boundary, and nothing the boundary node itself authored. Mutation tooling
validates a NEW or CHANGING terminal operation against this lens, so an
operation's own work can never become its own base.

``SELF`` (:func:`projected_self_source`) -- BASE plus the boundary semantic
node's own persisted direct terminal work. This is the lens
``dag_read``/``dag_grep``/``dag_search`` return, so a worker can verify what it
just authored.

Both lenses exclude same-frontier peers, shallower/future work, and unowned
sibling proposals by construction. The projection deliberately reuses
``compile_lower_work``, the same lowering the authoring preview uses, so a
worker reading through these tools sees exactly the projected content the
preview reports.

Unresolved, non-executable, or globally conflicted DAGs still project fine:
only conflicts in the *applicable* work surface mark paths as unreproducible
instead of silently falling back to stale live content, and broad searches
surface those conflicts rather than hiding them.
"""
from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from . import change_dag
from .change_dag_compiler_model import Conflict, _RepoView
from .change_dag_compiler_lowering import compile_operations
from .change_dag_compiler_phase import compile_lower_work
from .change_dag_patch import PatchError, read_text_preserving
from .change_dag_ops_support import _error, _load


_EXCLUDED_DIRS = {".git", ".control", "__pycache__", "change-dags", "node_modules", "vendor"}
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def live_paths(workspace_root: Path) -> list[str]:
    """Deterministic workspace-relative paths of live repository files.

    Shared by the projected-source tools so live scanning and projected scanning
    walk the same file set in the same order, and so neither needs a worktree.
    """
    found: list[str] = []
    for root, dirs, files in os.walk(workspace_root, topdown=True):
        dirs[:] = sorted(name for name in dirs if name not in _EXCLUDED_DIRS)
        for name in sorted(files):
            target = Path(root) / name
            try:
                found.append(target.relative_to(workspace_root).as_posix())
            except ValueError:
                continue
    return sorted(found)


def effective_content(
    workspace_root: Path, path: str, overlay: dict[str, str], removed: set[str]
) -> str | None:
    """Accepted content for one path: overlay wins, removals hide, else live."""
    if path in overlay:
        return overlay[path]
    if path in removed:
        return None
    target = workspace_root / path
    if not target.is_file():
        return None
    try:
        return read_text_preserving(target)
    except (OSError, PatchError, UnicodeError):
        return None


@dataclass
class ProjectedSource:
    """Live source plus accepted lower work below one semantic boundary."""

    workspace_root: Path
    slug: str
    node_id: str
    boundary_depth: int
    overlay: dict[str, str]
    removed: set[str]
    conflicts: list[Conflict] = field(default_factory=list)
    lower_node_ids: list[str] = field(default_factory=list)
    owned_node_ids: list[str] = field(default_factory=list)
    lower_path_nodes: dict[str, list[str]] = field(default_factory=dict)
    owned_path_nodes: dict[str, list[str]] = field(default_factory=dict)
    lower_overlay: dict[str, str] = field(default_factory=dict)
    lower_removed: set[str] = field(default_factory=set)

    def provenance(self, path: str, start: int, end: int) -> list[dict[str, Any]]:
        """Attribute the read window to ``live``/``accepted_lower``/``owned``.

        Three lenses are compared line by line: live repository content, the
        base (accepted lower work only), and self (base plus this boundary
        node's own terminal work). A line is ``owned`` where self diverges from
        base, ``accepted_lower`` where base diverges from live, and ``live``
        otherwise. Ranges are coalesced, clipped to the requested window, and
        carry only the nodes that actually touch the path.
        """
        live = effective_content(self.workspace_root, path, {}, set())
        base = effective_content(self.workspace_root, path, self.lower_overlay, self.lower_removed)
        self_text = effective_content(self.workspace_root, path, self.overlay, self.removed)
        lower_ids = self.lower_path_nodes.get(path) or list(self.lower_node_ids)
        owned_ids = self.owned_path_nodes.get(path) or list(self.owned_node_ids)
        if self_text is None:
            if path in self.lower_removed:
                return [{"lines": [], "node_ids": lower_ids, "relation": "accepted_lower"}]
            if path in self.removed:
                return [{"lines": [], "node_ids": owned_ids, "relation": "owned"}]
            return []
        if self_text == "":
            return []
        relations = _line_relations(live, base, self_text)
        clipped = _clip(relations, start, end)
        return [
            {
                "lines": [low, high],
                "node_ids": (
                    [] if relation == "live"
                    else owned_ids if relation == "owned"
                    else lower_ids
                ),
                "relation": relation,
            }
            for relation, low, high in clipped
        ]

    def content(self, path: str) -> str | None:
        if self.error(path) is not None:
            return None
        return effective_content(self.workspace_root, path, self.overlay, self.removed)

    def error(self, path: str) -> dict[str, Any] | None:
        """Compact failure when applicable projected work cannot be reproduced.

        A conflict on the path means the deeper work that should shape this
        path is malformed or unappliable against live content. Reporting that
        is strictly better than returning live content as if it were the
        accepted projection.
        """
        for conflict in self.conflicts:
            if conflict.path == path:
                return {
                    "error": "projection_failed",
                    "path": path,
                    "nodes": list(conflict.nodes),
                    "reason": conflict.reason,
                }
        return None

    def affected_paths(self) -> set[str]:
        """Paths whose truth is governed by accepted-lower or owned work.

        These are the paths where live repository truth is superseded: an
        affected path's live content and live matches are invalid, and the
        projected content is authoritative instead. Move operators contribute
        both sides, so a moved-away source and its destination are included.
        """
        return set(self.lower_path_nodes) | set(self.owned_path_nodes)

    def projection_failures(self) -> list[dict[str, Any]]:
        """Applicable self-view conflicts that make a broad read incomplete.

        Only conflicts belonging to this boundary's SELF view appear here:
        same-frontier peers and shallower/future work are excluded while the
        projection is built, so they can never poison the result. A broad
        search that silently skipped these paths would report a false negative,
        so callers must surface them instead.
        """
        seen: dict[str, dict[str, Any]] = {}
        for conflict in self.conflicts:
            if conflict.path in seen:
                continue
            seen[conflict.path] = {
                "path": conflict.path,
                "nodes": list(conflict.nodes),
                "reason": conflict.reason,
            }
        return [seen[path] for path in sorted(seen)]

    def paths(self) -> Iterator[str]:
        for candidate in sorted((set(live_paths(self.workspace_root)) | set(self.overlay)) - self.removed):
            if self.error(candidate) is None:
                yield candidate


def _boundary_error(dag: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    nodes = change_dag.node_map(dag)
    if node_id not in nodes:
        return _error("unknown_node", f"node not found: {node_id}")
    if change_dag.node_type(dag, node_id) != change_dag.SEMANTIC_TYPE:
        return _error(
            "invalid_boundary_node",
            f"projected source requires a semantic boundary node: {node_id}",
        )
    if node_id not in change_dag.derived_depth(dag):
        return _error(
            "invalid_boundary_node",
            f"boundary node is not reachable from the root: {node_id}",
        )
    return None


def projected_source(
    workspace_root: Path, slug: str, node_id: str
) -> tuple[ProjectedSource | None, dict[str, Any] | None]:
    """Build the shared lower-frontier projection without creating a worktree."""
    root = Path(workspace_root)
    dag, state, _location, err = _load(root, slug)
    if err is not None:
        return None, err
    assert dag is not None and state is not None
    boundary_error = _boundary_error(dag, node_id)
    if boundary_error is not None:
        return None, boundary_error
    boundary_depth = change_dag.derived_depth(dag)[node_id]
    ops, conflicts, overlay, removed = compile_lower_work(
        dag, root, boundary_depth, state=state
    )
    source = ProjectedSource(
        root, slug, node_id, boundary_depth, overlay, removed, conflicts
    )
    # BASE has no owned work: its self lens equals its base lens.
    source.lower_node_ids = [node for op in ops for node in op.nodes]
    source.lower_path_nodes = _path_nodes(ops)
    source.lower_overlay = overlay
    source.lower_removed = removed
    return source, None


def _owned_terminal_ids(dag: dict[str, Any], node_id: str) -> set[str]:
    return {
        child for child in change_dag.direct_children(dag, node_id)
        if change_dag.node_type(dag, child) in change_dag.TERMINAL_TYPES
    }


def _apply_ops(ops: list[Any], root: Path, overlay: dict[str, str], removed: set[str]) -> None:
    for op in ops:
        if op.op in {"create", "edit"} and op.path is not None:
            overlay[op.path] = op.applied if op.applied is not None else ""
            removed.discard(op.path)
        elif op.op == "remove" and op.path is not None:
            overlay.pop(op.path, None)
            removed.add(op.path)
        elif op.op == "move":
            content = overlay.get(op.from_path or "")
            if content is None and op.from_path not in removed:
                try:
                    content = effective_content(root, op.from_path or "", overlay, removed)
                except (OSError, PatchError, UnicodeError):
                    content = None
            if op.to_path is not None:
                overlay[op.to_path] = content or ""
                removed.discard(op.to_path)
            if op.from_path is not None:
                overlay.pop(op.from_path, None)
                removed.add(op.from_path)


def _path_nodes(ops: list[Any]) -> dict[str, list[str]]:
    """Map each affected path to the node IDs whose work touches it."""
    mapping: dict[str, list[str]] = {}
    for op in ops:
        candidates: list[str] = []
        if op.path is not None:
            candidates.append(op.path)
        if op.op == "move":
            for candidate in (op.from_path, op.to_path):
                if candidate is not None:
                    candidates.append(candidate)
        for candidate in candidates:
            bucket = mapping.setdefault(candidate, [])
            for node in op.nodes:
                if node not in bucket:
                    bucket.append(node)
    return mapping


def _line_relations(
    live: str | None, base: str | None, self_text: str
) -> list[tuple[str, int, int]]:
    """Classify every SELF line and coalesce adjacent equal relations."""
    self_lines = self_text.splitlines(keepends=True)
    if not self_lines:
        return []
    live_lines = live.splitlines(keepends=True) if live is not None else []
    base_lines = base.splitlines(keepends=True) if base is not None else []

    owned_index: set[int] = set()
    base_of_self: dict[int, int] = {}
    for tag, i1, _i2, j1, j2 in difflib.SequenceMatcher(
        None, base_lines, self_lines, autojunk=False
    ).get_opcodes():
        if tag in {"replace", "insert"}:
            owned_index.update(range(j1, j2))
        elif tag == "equal":
            for offset in range(j2 - j1):
                base_of_self[j1 + offset] = i1 + offset

    lower_base_index: set[int] = set()
    for tag, _i1, _i2, j1, j2 in difflib.SequenceMatcher(
        None, live_lines, base_lines, autojunk=False
    ).get_opcodes():
        if tag in {"replace", "insert"}:
            lower_base_index.update(range(j1, j2))

    relations: list[tuple[str, int, int]] = []
    current: str | None = None
    block_start = 0
    for index in range(len(self_lines)):
        if index in owned_index:
            relation = "owned"
        elif base_of_self.get(index) in lower_base_index:
            relation = "accepted_lower"
        else:
            relation = "live"
        if relation != current:
            if current is not None:
                relations.append((current, block_start + 1, index))
            current = relation
            block_start = index
    relations.append((current or "live", block_start + 1, len(self_lines)))
    return relations


def _clip(
    ranges: list[tuple[str, int, int]], start: int, end: int
) -> list[tuple[str, int, int]]:
    """Keep only ranges intersecting the window, clamped to it."""
    clipped: list[tuple[str, int, int]] = []
    for relation, low, high in ranges:
        low, high = max(low, start), min(high, end)
        if low <= high:
            clipped.append((relation, low, high))
    return clipped


def projected_self_source(
    workspace_root: Path, slug: str, node_id: str
) -> tuple[ProjectedSource | None, dict[str, Any] | None]:
    """Build BASE plus the boundary semantic node's own direct terminal work."""
    root = Path(workspace_root)
    dag, state, _location, err = _load(root, slug)
    if err is not None:
        return None, err
    assert dag is not None and state is not None
    boundary_error = _boundary_error(dag, node_id)
    if boundary_error is not None:
        return None, boundary_error
    boundary_depth = change_dag.derived_depth(dag)[node_id]
    lower_ops, conflicts, lower_overlay, lower_removed = compile_lower_work(
        dag, root, boundary_depth, state=state
    )
    owned = _owned_terminal_ids(dag, node_id)
    combined_overlay = dict(lower_overlay)
    combined_removed = set(lower_removed)
    repo = _RepoView(root, combined_overlay, combined_removed)
    owned_ops, owned_conflicts, _ = compile_operations(
        dag, {}, root, repo=repo, include_nodes=owned
    )
    conflicts = [*conflicts, *owned_conflicts]
    _apply_ops(owned_ops, root, combined_overlay, combined_removed)
    source = ProjectedSource(
        root, slug, node_id, boundary_depth, combined_overlay, combined_removed, conflicts
    )
    source.lower_node_ids = [node for op in lower_ops for node in op.nodes]
    source.owned_node_ids = [node for op in owned_ops for node in op.nodes]
    source.lower_path_nodes = _path_nodes(lower_ops)
    source.owned_path_nodes = _path_nodes(owned_ops)
    source.lower_overlay = lower_overlay
    source.lower_removed = lower_removed
    return source, None


def canonical_query_path(path: str | None) -> tuple[str | None, dict[str, Any] | None]:
    if path is None:
        return None, None
    try:
        return change_dag.canonical_path(path), None
    except (TypeError, ValueError) as exc:
        return None, _error("invalid_path", f"path: {exc}")


def line_content(content: str | None, start_line: int | None, end_line: int | None) -> tuple[int, int, str | None, dict[str, Any] | None]:
    if start_line is not None and (isinstance(start_line, bool) or start_line < 1):
        return 0, 0, None, _error("invalid_range", "start_line must be >= 1")
    if end_line is not None and (isinstance(end_line, bool) or end_line < 1):
        return 0, 0, None, _error("invalid_range", "end_line must be >= 1")
    if start_line is not None and end_line is not None and end_line < start_line:
        return 0, 0, None, _error("invalid_range", "end_line must be >= start_line")
    if content is None:
        start = start_line or 1
        end = end_line or start
        return start, end, None, None
    lines = content.splitlines(keepends=True)
    total = len(lines)
    start = start_line or 1
    end = end_line or total
    if total == 0:
        if start_line is not None or end_line is not None:
            return start, end, None, _error("invalid_range", "requested range is outside the empty file")
        return 1, 0, "", None
    if start > total or end > total:
        return start, end, None, _error("invalid_range", f"requested range exceeds file length ({total})")
    return start, end, "".join(lines[start - 1:end]), None


def iter_matches(source: ProjectedSource, pattern: re.Pattern[str], path: str | None = None) -> Iterator[tuple[str, int]]:
    paths = [path] if path is not None else source.paths()
    for candidate in paths:
        content = source.content(candidate)
        if content is None:
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            if pattern.search(line):
                yield candidate, line_number


def search_score(content: str, path: str, query: str) -> float:
    folded = content.casefold()
    phrase = query.casefold().strip()
    terms = [term.casefold() for term in _TOKEN_RE.findall(query)]
    score = float(folded.count(phrase) * 3) if phrase else 0.0
    score += sum(folded.count(term) for term in terms)
    score += sum(path.casefold().count(term) * 0.25 for term in terms)
    return score
