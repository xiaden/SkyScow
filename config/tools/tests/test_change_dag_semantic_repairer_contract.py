"""Contract tests for the bounded Change-DAG semantic repairer."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT = REPO_ROOT / "config/agents/change-dag-semantic-repairer.md"
REFERENCE = REPO_ROOT / "config/skills/dispatching-agents/references/change-dag-semantic-repairer.md"

SEMANTIC_READS = (
    "dag_show",
    "dag_validate",
    "dag_decomposition_scope",
    "dag_semantic_context",
    "dag_semantic_search",
)
SEMANTIC_MUTATIONS = (
    "dag_add_requirement",
    "dag_update_requirement",
    "dag_link_requirement",
    "dag_unlink_requirement",
    "dag_set_decomposition_only",
)
TERMINAL_MUTATIONS = (
    "dag_add_create",
    "dag_add_edit",
    "dag_add_remove",
    "dag_add_move",
    "dag_add_run",
    "dag_update_create",
    "dag_update_edit",
    "dag_update_remove",
    "dag_update_move",
    "dag_update_run",
)
LIFECYCLE = ("dag_start", "dag_status", "dag_stop", "dag_archive")


def _frontmatter() -> dict:
    parsed = yaml.safe_load(AGENT.read_text(encoding="utf-8").split("---", 2)[1])
    assert isinstance(parsed, dict)
    return parsed


def _permission() -> dict:
    permission = _frontmatter().get("permission")
    assert isinstance(permission, dict)
    return permission


def _allowed(tool: str) -> bool:
    return _permission().get(tool, "deny") != "deny"


def test_agent_and_reference_exist_with_leaf_frontmatter():
    assert AGENT.is_file()
    assert REFERENCE.is_file()
    frontmatter = _frontmatter()
    assert frontmatter["mode"] == "subagent"
    assert frontmatter["description"]
    assert not _allowed("task")


def test_contract_grants_only_semantic_repair_resolver_for_repair_lifecycle():
    assert _allowed("dag_semantic_repair_resolve")
    assert not _allowed("dag_semantic_repair_start")


def test_contract_allows_bounded_semantic_reads_and_mutations_only():
    for tool in (*SEMANTIC_READS, *SEMANTIC_MUTATIONS):
        assert _allowed(tool), f"repairer needs {tool}"
    for tool in (*TERMINAL_MUTATIONS, *LIFECYCLE, "read", "glob", "grep", "edit", "write", "bash"):
        assert not _allowed(tool), f"repairer must not own {tool}"


def test_contract_is_opaque_checkpoint_bound_and_fail_closed():
    for path in (AGENT, REFERENCE):
        text = path.read_text(encoding="utf-8")
        assert "opaque" in text.lower()
        assert "checkpoint" in text.lower()
        assert "stale" in text.lower()
        assert "fail closed" in text.lower()
        assert "authoritative current DAG" in text
        assert "dag_validate" in text
        assert "DONE | BLOCKED" in text
        assert "REPAIRED | UNCHANGED | ESCALATED" in text


def test_contract_excludes_exact_work_lifecycle_and_agent_dispatch():
    text = AGENT.read_text(encoding="utf-8")
    reference = REFERENCE.read_text(encoding="utf-8")
    combined = f"{text}\n{reference}"
    assert "Independent semantic/graph findings route here" in text
    assert "not back to Change-DAG-Author" in combined
    assert "exact-work defects route to `change-dag-fixer`" in text
    assert "exact terminal work" in combined
    assert "never spawn" in combined.lower()
    assert "never invoke" in combined.lower()
    assert "terminal work" in combined.lower()
    assert "terminal removal is never permitted" not in combined.lower()
    assert "schema" in combined.lower()
    assert "BASE/SELF" in combined
    assert "changed_semantic_node_ids" in combined
    assert "escalation:" in combined
