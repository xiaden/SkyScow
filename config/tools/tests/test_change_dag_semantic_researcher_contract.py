"""Contract tests for the read-only semantic researcher leaf."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT = REPO_ROOT / "config" / "agents" / "change-dag-semantic-researcher.md"
REFERENCE = (
    REPO_ROOT
    / "config"
    / "skills"
    / "dispatching-agents"
    / "references"
    / "change-dag-semantic-researcher.md"
)

FORBIDDEN_TOOLS = (
    "dag_show",
    "dag_preview",
    "dag_validate",
    "dag_read",
    "dag_grep",
    "dag_search",
    "dag_decomposition_scope",
    "dag_decomposition_frontier",
    "dag_create",
    "read",
    "grep",
    "glob",
    "aft_search",
    "aft_outline",
    "aft_zoom",
    "aft_inspect",
    "aft_conflicts",
    "ast_grep_search",
    "dag_add_requirement",
    "dag_link_requirement",
    "dag_unlink_requirement",
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
    "dag_set_decomposition_only",
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


class TestSemanticResearcherContract:
    def test_agent_frontmatter_and_leaf_status(self):
        assert AGENT.is_file()
        frontmatter = _frontmatter()
        assert frontmatter["mode"] == "subagent"
        assert not _allowed(_permission(), "task")

    def test_agent_cannot_modify_anything(self):
        permission = _permission()
        for tool in ("edit", "write", "bash"):
            assert not _allowed(permission, tool)

    def test_agent_has_only_semantic_dag_reads(self):
        permission = _permission()
        assert _allowed(permission, "dag_semantic_search")
        assert _allowed(permission, "dag_semantic_context")
        for tool in FORBIDDEN_TOOLS:
            assert not _allowed(permission, tool), f"forbidden tool allowed: {tool}"

    def test_forbidden_surface_excludes_terminal_detail(self):
        permission = _permission()
        assert not any(_allowed(permission, tool) for tool in FORBIDDEN_TOOLS)

    def test_body_documents_question_and_output_contract(self):
        text = AGENT.read_text(encoding="utf-8")
        assert "Does another semantic branch already own compatibility or verification semantics relevant to the adapter behavior found while lowering N83?" in text
        assert "Understand N83." in text
        for key in ("answer", "relevant_nodes", "relationships", "ambiguities"):
            assert key in text

    def test_body_states_no_spawn_or_mutation(self):
        text = AGENT.read_text(encoding="utf-8")
        assert "spawn another agent" in text
        assert "mutate the DAG" in text

    def test_dispatch_reference_contract(self):
        assert REFERENCE.is_file()
        text = REFERENCE.read_text(encoding="utf-8")
        assert "SEMANTIC_QUERY" in text
        assert "question:" in text
        assert "Researchers never call each other." in text
