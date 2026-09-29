from __future__ import annotations

from pathlib import Path

import pytest

from common.helpers.change_dag import atomic_write_json
from common.helpers.worker_resolution import (
    issue_branch_ref,
    require_worker_session,
    reset_worker_state,
    resolve_worker,
)
from common.tools.dag_worker_resolve import dag_worker_resolve


def _workspace(tmp_path: Path, dag: dict) -> Path:
    root = tmp_path / "workspace"
    bundle = root / "artifacts" / "change-dags" / "pending" / dag["slug"]
    bundle.mkdir(parents=True)
    atomic_write_json(bundle / "DAG.json", dag)
    atomic_write_json(bundle / "EXECUTION_STATE.json", {})
    (bundle / "WORK_LOG.jsonl").write_text("", encoding="utf-8")
    return root


def _dag(slug: str = "worker") -> dict:
    return {
        "slug": slug,
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "requires": ["N2"]},
            "N2": {"type": "semantic", "requirement": "author me"},
        },
    }


@pytest.fixture(autouse=True)
def clean_state():
    reset_worker_state()
    yield
    reset_worker_state()


def test_resolve_selects_deterministic_frontier_and_binds_session(tmp_path):
    root = _workspace(tmp_path, _dag())
    ref = issue_branch_ref(root, "worker", "change-dag-worker", "session-1")

    result = resolve_worker(root, "worker", "change-dag-worker", "session-1", ref)

    assert result["node_id"] == "N2"
    assert require_worker_session(root, "worker", "N2", "change-dag-worker", "session-1").branch_ref == ref


def test_branch_ref_is_opaque_one_use_and_bound_to_request(tmp_path):
    root = _workspace(tmp_path, _dag())
    ref = issue_branch_ref(root, "worker", "change-dag-worker", "session-1")

    with pytest.raises(ValueError, match="invalid_branch_ref"):
        resolve_worker(root, "worker", "change-dag-worker", "session-2", ref)
    with pytest.raises(ValueError, match="invalid_branch_ref"):
        resolve_worker(root, "worker", "change-dag-worker", "session-1", ref)


def test_authorization_prevents_wrong_agent_rebind_and_unbound_scope(tmp_path):
    root = _workspace(tmp_path, _dag())
    with pytest.raises(ValueError, match="unauthorized_agent"):
        issue_branch_ref(root, "worker", "not-a-worker", "session-1")

    ref = issue_branch_ref(root, "worker", "change-dag-worker", "session-1")
    resolve_worker(root, "worker", "change-dag-worker", "session-1", ref)
    with pytest.raises(ValueError, match="session_rebind"):
        resolve_worker(root, "worker", "change-dag-worker", "session-1", issue_branch_ref(root, "worker", "change-dag-worker", "session-1"))
    with pytest.raises(ValueError, match="session_unbound"):
        require_worker_session(root, "worker", "N2", "change-dag-worker", "never-bound")
    with pytest.raises(ValueError, match="session_scope_mismatch"):
        require_worker_session(root, "worker", "N1", "change-dag-worker", "session-1")


def test_plugin_tool_returns_structured_authorization_error(tmp_path):
    root = _workspace(tmp_path, _dag())
    result = dag_worker_resolve("worker", "opaque", "wrong-agent", "session", workspace_root=root)
    assert result["error"] == "unauthorized_agent"
