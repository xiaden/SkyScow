"""Structured edit authoring: exact replacements and service-generated patches.

An agent never hand-writes unified diff. ``dag_add_edit`` / ``dag_update_edit``
accept an ordered list of exact ``{old, new}`` replacements interpreted against
the semantic owner's accepted base; the service generates, validates, and
persists the internal unified diff.
"""
from __future__ import annotations

import pytest

from common.helpers import change_dag
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import add_work, update_node
from common.helpers.change_dag_patch import (
    StructuredReplacementError,
    apply_patches,
    apply_structured_replacements,
    generate_unified_diff,
    parse_unified_diff,
    validate_hunk_ranges,
)
from common.tools.dag_add_edit import dag_add_edit
from common.tools.dag_update_edit import dag_update_edit

SLUG = "structured"


def _dag(workspace, slug: str = SLUG) -> None:
    create_dag(
        workspace,
        slug,
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["impl"]},
                "impl": {"requirement": "impl"},
            },
        },
    )


def _three_level(workspace, slug: str = SLUG) -> None:
    # root=N1, mid=N2, leaf=N3 (all semantic).
    create_dag(
        workspace,
        slug,
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["mid"]},
                "mid": {"requirement": "mid", "requires": ["leaf"]},
                "leaf": {"requirement": "leaf"},
            },
        },
    )


def _seed(workspace, rel: str, text: str) -> None:
    path = workspace / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _nodes(workspace, slug: str = SLUG) -> dict:
    dag, _path, _location = change_dag.read_dag(workspace, slug)
    return change_dag.node_map(dag)


def _patch(workspace, node_id: str = "N3", slug: str = SLUG) -> str:
    return _nodes(workspace, slug)[node_id]["patch"]


def _dag_text(workspace, slug: str = SLUG) -> str:
    return change_dag.dag_json_path(workspace, slug).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Exact replace generation and round-trip
