"""Tool implementation for dag_preview — show compiled changes without executing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import preview


def dag_preview(
    slug: str,
    path: str | None = None,
    node_id: str | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return preview(workspace_root, slug, path=path, node_id=node_id)


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_preview(
                args["slug"],
                args.get("path"),
                args.get("node_id"),
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
