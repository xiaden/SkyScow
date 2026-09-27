"""Focused tests for the bounded Change DAG decomposition-scope Worker context.

The worker-facing question is "what exact semantic node do I own, what
immediately surrounds it, and where am I in the decomposition?" The derivation
is graph-local only: the target node, its immediate semantic parents, the
deduplicated sibling union, and the target's direct children. It performs no
repository discovery, compiles no patches, and never includes a whole-DAG dump,
a transitive ancestor tree, a prior worker summary, or same-frontier peer work.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from common.helpers.change_dag_decomposition import decomposition_scope
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import add_work
from common.tools.dag_decomposition_scope import dag_decomposition_scope

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "config" / "agents"

PATCH = "@@ -1 +1 @@\n-a\n+b\n"


def _payload(result: dict) -> dict:
    return json.loads(result["output"])


def _dag(nodes: dict) -> dict:
    return {"slug": "scope", "anchor_commit": "a" * 40, "root": "N1", "nodes": nodes}


def _semantic(requirement: str, children: list[str] | None = None, **extra) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if children is not None:
        node["requires"] = children
    node.update(extra)
    return node


def _edit(path: str = "x.txt") -> dict:
    return {"type": "edit", "path": path, "patch": PATCH}


def _permission(agent_name: str) -> dict:
    raw = (AGENTS / f"{agent_name}.md").read_text(encoding="utf-8")
    return yaml.safe_load(raw.split("---", 2)[1])["permission"]


# ---------------------------------------------------------------------------
# 1. the assigned target, its parents, and its children are reported
# ---------------------------------------------------------------------------
def test_correct_target_reports_assigned_scope():
    dag = _dag(
        {
            "N1": _semantic("root", ["N2"]),
            "N2": _semantic("mid", ["N3"]),
            "N3": _edit(),
        }
    )

    payload = decomposition_scope(dag, "N2")

    assert payload["target"] == {
        "id": "N2",
        "requirement": "mid",
        "depth": 1,
        "decomposition_only": False,
        "resolved": True,
        "scope": "assigned",
    }
    assert payload["parents"] == [
        {"id": "N1", "requirement": "root", "scope": "context_only"}
    ]
    assert payload["siblings"] == []
    assert payload["children"] == [
        {"id": "N3", "type": "edit", "path": "x.txt", "scope": "context_only"}
    ]


# ---------------------------------------------------------------------------
# 2. all immediate parents are returned (never modelled as one parent)
# ---------------------------------------------------------------------------
def test_multiple_immediate_parents_all_returned():
    dag = _dag(
        {
            "N1": _semantic("root", ["N2", "N3"]),
            "N2": _semantic("left", ["N4"]),
            "N3": _semantic("right", ["N4"]),
            "N4": _semantic("shared"),
        }
    )

    payload = decomposition_scope(dag, "N4")

    assert [p["id"] for p in payload["parents"]] == ["N2", "N3"]
    assert [p["requirement"] for p in payload["parents"]] == ["left", "right"]
    assert all(p["scope"] == "context_only" for p in payload["parents"])
    # The target's depth is the longest root path, via either parent.
    assert payload["target"]["depth"] == 2
    assert payload["siblings"] == []
    assert payload["children"] == []


# ---------------------------------------------------------------------------
# 3. sibling union across parents, deduplicated by canonical identity
# ---------------------------------------------------------------------------
def test_sibling_union_is_deduplicated_across_parents():
    dag = _dag(
        {
            "N1": _semantic("root", ["N2", "N3"]),
            "N2": _semantic("left", ["N4", "N5"]),
            "N3": _semantic("right", ["N4", "N5", "N6"]),
            "N4": _semantic("target"),
            "N5": _semantic("shared-sibling"),
            "N6": _semantic("right-only-sibling"),
        }
    )

    payload = decomposition_scope(dag, "N4")

    assert [s["id"] for s in payload["siblings"]] == ["N5", "N6"]
    assert [s["requirement"] for s in payload["siblings"]] == [
        "shared-sibling",
        "right-only-sibling",
    ]
    assert all(s["scope"] == "out_of_scope" for s in payload["siblings"])


# ---------------------------------------------------------------------------
# 4. children carry bounded semantic and terminal identity
# ---------------------------------------------------------------------------
def test_children_carry_semantic_and_terminal_identity():
    dag = _dag(
        {
            "N1": _semantic("root", ["N2"]),
            "N2": _semantic("target", ["N3", "N4", "N5", "N6", "N7"]),
            "N3": _semantic("semantic-child"),
            "N4": {"type": "create", "path": "new.txt", "content": "x\n"},
            "N5": _edit("edited.txt"),
            "N6": {"type": "remove", "path": "gone.txt"},
            "N7": {"type": "move", "from_path": "a.txt", "to_path": "b.txt"},
        }
    )

    payload = decomposition_scope(dag, "N2")

    assert payload["children"] == [
        {
            "id": "N3",
            "type": "semantic",
            "requirement": "semantic-child",
            "scope": "context_only",
        },
        {"id": "N4", "type": "create", "path": "new.txt", "scope": "context_only"},
        {"id": "N5", "type": "edit", "path": "edited.txt", "scope": "context_only"},
        {"id": "N6", "type": "remove", "path": "gone.txt", "scope": "context_only"},
        {
            "id": "N7",
            "type": "move",
            "from_path": "a.txt",
            "to_path": "b.txt",
            "scope": "context_only",
        },
    ]
    # A direct terminal child resolves the semantic requirement locally.
    assert payload["target"]["resolved"] is True


def test_run_child_reports_command_identity():
    dag = _dag(
        {
            "N1": _semantic("root", ["N2"]),
            "N2": _semantic("verify", ["N3"]),
            "N3": {"type": "run", "command": ["pytest", "-q"]},
        }
    )

    payload = decomposition_scope(dag, "N2")

    assert payload["children"] == [
        {"id": "N3", "type": "run", "command": ["pytest", "-q"], "scope": "context_only"}
    ]


# ---------------------------------------------------------------------------
# 5. shared-descendant topology stays graph-local
# ---------------------------------------------------------------------------
def test_shared_descendant_topology_stays_graph_local():
    dag = _dag(
        {
            "N1": _semantic("root", ["N2", "N3"]),
            "N2": _semantic("left", ["N4", "N5"]),
            "N3": _semantic("right", ["N4"]),
            "N4": _semantic("target", ["N7"]),
            "N5": _semantic("sibling", ["N6"]),
            "N6": _semantic("sibling-descendant"),
            "N7": _semantic("target-child", ["N8"]),
            "N8": _semantic("target-grandchild"),
        }
    )

    payload = decomposition_scope(dag, "N4")

    assert [p["id"] for p in payload["parents"]] == ["N2", "N3"]
    assert [s["id"] for s in payload["siblings"]] == ["N5"]
    assert [c["id"] for c in payload["children"]] == ["N7"]
    # No transitive ancestor tree and no deeper descendant traversal.
    rendered = json.dumps(payload)
    for excluded in ("N1", "N6", "N8"):
        assert excluded not in rendered


# ---------------------------------------------------------------------------
# 6. unknown and terminal targets are rejected
# ---------------------------------------------------------------------------
def test_unknown_target_rejected():
    dag = _dag({"N1": _semantic("root")})

    payload = decomposition_scope(dag, "N99")

    assert payload["error"] == "unknown_node"


def test_terminal_target_rejected():
    dag = _dag({"N1": _semantic("root", ["N2"]), "N2": _edit()})

    payload = decomposition_scope(dag, "N2")

    assert payload["error"] == "invalid_target_node"


# ---------------------------------------------------------------------------
# 7. resolved target is accurately reported across resolution states
# ---------------------------------------------------------------------------
def test_resolved_target_accurately_reported():
    # Semantic-only children without the decomposition flag: not resolved.
    open_dag = _dag(
        {
            "N1": _semantic("root", ["N2"]),
            "N2": _semantic("open", ["N3"]),
            "N3": _semantic("child"),
        }
    )
    target = decomposition_scope(open_dag, "N2")["target"]
    assert target["resolved"] is False
    assert target["decomposition_only"] is False

    # Declared fully decomposed into semantic children: resolved and flagged.
    decomposed_dag = _dag(
        {
            "N1": _semantic("root", ["N2"]),
            "N2": _semantic("decomposed", ["N3"], decomposition_only=True),
            "N3": _semantic("child"),
        }
    )
    target = decomposition_scope(decomposed_dag, "N2")["target"]
    assert target["resolved"] is True
    assert target["decomposition_only"] is True

    # No children at all: unresolved.
    leaf_dag = _dag({"N1": _semantic("root")})
    target = decomposition_scope(leaf_dag, "N1")["target"]
    assert target["resolved"] is False


# ---------------------------------------------------------------------------
# 8. scope labels are stable
# ---------------------------------------------------------------------------
def test_scope_labels_are_stable():
    dag = _dag(
        {
            "N1": _semantic("root", ["N2", "N3"]),
            "N2": _semantic("parent", ["N4", "N5"]),
            "N3": _semantic("other"),
            "N4": _semantic("target", ["N6"]),
            "N5": _semantic("sibling"),
            "N6": _semantic("child"),
        }
    )

    payload = decomposition_scope(dag, "N4")

    assert payload["target"]["scope"] == "assigned"
    assert {p["scope"] for p in payload["parents"]} == {"context_only"}
    assert {s["scope"] for s in payload["siblings"]} == {"out_of_scope"}
    assert {c["scope"] for c in payload["children"]} == {"context_only"}


# ---------------------------------------------------------------------------
# 9. tool-level behavior
# ---------------------------------------------------------------------------
def test_tool_returns_bounded_scope_for_semantic_node(workspace):
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["mid", "sib"]},
                "mid": {"requirement": "mid", "requires": ["impl"]},
                "sib": {"requirement": "sib"},
                "impl": {"requirement": "impl"},
            },
        },
    )

    payload = _payload(
        dag_decomposition_scope("demo", "N2", workspace_root=workspace)
    )

    assert payload["target"] == {
        "id": "N2",
        "requirement": "mid",
        "depth": 1,
        "decomposition_only": False,
        "resolved": False,
        "scope": "assigned",
    }
    assert payload["parents"] == [
        {"id": "N1", "requirement": "root", "scope": "context_only"}
    ]
    assert payload["siblings"] == [
        {"id": "N3", "type": "semantic", "requirement": "sib", "scope": "out_of_scope"}
    ]
    assert payload["children"] == [
        {"id": "N4", "type": "semantic", "requirement": "impl", "scope": "context_only"}
    ]


def test_tool_reports_resolved_target_after_terminal_work(workspace):
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
    add_work(workspace, "demo", "create", ["N2"], path="new.txt", content="x\n")

    payload = _payload(
        dag_decomposition_scope("demo", "N2", workspace_root=workspace)
    )

    assert payload["target"]["resolved"] is True
    assert payload["target"]["decomposition_only"] is False
    assert payload["children"] == [
        {"id": "N3", "type": "create", "path": "new.txt", "scope": "context_only"}
    ]


def test_missing_and_malformed_dag_follow_tool_error_conventions(workspace):
    missing = dag_decomposition_scope("missing", "N1", workspace_root=workspace)
    assert missing["error"] == "dag_not_found"

    bundle = workspace / "artifacts" / "change-dags" / "pending" / "broken"
    bundle.mkdir(parents=True)
    (bundle / "DAG.json").write_text("{ not json", encoding="utf-8")

    malformed = dag_decomposition_scope("broken", "N1", workspace_root=workspace)
    assert malformed["error"] == "dag_read_failed"


def test_tool_target_errors_are_unwrapped(workspace):
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
    add_work(workspace, "demo", "create", ["N2"], path="new.txt", content="x\n")

    unknown = dag_decomposition_scope("demo", "N99", workspace_root=workspace)
    assert unknown["error"] == "unknown_node"
    assert "output" not in unknown

    terminal = dag_decomposition_scope("demo", "N3", workspace_root=workspace)
    assert terminal["error"] == "invalid_target_node"
    assert "output" not in terminal


# ---------------------------------------------------------------------------
# 10. the Worker owns the tool; the Author and others do not
# ---------------------------------------------------------------------------
def test_worker_permission_owns_decomposition_scope():
    assert (
        _permission("change-dag-worker").get("dag_decomposition_scope") == "allow"
    )
    for agent in ("change-dag-author", "change-dag-reviewer", "nyx"):
        assert (
            _permission(agent).get("dag_decomposition_scope", "deny") == "deny"
        ), agent
