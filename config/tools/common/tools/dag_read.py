"""Read source from a semantic node's frontier-bounded DAG projection."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_projection import canonical_query_path, line_content, projected_self_source


def dag_read(
    slug: str,
    node_id: str,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    source, error = projected_self_source(workspace_root, slug, node_id)
    if error is not None:
        return error
    assert source is not None
    canonical, error = canonical_query_path(path)
    if error is not None:
        return error
    assert canonical is not None
    failure = source.error(canonical)
    if failure is not None:
        return {**failure, "slug": slug, "node_id": node_id}
    content = source.content(canonical)
    start, end, selected, error = line_content(content, start_line, end_line)
    if error is not None:
        return {**error, "path": canonical}
    return {
        "slug": slug,
        "node_id": node_id,
        "path": canonical,
        "present": content is not None,
        "start_line": start,
        "end_line": end,
        "content": selected,
        "provenance": source.provenance(canonical, start, end),
    }


if __name__ == "__main__":
    args = json.loads(input())
    print(json.dumps(dag_read(
        args["slug"], args["node_id"], args["path"],
        args.get("start_line"), args.get("end_line"),
        workspace_root=Path(args["workspace_root"]),
    )))
