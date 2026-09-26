from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag_control as control
from common.helpers import change_dag_policy as policy
from common.helpers import change_dag_state as state_helper
from common.tools import dag_executor
from common.tools.dag_archive import dag_archive
from common.tools.dag_executor import reconcile_interrupted, run_execution
from common.tools.dag_start import dag_start
from common.tools.dag_status import dag_status
from common.tools.dag_stop import dag_stop


def _alive(pid: int) -> bool:
    # Treat a zombie (killed child awaiting reap by a non-reaping parent) as
    # dead; it no longer holds execution resources.
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    tail = stat.rsplit(")", 1)[-1].strip()
    state = tail.split(" ", 1)[0] if tail else ""
    return state not in {"Z", "X", "x", ""}


def _wait_dead(pid: int, attempts: int = 200) -> bool:
    for _ in range(attempts):
        if not _alive(pid):
            return True
        time.sleep(0.02)
    return not _alive(pid)


@pytest.fixture
def nested_pytest_on_path(monkeypatch) -> None:
    """Make a nested ``python3 -m pytest`` importable.

    The suite's autouse ``isolated_home`` fixture redirects HOME, which hides the
    real user-site install of pytest from any subprocess. Point PYTHONPATH at the
    site-packages directory pytest is actually loaded from so run commands can
    execute real pytest verification.
    """
    site = str(Path(pytest.__file__).resolve().parents[1])
    existing = os.environ.get("PYTHONPATH")
    monkeypatch.setenv("PYTHONPATH", site if not existing else site + os.pathsep + existing)


def make_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / ".keep").write_text("keep\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    return tmp_path


def write_dag(root: Path, slug: str, command: list[str] | None = None) -> None:
    nodes = {
        "N1": {"type": "semantic", "requirement": "complete", "satisfied_by": ["N2", "N3"]},
        "N2": {"type": "create", "path": "created.txt", "content": "created\n"},
        "N3": {"type": "semantic", "requirement": "verified", "satisfied_by": ["N4"]},
        "N4": {"type": "run", "command": command or ["python3", "-m", "compileall", "-q", "."]},
    }
    write_raw_dag(root, slug, {"slug": slug, "anchor_commit": "a" * 40, "root": "N1", "nodes": nodes})


def write_raw_dag(root: Path, slug: str, dag: dict) -> None:
    bundle = root / "artifacts/change-dags/pending" / slug
    bundle.mkdir(parents=True)
    (bundle / "DAG.json").write_text(json.dumps(dag))


def wait_root(root: Path, slug: str) -> dict:
    for _ in range(100):
        result = dag_status(slug, workspace_root=root)
        if result["root_satisfied"] or result["state"] == "idle":
            return result
        time.sleep(0.05)
    pytest.fail("DAG did not finish")


def test_detached_end_to_end(tmp_path: Path):
    root = make_repo(tmp_path)
    write_dag(root, "demo")
    started = dag_start("demo", workspace_root=root)
    assert started["state"] == "running"
    assert started["detached"] is True
    result = wait_root(root, "demo")
    assert result["root_satisfied"]
    assert (root / "created.txt").is_file()
    for _ in range(100):
        entries = state_helper.read_work_log(root, "demo")
        if any(entry.get("operation") == "checkpoint" for entry in entries):
            break
        time.sleep(0.01)
    assert {entry["operation"] for entry in entries} >= {"create", "run", "checkpoint"}
    log = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=root, text=True, capture_output=True, check=True)
    assert log.stdout.strip() == "chore(change-dag): checkpoint demo"

    # The checkpoint WORK_LOG entry must carry the committed SHA and the
    # captured starting-worktree evidence, not just an operation marker.
    checkpoint = next(entry for entry in entries if entry.get("operation") == "checkpoint")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()
    assert checkpoint["committed"] is True
    assert checkpoint["sha"] == head
    assert set(checkpoint["inherited"]) >= {"head", "porcelain"}
    assert len(checkpoint["inherited"]["head"]) == 40
    assert checkpoint["message"].startswith("chore(change-dag): checkpoint demo")
    assert control.lock_acquirable(root)
    assert not control.marker_path(root).exists()


def test_failure_has_no_checkpoint(tmp_path: Path, nested_pytest_on_path):
    root = make_repo(tmp_path)
    # Allowlisted command that genuinely exits non-zero (pytest exit code 4 for a
    # missing path) so this exercises a real failed run, not a policy rejection.
    write_dag(root, "bad", ["python3", "-m", "pytest", "-q", "missing_test_file.py"])
    result = dag_start("bad", workspace_root=root)
    assert result["state"] == "running"
    status = wait_root(root, "bad")
    assert status["failed"] == ["N4"]
    assert "checkpoint bad" not in subprocess.run(["git", "log", "--format=%s"], cwd=root, text=True, capture_output=True, check=True).stdout
    assert control.lock_acquirable(root)


