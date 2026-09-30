"""Contract tests for the bounded Change-DAG-Fixer capability."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT = REPO_ROOT / "config" / "agents" / "change-dag-fixer.md"
REFERENCE = (
    REPO_ROOT
    / "config"
    / "skills"
    / "dispatching-agents"
    / "references"
    / "change-dag-fixer.md"
)
DISPATCH = REPO_ROOT / "config" / "skills" / "dispatching-agents" / "SKILL.md"
ORCHESTRATE = REPO_ROOT / "config" / "commands" / "ecc" / "orchestrate.md"

LIFECYCLE = ("dag_start", "dag_status", "dag_stop", "dag_archive")
SEMANTIC_GRAPH = (
    "dag_create",
    "dag_add_requirement",
    "dag_update_requirement",
    "dag_link_requirement",
    "dag_unlink_requirement",
    "dag_set_decomposition_only",
)
TERMINAL_MUTATIONS = (
    "dag_update_create",
    "dag_update_edit",
    "dag_update_remove",
    "dag_update_move",
    "dag_update_run",
    "dag_remove",
)


def _frontmatter() -> dict:
    return yaml.safe_load(AGENT.read_text(encoding="utf-8").split("---", 2)[1])


def _permission() -> dict:
    permission = _frontmatter().get("permission")
    assert isinstance(permission, dict)
    return permission


def _allowed(tool: str) -> bool:
    return _permission().get(tool, "deny") != "deny"


def test_agent_and_reference_are_indexed():
    assert AGENT.is_file()
    assert REFERENCE.is_file()
    dispatch = DISPATCH.read_text(encoding="utf-8")
    assert "references/change-dag-fixer.md" in dispatch
    assert "change-dag-fixer" in ORCHESTRATE.read_text(encoding="utf-8")


def test_fixer_is_read_only_for_repository_and_cannot_spawn():
    for tool in ("read", "glob", "grep", "edit", "write", "bash", "task"):
        assert not _allowed(tool), f"fixer must not own {tool}"


def test_fixer_has_dag_lensed_reads_and_terminal_mutations_only():
    for tool in ("dag_read", "dag_grep", "dag_search", "dag_fixer_mutate"):
        assert _allowed(tool), f"fixer needs {tool}"
    for tool in (*SEMANTIC_GRAPH, *LIFECYCLE, *TERMINAL_MUTATIONS):
        assert not _allowed(tool), f"fixer must not own {tool}"


def test_contract_preserves_semantics_and_escalates_graph_changes():
    for path in (AGENT, REFERENCE):
        text = path.read_text(encoding="utf-8")
        assert "existing mutable terminal" in text
        assert "semantic intent" in text.lower()
        assert "requires" in text
        assert "change-dag-semantic-repairer" in text
        assert "controller" in text
        assert "DONE | BLOCKED" in text
        assert "review_triggers" in text
        assert "dag_update_edit" in text
        assert "dag_read" in text
        assert "unified diff" in text.lower()


def test_contract_excludes_lifecycle_and_agent_dispatch():
    text = AGENT.read_text(encoding="utf-8")
    for tool in LIFECYCLE:
        assert tool not in text.split("permission:", 1)[1].split("---", 1)[0]
    assert "no child-agent capability" in REFERENCE.read_text(encoding="utf-8")
