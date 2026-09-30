"""Contract tests for the bounded incomplete-DAG reviewer."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT = REPO_ROOT / "config/agents/incomplete-dag-reviewer.md"
REFERENCE = REPO_ROOT / "config/skills/dispatching-agents/references/incomplete-dag-reviewer.md"
DISPATCH = REPO_ROOT / "config/skills/dispatching-agents/SKILL.md"
ORCHESTRATE = REPO_ROOT / "config/commands/ecc/orchestrate.md"

MUTATION_OR_LIFECYCLE = (
    "edit", "write", "bash", "dag_create", "dag_add_requirement", "dag_add_create",
    "dag_add_edit", "dag_add_remove", "dag_add_move", "dag_add_run",
    "dag_update_requirement", "dag_update_create", "dag_update_edit",
    "dag_update_remove", "dag_update_move", "dag_update_run", "dag_remove",
    "dag_link_requirement", "dag_unlink_requirement", "dag_start", "dag_status",
    "dag_stop", "dag_archive", "dag_set_decomposition_only",
)


def _frontmatter() -> dict:
    return yaml.safe_load(AGENT.read_text(encoding="utf-8").split("---", 2)[1])


def test_agent_is_read_only_and_cannot_spawn_or_operate_dag():
    permissions = _frontmatter()["permission"]
    for tool in MUTATION_OR_LIFECYCLE:
        assert permissions.get(tool) == "deny", tool
    assert permissions["task"] == "deny"
    for tool in ("dag_show", "dag_preview", "dag_validate", "dag_read", "dag_grep", "dag_search"):
        assert permissions.get(tool) == "allow", tool


def test_contract_names_normal_incomplete_state_and_bounded_scope():
    text = AGENT.read_text(encoding="utf-8")
    assert "resolved=false" in text
    assert "executable=false" in text
    assert "normal incomplete construction state" in text
    assert "missing future or shallower work" in text
    assert "one bounded Change-DAG construction question" in text
    for category in ("EXACT_WORK_DEFECT", "SEMANTIC_DEFECT", "GRAPH_DEFECT", "AUTHORITY_ISSUE"):
        assert category in text
    assert "PASS | FINDINGS | BLOCKED" in text


def test_reference_defines_author_routing_and_non_mutating_boundary():
    text = REFERENCE.read_text(encoding="utf-8")
    assert "change-dag-semantic-repairer" in text
    assert "controller" in text
    assert "EXACT_WORK_FIXER" in text
    assert "SEMANTIC_REPAIRER" in text
    assert "EXACT_WORK_DEFECT" in text
    assert "AUTHORITY_ESCALATION" in text
    assert "Do not amend the DAG" in text
    assert "does not gate archival" in text


def test_dispatch_and_command_index_the_new_capability():
    assert "references/incomplete-dag-reviewer.md" in DISPATCH.read_text(encoding="utf-8")
    assert "incomplete-dag-reviewer" in ORCHESTRATE.read_text(encoding="utf-8")


def test_no_execution_or_spawn_language_is_authorized():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "never execute" in text
    assert "never spawn" in text
    assert "never mutate" in text