def test_retry_resets_failed_nodes(tmp_path: Path, nested_pytest_on_path):
    root = make_repo(tmp_path)
    write_dag(root, "retry", ["python3", "-m", "pytest", "-q", "missing_test_file.py"])
    state_helper.write_state(root, "retry", {"N2": "satisfied", "N4": "failed"})
    result = run_execution(root, "retry", retry=True)
    assert result["state"] == "idle"
    assert state_helper.read_state(root, "retry")["N4"] == "failed"


def test_queue_and_stop(tmp_path: Path):
    root = make_repo(tmp_path)
    write_dag(root, "queued")
    acquired, fd = control.acquire_lock(root)
    assert acquired
    try:
        result = dag_start("queued", workspace_root=root)
        assert result == {"state": "queued", "dag": "queued", "position": 1}
        assert dag_stop("queued", workspace_root=root)["state"] == "idle"
    finally:
        control.release_lock(fd)


def test_stale_marker_reconciles_and_archive(tmp_path: Path):
    root = make_repo(tmp_path)
    write_dag(root, "stale")
    control.write_marker(root, "stale", 999999)
    status = dag_status("stale", workspace_root=root)
    assert status["state"] == "idle"
    assert not control.marker_path(root).exists()
    assert dag_archive("stale", workspace_root=root)["error"] == "incomplete_dag"


def test_interrupted_run_fails(tmp_path: Path):
    root = make_repo(tmp_path)
    write_dag(root, "interrupt")
    state_helper.write_state(root, "interrupt", {"N4": "in_progress"})
    result = reconcile_interrupted(root, "interrupt")
    assert result["reconciled"][0]["resolved"] == "failed"


def test_archive_after_satisfaction(tmp_path: Path):
    root = make_repo(tmp_path)
    write_dag(root, "archive")
    assert dag_start("archive", workspace_root=root)["state"] == "running"
    assert wait_root(root, "archive")["root_satisfied"]
    archived = dag_archive("archive", workspace_root=root)
    assert archived["archived"]
    assert (root / "artifacts/change-dags/completed/archive/DAG.json").exists()


def test_dag_start_rejects_non_executable_dag(tmp_path: Path):
    root = make_repo(tmp_path)
    write_raw_dag(root, "blocked", {
        "slug": "blocked",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "complete", "satisfied_by": ["N2", "N3"]},
            "N2": {"type": "create", "path": "dup.txt", "content": "one\n"},
            "N3": {"type": "create", "path": "dup.txt", "content": "two\n"},
        },
    })
    result = dag_start("blocked", workspace_root=root)
    assert result["error"] == "not_executable"
    assert result["issues"]
    # Admission is refused before any lock/marker is taken.
    assert control.lock_acquirable(root)
    assert not control.marker_path(root).exists()


def test_dag_start_rejects_invalid_dag(tmp_path: Path):
    root = make_repo(tmp_path)
    write_raw_dag(root, "invalid", {
        "slug": "invalid",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "complete", "satisfied_by": ["N99"]},
        },
    })
    result = dag_start("invalid", workspace_root=root)
    assert result["error"] == "invalid_dag"
    assert result["issues"]
    assert control.lock_acquirable(root)
    assert not control.marker_path(root).exists()


def test_reconcile_interrupted_marks_present_create_satisfied(tmp_path: Path):
    root = make_repo(tmp_path)
    write_dag(root, "reconcile-present")
    (root / "created.txt").write_text("created\n", encoding="utf-8")
    state_helper.write_state(root, "reconcile-present", {"N2": "in_progress"})
    result = reconcile_interrupted(root, "reconcile-present")
    assert result["reconciled"][0]["resolved"] == "satisfied"
    assert state_helper.read_state(root, "reconcile-present")["N2"] == "satisfied"


def test_reconcile_interrupted_marks_absent_create_not_satisfied(tmp_path: Path):
    root = make_repo(tmp_path)
    write_dag(root, "reconcile-absent")
    state_helper.write_state(root, "reconcile-absent", {"N2": "in_progress"})
    result = reconcile_interrupted(root, "reconcile-absent")
    assert result["reconciled"][0]["resolved"] == "not_satisfied"
    assert state_helper.read_state(root, "reconcile-absent")["N2"] == "not_satisfied"


