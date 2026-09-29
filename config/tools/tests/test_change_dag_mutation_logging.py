"""Focused tests for append-only Change DAG construction provenance."""
from __future__ import annotations

import json
from pathlib import Path

from common.helpers.change_dag import dag_json_path
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import add_requirement, link_requirement
from common.helpers.change_dag_mutation_log import mutation_log_path


def _events(workspace: Path, slug: str = "demo") -> list[dict]:
    path = mutation_log_path(workspace, slug)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _create(workspace: Path, slug: str = "demo") -> dict:
    return create_dag(
        workspace,
        slug,
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["child"]},
                "child": {"requirement": "child"},
            },
        },
    )


def test_creation_and_successful_mutation_log_sequence_and_snapshots(workspace):
    _create(workspace)
    result = add_requirement(workspace, "demo", "new child", ["N2"])

    events = _events(workspace)
    assert [event["sequence"] for event in events] == [1, 2]
    assert all(event["success"] for event in events)
    assert events[0]["operation"] == "create_dag"
    assert events[0]["before_digest"] is None
    assert events[0]["after_digest"]
    mutation = events[1]
    assert mutation["before_digest"] != mutation["after_digest"]
    assert mutation["after_digest"]
    assert set(mutation["affected_node_ids"]) == {"N2", "N3"}
    assert set(mutation["before_nodes"]) == {"N2"}
    assert set(mutation["after_nodes"]) == {"N2", "N3"}
    assert mutation["requires_added"] == [{"parent_id": "N2", "child_id": "N3"}]
    assert "semantic_graph" not in mutation["operation_args"]["kwargs"] or "secret" not in json.dumps(mutation["operation_args"])
    dag = json.loads(dag_json_path(workspace, "demo").read_text())
    assert dag["nodes"]["N3"]["requirement"] == "new child"


def test_failed_mutation_logs_without_changing_dag_or_claiming_success(workspace):
    _create(workspace)
    before = dag_json_path(workspace, "demo").read_bytes()

    result = add_requirement(workspace, "demo", "", ["N1"])

    assert result["error"] == "invalid_requirement"
    assert dag_json_path(workspace, "demo").read_bytes() == before
    event = _events(workspace)[1]
    assert event["success"] is False
    assert "after_digest" not in event
    assert event["before_digest"]
    assert event["before_nodes"] == {}
    assert event["after_nodes"] == {}
    assert event["error"]["code"] == "invalid_requirement"


def test_legacy_dag_initializes_log_on_first_mutation(workspace):
    _create(workspace)
    mutation_log_path(workspace, "demo").unlink()

    result = link_requirement(workspace, "demo", "N1", "N1")

    assert result["error"] == "self_reference"
    events = _events(workspace)
    assert len(events) == 1
    assert events[0]["sequence"] == 1
    assert events[0]["success"] is False
