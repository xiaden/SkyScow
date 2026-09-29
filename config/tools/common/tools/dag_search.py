"""Rank projected source files with a small deterministic text scorer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers import change_dag_patch
from ..helpers.change_dag_projection import (
    canonical_query_path,
    effective_content,
    live_paths,
    projected_self_source,
    search_score,
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
        # A broad ranking must not be truncated over an incomplete view, so an
        # unreproducible applicable path fails the call instead of being skipped.
        failures = source.projection_failures()
        if failures:
            return {
                "error": "projection_failed",
                "slug": slug,
                "node_id": node_id,
                "failures": failures,
            }
        candidates = sorted(set(live_paths(workspace_root)) | affected)

    results: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_path = workspace_root / candidate
        content: str | None = None
        if candidate in source.removed:
            continue
        if candidate in affected:
            content = source.content(candidate)
            if content is not None and len(content.encode("utf-8")) > change_dag_patch.MAX_MATERIALIZED_TEXT_BYTES:
                return {"error": "search_incomplete", "slug": slug, "node_id": node_id,
                        "path": candidate, "size": len(content.encode("utf-8")),
                        "reason": "oversized projected content cannot be safely scored"}
        elif change_dag_patch.classify_file(candidate_path) == "oversized":
            return {"error": "search_incomplete", "slug": slug, "node_id": node_id,
                    "path": candidate, "size": candidate_path.stat().st_size,
                    "reason": "oversized candidate cannot be scored without full materialization"}
        elif candidate not in affected:
            content = effective_content(workspace_root, candidate, {}, set())
        if content is not None and len(content.encode("utf-8")) > change_dag_patch.MAX_MATERIALIZED_TEXT_BYTES:
            return {"error": "search_incomplete", "slug": slug, "node_id": node_id,
                    "path": candidate, "size": len(content.encode("utf-8")),
                    "reason": "oversized projected content cannot be safely scored"}
        if content is None:
            continue
        score = search_score(content, candidate, query)
        if score > 0:
            results.append({"path": candidate, "score": round(score, 6)})

    # Ranking and the limit are applied only after the authoritative merge of
    # live and projected candidates; the same scorer serves both lenses.
    results.sort(key=lambda result: (-result["score"], result["path"]))
    return {"slug": slug, "node_id": node_id, "query": query, "results": results[: max(0, limit)]}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_search(
        args["slug"], args["node_id"], args["query"], args.get("path"),
        args.get("limit", 20), workspace_root=Path(args["workspace_root"]),
    )))
