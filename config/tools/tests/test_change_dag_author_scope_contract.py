"""Contract tests for the Change-DAG-Author boundary."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "config" / "agents"


def _frontmatter(agent_name: str) -> dict:
    raw = (AGENTS / f"{agent_name}.md").read_text(encoding="utf-8")
    return yaml.safe_load(raw.split("---", 2)[1])


def _permission(agent_name: str) -> dict:
    permission = _frontmatter(agent_name).get("permission")
    assert isinstance(permission, dict)
    return permission


def _allowed(agent_name: str, tool: str) -> bool:
    permission = _permission(agent_name)
    return permission.get(tool, "deny") != "deny"


def _task_map(agent_name: str) -> dict:
    task = _permission(agent_name).get("task")
    assert isinstance(task, dict)
    return task


def _can_spawn(agent_name: str, child: str) -> bool:
    task = _task_map(agent_name)
    return task.get(child, task.get("*", "deny")) != "deny"


def test_author_task_map_allows_worker_optional_review_and_fixer():
    assert _task_map("change-dag-author") == {
        "*": "deny",
        "change-dag-worker": "allow",
        "incomplete-dag-reviewer": "allow",
        "change-dag-fixer": "allow",
    }
    for child in ("change-dag-semantic-researcher", "change-dag-file-researcher", "change-dag-reviewer", "nyx"):
        assert not _can_spawn("change-dag-author", child)


def test_link_unlink_are_author_only():
    for tool in ("dag_link_requirement", "dag_unlink_requirement"):
        assert _allowed("change-dag-author", tool)
        for agent in ("change-dag-worker", "nyx", "change-dag-reviewer"):
            assert not _allowed(agent, tool)


def test_author_does_not_get_semantic_read_tools():
    for tool in ("dag_semantic_search", "dag_semantic_context"):
        assert not _allowed("change-dag-author", tool)


def test_author_boundary_prose():
    author = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
    assert "optionally dispatch `incomplete-dag-reviewer`" in author
    assert "`change-dag-fixer`" in author
    assert "semantic/graph correction" in author
    assert "final/controller-level `Change-DAG-Reviewer`" in author
    assert "Initial semantic decomposition follows known correctness/causal structure" in author
    assert "must not attempt to pre-size every initial semantic node" in author
    for phrase in (
        "The initial semantic graph",
        "Causal relationships (`requires` edges)",
        "Global semantic reconciliation",
        "Cross-branch convergence",
        "Local exact lowering",
        "Scale decomposition beneath its assigned scope",
        "Selective dispatch of its two read-only researchers",
    ):
        assert phrase in author
    for signal in ("semantic gap", "duplicate ownership", "cross-branch relationship", "missing prerequisite"):
        assert signal in author
    assert "graph-reconciliation evidence" in author


def test_scale_doctrine_is_present_on_decomposition_surfaces():
    skill = (REPO_ROOT / "config/skills/decomposing-design-documents/SKILL.md").read_text(encoding="utf-8")
    generation = (REPO_ROOT / "config/skills/decomposing-design-documents/references/semantic-generation.md").read_text(encoding="utf-8")
    assert "SCALE" in skill and "lossless" in skill
    assert "Broad implementation discovery is evidence to evaluate SCALE decomposition" in skill
    assert "SCALE decomposition must be lossless and exhaustive" in generation
    assert "A broad initial node is acceptable" in generation


def test_author_dispatches_branch_capabilities_not_selected_nodes():
    author = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
    worker = (AGENTS / "change-dag-worker.md").read_text(encoding="utf-8")
    dispatch = (REPO_ROOT / "config/skills/dispatching-agents/references/change-dag-author.md").read_text(encoding="utf-8")
    for text in (author, dispatch):
        assert "branch_ref" in text
        assert "at most one" in text
        assert "branch" in text and "per" in text
        assert "dag_worker_resolve" in text
    assert "branch_ref" in worker
    assert "dag_worker_resolve(slug, branch_ref)" in worker
    assert "branch_ref" in worker and "service-assigned" in worker
    assert "one Worker per returned semantic node" not in author
    assert "one Worker per returned semantic node" not in dispatch
