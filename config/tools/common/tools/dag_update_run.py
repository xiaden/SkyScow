"""Tool implementation for dag_update_run — correct a mutable run node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import update_node


def dag_update_run(
    slug: str,
    node_id: str,
    command: list[str] | None = None,
    exclusive: bool | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return update_node(workspace_root, slug, node_id, command=command, exclusive=exclusive)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_update_run(
                args["slug"],
                args["node_id"],
                args.get("command"),
                args.get("exclusive"),
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
