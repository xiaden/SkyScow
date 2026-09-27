"""Cross-frontier edit contradiction classification (F1).

A hunk failure is a deterministic intra-DAG contradiction only when the content
it failed against is DAG-produced: the authored base, or the accepted result of a
deeper frontier. A shallower edit authored against the common lower base that
cannot consume a deeper frontier's accepted transformation is a deterministic
contradiction naming both nodes; a shallower edit that *does* apply to the
transformed content is intentionally consuming deeper work and stays accepted. A
failure against pure live content -- even in a region no DAG work touched --
remains recoverable runtime drift.
"""
from __future__ import annotations

from pathlib import Path

from common.helpers.change_dag_compiler_lowering import compile_operations
from common.helpers.change_dag_compiler_phase import preflight


def dag_with(nodes: dict) -> dict:
    return {"slug": "cross-frontier", "anchor_commit": "a" * 40, "root": "N1", "nodes": nodes}


def semantic(requirement: str, children: list[str] | None = None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if children is not None:
        node["requires"] = children
    return node


def edit(path: str, patch_text: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch_text}


def patch(path: str, old: str, new: str, *, line: int = 1) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"


def deeper_shallower(deeper_patch: str, shallower_patch: str) -> dict:
    """Two edit nodes for one file: N10 is deeper (depth 3) than N11 (depth 2)."""
    return dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N3", "N11"]),
            "N3": semantic("lower", ["N10"]),
            "N10": edit("f.txt", deeper_patch),
            "N11": edit("f.txt", shallower_patch),
        }
    )


def _workspace(tmp_path: Path, content: str) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "f.txt").write_text(content, encoding="utf-8")
    return workspace


# ---------------------------------------------------------------------------
# 1. exact F1 reproducer: shallower edit contradicts accepted deeper work
# ---------------------------------------------------------------------------
def test_shallower_edit_contradicting_deeper_accepted_work_is_intra_dag(tmp_path: Path):
    workspace = _workspace(tmp_path, "foo\n")
    dag = deeper_shallower(patch("f.txt", "foo", "bar"), patch("f.txt", "foo", "baz"))

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert ops == []
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.scope == "intra_dag"
    assert set(conflict.nodes) == {"N10", "N11"}
    # Both the failing shallower node and the deeper contributor are named.
    assert "N11" in conflict.reason and "N10" in conflict.reason

    result = preflight(dag, {}, workspace)
    assert result["executable"] is False
    assert result["runtime_failures"] == []
    assert (workspace / "f.txt").read_text(encoding="utf-8") == "foo\n"


# ---------------------------------------------------------------------------
# 2. compatible deeper-to-shallower consumption is preserved
# ---------------------------------------------------------------------------
def test_shallower_edit_consuming_deeper_work_is_accepted(tmp_path: Path):
    workspace = _workspace(tmp_path, "foo\n")
    dag = deeper_shallower(patch("f.txt", "foo", "bar"), patch("f.txt", "bar", "baz"))

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].applied == "baz\n"
    assert set(ops[0].nodes) == {"N10", "N11"}
    assert preflight(dag, {}, workspace)["executable"] is True


# ---------------------------------------------------------------------------
# 3. common-base same-frontier peer composition is unchanged
# ---------------------------------------------------------------------------
def test_common_base_same_frontier_peers_still_compose(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nb\nc\nd\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N10", "N11"]),
            "N10": edit("f.txt", patch("f.txt", "a", "A", line=1)),
            "N11": edit("f.txt", patch("f.txt", "d", "D", line=4)),
        }
    )

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].applied == "A\nb\nc\nD\n"
    assert set(ops[0].nodes) == {"N10", "N11"}
    assert preflight(dag, {}, workspace)["executable"] is True


# ---------------------------------------------------------------------------
# 4. an unrelated deeper edit must not turn live drift into an intra-DAG conflict
# ---------------------------------------------------------------------------
def test_unrelated_deeper_region_does_not_false_classify_live_drift(tmp_path: Path):
    # Deeper N10 transforms line 1; shallower N11 targets line 3, which is *live*
    # drift (DRIFT) present in the base as well. N11 fails against accepted deeper
    # content but the failure is not attributable to it, so it stays runtime.
    workspace = _workspace(tmp_path, "a\nx\nDRIFT\n")
    dag = deeper_shallower(patch("f.txt", "a", "A", line=1), patch("f.txt", "b", "B", line=3))

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert ops == []
    assert [conflict.scope for conflict in conflicts] == ["runtime"]
    assert conflicts[0].nodes == ["N11"]
    assert not any(conflict.scope == "intra_dag" for conflict in conflicts)
    assert all("N10" not in conflict.nodes for conflict in conflicts)

    result = preflight(dag, {}, workspace)
    assert result["executable"] is True
    assert [entry["nodes"] for entry in result["runtime_failures"]] == [["N11"]]
    assert (workspace / "f.txt").read_text(encoding="utf-8") == "a\nx\nDRIFT\n"