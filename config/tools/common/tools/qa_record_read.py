"""Read and query durable QA round records, failing closed on corruption."""
from __future__ import annotations

import fcntl
import json
import sqlite3
from pathlib import Path
from typing import Any

from ..helpers.qa_round_records import LOGS_DIR, QA_ROUNDS_DIR, WRITERS, identity_index_path, record_path, safe_key, synchronize_identity_index


def _indexed_records(path: Path, *, task_family: str, writer: str, subject: str, decision: str, source_kind: str, source_ref: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a", encoding="utf-8") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
        try:
            with sqlite3.connect(identity_index_path(path)) as index:
                index.execute("PRAGMA synchronous = OFF")
                synchronize_identity_index(index, path, task_family=task_family, writer=writer)
                clauses: list[str] = []
                parameters: list[str] = []
                if subject: clauses += ["instr(subject_text, ?) > 0"]; parameters.append(subject)
                if decision: clauses += ["decision = ?"]; parameters.append(decision)
                if source_kind: clauses += ["source_kind = ?"]; parameters.append(source_kind)
                if source_ref: clauses += ["instr(source_ref, ?) > 0"]; parameters.append(source_ref)
                where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
                rows = index.execute("SELECT payload FROM records" + where + " ORDER BY rowid", parameters).fetchall()
            return [json.loads(row[0]) for row in rows]
        finally:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)


def qa_record_read(*, workspace_root: Path, task_family: str = "", dag_slug: str = "", round: int | None = None, writer: str = "", subject: str = "", decision: str = "", source_kind: str = "", source_ref: str = "") -> dict[str, Any]:
    try:
        if task_family and dag_slug and task_family.strip() != dag_slug.strip():
            raise ValueError("dag_slug and task_family must identify the same family")
        family = safe_key(dag_slug or task_family, "DAG identity" if dag_slug else "task family")
        writers = [writer] if writer else sorted(WRITERS)
        if any(item not in WRITERS for item in writers):
            raise ValueError("unsupported writer")
        root = workspace_root / LOGS_DIR / QA_ROUNDS_DIR / family
        if round is not None:
            if isinstance(round, bool) or not isinstance(round, int) or round < 1:
                raise ValueError("round must be a positive integer")
            paths = [record_path(workspace_root, family, round, item) for item in writers]
        elif root.exists():
            paths = [path for path in root.glob("round-*/*.jsonl") if path.name.removesuffix(".jsonl") in writers]
        else:
            paths = []
        records: list[dict[str, Any]] = []
        for path in paths:
            records.extend(_indexed_records(path, task_family=family, writer=path.stem, subject=subject, decision=decision, source_kind=source_kind, source_ref=source_ref))
        return {"output": json.dumps({"task_family": family, "dag_slug": family, "records": records, "total": len(records)}), "title": "Read QA Round Records", "metadata": {"count": len(records)}}
    except (OSError, ValueError, TypeError, json.JSONDecodeError, sqlite3.Error) as exc:
        return {"error": "invalid_qa_history", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(qa_record_read(workspace_root=Path(args["workspace_root"]), task_family=args.get("task_family", ""), dag_slug=args.get("dag_slug", ""), round=args.get("round"), writer=args.get("writer", ""), subject=args.get("subject", ""), decision=args.get("decision", ""), source_kind=args.get("source_kind", ""), source_ref=args.get("source_ref", ""))))