def test_reconcile_interrupted_marks_ambiguous_create_failed(tmp_path: Path):
    root = make_repo(tmp_path)
    write_dag(root, "reconcile-ambiguous")
    (root / "created.txt").write_text("different\n", encoding="utf-8")
    state_helper.write_state(root, "reconcile-ambiguous", {"N2": "in_progress"})
    result = reconcile_interrupted(root, "reconcile-ambiguous")
    assert result["reconciled"][0]["resolved"] == "failed"
    assert state_helper.read_state(root, "reconcile-ambiguous")["N2"] == "failed"


def test_reconcile_interrupted_logs_work_log_entry(tmp_path: Path):
    root = make_repo(tmp_path)
    write_dag(root, "reconcile-log")
    state_helper.write_state(root, "reconcile-log", {"N2": "in_progress"})
    reconcile_interrupted(root, "reconcile-log")
    entries = [entry for entry in state_helper.read_work_log(root, "reconcile-log") if entry.get("operation") == "reconcile"]
    assert len(entries) == 1
    assert entries[0]["nodes"] == ["N2"]
    assert entries[0]["previous"] == "in_progress"
    assert entries[0]["resolved"] == "not_satisfied"


# ---------------------------------------------------------------------------
# F1: a mechanical node that cannot be applied must not loop forever
# ---------------------------------------------------------------------------
def test_unapplied_edit_terminates_and_records_failure_once(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("hello\n", encoding="utf-8")
    write_raw_dag(root, "loop", {
        "slug": "loop",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "satisfied_by": ["N2"]},
            "N2": {"type": "edit", "path": "f.txt", "patch": "--- a/f.txt\n+++ b/f.txt\n@@ -1,1 +1,1 @@\n-goodbye\n+hi\n"},
        },
    })

    def _boom(signum, frame):
        raise TimeoutError("run_execution did not terminate")

    previous = signal.signal(signal.SIGALRM, _boom)
    signal.setitimer(signal.ITIMER_REAL, 20)
    try:
        result = run_execution(root, "loop")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)

    assert result["state"] == "idle"
    assert result["failed"] == ["N2"]
    assert state_helper.read_state(root, "loop")["N2"] == "failed"
    failures = [entry for entry in state_helper.read_work_log(root, "loop") if entry.get("nodes") == ["N2"] and entry.get("result") == "failure"]
    assert len(failures) == 1
    assert control.lock_acquirable(root)
    assert not control.marker_path(root).exists()


# ---------------------------------------------------------------------------
# F3: run command process groups are terminated on timeout and on stop
# ---------------------------------------------------------------------------
_SPAWNER_SOURCE = (
    "import os, subprocess, sys, time\n"
    "\n"
    "_child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
    "with open(os.environ['GRANDCHILD_PID_FILE'], 'w') as _handle:\n"
    "    _handle.write(str(_child.pid))\n"
    "\n"
    "def test_spawn_grandchild():\n"
    "    time.sleep(60)\n"
)


def _write_spawner(root: Path, name: str) -> None:
    (root / name).write_text(_SPAWNER_SOURCE, encoding="utf-8")


def test_run_timeout_kills_process_group(tmp_path: Path, monkeypatch, nested_pytest_on_path):
    root = make_repo(tmp_path)
    pid_file = tmp_path / "grandchild.pid"
    _write_spawner(root, "test_spawn_timeout.py")
    monkeypatch.setenv("GRANDCHILD_PID_FILE", str(pid_file))
    monkeypatch.setattr(dag_executor, "RUN_TIMEOUT_SECONDS", 6)

    write_dag(root, "slow", ["python3", "-m", "pytest", "-q", "test_spawn_timeout.py"])
    result = run_execution(root, "slow")

    assert result["state"] == "idle"
    assert state_helper.read_state(root, "slow")["N4"] == "failed"
    assert pid_file.is_file()
    assert _wait_dead(int(pid_file.read_text().strip()))


