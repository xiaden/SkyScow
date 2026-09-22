from __future__ import annotations

import json
from pathlib import Path

from common.helpers.implementation_graph import implementation_state_digest, workspace_fingerprint
from common.tools.impl_graph_amend import impl_graph_amend
from common.tools.impl_graph_archive import impl_graph_archive
from common.tools.impl_graph_block import impl_graph_block
from common.tools.impl_graph_claim import impl_graph_claim
from common.tools.impl_graph_complete import impl_graph_complete
from common.tools.impl_graph_create import impl_graph_create
from common.tools.impl_graph_read import impl_graph_read
from common.tools.impl_graph_record_qa import impl_graph_record_qa
from common.tools.impl_graph_release import impl_graph_release
from common.tools.impl_graph_validate import impl_graph_validate


def graph(request_context="artifacts/requests/CTX_test.md"):
    return {
        "graph_id": "test-graph",
        "title": "Test graph",
        "source": {"request_context": request_context, "design_doc": None},
        "requirements": [{"id": "R1", "text": "make it work", "source": "request"}],
        "contracts": [],
        "nodes": [
            {"id": "I001", "title": "first", "obligation": "Implement first", "depends_on": [], "satisfies": ["R1"], "acceptance": ["evidence"], "status": "PENDING"},
            {"id": "I002", "title": "second", "obligation": "Implement second", "depends_on": ["I001"], "satisfies": [], "acceptance": ["evidence"], "status": "PENDING"},
        ],
        "final_qa": {"status": "PENDING"},
    }


def unwrap(result):
    return json.loads(result["output"])


def test_graph_lifecycle_and_qa_invalidation(tmp_path: Path):
    request = tmp_path / "workspace/artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    workspace = request.parents[2]
    assert "error" not in impl_graph_create(graph(), workspace_root=workspace)
    assert unwrap(impl_graph_read("test-graph", "ready", workspace_root=workspace))["nodes"][0]["id"] == "I001"
    claimed = unwrap(impl_graph_claim("test-graph", ["I001"], "claim-1", worker="worker", manager_session="session-1", write_scopes=["src/**"], workspace_root=workspace))
    assert claimed["claimed"] == ["I001"]
    assert "error" in impl_graph_claim("test-graph", ["I002"], "claim-2", manager_session="session-1", write_scopes=["src/**"], workspace_root=workspace)
    complete = unwrap(impl_graph_complete("test-graph", ["I001"], "claim-1", results=[{"node_id": "I001", "evidence": ["ok"]}], workspace_root=workspace))
    assert complete["completed"] == ["I001"]
    assert unwrap(impl_graph_read("test-graph", "ready", workspace_root=workspace))["nodes"][0]["id"] == "I002"
    assert "error" not in impl_graph_amend("test-graph", nodes=[{"id": "I003", "title": "third", "obligation": "third", "depends_on": ["I002"], "status": "PENDING"}], actor="planner", reason="add downstream obligation", workspace_root=workspace)
    assert unwrap(impl_graph_validate("test-graph", workspace_root=workspace))["valid"]
    claimed = unwrap(impl_graph_claim("test-graph", ["I002"], "claim-2", worker="worker", manager_session="session-1", write_scopes=["src/**"], workspace_root=workspace))
    assert claimed["claimed"] == ["I002"]
    assert "error" in impl_graph_release("test-graph", ["I002"], "missing", workspace_root=workspace)
    released = unwrap(impl_graph_release("test-graph", ["I002"], "claim-2", workspace_root=workspace))
    assert released["released"] == ["I002"]
    assert "error" not in impl_graph_block("test-graph", ["I002"], "waiting", workspace_root=workspace)


def test_cycle_and_missing_reference_are_rejected(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    candidate = graph()
    candidate["nodes"][0]["depends_on"] = ["I002"]
    assert "error" in impl_graph_create(candidate, workspace_root=workspace)
    candidate = graph()
    candidate["nodes"][1]["depends_on"] = ["I999"]
    assert "error" in impl_graph_create(candidate, workspace_root=workspace)


def test_terminal_qa_and_archive_require_fresh_evidence(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    candidate = graph(); candidate["nodes"] = [candidate["nodes"][0]]
    assert "error" not in impl_graph_create(candidate, workspace_root=workspace)
    claim = unwrap(impl_graph_claim("test-graph", ["I001"], "claim", manager_session="session-1", write_scopes=["src/**"], workspace_root=workspace))
    impl_graph_complete("test-graph", ["I001"], "claim", results=[{"node_id": "I001", "evidence": ["ok"]}], workspace_root=workspace)
    current = json.loads((workspace / "artifacts/implementation/pending/test-graph/GRAPH.json").read_text())
    assert "error" not in impl_graph_record_qa("test-graph", "PASS", {"checks": ["ok"]}, workspace_root=workspace)
    assert "error" not in impl_graph_archive("test-graph", workspace_root=workspace)
    assert (workspace / "artifacts/implementation/completed/test-graph/GRAPH.json").is_file()
