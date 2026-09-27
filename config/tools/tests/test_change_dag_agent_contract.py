"""Regression tests: Change DAG authority boundaries across shipped config.

Pins the settled architecture where there is no ``change-dag-runner`` agent:

    Nyx        -- owns orchestration and Change DAG lifecycle control
                  (``dag_start`` / ``dag_status`` / ``dag_stop`` / ``dag_archive``)
                  but never authors or mutates a DAG
    Author     -- owns DAG construction/amendment, never executes
    Reviewer   -- optional, read-only, bounded
    executor   -- deterministic runtime, unchanged

These tests read the shipped agent frontmatter and active routing prose
directly, so a future edit that re-adds a Runner route or leaks lifecycle
tools into the Author (or mutation tools into Nyx) fails loudly.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "config" / "agents"
SKILLS = REPO_ROOT / "config" / "skills"
COMMANDS = REPO_ROOT / "config" / "commands"

LIFECYCLE_TOOLS = ("dag_start", "dag_status", "dag_stop", "dag_archive")
MUTATION_TOOLS = (
    "dag_create",
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
)

RUNNER_STEMS = ("change-dag-runner", "Change-DAG-Runner")


def _permission(agent_name: str) -> dict:
    raw = (AGENTS / f"{agent_name}.md").read_text(encoding="utf-8")
    frontmatter = raw.split("---", 2)[1]
    data = yaml.safe_load(frontmatter)
    permission = data.get("permission")
    assert isinstance(permission, dict), f"{agent_name} has no permission block"
    return permission


def _allowed(permission: dict, tool: str) -> bool:
    return permission.get(tool, "deny") != "deny"


class TestNyxLifecycleAuthority:
    def test_nyx_owns_all_lifecycle_tools(self):
        permission = _permission("nyx")
        for tool in LIFECYCLE_TOOLS:
            assert _allowed(permission, tool), f"Nyx must own {tool}"

    def test_nyx_does_not_gain_dag_mutation_tools(self):
        permission = _permission("nyx")
        for tool in MUTATION_TOOLS:
            assert not _allowed(permission, tool), (
                f"Nyx must not own DAG mutation tool {tool}; "
                "authoring stays with Change-DAG-Author"
            )
        assert not _allowed(permission, "dag_preview")
        assert not _allowed(permission, "dag_validate")


class TestAuthorAuthority:
    def test_author_keeps_mutation_preview_validate(self):
        permission = _permission("change-dag-author")
        for tool in (*MUTATION_TOOLS, "dag_preview", "dag_validate"):
            assert _allowed(permission, tool), f"Author must keep {tool}"

    def test_author_cannot_execute(self):
        permission = _permission("change-dag-author")
        for tool in LIFECYCLE_TOOLS:
            assert not _allowed(permission, tool), f"Author must not own {tool}"


class TestReviewerAuthority:
    def test_reviewer_is_read_only(self):
        permission = _permission("change-dag-reviewer")
        for tool in ("edit", "write", "bash", "task"):
            assert not _allowed(permission, tool), f"Reviewer must not own {tool}"
        for tool in MUTATION_TOOLS:
            assert not _allowed(permission, tool), f"Reviewer must not own {tool}"
        for tool in LIFECYCLE_TOOLS:
            assert not _allowed(permission, tool), f"Reviewer must not own {tool}"

    def test_reviewer_can_inspect(self):
        permission = _permission("change-dag-reviewer")
        for tool in ("dag_show", "dag_preview", "dag_validate"):
            assert _allowed(permission, tool), f"Reviewer needs {tool}"


class TestRunnerRemoval:
    def test_runner_agent_file_removed(self):
        assert not (AGENTS / "change-dag-runner.md").exists()

    def test_runner_dispatch_reference_removed(self):
        reference = (
            SKILLS / "dispatching-agents" / "references" / "change-dag-runner.md"
        )
        assert not reference.exists()

    def test_no_active_runner_references(self):
        surfaces = [
            *sorted(AGENTS.glob("*.md")),
            *sorted(SKILLS.glob("*/SKILL.md")),
            *sorted(SKILLS.glob("*/references/*.md")),
            *sorted(COMMANDS.glob("*.md")),
            *sorted(COMMANDS.glob("**/*.md")),
            REPO_ROOT / "README.md",
            REPO_ROOT / "AGENTS.md",
        ]
        offenders: list[str] = []
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            for stem in RUNNER_STEMS:
                if stem in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {stem}")
        assert not offenders, "stale Change-DAG-Runner references: " + ", ".join(
            offenders
        )


class TestLifecycleDocumentation:
    def test_lifecycle_skill_shipped(self):
        skill = SKILLS / "change-dag-lifecycle" / "SKILL.md"
        assert skill.exists()
        frontmatter = skill.read_text(encoding="utf-8").split("---", 2)[1]
        data = yaml.safe_load(frontmatter)
        assert data["name"] == "change-dag-lifecycle"
        assert isinstance(data.get("description"), str) and data["description"].strip()

    def test_nyx_declares_lifecycle_boundary(self):
        text = (AGENTS / "nyx.md").read_text(encoding="utf-8")
        assert "Change DAG lifecycle" in text
        for tool in LIFECYCLE_TOOLS:
            assert tool in text

    def test_orchestrate_routes_lifecycle_through_nyx(self):
        text = (COMMANDS / "ecc" / "orchestrate.md").read_text(encoding="utf-8")
        assert "Nyx" in text
        assert "dag_start" in text
        for stem in RUNNER_STEMS:
            assert stem not in text

    def test_recovery_routes_to_author_then_lifecycle_retry(self):
        text = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
        assert "dag_start(retry=true)" in text
        assert "Change-DAG-Author" in text

    def test_qa_is_independent_and_never_reopens_completed_dag(self):
        nyx = (AGENTS / "nyx.md").read_text(encoding="utf-8")
        assert "never reopens a completed DAG" in nyx
        orchestrate = (COMMANDS / "ecc" / "orchestrate.md").read_text(encoding="utf-8")
        assert "never reopen" in orchestrate
