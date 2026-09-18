"""Write validated terminal QA records atomically to a writer-isolated JSONL file."""
from __future__ import annotations

import fcntl
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from ..helpers.qa_round_records import (
    identity_index_path,
    record_identity_key,
    record_path,
    synchronize_identity_index,
    validate_record,
)




def qa_record_write(record: dict[str, Any], *, workspace_root: Path) -> dict[str, Any]:
    """Validate and append a terminal QA record before returning.

    The validated record is serialized to the writer-isolated JSONL path under
    ``artifacts/logs/qa-rounds``. An exclusive advisory lock on the writer's
    history serializes incremental duplicate detection and append so a repeated
    stable identity is rejected fail-closed while distinct findings remain
    allowed. The append uses ``O_APPEND``, flushes, and calls ``fsync`` before
    success is returned; the identity index is advanced only after that durable
    append, so a retry can rebuild a partially advanced index.
    """
    try:
        checked = validate_record(record)
        path = record_path(
            workspace_root,
            checked["task_family"],
            checked["round"],
            checked["writer"],
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(path.name + ".lock")
        with open(lock_path, "a", encoding="utf-8") as lock_stream:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
            try:
                index_path = identity_index_path(path)
                with sqlite3.connect(index_path) as index:
                    # The JSONL append is the durable source of truth. The
                    # SQLite index is derived state and may be rebuilt after a
                    # crash, so do not add a second synchronous durability
                    # barrier to every terminal record.
                    index.execute("PRAGMA synchronous = OFF")
                    synchronize_identity_index(
                        index,
                        path,
                        task_family=checked["task_family"],
                        writer=checked["writer"],
                    )
                    identity_key = record_identity_key(checked)
                    if index.execute(
                        "SELECT 1 FROM records WHERE identity = ?",
                        (identity_key,),
                    ).fetchone():
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

                    payload = json.dumps(checked, ensure_ascii=False, sort_keys=True)
                    index.execute(
                        "INSERT INTO records(identity, payload, subject_text, decision, "
                        "source_kind, source_ref) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            identity_key,
                            payload,
                            json.dumps(checked["subject"], sort_keys=True),
                            checked["decision"],
                            checked["source_kind"],
                            checked["source_ref"],
                        ),
                    )
                    index.execute(
                        "UPDATE metadata SET value = ? WHERE key = 'indexed_offset'",
                        (str(path.stat().st_size),),
                    )
                    index.execute(
                        "UPDATE metadata SET value = ? WHERE key = 'indexed_mtime_ns'",
                        (str(path.stat().st_mtime_ns),),
                    )
                    index.commit()
            finally:
                fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
        return {
            "output": json.dumps(
                {"path": str(path.relative_to(workspace_root)), "record": checked}
            ),
            "title": "Write QA Round Record",
            "metadata": {"writer": checked["writer"], "round": checked["round"]},
        }
    except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
        return {"error": "invalid_qa_record", "message": str(exc)}


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(qa_record_write(args["record"], workspace_root=Path(args["workspace_root"]))))
