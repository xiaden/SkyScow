"""Same-frontier peer composition semantics for Change DAG edit nodes.

Construction depth is the frontier: peers at the same depth are authored from the
same accepted lower-work state, so their proposals are interpreted against that
one state and only their non-overlapping changed spans compose. Numerical node
IDs are a deterministic display order, never semantic causality. Deeper accepted
work may still be intentionally consumed by shallower work.
"""
from __future__ import annotations

from pathlib import Path

from common.helpers.change_dag_compiler_lowering import compile_operations
from common.helpers.change_dag_compiler_phase import preflight


def dag_with(nodes: dict) -> dict:
    return {"slug": "frontier", "anchor_commit": "a" * 40, "root": "N1", "nodes": nodes}


def semantic(requirement: str, children: list[str] | None = None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if children is not None:
        node["satisfied_by"] = children
    return node


def edit(path: str, patch_text: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch_text}


def patch(path: str, old: str, new: str, *, line: int = 1) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"


def insert_after(path: str, line: int, context: str, added: str) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},2 @@\n {context}\n+{added}\n"


def peer_dag(first: str, second: str) -> dict:
    """Two edit peers at the same construction depth (both children of N2)."""
    return dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N10", "N11"]),
            "N10": edit("f.txt", first),
            "N11": edit("f.txt", second),
        }
    )


def compiled(dag: dict, workspace: Path):
    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)
    return ops, conflicts


def _workspace(tmp_path: Path, content: str) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "f.txt").write_text(content, encoding="utf-8")
    return workspace


# ---------------------------------------------------------------------------
# 1. independent compatible peer edits compose
# ---------------------------------------------------------------------------
def test_same_frontier_peers_editing_independent_regions_compose(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nb\nc\nd\n")
    dag = peer_dag(patch("f.txt", "a", "A"), patch("f.txt", "d", "D", line=4))

    ops, conflicts = compiled(dag, workspace)

    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].applied == "A\nb\nc\nD\n"
    assert set(ops[0].nodes) == {"N10", "N11"}
    assert preflight(dag, {}, workspace)["executable"] is True


# ---------------------------------------------------------------------------
# 2. an insertion before a peer's edit location must not shadow that peer
# ---------------------------------------------------------------------------
def test_peer_insertion_does_not_shadow_an_independently_authored_peer_edit(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nb\nc\n")
    # N10 inserts after line 1; N11 edits the original line 3. N10 has the lower
    # numeric ID, so sequential application would have shifted N11's target.
    dag = peer_dag(insert_after("f.txt", 1, "a", "ins"), patch("f.txt", "c", "C", line=3))

    ops, conflicts = compiled(dag, workspace)

    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].applied == "a\nins\nb\nC\n"
    assert preflight(dag, {}, workspace)["executable"] is True


# ---------------------------------------------------------------------------
# 3. a peer may not reference text another peer introduces at the same frontier
# ---------------------------------------------------------------------------
def test_peer_referencing_peer_output_is_a_deterministic_conflict(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nb\n")
    dag = peer_dag(insert_after("f.txt", 1, "a", "ins"), patch("f.txt", "ins", "INS", line=2))

    result = preflight(dag, {}, workspace)
    ops, conflicts = compiled(dag, workspace)

    assert result["executable"] is False
    assert result["runtime_failures"] == []
    assert ops == []
    assert len(conflicts) == 1
    assert conflicts[0].scope == "intra_dag"
    assert set(conflicts[0].nodes) == {"N10", "N11"}
    assert conflicts[0].reason.startswith("context_conflict:")


# ---------------------------------------------------------------------------
# 4. overlapping peer edits are a deterministic conflict
# ---------------------------------------------------------------------------
def test_overlapping_same_frontier_peer_edits_conflict(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nb\nc\n")
    dag = peer_dag(patch("f.txt", "b", "B", line=2), patch("f.txt", "b", "BB", line=2))

    result = preflight(dag, {}, workspace)
    ops, conflicts = compiled(dag, workspace)

    assert result["executable"] is False
    assert ops == []
    assert len(conflicts) == 1
    assert conflicts[0].scope == "intra_dag"
    assert set(conflicts[0].nodes) == {"N10", "N11"}
    assert (workspace / "f.txt").read_text(encoding="utf-8") == "a\nb\nc\n"


# ---------------------------------------------------------------------------
# 5. deeper accepted work may be intentionally consumed by shallower work
# ---------------------------------------------------------------------------
def test_deeper_work_may_be_consumed_by_shallower_work(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N3", "N20"]),
            "N3": semantic("lower", ["N10"]),
            "N10": edit("f.txt", insert_after("f.txt", 1, "a", "ins")),  # depth 3
            "N20": edit("f.txt", patch("f.txt", "ins", "INS", line=2)),  # depth 2
        }
    )

    ops, conflicts = compiled(dag, workspace)

    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].applied == "a\nINS\n"
    assert preflight(dag, {}, workspace)["executable"] is True


# ---------------------------------------------------------------------------
# 6. swapping peer node IDs changes nothing semantically
# ---------------------------------------------------------------------------
def test_swapping_peer_node_ids_does_not_change_result_or_classification(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nb\nc\n")
    insertion = insert_after("f.txt", 1, "a", "ins")
    replacement = patch("f.txt", "c", "C", line=3)

    forward_ops, _forward_conflicts = compiled(peer_dag(insertion, replacement), workspace)
    swapped = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N10", "N11"]),
            "N10": edit("f.txt", replacement),
            "N11": edit("f.txt", insertion),
        }
    )
    backward_ops, _backward_conflicts = compiled(swapped, workspace)

    assert forward_ops[0].applied == backward_ops[0].applied == "a\nins\nb\nC\n"

    # The peer-dependency classification is also ID-order independent.
    dependent = patch("f.txt", "A", "AA")
    baseline = preflight(peer_dag(patch("f.txt", "a", "A"), dependent), {}, workspace)
    mirrored = preflight(
        dag_with(
            {
                "N1": semantic("root", ["N2"]),
                "N2": semantic("implementation", ["N10", "N11"]),
                "N10": edit("f.txt", dependent),
                "N11": edit("f.txt", patch("f.txt", "a", "A")),
            }
        ),
        {},
        workspace,
    )

    assert baseline["executable"] is mirrored["executable"] is False
    assert sorted(baseline["conflicts"][0]["nodes"]) == ["N10", "N11"]
    assert sorted(mirrored["conflicts"][0]["nodes"]) == ["N10", "N11"]


# ---------------------------------------------------------------------------
# 7. three same-frontier peers: two compatible, one conflicting
# ---------------------------------------------------------------------------
def test_three_same_frontier_peers_two_compatible_one_conflicting(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nb\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N10", "N11", "N12"]),
            "N10": edit("f.txt", patch("f.txt", "a", "A")),           # independent
            "N11": edit("f.txt", patch("f.txt", "b", "B", line=2)),
            "N12": edit("f.txt", patch("f.txt", "b", "C", line=2)),   # overlaps N11
        }
    )

    result = preflight(dag, {}, workspace)
    ops, conflicts = compiled(dag, workspace)

    assert result["executable"] is False
    assert ops == []
    assert len(conflicts) == 1
    assert conflicts[0].scope == "intra_dag"
    assert set(conflicts[0].nodes) == {"N11", "N12"}
    assert "N12" in conflicts[0].reason
