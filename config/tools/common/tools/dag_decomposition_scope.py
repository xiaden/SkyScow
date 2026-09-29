"""Tool implementation for dag_decomposition_scope — bounded worker context."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.caller_identity import set_caller_identity
from ..helpers.change_dag_decomposition import decomposition_scope_view
from ..helpers.worker_resolution import authorize_worker_read


def dag_decomposition_scope(
    slug: str, node_id: str, *, workspace_root: Path
) -> dict[str, Any]:
    try:
        node_id = authorize_worker_read(workspace_root, slug, node_id)
    except ValueError as exc:
        code, _, message = str(exc).partition(": ")
        return {"error": code, "message": message or code}
    return decomposition_scope_view(workspace_root, slug, node_id)


if __name__ == "__main__":
    args = json.loads(input())
    set_caller_identity(args)
    print(
        json.dumps(
            dag_decomposition_scope(
                args["slug"],
                args["node_id"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
