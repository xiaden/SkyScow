"""Compiler-side F4 coordinate consistency and F6 overlap rejection.

The compiler composes accepted edit results from base-coordinate changed spans
(``_changed_span``) and proves an interrupted edit's result with
``_already_applied``. Both must use the same insertion coordinate the patch
engine applies (F4): a zero-``old_count`` hunk inserts after original line
``old_start`` at base index ``old_start``. F6's overlap rejection must surface as
a deterministic intra-DAG conflict through ``compile_operations`` and through
``compile_whole_dag``/``preflight`` without mutating the repository.
"""
from __future__ import annotations

from pathlib import Path

from common.helpers.change_dag_compiler import (
    _already_applied,
    apply_compiled,
    compile_operations,
    compile_whole_dag,
    node_present,
    preflight,
)
from common.helpers.change_dag_patch import apply_file_patch, parse_unified_diff


def dag_with(nodes: dict, root: str = "N1") -> dict:
    return {"slug": "coordinates", "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def semantic(requirement: str, children: list[str] | None = None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if children is not None:
        node["satisfied_by"] = children
    return node


def edit(path: str, patch_text: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch_text}


def single_edit_dag(patch_text: str, node_id: str = "N2") -> dict:
    return dag_with(
        {"N1": semantic("root", [node_id]), node_id: edit("f.txt", patch_text)}
    )


def _diff(body: str, path: str = "f.txt") -> str:
    return f"--- a/{path}\n+++ b/{path}\n{body}"


def _workspace(base: Path, content: str) -> Path:
    workspace = base / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "f.txt").write_text(content, encoding="utf-8")
    return workspace


# ---------------------------------------------------------------------------
# F6 -- overlapping hunks are a deterministic intra-DAG conflict, no mutation
# ---------------------------------------------------------------------------
F6_OVERLAP = _diff(
    "@@ -1,2 +1,2 @@\n-a\n-b\n+X\n+Y\n"
    "@@ -2,1 +2,1 @@\n-Y\n+Z\n"
)


def test_f6_overlap_is_intra_dag_conflict_through_compile_and_preflight(tmp_path: Path):
    workspace = _workspace(tmp_path, "a\nb\n")
    dag = single_edit_dag(F6_OVERLAP)

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert ops == []
    assert len(conflicts) == 1
    assert conflicts[0].scope == "intra_dag"
    assert conflicts[0].reason.startswith("compile_conflict")
    assert conflicts[0].nodes == ["N2"]

    result = preflight(dag, {}, workspace)
    assert result["executable"] is False
    assert result["runtime_failures"] == []
    assert any(issue["kind"] == "compile_conflict" for issue in result["issues"])

    # compile_whole_dag -- the engine preflight delegates to -- rejects it too and
    # produces no executable phase.
    phases, whole_conflicts, _whole_blocked = compile_whole_dag(dag, {}, workspace)
    assert phases == []
    assert whole_conflicts and whole_conflicts[0].scope == "intra_dag"

    # Preview and execution agree: no op is produced, so nothing is applied.
    assert apply_compiled(ops, workspace) == []
    assert (workspace / "f.txt").read_text(encoding="utf-8") == "a\nb\n"


# ---------------------------------------------------------------------------
# F4 -- zero-old-count insertions compose at the applied base coordinate
# ---------------------------------------------------------------------------
def test_f4_zero_count_insertion_composes_at_correct_base_anchor(tmp_path: Path):
    patch_text = _diff("@@ -1,0 +2,1 @@\n+X\n")
    workspace = _workspace(tmp_path, "a\nb\n")
    dag = single_edit_dag(patch_text)

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert conflicts == []
    assert len(ops) == 1
    # F4: @@ -1,0 +2,1 @@ inserts after original line 1 -> "a\nX\nb\n".
    assert ops[0].applied == "a\nX\nb\n"
    # Consistency with the patch engine's own application of the same patch.
    parsed = parse_unified_diff(patch_text)
    assert apply_file_patch("a\nb\n", parsed[0]) == "a\nX\nb\n"
    assert preflight(dag, {}, workspace)["executable"] is True


def test_f4_zero_count_insertion_after_preceding_delta(tmp_path: Path):
    # Hunk 1 replaces original line 1 with three lines (+2 delta); hunk 2 is a
    # zero-count insertion after original line 3. The composed result must match
    # the engine's offset accumulation rather than double-counting or anchoring
    # one line early.
    patch_text = _diff(
        "@@ -1,1 +1,3 @@\n-a\n+A\n+A2\n+A3\n"
        "@@ -3,0 +5,1 @@\n+X\n"
    )
    workspace = _workspace(tmp_path, "a\nb\nc\n")
    dag = single_edit_dag(patch_text)

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    expected = "A\nA2\nA3\nb\nc\nX\n"
    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].applied == expected
    parsed = parse_unified_diff(patch_text)
    assert apply_file_patch("a\nb\nc\n", parsed[0]) == expected


def test_already_applied_matches_f4_insertion_coordinate(tmp_path: Path):
    patch_text = _diff("@@ -1,0 +2,1 @@\n+X\n")
    parsed = parse_unified_diff(patch_text)

    # The F4-correct applied result is provably present; the pristine base is not.
    assert _already_applied("a\nX\nb\n", parsed) is True
    assert _already_applied("a\nb\n", parsed) is False

    # Under the F4 coordinate the inserted line is now detected in the applied
    # result, but a context-free zero-count insertion is still inherently
    # ambiguous: re-applying it would duplicate "X". Before the coordinate fix
    # this reported "absent" (the new side was searched one line too high).
    workspace = _workspace(tmp_path, "a\nX\nb\n")
    dag = single_edit_dag(patch_text)
    assert node_present(dag, "N2", workspace) == "ambiguous"


# ---------------------------------------------------------------------------
# Valid adjacent and disjoint multi-hunk patches remain accepted
# ---------------------------------------------------------------------------
def test_adjacent_and_disjoint_multi_hunk_patches_still_accepted(tmp_path: Path):
    disjoint = _diff("@@ -1,1 +1,1 @@\n-a\n+A\n@@ -4,1 +4,1 @@\n-d\n+D\n")
    workspace = _workspace(tmp_path, "a\nb\nc\nd\n")
    ops, conflicts, _blocked = compile_operations(single_edit_dag(disjoint), {}, workspace)
    assert conflicts == []
    assert ops[0].applied == "A\nb\nc\nD\n"

    # Hunk 2 is a zero-count insertion exactly at hunk 1's boundary: adjacent, not
    # overlapping, and therefore accepted.
    adjacent = _diff("@@ -1,2 +1,2 @@\n-a\n-b\n+X\n+Y\n@@ -2,0 +3,1 @@\n+Q\n")
    boundary = _workspace(tmp_path / "boundary", "a\nb\nc\n")
    ops2, conflicts2, _blocked2 = compile_operations(
        single_edit_dag(adjacent), {}, boundary
    )
    assert conflicts2 == []
    assert ops2[0].applied == "X\nY\nQ\nc\n"