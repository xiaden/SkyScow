"""Tool implementation for dag_set_decomposition_only — semantic decomposition intent."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.caller_identity import set_caller_identity
from ..helpers.change_dag_ops_mutation import set_decomposition_only


def dag_set_decomposition_only(
    slug: str,
    node_id: str,
    value: bool,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return set_decomposition_only(workspace_root, slug, node_id, value)


if __name__ == "__main__":
    args = json.loads(input())
    set_caller_identity(args)
    print(
        json.dumps(
            dag_set_decomposition_only(
                args["slug"],
                args["node_id"],
                args["value"],
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
