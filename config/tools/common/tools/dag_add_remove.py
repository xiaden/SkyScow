"""Tool implementation for dag_add_remove — attach a remove node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import add_work


def dag_add_remove(
    slug: str,
    parent_ids: list[str],
    path: str,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return add_work(workspace_root, slug, "remove", parent_ids, path=path)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_add_remove(
                args["slug"],
                args["parent_ids"],
                args["path"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
