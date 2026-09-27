"""F9-B: retry admission must evaluate the effective state retry will attempt.

``dag_start(retry=True)`` must reset ``failed -> not_satisfied`` *before* the
admission preflight, so a deterministic intra-DAG conflict that retry would hit
is refused at admission instead of being admitted and only discovered after the
executor resets. Ordinary live-repository drift remains an admitted, recoverable
terminal failure, and satisfied work is never replayed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag  # noqa: E402
from common.helpers import change_dag_compiler as compiler  # noqa: E402
from common.helpers import change_dag_control as control  # noqa: E402
from common.helpers import change_dag_state as state_helper  # noqa: E402
from common.tools.dag_start import dag_start  # noqa: E402
from common.tools.dag_status import dag_status  # noqa: E402
from common.tools.dag_stop import dag_stop  # noqa: E402


def make_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / ".keep").write_text("keep\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    return tmp_path


def write_raw_dag(root: Path, slug: str, dag: dict) -> None:
    bundle = root / "artifacts/change-dags/pending" / slug
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "DAG.json").write_text(json.dumps(dag), encoding="utf-8")


def semantic(requirement: str, children: list[str]) -> dict:
    return {"type": "semantic", "requirement": requirement, "satisfied_by": children}


def edit(path: str, old: str, new: str, *, line: int = 1) -> dict:
    return {"type": "edit", "path": path, "patch": f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"}


def _settled(root: Path, slug: str) -> dict:
    for _ in range(400):
        status = dag_status(slug, workspace_root=root)
        if status["state"] in {"idle", "root_satisfied"}:
            return status
        time.sleep(0.05)
    return dag_status(slug, workspace_root=root)


# ---------------------------------------------------------------------------
# Root cause: stored ``failed`` state hides the deterministic conflict
# ---------------------------------------------------------------------------
def test_stored_failed_state_hides_the_conflict_that_retry_would_hit(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("foo\n", encoding="utf-8")
    write_raw_dag(root, "conflict", {
        "slug": "conflict", "anchor_commit": "a" * 40, "root": "N1",
        "nodes": {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N10", "N11"]),
            "N10": edit("f.txt", "foo", "bar"),
            "N11": edit("f.txt", "foo", "baz"),
        },
    })
    dag = change_dag.read_dag(root, "conflict")[0]

    stale = compiler.preflight(dag, {"N10": "failed", "N11": "failed"}, root)
    effective = compiler.preflight(dag, {"N10": "not_satisfied", "N11": "not_satisfied"}, root)

    # Stored failed state: both nodes skipped -> looks executable (the bug).
    assert stale["executable"] is True
    # Effective retry state: the deterministic conflict is visible.
    assert effective["executable"] is False
    assert any(issue["kind"] == "context_conflict" for issue in effective["issues"])


# ---------------------------------------------------------------------------
# Deterministically invalid retry is refused at admission, repo untouched
# ---------------------------------------------------------------------------
def test_retry_admission_refuses_deterministic_intra_dag_conflict(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("foo\n", encoding="utf-8")
    write_raw_dag(root, "conflict", {
        "slug": "conflict", "anchor_commit": "a" * 40, "root": "N1",
        "nodes": {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N10", "N11"]),
            "N10": edit("f.txt", "foo", "bar"),
            "N11": edit("f.txt", "foo", "baz"),
        },
    })
    state_helper.write_state(root, "conflict", {"N10": "failed", "N11": "failed"})
    state_path = change_dag.state_json_path(root, "conflict")
    state_before = state_path.read_text(encoding="utf-8")

    result = dag_start("conflict", retry=True, workspace_root=root)

    assert result["error"] == "not_executable"
    assert result["issues"]
    assert control.lock_acquirable(root)
    assert not control.marker_path(root).exists()
    assert (root / "f.txt").read_text(encoding="utf-8") == "foo\n"
    # Admission is read-only: the stored retry state is not rewritten.
    assert state_path.read_text(encoding="utf-8") == state_before


def test_retry_admission_preserves_satisfied_work_and_still_refuses(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("foo\n", encoding="utf-8")
    # N9 already satisfied; N10/N11 are conflicting failures. Resetting only the
    # failures must still expose a deterministic conflict without replaying N9.
    write_raw_dag(root, "mixed", {
        "slug": "mixed", "anchor_commit": "a" * 40, "root": "N1",
        "nodes": {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N9", "N10", "N11"]),
            "N9": edit("f.txt", "foo", "FOO"),
            "N10": edit("f.txt", "foo", "bar"),
            "N11": edit("f.txt", "foo", "baz"),
        },
    })
    original = {"N9": "satisfied", "N10": "failed", "N11": "failed"}
    state_helper.write_state(root, "mixed", original)

    result = dag_start("mixed", retry=True, workspace_root=root)

    assert result["error"] == "not_executable"
    assert state_helper.read_state(root, "mixed") == original
    assert (root / "f.txt").read_text(encoding="utf-8") == "foo\n"


# ---------------------------------------------------------------------------
# Ordinary live drift stays admitted and is a recoverable terminal failure
# ---------------------------------------------------------------------------
def test_retry_admission_still_admits_recoverable_live_drift(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("baz\n", encoding="utf-8")
    write_raw_dag(root, "drift", {
        "slug": "drift", "anchor_commit": "a" * 40, "root": "N1",
        "nodes": {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N9", "N10"]),
            # N9 is satisfied and must not be replayed.
            "N9": edit("f.txt", "alpha", "ALPHA"),
            # N10 fails only because the live file drifted away from "foo".
            "N10": edit("f.txt", "foo", "bar"),
        },
    })
    state_helper.write_state(root, "drift", {"N9": "satisfied", "N10": "failed"})

    result = dag_start("drift", retry=True, workspace_root=root)
    assert result.get("error") is None, result

    status = _settled(root, "drift")
    # The retry ran, hit ordinary drift, and settled as a recoverable failure.
    assert status["state"] == "idle"
    assert status["failed"] == ["N10"]
    assert state_helper.read_state(root, "drift") == {"N9": "satisfied", "N10": "failed"}
    assert (root / "f.txt").read_text(encoding="utf-8") == "baz\n"

    if control.marker_path(root).exists():
        dag_stop("drift", workspace_root=root)
    assert control.lock_acquirable(root)
