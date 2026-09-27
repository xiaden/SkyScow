"""Tool implementation for dag_decomposition_frontier — manager frontier retrieval."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_decomposition import decomposition_frontier_view


def dag_decomposition_frontier(slug: str, *, workspace_root: Path) -> dict[str, Any]:
    return decomposition_frontier_view(workspace_root, slug)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_decomposition_frontier(
                args["slug"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
