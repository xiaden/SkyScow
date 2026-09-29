"""Tool implementation for semantic DAG requirement search."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_decomposition import semantic_search_view


def dag_semantic_search(
    slug: str, query: str, limit: int = 20, *, workspace_root: Path
) -> dict[str, Any]:
    return semantic_search_view(workspace_root, slug, query, limit)


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_semantic_search(
        args["slug"], args["query"], args.get("limit", 20),
        workspace_root=Path(args["workspace_root"]),
    )))
