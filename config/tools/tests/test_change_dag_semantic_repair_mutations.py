from __future__ import annotations

from pathlib import Path

from common.helpers.caller_identity import set_caller_identity
from common.helpers.change_dag_control import checkpoint_identity
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import link_requirement, unlink_requirement
from common.helpers import change_dag


def _identity(agent: str, session: str) -> dict:
    return {
        "__skyscow_internal": {
            "caller_identity": {"agent": agent, "session": session, "message": "test"},
            "semantic_repair_binding": {
                "slug": "repair",
                "session_id": session,
                "checkpoint_identity": "PLACEHOLDER",
            },
        }
    }


def _checkpoint(workspace: Path) -> str:
    dag, _path, _location = change_dag.read_dag(workspace, "repair")
    return checkpoint_identity(dag)


def test_repair_session_advances_checkpoint_across_unlink_then_link(workspace: Path):
    create_dag(
        workspace,
        "repair",
        {"root": "root", "nodes": {"root": {"requirement": "root", "requires": ["parent", "other"]}, "parent": {"requirement": "parent", "requires": ["leaf"]}, "other": {"requirement": "other", "requires": ["leaf"]}, "leaf": {"requirement": "leaf"}}},
    )
    session = "repair-session"
    binding = _identity("change-dag-semantic-repairer", session)
    binding["__skyscow_internal"]["semantic_repair_binding"]["checkpoint_identity"] = _checkpoint(workspace)

    set_caller_identity(binding)
    unlinked = unlink_requirement(workspace, "repair", "N2", "N4")
    assert "error" not in unlinked
    next_checkpoint = unlinked["metadata"]["semantic_repair_checkpoint_identity"]
    assert next_checkpoint != binding["__skyscow_internal"]["semantic_repair_binding"]["checkpoint_identity"]

    binding["__skyscow_internal"]["semantic_repair_binding"]["checkpoint_identity"] = next_checkpoint
    set_caller_identity(binding)
    linked = link_requirement(workspace, "repair", "N1", "N4")
    assert "error" not in linked
    assert linked["metadata"]["semantic_repair_checkpoint_identity"] == _checkpoint(workspace)


def test_repair_session_rejects_external_drift(workspace: Path):
    create_dag(
        workspace,
        "repair",
        {"root": "root", "nodes": {"root": {"requirement": "root", "requires": ["parent", "other"]}, "parent": {"requirement": "parent", "requires": ["leaf"]}, "other": {"requirement": "other", "requires": ["leaf"]}, "leaf": {"requirement": "leaf"}}},
    )
    session = "repair-session"
    binding = _identity("change-dag-semantic-repairer", session)
    binding["__skyscow_internal"]["semantic_repair_binding"]["checkpoint_identity"] = _checkpoint(workspace)

    external = {"__skyscow_internal": {"caller_identity": {"agent": "change-dag-author", "session": "author", "message": "external"}}}
    set_caller_identity(external)
    external_result = unlink_requirement(workspace, "repair", "N2", "N4")
    assert "error" not in external_result

    set_caller_identity(binding)
    rejected = link_requirement(workspace, "repair", "N1", "N4")
    assert rejected["error"] == "semantic_repair_scope_violation"
    assert "stale" in rejected["message"]
