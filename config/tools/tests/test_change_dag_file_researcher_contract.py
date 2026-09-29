"""Contract tests for the read-only repository file-researcher leaf."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT = REPO_ROOT / "config" / "agents" / "change-dag-file-researcher.md"
REFERENCE = (
    REPO_ROOT
    / "config"
    / "skills"
    / "dispatching-agents"
    / "references"
    / "change-dag-file-researcher.md"
)

FORBIDDEN_TOOLS = (
    "dag_show",
    "dag_preview",
    "dag_validate",
    "dag_decomposition_frontier",
    "dag_create",
    "dag_set_decomposition_only",
    "dag_semantic_search",
    "dag_semantic_context",
    "dag_add_requirement",
    "dag_add_create",
    "dag_add_edit",
    "dag_add_remove",
    "dag_add_move",
    "dag_add_run",
    "dag_update_requirement",
    "dag_update_create",
    "dag_update_edit",
    "dag_update_remove",
    "dag_update_move",
    "dag_update_run",
    "dag_remove",
    "dag_link_requirement",
    "dag_unlink_requirement",
    "dag_start",
    "dag_status",
    "dag_stop",
    "dag_archive",
)


def _frontmatter() -> dict:
    raw = AGENT.read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw.split("---", 2)[1])
    assert isinstance(parsed, dict)
    return parsed


def _permission() -> dict:
    permission = _frontmatter().get("permission")
    assert isinstance(permission, dict)
    return permission


def _allowed(permission: dict, tool: str) -> bool:
    return permission.get(tool, "deny") != "deny"


class TestFileResearcherContract:
    def test_agent_frontmatter_and_model(self):
        assert AGENT.is_file()
        frontmatter = _frontmatter()
        assert frontmatter["mode"] == "subagent"
        assert frontmatter["model"] == "omniroute/flash-combo"

    def test_agent_is_leaf(self):
        assert not _allowed(_permission(), "task")

    def test_agent_cannot_modify_anything(self):
        permission = _permission()
        for tool in ("edit", "write", "bash"):
            assert not _allowed(permission, tool)

    def test_agent_has_authoritative_projected_lens(self):
        permission = _permission()
        for tool in ("dag_read", "dag_grep", "dag_search", "dag_decomposition_scope"):
            assert _allowed(permission, tool), f"missing projected lens tool: {tool}"

    def test_forbidden_tools_are_denied(self):
        permission = _permission()
        for tool in FORBIDDEN_TOOLS:
            assert not _allowed(permission, tool), f"forbidden tool allowed: {tool}"

    def test_no_forbidden_tool_is_granted(self):
        permission = _permission()
        assert not any(_allowed(permission, tool) for tool in FORBIDDEN_TOOLS)


class TestAuthoritativeEvidenceContract:
    def test_body_states_locators_only(self):
        text = AGENT.read_text(encoding="utf-8")
        assert "candidate LOCATORS only" in text

    def test_body_requires_verification_against_projected_source(self):
        text = AGENT.read_text(encoding="utf-8")
        assert "verified against the node's DAG-projected source" in text
        assert "Never return a live-only claim as authoritative" in text

    def test_body_explains_live_only_insufficiency(self):
        text = AGENT.read_text(encoding="utf-8")
        assert "changed file contents" in text
        assert "created files, removed files, or moved files" in text


class TestOutputContract:
    def test_body_documents_output_keys(self):
        text = AGENT.read_text(encoding="utf-8")
        for key in (
            "answer",
            "required_surfaces",
            "related_surfaces",
            "relationships",
            "scope_assessment",
            "unresolved",
        ):
            assert key in text

    def test_body_forbids_patch_suggestions(self):
        text = AGENT.read_text(encoding="utf-8")
        assert "No patch suggestions" in text


class TestDispatchReferenceContract:
    def test_dispatch_reference_contract(self):
        assert REFERENCE.is_file()
        text = REFERENCE.read_text(encoding="utf-8")
        assert "FILE_QUERY" in text
        assert "question:" in text
        assert "Researchers never call each other." in text
