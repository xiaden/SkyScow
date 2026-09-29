"""Tool implementation for dag_unlink_requirement — remove one causal requires edge."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops_mutation import unlink_requirement


def dag_unlink_requirement(
    slug: str,
    parent_id: str,
    child_id: str,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return unlink_requirement(workspace_root, slug, parent_id, child_id)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_unlink_requirement(
                args["slug"],
                args["parent_id"],
                args["child_id"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
