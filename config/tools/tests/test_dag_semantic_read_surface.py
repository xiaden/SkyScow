"""Tests for the semantic-only DAG read surface."""
from __future__ import annotations

import json
from pathlib import Path

from common.helpers.change_dag import atomic_write_json, dag_json_path
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import add_work
from common.tools.dag_semantic_context import dag_semantic_context
from common.tools.dag_semantic_search import dag_semantic_search


def _payload(result: dict) -> dict:
    return json.loads(result["output"]) if "output" in result else result


def _dag(workspace: Path, slug: str = "demo") -> None:
    create_dag(workspace, slug, {"root": "root", "nodes": {
        "root": {"requirement": "root requirement", "requires": ["feature"]},
        "feature": {"requirement": "implement searchable feature", "requires": ["detail"]},
        "detail": {"requirement": "detail requirement"},
    }})


def test_search_is_semantic_only_deterministic_and_limited(workspace):
    _dag(workspace)
    first = _payload(dag_semantic_search("demo", "feature", 1, workspace_root=workspace))
    second = _payload(dag_semantic_search("demo", "feature", 1, workspace_root=workspace))
    assert first == second
    assert first["slug"] == "demo"
    assert len(first["results"]) == 1
    assert set(first["results"][0]) == {"node_id", "requirement", "depth"}
    assert first["results"][0]["node_id"] == "N2"
    assert _payload(dag_semantic_search("demo", "", workspace_root=workspace))["results"] == []


def test_search_excludes_terminals_and_unreachable_nodes(workspace):
    _dag(workspace)
    add_work(workspace, "demo", "create", ["N3"], path="feature-terminal-marker.txt", content="feature-marker")
    dag = json.loads(dag_json_path(workspace, "demo").read_text())
    dag["nodes"]["N99"] = {"type": "semantic", "requirement": "feature unreachable marker"}
    atomic_write_json(dag_json_path(workspace, "demo"), dag)
    payload = _payload(dag_semantic_search("demo", "feature", workspace_root=workspace))
    ids = {item["node_id"] for item in payload["results"]}
    assert "N4" not in ids
    assert "N99" not in ids


def test_context_reports_semantic_relationships_without_terminal_detail(workspace):
    _dag(workspace)
    add_work(workspace, "demo", "create", ["N3"], path="PATH_MARKER", content="CONTENT_MARKER")
    add_work(workspace, "demo", "edit", ["N3"], path="EDIT_PATH_MARKER", replacements=[{"old": "x", "new": "PATCH_MARKER"}])
    payload = _payload(dag_semantic_context("demo", ["N2"], workspace_root=workspace))
    assert [node["id"] for node in payload["parents"]] == ["N1"]
    assert payload["requires"] == [{"id": "N3", "type": "semantic", "requirement": "detail requirement"}]
    dumped = json.dumps(payload)
    for marker in ("PATH_MARKER", "CONTENT_MARKER", "EDIT_PATH_MARKER", "PATCH_MARKER"):
        assert marker not in dumped
    assert dag_semantic_context("demo", ["N4"], workspace_root=workspace)["error"] == "invalid_target_node"


def test_context_rejects_unknown_and_too_many_ids(workspace):
    _dag(workspace)
    assert dag_semantic_context("demo", ["N99"], workspace_root=workspace)["error"] == "unknown_node"
    result = dag_semantic_context("demo", ["N2"] * 26, workspace_root=workspace)
    assert result["error"] == "too_many_nodes"


def test_plugins_register_both_semantic_tools():
    source = Path(__file__).parents[2].joinpath("plugins", "tools.ts").read_text()
    for tool_name in ("dag_semantic_search", "dag_semantic_context"):
        assert f"{tool_name}: tool(" in source
        assert f"common.tools.{tool_name}" in source
