"""``executable`` is the aggregate DAG execution-admission result.

A DAG is executable only when it is structurally valid, ``resolved``, and free
of deterministic compiler/context admission conflicts. Validation reports every
independently discoverable reason in one pass: unresolved authoring state does
not short-circuit the compiler analysis, and recoverable live-applicability
failures stay reported as ``runtime_failures`` rather than admission blockers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag  # noqa: E402
from common.helpers.change_dag_compiler_phase import preflight  # noqa: E402
from common.tools.dag_start import dag_start  # noqa: E402


def dag_with(nodes: dict, root: str = "N1", slug: str = "demo") -> dict:
    # The root is always decomposition_only; fixtures only supply the graph.
    nodes.setdefault(root, {}).setdefault("decomposition_only", True)
    return {"slug": slug, "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def semantic(requirement: str = "r", requires=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if requires is not None:
        node["requires"] = requires
    return node


def edit(path: str, patch_text: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch_text}


def create(path: str, content: str) -> dict:
    return {"type": "create", "path": path, "content": content}


def patch(path: str, old: str, new: str, line: int = 1) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"


def write_bundle(root: Path, slug: str, dag: dict, state: dict | None = None) -> None:
    bundle = root / "artifacts/change-dags/pending" / slug
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "DAG.json").write_text(json.dumps(dag))
    (bundle / "EXECUTION_STATE.json").write_text(json.dumps(state or {}))
    (bundle / "WORK_LOG.jsonl").write_text("")


def _kinds(result: dict) -> set[str]:
    return {issue["kind"] for issue in result["issues"]}


# ---------------------------------------------------------------------------
# resolved + no conflicts -> executable
# ---------------------------------------------------------------------------
def test_resolved_dag_without_conflicts_is_executable(tmp_path: Path):
    (tmp_path / "f.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N3"]),
            "N3": edit("f.txt", patch("f.txt", "a", "b")),
        }
    )
    assert change_dag.is_resolved(dag) is True
    result = preflight(dag, {}, tmp_path)
    assert result["executable"] is True
    assert result["issues"] == []


# ---------------------------------------------------------------------------
# unresolved + otherwise clean -> not executable, unresolved issue
# ---------------------------------------------------------------------------
def test_unresolved_authoring_state_blocks_execution(tmp_path: Path):
    (tmp_path / "f.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N3"]),
            "N2": semantic("undecided"),                       # unresolved
            "N3": semantic("implementation", ["N4"]),
            "N4": edit("f.txt", patch("f.txt", "a", "b")),
        }
    )
    assert change_dag.is_resolved(dag) is False
    result = preflight(dag, {}, tmp_path)
    assert result["executable"] is False
    unresolved = [issue for issue in result["issues"] if issue["kind"] == "unresolved"]
    assert len(unresolved) == 1
    assert unresolved[0]["nodes"] == ["N2"]
    assert unresolved[0]["message"] == "Change DAG contains unresolved semantic requirements"


# ---------------------------------------------------------------------------
# resolved + compile conflict -> not executable, only the conflict
# ---------------------------------------------------------------------------
def test_resolved_dag_with_compile_conflict_is_not_executable(tmp_path: Path):
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N3", "N4"]),
            "N3": create("new.txt", "x\n"),
            "N4": create("new.txt", "y\n"),
        }
    )
    assert change_dag.is_resolved(dag) is True
    result = preflight(dag, {}, tmp_path)
    assert result["executable"] is False
    assert "compile_conflict" in _kinds(result)
    assert "unresolved" not in _kinds(result)


# ---------------------------------------------------------------------------
# unresolved + compile conflict -> both reported in one pass
# ---------------------------------------------------------------------------
def test_unresolved_and_compile_conflict_are_reported_together(tmp_path: Path):
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N5"]),
            "N2": semantic("undecided"),                       # unresolved
            "N5": semantic("implementation", ["N3", "N4"]),
            "N3": create("new.txt", "x\n"),
            "N4": create("new.txt", "y\n"),
        }
    )
    assert change_dag.is_resolved(dag) is False
    result = preflight(dag, {}, tmp_path)
    assert result["executable"] is False
    kinds = _kinds(result)
    assert "unresolved" in kinds
    assert "compile_conflict" in kinds


# ---------------------------------------------------------------------------
# every unresolved node id reported deterministically
# ---------------------------------------------------------------------------
def test_all_unresolved_semantic_nodes_are_reported_deterministically(tmp_path: Path):
    (tmp_path / "f.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N5", "N2"]),
            "N5": semantic("open five"),
            "N2": semantic("open two"),
        }
    )
    result = preflight(dag, {}, tmp_path)
    assert result["executable"] is False
    unresolved = [issue for issue in result["issues"] if issue["kind"] == "unresolved"]
    assert len(unresolved) == 1
    assert unresolved[0]["nodes"] == ["N2", "N5"]


# ---------------------------------------------------------------------------
# retry=true shares the same executable definition
# ---------------------------------------------------------------------------
def test_retry_cannot_bypass_unresolved_admission(tmp_path: Path):
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N3"]),
            "N2": semantic("undecided"),                       # unresolved
            "N3": semantic("implementation", ["N4"]),
            "N4": edit("f.txt", patch("f.txt", "a", "b")),
        }
    )
    write_bundle(tmp_path, "retryable", dag, {"N4": "failed"})

    result = dag_start("retryable", retry=True, workspace_root=tmp_path)
    assert result["error"] == "not_executable"
    assert any(issue["kind"] == "unresolved" for issue in result["issues"])


# ---------------------------------------------------------------------------
# runtime satisfaction stays independent of authoring resolution
# ---------------------------------------------------------------------------
def test_derived_satisfaction_ignores_authoring_resolution(tmp_path: Path):
    (tmp_path / "f.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("middle", ["N3"]),   # only a semantic child -> unresolved
            "N3": semantic("leaf", ["N4"]),
            "N4": edit("f.txt", patch("f.txt", "a", "b")),
        }
    )
    assert change_dag.is_resolved(dag) is False
    # Runtime satisfaction still derives purely from the requires edges.
    satisfaction = change_dag.derived_satisfaction(dag, {"N4": "satisfied"})
    assert satisfaction["N3"] is True
    assert satisfaction["N2"] is True
    assert satisfaction["N1"] is True
    # ...while the DAG is still not executable because authoring is unresolved.
    assert preflight(dag, {"N4": "satisfied"}, tmp_path)["executable"] is False
