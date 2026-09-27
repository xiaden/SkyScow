"""One canonical compiler phase for execution, whole-DAG preview, and validation.

Execution, preview, and validation used to determine "what mechanical work is
compilable now" and "which run nodes are ready" through separate paths, so a
change in one could silently diverge from the others. These tests pin the single
canonical primitive -- :func:`compile_phase` -- as the shared determination,
prove preview compiles the whole DAG exactly once, and prove the executor
observes the same phase/frontier decisions the whole-DAG simulator does.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag_compiler  # noqa: E402
from common.helpers import change_dag_compiler_phase as compiler_phase  # noqa: E402
from common.helpers.change_dag_compiler import (  # noqa: E402
    compile_phase,
    compile_whole_dag,
    preflight,
    ready_run_nodes,
)
from common.helpers.change_dag_ops import preview, validate  # noqa: E402
from common.tools.dag_executor import run_execution  # noqa: E402


# ---------------------------------------------------------------------------
# Builders (mirrors test_change_dag_whole_dag_preflight.py)
# ---------------------------------------------------------------------------
def dag_with(nodes: dict, root: str = "N1", slug: str = "demo") -> dict:
    return {"slug": slug, "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def semantic(requirement: str = "r", satisfied_by=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if satisfied_by is not None:
        node["satisfied_by"] = satisfied_by
    return node


def edit(path: str, patch_text: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch_text}


def run(command=None) -> dict:
    return {"type": "run", "command": command or ["python3", "-m", "compileall", "-q", "."]}


def patch(path: str, old: str = "a", new: str = "b", line: int = 1) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"


def barrier_dag(lower_patch: str, higher_patch: str, slug: str = "demo") -> dict:
    """root -> agg -> [verified -> inner -> (run, lower -> edit), higher edit].

    ``N7`` (the higher edit) sits above ``N5``'s run barrier, so runtime
    compilation defers it while ``N8`` (the lower edit) sits inside the barrier.
    """
    return dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("aggregate", ["N3", "N7"]),
            "N3": semantic("verified", ["N4"]),
            "N4": semantic("inner", ["N5", "N6"]),
            "N5": run(),
            "N6": semantic("lower", ["N8"]),
            "N8": edit("f.txt", lower_patch),
            "N7": edit("f.txt", higher_patch),
        },
        slug=slug,
    )


def independent_barrier_dag(slug: str = "demo") -> dict:
    """root -> agg -> [verified -> inner -> (run, lower edit), higher edit].

    The higher edit (``N6``) touches a different file than the lower one, so
    replaying the canonical phase one step at a time needs no repository overlay
    to reproduce the whole-DAG simulator's segments.
    """
    return dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("aggregate", ["N3", "N6"]),
            "N3": semantic("verified", ["N4"]),
            "N4": semantic("inner", ["N5", "N8"]),
            "N5": run(),
            "N8": edit("f.txt", patch("f.txt", "a", "b")),
            "N6": edit("g.txt", patch("g.txt", "a", "A")),
        },
        slug=slug,
    )


def make_repo(root: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / ".keep").write_text("keep\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    return root


def write_bundle(root: Path, slug: str, dag: dict, state: dict | None = None) -> None:
    bundle = root / "artifacts/change-dags/pending" / slug
    bundle.mkdir(parents=True)
    (bundle / "DAG.json").write_text(json.dumps(dag))
    (bundle / "EXECUTION_STATE.json").write_text(json.dumps(state or {}))
    (bundle / "WORK_LOG.jsonl").write_text("")


def _nodes(ops) -> list[str]:
    return sorted(node for op in ops for node in op.nodes)


def _segment_nodes(segments) -> list[list[str]]:
    return [_nodes(segment) for segment in segments]


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    (workspace / "g.txt").write_text("a\n")
    return workspace


# ---------------------------------------------------------------------------
# 1. compile_phase is the whole-DAG simulator's own step
# ---------------------------------------------------------------------------
def test_compile_phase_is_the_first_whole_dag_segment(tmp_path: Path):
    workspace = _workspace(tmp_path)
    dag = independent_barrier_dag()

    segments, conflicts, blocked = compile_whole_dag(dag, {}, workspace)
    assert _segment_nodes(segments) == [["N8"], ["N6"]]
    assert conflicts == []
    assert blocked == []

    first = compile_phase(dag, {}, workspace)
    assert _nodes(first.ops) == _nodes(segments[0])
    assert first.conflicts == []
    assert {entry.node_id for entry in first.blocked} == {"N6"}


def test_replaying_compile_phase_reproduces_every_whole_dag_segment(tmp_path: Path):
    workspace = _workspace(tmp_path)
    dag = independent_barrier_dag()

    segments, _conflicts, _blocked = compile_whole_dag(dag, {}, workspace)

    state: dict[str, str] = {}
    replayed: list[list[str]] = []
    for _ in range(10):
        phase = compile_phase(dag, state, workspace)
        progressed = bool(phase.ops or phase.ready_runs)
        if progressed:
            replayed.append(_nodes(phase.ops))
        for op in phase.ops:
            for node_id in op.nodes:
                state[node_id] = "satisfied"
        for node_id in phase.ready_runs:
            state[node_id] = "satisfied"
        if not progressed:
            break

    assert replayed == _segment_nodes(segments)


# ---------------------------------------------------------------------------
# 2. the ready-run frontier is the same determination for both
# ---------------------------------------------------------------------------
def test_ready_frontier_comes_from_the_canonical_phase(tmp_path: Path):
    workspace = _workspace(tmp_path)
    dag = barrier_dag(patch("f.txt", "a", "b"), patch("f.txt", "b", "c"))

    state = {"N8": "satisfied"}
    phase = compile_phase(dag, state, workspace)

    assert phase.ops == []
    assert phase.ready_runs == ready_run_nodes(dag, state, workspace) == ["N5"]


# ---------------------------------------------------------------------------
# 3. preview compiles the whole DAG exactly once
# ---------------------------------------------------------------------------
def _counting_compiler(monkeypatch) -> list[int]:
    calls: list[int] = []
    real = change_dag_compiler.compile_whole_dag

    def counted(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    # Preview compiles through the facade attribute; standalone preflight compiles
    # through the phase module's own global, so both bindings are counted.
    monkeypatch.setattr(change_dag_compiler, "compile_whole_dag", counted)
    monkeypatch.setattr(compiler_phase, "compile_whole_dag", counted)
    return calls


def test_preview_compiles_the_whole_dag_once(tmp_path: Path, monkeypatch):
    workspace = make_repo(tmp_path)
    (workspace / "f.txt").write_text("a\n")
    dag = barrier_dag(patch("f.txt", "a", "b"), patch("f.txt", "b", "c"), slug="compose")
    write_bundle(workspace, "compose", dag)

    calls = _counting_compiler(monkeypatch)
    payload = json.loads(preview(workspace, "compose")["output"])

    assert len(calls) == 1
    assert payload["executable"] is True
    assert payload["simulated_segments"] == 2


def test_standalone_preflight_still_compiles_the_whole_dag(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n")
    dag = barrier_dag(patch("f.txt", "a", "b"), patch("f.txt", "b", "c"))

    calls = _counting_compiler(monkeypatch)
    result = preflight(dag, {}, workspace)

    assert len(calls) == 1
    assert result["executable"] is True


# ---------------------------------------------------------------------------
# 4. preview and validation report the same compilation
# ---------------------------------------------------------------------------
def _issue_identities(payload) -> set[tuple]:
    return {
        (issue["kind"], issue.get("path"), tuple(issue.get("nodes") or []))
        for issue in payload["issues"]
        if issue["kind"] not in {"schema", "structure"}
    }


def test_preview_and_validate_agree_on_an_executable_dag(tmp_path: Path):
    workspace = make_repo(tmp_path)
    (workspace / "f.txt").write_text("a\n")
    # The higher edit consumes what the lower edit produced.
    dag = barrier_dag(patch("f.txt", "a", "b"), patch("f.txt", "b", "c"), slug="agree")
    write_bundle(workspace, "agree", dag)

    previewed = json.loads(preview(workspace, "agree")["output"])
    validated = json.loads(validate(workspace, "agree")["output"])

    assert previewed["executable"] == validated["executable"] is True
    assert previewed["issues"] == []
    assert _issue_identities(validated) == set()


def test_preview_and_validate_agree_on_a_non_executable_dag(tmp_path: Path):
    workspace = make_repo(tmp_path)
    (workspace / "f.txt").write_text("a\n")
    # Both edits rewrite the same line from the same base: a deterministic conflict.
    dag = barrier_dag(patch("f.txt", "a", "b"), patch("f.txt", "a", "c"), slug="conflict")
    write_bundle(workspace, "conflict", dag)

    previewed = json.loads(preview(workspace, "conflict")["output"])
    validated = json.loads(validate(workspace, "conflict")["output"])

    assert previewed["executable"] is False
    assert validated["executable"] is False
    assert _issue_identities(previewed) == _issue_identities(validated)


# ---------------------------------------------------------------------------
# 5. real execution observes the same canonical phase
# ---------------------------------------------------------------------------
def test_execution_determines_its_phase_through_compile_phase(tmp_path: Path, monkeypatch):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("a\n")
    (root / "mod.py").write_text("x = 1\n")
    dag = barrier_dag(patch("f.txt", "a", "b"), patch("f.txt", "b", "c"), slug="exec")
    write_bundle(root, "exec", dag)

    seen: list[tuple[list[str], list[str]]] = []
    real = change_dag_compiler.compile_phase

    def spy(*args, **kwargs):
        phase = real(*args, **kwargs)
        seen.append((_nodes(phase.ops), list(phase.ready_runs)))
        return phase

    monkeypatch.setattr(change_dag_compiler, "compile_phase", spy)

    result = run_execution(root, "exec")

    assert seen, "execution must derive its phase from the canonical primitive"
    # Same ordering the whole-DAG simulator reports: the lower edit and the run
    # frontier are reachable before the higher edit above the barrier.
    assert seen[0] == (["N8"], ["N5"])
    assert result["state"] == "root_satisfied"
    assert (root / "f.txt").read_text() == "c\n"
