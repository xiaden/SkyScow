"""Tool implementation for dag_add_run — attach a bounded verification run node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.caller_identity import set_caller_identity
from ..helpers.change_dag_ops_mutation import add_work


def dag_add_run(
    slug: str,
    parent_ids: list[str],
    command: list[str],
    exclusive: bool = False,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return add_work(workspace_root, slug, "run", parent_ids, command=command, exclusive=exclusive)


if __name__ == "__main__":
    args = json.loads(input())
    set_caller_identity(args)
    print(
        json.dumps(
            dag_add_run(
                args["slug"],
                args["parent_ids"],
                args["command"],
                args.get("exclusive", False),
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
