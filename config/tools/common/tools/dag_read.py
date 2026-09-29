"""Read source from a semantic node's frontier-bounded DAG projection."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers import change_dag_patch
from ..helpers.change_dag_projection import canonical_query_path, line_content, projected_self_source


def _range_error(start_line: int | None, end_line: int | None) -> dict[str, Any] | None:
    if start_line is not None and (isinstance(start_line, bool) or start_line < 1):
        return {"error": "invalid_range", "reason": "start_line must be >= 1"}
    if end_line is not None and (isinstance(end_line, bool) or end_line < 1):
        return {"error": "invalid_range", "reason": "end_line must be >= 1"}
    if start_line is not None and end_line is not None and end_line < start_line:
        return {"error": "invalid_range", "reason": "end_line must be >= start_line"}
    return None


def _read_live_range(path: Path, start_line: int | None, end_line: int | None) -> tuple[int, int, str | None, dict[str, Any] | None]:
    invalid = _range_error(start_line, end_line)
    if invalid is not None:
        return 0, 0, None, invalid
    start = start_line or 1
    requested_end = end_line
    if requested_end is None:
        return start, start, None, {"error": "range_required", "reason": "oversized reads require both start_line and end_line"}
    selected: list[str] = []
    total = 0
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            for number, line in enumerate(stream, 1):
                total = number
                if number >= start and (requested_end is None or number <= requested_end):
                    selected.append(line)
    except (OSError, UnicodeError) as exc:
        return start, requested_end or start, None, {"error": "file_too_large", "reason": f"cannot stream oversized file: {exc}"}
    if total == 0:
        if start_line is not None or end_line is not None:
            return start, requested_end or start, None, {"error": "invalid_range", "reason": "requested range is outside the empty file"}
        return 1, 0, "", None
    if start > total:
        return start, requested_end or start, None, {"error": "invalid_range", "reason": f"requested range exceeds file length ({total})"}
    end = min(requested_end or total, total)
    return start, end, "".join(selected), None


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
    target = workspace_root / canonical
    classification = change_dag_patch.classify_file(target)
    if canonical not in source.affected_paths() and classification == "oversized":
        start, end, selected, error = _read_live_range(target, start_line, end_line)
        if error is not None:
            return {**error, "path": canonical, "size": target.stat().st_size}
        provenance = [] if selected == "" else [{"lines": [start, end], "node_ids": [], "relation": "live"}]
        return {
            "slug": slug, "node_id": node_id, "path": canonical, "present": True,
            "start_line": start, "end_line": end, "content": selected,
            "provenance": provenance,
        }
    content = source.content(canonical)
    if content is not None and len(content.encode("utf-8")) > change_dag_patch.MAX_MATERIALIZED_TEXT_BYTES:
        return {"error": "file_too_large", "path": canonical, "size": len(content.encode("utf-8")),
                "reason": "projected content exceeds maximum materialized text size"}
    start, end, selected, error = line_content(content, start_line, end_line)
    if error is not None:
        if error.get("error") == "invalid_range" and end_line is not None and content is not None:
            total = len(content.splitlines(keepends=True))
            if start_line is not None and start_line <= total and end_line > total:
                end_line = total
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
