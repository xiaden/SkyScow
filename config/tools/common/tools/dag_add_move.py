"""Tool implementation for dag_add_move — attach a move node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import add_work


def dag_add_move(
    slug: str,
    parent_ids: list[str],
    from_path: str,
    to_path: str,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return add_work(workspace_root, slug, "move", parent_ids, from_path=from_path, to_path=to_path)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_add_move(
                args["slug"],
                args["parent_ids"],
                args["from_path"],
                args["to_path"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
