"""Find matching source lines in a semantic node's DAG projection."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..helpers.change_dag_projection import canonical_query_path, iter_matches, projected_source
from ..helpers.change_dag_ops_support import _error


def dag_grep(
    slug: str,
    node_id: str,
    pattern: str,
    path: str | None = None,
    ignore_case: bool = False,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    source, error = projected_source(workspace_root, slug, node_id)
    if error is not None:
        return error
    assert source is not None
    canonical, error = canonical_query_path(path)
    if error is not None:
        return error
    flags = re.IGNORECASE if ignore_case else 0
    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        return _error("invalid_pattern", str(exc))
    if canonical is not None:
        failure = source.error(canonical)
        if failure is not None:
            return {**failure, "slug": slug, "node_id": node_id}
    matches = [
        {"path": candidate, "line": line}
        for candidate, line in iter_matches(source, compiled, canonical)
    ]
    return {"slug": slug, "node_id": node_id, "pattern": pattern, "matches": matches}


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_grep(
        args["slug"], args["node_id"], args["pattern"], args.get("path"),
        args.get("ignore_case", False), workspace_root=Path(args["workspace_root"]),
    )))
