from __future__ import annotations

import json
from pathlib import Path

from common.helpers.implementation_graph import graph_structure_digest, implementation_state_digest, workspace_fingerprint
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


def _frontier_graph(request_context: str, node_ids: list[str]) -> dict:
    return {
        "graph_id": "frontier-graph",
        "title": "Frontier graph",
        "source": {"request_context": request_context, "design_doc": None},
        "requirements": [{"id": "R1", "text": "frontier", "source": "request"}],
        "contracts": [],
        "nodes": [
            {"id": node_id, "title": node_id, "obligation": f"Implement {node_id}",
             "depends_on": [], "satisfies": ["R1"] if index == 0 else [],
             "acceptance": ["evidence"], "status": "PENDING"}
            for index, node_id in enumerate(node_ids)
        ],
        "final_qa": {"status": "PENDING"},
    }


def test_multi_node_claim_uses_one_packet_scope_and_releases_on_completion(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    assert "error" not in impl_graph_create(_frontier_graph("artifacts/requests/CTX_test.md", ["I001", "I002"]), workspace_root=workspace)

    claimed = impl_graph_claim(
        "frontier-graph", ["I001", "I002"], "packet-1", worker="worker",
        manager_session="session-1", write_scopes=["src/shared/**"], workspace_root=workspace,
    )
    assert unwrap(claimed)["claimed"] == ["I001", "I002"]
    assert "error" in impl_graph_claim(
        "frontier-graph", ["I001"], "packet-2", manager_session="session-2",
        write_scopes=["src/shared/**"], workspace_root=workspace,
    )
    assert "error" not in impl_graph_release("frontier-graph", ["I001", "I002"], "packet-1", workspace_root=workspace)

    assert "error" not in impl_graph_claim(
        "frontier-graph", ["I001"], "packet-3", manager_session="session-3",
        write_scopes=["src/one/**"], workspace_root=workspace,
    )
    assert "error" not in impl_graph_claim(
        "frontier-graph", ["I002"], "packet-4", manager_session="session-4",
        write_scopes=["src/two/**"], workspace_root=workspace,
    )
    assert "error" in impl_graph_claim(
        "frontier-graph", ["I001"], "packet-5", manager_session="session-5",
        write_scopes=["src/one/**"], workspace_root=workspace,
    )
    assert "error" not in impl_graph_complete(
        "frontier-graph", ["I001"], "packet-3",
        results=[{"node_id": "I001", "evidence": ["done"]}], workspace_root=workspace,
    )
    assert "error" not in impl_graph_release("frontier-graph", ["I002"], "packet-4", workspace_root=workspace)
    assert "error" not in impl_graph_claim(
        "frontier-graph", ["I002"], "packet-6", manager_session="session-6",
        write_scopes=["src/one/**"], workspace_root=workspace,
    )


def test_claim_rejects_duplicate_node_ids(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    assert "error" not in impl_graph_create(_frontier_graph("artifacts/requests/CTX_test.md", ["I001"]), workspace_root=workspace)
    result = impl_graph_claim(
        "frontier-graph", ["I001", "I001"], "packet", manager_session="session",
        write_scopes=["src/**"], workspace_root=workspace,
    )
    assert result["error"] == "invalid_claim"


def test_claim_requires_current_structure_view_and_accepts_matching_revision(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    assert "error" not in impl_graph_create(_frontier_graph("artifacts/requests/CTX_test.md", ["I001"]), workspace_root=workspace)
    current = json.loads((workspace / "artifacts/implementation/pending/frontier-graph/GRAPH.json").read_text())
    assert "error" not in impl_graph_amend(
        "frontier-graph", operations=[{"op": "update_pending_node", "node_id": "I001", "patch": {"title": "updated"}}],
        actor="planner", reason="structural race", workspace_root=workspace,
    )
    stale = impl_graph_claim(
        "frontier-graph", ["I001"], "stale", manager_session="session", write_scopes=["src/**"],
        expected_structure_revision=current["structure_revision"], workspace_root=workspace,
    )
    assert stale["error"] == "stale_graph_view"
    current = json.loads((workspace / "artifacts/implementation/pending/frontier-graph/GRAPH.json").read_text())
    matching = impl_graph_claim(
        "frontier-graph", ["I001"], "current", manager_session="session", write_scopes=["src/**"],
        expected_structure_revision=current["structure_revision"], expected_structure_digest=graph_structure_digest(current),
        workspace_root=workspace,
    )
    assert "error" not in matching


def test_bounded_amendment_operations_and_guards(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    candidate = _frontier_graph("artifacts/requests/CTX_test.md", ["I001"])
    assert "error" not in impl_graph_create(candidate, workspace_root=workspace)
    result = impl_graph_amend(
        "frontier-graph",
        operations=[
            {"op": "add_node", "node": {"id": "I002", "title": "second", "obligation": "second"}},
            {"op": "add_dependency", "node_id": "I002", "depends_on": "I001"},
            {"op": "update_pending_node", "node_id": "I002", "patch": {"acceptance": ["contract"]}},
            {"op": "map_requirement", "node_id": "I002", "requirement_id": "R1"},
        ], actor="planner", reason="add bounded downstream obligation", workspace_root=workspace,
    )
    assert "error" not in result
    graph_path = workspace / "artifacts/implementation/pending/frontier-graph/GRAPH.json"
    graph_state = json.loads(graph_path.read_text())
    assert graph_state["structure_revision"] == 2
    assert graph_state["nodes"][1]["depends_on"] == ["I001"]
    assert "error" in impl_graph_amend(
        "frontier-graph", operations=[{"op": "add_dependency", "node_id": "I001", "depends_on": "I002"}],
        actor="planner", reason="cycle", workspace_root=workspace,
    )
    assert "error" not in impl_graph_amend(
        "frontier-graph", operations=[{"op": "remove_dependency", "node_id": "I002", "depends_on": "I001"}],
        actor="planner", reason="remove edge", workspace_root=workspace,
    )

    claimed = impl_graph_claim("frontier-graph", ["I001"], "claim", manager_session="session", write_scopes=["src/**"], workspace_root=workspace)
    assert "error" not in claimed
    blocked = impl_graph_amend(
        "frontier-graph", operations=[{"op": "update_pending_node", "node_id": "I002", "patch": {"title": "later"}}],
        actor="planner", reason="blocked amendment", workspace_root=workspace,
    )
    assert blocked["error"] == "amend_failed"


def test_state_progress_does_not_stale_structural_claim_view(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    assert "error" not in impl_graph_create(_frontier_graph("artifacts/requests/CTX_test.md", ["I001", "I002"]), workspace_root=workspace)
    state = json.loads((workspace / "artifacts/implementation/pending/frontier-graph/GRAPH.json").read_text())
    structure_revision = state["structure_revision"]
    structure_digest = graph_structure_digest(state)
    assert "error" not in impl_graph_claim(
        "frontier-graph", ["I002"], "packet-1", manager_session="session-1", write_scopes=["src/two/**"],
        expected_structure_revision=structure_revision, expected_structure_digest=structure_digest, workspace_root=workspace,
    )
    assert "error" not in impl_graph_claim(
        "frontier-graph", ["I001"], "packet-2", manager_session="session-2", write_scopes=["src/one/**"],
        expected_structure_revision=structure_revision, expected_structure_digest=structure_digest, workspace_root=workspace,
    )


def test_supersede_blocked_node_rewires_dependents(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    assert "error" not in impl_graph_create(graph(), workspace_root=workspace)
    assert "error" not in impl_graph_claim(
        "test-graph", ["I001"], "packet", manager_session="session", write_scopes=["src/**"], workspace_root=workspace,
    )
    assert "error" not in impl_graph_block("test-graph", ["I001"], "blocked", claim_id="packet", workspace_root=workspace)
    amended = impl_graph_amend(
        "test-graph", operations=[{
            "op": "supersede_blocked_node", "blocked_node_id": "I001",
            "replacement_node": {"id": "I003", "title": "replacement", "obligation": "Implement replacement", "depends_on": [], "satisfies": ["R1"], "acceptance": ["evidence"], "consumes": [], "produces": [], "context_hints": {}},
            "rewire_dependents": ["I002"], "rewire_contracts": [], "rewire_requirements": ["R1"],
        }], actor="planner", reason="recover blocked producer", workspace_root=workspace,
    )
    assert "error" not in amended
    state = json.loads((workspace / "artifacts/implementation/pending/test-graph/GRAPH.json").read_text())
    nodes = {node["id"]: node for node in state["nodes"]}
    assert nodes["I001"]["status"] == "SUPERSEDED"
    assert nodes["I002"]["depends_on"] == ["I003"]
    assert nodes["I003"]["status"] == "PENDING"
    assert unwrap(impl_graph_read("test-graph", "ready", workspace_root=workspace))["nodes"][0]["id"] == "I003"


def test_supersede_rejects_active_or_complete_targets(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    assert "error" not in impl_graph_create(_frontier_graph("artifacts/requests/CTX_test.md", ["I001"]), workspace_root=workspace)
    assert "error" not in impl_graph_claim("frontier-graph", ["I001"], "active", manager_session="session", write_scopes=["src/**"], workspace_root=workspace)
    active = impl_graph_amend("frontier-graph", operations=[{"op": "supersede_blocked_node", "blocked_node_id": "I001", "replacement_node": {"id": "I002", "obligation": "replacement"}, "rewire_dependents": [], "rewire_contracts": [], "rewire_requirements": []}], actor="planner", reason="invalid active", workspace_root=workspace)
    assert active["error"] == "amend_failed"


def test_add_node_preserves_semantic_fields_and_resets_runtime_fields(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = workspace / "artifacts/requests/CTX_test.md"
    request.parent.mkdir(parents=True)
    request.write_text("request", encoding="utf-8")
    assert "error" not in impl_graph_create(_frontier_graph("artifacts/requests/CTX_test.md", ["I001"]), workspace_root=workspace)
    semantic = {
        "id": "I002", "title": "Preserve title", "obligation": "Preserve obligation",
        "depends_on": ["I001"], "satisfies": ["R1"], "acceptance": ["contract"],
        "consumes": [], "produces": [], "context_hints": {"files": ["src/a.py"]},
        "status": "COMPLETE", "claim": {"id": "old"}, "evidence": ["old"],
        "provenance": ["old"], "changed_files": ["old.py"], "deviations": ["old"],
        "blocker": "old", "completion_result": {"old": True},
    }
    assert "error" not in impl_graph_amend(
        "frontier-graph", operations=[{"op": "add_node", "node": semantic}],
        actor="planner", reason="add semantic node", workspace_root=workspace,
    )
    state = json.loads((workspace / "artifacts/implementation/pending/frontier-graph/GRAPH.json").read_text())
    node = next(item for item in state["nodes"] if item["id"] == "I002")
    assert node["title"] == "Preserve title"
    assert node["obligation"] == "Preserve obligation"
    assert node["depends_on"] == ["I001"]
    assert node["context_hints"] == {"files": ["src/a.py"]}
    assert node["status"] == "PENDING" and node["claim"] is None
    assert node["evidence"] == [] and node["provenance"] == [] and node["changed_files"] == []
    assert node["deviations"] == [] and node["blocker"] is None and "completion_result" not in node


def test_workspace_fingerprint_distinguishes_symlink_from_regular_file(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    regular = workspace / "target.txt"
    regular.write_text("same", encoding="utf-8")
    first = workspace / "first.txt"
    first.write_text("same", encoding="utf-8")
    regular_fingerprint = workspace_fingerprint(workspace)
    first.unlink()
    first.symlink_to("target.txt")
    symlink_fingerprint = workspace_fingerprint(workspace)
    assert symlink_fingerprint != regular_fingerprint
