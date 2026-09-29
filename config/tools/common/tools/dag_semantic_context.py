"""Tool implementation for semantic DAG context."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_decomposition import semantic_context_view
from ..helpers.worker_resolution import worker_binding_for_call


def dag_semantic_context(
    slug: str, node_ids: list[str], *, workspace_root: Path
) -> dict[str, Any]:
    try:
        binding = worker_binding_for_call(workspace_root, slug)
    except ValueError as exc:
        code, _, message = str(exc).partition(": ")
        return {"error": code, "message": message or code}
    if binding is not None and (len(node_ids) != 1 or node_ids[0] != binding.node_id):
        return {"error": "worker_scope_mismatch", "message": "semantic context is outside the bound worker scope"}
    return semantic_context_view(workspace_root, slug, node_ids)


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_semantic_context(
        args["slug"], args["node_ids"], workspace_root=Path(args["workspace_root"]),
    )))
