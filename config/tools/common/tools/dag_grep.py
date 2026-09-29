"""Find matching source lines in a semantic node's projected SELF view."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops_support import _error
from ..helpers.caller_identity import set_caller_identity
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


def _stream_matching_lines(path: Path, pattern: re.Pattern[str]) -> Any:
    with path.open("r", encoding="utf-8", newline="") as stream:
        for number, line in enumerate(stream, 1):
            if pattern.search(line):
                yield number


def dag_grep(
    slug: str,
    node_id: str,
    pattern: str,
    path: str | None = None,
    ignore_case: bool = False,
    offset: int = 0,
    limit: int = 50,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        return _error("invalid_bounds", "offset must be a nonnegative integer")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 < limit <= 200:
        return _error("invalid_bounds", "limit must be a positive integer no greater than 200")
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

    retained: list[dict[str, Any]] = []
    skipped = 0
    last_key: tuple[str, int] | None = None

    def accept(match: dict[str, Any]) -> None:
        nonlocal skipped, last_key
        key = (match["path"], match["line"])
        if last_key is not None and key < last_key:
            raise ValueError("discovery order is not deterministic")
        last_key = key
        if skipped < offset:
            skipped += 1
        elif len(retained) < limit + 1:
            retained.append(match)

    def finish() -> dict[str, Any]:
        has_more = len(retained) > limit
        return {"slug": slug, "node_id": node_id, "pattern": pattern,
                "offset": offset, "limit": limit, "has_more": has_more,
                "matches": retained[:limit]}

    def consume_lines(candidate: str, lines: Any) -> None:
        for number in lines:
            accept({"path": candidate, "line": number})

    def stream_lines(candidate: str) -> Any:
        return _stream_matching_lines(workspace_root / candidate, compiled)

    try:
        if canonical is not None:
            failure = source.error(canonical)
            if failure is not None:
                return {**failure, "slug": slug, "node_id": node_id}
            content = source.content(canonical)
            if content is None and canonical not in source.affected_paths() and change_dag_patch.classify_file(workspace_root / canonical) == "oversized":
                consume_lines(canonical, stream_lines(canonical))
            elif content is not None:
                consume_lines(canonical, _matching_lines(content, compiled))
            return finish()

        failures = source.projection_failures()
        if failures:
            return {"error": "projection_failed", "slug": slug, "node_id": node_id, "failures": failures}
        affected = source.affected_paths()
        # Scan the live/projected union in one global path order. Matches are
        # consumed as they are found so pagination remains bounded in memory.
        for candidate in sorted(set(live_paths(workspace_root)) | affected):
            candidate_path = workspace_root / candidate
            if candidate in affected:
                content = source.content(candidate)
                if content is None:
                    if candidate in source.removed:
                        continue
                    return {"error": "search_incomplete", "path": candidate, "reason": "oversized projected content cannot be safely inspected"}
                consume_lines(candidate, _matching_lines(content, compiled))
            elif change_dag_patch.classify_file(candidate_path) == "oversized":
                consume_lines(candidate, stream_lines(candidate))
            else:
                content = effective_content(workspace_root, candidate, {}, set())
                if content is not None:
                    consume_lines(candidate, _matching_lines(content, compiled))
    except (OSError, UnicodeError, ValueError) as exc:
        return {"error": "search_incomplete", "reason": str(exc)}
    return finish()




if __name__ == "__main__":
    args = json.loads(input())
    set_caller_identity(args)
    print(json.dumps(dag_grep(
        args["slug"], args["node_id"], args["pattern"], args.get("path"),
        args.get("ignore_case", False), args.get("offset", 0), args.get("limit", 50), workspace_root=Path(args["workspace_root"]),
    )))
