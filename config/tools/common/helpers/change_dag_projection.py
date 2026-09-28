"""Frontier-bounded source projection for Change DAG authoring tools."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from . import change_dag
from .change_dag_compiler_phase import compile_lower_work
from .change_dag_patch import PatchError, read_text_preserving
from .change_dag_ops_support import _error, _load


_EXCLUDED_DIRS = {".git", ".control", "__pycache__"}
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


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

    def content(self, path: str) -> str | None:
        return effective_content(self.workspace_root, path, self.overlay, self.removed)

    def paths(self) -> Iterator[str]:
        live: set[str] = set()
        for root, dirs, files in os.walk(self.workspace_root, topdown=True):
            dirs[:] = sorted(name for name in dirs if name not in _EXCLUDED_DIRS)
            for name in sorted(files):
                target = Path(root) / name
                try:
                    live.add(target.relative_to(self.workspace_root).as_posix())
                except ValueError:
                    continue
        yield from sorted((live | set(self.overlay)) - self.removed)


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
    _ops, _conflicts, overlay, removed = compile_lower_work(
        dag, root, boundary_depth, state=state
    )
    return ProjectedSource(root, slug, node_id, boundary_depth, overlay, removed), None


def canonical_query_path(path: str | None) -> tuple[str | None, dict[str, Any] | None]:
    if path is None:
        return None, None
    try:
        return change_dag.canonical_path(path), None
    except ValueError as exc:
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