# ---------------------------------------------------------------------------
def test_valid_replacement_generates_roundtripping_patch(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\n")

    result = add_work(
        workspace, SLUG, "edit", ["N2"], path="a.txt",
        replacements=[{"old": "a", "new": "b"}],
    )
    assert result.get("error") is None

    node = _nodes(workspace)["N3"]
    assert node["type"] == "edit"
    assert node["path"] == "a.txt"
    parsed = parse_unified_diff(node["patch"])
    assert len(parsed) == 1
    assert parsed[0].path == "a.txt"
    validate_hunk_ranges(parsed[0], path="a.txt")
    assert apply_patches("a\n", parsed, path="a.txt") == "b\n"


def test_missing_old_is_context_missing(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\n")
    before = _dag_text(workspace)

    rejected = add_work(
        workspace, SLUG, "edit", ["N2"], path="a.txt",
        replacements=[{"old": "zzz", "new": "b"}],
    )
    assert rejected["error"] == "edit_context_missing"
    assert _dag_text(workspace) == before


def test_ambiguous_old_is_context_ambiguous(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "x\nx\n")
    before = _dag_text(workspace)

    rejected = add_work(
        workspace, SLUG, "edit", ["N2"], path="a.txt",
        replacements=[{"old": "x", "new": "y"}],
    )
    assert rejected["error"] == "edit_context_ambiguous"
    assert _dag_text(workspace) == before


def test_noop_replacement_is_no_change(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\n")
    before = _dag_text(workspace)

    rejected = add_work(
        workspace, SLUG, "edit", ["N2"], path="a.txt",
        replacements=[{"old": "a", "new": "a"}],
    )
    assert rejected["error"] == "edit_no_change"
    assert _dag_text(workspace) == before


def test_sequential_replacements_apply_in_order(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\n")

    result = add_work(
        workspace, SLUG, "edit", ["N2"], path="a.txt",
        replacements=[{"old": "a", "new": "b"}, {"old": "b", "new": "c"}],
    )
    assert result.get("error") is None
    assert apply_patches("a\n", parse_unified_diff(_patch(workspace)), path="a.txt") == "c\n"


def test_insertion_is_anchor_plus_text_and_empty_new_deletes(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\nb\n")

    insert = add_work(
        workspace, SLUG, "edit", ["N2"], path="a.txt",
        replacements=[{"old": "b\n", "new": "b\ninserted\n"}],
    )
    assert insert.get("error") is None
    assert (
        apply_patches("a\nb\n", parse_unified_diff(_patch(workspace)), path="a.txt")
        == "a\nb\ninserted\n"
    )


def test_empty_new_deletes_matched_text(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\nb\n")

    result = add_work(
        workspace, SLUG, "edit", ["N2"], path="a.txt",
        replacements=[{"old": "a\n", "new": ""}],
    )
    assert result.get("error") is None
    assert apply_patches("a\nb\n", parse_unified_diff(_patch(workspace)), path="a.txt") == "b\n"


# ---------------------------------------------------------------------------
# Raw diff syntax is not part of the agent-facing API
# ---------------------------------------------------------------------------
def test_raw_patch_input_is_rejected(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\n")
    before = _dag_text(workspace)

    rejected = add_work(
        workspace, SLUG, "edit", ["N2"], path="a.txt",
        patch="--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-a\n+b\n",
    )
    assert rejected["error"] == "invalid_replacements"
    assert _dag_text(workspace) == before


def test_envelope_replacement_is_not_fuzzy_matched(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\n")

    rejected = add_work(
        workspace, SLUG, "edit", ["N2"], path="a.txt",
        replacements=[{"old": "*** Begin Patch", "new": ""}],
    )
    assert rejected["error"] == "edit_context_missing"


def test_update_rejects_raw_patch_field(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\n")
    add_work(workspace, SLUG, "edit", ["N2"], path="a.txt",
             replacements=[{"old": "a", "new": "b"}])

    rejected = update_node(
        workspace, SLUG, "N3",
        patch="--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-a\n+b\n",
    )
    assert rejected["error"] == "invalid_field"


# ---------------------------------------------------------------------------
# Authoritative base: live, lower work, peers, absence
# ---------------------------------------------------------------------------
def test_edit_sees_file_created_by_accepted_lower_work(workspace):
    _three_level(workspace)
    created = add_work(workspace, SLUG, "create", ["N3"], path="gen.txt", content="hello\n")
    assert created.get("error") is None

    result = add_work(
        workspace, SLUG, "edit", ["N2"], path="gen.txt",
        replacements=[{"old": "hello", "new": "bye"}],
    )
    assert result.get("error") is None
    parsed = parse_unified_diff(_patch(workspace, "N5"))
    assert apply_patches("hello\n", parsed, path="gen.txt") == "bye\n"


def test_edit_does_not_see_same_frontier_peer(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\n")
    first = add_work(workspace, SLUG, "edit", ["N2"], path="a.txt",
                     replacements=[{"old": "a", "new": "A"}])
    assert first.get("error") is None

    # The peer's output is invisible: the base stays the live accepted content.
    rejected = add_work(workspace, SLUG, "edit", ["N2"], path="a.txt",
                        replacements=[{"old": "A", "new": "AA"}])
    assert rejected["error"] == "edit_context_missing"


def test_edit_absent_file_is_base_unavailable(workspace):
    _dag(workspace)
    before = _dag_text(workspace)

    rejected = add_work(workspace, SLUG, "edit", ["N2"], path="ghost.txt",
                        replacements=[{"old": "a", "new": "b"}])
    assert rejected["error"] == "edit_base_unavailable"
    assert _dag_text(workspace) == before


# ---------------------------------------------------------------------------
# Local preconditions for the other terminal kinds
# ---------------------------------------------------------------------------
def test_create_precondition_target_exists(workspace):
    _dag(workspace)
    _seed(workspace, "x.txt", "a\n")

    rejected = add_work(workspace, SLUG, "create", ["N2"], path="x.txt", content="new\n")
    assert rejected["error"] == "create_target_exists"


def test_remove_precondition_target_unavailable(workspace):
    _dag(workspace)
    rejected = add_work(workspace, SLUG, "remove", ["N2"], path="ghost.txt")
    assert rejected["error"] == "remove_target_unavailable"


def test_move_source_unavailable(workspace):
    _dag(workspace)
    rejected = add_work(workspace, SLUG, "move", ["N2"], from_path="src.txt", to_path="dst.txt")
    assert rejected["error"] == "move_source_unavailable"


def test_move_destination_conflict_and_overwrite(workspace):
    _dag(workspace)
    _seed(workspace, "src.txt", "s\n")
    _seed(workspace, "dst.txt", "d\n")

    rejected = add_work(workspace, SLUG, "move", ["N2"], from_path="src.txt", to_path="dst.txt")
    assert rejected["error"] == "move_destination_conflict"

    allowed = add_work(
        workspace, SLUG, "move", ["N2"], from_path="src.txt", to_path="dst.txt", overwrite=True
    )
    assert allowed.get("error") is None


def test_move_destination_produced_by_lower_work_conflicts(workspace):
    _three_level(workspace)
    _seed(workspace, "src.txt", "s\n")
    created = add_work(workspace, SLUG, "create", ["N3"], path="dst.txt", content="d\n")
    assert created.get("error") is None

    rejected = add_work(workspace, SLUG, "move", ["N2"], from_path="src.txt", to_path="dst.txt")
    assert rejected["error"] == "move_destination_conflict"


# ---------------------------------------------------------------------------
# Atomic update: regenerate one consolidated patch, never partial
# ---------------------------------------------------------------------------
def test_failed_update_leaves_previous_edit_unchanged(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\nb\n")
    added = add_work(workspace, SLUG, "edit", ["N2"], path="a.txt",
                     replacements=[{"old": "a", "new": "A"}])
    assert added.get("error") is None
    before = _dag_text(workspace)

    rejected = update_node(workspace, SLUG, "N3", replacements=[{"old": "zzz", "new": "x"}])
    assert rejected["error"] == "edit_context_missing"
    assert _dag_text(workspace) == before

    updated = update_node(workspace, SLUG, "N3", replacements=[{"old": "b", "new": "B"}])
    assert updated.get("error") is None
    parsed = parse_unified_diff(_patch(workspace))
    assert apply_patches("a\nb\n", parsed, path="a.txt") == "A\nB\n"


def test_tool_modules_accept_structured_replacements(workspace):
    _dag(workspace)
    _seed(workspace, "a.txt", "a\n")

    added = dag_add_edit(SLUG, ["N2"], "a.txt", [{"old": "a", "new": "b"}], workspace_root=workspace)
    assert added["metadata"]["node_id"] == "N3"

    updated = dag_update_edit(SLUG, "N3", replacements=[{"old": "b", "new": "c"}], workspace_root=workspace)
    assert updated["metadata"]["node_id"] == "N3"

    parsed = parse_unified_diff(_patch(workspace))
    assert apply_patches("a\n", parsed, path="a.txt") == "c\n"


# ---------------------------------------------------------------------------
# Generator and application helpers
# ---------------------------------------------------------------------------
def test_generate_unified_diff_round_trips_and_validates():
    patch = generate_unified_diff("a\nb\n", "A\nb\n", "p.txt")
    parsed = parse_unified_diff(patch)
    assert len(parsed) == 1
    assert parsed[0].path == "p.txt"
    validate_hunk_ranges(parsed[0], path="p.txt")
    assert apply_patches("a\nb\n", parsed, path="p.txt") == "A\nb\n"


def test_generate_unified_diff_handles_no_trailing_newline():
    patch = generate_unified_diff("a", "b", "p.txt")
    parsed = parse_unified_diff(patch)
    assert apply_patches("a", parsed, path="p.txt") == "b"


def test_apply_structured_replacements_error_classes():
    cases = [
        ([], "invalid_replacements"),
        ([{"old": "z", "new": "b"}], "edit_context_missing"),
        ([{"old": "x", "new": "y"}], "edit_context_ambiguous"),
        ([{"old": "a", "new": "a"}], "edit_no_change"),
        ([{"old": "a", "new": 5}], "invalid_replacements"),
        ([{"old": "", "new": "b"}], "invalid_replacements"),
        (["a"], "invalid_replacements"),
    ]
    for replacements, code in cases:
        with pytest.raises(StructuredReplacementError) as exc:
            apply_structured_replacements("x\nx\n" if code == "edit_context_ambiguous" else "a\n", replacements)
        assert exc.value.code == code
