"""F2: run-barrier gating is graph-derived, not node-map-order-derived."""
from __future__ import annotations

from itertools import permutations
from pathlib import Path

from common.helpers.change_dag_compiler_lowering import compile_operations


def semantic(requirement: str, children: list[str]) -> dict:
    return {"type": "semantic", "requirement": requirement, "requires": children}


def run() -> dict:
    return {"type": "run", "command": ["python3", "-m", "compileall", "-q", "."]}


def edit(path: str) -> dict:
    return {
        "type": "edit",
        "path": path,
        "patch": f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,1 @@\n-a\n+b\n",
    }


def dag_for(order: list[str], *, independent: bool = False) -> dict:
    nodes = {
        "N1": semantic("root", ["N2", "N4", "N8"]),
        "N2": semantic("first barrier", ["N3"]),
        "N3": run(),
        "N4": semantic("second barrier", ["N5"]),
        "N5": semantic("middle", ["N6", "N9"] if independent else ["N6"]),
        "N6": semantic("deep", ["N7"]),
        "N7": run(),
        "N8": edit("blocked.txt"),
    }
    if independent:
        # N9 sits at the same depth as N6 (the deep barrier's semantic parent),
        # so it is an independent sibling prerequisite and must still apply.
        nodes["N9"] = edit("independent.txt")
    return {
        "slug": "barriers",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {node_id: nodes[node_id] for node_id in order},
    }


def blocked(dag: dict, workspace: Path, state: dict | None = None) -> dict[str, str]:
    _ops, _conflicts, entries = compile_operations(dag, state or {}, workspace)
    return {entry.node_id: entry.reason for entry in entries}


def test_multiple_barriers_are_insertion_order_invariant(tmp_path: Path):
    (tmp_path / "blocked.txt").write_text("a\n", encoding="utf-8")
    ids = ["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8"]
    expected = {"N8": "blocked by unsatisfied run barrier N7"}

    for order in permutations(ids):
        assert blocked(dag_for(list(order)), tmp_path) == expected


def test_deeper_barrier_is_not_masked_by_shallower_barrier(tmp_path: Path):
    (tmp_path / "blocked.txt").write_text("a\n", encoding="utf-8")
    dag = dag_for(["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8"])

    # The shallower N3 barrier must not win over the deeper N7 barrier.
    assert blocked(dag, tmp_path) == {"N8": "blocked by unsatisfied run barrier N7"}


def test_independent_branch_progresses_while_barrier_branch_waits(tmp_path: Path):
    (tmp_path / "blocked.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "independent.txt").write_text("a\n", encoding="utf-8")
    dag = dag_for(["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9"], independent=True)

    ops, _conflicts, entries = compile_operations(dag, {}, tmp_path)
    assert [op.path for op in ops] == ["independent.txt"]
    assert {entry.node_id for entry in entries} == {"N8"}


def test_failed_barrier_does_not_permanently_gate_unrelated_work(tmp_path: Path):
    (tmp_path / "blocked.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "independent.txt").write_text("a\n", encoding="utf-8")
    dag = dag_for(["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9"], independent=True)

    ops, conflicts, entries = compile_operations(dag, {"N7": "failed"}, tmp_path)
    assert not conflicts
    # Gating is depth/hierarchy-based, not branch-based. N8 is a child of root
    # N1 and N1 is an ancestor of the deep barrier's parent N6, so N8 sits above
    # the barrier and stays deferred while the barrier is failed. N9 sits at the
    # barrier parent's own depth, so it is not gated and still applies.
    assert [op.path for op in ops] == ["independent.txt"]
    assert {entry.node_id for entry in entries} == {"N8"}
