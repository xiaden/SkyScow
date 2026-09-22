"""Validate an implementation graph without mutating it."""
from __future__ import annotations

import json
from pathlib import Path

from ..helpers.implementation_graph import output, read_graph, validate_graph


def impl_graph_validate(graph_id: str, *, workspace_root: Path) -> dict:
    try:
        graph, _, location = read_graph(workspace_root, graph_id)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": "graph_read_failed", "message": str(exc)}
    errors = validate_graph(graph, workspace_root)
    return output({"graph_id": graph_id, "location": location, "valid": not errors, "errors": errors}, "Validate Implementation Graph", {"graph_id": graph_id})


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_validate(args["graph_id"], workspace_root=Path(args["workspace_root"]))))
