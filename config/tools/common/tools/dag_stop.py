"""Stop a running Change DAG and deterministically start the next queued one.

Stopping is split from succession so queue progression does not depend on the
executor winning a race against ``stop_process_group``'s SIGKILL: ``dag_stop``
signals the executor, confirms it has exited, reconciles and clears the marker,
then hands off to the shared ``_launch_next`` launch path under the workspace
lock. Both that path and the executor's own cleanup are idempotent, so exactly
one of them launches the next DAG.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from ..helpers import change_dag_control as control

# Bounded waits: succession must not hang if a concurrently-finishing executor
# still holds the lock, and a missing process must not block indefinitely.
_SUCCESSION_LOCK_WAIT_SECONDS = 3.0
_EXECUTOR_EXIT_WAIT_SECONDS = 5.0


def _executor_exited(pid: int, timeout: float) -> bool:
    """Best-effort wait for ``pid`` to exit, reaping it when it is our child."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            reaped, _ = os.waitpid(pid, os.WNOHANG)
            if reaped == pid:
                return True
        except ChildProcessError:
            pass
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)


def _start_next(workspace_root: Path) -> None:
    from .dag_executor import _launch_next

    _launch_next(workspace_root, wait_seconds=_SUCCESSION_LOCK_WAIT_SECONDS)


def dag_stop(slug: str, *, workspace_root: Path) -> dict:
    root = Path(workspace_root)
    if control.queue_remove(root, slug):
        return {"state": "idle", "dag": slug}
    marker = control.read_marker(root)
    if marker and marker.get("slug") == slug:
        control.stop_process_group(int(marker["pid"]))
        _executor_exited(int(marker["pid"]), _EXECUTOR_EXIT_WAIT_SECONDS)
        from .dag_executor import reconcile_interrupted

        reconcile_interrupted(root, slug)
        # Only clear the marker if it still belongs to the stopped DAG: the
        # executor's own cleanup may already have launched the next queued DAG
        # and written its marker, which must survive.
        current = control.read_marker(root)
        if current is None or current.get("slug") == slug:
            control.remove_marker(root)
        _start_next(root)
        return {"state": "idle", "dag": slug}
    if control.marker_stale(root):
        stale = control.read_marker(root)
        if stale:
            from .dag_executor import reconcile_interrupted

            reconcile_interrupted(root, stale["slug"])
        control.remove_marker(root)
    return {"state": "idle", "dag": slug}


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(dag_stop(args["slug"], workspace_root=Path(args["workspace_root"]))))
