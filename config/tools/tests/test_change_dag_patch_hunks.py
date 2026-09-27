"""Regression tests for the Change DAG unified-diff hunk engine.

Covers three bounded findings:

* F4 -- zero-old-count insertion coordinates and multi-hunk offset accumulation.
* F6 -- overlapping hunks must be rejected deterministically before mutation so
  preview-time composition and apply-time application cannot disagree.
* F7 -- atomic replacement preserves the destination's permission bits.

Expected results are derived by hand from the unified-diff specification; none
of the assertions read the implementation's own output as an oracle.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from common.helpers.change_dag_patch import (
    FilePatch,
    Hunk,
    PatchContextError,
    PatchError,
    apply_file_patch,
    apply_patches,
    atomic_replace,
    parse_unified_diff,
)


def _diff(body: str, path: str = "f.txt") -> str:
    return f"--- a/{path}\n+++ b/{path}\n{body}"


# ---------------------------------------------------------------------------
# F4 -- zero-old-count insertion coordinates
# ---------------------------------------------------------------------------
def test_f4_insert_at_beginning():
    # @@ -0,0 +1,1 @@ inserts before the first original line (0-based index 0).
    file_patch = parse_unified_diff(_diff("@@ -0,0 +1,1 @@\n+X\n"))[0]
    assert apply_file_patch("a\nb\n", file_patch) == "X\na\nb\n"


def test_f4_insert_in_middle():
    # @@ -1,0 +2,1 @@ inserts after original line 1 (0-based index 1).
    file_patch = parse_unified_diff(_diff("@@ -1,0 +2,1 @@\n+X\n"))[0]
    assert apply_file_patch("a\nb\n", file_patch) == "a\nX\nb\n"


def test_f4_insert_at_end():
    # @@ -2,0 +3,1 @@ inserts after original line 2 (0-based index 2 == EOF).
    file_patch = parse_unified_diff(_diff("@@ -2,0 +3,1 @@\n+X\n"))[0]
    assert apply_file_patch("a\nb\n", file_patch) == "a\nb\nX\n"


def test_f4_insert_after_preceding_line_count_change():
    # Hunk 1 replaces original line 1 with three lines (+2 delta). Hunk 2 then
    # inserts after original line 3; the running offset (+2) must reposition it.
    patch = _diff(
        "@@ -1,1 +1,3 @@\n-a\n+A\n+A2\n+A3\n"
        "@@ -3,0 +5,1 @@\n+X\n"
    )
    file_patch = parse_unified_diff(patch)[0]
    assert apply_file_patch("a\nb\nc\n", file_patch) == "A\nA2\nA3\nb\nc\nX\n"


def test_f4_insert_composed_with_replacement():
    # Hunk 1 inserts after line 1 (delta +1); hunk 2 replaces original line 4.
    patch = _diff(
        "@@ -1,0 +2,1 @@\n+X\n"
        "@@ -4,1 +5,1 @@\n-d\n+D\n"
    )
    file_patch = parse_unified_diff(patch)[0]
    assert apply_file_patch("a\nb\nc\nd\n", file_patch) == "a\nX\nb\nc\nD\n"


def test_f4_insert_past_end_of_file_is_rejected():
    # old_start == 3 on a two-line file targets index 3 > len(lines); appending
    # silently or clamping would both be wrong.
    file_patch = parse_unified_diff(_diff("@@ -3,0 +4,1 @@\n+X\n"))[0]
    with pytest.raises(PatchContextError):
        apply_file_patch("a\nb\n", file_patch)


def test_f4_insert_far_past_end_of_file_is_rejected():
    file_patch = parse_unified_diff(_diff("@@ -9,0 +10,1 @@\n+X\n"))[0]
    with pytest.raises(PatchContextError):
        apply_file_patch("a\nb\n", file_patch)


# ---------------------------------------------------------------------------
# F6 -- overlapping hunks rejected before any mutation
# ---------------------------------------------------------------------------
F6_OVERLAP = _diff(
    "@@ -1,2 +1,2 @@\n-a\n-b\n+X\n+Y\n"
    "@@ -2,1 +2,1 @@\n-Y\n+Z\n"
)


def test_f6_overlapping_hunks_rejected_at_parse():
    with pytest.raises(PatchError) as excinfo:
        parse_unified_diff(F6_OVERLAP)
    message = str(excinfo.value)
    assert "overlap" in message.lower()
    assert "f.txt" in message
    assert "hunk 0" in message
    assert "hunk 1" in message


def test_f6_overlapping_hunks_produce_no_mutation_through_apply_patches():
    live = "a\nb\n"
    result = live
    with pytest.raises(PatchError):
        # The only producer of FilePatch objects is parse_unified_diff, which
        # rejects the overlap before apply_patches is ever reached.
        patches = parse_unified_diff(F6_OVERLAP)
        result = apply_patches(live, patches)
    assert result == live


def test_f6_overlapping_hunks_rejected_when_constructed_directly():
    # apply_patches/apply_file_patch are public entry points, so a directly
    # constructed overlapping FilePatch is rejected too (never partially mutated).
    file_patch = FilePatch(
        path="f.txt",
        hunks=[
            Hunk(1, 2, 1, 2, ["-a", "-b", "+X", "+Y"]),
            Hunk(2, 1, 2, 1, ["-Y", "+Z"]),
        ],
    )
    with pytest.raises(PatchError):
        apply_patches("a\nb\n", [file_patch])


def test_f6_adjacent_hunks_are_accepted():
    # Hunk 1 covers original lines 1-2; hunk 2 starts at original line 3.
    patch = _diff(
        "@@ -1,2 +1,2 @@\n-a\n-b\n+X\n+Y\n"
        "@@ -3,1 +3,1 @@\n-c\n+Z\n"
    )
    file_patch = parse_unified_diff(patch)[0]
    assert apply_file_patch("a\nb\nc\n", file_patch) == "X\nY\nZ\n"


def test_f6_disjoint_multi_hunk_patch_is_accepted():
    patch = _diff(
        "@@ -1,1 +1,1 @@\n-a\n+A\n"
        "@@ -4,1 +4,1 @@\n-d\n+D\n"
    )
    file_patch = parse_unified_diff(patch)[0]
    assert apply_file_patch("a\nb\nc\nd\n", file_patch) == "A\nb\nc\nD\n"


def test_f6_zero_count_insertion_at_boundary_is_accepted():
    # Hunk 1 covers original lines 1-2 (0-based [0, 2)); hunk 2 inserts at
    # 0-based index 2, exactly the boundary, which must remain valid.
    patch = _diff(
        "@@ -1,2 +1,2 @@\n-a\n-b\n+X\n+Y\n"
        "@@ -2,0 +3,1 @@\n+Q\n"
    )
    file_patch = parse_unified_diff(patch)[0]
    assert apply_file_patch("a\nb\nc\n", file_patch) == "X\nY\nQ\nc\n"


# ---------------------------------------------------------------------------
# F7 -- atomic replacement preserves permission bits
# ---------------------------------------------------------------------------
def test_f7_existing_executable_mode_is_preserved(tmp_path: Path):
    target = tmp_path / "run.sh"
    target.write_text("a\n", encoding="utf-8")
    os.chmod(target, 0o755)
    atomic_replace(target, b"b\n")
    assert target.read_bytes() == b"b\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o755


def test_f7_existing_non_executable_mode_is_preserved(tmp_path: Path):
    target = tmp_path / "f.txt"
    target.write_text("a\n", encoding="utf-8")
    os.chmod(target, 0o644)
    atomic_replace(target, b"b\n")
    assert stat.S_IMODE(target.stat().st_mode) == 0o644


def test_f7_create_new_file_keeps_default_mode(tmp_path: Path):
    target = tmp_path / "new.txt"
    atomic_replace(target, b"x\n")
    assert target.read_bytes() == b"x\n"
    # Create-new policy is unchanged: the mkstemp default (0o600) survives.
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_f7_apply_then_atomic_replace_preserves_exec_bit(tmp_path: Path):
    # The edit path is read -> apply_patches -> atomic_replace; the executable
    # bit must survive the whole path.
    target = tmp_path / "run.sh"
    target.write_text("a\nb\n", encoding="utf-8")
    os.chmod(target, 0o755)
    file_patch = parse_unified_diff(_diff("@@ -1,2 +1,2 @@\n-a\n+A\n b\n"))[0]
    updated = apply_patches(target.read_text(encoding="utf-8"), [file_patch])
    atomic_replace(target, updated.encode("utf-8"))
    assert target.read_text(encoding="utf-8") == "A\nb\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o755


def test_f7_failure_cleanup_is_preserved(tmp_path: Path, monkeypatch):
    workdir = tmp_path / "work"
    workdir.mkdir()
    target = workdir / "f.txt"
    target.write_text("old", encoding="utf-8")
    os.chmod(target, 0o755)

    def _boom(*_args, **_kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr("common.helpers.change_dag_patch.os.replace", _boom)
    with pytest.raises(OSError):
        atomic_replace(target, b"new")
    # Original untouched, temporary file removed.
    assert target.read_text(encoding="utf-8") == "old"
    assert [entry.name for entry in workdir.iterdir()] == ["f.txt"]
    assert stat.S_IMODE(target.stat().st_mode) == 0o755
