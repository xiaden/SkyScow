"""Whole-DAG deterministic preflight (`executable` covers all specified work).

Runtime compilation is segmented at run barriers and driven by Execution State,
so a single state-aware pass only sees the first executable segment. Preflight
must still lower every currently specified terminal work item so a deterministic
contradiction hidden above a run barrier makes the DAG non-executable *before*
anything runs. The simulation must never write to the repository, never execute a
run command, and never materialise a projected worktree.
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
from common.helpers.change_dag_compiler_lowering import compile_operations  # noqa: E402
from common.helpers.change_dag_compiler_phase import (  # noqa: E402
    compile_whole_dag,
    preflight,
)
from common.helpers.change_dag_ops_views import preview  # noqa: E402
from common.tools.dag_executor import run_execution  # noqa: E402


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def dag_with(nodes: dict, root: str = "N1", slug: str = "demo") -> dict:
    # The root is always decomposition_only; fixtures only supply the graph.
    nodes.setdefault(root, {}).setdefault("decomposition_only", True)
    return {"slug": slug, "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def semantic(requirement: str = "r", requires=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if requires is not None:
        node["requires"] = requires
    return node


def edit(path: str, patch: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch}


def run(command=None) -> dict:
    return {"type": "run", "command": command or ["python3", "-m", "compileall", "-q", "."]}


def patch(path: str, old: str, new: str, line: int = 1) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"


def barrier_dag(lower_patch: str, higher_patch: str, command=None,
               higher_path: str = "f.txt", slug: str = "demo") -> dict:
    """root -> agg -> [verified -> inner -> (run, lower -> edit), higher edit].

    ``N7`` (the higher edit) sits above ``N5``'s run barrier, so runtime
    compilation defers it while ``N8`` (the lower edit) is inside the barrier.
    """
    return dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("aggregate", ["N3", "N7"]),
            "N3": semantic("verified", ["N4"]),
            "N4": semantic("inner", ["N5", "N6"]),
            "N5": run(command),
            "N6": semantic("lower", ["N8"]),
            "N8": edit("f.txt", lower_patch),
            "N7": edit(higher_path, higher_patch),
        },
        slug=slug,
    )


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


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    }


def _op_nodes(segments) -> set[str]:
    return {node for segment in segments for op in segment for node in op.nodes}


def _phase_for(segments, node_id: str) -> int:
    return next(
        index
        for index, phase in enumerate(segments)
        if any(node_id in op.nodes for op in phase)
    )


# ---------------------------------------------------------------------------
# 1. lower valid edit -> RUN -> higher conflicting edit
# ---------------------------------------------------------------------------
def test_higher_conflicting_edit_above_barrier_makes_dag_non_executable(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    dag = barrier_dag(patch("f.txt", "a", "b"), patch("f.txt", "a", "c"))

    # Runtime compilation only sees the first segment: the higher edit is gated.
    runtime_ops, _runtime_conflicts, runtime_blocked = compile_operations(dag, {}, workspace)
    assert {entry.node_id for entry in runtime_blocked} == {"N7"}
    assert {op.nodes[0] for op in runtime_ops} == {"N8"}

    # Whole-DAG lowering sees the higher edit contradicting the lower result.
    result = preflight(dag, {}, workspace)
    assert result["executable"] is False
    assert result["runtime_failures"] == []
    issue = next(issue for issue in result["issues"] if issue["kind"] == "context_conflict")
    assert "N7" in issue["nodes"]
    assert (workspace / "f.txt").read_text() == "a\n"


# ---------------------------------------------------------------------------
# 2. lower valid edit -> RUN -> higher valid edit consuming the lower result
# ---------------------------------------------------------------------------
def test_higher_edit_consuming_lower_result_is_executable_and_previewed(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    (workspace / "mod.py").write_text("x = 1\n")
    dag = barrier_dag(patch("f.txt", "a", "b"), patch("f.txt", "b", "c"), slug="compose")
    write_bundle(workspace, "compose", dag)

    result = preflight(dag, {}, workspace)
    assert result["executable"] is True
    assert result["issues"] == []

    segments, conflicts, _blocked = compile_whole_dag(dag, {}, workspace)
    assert conflicts == []
    assert len(segments) == 2
    assert _op_nodes(segments) == {"N7", "N8"}
    higher = next(op for op in segments[1] if "N7" in op.nodes)
    assert higher.applied == "c\n"

    payload = json.loads(preview(workspace, "compose")["output"])
    assert payload["executable"] is True
    assert payload["simulated_segments"] == 2
    assert payload["simulated_execution_phases"] == 2
    previewed = next(op for op in payload["ops"] if "N7" in op["nodes"])
    assert previewed["segment"] == 1
    assert previewed["execution_phase"] == 1
    assert previewed["applied"] == "c\n"

    # No run command executed and no repository write: compileall would have
    # produced __pycache__ for mod.py.
    assert not (workspace / "__pycache__").exists()
    assert (workspace / "f.txt").read_text() == "a\n"


# ---------------------------------------------------------------------------
# 3. empty and consecutive execution phases are preserved
# ---------------------------------------------------------------------------
def test_ready_run_before_higher_edit_advances_execution_phase(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("aggregate", ["N3", "N6"]),
            "N3": semantic("run branch", ["N4"]),
            "N4": semantic("ready run", ["N5"]),
            "N5": run(),
            "N6": edit("f.txt", patch("f.txt", "a", "b")),
        },
        slug="ready-run",
    )
    write_bundle(workspace, "ready-run", dag)

    segments, conflicts, blocked = compile_whole_dag(dag, {}, workspace)

    assert conflicts == []
    assert blocked == []
    assert segments[0] == []
    assert _phase_for(segments, "N6") == 1
    payload = json.loads(preview(workspace, "ready-run")["output"])
    operation = next(op for op in payload["ops"] if "N6" in op["nodes"])
    assert operation["segment"] == 1
    assert operation["execution_phase"] == 1
    assert payload["simulated_segments"] == 2
    assert payload["simulated_execution_phases"] == 2


def test_run_run_without_mechanical_work_preserves_both_crossings(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N10"]),
            "N2": semantic("aggregate", ["N4"]),
            "N4": semantic("second run parent", ["N3", "N5"]),
            "N3": semantic("first run parent", ["N6"]),
            "N6": run(),
            "N5": run(),
            "N10": edit("f.txt", patch("f.txt", "a", "b")),
        },
        slug="run-run",
    )

    segments, conflicts, blocked = compile_whole_dag(dag, {}, workspace)

    assert conflicts == []
    assert blocked == []
    assert segments[:2] == [[], []]
    assert _phase_for(segments, "N10") == 2
    assert len(segments) == 3


def test_two_ready_runs_share_one_execution_phase_crossing(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("aggregate", ["N3", "N9"]),
            "N3": semantic("parallel runs", ["N4", "N6"]),
            "N4": semantic("run one", ["N5"]),
            "N5": run(),
            "N6": semantic("run two", ["N7"]),
            "N7": run(),
            "N9": edit("f.txt", patch("f.txt", "a", "b")),
        },
        slug="parallel-runs",
    )

    segments, conflicts, blocked = compile_whole_dag(dag, {}, workspace)

    assert conflicts == []
    assert blocked == []
    assert segments[0] == []
    assert _phase_for(segments, "N9") == 1
    assert len(segments) == 2


def test_independent_mechanical_work_stays_in_current_execution_phase(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N5"]),
            "N2": semantic("ready run", ["N3"]),
            "N3": run(),
            "N5": edit("f.txt", patch("f.txt", "a", "b")),
        },
        slug="independent-work",
    )

    segments, conflicts, blocked = compile_whole_dag(dag, {}, workspace)

    assert conflicts == []
    assert blocked == []
    assert _phase_for(segments, "N5") == 0


# ---------------------------------------------------------------------------
# 4. two sequential run barriers with work between/above them
# ---------------------------------------------------------------------------
def test_preflight_traverses_sequential_run_barriers(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    (workspace / "g.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("aggregate", ["N3", "N7"]),
            "N3": semantic("stage1", ["N4"]),
            "N4": semantic("stage2", ["N5", "N6"]),
            "N5": run(),                      # runA
            "N6": semantic("stage3", ["N8"]),
            "N8": semantic("stage4", ["N9", "N10"]),
            "N9": run(),                      # runB, after stage3
            "N10": semantic("stage5", ["N11"]),
            "N11": edit("f.txt", patch("f.txt", "a", "b")),   # deep work
            "N7": edit("g.txt", patch("g.txt", "a", "A")),    # above both runs
        }
    )

    runtime_ops, _conflicts, runtime_blocked = compile_operations(dag, {}, workspace)
    assert {entry.node_id for entry in runtime_blocked} == {"N7"}
    assert {op.nodes[0] for op in runtime_ops} == {"N11"}

    segments, conflicts, blocked = compile_whole_dag(dag, {}, workspace)
    assert conflicts == []
    assert blocked == []
    assert _op_nodes(segments) == {"N7", "N11"}
    assert _phase_for(segments, "N11") == 0
    assert _phase_for(segments, "N7") == 2
    assert preflight(dag, {}, workspace)["executable"] is True


# ---------------------------------------------------------------------------
# 5. an unresolved semantic node elsewhere does not make executable false
# ---------------------------------------------------------------------------
def test_unresolved_semantic_node_does_not_block_whole_dag_preflight(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N9"]),
            "N2": semantic("needs a product decision"),        # unresolved semantic node
            "N9": semantic("aggregate", ["N3", "N7"]),
            "N3": semantic("verified", ["N4"]),
            "N4": semantic("inner", ["N5", "N6"]),
            "N5": run(),
            "N6": semantic("lower", ["N8"]),
            "N8": edit("f.txt", patch("f.txt", "a", "b")),
            "N7": edit("f.txt", patch("f.txt", "b", "c")),
        }
    )
    # The root is always decomposition_only and therefore locally resolved; N3
    # still has only semantic children without the decomposition flag.
    assert change_dag.unresolved_semantic_nodes(dag) == ["N2", "N3"]

    segments, conflicts, _blocked = compile_whole_dag(dag, {}, workspace)
    assert conflicts == []
    assert _op_nodes(segments) == {"N7", "N8"}
    result = preflight(dag, {}, workspace)
    assert result["executable"] is True
    assert result["issues"] == []


# ---------------------------------------------------------------------------
# 6. live drift in a later segment is runtime evidence, not deterministic
# ---------------------------------------------------------------------------
def test_later_segment_live_drift_is_runtime_not_deterministic(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    (workspace / "g.txt").write_text("drifted\n")
    dag = barrier_dag(
        patch("f.txt", "a", "b"),
        patch("g.txt", "a", "A"),          # never applicable to the live g.txt
        higher_path="g.txt",
    )

    _segments, conflicts, _blocked = compile_whole_dag(dag, {}, workspace)
    assert [(conflict.path, conflict.scope) for conflict in conflicts] == [("g.txt", "runtime")]

    result = preflight(dag, {}, workspace)
    assert result["executable"] is True
    assert result["issues"] == []
    assert any(entry["path"] == "g.txt" for entry in result["runtime_failures"])


# ---------------------------------------------------------------------------
# 7. the executor still stops at the barrier and defers higher work
# ---------------------------------------------------------------------------
def test_executor_stops_at_barrier_and_defers_higher_work(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("a\n")
    (root / "g.txt").write_text("a\n")
    (root / "bad.py").write_text("def (:\n")
    dag = barrier_dag(
        patch("f.txt", "a", "b"),
        patch("g.txt", "a", "A"),
        command=["python3", "-m", "compileall", "-q", "bad.py"],  # deterministically fails
        higher_path="g.txt",
    )
    dag["slug"] = "segmented"
    write_bundle(root, "segmented", dag)

    # Whole-DAG deterministic lowering is fine; runtime segmentation still holds.
    assert preflight(dag, {}, root)["executable"] is True

    run_execution(root, "segmented")

    state = state_helper.read_state(root, "segmented")
    assert state["N5"] == "failed"
    assert state["N8"] == "satisfied"
    assert state["N7"] == "not_satisfied"
    assert (root / "f.txt").read_text() == "b\n"      # lower work applied
    assert (root / "g.txt").read_text() == "a\n"      # higher work deferred
    assert change_dag.derived_satisfaction(dag, state)["N1"] is False


# ---------------------------------------------------------------------------
# 8. preview/preflight perform zero repository writes
# ---------------------------------------------------------------------------
def test_preview_and_preflight_write_nothing(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("a\n")
    (root / "g.txt").write_text("a\n")
    (root / "mod.py").write_text("x = 1\n")
    dag = barrier_dag(patch("f.txt", "a", "b"), patch("g.txt", "a", "A"),
                      higher_path="g.txt", slug="readonly")
    write_bundle(root, "readonly", dag)

    before = snapshot(root)
    assert preflight(dag, {}, root)["executable"] is True
    json.loads(preview(root, "readonly")["output"])
    after = snapshot(root)

    assert after == before
    assert not (root / "__pycache__").exists()
