"""Drift classification by content provenance (F5).

A hunk that fails because the *live* file differs from the content the edit was
authored against is recoverable runtime drift, even when the failing hunk is not
the first one of the patch. A hunk that fails because accepted DAG work
transformed the content is a deterministic intra-DAG contradiction. The failing
hunk's index is not, by itself, the discriminator.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from common.helpers import change_dag_state as state_helper
from common.helpers.change_dag_compiler_lowering import compile_operations
from common.helpers.change_dag_compiler_phase import preflight
from common.tools import dag_executor


def dag_with(nodes: dict) -> dict:
    return {"slug": "drift", "anchor_commit": "a" * 40, "root": "N1", "nodes": nodes}


def semantic(requirement: str, children: list[str] | None = None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if children is not None:
        node["requires"] = children
    return node


def edit(path: str, patch_text: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch_text}


def root_semantic(children: list[str]) -> dict:
    node = semantic("root", children)
    node["decomposition_only"] = True
    return node


def patch(path: str, old: str, new: str, *, line: int = 1) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"


# Two disjoint hunks authored against a common base; the second targets line 3.
TWO_HUNKS = (
    "--- a/f.txt\n+++ b/f.txt\n"
    "@@ -1,1 +1,1 @@\n-a\n+A\n"
    "@@ -3,1 +3,1 @@\n-b\n+B\n"
)


def _workspace(tmp_path: Path, content: str) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "f.txt").write_text(content, encoding="utf-8")
    return workspace


def _make_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / ".keep").write_text("keep\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    return tmp_path


def _bundle(root: Path, slug: str, dag: dict) -> None:
    bundle = root / "artifacts" / "change-dags" / "pending" / slug
    bundle.mkdir(parents=True, exist_ok=True)
    payload = dict(dag)
    payload["slug"] = slug
    (bundle / "DAG.json").write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. exact F5 reproducer: later hunk fails on live drift, not on DAG work
# ---------------------------------------------------------------------------
def test_later_hunk_live_drift_is_runtime_not_intra_dag(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nx\nDRIFT\n")
    dag = dag_with(
        {
            "N1": root_semantic(["N2"]),
            "N2": semantic("implementation", ["N3"]),
            "N3": edit("f.txt", TWO_HUNKS),
        }
    )

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert ops == []
    assert len(conflicts) == 1
    assert conflicts[0].scope == "runtime"
    assert conflicts[0].nodes == ["N3"]

    result = preflight(dag, {}, workspace)
    assert result["executable"] is True
    assert [entry["nodes"] for entry in result["runtime_failures"]] == [["N3"]]
    assert (workspace / "f.txt").read_text(encoding="utf-8") == "a\nx\nDRIFT\n"


def test_later_hunk_live_drift_becomes_ordinary_terminal_failure(tmp_path: Path):
    # End-to-end: the runtime-classified conflict becomes an ordinary failed
    # terminal node when execution reaches it, and the file is left untouched.
    root = _make_repo(tmp_path)
    (root / "f.txt").write_text("a\nx\nDRIFT\n", encoding="utf-8")
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": edit("f.txt", TWO_HUNKS)})
    _bundle(root, "drift", dag)
    state_helper.write_state(root, "drift", {"N2": "not_satisfied"})

    result = dag_executor.run_execution(root, "drift")

    assert result["state"] == "idle"
    assert result["failed"] == ["N2"]
    assert state_helper.read_state(root, "drift")["N2"] == "failed"
    assert (root / "f.txt").read_text(encoding="utf-8") == "a\nx\nDRIFT\n"


# ---------------------------------------------------------------------------
# 2. later hunk fails against accepted deeper DAG work -> intra-DAG
# ---------------------------------------------------------------------------
def test_later_hunk_against_accepted_deeper_work_is_intra_dag(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nx\nb\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N3", "N11"]),
            "N3": semantic("lower", ["N10"]),
            "N10": edit("f.txt", patch("f.txt", "x", "X", line=2)),
            "N11": edit(
                "f.txt",
                "--- a/f.txt\n+++ b/f.txt\n"
                "@@ -1,1 +1,1 @@\n-a\n+A\n"
                "@@ -2,1 +2,1 @@\n-x\n+Y\n",
            ),
        }
    )

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert ops == []
    assert len(conflicts) == 1
    assert conflicts[0].scope == "intra_dag"
    assert set(conflicts[0].nodes) == {"N10", "N11"}
    assert "N10" in conflicts[0].reason

    result = preflight(dag, {}, workspace)
    assert result["executable"] is False
    assert result["runtime_failures"] == []


# ---------------------------------------------------------------------------
# 3. first hunk fails against pure live content -> runtime (unchanged)
# ---------------------------------------------------------------------------
def test_first_hunk_against_pure_live_content_is_runtime(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nb\n")
    dag = dag_with(
        {
            "N1": root_semantic(["N2"]),
            "N2": semantic("implementation", ["N3"]),
            "N3": edit("f.txt", patch("f.txt", "zzz", "yyy")),
        }
    )

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert ops == []
    assert [conflict.scope for conflict in conflicts] == ["runtime"]
    assert preflight(dag, {}, workspace)["executable"] is True


# ---------------------------------------------------------------------------
# 4. two disjoint hunks that both apply are accepted with the exact result
# ---------------------------------------------------------------------------
def test_two_disjoint_hunks_both_applying_are_accepted(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nx\nb\n")
    dag = dag_with(
        {
            "N1": root_semantic(["N2"]),
            "N2": semantic("implementation", ["N3"]),
            "N3": edit("f.txt", TWO_HUNKS),
        }
    )

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].applied == "A\nx\nB\n"
    assert preflight(dag, {}, workspace)["executable"] is True