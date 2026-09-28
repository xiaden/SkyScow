"""Rank projected source files with a small deterministic text scorer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_projection import canonical_query_path, projected_source, search_score


def dag_search(
    slug: str,
    node_id: str,
    query: str,
    path: str | None = None,
    limit: int = 20,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    source, error = projected_source(workspace_root, slug, node_id)
    if error is not None:
        return error
    assert source is not None
    canonical, error = canonical_query_path(path)
    if error is not None:
        return error
    candidates = [canonical] if canonical is not None else source.paths()
    results = []
    for candidate in candidates:
        content = source.content(candidate)
        if content is None:
            continue
        score = search_score(content, candidate, query)
        if score > 0:
            results.append({"path": candidate, "score": round(score, 6)})
    results.sort(key=lambda result: (-result["score"], result["path"]))
    return {"slug": slug, "node_id": node_id, "query": query, "results": results[: max(0, limit)]}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_search(
        args["slug"], args["node_id"], args["query"], args.get("path"),
        args.get("limit", 20), workspace_root=Path(args["workspace_root"]),
    )))
