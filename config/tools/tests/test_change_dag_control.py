from __future__ import annotations

import re
import subprocess
from pathlib import Path

from common.helpers.change_dag_control import (
    acquire_lock, active_dag, capture_inherited_state, checkpoint_commit, dequeue_next,
    enqueue, lock_acquirable, marker_stale, queue_list, queue_remove, read_marker,
    release_lock, remove_marker, write_marker,
)


def test_lock_and_marker(tmp_path: Path):
    ok, fd = acquire_lock(tmp_path)
    assert ok and fd is not None and not lock_acquirable(tmp_path)
    write_marker(tmp_path, "demo", 99999999)
    assert read_marker(tmp_path)["slug"] == "demo"
    assert not marker_stale(tmp_path) and active_dag(tmp_path) == "demo"
    release_lock(fd)
    assert lock_acquirable(tmp_path) and marker_stale(tmp_path) and active_dag(tmp_path) is None
    remove_marker(tmp_path)
    assert read_marker(tmp_path) is None


def test_queue_fifo_and_duplicates(tmp_path: Path):
    assert enqueue(tmp_path, "a") == 1
    assert enqueue(tmp_path, "b", retry=True) == 2
    assert enqueue(tmp_path, "a", retry=True) == 2
    assert queue_list(tmp_path) == [{"slug": "b", "retry": True}, {"slug": "a", "retry": True}]
    assert queue_remove(tmp_path, "b")
    assert dequeue_next(tmp_path) == {"slug": "a", "retry": True}
    assert dequeue_next(tmp_path) is None


def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "base.txt").write_text("base")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    return tmp_path


def test_capture_and_checkpoint(tmp_path: Path):
    repo = git_repo(tmp_path)
    (repo / "change.txt").write_text("change")
    inherited = capture_inherited_state(repo)
    assert re.fullmatch(r"[0-9a-f]{40}", inherited["head"])
    assert "?? change.txt" in inherited["porcelain"]
    result = checkpoint_commit(repo, "demo", inherited)
    assert result["committed"] and re.fullmatch(r"[0-9a-f]{40}", result["sha"])
    assert result["inherited"] == inherited
    second = checkpoint_commit(repo, "demo", inherited)
    assert not second["committed"]
