"""Workspace-wide serialized Change DAG execution control."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from . import change_dag

CONTROL_DIR_NAME = "artifacts/change-dags/.control"
QUEUE_LOCK_NAME = "queue.lock"
INHERITED_DIFF_LIMIT = 65536


def control_dir(workspace_root: Path) -> Path:
    return Path(workspace_root) / CONTROL_DIR_NAME


def lock_path(workspace_root: Path) -> Path:
    return control_dir(workspace_root) / "lock"


def marker_path(workspace_root: Path) -> Path:
    return control_dir(workspace_root) / "marker.json"


def queue_path(workspace_root: Path) -> Path:
    return control_dir(workspace_root) / "queue.jsonl"


@contextlib.contextmanager
def _exclusive_file_lock(path: Path):
    """Hold a short-lived exclusive flock for a small control-file mutation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield fd
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def queue_lock(workspace_root: Path):
    """Serialize small FIFO queue read/modify/write mutations.

    This is separate from the long-lived execution lock: it is held only for the
    brief duration of a queue mutation so concurrent admissions cannot lose,
    duplicate, or reorder entries.
    """
    return _exclusive_file_lock(control_dir(workspace_root) / QUEUE_LOCK_NAME)


def mutation_lock(workspace_root: Path, slug: str):
    """Serialize graph mutations so concurrent authoring invocations cannot race."""
    return _exclusive_file_lock(control_dir(workspace_root) / f"dag-{change_dag._safe_slug(slug)}.lock")


def acquire_lock(workspace_root: Path) -> tuple[bool, int | None]:
    path = lock_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        os.close(fd)
        return False, None
    return True, fd


def release_lock(fd: int | None) -> None:
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def lock_acquirable(workspace_root: Path) -> bool:
    acquired, fd = acquire_lock(workspace_root)
    if acquired:
        release_lock(fd)
    return acquired


def read_marker(workspace_root: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(marker_path(workspace_root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) and isinstance(value.get("slug"), str) and isinstance(value.get("pid"), int) else None


def write_marker(workspace_root: Path, slug: str, pid: int) -> None:
    change_dag.atomic_write_json(marker_path(workspace_root), {"slug": slug, "pid": pid})


def remove_marker(workspace_root: Path) -> None:
    try:
        marker_path(workspace_root).unlink()
    except FileNotFoundError:
        pass


def marker_stale(workspace_root: Path) -> bool:
    return marker_path(workspace_root).is_file() and lock_acquirable(workspace_root)


def active_dag(workspace_root: Path) -> str | None:
    marker = read_marker(workspace_root)
    if marker is None or marker_stale(workspace_root):
        return None
    return marker["slug"]


def queue_list(workspace_root: Path) -> list[dict[str, Any]]:
    path = queue_path(workspace_root)
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("slug"), str):
            entries.append({"slug": value["slug"], "retry": bool(value.get("retry", False))})
    return entries


def _write_queue(workspace_root: Path, entries: list[dict[str, Any]]) -> None:
    path = queue_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(entry, separators=(",", ":")) + "\n" for entry in entries)
    fd, temporary = __import__("tempfile").mkstemp(prefix=".queue.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def enqueue(workspace_root: Path, slug: str, retry: bool = False) -> int:
    with queue_lock(workspace_root):
        entries = [entry for entry in queue_list(workspace_root) if entry["slug"] != slug]
        entries.append({"slug": slug, "retry": retry})
        _write_queue(workspace_root, entries)
    return len(entries)


def dequeue_next(workspace_root: Path) -> dict[str, Any] | None:
    with queue_lock(workspace_root):
        entries = queue_list(workspace_root)
        if not entries:
            return None
        first = entries.pop(0)
        _write_queue(workspace_root, entries)
    return first


def queue_remove(workspace_root: Path, slug: str) -> bool:
    with queue_lock(workspace_root):
        entries = queue_list(workspace_root)
        filtered = [entry for entry in entries if entry["slug"] != slug]
        if len(filtered) == len(entries):
            return False
        _write_queue(workspace_root, filtered)
    return True


def _git(workspace_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=workspace_root, capture_output=True, text=True, check=False)


def capture_inherited_state(workspace_root: Path) -> dict[str, Any]:
    """Record concrete starting-worktree evidence for later independent QA.

    A digest alone cannot distinguish inherited changes (which ``git add -A``
    will include in the checkpoint) from DAG-produced work, so concrete staged,
    unstaged, and untracked evidence is captured as well.
    """
    try:
        head = _git(workspace_root, "rev-parse", "HEAD")
        status = _git(workspace_root, "status", "--porcelain")
        diff = _git(workspace_root, "diff")
        staged = _git(workspace_root, "diff", "--cached")
        untracked = _git(workspace_root, "ls-files", "--others", "--exclude-standard")
        diff_text = diff.stdout if diff.returncode == 0 else ""
        return {
            "head": head.stdout.strip() if head.returncode == 0 else "",
            "porcelain": status.stdout if status.returncode == 0 else "",
            "diff": diff_text[:INHERITED_DIFF_LIMIT],
            "diff_truncated": len(diff_text) > INHERITED_DIFF_LIMIT,
            "diff_digest": hashlib.sha256(diff_text.encode()).hexdigest() if diff.returncode == 0 else "",
            "staged_diff": (staged.stdout if staged.returncode == 0 else "")[:INHERITED_DIFF_LIMIT],
            "untracked_files": [line for line in (untracked.stdout.splitlines() if untracked.returncode == 0 else []) if line],
        }
    except (OSError, subprocess.SubprocessError):
        return {"head": "", "porcelain": "", "diff": "", "diff_truncated": False, "diff_digest": "", "staged_diff": "", "untracked_files": []}


def checkpoint_commit(workspace_root: Path, slug: str, inherited: dict[str, Any]) -> dict[str, Any]:
    message = f"chore(change-dag): checkpoint {slug}\n\nExecutor-owned local checkpoint before independent QA. Not publication."
    try:
        add = _git(workspace_root, "add", "-A")
        if add.returncode != 0:
            return {"committed": False, "sha": None, "message": message, "inherited": inherited, "stdout": add.stdout, "stderr": add.stderr}
        commit = _git(workspace_root, "commit", "-m", message)
        if commit.returncode != 0:
            return {"committed": False, "sha": None, "message": message, "inherited": inherited, "stdout": commit.stdout, "stderr": commit.stderr or "nothing to commit"}
        sha = _git(workspace_root, "rev-parse", "HEAD")
        return {"committed": True, "sha": sha.stdout.strip() if sha.returncode == 0 else None, "message": message, "inherited": inherited, "stdout": commit.stdout, "stderr": commit.stderr}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"committed": False, "sha": None, "message": message, "inherited": inherited, "stdout": "", "stderr": str(exc)}


def stop_process_group(pid: int) -> bool:
    delivered = False
    try:
        os.killpg(pid, signal.SIGTERM)
        delivered = True
    except (ProcessLookupError, PermissionError):
        try:
            os.kill(pid, signal.SIGTERM)
            delivered = True
        except (ProcessLookupError, PermissionError):
            return False
    time.sleep(0.05)
    try:
        os.killpg(pid, 0)
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    return delivered
