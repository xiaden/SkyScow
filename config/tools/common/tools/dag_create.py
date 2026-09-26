"""Tool implementation for dag_create — create and persist the initial semantic DAG."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import create_dag


def dag_create(slug: str, semantic_graph: dict[str, Any], *, workspace_root: Path) -> dict[str, Any]:
    return create_dag(workspace_root, slug, semantic_graph)


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_create(args["slug"], args["semantic_graph"], workspace_root=Path(args["workspace_root"]))))
