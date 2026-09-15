"""Read and query durable QA round records, failing closed on corruption."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.qa_round_records import (
    LOGS_DIR,
    QA_ROUNDS_DIR,
    WRITERS,
    load_records,
    record_path,
    safe_key,
)


def qa_record_read(*, workspace_root: Path, task_family: str, round: int | None = None, writer: str = "", subject: str = "", decision: str = "", source_kind: str = "", source_ref: str = "") -> dict[str, Any]:
    """Read validated terminal QA history for an existing task family.

    The required family can be narrowed by round, writer, subject substring,
    decision, and provenance. Missing history returns an empty ``records``
    list; malformed, cross-family, or writer-mismatched history returns a
    fail-closed error.

    Args:
        workspace_root: Workspace containing the artifacts directory.
        task_family: Existing task-family identity to query.
        round: Optional positive QA round number.
        writer: Optional supported writer filter.
        subject: Optional subject substring filter.
        decision: Optional terminal decision filter.
        source_kind: Optional exact provenance kind filter.
        source_ref: Optional provenance reference substring filter.

    Returns:
        A structured result containing matching records and their total, or an
        ``invalid_qa_history`` error response.
    """
    try:
        family = safe_key(task_family, "task family")
        writers = [writer] if writer else sorted(WRITERS)
        for item in writers:
            if item not in WRITERS:
                raise ValueError("unsupported writer")
        paths = []
        root = workspace_root / LOGS_DIR / QA_ROUNDS_DIR / family
        if round is not None:
            if isinstance(round, bool) or not isinstance(round, int) or round < 1:
                raise ValueError("round must be a positive integer")
            paths = [record_path(workspace_root, family, round, item) for item in writers]
        elif root.exists():
            paths = [p for p in root.glob("round-*/*.jsonl") if p.name.removesuffix(".jsonl") in writers]
        records = []
        for path in paths:
            records.extend(load_records(path, task_family=family, writer=path.stem))
        if subject:
            records = [r for r in records if subject in json.dumps(r.get("subject", ""), sort_keys=True)]
        if decision:
            records = [r for r in records if r.get("decision") == decision]
        if source_kind:
            records = [r for r in records if r.get("source_kind") == source_kind]
        if source_ref:
            records = [r for r in records if source_ref in json.dumps(r.get("source_ref", ""), sort_keys=True)]
        return {"output": json.dumps({"task_family": family, "records": records, "total": len(records)}), "title": "Read QA Round Records", "metadata": {"count": len(records)}}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"error": "invalid_qa_history", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(qa_record_read(workspace_root=Path(args["workspace_root"]), task_family=args["task_family"], round=args.get("round"), writer=args.get("writer", ""), subject=args.get("subject", ""), decision=args.get("decision", ""), source_kind=args.get("source_kind", ""), source_ref=args.get("source_ref", ""))))
