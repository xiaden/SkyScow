"""Tool implementation for dag_update_edit — correct a mutable edit node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops_mutation import update_node


def dag_update_edit(
    slug: str,
    node_id: str,
    path: str | None = None,
    replacements: list[dict[str, str]] | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return update_node(workspace_root, slug, node_id, path=path, replacements=replacements)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_update_edit(
                args["slug"],
                args["node_id"],
                args.get("path"),
                args.get("replacements"),
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
