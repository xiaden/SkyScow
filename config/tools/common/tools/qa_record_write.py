"""Write validated terminal QA records atomically to a writer-isolated JSONL file."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any

from ..helpers.qa_round_records import (
    load_records,
    record_identity,
    record_path,
    validate_record,
)


def qa_record_write(record: dict[str, Any], *, workspace_root: Path) -> dict[str, Any]:
    """Validate and append a terminal QA record before returning.

    The validated record is serialized to the writer-isolated JSONL path under
    ``artifacts/logs/qa-rounds``. An exclusive advisory lock on the writer's
    history serializes the duplicate check and append so a repeated stable
    identity is rejected fail-closed while distinct findings remain allowed.
    The append uses ``O_APPEND``, flushes, and calls ``fsync`` before the
    success result is returned; this does not claim transactional semantics
    beyond that filesystem write boundary.

    Args:
        record: Terminal record containing task family, round, writer, agent,
            subject, decision, evidence, verification, provenance, and any
            applicable repair data.
        workspace_root: Workspace containing the artifacts directory.

    Returns:
        A structured success result with the relative path and validated
        record, or an ``invalid_qa_record`` error result when validation or
        writing fails.
    """
    try:
        checked = validate_record(record)
        path = record_path(workspace_root, checked["task_family"], checked["round"], checked["writer"])
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(path.name + ".lock")
        with open(lock_path, "a", encoding="utf-8") as lock_stream:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
            try:
                existing = load_records(path, task_family=checked["task_family"], writer=checked["writer"])
                identity = record_identity(checked)
                if any(record_identity(item) == identity for item in existing):
                    raise ValueError("duplicate record identity")
                line = json.dumps(checked, ensure_ascii=False, sort_keys=True) + "\n"
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                try:
                    with os.fdopen(fd, "a", encoding="utf-8") as stream:
                        stream.write(line)
                        stream.flush()
                        os.fsync(stream.fileno())
                except BaseException:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                    raise
            finally:
                fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
        return {"output": json.dumps({"path": str(path.relative_to(workspace_root)), "record": checked}), "title": "Write QA Round Record", "metadata": {"writer": checked["writer"], "round": checked["round"]}}
    except (OSError, ValueError, TypeError) as exc:
        return {"error": "invalid_qa_record", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(qa_record_write(args["record"], workspace_root=Path(args["workspace_root"]))))
