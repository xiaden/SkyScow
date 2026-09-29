"""Tool implementation for dag_decomposition_frontier — manager frontier retrieval."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_decomposition import decomposition_frontier_view
from ..helpers.caller_identity import current_internal_metadata, set_caller_identity


def dag_decomposition_frontier(slug: str, *, workspace_root: Path) -> dict[str, Any]:
    internal = current_internal_metadata() or {}
    return decomposition_frontier_view(workspace_root, slug, include_branch_claims=internal.get("frontier_claims") is True)


if __name__ == "__main__":
    args = json.loads(input())
    set_caller_identity(args)
    print(
        json.dumps(
            dag_decomposition_frontier(
                args["slug"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
