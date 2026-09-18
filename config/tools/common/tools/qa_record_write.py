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
    validate_record,
)


def _synchronize_identity_index(
    connection: sqlite3.Connection,
    path: Path,
    *,
    task_family: str,
    writer: str,
) -> None:
    """Create or advance the duplicate-identity index under the writer lock."""
    connection.execute(
        "CREATE TABLE IF NOT EXISTS identities (identity TEXT PRIMARY KEY)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    row = connection.execute(
        "SELECT value FROM metadata WHERE key = 'indexed_offset'"
    ).fetchone()
    current_size = path.stat().st_size if path.exists() else 0
    indexed_offset = int(row[0]) if row is not None else -1

    if indexed_offset < 0 or indexed_offset > current_size:
        connection.execute("DELETE FROM identities")
        indexed_offset = 0

    if indexed_offset < current_size:
        with path.open("rb") as stream:
            stream.seek(indexed_offset)
            tail = stream.read()
        for raw_line in tail.splitlines():
            if not raw_line.strip():
                continue
            checked = validate_record(json.loads(raw_line))
            if checked["task_family"] != task_family or checked["writer"] != writer:
                raise ValueError("cross-family or writer-mismatched history")
            connection.execute(
                "INSERT INTO identities(identity) VALUES (?)",
                (record_identity_key(checked),),
            )

    connection.execute(
        "INSERT INTO metadata(key, value) VALUES ('indexed_offset', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(current_size),),
    )
    connection.commit()


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
                    _synchronize_identity_index(
                        index,
                        path,
                        task_family=checked["task_family"],
                        writer=checked["writer"],
                    )
                    identity_key = record_identity_key(checked)
                    if index.execute(
                        "SELECT 1 FROM identities WHERE identity = ?",
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

                    index.execute(
                        "INSERT INTO identities(identity) VALUES (?)",
                        (identity_key,),
                    )
                    index.execute(
                        "UPDATE metadata SET value = ? WHERE key = 'indexed_offset'",
                        (str(path.stat().st_size),),
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
