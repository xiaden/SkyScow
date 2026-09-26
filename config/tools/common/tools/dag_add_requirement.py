"""Tool implementation for dag_add_requirement — insert a semantic node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import add_requirement


def dag_add_requirement(
    slug: str,
    requirement: str,
    parent_ids: list[str],
    child_ids: list[str] | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return add_requirement(workspace_root, slug, requirement, parent_ids, child_ids)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_add_requirement(
                args["slug"],
                args["requirement"],
                args["parent_ids"],
                args.get("child_ids"),
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
