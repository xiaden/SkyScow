"""Focused regression tests for interrupted ``edit`` reconciliation.

The old ``_already_applied`` heuristic matched only new-side lines, so:

* a deletion-only hunk (``@@ -1,1 +0,0 @@`` / ``-delete_me``) had no new-side
  line to compare and succeeded vacuously, marking an unrelated file as the
  applied result; and
* a multi-hunk region position added the accumulated ``new_count - old_count``
  delta on top of ``new_start``, double-counting the delta when the patch
  already carried resulting-file starts.

These tests pin the conservative proof: present requires an exact new-side region
match at the resulting-file coordinate, deletion-only hunks cannot prove
applied-ness, and every other state is ambiguous (which reconciliation maps to
``failed``).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag_state as state_helper
from common.helpers.change_dag_compiler_runtime import _already_applied, node_present
from common.helpers.change_dag_patch import parse_unified_diff
from common.tools import dag_executor


def _diff(body: str, path: str = "f.txt") -> str:
    return f"--- a/{path}\n+++ b/{path}\n{body}"


def _edit_dag(node_id: str, path: str, patch: str) -> dict:
    return {
        "slug": "demo",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "edit", "requires": [node_id]},
            node_id: {"type": "edit", "path": path, "patch": patch},
        },
    }


def _write(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_bytes(root: Path, name: str, content: bytes) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _bundle(root: Path, slug: str, patch: str, state: dict[str, str]) -> None:
    bundle = root / "artifacts" / "change-dags" / "pending" / slug
    bundle.mkdir(parents=True, exist_ok=True)
    dag = _edit_dag("N2", "f.txt", patch)
    dag["slug"] = slug
    (bundle / "DAG.json").write_text(json.dumps(dag), encoding="utf-8")
    state_helper.write_state(root, slug, state)


REPLACE = _diff("@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n")


# ---------------------------------------------------------------------------
# Simple replacement: absent / exact final / unrelated
# ---------------------------------------------------------------------------
def test_replacement_absent_final_and_unrelated(tmp_path: Path):
    patches = parse_unified_diff(REPLACE)
    assert _already_applied("a\nb\nc\n", patches) is False  # original intact
    assert _already_applied("a\nB\nc\n", patches) is True   # exact final result
    assert _already_applied("a\nX\nc\n", patches) is False  # unrelated

    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = _edit_dag("N2", "f.txt", REPLACE)
    _write(workspace, "f.txt", "a\nb\nc\n")
    assert node_present(dag, "N2", workspace) == "absent"
    _write(workspace, "f.txt", "a\nB\nc\n")
    assert node_present(dag, "N2", workspace) == "present"
    _write(workspace, "f.txt", "a\nX\nc\n")
    assert node_present(dag, "N2", workspace) == "ambiguous"


# ---------------------------------------------------------------------------
# Pure deletion
# ---------------------------------------------------------------------------
def test_context_anchored_pure_deletion(tmp_path: Path):
    patch = _diff("@@ -1,3 +1,2 @@\n keep1\n-delete_me\n keep2\n")
    patches = parse_unified_diff(patch)
    assert _already_applied("keep1\ndelete_me\nkeep2\n", patches) is False  # original
    assert _already_applied("keep1\nkeep2\n", patches) is True              # exact post-delete
    assert _already_applied("keep1\nother\nkeep2\n", patches) is False      # mismatch

    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = _edit_dag("N2", "f.txt", patch)
    _write(workspace, "f.txt", "keep1\ndelete_me\nkeep2\n")
    assert node_present(dag, "N2", workspace) == "absent"
    _write(workspace, "f.txt", "keep1\nkeep2\n")
    assert node_present(dag, "N2", workspace) == "present"
    _write(workspace, "f.txt", "keep1\nother\nkeep2\n")
    assert node_present(dag, "N2", workspace) == "ambiguous"


def test_zero_context_pure_deletion_never_false_positive(tmp_path: Path):
    # The exact false-positive shape from the report: no new-side line exists.
    patch = _diff("@@ -1,1 +0,0 @@\n-delete_me\n")
    patches = parse_unified_diff(patch)
    assert _already_applied("unrelated\n", patches) is False
    assert _already_applied("delete_me_extra\n", patches) is False
    # An empty file is not provable either: the original could have been empty.
    assert _already_applied("", patches) is False

    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = _edit_dag("N2", "f.txt", patch)
    _write(workspace, "f.txt", "delete_me\n")
    assert node_present(dag, "N2", workspace) == "absent"  # provably unmodified
    _write(workspace, "f.txt", "unrelated\n")
    assert node_present(dag, "N2", workspace) == "ambiguous"  # not "present"


# ---------------------------------------------------------------------------
# Pure insertion
# ---------------------------------------------------------------------------
def test_pure_insertion_anchored_by_trailing_context(tmp_path: Path):
    # The trailing context anchors the insertion, so the applied result cannot be
    # re-applied and is provably present.
    patch = _diff("@@ -1,2 +1,3 @@\n keep\n+added\n tail\n")
    patches = parse_unified_diff(patch)
    assert _already_applied("keep\ntail\n", patches) is False
    assert _already_applied("keep\nadded\ntail\n", patches) is True
    assert _already_applied("keep\nother\ntail\n", patches) is False

    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = _edit_dag("N2", "f.txt", patch)
    _write(workspace, "f.txt", "keep\ntail\n")
    assert node_present(dag, "N2", workspace) == "absent"
    _write(workspace, "f.txt", "keep\nadded\ntail\n")
    assert node_present(dag, "N2", workspace) == "present"
    _write(workspace, "f.txt", "keep\nother\ntail\n")
    assert node_present(dag, "N2", workspace) == "ambiguous"


def test_trailing_insertion_overlap_is_ambiguous(tmp_path: Path):
    # Without a trailing anchor the already-inserted file still applies (it would
    # insert again), so it is neither provably present nor safe to re-apply.
    patch = _diff("@@ -1,1 +1,2 @@\n keep\n+added\n")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = _edit_dag("N2", "f.txt", patch)
    _write(workspace, "f.txt", "keep\n")
    assert node_present(dag, "N2", workspace) == "absent"
    _write(workspace, "f.txt", "keep\nadded\n")
    assert node_present(dag, "N2", workspace) == "ambiguous"


# ---------------------------------------------------------------------------
# Multiple hunks with an earlier line-count delta
# ---------------------------------------------------------------------------
def test_multi_hunk_uses_resulting_file_coordinates(tmp_path: Path):
    final = "1\none\nuno\n2\n3\nfour\n5\n"
    original = "1\n2\n3\n4\n5\n"
    # Canonical diff: the second hunk's ``new_start`` already includes the +2
    # delta from the first hunk. The old code added the delta again and missed.
    canonical = _diff(
        "@@ -1,1 +1,3 @@\n 1\n+one\n+uno\n@@ -4,1 +6,1 @@\n-4\n+four\n"
    )
    # Change DAG convention: hunks are authored against the common base, so
    # ``new_start`` does not include the delta. ``old_start`` + delta is correct.
    base_authored = _diff(
        "@@ -1,1 +1,3 @@\n 1\n+one\n+uno\n@@ -4,1 +4,1 @@\n-4\n+four\n"
    )
    for patch in (canonical, base_authored):
        patches = parse_unified_diff(patch)
        assert _already_applied(final, patches) is True
        assert _already_applied(original, patches) is False

    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = _edit_dag("N2", "f.txt", canonical)
    _write(workspace, "f.txt", final)
    assert node_present(dag, "N2", workspace) == "present"
    _write(workspace, "f.txt", original)
    assert node_present(dag, "N2", workspace) == "absent"


# ---------------------------------------------------------------------------
# Partial multi-hunk application is ambiguous
# ---------------------------------------------------------------------------
def test_partial_multi_hunk_is_ambiguous(tmp_path: Path):
    patch = _diff("@@ -1,1 +1,2 @@\n l1\n+ins\n@@ -3,1 +3,1 @@\n-l3\n+l3b\n")
    patches = parse_unified_diff(patch)
    final = "l1\nins\nl2\nl3b\n"
    partial = "l1\nins\nl2\nl3\n"  # first hunk applied, second not
    assert _already_applied(final, patches) is True
    assert _already_applied(partial, patches) is False

    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = _edit_dag("N2", "f.txt", patch)
    _write(workspace, "f.txt", final)
    assert node_present(dag, "N2", workspace) == "present"
    _write(workspace, "f.txt", partial)
    assert node_present(dag, "N2", workspace) == "ambiguous"


# ---------------------------------------------------------------------------
# Overlapping external modification is ambiguous
# ---------------------------------------------------------------------------
def test_external_overlapping_modification_is_ambiguous(tmp_path: Path):
    patches = parse_unified_diff(REPLACE)
    # The 'a' context line was externally renamed while 'B' was inserted.
    assert _already_applied("X\nB\nc\n", patches) is False
    assert _already_applied("a\nB\nX\n", patches) is False

    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = _edit_dag("N2", "f.txt", REPLACE)
    _write(workspace, "f.txt", "X\nB\nc\n")
    assert node_present(dag, "N2", workspace) == "ambiguous"


# ---------------------------------------------------------------------------
# CRLF normalization matches patch application
# ---------------------------------------------------------------------------
def test_crlf_result_is_present_and_original_is_absent(tmp_path: Path):
    patches = parse_unified_diff(REPLACE)
    assert _already_applied("a\r\nB\r\nc\r\n", patches) is True

    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = _edit_dag("N2", "f.txt", REPLACE)
    _write_bytes(workspace, "f.txt", b"a\r\nB\r\nc\r\n")
    assert node_present(dag, "N2", workspace) == "present"
    _write_bytes(workspace, "f.txt", b"a\r\nb\r\nc\r\n")
    assert node_present(dag, "N2", workspace) == "absent"


# ---------------------------------------------------------------------------
# reconcile_interrupted mapping: present/absent/ambiguous
# ---------------------------------------------------------------------------
def test_reconcile_interrupted_maps_edit_outcomes(tmp_path: Path):
    present = tmp_path / "present"
    present.mkdir()
    _write(present, "f.txt", "a\nB\nc\n")
    _bundle(present, "present", REPLACE, {"N2": "in_progress"})
    result = dag_executor.reconcile_interrupted(present, "present")
    assert result["reconciled"][0]["resolved"] == "satisfied"
    assert state_helper.read_state(present, "present")["N2"] == "satisfied"

    absent = tmp_path / "absent"
    absent.mkdir()
    _write(absent, "f.txt", "a\nb\nc\n")
    _bundle(absent, "absent", REPLACE, {"N2": "in_progress"})
    result = dag_executor.reconcile_interrupted(absent, "absent")
    assert result["reconciled"][0]["resolved"] == "not_satisfied"
    assert state_helper.read_state(absent, "absent")["N2"] == "not_satisfied"

    ambiguous = tmp_path / "ambiguous"
    ambiguous.mkdir()
    _write(ambiguous, "f.txt", "a\nX\nc\n")
    _bundle(ambiguous, "ambiguous", REPLACE, {"N2": "in_progress"})
    result = dag_executor.reconcile_interrupted(ambiguous, "ambiguous")
    assert result["reconciled"][0]["resolved"] == "failed"
    assert state_helper.read_state(ambiguous, "ambiguous")["N2"] == "failed"
