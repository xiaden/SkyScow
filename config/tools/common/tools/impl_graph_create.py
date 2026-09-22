"""Create a validated persistent implementation graph."""
from __future__ import annotations

import json
import fcntl
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
    lock_path = path.parent.parent / f".{candidate['graph_id']}.create.lock"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if path.exists() or graph_path(workspace_root, candidate["graph_id"], completed=True).exists():
                return {"error": "already_exists", "message": f"graph already exists: {candidate['graph_id']}"}
            atomic_write(path, candidate)
    except OSError as exc:
        return {"error": "write_failed", "message": str(exc)}
    return output({"graph_id": candidate["graph_id"], "structure_revision": candidate["structure_revision"], "state_revision": candidate["state_revision"], "revision": candidate["revision"], "path": str(path.relative_to(workspace_root))}, "Create Implementation Graph")


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(impl_graph_create(args["graph"], workspace_root=Path(args["workspace_root"]))))
