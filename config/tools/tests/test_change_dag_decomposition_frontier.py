"""Focused tests for the Change DAG decomposition-frontier derivation and tool.

The manager-facing question is "which unresolved semantic branches are currently
the deepest branches ready for bounded worker authoring?" The derivation reuses
the existing strict depth/frontier model (longest path from root plus the
existing local-resolution semantics) and never infers a dependency the graph
does not express through ``requires``.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from common.helpers.change_dag_decomposition import decomposition_frontier
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import add_requirement
from common.tools.dag_decomposition_frontier import dag_decomposition_frontier

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "config" / "agents"

PATCH = "@@ -1 +1 @@\n-a\n+b\n"


def _payload(result: dict) -> dict:
    return json.loads(result["output"])


def _dag(nodes: dict) -> dict:
    return {"slug": "frontier", "anchor_commit": "a" * 40, "root": "N1", "nodes": nodes}


def _semantic(requirement: str, children: list[str] | None = None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if children is not None:
        node["requires"] = children
    return node


def _edit(path: str = "x.txt") -> dict:
    return {"type": "edit", "path": path, "patch": PATCH}


def _permission(agent_name: str) -> dict:
    raw = (AGENTS / f"{agent_name}.md").read_text(encoding="utf-8")
    return yaml.safe_load(raw.split("---", 2)[1])["permission"]


# ---------------------------------------------------------------------------
# 1. deepest unresolved nodes selected; shallower wait; resolved excluded
# ---------------------------------------------------------------------------
def test_deepest_unresolved_selected_shallower_wait_resolved_excluded():
    dag = _dag(
        {
            "N1": _semantic("root", ["N2", "N5"]),
            "N2": _semantic("mid-a", ["N3"]),
            "N3": _semantic("mid-b", ["N4"]),
            "N4": _semantic("resolved-branch", ["N10"]),
            "N10": _edit(),
            "N5": _semantic("mid-c", ["N6"]),
            "N6": _semantic("mid-d", ["N7"]),
            "N7": _semantic("deepest-open"),
        }
    )

    payload = decomposition_frontier(dag)

    # N7 is the deepest unresolved node (depth 3). Its same-depth sibling N4 is
    # excluded because it resolves through a terminal child; the shallower
    # unresolved N1/N2/N3/N5/N6 wait.
    assert payload == {
        "resolved": False,
        "frontier": {"depth": 3, "branches": [{"node_id": "N7"}]},
    }


# ---------------------------------------------------------------------------
# 2. a shared descendant appears once by canonical node identity
# ---------------------------------------------------------------------------
def test_shared_descendant_returned_once():
    dag = _dag(
        {
            "N1": _semantic("root", ["N2", "N3"]),
            "N2": _semantic("left", ["N4"]),
            "N3": _semantic("right", ["N4"]),
            "N4": _semantic("shared-open"),
        }
    )

    payload = decomposition_frontier(dag)

    assert payload["resolved"] is False
    assert payload["frontier"]["depth"] == 2
    assert payload["frontier"]["branches"] == [{"node_id": "N4"}]


# ---------------------------------------------------------------------------
# 3. an entirely resolved graph returns no frontier
# ---------------------------------------------------------------------------
def test_entirely_resolved_graph_has_no_frontier():
    dag = _dag({"N1": _semantic("root", ["N2"]), "N2": _edit()})

    assert decomposition_frontier(dag) == {"resolved": True, "frontier": None}


# ---------------------------------------------------------------------------
# 4. newly introduced deeper semantics become the next frontier
# ---------------------------------------------------------------------------
def test_newly_introduced_deeper_semantics_become_next_frontier(workspace):
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["mid"]},
                "mid": {"requirement": "mid", "requires": ["leaf"]},
                "leaf": {"requirement": "leaf"},
            },
        },
    )

    first = _payload(dag_decomposition_frontier("demo", workspace_root=workspace))
    assert first == {
        "resolved": False,
        "frontier": {"depth": 2, "branches": [{"node_id": "N3"}]},
    }

    added = add_requirement(workspace, "demo", "deeper", ["N3"])
    assert _payload(added)["node_id"] == "N4"

    second = _payload(dag_decomposition_frontier("demo", workspace_root=workspace))
    assert second == {
        "resolved": False,
        "frontier": {"depth": 3, "branches": [{"node_id": "N4"}]},
    }


def test_resolved_dag_tool_reports_no_frontier(workspace):
    create_dag(
        workspace,
        "demo",
        {"root": "root", "nodes": {"root": {"requirement": "root"}}},
    )
    from common.helpers.change_dag_ops_mutation import add_work

    add_work(workspace, "demo", "create", ["N1"], path="new.txt", content="x\n")

    assert _payload(dag_decomposition_frontier("demo", workspace_root=workspace)) == {
        "resolved": True,
        "frontier": None,
    }


# ---------------------------------------------------------------------------
# 5. missing / malformed DAG follows normal tool error conventions
# ---------------------------------------------------------------------------
def test_missing_and_malformed_dag_follow_tool_error_conventions(workspace):
    missing = dag_decomposition_frontier("missing", workspace_root=workspace)
    assert missing["error"] == "dag_not_found"

    bundle = workspace / "artifacts" / "change-dags" / "pending" / "broken"
    bundle.mkdir(parents=True)
    (bundle / "DAG.json").write_text("{ not json", encoding="utf-8")

    malformed = dag_decomposition_frontier("broken", workspace_root=workspace)
    assert malformed["error"] == "dag_read_failed"


# ---------------------------------------------------------------------------
# 6. Author permission owns the tool; worker, reviewer, and Nyx do not
# ---------------------------------------------------------------------------
def test_author_permission_owns_decomposition_frontier():
    assert _permission("change-dag-author").get("dag_decomposition_frontier") == "allow"
    for agent in ("change-dag-worker", "change-dag-reviewer", "nyx"):
        assert _permission(agent).get("dag_decomposition_frontier", "deny") == "deny", agent
