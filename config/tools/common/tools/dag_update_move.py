"""Tool implementation for dag_update_move — correct a mutable move node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import update_node


def dag_update_move(
    slug: str,
    node_id: str,
    from_path: str | None = None,
    to_path: str | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return update_node(workspace_root, slug, node_id, from_path=from_path, to_path=to_path)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_update_move(
                args["slug"],
                args["node_id"],
                args.get("from_path"),
                args.get("to_path"),
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
