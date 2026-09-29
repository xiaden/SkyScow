"""Focused tests for append-only Change DAG construction provenance."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.helpers.change_dag import dag_json_path
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import add_requirement, link_requirement
from common.helpers import change_dag_mutation_log
from common.helpers.change_dag_mutation_log import mutation_log_path
from common.helpers.caller_identity import caller_identity_from_args, set_caller_identity


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


def test_public_args_cannot_forge_caller_identity():
    assert caller_identity_from_args({"agent": "forged", "session": "forged", "message": "forged"}) is None


def test_plugin_caller_identity_is_logged_and_direct_calls_are_unattributed(workspace):
    _create(workspace)
    set_caller_identity({"__skyscow_internal": {"caller_identity": {"agent": "change-dag-author", "session": "ses_1", "message": "msg_1"}}})
    add_requirement(workspace, "demo", "plugin child", ["N2"])
    assert _events(workspace)[1]["caller_identity"] == {
        "agent": "change-dag-author",
        "session": "ses_1",
        "message": "msg_1",
    }

    add_requirement(workspace, "demo", "direct child", ["N2"])
    assert _events(workspace)[2]["caller_identity"] is None


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


def test_logging_is_enabled_by_default(workspace):
    _create(workspace)

    assert mutation_log_path(workspace, "demo").exists()


@pytest.mark.parametrize("disabled_value", ["off", "false", "0"])
def test_logging_is_disabled_without_changing_graph(workspace, monkeypatch, disabled_value):
    _create(workspace)
    monkeypatch.setenv(change_dag_mutation_log.MUTATION_LOG_ENV, disabled_value)
    before = dag_json_path(workspace, "demo").read_bytes()
    log_before = mutation_log_path(workspace, "demo").read_bytes()

    result = add_requirement(workspace, "demo", "disabled child", ["N2"])

    assert "error" not in result
    assert dag_json_path(workspace, "demo").read_bytes() != before
    assert mutation_log_path(workspace, "demo").read_bytes() == log_before


def test_append_failure_is_nonfatal_and_warns_after_persistence(workspace, monkeypatch):
    _create(workspace)
    monkeypatch.setattr("common.helpers.change_dag_ops_support.append_mutation_event", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")))

    result = add_requirement(workspace, "demo", "persisted child", ["N2"])

    assert "error" not in result
    assert result["metadata"]["warning"] == "mutation provenance was not recorded: disk full"
    assert json.loads(dag_json_path(workspace, "demo").read_text())["nodes"]["N3"]["requirement"] == "persisted child"


def test_sequence_uses_newest_tail_entry(workspace):
    _create(workspace)
    path = mutation_log_path(workspace, "demo")
    path.write_text("".join(json.dumps({"sequence": sequence}) + "\n" for sequence in range(1, 4)), encoding="utf-8")

    add_requirement(workspace, "demo", "tail child", ["N2"])

    assert _events(workspace)[-1]["sequence"] == 4


def test_sequence_ignores_partial_tail_prefix(workspace):
    _create(workspace)
    path = mutation_log_path(workspace, "demo")
    path.write_text(
        json.dumps({"sequence": 2, "padding": "x" * change_dag_mutation_log._SEQUENCE_TAIL_BYTES})
        + "\n"
        + json.dumps({"sequence": 3})
        + "\n",
        encoding="utf-8",
    )

    add_requirement(workspace, "demo", "tail edge child", ["N2"])

    assert _events(workspace)[-1]["sequence"] == 4


def test_legacy_dag_initializes_log_on_first_mutation(workspace):
    _create(workspace)
    mutation_log_path(workspace, "demo").unlink()

    result = link_requirement(workspace, "demo", "N1", "N1")

    assert result["error"] == "self_reference"
    events = _events(workspace)
    assert len(events) == 1
    assert events[0]["sequence"] == 1
    assert events[0]["success"] is False
