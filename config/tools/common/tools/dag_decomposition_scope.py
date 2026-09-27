"""Tool implementation for dag_decomposition_scope — bounded worker context."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_decomposition import decomposition_scope_view


def dag_decomposition_scope(
    slug: str, node_id: str, *, workspace_root: Path
) -> dict[str, Any]:
    return decomposition_scope_view(workspace_root, slug, node_id)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_decomposition_scope(
                args["slug"],
                args["node_id"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
