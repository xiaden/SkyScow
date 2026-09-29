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


def test_author_task_map_is_worker_only():
    assert _task_map("change-dag-author") == {"*": "deny", "change-dag-worker": "allow"}
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
