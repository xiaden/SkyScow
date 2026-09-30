"""Focused tests for the semantic-edge reconciliation primitives.

``dag_link_requirement`` / ``dag_unlink_requirement`` are the Author's
one-edge-at-a-time graph-surgery tools. They add or remove exactly one causal
``requires`` edge from an existing semantic parent to an existing semantic or
terminal child, running through
the same candidate/validate/persist pipeline as every other DAG mutation. These
tests pin that behavior, its precise errors, byte-for-byte atomicity, the
link/unlink round trip, the author/worker permission split, and that the bulk
``requires`` update surface was NOT opened.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import yaml

from common.helpers.change_dag import dag_json_path
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import (
    add_work,
    link_requirement,
    unlink_requirement,
    update_node,
)
from common.tools.dag_link_requirement import dag_link_requirement
from common.tools.dag_unlink_requirement import dag_unlink_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "config" / "agents"
PLUGIN = REPO_ROOT / "config" / "plugins" / "tools.ts"

EDGE_TOOLS = ("dag_link_requirement", "dag_unlink_requirement")


def _payload(result: dict) -> dict:
    return json.loads(result["output"]) if "output" in result else result


def _text(workspace, slug: str = "demo") -> str:
    return dag_json_path(workspace, slug).read_text(encoding="utf-8")


def _dag(workspace, slug: str = "demo") -> dict:
    return json.loads(_text(workspace, slug))


def _permission(agent_name: str) -> dict:
    raw = (AGENTS / f"{agent_name}.md").read_text(encoding="utf-8")
    return yaml.safe_load(raw.split("---", 2)[1])["permission"]


def _siblings(workspace) -> None:
    # BFS canonical IDs: root=N1, left=N2, right=N3. ``left`` and ``right`` are
    # independent semantic leaves.
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["left", "right"]},
                "left": {"requirement": "left"},
                "right": {"requirement": "right"},
            },
        },
    )


def _diamond(workspace) -> None:
    # BFS canonical IDs: root=N1, left=N2, right=N3, shared=N4. ``shared`` is
    # reached through both ``left`` and ``right``.
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["left", "right"]},
                "left": {"requirement": "left", "requires": ["shared"]},
                "right": {"requirement": "right", "requires": ["shared"]},
                "shared": {"requirement": "shared"},
            },
        },
    )


def _chain(workspace) -> None:
    # BFS canonical IDs: root=N1, a=N2, b=N3.
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["a"]},
                "a": {"requirement": "a", "requires": ["b"]},
                "b": {"requirement": "b"},
            },
        },
    )




def _with_terminal(workspace) -> str:
    # BFS canonical IDs: root=N1, impl=N2; the create terminal lands as N3.
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["impl"]},
                "impl": {"requirement": "impl"},
            },
        },
    )
    added = add_work(workspace, "demo", "create", ["N2"], path="new.txt", content="x\n")
    return _payload(added)["node_id"]


# ---------------------------------------------------------------------------
# link
# ---------------------------------------------------------------------------
def test_link_adds_exactly_one_edge_and_leaves_endpoints_unchanged(workspace):
    _siblings(workspace)
    before = _dag(workspace)

    result = link_requirement(workspace, "demo", "N2", "N3")

    assert _payload(result) == {"slug": "demo", "parent_id": "N2", "child_id": "N3"}
    after = _dag(workspace)
    assert after["nodes"]["N2"]["requires"] == ["N3"]
    # Every other node, and both endpoints otherwise, is untouched.
    assert after["nodes"]["N3"] == before["nodes"]["N3"]
    assert after["nodes"]["N1"] == before["nodes"]["N1"]
    assert after["root"] == "N1"
    assert set(after["nodes"]) == {"N1", "N2", "N3"}


def test_link_duplicate_edge_is_rejected_and_writes_nothing(workspace):
    _siblings(workspace)
    before = _text(workspace)

    result = link_requirement(workspace, "demo", "N1", "N3")

    assert result["error"] == "duplicate_edge"
    assert _text(workspace) == before


def test_link_self_edge_is_rejected_and_writes_nothing(workspace):
    _siblings(workspace)
    before = _text(workspace)

    result = link_requirement(workspace, "demo", "N2", "N2")

    assert result["error"] == "self_reference"
    assert _text(workspace) == before


def test_link_terminal_endpoint_is_rejected_and_writes_nothing(workspace):
    terminal_id = _with_terminal(workspace)
    before = _text(workspace)

    as_child = link_requirement(workspace, "demo", "N1", terminal_id)
    assert as_child["error"] == "invalid_graph"
    assert any("root" in error for error in as_child["errors"])
    assert _text(workspace) == before

    as_parent = link_requirement(workspace, "demo", terminal_id, "N1")
    assert as_parent["error"] == "invalid_node"
    assert _text(workspace) == before


def test_link_that_creates_a_cycle_is_rejected_and_writes_nothing(workspace):
    _chain(workspace)
    before = _text(workspace)

    result = link_requirement(workspace, "demo", "N3", "N2")

    assert result["error"] == "cycle_detected"
    assert _text(workspace) == before


def test_link_unknown_endpoint_is_rejected_and_writes_nothing(workspace):
    _siblings(workspace)
    before = _text(workspace)

    assert link_requirement(workspace, "demo", "N1", "N99")["error"] == "unknown_node"
    assert _text(workspace) == before
    assert link_requirement(workspace, "demo", "N99", "N1")["error"] == "unknown_node"
    assert _text(workspace) == before


@pytest.mark.parametrize(
    ("kind", "fields"),
    [
        ("edit", {"path": "base.txt", "replacements": [{"old": "a", "new": "b"}]}),
        ("create", {"path": "created.txt", "content": "x\n"}),
        ("remove", {"path": "removable.txt"}),
        ("move", {"from_path": "source.txt", "to_path": "target.txt"}),
        ("run", {"command": ["python3", "-m", "compileall", "-q", "."]}),
    ],
)
def test_link_accepts_each_terminal_child_kind_when_structurally_legal(workspace, kind, fields):
    _siblings(workspace)
    if kind in {"edit", "remove"}:
        (workspace / fields["path"]).write_text("a\n", encoding="utf-8")
    if kind == "move":
        (workspace / fields["from_path"]).write_text("a\n", encoding="utf-8")
    terminal = _payload(add_work(workspace, "demo", kind, ["N2"], **fields))["node_id"]
    linked = link_requirement(workspace, "demo", "N3", terminal)
    assert "error" not in linked
    assert terminal in _dag(workspace)["nodes"]["N3"]["requires"]


def test_shared_terminal_owner_is_valid_graph_but_ambiguous_for_owner_mutation(workspace):
    _siblings(workspace)
    terminal = _payload(
        add_work(workspace, "demo", "create", ["N2"], path="shared.txt", content="x\n")
    )["node_id"]
    assert "error" not in link_requirement(workspace, "demo", "N3", terminal)
    before = _text(workspace)
    result = update_node(workspace, "demo", terminal, content="changed\n")
    assert result["error"] == "ambiguous_terminal_owner"
    assert _text(workspace) == before


# ---------------------------------------------------------------------------
# unlink
# ---------------------------------------------------------------------------
def test_unlink_removes_one_edge_and_pops_the_last_requires(workspace):
    _diamond(workspace)
    before = _dag(workspace)

    # N2(left) -> N4(shared) is redundant for reachability: N4 stays reachable
    # through N3(right).
    result = unlink_requirement(workspace, "demo", "N2", "N4")

    assert _payload(result) == {"slug": "demo", "parent_id": "N2", "child_id": "N4"}
    after = _dag(workspace)
    # The last edge was removed, so ``requires`` is popped, not left empty.
    assert "requires" not in after["nodes"]["N2"]
    assert after["nodes"]["N4"] == before["nodes"]["N4"]
    assert after["nodes"]["N3"] == before["nodes"]["N3"]
    assert after["nodes"]["N1"] == before["nodes"]["N1"]


def test_unlink_non_existent_edge_is_rejected_and_writes_nothing(workspace):
    _diamond(workspace)
    before = _text(workspace)

    # root does not directly require shared, and the reversed edge does not exist.
    assert unlink_requirement(workspace, "demo", "N1", "N4")["error"] == "unknown_edge"
    assert _text(workspace) == before
    assert unlink_requirement(workspace, "demo", "N4", "N2")["error"] == "unknown_edge"
    assert _text(workspace) == before


def test_unlink_that_would_strand_a_node_is_rejected_and_writes_nothing(workspace):
    _chain(workspace)
    before = _text(workspace)

    # Removing N2 -> N3 strands N3: no other path reaches it.
    result = unlink_requirement(workspace, "demo", "N2", "N3")

    assert result["error"] == "invalid_graph"
    assert any("not reachable from root" in message for message in result["errors"])
    assert _text(workspace) == before


def test_link_then_unlink_restores_byte_identical_dag(workspace):
    _siblings(workspace)
    before = _text(workspace)

    linked = link_requirement(workspace, "demo", "N2", "N3")
    assert _payload(linked)["child_id"] == "N3"
    assert _text(workspace) != before

    unlinked = unlink_requirement(workspace, "demo", "N2", "N3")
    assert _payload(unlinked)["child_id"] == "N3"
    assert _text(workspace) == before


# ---------------------------------------------------------------------------
# tool wrappers and registration
# ---------------------------------------------------------------------------
def test_tool_modules_delegate_to_the_shared_pipeline(workspace):
    _siblings(workspace)

    linked = _payload(dag_link_requirement("demo", "N2", "N3", workspace_root=workspace))
    assert linked["parent_id"] == "N2"
    unlinked = _payload(
        dag_unlink_requirement("demo", "N2", "N3", workspace_root=workspace)
    )
    assert unlinked["child_id"] == "N3"
    assert "requires" not in _dag(workspace)["nodes"]["N2"]


def test_plugin_registers_both_edge_tools():
    source = PLUGIN.read_text(encoding="utf-8")
    for tool_name in EDGE_TOOLS:
        assert f"{tool_name}: tool(" in source, f"{tool_name} is not registered"
        assert f"common.tools.{tool_name}" in source, f"{tool_name} runner dispatch missing"


# ---------------------------------------------------------------------------
# authority
# ---------------------------------------------------------------------------
def test_author_and_worker_explicitly_deny_edge_tools():
    author = _permission("change-dag-author")
    assert author.get("dag_link_requirement", "deny") == "deny"
    assert author.get("dag_unlink_requirement", "deny") == "deny"

    worker = _permission("change-dag-worker")
    assert worker.get("dag_link_requirement") == "deny"
    assert worker.get("dag_unlink_requirement") == "deny"

    for agent in ("change-dag-worker", "change-dag-reviewer", "nyx"):
        permission = _permission(agent)
        for tool in EDGE_TOOLS:
            assert permission.get(tool, "deny") == "deny", f"{agent} must not own {tool}"


# ---------------------------------------------------------------------------
# the bulk requires surface stays closed
# ---------------------------------------------------------------------------
def test_requires_is_not_an_updatable_field(workspace):
    _siblings(workspace)
    before = _text(workspace)

    result = update_node(workspace, "demo", "N2", requires=["N3"])

    assert result["error"] == "invalid_field"
    assert _text(workspace) == before
