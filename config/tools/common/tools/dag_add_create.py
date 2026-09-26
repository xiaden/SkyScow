"""Tool implementation for dag_add_create — attach a create node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import add_work


def dag_add_create(
    slug: str,
    parent_ids: list[str],
    path: str,
    content: str,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return add_work(workspace_root, slug, "create", parent_ids, path=path, content=content)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_add_create(
                args["slug"],
                args["parent_ids"],
                args["path"],
                args["content"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
