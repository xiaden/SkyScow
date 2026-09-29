"""Tool implementation for dag_add_edit — attach an edit node."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.caller_identity import set_caller_identity
from ..helpers.change_dag_ops_mutation import add_work


def dag_add_edit(
    slug: str,
    parent_ids: list[str],
    path: str,
    replacements: list[dict[str, str]],
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return add_work(workspace_root, slug, "edit", parent_ids, path=path, replacements=replacements)


if __name__ == "__main__":
    args = json.loads(input())
    set_caller_identity(args)
    print(
        json.dumps(
            dag_add_edit(
                args["slug"],
                args["parent_ids"],
                args["path"],
                args["replacements"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
