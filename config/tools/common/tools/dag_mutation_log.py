"""Read a bounded, read-only slice of Change DAG mutation provenance."""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path
from typing import Any

from ..helpers import change_dag
from ..helpers.change_dag_mutation_log import MUTATION_LOG_FILENAME

_MAX_LIMIT = 50


def _bounds(offset: int, limit: int) -> str | None:
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        return "offset must be a nonnegative integer"
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 < limit <= _MAX_LIMIT:
        return f"limit must be a positive integer no greater than {_MAX_LIMIT}"
    return None


def dag_mutation_log(
    slug: str,
    offset: int = 0,
    limit: int = _MAX_LIMIT,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    """Return newest-first mutation events using a bounded offset and limit."""
    try:
        bounds_error = _bounds(offset, limit)
        if bounds_error:
            return {"error": "invalid_bounds", "message": bounds_error}

        _dag, _dag_path, location = change_dag.read_dag(Path(workspace_root), slug)
        log_path = change_dag.bundle_dir(Path(workspace_root), slug, archived=location == "archived") / MUTATION_LOG_FILENAME
        if not log_path.exists():
            entries: list[dict[str, Any]] = []
            total = 0
        else:
            retained: deque[dict[str, Any]] = deque(maxlen=offset + limit)
            total = 0
            with log_path.open(encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"invalid mutation log JSON at line {line_number}") from exc
                    if not isinstance(event, dict):
                        raise ValueError(f"mutation log entry at line {line_number} is not an object")
                    retained.append(event)
                    total += 1
            entries = list(reversed(retained))[offset:offset + limit]

        return {
            "output": json.dumps(
                {
                    "slug": slug,
                    "location": location,
                    "offset": offset,
                    "limit": limit,
                    "total": total,
                    "entries": entries,
                },
                sort_keys=True,
            ),
            "title": "Read DAG Mutation Log",
            "metadata": {"count": len(entries), "total": total, "location": location},
        }
    except FileNotFoundError as exc:
        return {"error": "dag_not_found", "message": str(exc)}
    except (OSError, ValueError) as exc:
        return {"error": "invalid_mutation_log", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(
        json.dumps(
            dag_mutation_log(
                slug=args["slug"],
                offset=args.get("offset", 0),
                limit=args.get("limit", _MAX_LIMIT),
                workspace_root=Path(args["workspace_root"]),
            )
        )
    )
