"""Create a validated persistent implementation graph."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.implementation_graph import (
    SCHEMA_VERSION,
    atomic_write,
    graph_path,
    normalize_graph,
    output,
    validate_graph,
)


def impl_graph_create(graph: dict[str, Any], *, workspace_root: Path) -> dict[str, Any]:
    if not isinstance(graph, dict):
        return {"error": "invalid_graph", "message": "graph must be an object"}
    candidate = normalize_graph(graph)
    candidate["schema_version"] = SCHEMA_VERSION
    errors = validate_graph(candidate, workspace_root)
    if errors:
        return {"error": "invalid_graph", "message": "; ".join(errors[:8]), "errors": errors}
    try:
        path = graph_path(workspace_root, candidate["graph_id"])
    except ValueError as exc:
        return {"error": "invalid_graph_id", "message": str(exc)}
    if path.exists():
        return {"error": "already_exists", "message": f"graph already exists: {candidate['graph_id']}"}
    try:
        atomic_write(path, candidate)
    except OSError as exc:
        return {"error": "write_failed", "message": str(exc)}
    return output({"graph_id": candidate["graph_id"], "revision": candidate["revision"], "path": str(path.relative_to(workspace_root))}, "Create Implementation Graph")


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_create(args["graph"], workspace_root=Path(args["workspace_root"]))))
