"""Rank projected source files with a small deterministic text scorer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers import change_dag_patch
from ..helpers.caller_identity import set_caller_identity
from ..helpers.worker_resolution import authorize_worker_read
from ..helpers.change_dag_projection import (
    canonical_query_path,
    effective_content,
    live_paths,
    projected_self_source,
    search_score,
    search_score_stream,
)


def dag_search(
    slug: str,
    node_id: str,
    query: str,
    path: str | None = None,
    limit: int = 20,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 < limit <= 200:
        return {"error": "invalid_bounds", "message": "limit must be a positive integer no greater than 200"}
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
    affected = source.affected_paths()
    if canonical is not None:
        failure = source.error(canonical)
        if failure is not None:
            return {**failure, "slug": slug, "node_id": node_id}
        candidates = [canonical]
    else:
        failures = source.projection_failures()
        if failures:
            return {"error": "projection_failed", "slug": slug, "node_id": node_id, "failures": failures}
        candidates = sorted(set(live_paths(workspace_root)) | affected)

    # Keep only the best K entries. Linear replacement is intentional: memory is
    # O(limit), and the bounded limit keeps the comparison cost negligible.
    ranked: list[tuple[float, str, dict[str, Any]]] = []
    for candidate in candidates:
        candidate_path = workspace_root / candidate
        if candidate in source.removed:
            continue
        content: str | None = None
        stream_live = candidate not in affected and change_dag_patch.classify_file(candidate_path) == "oversized"
        if candidate in affected:
            content = source.content(candidate)
            if content is None:
                continue
            if len(content.encode("utf-8")) > change_dag_patch.DISCOVERY_MAX_TEXT_BYTES:
                return {"error": "search_incomplete", "slug": slug, "node_id": node_id, "path": candidate, "reason": "projected content exceeds discovery limit"}
        elif stream_live:
            try:
                score = search_score_stream(candidate_path, candidate, query)
            except (OSError, UnicodeError) as exc:
                return {"error": "search_incomplete", "slug": slug, "node_id": node_id, "path": candidate, "reason": str(exc)}
        else:
            content = effective_content(workspace_root, candidate, {}, set())
        if not stream_live:
            if content is None:
                continue
            score = search_score(content, candidate, query)
        if score <= 0:
            continue
        entry = {"path": candidate, "score": round(score, 6)}
        # Python tuple ordering gives score ascending first; path is reversed
        # through a small wrapper key so equal-score eviction prefers path_asc.
        item = (score, candidate, entry)
        if len(ranked) < limit:
            ranked.append(item)
        else:
            worst_score = min(item[0] for item in ranked)
            worst_index = max(
                (index for index, item in enumerate(ranked) if item[0] == worst_score),
                key=lambda index: ranked[index][1],
            )
            worst = ranked[worst_index]
            if score > worst[0] or (score == worst[0] and candidate < worst[1]):
                ranked[worst_index] = item

    results = [item[2] for item in ranked]
    results.sort(key=lambda result: (-result["score"], result["path"]))
    return {"slug": slug, "node_id": node_id, "query": query, "results": results}



if __name__ == "__main__":
    args = json.loads(input())
    set_caller_identity(args)
    print(json.dumps(dag_search(
        args["slug"], args["node_id"], args["query"], args.get("path"),
        args.get("limit", 20), workspace_root=Path(args["workspace_root"]),
    )))
