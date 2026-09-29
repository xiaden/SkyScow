"""Tool implementation for semantic DAG context."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_decomposition import semantic_context_view


def dag_semantic_context(
    slug: str, node_ids: list[str], *, workspace_root: Path
) -> dict[str, Any]:
    return semantic_context_view(workspace_root, slug, node_ids)


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_semantic_context(
        args["slug"], args["node_ids"], workspace_root=Path(args["workspace_root"]),
    )))
