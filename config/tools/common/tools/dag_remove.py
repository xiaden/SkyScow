"""Tool implementation for dag_remove — remove mutable content and GC unreachable work."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import remove_node


def dag_remove(slug: str, node_id: str, *, workspace_root: Path) -> dict[str, Any]:
    return remove_node(workspace_root, slug, node_id)


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_remove(args["slug"], args["node_id"], workspace_root=Path(args["workspace_root"]))))
