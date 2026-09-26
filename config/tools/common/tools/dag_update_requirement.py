"""Tool implementation for dag_update_requirement — change semantic requirement text."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import update_node


def dag_update_requirement(
    slug: str,
    node_id: str,
    requirement: str,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return update_node(workspace_root, slug, node_id, requirement=requirement)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_update_requirement(
                args["slug"],
                args["node_id"],
                args["requirement"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
