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


def test_author_cannot_spawn_construction_agents():
    assert _task_map("change-dag-author") == {"*": "deny"}
    for child in ("change-dag-worker", "incomplete-dag-reviewer", "change-dag-fixer", "change-dag-semantic-repairer", "change-dag-reviewer", "nyx"):
        assert not _can_spawn("change-dag-author", child)


def test_author_cannot_repair_semantic_edges():
    for tool in ("dag_link_requirement", "dag_unlink_requirement"):
        assert not _allowed("change-dag-author", tool)


def test_author_only_has_initial_creation_tools():
    for tool in ("dag_create", "dag_show", "dag_preview", "dag_validate"):
        assert _allowed("change-dag-author", tool)
    for tool in ("dag_decomposition_frontier", "dag_link_requirement", "dag_unlink_requirement", "dag_add_requirement", "dag_add_edit", "dag_update_edit", "dag_remove"):
        assert not _allowed("change-dag-author", tool)


def test_author_boundary_prose():
    author = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
    reference = (REPO_ROOT / "config/skills/dispatching-agents/references/change-dag-author.md").read_text(encoding="utf-8")
    for text in (author, reference):
        assert "exactly one" in text
        assert "dag_create" in text
        assert "controller" in text.lower()
        assert "exit" in text.lower()
        assert "must not" in text
    for phrase in ("frontier", "worker", "reconciliation", "repair"):
        assert phrase in author.lower()  # explicit negative boundary remains documented
    assert "do not own frontier" in author


def test_scale_doctrine_is_present_on_decomposition_surfaces():
    skill = (REPO_ROOT / "config/skills/decomposing-design-documents/SKILL.md").read_text(encoding="utf-8")
    generation = (REPO_ROOT / "config/skills/decomposing-design-documents/references/semantic-generation.md").read_text(encoding="utf-8")
    assert "SCALE" in skill and "lossless" in skill
    assert "Broad implementation discovery is evidence to evaluate SCALE decomposition" in skill
    assert "SCALE decomposition must be lossless and exhaustive" in generation
    assert "A broad initial node is acceptable" in generation


def test_controller_owns_opaque_branch_admission():
    author = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
    worker = (AGENTS / "change-dag-worker.md").read_text(encoding="utf-8")
    dispatch = (REPO_ROOT / "config/skills/dispatching-agents/references/change-dag-author.md").read_text(encoding="utf-8")
    assert "branch_ref" not in author
    assert "branch_ref" not in dispatch
    assert "branch_ref" in worker
    assert "dag_worker_resolve" in worker
    assert "one Worker per returned semantic node" not in author
    assert "one Worker per returned semantic node" not in dispatch
