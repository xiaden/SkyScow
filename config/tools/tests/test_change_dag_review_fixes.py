"""Regressions for two material adversarial-review findings in the integrated
Change DAG compiler repair set.

FINDING 1 -- same-anchor duplicate insertions.

``validate_hunk_ranges`` accepted two pure-insertion hunks (``old_count == 0``)
at the *same* anchor. Preview composition (``_compose_replacements``) and
application (``apply_file_patch``) ordered equal-anchor insertions oppositely,
so the compiler's ``applied`` result diverged byte-for-byte from what execution
writes. The single-gate invariant is that every patch accepted by
``validate_hunk_ranges``/``parse_unified_diff`` composes to exactly what
``apply_file_patch`` writes. Same-anchor insertions are now rejected as
unordered; an enumeration over a representative hunk corpus (see below) confirms
that this is the *only* structure that violated the invariant.

FINDING 2 -- same-frontier move chains.

Two moves at the same construction depth are both interpreted against the same
accepted lower-work base and may not consume each other's output. When one move's
destination equals another move's source, the final repository state depended
only on the numeric-ID tie-break (a move chain ``a->b`` then ``b->c`` either lost
``B`` or reordered entirely). Such pairs are now a deterministic intra-DAG
compiler conflict naming both nodes; different construction depths remain legal
and are ordered deeper-first.

Expected results in this module are hand-derived from the unified-diff spec and
the stated contracts; none read the implementation's own output as an oracle.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.helpers.change_dag_compiler_lowering import compile_operations
from common.helpers.change_dag_compiler_phase import compile_whole_dag, preflight
from common.helpers.change_dag_compiler_reconcile import (
    _changed_span,
    _compose_replacements,
)
from common.helpers.change_dag_compiler_runtime import apply_compiled
from common.helpers.change_dag_patch import (
    FilePatch,
    Hunk,
    PatchError,
    apply_file_patch,
    parse_unified_diff,
    validate_hunk_ranges,
)
from common.helpers.change_dag_ops_views import preview

# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------
ANCHOR = "a" * 40


def _workspace(tmp_path: Path, files: dict[str, str], *, name: str = "workspace") -> Path:
    workspace = tmp_path / name
    workspace.mkdir(parents=True)
    for name, content in files.items():
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return workspace


def _semantic(requirement: str, children: list[str] | None = None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if children is not None:
        node["satisfied_by"] = children
    return node


def _edit(path: str, patch_text: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch_text}


def _move(source: str, destination: str, *, overwrite: bool = False) -> dict:
    return {
        "type": "move",
        "from_path": source,
        "to_path": destination,
        "overwrite": overwrite,
    }


def _dag(slug: str, nodes: dict) -> dict:
    return {"slug": slug, "anchor_commit": ANCHOR, "root": "N1", "nodes": nodes}


def _bundle(root: Path, slug: str, dag: dict, state: dict[str, str] | None = None) -> None:
    bundle = root / "artifacts" / "change-dags" / "pending" / slug
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "DAG.json").write_text(json.dumps(dag), encoding="utf-8")
    (bundle / "EXECUTION_STATE.json").write_text(json.dumps(state or {}), encoding="utf-8")
    (bundle / "WORK_LOG.jsonl").write_text("", encoding="utf-8")


def _composed(base: str, file_patch: FilePatch) -> str:
    spans = []
    for hunk in file_patch.hunks:
        span = _changed_span(hunk)
        if span is not None:
            spans.append(span)
    return _compose_replacements(base, spans)


# The exact flagged reproducer: two insertions at the same anchor.
SAME_ANCHOR_INSERTIONS = (
    "--- a/f.txt\n+++ b/f.txt\n"
    "@@ -1,0 +2,1 @@\n+alpha\n"
    "@@ -1,0 +2,1 @@\n+beta\n"
)

# Same-frontier move chain: N10 and N11 are both direct children of the same
# semantic parent, so they share construction depth and the same accepted base.
SAME_FRONTIER_MOVE_NODES = {
    "N1": _semantic("root", ["N2"]),
    "N2": _semantic("implementation", ["N10", "N11"]),
}


# ---------------------------------------------------------------------------
# FINDING 1
# ---------------------------------------------------------------------------
def test_f1_same_anchor_insertions_rejected_at_parse():
    with pytest.raises(PatchError) as excinfo:
        parse_unified_diff(SAME_ANCHOR_INSERTIONS)
    message = str(excinfo.value)
    assert "f.txt" in message
    assert "insert" in message.lower()
    assert "hunk 0" in message and "hunk 1" in message
    assert "old_start=1" in message


def test_f1_same_anchor_insertions_rejected_when_constructed_directly():
    # apply_file_patch/validate_hunk_ranges are public entry points, so a
    # directly constructed duplicate-anchor FilePatch is rejected too.
    file_patch = FilePatch(
        path="f.txt",
        hunks=[
            Hunk(1, 0, 2, 1, ["+alpha"]),
            Hunk(1, 0, 2, 1, ["+beta"]),
        ],
    )
    with pytest.raises(PatchError):
        validate_hunk_ranges(file_patch, path="f.txt")
    with pytest.raises(PatchError):
        apply_file_patch("a\nb\n", file_patch, path="f.txt")


def test_f1_same_anchor_reproducer_is_intra_dag_conflict_without_mutation(tmp_path: Path):
    workspace = _workspace(tmp_path, {"f.txt": "a\nb\n"})
    dag = _dag(
        "f1",
        {
            "N1": _semantic("root", ["N2"]),
            "N2": _edit("f.txt", SAME_ANCHOR_INSERTIONS),
        },
    )

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert ops == []
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.scope == "intra_dag"
    assert conflict.nodes == ["N2"]
    assert conflict.reason.startswith("compile_conflict")

    result = preflight(dag, {}, workspace)
    assert result["executable"] is False
    assert result["runtime_failures"] == []
    assert (workspace / "f.txt").read_text(encoding="utf-8") == "a\nb\n"
    assert apply_compiled(ops, workspace) == []
    assert (workspace / "f.txt").read_text(encoding="utf-8") == "a\nb\n"


# Accepted corpus. (base, patch, expected) with expected derived by hand from the
# unified-diff specification: single insertion; two insertions at DIFFERENT
# anchors; insertion + replacement; adjacent hunks; multi-hunk line-count change.
ACCEPTED_CORPUS = [
    (
        "a\nb\n",
        "--- a/f.txt\n+++ b/f.txt\n@@ -1,0 +2,1 @@\n+X\n",
        "a\nX\nb\n",
    ),
    (
        "a\nb\n",
        "--- a/f.txt\n+++ b/f.txt\n"
        "@@ -0,0 +1,1 @@\n+X\n"
        "@@ -2,0 +3,1 @@\n+Y\n",
        "X\na\nb\nY\n",
    ),
    (
        "a\nb\n",
        "--- a/f.txt\n+++ b/f.txt\n"
        "@@ -1,0 +2,1 @@\n+X\n"
        "@@ -2,1 +3,1 @@\n-b\n+B\n",
        "a\nX\nB\n",
    ),
    (
        "a\nb\nc\n",
        "--- a/f.txt\n+++ b/f.txt\n"
        "@@ -1,2 +1,2 @@\n-a\n-b\n+X\n+Y\n"
        "@@ -3,1 +3,1 @@\n-c\n+Z\n",
        "X\nY\nZ\n",
    ),
    (
        "1\n2\n3\n4\n5\n",
        "--- a/f.txt\n+++ b/f.txt\n"
        "@@ -1,1 +1,3 @@\n 1\n+one\n+uno\n"
        "@@ -4,1 +4,1 @@\n-4\n+four\n",
        "1\none\nuno\n2\n3\nfour\n5\n",
    ),
]


@pytest.mark.parametrize("base, patch, expected", ACCEPTED_CORPUS)
def test_f1_composition_matches_application_for_accepted_corpus(base, patch, expected):
    file_patch = parse_unified_diff(patch)[0]
    applied = apply_file_patch(base, file_patch)
    assert applied == expected
    # The single-gate invariant: composition and application must agree exactly.
    assert _composed(base, file_patch) == applied


def test_f1_two_insertions_at_different_anchors_remain_accepted():
    base = "a\nb\n"
    patch = (
        "--- a/f.txt\n+++ b/f.txt\n"
        "@@ -0,0 +1,1 @@\n+X\n"
        "@@ -2,0 +3,1 @@\n+Y\n"
    )
    file_patch = parse_unified_diff(patch)[0]
    applied = apply_file_patch(base, file_patch)
    assert applied == "X\na\nb\nY\n"
    assert _composed(base, file_patch) == applied


# ---------------------------------------------------------------------------
# FINDING 2
# ---------------------------------------------------------------------------
def _same_frontier_chain_dag(slug: str, first: dict, second: dict) -> dict:
    """N10/N11 are same-frontier children of N2; ``first`` is N10, ``second`` N11."""
    return _dag(
        slug,
        {
            **SAME_FRONTIER_MOVE_NODES,
            "N10": first,
            "N11": second,
        },
    )


def test_f2_same_frontier_move_chain_rejected_in_both_numeric_assignments(tmp_path: Path):
    variant_a = _same_frontier_chain_dag(
        "f2a", _move("a", "b", overwrite=True), _move("b", "c", overwrite=False)
    )
    variant_b = _same_frontier_chain_dag(
        "f2b", _move("b", "c", overwrite=False), _move("a", "b", overwrite=True)
    )

    observed = []
    for index, dag in enumerate((variant_a, variant_b)):
        workspace = _workspace(tmp_path, {"a": "A\n", "b": "B\n"}, name=f"ws{index}")
        ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

        assert ops == []
        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict.scope == "intra_dag"
        assert conflict.nodes == ["N10", "N11"]
        assert conflict.reason.startswith("compile_conflict")
        assert "N10" in conflict.reason and "N11" in conflict.reason

        # No move op emitted for either node, and no repository mutation.
        assert apply_compiled(ops, workspace) == []
        assert (workspace / "a").read_text(encoding="utf-8") == "A\n"
        assert (workspace / "b").read_text(encoding="utf-8") == "B\n"
        assert not (workspace / "c").exists()

        assert preflight(dag, {}, workspace)["executable"] is False
        observed.append((conflict.path, tuple(conflict.nodes), conflict.reason))

    # Deterministic: numeric-ID assignment must not change the outcome.
    assert observed[0] == observed[1]
    assert observed[0][0] == "b"


def test_f2_same_frontier_chain_with_non_overwrite_rejected_deterministically(tmp_path: Path):
    first = _move("a", "b", overwrite=False)
    second = _move("b", "c", overwrite=False)
    workspace = _workspace(tmp_path, {"a": "A\n", "b": "B\n"})
    dag = _same_frontier_chain_dag("f2nonoverwrite", first, second)

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert ops == []
    chain = [c for c in conflicts if c.scope == "intra_dag" and set(c.nodes) == {"N10", "N11"}]
    assert len(chain) == 1
    assert (workspace / "a").read_text(encoding="utf-8") == "A\n"
    assert (workspace / "b").read_text(encoding="utf-8") == "B\n"
    assert not (workspace / "c").exists()


def test_f2_different_depth_move_chain_supported_case_unchanged(tmp_path: Path):
    # Deeper N10 frees b by moving it to c; shallower N11 then consumes a->b.
    # N3 makes N10 (depth 3) deeper than N11 (depth 2).
    workspace = _workspace(tmp_path, {"a": "A\n", "b": "B\n"})
    dag = _dag(
        "f2depth",
        {
            "N1": _semantic("root", ["N2"]),
            "N2": _semantic("implementation", ["N3", "N11"]),
            "N3": _semantic("lower", ["N10"]),
            "N10": _move("b", "c", overwrite=False),
            "N11": _move("a", "b", overwrite=True),
        },
    )

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert conflicts == []
    assert [op.nodes for op in ops] == [["N10"], ["N11"]]
    assert preflight(dag, {}, workspace)["executable"] is True

    apply_compiled(ops, workspace)
    assert (workspace / "c").read_text(encoding="utf-8") == "B\n"
    assert (workspace / "b").read_text(encoding="utf-8") == "A\n"
    assert not (workspace / "a").exists()


def test_f2_ordinary_independent_moves_unchanged(tmp_path: Path):
    workspace = _workspace(tmp_path, {"a": "A\n", "b": "B\n"})
    dag = _same_frontier_chain_dag(
        "f2independent", _move("a", "x"), _move("b", "y")
    )

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert conflicts == []
    assert sorted(op.nodes[0] for op in ops) == ["N10", "N11"]
    apply_compiled(ops, workspace)
    assert (workspace / "x").read_text(encoding="utf-8") == "A\n"
    assert (workspace / "y").read_text(encoding="utf-8") == "B\n"
    assert not (workspace / "a").exists()
    assert not (workspace / "b").exists()


def test_f2_preview_and_whole_dag_simulation_report_same_conflict(tmp_path: Path):
    workspace = _workspace(tmp_path, {"a": "A\n", "b": "B\n"})
    dag = _same_frontier_chain_dag(
        "f2preview", _move("a", "b", overwrite=True), _move("b", "c", overwrite=False)
    )
    _bundle(workspace, "f2preview", dag)

    whole = json.loads(preview(workspace, "f2preview")["output"])

    assert whole["ops"] == []
    assert whole["executable"] is False
    chain = [
        c
        for c in whole["conflicts"]
        if c["scope"] == "intra_dag" and set(c["nodes"]) == {"N10", "N11"}
    ]
    assert len(chain) == 1

    phases, conflicts, _blocked = compile_whole_dag(dag, {}, workspace)
    assert phases == []
    simulated = [c for c in conflicts if c.scope == "intra_dag" and set(c.nodes) == {"N10", "N11"}]
    assert len(simulated) == 1
    assert simulated[0].path == chain[0]["path"]
    assert simulated[0].reason == chain[0]["reason"]
