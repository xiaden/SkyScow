"""Regression tests: Change DAG authority boundaries across shipped config.

Pins the settled architecture where there is no ``change-dag-runner`` agent:

    Nyx        -- owns orchestration and Change DAG lifecycle control
                  (``dag_start`` / ``dag_status`` / ``dag_stop`` / ``dag_archive``)
                  but never authors or mutates a DAG, and never dispatches
                  node-level workers
    Author     -- construction manager: owns DAG construction/amendment and the
                  construction-frontier loop; dispatches only Change-DAG-Worker;
                  never executes
    Worker     -- bounded leaf: lowers exactly one assigned semantic node, never
                  mutates source, never executes, never spawns agents
    Reviewer   -- optional, read-only, bounded; Nyx-selected only
    executor   -- deterministic runtime, unchanged

These tests read the shipped agent frontmatter and active routing prose
directly, so a future edit that re-adds a Runner route, leaks lifecycle tools
into the Author (or mutation tools into Nyx), or dissolves the manager/worker
split fails loudly.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "config" / "agents"
SKILLS = REPO_ROOT / "config" / "skills"
COMMANDS = REPO_ROOT / "config" / "commands"
DOCS = REPO_ROOT / "docs"

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
WORKER_TOOLS = (
    "dag_show",
    "dag_preview",
    "dag_validate",
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

# Wording from the pre-worker model where a single Author session was invoked
# once per frontier. None of it may survive in an active contract.
STALE_OWNERSHIP_PHRASES = (
    "one bounded invocation per frontier",
    "one fresh bounded Change-DAG-Author invocation per frontier",
    "fresh Change-DAG-Author invocation",
)


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


def _active_surfaces() -> list[Path]:
    return [
        *sorted(AGENTS.glob("*.md")),
        *sorted(SKILLS.glob("*/SKILL.md")),
        *sorted(SKILLS.glob("*/references/*.md")),
        *sorted(COMMANDS.glob("*.md")),
        *sorted(COMMANDS.glob("**/*.md")),
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
    ]


def _documented_surfaces() -> list[Path]:
    return [*_active_surfaces(), *sorted(DOCS.glob("**/*.md"))]


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

    def test_nyx_does_not_dispatch_node_workers(self):
        assert _can_spawn("nyx", "change-dag-author")
        assert _can_spawn("nyx", "change-dag-reviewer")
        assert not _can_spawn("nyx", "change-dag-worker"), (
            "Nyx must not dispatch Change-DAG-Worker directly; worker dispatch is "
            "internal to Change-DAG-Author"
        )


class TestAuthorAuthority:
    def test_author_keeps_mutation_preview_validate(self):
        permission = _permission("change-dag-author")
        for tool in (*MUTATION_TOOLS, "dag_preview", "dag_validate"):
            assert _allowed(permission, tool), f"Author must keep {tool}"

    def test_author_cannot_execute(self):
        permission = _permission("change-dag-author")
        for tool in LIFECYCLE_TOOLS:
            assert not _allowed(permission, tool), f"Author must not own {tool}"

    def test_author_cannot_edit_or_run_shell(self):
        permission = _permission("change-dag-author")
        for tool in ("edit", "write", "bash"):
            assert not _allowed(permission, tool), f"Author must not own {tool}"

    def test_author_spawns_only_workers(self):
        assert _can_spawn("change-dag-author", "change-dag-worker")
        assert not _can_spawn("change-dag-author", "change-dag-reviewer")
        specific = {key for key in _task_map("change-dag-author") if key != "*"}
        assert specific == {"change-dag-worker"}, specific


class TestWorkerAuthority:
    def test_worker_agent_file_exists(self):
        assert (AGENTS / "change-dag-worker.md").exists()

    def test_worker_is_a_leaf(self):
        permission = _permission("change-dag-worker")
        assert not _allowed(permission, "task"), "Worker must not spawn other agents"
        for tool in ("edit", "write", "bash"):
            assert not _allowed(permission, tool), f"Worker must not own {tool}"

    def test_worker_cannot_create_or_operate_lifecycle(self):
        permission = _permission("change-dag-worker")
        assert not _allowed(permission, "dag_create")
        for tool in LIFECYCLE_TOOLS:
            assert not _allowed(permission, tool), f"Worker must not own {tool}"

    def test_worker_has_bounded_authoring_permissions(self):
        permission = _permission("change-dag-worker")
        for tool in WORKER_TOOLS:
            assert _allowed(permission, tool), f"Worker needs {tool}"


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

    def test_reviewer_not_spawnable_by_author_or_worker(self):
        assert not _can_spawn("change-dag-author", "change-dag-reviewer")
        assert not _allowed(_permission("change-dag-worker"), "task")


class TestRunnerRemoval:
    def test_runner_agent_file_removed(self):
        assert not (AGENTS / "change-dag-runner.md").exists()

    def test_runner_dispatch_reference_removed(self):
        reference = (
            SKILLS / "dispatching-agents" / "references" / "change-dag-runner.md"
        )
        assert not reference.exists()

    def test_no_active_runner_references(self):
        offenders: list[str] = []
        for path in _active_surfaces():
            text = path.read_text(encoding="utf-8")
            for stem in RUNNER_STEMS:
                if stem in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {stem}")
        assert not offenders, "stale Change-DAG-Runner references: " + ", ".join(
            offenders
        )


class TestManagerWorkerRouting:
    def test_worker_dispatch_reference_shipped(self):
        reference = (
            SKILLS / "dispatching-agents" / "references" / "change-dag-worker.md"
        )
        assert reference.exists()
        text = reference.read_text(encoding="utf-8")
        assert "one assigned semantic node" in text
        assert "never spawns another worker" in text

    def test_dispatching_skill_routes_through_author(self):
        text = (SKILLS / "dispatching-agents" / "SKILL.md").read_text(encoding="utf-8")
        assert "change-dag-worker" in text
        assert "Nyx never dispatches Change-DAG-Worker directly" in text

    def test_author_contract_names_worker_and_review_trigger(self):
        text = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
        assert "change-dag-worker" in text
        assert "review_trigger" in text

    def test_no_stale_single_session_frontier_wording(self):
        offenders: list[str] = []
        for path in _documented_surfaces():
            text = path.read_text(encoding="utf-8")
            for phrase in STALE_OWNERSHIP_PHRASES:
                if phrase in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {phrase}")
        assert not offenders, "stale single-session authoring wording: " + ", ".join(
            offenders
        )

    def test_nyx_and_author_reference_drop_semantic_scope_input(self):
        assert "semantic_scope" not in (AGENTS / "nyx.md").read_text(encoding="utf-8")
        author_ref = (
            SKILLS / "dispatching-agents" / "references" / "change-dag-author.md"
        ).read_text(encoding="utf-8")
        assert "semantic_scope" not in author_ref


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

    def test_orchestrate_mentions_worker(self):
        text = (COMMANDS / "ecc" / "orchestrate.md").read_text(encoding="utf-8")
        assert "change-dag-worker" in text

    def test_recovery_routes_to_author_then_lifecycle_retry(self):
        text = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
        assert "dag_start(retry=true)" in text
        assert "Change-DAG-Author" in text

    def test_qa_is_independent_and_never_reopens_completed_dag(self):
        nyx = (AGENTS / "nyx.md").read_text(encoding="utf-8")
        assert "never reopens a completed DAG" in nyx
        orchestrate = (COMMANDS / "ecc" / "orchestrate.md").read_text(encoding="utf-8")
        assert "never reopen" in orchestrate
