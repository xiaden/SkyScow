"""Find matching source lines in a semantic node's projected SELF view."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops_support import _error
from ..helpers import change_dag_patch
from ..helpers.worker_resolution import authorize_worker_read
from ..helpers.change_dag_projection import (
    canonical_query_path,
    effective_content,
    live_paths,
    projected_self_source,
)


def _matching_lines(content: str, pattern: re.Pattern[str]) -> list[int]:
    return [number for number, line in enumerate(content.splitlines(), 1) if pattern.search(line)]


def _stream_matching_lines(path: Path, pattern: re.Pattern[str]) -> list[int]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return [number for number, line in enumerate(stream, 1) if pattern.search(line)]


def dag_grep(
    slug: str,
    node_id: str,
    pattern: str,
    path: str | None = None,
    ignore_case: bool = False,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    try:
        node_id = authorize_worker_read(workspace_root, slug, node_id)
    except ValueError as exc:
        code, _, message = str(exc).partition(": ")
        return {"error": code, "message": message or code}
    source, error = projected_self_source(workspace_root, slug, node_id)
    if error is not None:
        return error
    assert source is not None
    canonical, error = canonical_query_path(path)
    if error is not None:
        return error
    flags = re.IGNORECASE if ignore_case else 0
    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        return _error("invalid_pattern", str(exc))

    if canonical is not None:
        failure = source.error(canonical)
        if failure is not None:
            return {**failure, "slug": slug, "node_id": node_id}
        content = source.content(canonical)
        if content is None and canonical not in source.affected_paths() and change_dag_patch.classify_file(workspace_root / canonical) == "oversized":
            try:
                lines = _stream_matching_lines(workspace_root / canonical, compiled)
            except (OSError, UnicodeError) as exc:
                return {"error": "search_incomplete", "path": canonical, "reason": str(exc)}
            matches = [{"path": canonical, "line": number} for number in lines]
        else:
            matches = ([] if content is None else [{"path": canonical, "line": number} for number in _matching_lines(content, compiled)])
        return {"slug": slug, "node_id": node_id, "pattern": pattern, "matches": matches}

    # A broad search reads the WHOLE projected reality, so a path that cannot be
    # reproduced must fail the call rather than silently vanish from the result.
    failures = source.projection_failures()
    if failures:
        return {
            "error": "projection_failed",
            "slug": slug,
            "node_id": node_id,
            "failures": failures,
        }

    affected = source.affected_paths()
    matches: list[dict[str, Any]] = []
    # An affected path invalidates live grep truth for that path, so ordinary
    # live matches are authoritative only for unaffected paths. Individual live
    # matches are never validated; the whole path is replaced.
    for candidate in live_paths(workspace_root):
        if candidate in affected:
            continue
        candidate_path = workspace_root / candidate
        if change_dag_patch.classify_file(candidate_path) == "oversized":
            try:
                lines = _stream_matching_lines(candidate_path, compiled)
            except (OSError, UnicodeError) as exc:
                return {"error": "search_incomplete", "path": candidate, "size": candidate_path.stat().st_size, "reason": str(exc)}
            matches.extend({"path": candidate, "line": number} for number in lines)
            continue
        content = effective_content(workspace_root, candidate, {}, set())
        if content is None:
            continue
        matches.extend({"path": candidate, "line": number} for number in _matching_lines(content, compiled))
    for candidate in sorted(affected):
        content = source.content(candidate)
        if content is None:
            if candidate in source.removed:
                continue
            candidate_path = workspace_root / candidate
            if change_dag_patch.classify_file(candidate_path) == "oversized":
                return {"error": "search_incomplete", "path": candidate, "size": candidate_path.stat().st_size, "reason": "oversized projected content cannot be safely inspected"}
            continue
        matches.extend({"path": candidate, "line": number} for number in _matching_lines(content, compiled))
    matches.sort(key=lambda entry: (entry["path"], entry["line"]))
    return {"slug": slug, "node_id": node_id, "pattern": pattern, "matches": matches}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_grep(
        args["slug"], args["node_id"], args["pattern"], args.get("path"),
        args.get("ignore_case", False), workspace_root=Path(args["workspace_root"]),
    )))
