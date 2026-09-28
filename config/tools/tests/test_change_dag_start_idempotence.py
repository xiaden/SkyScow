"""An already-satisfied pending DAG must never be relaunched.

``dag_start`` admits a pending Change DAG, and the executor's success path ends
with a checkpoint that stages the entire working tree (``git add -A``).
Admitting a DAG whose root is already runtime-satisfied would create a second
checkpoint and sweep unrelated working-tree changes into it. These tests pin the
idempotent admission result and the absence of every launch side effect.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag  # noqa: E402
from common.helpers import change_dag_control as control  # noqa: E402
from common.helpers import change_dag_state as state_helper  # noqa: E402
from common.tools import dag_start as dag_start_module  # noqa: E402
from common.tools.dag_archive import dag_archive  # noqa: E402
from common.tools.dag_start import dag_start  # noqa: E402
from common.tools.dag_stop import dag_stop  # noqa: E402

SATISFIED = {"N3": "satisfied"}
IDEMPOTENT = {"state": "root_satisfied", "dag": "done", "root_satisfied": True, "idempotent": True}


def _make_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / ".keep").write_text("keep\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    return tmp_path


def _nodes() -> dict:
    # The only terminal is a ``run`` node: a satisfied run lowers to no
    # mechanical ops, so preflight is clean and root satisfaction is decided by
    # execution state alone.
    return {
        "N1": {"type": "semantic", "requirement": "complete", "requires": ["N2"], "decomposition_only": True},
        "N2": {"type": "semantic", "requirement": "verified", "requires": ["N3"]},
        "N3": {"type": "run", "command": ["python3", "-m", "compileall", "-q", "."]},
    }


def _write_bundle(root: Path, slug: str, state: dict | None = None) -> Path:
    bundle = root / change_dag.PENDING_DIR / slug
    bundle.mkdir(parents=True, exist_ok=True)
    dag = {"slug": slug, "anchor_commit": "a" * 40, "root": "N1", "nodes": _nodes()}
    (bundle / change_dag.DAG_FILENAME).write_text(json.dumps(dag), encoding="utf-8")
    (bundle / change_dag.STATE_FILENAME).write_text(json.dumps(state or {}), encoding="utf-8")
    (bundle / change_dag.WORK_LOG_FILENAME).write_text("", encoding="utf-8")
    return bundle


def _launch_spy(monkeypatch) -> list:
    """Record executor launch attempts without changing behavior."""
    calls: list = []
    real = subprocess.Popen

    def _spy(*args, **kwargs):
        command = args[0] if args else []
        if isinstance(command, (list, tuple)) and any("change_dag_executor" in str(part) or "common.tools.dag_executor" in str(part) for part in command):
            calls.append(list(command))
        return real(*args, **kwargs)

    monkeypatch.setattr(dag_start_module.subprocess, "Popen", _spy)
    return calls


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True).stdout


def _no_checkpoint(root: Path) -> None:
    assert "checkpoint" not in _git(root, "log", "--format=%s")


def test_launch_detector_matches_the_real_launch_command():
    # Positive control: the spy's predicate must match what dag_start actually
    # launches, otherwise `launches == []` would prove nothing.
    command = dag_start_module._launch_command("demo", Path("/tmp"), False)
    assert any("common.tools.dag_executor" in str(part) for part in command)


def test_satisfied_pending_dag_is_not_relaunched(tmp_path: Path, monkeypatch):
    root = _make_repo(tmp_path)
    _write_bundle(root, "done", SATISFIED)
    launches = _launch_spy(monkeypatch)

    result = dag_start("done", workspace_root=root)

    assert result == IDEMPOTENT
    assert launches == []
    assert control.queue_list(root) == []
    assert control.marker_path(root).exists() is False
    assert control.lock_acquirable(root)


def test_satisfied_start_writes_no_checkpoint_and_preserves_unrelated_changes(tmp_path: Path, monkeypatch):
    root = _make_repo(tmp_path)
    _write_bundle(root, "done", SATISFIED)
    launches = _launch_spy(monkeypatch)
    work_log = change_dag.work_log_path(root, "done")
    log_before = work_log.read_text(encoding="utf-8")

    # Unrelated changes present after the original run completed: an idempotent
    # re-admission must leave them uncommitted and untouched, and must not create
    # a second checkpoint or Work Log checkpoint record.
    (root / "unrelated.txt").write_text("post-run noise\n", encoding="utf-8")
    (root / ".keep").write_text("keep\nmodified after the original run\n", encoding="utf-8")
    head_before = _git(root, "rev-parse", "HEAD")
    porcelain_before = _git(root, "status", "--porcelain")
    assert porcelain_before  # the working tree really is dirty

    assert dag_start("done", workspace_root=root)["state"] == "root_satisfied"

    assert launches == []
    assert _git(root, "rev-parse", "HEAD") == head_before
    assert _git(root, "status", "--porcelain") == porcelain_before
    assert (root / "unrelated.txt").read_text(encoding="utf-8") == "post-run noise\n"
    _no_checkpoint(root)
    assert work_log.read_text(encoding="utf-8") == log_before
    assert [entry for entry in state_helper.read_work_log(root, "done") if entry.get("operation") == "checkpoint"] == []


def test_retry_true_cannot_relaunch_a_satisfied_dag(tmp_path: Path, monkeypatch):
    root = _make_repo(tmp_path)
    _write_bundle(root, "done", SATISFIED)
    launches = _launch_spy(monkeypatch)
    head_before = _git(root, "rev-parse", "HEAD")
    log_before = change_dag.work_log_path(root, "done").read_text(encoding="utf-8")

    result = dag_start("done", retry=True, workspace_root=root)

    assert result == IDEMPOTENT
    assert launches == []
    assert control.queue_list(root) == []
    assert control.marker_path(root).exists() is False
    assert control.lock_acquirable(root)
    assert _git(root, "rev-parse", "HEAD") == head_before
    _no_checkpoint(root)
    assert change_dag.work_log_path(root, "done").read_text(encoding="utf-8") == log_before


def test_unsatisfied_pending_dag_still_follows_admission_flow(tmp_path: Path):
    root = _make_repo(tmp_path)
    _write_bundle(root, "todo")
    acquired, fd = control.acquire_lock(root)
    assert acquired
    try:
        result = dag_start("todo", workspace_root=root)
        assert result == {"state": "queued", "dag": "todo", "position": 1}
        assert [entry["slug"] for entry in control.queue_list(root)] == ["todo"]
        assert dag_stop("todo", workspace_root=root)["state"] == "idle"
    finally:
        control.release_lock(fd)


def test_archived_dag_still_rejects_execution(tmp_path: Path):
    root = _make_repo(tmp_path)
    _write_bundle(root, "retired", SATISFIED)
    archived = dag_archive("retired", "superseded by parser-v2", workspace_root=root)
    assert archived["archived"] is True
    assert archived["state_at_archive"]["root_satisfied"] is True

    result = dag_start("retired", workspace_root=root)

    # The archived check precedes the satisfied check: retirement always wins.
    assert result["error"] == "dag_archived"
    assert control.queue_list(root) == []
    assert control.marker_path(root).exists() is False
