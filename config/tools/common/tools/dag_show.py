"""Tool implementation for dag_show — show the graph or a bounded centered view."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import show


def dag_show(
    slug: str,
    node_id: str | None = None,
    include_ancestors: bool = False,
    include_descendants: bool = False,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    return show(
        workspace_root,
        slug,
        node_id=node_id,
        include_ancestors=include_ancestors,
        include_descendants=include_descendants,
    )


if __name__ == "__main__":
    args = json.loads(input())
    print(
        json.dumps(
            dag_show(
                args["slug"],
                args.get("node_id"),
                args.get("include_ancestors", False),
                args.get("include_descendants", False),
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
