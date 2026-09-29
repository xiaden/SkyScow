"""Regression tests: Change-DAG-Worker selective research fan-out doctrine.

The Worker stays the orchestrator of its own reasoning and keeps ordinary local
discovery, but may now selectively delegate expensive exploration into disposable
child contexts:

    change-dag-worker -- may spawn ONLY --> change-dag-semantic-researcher
                                       \\-> change-dag-file-researcher

Both researchers are read-only leaves. Non-mandatory delegation, MEANING-vs-SCALE
semantic decomposition, and the projected-source requirement for the file
researcher are pinned here so a future edit cannot silently re-add broad semantic
exploration to the Worker or turn the researchers into a mandatory pipeline.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "config" / "agents"
SKILLS = REPO_ROOT / "config" / "skills"

WORKER = AGENTS / "change-dag-worker.md"
WORKER_REFERENCE = SKILLS / "dispatching-agents" / "references" / "change-dag-worker.md"
SEMANTIC_RESEARCHER = AGENTS / "change-dag-semantic-researcher.md"
FILE_RESEARCHER = AGENTS / "change-dag-file-researcher.md"

WORKER_CHILDREN = {
    "*": "deny",
    "change-dag-semantic-researcher": "allow",
    "change-dag-file-researcher": "allow",
}

LOCAL_DISCOVERY = (
    "dag_decomposition_scope",
    "dag_search",
    "dag_grep",
    "dag_read",
)

BROAD_SEMANTIC_EXPLORATION = ("dag_semantic_search", "dag_semantic_context")


def _frontmatter(agent_name: str) -> dict:
    raw = (AGENTS / f"{agent_name}.md").read_text(encoding="utf-8")
    return yaml.safe_load(raw.split("---", 2)[1])


def _permission(agent_name: str) -> dict:
    permission = _frontmatter(agent_name).get("permission")
    assert isinstance(permission, dict), f"{agent_name} has no permission block"
    return permission


def _allowed(permission: dict, tool: str) -> bool:
    return permission.get(tool, "deny") != "deny"


def _task_map(agent_name: str) -> dict:
    task = _permission(agent_name).get("task")
    assert isinstance(task, dict), f"{agent_name} must declare an explicit task map"
    return task


def _can_spawn(agent_name: str, child: str) -> bool:
    task = _task_map(agent_name)
    return task.get(child, task.get("*", "deny")) != "deny"


class TestWorkerFanOutPermissions:
    def test_worker_spawns_only_the_two_researchers(self):
        task = _task_map("change-dag-worker")
        assert task == WORKER_CHILDREN
        assert {key for key in task if key != "*"} == {
            "change-dag-semantic-researcher",
            "change-dag-file-researcher",
        }
        assert _can_spawn("change-dag-worker", "change-dag-semantic-researcher")
        assert _can_spawn("change-dag-worker", "change-dag-file-researcher")

    def test_worker_cannot_spawn_any_other_agent(self):
        for child in (
            "change-dag-reviewer",
            "change-dag-author",
            "change-dag-worker",
            "nyx",
            "support-researcher",
        ):
            assert not _can_spawn("change-dag-worker", child), (
                f"Worker must not spawn {child}"
            )
            assert child not in _task_map("change-dag-worker")

    def test_both_researchers_are_leaves(self):
        for agent in ("change-dag-semantic-researcher", "change-dag-file-researcher"):
            assert not _allowed(_permission(agent), "task"), (
                f"{agent} must not spawn any agent"
            )

    def test_worker_retains_local_discovery_but_not_broad_semantic_exploration(self):
        permission = _permission("change-dag-worker")
        for tool in LOCAL_DISCOVERY:
            assert _allowed(permission, tool), f"Worker must retain local discovery {tool}"
        for tool in BROAD_SEMANTIC_EXPLORATION:
            assert not _allowed(permission, tool), (
                f"Worker must not own broad semantic exploration tool {tool}; "
                "that is delegated to the semantic researcher"
            )


class TestWorkerFanOutDoctrine:
    def test_non_mandatory_delegation_rule(self):
        for path in (WORKER, WORKER_REFERENCE):
            text = path.read_text(encoding="utf-8")
            assert "Do not delegate merely because a child exists" in text, path

    def test_simple_expected_path_remains_valid(self):
        for path in (WORKER, WORKER_REFERENCE):
            text = path.read_text(encoding="utf-8")
            assert "scope" in text and "dag_search" in text, path
            assert "dag_read -> exact work" in text, path
            assert "explicitly valid and expected" in text, path

    def test_no_mandatory_researcher_pipeline(self):
        for path in (WORKER, WORKER_REFERENCE):
            text = path.read_text(encoding="utf-8")
            assert "optional query nodes" in text, path
            assert "not a pipeline" in text, path
            assert "never call each other" in text, path

    def test_scale_decomposition_semantics(self):
        for path in (WORKER, WORKER_REFERENCE):
            text = path.read_text(encoding="utf-8")
            assert "MEANING" in text, path
            assert "SCALE" in text, path
            assert "lossless/exhaustive" in text, path
            assert '"All API consumers use canonical lookup semantics."' in text, path
            assert '"Edit foo.py."' in text, path

    def test_meaning_and_scale_are_distinguished(self):
        text = WORKER.read_text(encoding="utf-8")
        assert "multiple distinct required states exist" in text
        assert "same postcondition spans too much implementation surface" in text

    def test_decision_cases_b_and_c_delegate_one_concrete_question(self):
        for path in (WORKER, WORKER_REFERENCE):
            text = path.read_text(encoding="utf-8")
            assert "change-dag-semantic-researcher" in text, path
            assert "change-dag-file-researcher" in text, path
            assert "ONE concrete question" in text, path


class TestFileResearcherProjectedSourceRequirement:
    def test_live_and_aft_and_ast_are_candidate_locators_only(self):
        text = FILE_RESEARCHER.read_text(encoding="utf-8")
        assert "candidate LOCATORS only" in text

    def test_material_findings_verified_against_projected_source(self):
        text = FILE_RESEARCHER.read_text(encoding="utf-8")
        assert "verified against the node's DAG-projected source" in text
