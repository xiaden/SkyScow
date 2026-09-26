"""Detached one-shot Change DAG executor.

The executor is deliberately out-of-band: ``dag_start`` launches this module in
its own session with redirected stdio, while the workspace flock inherited from
the starter serializes the whole execution lifetime.

Every ``run`` command is launched as its own process group so that a timeout or
an executor shutdown (SIGTERM/SIGINT from ``dag_stop``) terminates the command's
entire process tree, not just the direct child.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ..helpers import change_dag, change_dag_compiler as compiler
from ..helpers import change_dag_control as control
from ..helpers import change_dag_policy as policy
from ..helpers import change_dag_state as state_helper

RUN_TIMEOUT_SECONDS = 300

# Process groups of currently active run commands. The shutdown handler kills
# every registered group so grandchildren cannot outlive a stop/timeout.
_ACTIVE_RUN_GROUPS: set[int] = set()
_SHUTDOWN_REQUESTED = False


def _terminal_defaults(dag: dict[str, Any], state: dict[str, str]) -> dict[str, str]:
    result = dict(state)
    for node_id, node in change_dag.node_map(dag).items():
        if node.get("type") in change_dag.TERMINAL_TYPES:
            result.setdefault(node_id, "not_satisfied")
    return result


def reconcile_interrupted(workspace_root: Path, slug: str) -> dict[str, Any]:
    dag, _, _ = change_dag.read_dag(workspace_root, slug)
    current = state_helper.read_state(workspace_root, slug)
    state = _terminal_defaults(dag, current)
    reconciled: list[dict[str, Any]] = []
    for node_id, previous in list(state.items()):
        if previous != "in_progress":
            continue
        kind = change_dag.node_type(dag, node_id)
        if kind == "run":
            resolved, evidence = "failed", "interrupted run is never replayed automatically"
        else:
            present = compiler.node_present(dag, node_id, workspace_root)
            resolved = {"present": "satisfied", "absent": "not_satisfied"}.get(present, "failed")
            evidence = present
        state_helper.set_node_state(state, node_id, resolved)
        entry = state_helper.log_reconciliation(node_id, previous, resolved, reason="interrupted execution", evidence=evidence)
        state_helper.append_work_log(workspace_root, slug, entry)
        reconciled.append(entry)
    if reconciled:
        state_helper.write_state(workspace_root, slug, state)
    return {"dag": slug, "reconciled": reconciled}


def _terminate_group(pgid: int, grace: float = 0.2) -> None:
    """Terminate a run command's process group (direct child + grandchildren)."""
    if pgid <= 0:
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        return
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except (ProcessLookupError, PermissionError):
            return
        except OSError:
            return
        time.sleep(0.02)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _request_shutdown(signum: int, frame: Any) -> None:
    """Signal handler: flag shutdown and immediately kill active run groups."""
    global _SHUTDOWN_REQUESTED
    _SHUTDOWN_REQUESTED = True
    for pgid in list(_ACTIVE_RUN_GROUPS):
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(pgid, sig)
            except (ProcessLookupError, PermissionError, OSError):
                break