def test_dag_stop_kills_run_process_group(tmp_path: Path, nested_pytest_on_path):
    root = make_repo(tmp_path)
    pid_file = tmp_path / "grandchild_stop.pid"
    _write_spawner(root, "test_spawn_stop.py")
    write_dag(root, "stoppable", ["python3", "-m", "pytest", "-q", "test_spawn_stop.py"])

    previous = os.environ.get("GRANDCHILD_PID_FILE")
    os.environ["GRANDCHILD_PID_FILE"] = str(pid_file)
    try:
        started = dag_start("stoppable", workspace_root=root)
        assert started["state"] == "running"
        for _ in range(400):
            if pid_file.is_file():
                break
            time.sleep(0.05)
        assert pid_file.is_file(), "run command never spawned its grandchild"

        grandchild = int(pid_file.read_text().strip())
        assert dag_stop("stoppable", workspace_root=root)["state"] == "idle"
        assert _wait_dead(grandchild)
        assert control.lock_acquirable(root)
        assert not control.marker_path(root).exists()
    finally:
        if previous is None:
            os.environ.pop("GRANDCHILD_PID_FILE", None)
        else:
            os.environ["GRANDCHILD_PID_FILE"] = previous


# ---------------------------------------------------------------------------
# F6: policy rejects only boundary-anchored publication/lifecycle forms
# ---------------------------------------------------------------------------
def test_policy_accepts_verification_tokens_containing_pr():
    assert policy.validate_run_command(["pytest", "tests/test_provider.py"]) == (True, "")
    assert policy.validate_run_command(["ruff", "check", "src/prompts"]) == (True, "")
    assert policy.validate_run_command(["python3", "-m", "pytest", "-q", "test_progress.py"]) == (True, "")
    assert policy.validate_run_command(["cargo", "build", "--release"]) == (True, "")


def test_policy_rejects_publication_and_lifecycle_commands():
    for command in (
        ["gh", "pr", "create"],
        ["git", "commit", "-m", "x"],
        ["git", "push"],
        ["npm", "publish"],
    ):
        allowed, reason = policy.validate_run_command(command)
        assert allowed is False, command
        assert reason


# ---------------------------------------------------------------------------
# F4: marker-write failure after launch must never trigger the sync fallback
# ---------------------------------------------------------------------------
def test_marker_write_failure_never_double_runs(tmp_path: Path, monkeypatch):
    import common.tools.dag_start as dag_start_module

    root = make_repo(tmp_path)
    write_dag(root, "marker")
    monkeypatch.setattr(dag_start_module, "SYNCHRONOUS_FALLBACK_USED", False)

    def _boom(*args, **kwargs):
        raise OSError("marker write failed")

    monkeypatch.setattr(control, "write_marker", _boom)
    result = dag_start("marker", workspace_root=root)

    assert result["error"] == "marker_write_failed"
    assert dag_start_module.SYNCHRONOUS_FALLBACK_USED is False
    assert result.get("detached") is not True
    assert not control.marker_path(root).exists()
    for _ in range(200):
        if control.lock_acquirable(root):
            break
        time.sleep(0.02)
    assert control.lock_acquirable(root)


# ---------------------------------------------------------------------------
# F5: a failed launch must not lose the queued request
# ---------------------------------------------------------------------------
def test_launch_next_preserves_queue_on_spawn_failure(tmp_path: Path, monkeypatch):
    root = make_repo(tmp_path)
    write_dag(root, "next")
    assert control.enqueue(root, "next", False) == 1

    def _boom(*args, **kwargs):
        raise OSError("spawn failed")

    monkeypatch.setattr(dag_executor.subprocess, "Popen", _boom)
    dag_executor._launch_next(root)

    assert [entry["slug"] for entry in control.queue_list(root)] == ["next"]
    assert control.lock_acquirable(root)


