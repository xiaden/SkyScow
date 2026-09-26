"""Tool implementation for dag_update_edit — correct a mutable edit node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import update_node


def dag_update_edit(
    slug: str,
    node_id: str,
    path: str | None = None,
    patch: str | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return update_node(workspace_root, slug, node_id, path=path, patch=patch)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_update_edit(
                args["slug"],
                args["node_id"],
                args.get("path"),
                args.get("patch"),
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