def _run_command(command: list[str], workspace_root: Path) -> tuple[int | None, str, str, str | None]:
    allowed, reason = policy.validate_run_command(command)
    if not allowed:
        return None, "", "", reason
    try:
        process = subprocess.Popen(
            command,
            cwd=workspace_root,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as exc:
        return None, "", "", str(exc)
    pgid = process.pid  # start_new_session makes the child a process-group leader
    _ACTIVE_RUN_GROUPS.add(pgid)
    try:
        try:
            stdout, stderr = process.communicate(timeout=RUN_TIMEOUT_SECONDS)
            return process.returncode, stdout, stderr, None
        except subprocess.TimeoutExpired:
            _terminate_group(pgid)
            stdout, stderr = process.communicate()
            return 124, stdout or "", stderr or "", "timeout"
    finally:
        _ACTIVE_RUN_GROUPS.discard(pgid)


def _descriptive(slug: str, state: dict[str, str], status: str) -> dict[str, Any]:
    return {
        "state": status,
        "dag": slug,
        "root_satisfied": False,
        "failed": [node for node, value in state.items() if value == "failed"],
        "in_progress": [node for node, value in state.items() if value == "in_progress"],
        "state_map": state,
    }


def run_execution(workspace_root: Path, slug: str, retry: bool = False) -> dict[str, Any]:
    global _SHUTDOWN_REQUESTED
    _SHUTDOWN_REQUESTED = False
    workspace_root = Path(workspace_root)
    dag, _, _ = change_dag.read_dag(workspace_root, slug)
    current = state_helper.read_state(workspace_root, slug)
    state = _terminal_defaults(dag, current)
    if retry:
        for node_id, value in list(state.items()):
            if value == "failed":
                state[node_id] = "not_satisfied"
        state_helper.write_state(workspace_root, slug, state)

    inherited = control.capture_inherited_state(workspace_root)
    reconcile_interrupted(workspace_root, slug)
    state = _terminal_defaults(dag, state_helper.read_state(workspace_root, slug))

    while not _SHUTDOWN_REQUESTED:
        satisfaction = change_dag.derived_satisfaction(dag, state)
        if satisfaction.get(dag["root"], False):
            checkpoint = control.checkpoint_commit(workspace_root, slug, inherited)
            state_helper.append_work_log(workspace_root, slug, state_helper.log_checkpoint(slug, sha=checkpoint.get("sha"), committed=bool(checkpoint.get("committed")), inherited=inherited, message=checkpoint.get("message", "")))
            return {"state": "root_satisfied", "dag": slug, "checkpoint": checkpoint}

        changed = False

        ops, conflicts, _blocked = compiler.compile_operations(dag, state, workspace_root)
        if conflicts:
            recorded = False
            for conflict in conflicts:
                newly_failed = False
                for node_id in conflict.nodes:
                    if state.get(node_id) not in {"satisfied", "failed"}:
                        state[node_id] = "failed"
                        newly_failed = True
                if newly_failed:
                    state_helper.append_work_log(workspace_root, slug, {"operation": "compile", "result": "failure", "path": conflict.path, "nodes": conflict.nodes, "detail": conflict.reason})
                    recorded = True
            if recorded:
                state_helper.write_state(workspace_root, slug, state)
                changed = True

        # Defense in depth: never re-apply work whose terminal node already failed.
        # Recovery is owned by dag_start(retry=true), which resets failed -> not_satisfied.
        ops = [op for op in ops if not any(state.get(node_id) in {"satisfied", "failed"} for node_id in op.nodes)]
        if ops:
            for op in ops:
                for node_id in op.nodes:
                    state[node_id] = "in_progress"
            state_helper.write_state(workspace_root, slug, state)
            results = compiler.apply_compiled(ops, workspace_root)
            for result in results:
                outcome = "success" if result.get("ok") else "failure"
                for node_id in result.get("nodes", []):
                    state[node_id] = "satisfied" if result.get("ok") else "failed"
                state_helper.append_work_log(workspace_root, slug, state_helper.log_file_operation(result.get("nodes", []), result.get("action", "edit"), path=result.get("path", ""), result=outcome, detail=result.get("error", "")))
            state_helper.write_state(workspace_root, slug, state)
            changed = True

        ready = compiler.ready_run_nodes(dag, state, workspace_root)
        if ready:
            for node_id in ready:
                if _SHUTDOWN_REQUESTED:
                    break
                command = list(change_dag.node_map(dag)[node_id].get("command", []))
                state[node_id] = "in_progress"
                state_helper.write_state(workspace_root, slug, state)
                code, stdout, stderr, error = _run_command(command, workspace_root)
                ok = error is None and code == 0
                state[node_id] = "satisfied" if ok else "failed"
                state_helper.append_work_log(workspace_root, slug, state_helper.log_run(node_id, command, stdout=stdout, stderr=stderr, exit_code=code, result="success" if ok else "failure"))
                state_helper.write_state(workspace_root, slug, state)
            changed = True

        if _SHUTDOWN_REQUESTED:
            return _descriptive(slug, state, "stopped")
        if not changed:
            # No node transitioned and no new run became ready: the remaining
            # reachable work is blocked/failed/unresolved. Terminate rather than
            # spin (and never clear failed state here).
            return _descriptive(slug, state, "idle")
        time.sleep(0.01)

    return _descriptive(slug, state, "stopped")


def _release_inherited_lock(workspace_root: Path) -> None:
    # close_fds + pass_fds means the only non-stdio descriptor inherited here
    # is the starter's lock.  Locate it by its proc target, then unlock/close it.
    try:
        lock_target = str(control.lock_path(workspace_root).resolve())
        for entry in Path("/proc/self/fd").iterdir():
            try:
                if os.path.realpath(entry) == lock_target:
                    fd = int(entry.name)
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    os.close(fd)
                    return
            except (OSError, ValueError):
                continue
    except OSError:
        return


def _launch_next(workspace_root: Path, *, wait_seconds: float = 0.0) -> bool:
    """Launch the first queued DAG, transferring the workspace lock to it.

    This is the single launch path used both by the executor's own cleanup and
    by ``dag_stop``'s deterministic succession. It is idempotent under the
    workspace lock: only one caller can hold the lock, and while holding it any
    marker belongs to an already-stopped executor (a live owner would still
    hold the lock), so a stale marker is cleared before deciding to launch.

    ``wait_seconds`` lets ``dag_stop`` briefly retry a lock held by a
    concurrently-finishing executor. Returns True iff a DAG was launched.
    """
    workspace_root = Path(workspace_root)
    if not control.queue_list(workspace_root):
        return False
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while True:
        acquired, fd = control.acquire_lock(workspace_root)
        if acquired:
            break
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)
    transferred = False
    try:
        # Holding the lock proves no live executor owns this marker.
        control.remove_marker(workspace_root)
        entries = control.queue_list(workspace_root)
        if not entries:
            return False
        entry = entries[0]
        child: subprocess.Popen | None = None
        try:
            log_path = change_dag.work_log_path(workspace_root, entry["slug"]).with_name("executor.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            stream = log_path.open("a", encoding="utf-8")
            try:
                child = subprocess.Popen([sys.executable, "-m", "common.tools.dag_executor", entry["slug"], "--workspace-root", str(workspace_root)] + (["--retry"] if entry.get("retry") else []), cwd=Path(__file__).parents[2], stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, start_new_session=True, close_fds=True, pass_fds=(fd,))
            finally:
                stream.close()
            control.write_marker(workspace_root, entry["slug"], child.pid)
        except OSError:
            if child is not None:
                control.stop_process_group(child.pid)
            return False  # entry preserved for a later launch attempt

        # Launch succeeded: remove the queued entry and hand the lock to the
        # child's inherited descriptor (do NOT LOCK_UN, which would release the
        # shared open-file-description lock the child relies on).
        control.dequeue_next(workspace_root)
        os.close(fd)
        transferred = True
        return True
    finally:
        if not transferred:
            control.release_lock(fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--retry", action="store_true")
    args = parser.parse_args()
    root = Path(args.workspace_root)
    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)
    result: dict[str, Any] = {"state": "idle", "dag": args.slug}
    try:
        result = run_execution(root, args.slug, args.retry)
    finally:
        if _SHUTDOWN_REQUESTED:
            try:
                reconcile_interrupted(root, args.slug)
            except (FileNotFoundError, ValueError):
                pass
        control.remove_marker(root)
        _release_inherited_lock(root)
        _launch_next(root)
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
