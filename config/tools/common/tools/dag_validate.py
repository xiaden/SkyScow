"""Tool implementation for dag_validate — report derived schema/executable/resolved."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_ops import validate


def dag_validate(slug: str, *, workspace_root: Path) -> dict[str, Any]:
    return validate(workspace_root, slug)


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_validate(args["slug"], workspace_root=Path(args["workspace_root"]))))
