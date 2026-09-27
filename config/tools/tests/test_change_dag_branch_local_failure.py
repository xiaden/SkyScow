"""Regression tests for branch-local terminal-failure propagation.

A failed terminal must not become a global poison flag: it blocks only the work
that genuinely depends on that requirement. Independent and sibling branches
keep progressing, and the executor terminates cleanly once all independently
progressable work has finished.
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
from common.helpers import change_dag_state as state_helper  # noqa: E402
from common.helpers.change_dag_compiler import (  # noqa: E402
    compile_operations,
    ready_run_nodes,
)
from common.tools.dag_executor import run_execution  # noqa: E402


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def dag_with(nodes: dict, root: str = "N1", slug: str = "demo") -> dict:
    return {"slug": slug, "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def semantic(requirement: str = "r", satisfied_by=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if satisfied_by is not None:
        node["satisfied_by"] = satisfied_by
    return node


def edit(path: str, patch: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch}


def run(command=None) -> dict:
    return {"type": "run", "command": command or ["python3", "-m", "compileall", "-q", "."]}


def patch(path: str) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,1 @@\n-a\n+b\n"


def make_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / ".keep").write_text("keep\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    return tmp_path


def write_bundle(root: Path, slug: str, dag: dict, state: dict | None = None) -> None:
    bundle = root / "artifacts/change-dags/pending" / slug
    bundle.mkdir(parents=True)
    (bundle / "DAG.json").write_text(json.dumps(dag))
    (bundle / "EXECUTION_STATE.json").write_text(json.dumps(state or {}))
    (bundle / "WORK_LOG.jsonl").write_text("")


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    for name in ("a.txt", "b.txt", "c.txt", "s.txt", "u.txt"):
        (workspace / name).write_text("a\n")
    return workspace


# 1. ROOT has independent A and B. A fails. B mechanical work still executes.
def test_failed_sibling_branch_does_not_block_mechanical_work(tmp_path: Path):
    workspace = _workspace(tmp_path)
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N5"]),
            "N2": semantic("A", ["N3"]),
            "N3": edit("a.txt", patch("a.txt")),
            "N5": semantic("B", ["N6"]),
            "N6": edit("b.txt", patch("b.txt")),
        }
    )

    ops, conflicts, blocked = compile_operations(dag, {"N3": "failed"}, workspace)

    assert conflicts == []
    assert {op.path for op in ops} == {"b.txt"}
    assert all(entry.node_id != "N6" for entry in blocked)


def test_executor_still_runs_independent_branch_after_sibling_failure(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "a.txt").write_text("a\n")
    (root / "b.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N5"]),
            "N2": semantic("A", ["N3"]),
            "N3": edit("a.txt", patch("a.txt")),
            "N5": semantic("B", ["N6"]),
            "N6": edit("b.txt", patch("b.txt")),
        },
        slug="branchlocal",
    )
    write_bundle(root, "branchlocal", dag, state={"N3": "failed"})

    result = run_execution(root, "branchlocal")

    state = state_helper.read_state(root, "branchlocal")
    assert state["N3"] == "failed"
    assert state["N6"] == "satisfied"
    assert (root / "b.txt").read_text() == "b\n"
    assert (root / "a.txt").read_text() == "a\n"  # failed branch work is not applied
    assert result["state"] == "idle"
    assert result["root_satisfied"] is False


# 2. A fails. B's own prerequisites satisfy. B's RUN still becomes ready.
def test_run_on_independent_branch_is_ready_after_sibling_failure(tmp_path: Path):
    workspace = _workspace(tmp_path)
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N5"]),
            "N2": semantic("A", ["N3"]),
            "N3": edit("a.txt", patch("a.txt")),
            "N5": semantic("B", ["N6", "N7"]),
            "N6": edit("b.txt", patch("b.txt")),
            "N7": run(["python3", "-m", "compileall", "-q", "."]),
        }
    )

    # A's failure lives in a different root branch, so B's run is unaffected.
    assert ready_run_nodes(dag, {"N3": "failed"}, workspace) == []
    assert ready_run_nodes(dag, {"N3": "failed", "N6": "satisfied"}, workspace) == ["N7"]


# 3. A failure inside the SAME required semantic branch prevents work that
#    genuinely depends on that failed requirement.
def test_failed_prerequisite_in_same_branch_blocks_dependent_run(tmp_path: Path):
    workspace = _workspace(tmp_path)
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("verify", ["N3", "N4"]),
            "N3": semantic("implement", ["N5"]),
            "N4": run(["python3", "-m", "compileall", "-q", "."]),
            "N5": edit("b.txt", patch("b.txt")),
        }
    )

    # N4 runs only once N3's whole requirement branch is satisfied.
    assert ready_run_nodes(dag, {}, workspace) == []
    assert ready_run_nodes(dag, {"N5": "failed"}, workspace) == []
    assert ready_run_nodes(dag, {"N5": "satisfied"}, workspace) == ["N4"]


def test_failed_run_barrier_defers_mechanical_work_above_it(tmp_path: Path):
    workspace = _workspace(tmp_path)
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("aggregate", ["N3", "N7"]),
            "N3": semantic("verified", ["N4"]),
            "N4": semantic("inner", ["N5"]),
            "N5": run(["python3", "-m", "compileall", "-q", "."]),
            "N7": edit("u.txt", patch("u.txt")),
        }
    )

    ops, _conflicts, blocked = compile_operations(dag, {"N5": "failed"}, workspace)

    # N7 is above N5's run barrier in the same required subtree, so it waits.
    assert {entry.node_id for entry in blocked} == {"N7"}
    assert all(op.path != "u.txt" for op in ops)


# 4. Shared descendant/convergence does not make unrelated failure global.
def test_shared_descendant_failure_does_not_propagate_globally(tmp_path: Path):
    workspace = _workspace(tmp_path)
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N4", "N6"]),
            "N2": semantic("A", ["N3", "N9"]),
            "N4": semantic("B", ["N3", "N10"]),
            "N3": semantic("shared", ["N7"]),
            "N7": edit("s.txt", patch("s.txt")),
            "N6": semantic("C", ["N8"]),
            "N8": edit("c.txt", patch("c.txt")),
            "N9": edit("a.txt", patch("a.txt")),
            "N10": edit("b.txt", patch("b.txt")),
        }
    )

    ops, conflicts, blocked = compile_operations(dag, {"N7": "failed"}, workspace)

    assert conflicts == []
    # The shared failure stays local to the branches that require it: the
    # unrelated branch C and the siblings of the shared node keep progressing.
    assert {op.path for op in ops} == {"a.txt", "b.txt", "c.txt"}
    assert blocked == []
    # Branches that genuinely require the shared descendant cannot satisfy.
    satisfaction = change_dag.derived_satisfaction(dag, {"N7": "failed"})
    assert satisfaction["N2"] is False
    assert satisfaction["N4"] is False
    assert satisfaction["N1"] is False


# 5. Root remains unsatisfied when one required root branch failed even though
#    another branch completes.
def test_root_stays_unsatisfied_when_one_root_branch_failed(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "a.txt").write_text("a\n")
    (root / "b.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N5"]),
            "N2": semantic("A", ["N3"]),
            "N3": edit("a.txt", patch("a.txt")),
            "N5": semantic("B", ["N6", "N7"]),
            "N6": edit("b.txt", patch("b.txt")),
            "N7": run(["python3", "-m", "compileall", "-q", "."]),
        },
        slug="rootfail",
    )
    write_bundle(root, "rootfail", dag, state={"N3": "failed"})

    result = run_execution(root, "rootfail")

    state = state_helper.read_state(root, "rootfail")
    assert state["N3"] == "failed"
    assert state["N6"] == "satisfied"
    assert state["N7"] == "satisfied"
    assert result["state"] == "idle"
    assert result["root_satisfied"] is False
    assert change_dag.derived_satisfaction(dag, state)["N1"] is False


# 6. Executor terminates cleanly once all independently progressable work has
#    finished (no spin, no checkpoint, stable on a second pass).
def test_executor_terminates_cleanly_after_progressable_work_finishes(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "a.txt").write_text("a\n")
    (root / "b.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N5"]),
            "N2": semantic("A", ["N3"]),
            "N3": edit("a.txt", patch("a.txt")),
            "N5": semantic("B", ["N6", "N7"]),
            "N6": edit("b.txt", patch("b.txt")),
            "N7": run(["python3", "-m", "compileall", "-q", "."]),
        },
        slug="clean-stop",
    )
    write_bundle(root, "clean-stop", dag, state={"N3": "failed"})

    first = run_execution(root, "clean-stop")
    second = run_execution(root, "clean-stop")

    assert first["state"] == "idle"
    assert second["state"] == "idle"
    state = state_helper.read_state(root, "clean-stop")
    assert state["N6"] == "satisfied"
    assert state["N7"] == "satisfied"
    assert state["N3"] == "failed"