# ---------------------------------------------------------------------------
# F10b: dag_stop deterministically launches the next queued DAG
# ---------------------------------------------------------------------------
def test_stop_starts_next_queued_dag(tmp_path: Path, nested_pytest_on_path):
    root = make_repo(tmp_path)
    pid_file = tmp_path / "alpha_grandchild.pid"
    _write_spawner(root, "test_spawn_alpha.py")
    write_dag(root, "alpha", ["python3", "-m", "pytest", "-q", "test_spawn_alpha.py"])
    # beta creates a distinct path so it does not conflict with alpha's create.
    write_raw_dag(root, "beta", {
        "slug": "beta",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "complete", "satisfied_by": ["N2", "N3"]},
            "N2": {"type": "create", "path": "beta.txt", "content": "beta\n"},
            "N3": {"type": "semantic", "requirement": "verified", "satisfied_by": ["N4"]},
            "N4": {"type": "run", "command": ["python3", "-m", "compileall", "-q", "."]},
        },
    })

    previous = os.environ.get("GRANDCHILD_PID_FILE")
    os.environ["GRANDCHILD_PID_FILE"] = str(pid_file)

    def _boom(signum, frame):
        raise TimeoutError("stop/succession did not complete")

    guard = signal.signal(signal.SIGALRM, _boom)
    signal.setitimer(signal.ITIMER_REAL, 60)
    try:
        started = dag_start("alpha", workspace_root=root)
        assert started["state"] == "running"
        for _ in range(400):
            if pid_file.is_file():
                break
            time.sleep(0.05)
        assert pid_file.is_file(), "alpha never started its run subprocess"
        alpha_grandchild = int(pid_file.read_text().strip())

        assert dag_start("beta", workspace_root=root) == {"state": "queued", "dag": "beta", "position": 1}

        assert dag_stop("alpha", workspace_root=root)["state"] == "idle"

        beta_state = None
        for _ in range(400):
            status = dag_status("beta", workspace_root=root)
            if status["state"] in {"running", "root_satisfied"}:
                beta_state = status["state"]
                break
            time.sleep(0.05)
        assert beta_state in {"running", "root_satisfied"}, dag_status("beta", workspace_root=root)
        for _ in range(200):
            if (root / "beta.txt").is_file():
                break
            time.sleep(0.05)
        assert (root / "beta.txt").is_file(), "beta was not executed by succession"
        assert (root / "created.txt").is_file(), "alpha's satisfied work was rolled back"

        assert _wait_dead(alpha_grandchild)
        alpha_status = dag_status("alpha", workspace_root=root)
        assert alpha_status["state"] != "running"
        assert alpha_status["terminal"].get("N4") == "failed"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, guard)
        if previous is None:
            os.environ.pop("GRANDCHILD_PID_FILE", None)
        else:
            os.environ["GRANDCHILD_PID_FILE"] = previous


# ---------------------------------------------------------------------------
# F10b: successor launch transfers the workspace lock and is idempotent
# ---------------------------------------------------------------------------
def test_successor_launch_holds_lock_and_never_double_launches(tmp_path: Path, nested_pytest_on_path):
    root = make_repo(tmp_path)
    pid_file = tmp_path / "beta_grandchild.pid"
    _write_spawner(root, "test_spawn_beta.py")
    write_dag(root, "beta", ["python3", "-m", "pytest", "-q", "test_spawn_beta.py"])
    # A distinct successor so a double launch/dequeue is observable.
    write_raw_dag(root, "gamma", {
        "slug": "gamma",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "complete", "satisfied_by": ["N2", "N3"]},
            "N2": {"type": "create", "path": "gamma.txt", "content": "gamma\n"},
            "N3": {"type": "semantic", "requirement": "verified", "satisfied_by": ["N4"]},
            "N4": {"type": "run", "command": ["python3", "-m", "compileall", "-q", "."]},
        },
    })

    previous = os.environ.get("GRANDCHILD_PID_FILE")
    os.environ["GRANDCHILD_PID_FILE"] = str(pid_file)
    beta_grandchild: int | None = None

    def _boom(signum, frame):
        raise TimeoutError("successor launch invariant did not complete")

    guard = signal.signal(signal.SIGALRM, _boom)
    signal.setitimer(signal.ITIMER_REAL, 60)
    try:
        control.enqueue(root, "beta", False)
        control.enqueue(root, "gamma", False)
        assert dag_executor._launch_next(root) is True

        for _ in range(400):
            if pid_file.is_file():
                break
            time.sleep(0.05)
        assert pid_file.is_file(), "beta never started its run subprocess"
        beta_grandchild = int(pid_file.read_text().strip())

        # Invariant 1: the successor's inherited descriptor holds the workspace
        # flock. If _launch_next released it (LOCK_UN / release_lock) instead of
        # transferring via os.close, this would be True and a second DAG could
        # execute concurrently in the same workspace.
        assert control.lock_acquirable(root) is False

        # Invariant 2: a second launch attempt under the still-held lock must
        # neither launch nor dequeue the queued successor.
        assert dag_executor._launch_next(root, wait_seconds=0) is False
        assert [entry["slug"] for entry in control.queue_list(root)] == ["gamma"]
        assert not (root / "gamma.txt").exists()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, guard)
        # Keep teardown deterministic: do not leave gamma queued for dag_stop's
        # succession to launch while beta is being stopped.
        control.queue_remove(root, "gamma")
        dag_stop("beta", workspace_root=root)
        if beta_grandchild is not None:
            assert _wait_dead(beta_grandchild)
        for _ in range(400):
            if control.lock_acquirable(root):
                break
            time.sleep(0.05)
        assert control.lock_acquirable(root)
        assert not control.marker_path(root).exists()
        if previous is None:
            os.environ.pop("GRANDCHILD_PID_FILE", None)
        else:
            os.environ["GRANDCHILD_PID_FILE"] = previous
