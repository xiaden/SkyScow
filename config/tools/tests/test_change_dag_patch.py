"""Focused tests for the custom Change DAG unified-diff patch engine."""
from __future__ import annotations

from pathlib import Path

import pytest

from common.helpers.change_dag_patch import (
    FilePatch,
    PatchContextError,
    PatchError,
    apply_file_patch,
    apply_patches,
    atomic_replace,
    detect_eol,
    normalize_eol,
    parse_unified_diff,
    read_text_preserving,
)


def test_parse_simple_diff_with_ab_headers():
    patch = "--- a/x.txt\n+++ b/x.txt\n@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n"
    files = parse_unified_diff(patch)
    assert len(files) == 1
    assert files[0].path == "x.txt"
    hunk = files[0].hunks[0]
    assert (hunk.old_start, hunk.old_count, hunk.new_start, hunk.new_count) == (1, 3, 1, 3)
    assert hunk.lines == [" a", "-b", "+B", " c"]


def test_parse_bare_headers_and_optional_counts():
    patch = "--- x.txt\n+++ x.txt\n@@ -1 +1 @@\n-a\n+b\n"
    files = parse_unified_diff(patch)
    assert files[0].path == "x.txt"
    hunk = files[0].hunks[0]
    assert (hunk.old_count, hunk.new_count) == (1, 1)


def test_parse_multiple_files():
    patch = (
        "--- a/one.txt\n+++ b/one.txt\n@@ -1,1 +1,1 @@\n-a\n+b\n"
        "--- a/two.txt\n+++ b/two.txt\n@@ -1,1 +1,1 @@\n-c\n+d\n"
    )
    files = parse_unified_diff(patch)
    assert [file.path for file in files] == ["one.txt", "two.txt"]


def test_parse_rejects_malformed_input():
    with pytest.raises(PatchError):
        parse_unified_diff("not a diff at all\n")
    with pytest.raises(PatchError):
        parse_unified_diff("--- a/x\n+++ b/x\n")  # no hunks
    with pytest.raises(PatchError):
        parse_unified_diff("--- a/x\n@@ -1,1 +1,1 @@\n-a\n+b\n")  # no +++ header


def test_parse_rejects_no_newline_marker():
    patch = "--- a/x\n+++ b/x\n@@ -2,2 +2,2 @@\n a\n\\ No newline at end of file\n"
    with pytest.raises(PatchError):
        parse_unified_diff(patch)


def test_apply_exact_context_success():
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n"
    file_patch = parse_unified_diff(patch)[0]
    assert apply_file_patch("a\nb\nc\n", file_patch) == "a\nB\nc\n"


def test_zero_fuzz_context_mismatch_raises():
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1,2 +1,2 @@\n a\n-b\n+B\n"
    file_patch = parse_unified_diff(patch)[0]
    with pytest.raises(PatchContextError) as excinfo:
        apply_file_patch("a\nX\n", file_patch)
    assert excinfo.value.hunk_index == 0
    assert excinfo.value.path == "f.txt"


def test_trailing_whitespace_is_significant():
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1,2 +1,2 @@\n a\n-b\n+B\n"
    file_patch = parse_unified_diff(patch)[0]
    # The live line has a trailing space; the patch expects an exact 'b'.
    with pytest.raises(PatchContextError):
        apply_file_patch("a\nb \n", file_patch)

    patch_ws = "--- a/f.txt\n+++ b/f.txt\n@@ -1,2 +1,2 @@\n a\n-b \n+B\n"
    file_patch_ws = parse_unified_diff(patch_ws)[0]
    assert apply_file_patch("a\nb \n", file_patch_ws) == "a\nB\n"


def test_multi_hunk_offset_rebasing():
    original = "1\n2\n3\n4\n5\n"
    patch = (
        "--- a/f.txt\n+++ b/f.txt\n"
        "@@ -1,1 +1,3 @@\n 1\n+one\n+uno\n"
        "@@ -4,1 +4,1 @@\n-4\n+four\n"
    )
    file_patch = parse_unified_diff(patch)[0]
    assert apply_file_patch(original, file_patch) == "1\none\nuno\n2\n3\nfour\n5\n"


def test_out_of_order_hunks_are_rejected():
    patch = (
        "--- a/f.txt\n+++ b/f.txt\n"
        "@@ -4,1 +4,1 @@\n-4\n+four\n"
        "@@ -1,1 +1,2 @@\n 1\n+one\n"
    )
    file_patch = parse_unified_diff(patch)[0]
    with pytest.raises(PatchError):
        apply_file_patch("1\n2\n3\n4\n5\n", file_patch)


def test_crlf_eol_is_preserved():
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n"
    file_patch = parse_unified_diff(patch)[0]
    result = apply_file_patch("a\r\nb\r\nc\r\n", file_patch)
    assert result == "a\r\nB\r\nc\r\n"
    assert detect_eol(result) == "\r\n"
    assert normalize_eol(result) == "a\nB\nc\n"


def test_apply_patches_sequential_against_evolving_text():
    first = parse_unified_diff("--- a/f\n+++ b/f\n@@ -1,1 +1,2 @@\n a\n+inserted\n")[0]
    # Each FilePatch is interpreted against the evolving text, so the second
    # hunk uses the post-first-application line number (line 4, not line 3).
    second = parse_unified_diff("--- a/f\n+++ b/f\n@@ -4,1 +4,1 @@\n-c\n+C\n")[0]
    assert apply_patches("a\nb\nc\n", [first, second]) == "a\ninserted\nb\nC\n"


def test_atomic_replace_round_trip_and_no_leftovers(tmp_path: Path):
    target = tmp_path / "nested" / "f.bin"
    atomic_replace(target, b"\x00\x01payload")
    assert target.read_bytes() == b"\x00\x01payload"
    # The temporary sibling must be gone and the parent must contain only it.
    assert [entry.name for entry in target.parent.iterdir()] == ["f.bin"]


def test_atomic_replace_overwrites_existing(tmp_path: Path):
    target = tmp_path / "f.txt"
    target.write_text("old", encoding="utf-8")
    atomic_replace(target, b"new")
    assert target.read_bytes() == b"new"
    names = [entry.name for entry in tmp_path.iterdir()]
    assert "f.txt" in names
    assert not any(name.endswith(".tmp") for name in names)


def test_read_text_preserving_missing_raises(tmp_path: Path):
    with pytest.raises(PatchError):
        read_text_preserving(tmp_path / "nope.txt")


def test_read_text_preserving_binary_raises(tmp_path: Path):
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"ab\x00cd")
    with pytest.raises(PatchError):
        read_text_preserving(binary)


def test_read_text_preserving_keeps_crlf(tmp_path: Path):
    target = tmp_path / "f.txt"
    target.write_bytes(b"a\r\nb\r\n")
    assert read_text_preserving(target) == "a\r\nb\r\n"


def test_filepatch_dataclass_shape():
    file_patch = FilePatch(path="a.txt", hunks=[])
    assert file_patch.path == "a.txt"
    assert file_patch.hunks == []
