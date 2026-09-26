"""Start a Change DAG, returning promptly after detached admission."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
from ..helpers import change_dag, change_dag_compiler as compiler, change_dag_control as control, change_dag_state as state_helper

# Observable fallback flag: set only when detached Popen is unavailable.
SYNCHRONOUS_FALLBACK_USED = False


def _launch_command(slug: str, root: Path, retry: bool) -> list[str]:
    return [sys.executable, "-m", "common.tools.dag_executor", slug, "--workspace-root", str(root)] + (["--retry"] if retry else [])


def dag_start(slug: str, retry: bool = False, *, workspace_root: Path) -> dict:
    global SYNCHRONOUS_FALLBACK_USED
    root = Path(workspace_root)
    try:
        dag, _, _ = change_dag.read_dag(root, slug)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": "invalid_dag", "message": str(exc)}
    errors = change_dag.validate_dag(dag)
    if errors:
        return {"error": "invalid_dag", "issues": errors}
    preflight = compiler.preflight(dag, state_helper.read_state(root, slug), root)
    if not preflight["executable"]:
        return {"error": "not_executable", "issues": preflight["issues"]}
    active = control.active_dag(root)
    if active == slug:
        marker = control.read_marker(root) or {}
        return {"state": "running", "dag": slug, "pid": marker.get("pid"), "idempotent": True}
    if control.marker_stale(root):
        marker = control.read_marker(root)
        if marker:
            from .dag_executor import reconcile_interrupted
            reconcile_interrupted(root, marker["slug"])
        control.remove_marker(root)
    acquired, fd = control.acquire_lock(root)
    if not acquired:
        position = control.enqueue(root, slug, retry)
        return {"state": "queued", "dag": slug, "position": position}

    from . import dag_executor
    log_path = change_dag.work_log_path(root, slug).with_name("executor.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        stream = log_path.open("a", encoding="utf-8")
    except OSError as exc:
        control.release_lock(fd)
        return {"error": "executor_log_unavailable", "message": str(exc), "dag": slug}

    # The synchronous fallback applies ONLY to a genuine Popen failure (detached
    # execution unsupported). A marker-write failure after a successful launch
    # must never trigger it, or the detached child and the in-process loop would
    # both run the same DAG.
    try:
        child = subprocess.Popen(_launch_command(slug, root, retry), cwd=Path(__file__).parents[2], stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, start_new_session=True, close_fds=True, pass_fds=(fd,))
    except (OSError, ValueError):
        SYNCHRONOUS_FALLBACK_USED = True
        try:
            result = dag_executor.run_execution(root, slug, retry)
        finally:
            stream.close()
            control.remove_marker(root)
            control.release_lock(fd)
        return {**result, "detached": False, "synchronous_fallback": True}
    finally:
        stream.close()

    try:
        control.write_marker(root, slug, child.pid)
    except (OSError, ValueError) as exc:
        control.stop_process_group(child.pid)
        control.release_lock(fd)
        return {"error": "marker_write_failed", "message": str(exc), "dag": slug}

    # Launch + marker succeeded. Close the parent's descriptor without an
    # explicit LOCK_UN: the child's inherited descriptor references the same
    # open-file-description and keeps the flock held for the child's lifetime.
    os.close(fd)
    return {"state": "running", "dag": slug, "pid": child.pid, "detached": True}


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(dag_start(args["slug"], args.get("retry", False), workspace_root=Path(args["workspace_root"]))))
