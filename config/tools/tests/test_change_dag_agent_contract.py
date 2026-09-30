"""Regression tests: Change DAG authority boundaries across shipped config.

Pins the settled architecture where there is no ``change-dag-runner`` agent:

    Nyx        -- owns orchestration and Change DAG lifecycle control
                  (``dag_start`` / ``dag_status`` / ``dag_stop`` / ``dag_archive``)
                  but never authors or mutates a DAG, and never dispatches
                  node-level workers
    Author     -- performs one atomic initial semantic ``dag_create`` and hands
                   construction authority to the controller; never schedules or
                   repairs construction
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
    "dag_read",
    "dag_grep",
    "dag_search",
    "dag_decomposition_scope",
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
    "dag_set_decomposition_only",
)

# Tools the Worker must NOT own: whole-DAG structure/validation belongs to the
# Author, and the projected DAG lens replaces raw whole-repository inspection.
WORKER_DENIED_TOOLS = (
    "dag_show",
    "dag_preview",
    "dag_validate",
    "dag_semantic_search",
    "dag_semantic_context",
    "read",
    "grep",
    "glob",
    "aft_search",
    "aft_outline",
    "aft_zoom",
    "aft_inspect",
    "aft_conflicts",
    "ast_grep_search",
)

WORKER_SURFACES = (
    AGENTS / "change-dag-worker.md",
    SKILLS / "dispatching-agents" / "references" / "change-dag-worker.md",
)

RUNNER_STEMS = ("change-dag-runner", "Change-DAG-Runner")

# Wording from the pre-worker model where a single Author session was invoked
# once per frontier. None of it may survive in an active contract.
STALE_OWNERSHIP_PHRASES = (
    "one bounded invocation per frontier",
    "one fresh bounded Change-DAG-Author invocation per frontier",
    "fresh Change-DAG-Author invocation",
)

# Wording from the manual-frontier model where the Author computed depths itself
# and kept a processed-frontier registry. None of it may survive in an active
# surface: progress must come from the DAG service, never session memory.
STALE_FRONTIER_PHRASES = (
    "construction frontier",
    "construction-frontier",
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
    def test_nyx_owns_controller_construction_review_and_repair_tools(self):
        permission = _permission("nyx")
        for tool in ("dag_construction_state", "dag_construction_review", "dag_construction_start", "dag_semantic_repair_start", "dag_issue_repair_grant"):
            assert _allowed(permission, tool), f"Nyx must own {tool}"

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
        for researcher in (
            "change-dag-semantic-researcher",
            "change-dag-file-researcher",
        ):
            assert not _can_spawn("nyx", researcher), (
                f"Nyx must not dispatch {researcher}; the research children are "
                "internal to Change-DAG-Worker"
            )


class TestAuthorAuthority:
    def test_author_keeps_only_initial_creation_and_validation_tools(self):
        permission = _permission("change-dag-author")
        for tool in ("dag_create", "dag_show", "dag_preview", "dag_validate"):
            assert _allowed(permission, tool), f"Author needs {tool}"
        for tool in (*MUTATION_TOOLS[1:], "dag_decomposition_frontier"):
            assert not _allowed(permission, tool), f"Author must not own {tool}"

    def test_author_cannot_execute(self):
        permission = _permission("change-dag-author")
        for tool in LIFECYCLE_TOOLS:
            assert not _allowed(permission, tool), f"Author must not own {tool}"

    def test_author_cannot_edit_or_run_shell(self):
        permission = _permission("change-dag-author")
        for tool in ("edit", "write", "bash"):
            assert not _allowed(permission, tool), f"Author must not own {tool}"

    def test_author_cannot_spawn_or_route_construction_agents(self):
        assert _task_map("change-dag-author") == {"*": "deny"}
        for child in ("change-dag-worker", "incomplete-dag-reviewer", "change-dag-fixer", "change-dag-semantic-repairer"):
            assert not _can_spawn("change-dag-author", child)

    def test_author_exits_after_controller_handoff(self):
        text = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
        assert "exactly one initial semantic construction" in text
        assert "After successful creation and handoff, you exit" in text
        assert "controller" in text.lower()
        assert "do not own frontier" in text

    def test_author_handoff_names_controller_routes(self):
        combined = "\n".join([
            (AGENTS / "change-dag-author.md").read_text(encoding="utf-8"),
            (SKILLS / "dispatching-agents" / "references" / "change-dag-author.md").read_text(encoding="utf-8"),
        ])
        for phrase in ("exact-work routing", "semantic/graph routing", "authority issues", "final `dag_validate`"):
            assert phrase in combined

    def test_author_contract_does_not_reintroduce_worker_or_repair_doctrine(self):
        author = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
        for phrase in ("frontier loop", "reconcile worker"):
            assert phrase not in author


class TestWorkerAuthority:
    def test_worker_agent_file_exists(self):
        assert (AGENTS / "change-dag-worker.md").exists()

    def test_worker_spawns_only_the_two_researchers(self):
        permission = _permission("change-dag-worker")
        assert _task_map("change-dag-worker") == {
            "*": "deny",
            "change-dag-semantic-researcher": "allow",
            "change-dag-file-researcher": "allow",
        }, "Worker may spawn only its two read-only researchers"
        for tool in ("edit", "write", "bash"):
            assert not _allowed(permission, tool), f"Worker must not own {tool}"

    def test_worker_cannot_create_or_operate_lifecycle(self):
        permission = _permission("change-dag-worker")
        assert not _allowed(permission, "dag_create")
        for tool in LIFECYCLE_TOOLS:
            assert not _allowed(permission, tool), f"Worker must not own {tool}"

    def test_worker_has_bounded_authoring_permissions(self):
        permission = _permission("change-dag-worker")
        for tool in (*WORKER_TOOLS, "dag_worker_resolve"):
            assert _allowed(permission, tool), f"Worker needs {tool}"

    def test_worker_has_dag_read_lens_and_lacks_raw_or_whole_dag_tools(self):
        permission = _permission("change-dag-worker")
        for tool in ("dag_read", "dag_grep", "dag_search", "dag_decomposition_scope"):
            assert _allowed(permission, tool), f"Worker needs DAG read lens {tool}"
        for tool in WORKER_DENIED_TOOLS:
            assert not _allowed(permission, tool), f"Worker must not own {tool}"
        for path in WORKER_SURFACES:
            text = path.read_text(encoding="utf-8")
            assert "dag_read" in text and "dag_grep" in text and "dag_search" in text

    def test_worker_cannot_whole_dag_inspect_through_dag_show(self):
        permission = _permission("change-dag-worker")
        assert not _allowed(permission, "dag_show"), "Worker must not whole-DAG inspect"
        assert not _allowed(permission, "dag_validate")
        assert not _allowed(permission, "dag_preview")

    def test_worker_contract_requires_self_verification_through_dag_read(self):
        agent = (AGENTS / "change-dag-worker.md").read_text(encoding="utf-8")
        assert "self-verification is re-reading your own projected work through `dag_read`" in agent
        reference = (
            SKILLS / "dispatching-agents" / "references" / "change-dag-worker.md"
        ).read_text(encoding="utf-8")
        assert "Self-verify by re-reading your own projected result with `dag_read`" in reference
        assert "never through `dag_validate`" in reference

    def test_worker_contract_is_new_work_only(self):
        for path in WORKER_SURFACES:
            text = path.read_text(encoding="utf-8")
            assert "NEW WORK ONLY" in text or "new-work lowering only" in text
            assert "RECONCILE" not in text
            assert "RECONCILED" not in text
            assert "Change-DAG-Fixer" in text

    def test_worker_contract_describes_exclusive_terminals(self):
        for path in WORKER_SURFACES:
            text = path.read_text(encoding="utf-8")
            assert "composable" in text, path
            assert "exclusive" in text, path

    def test_worker_contract_never_instructs_hand_authored_unified_diff(self):
        for path in WORKER_SURFACES:
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            assert "replacements" in text, path
            assert "unified diff" in lowered, path
            assert "not write unified diff" in lowered or "never unified diff syntax" in lowered, path
            assert "*** Begin Patch" in text, path

    def test_lowered_wording_describes_authoring_not_runtime(self):
        # Adding exact work resolves the node's authoring obligation; runtime
        # execution is what satisfies it. Pin both active worker surfaces.
        surfaces = (
            AGENTS / "change-dag-worker.md",
            SKILLS / "dispatching-agents" / "references" / "change-dag-worker.md",
        )
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            assert "locally resolves the assigned node's authoring obligation" in text
            assert "satisfies the assigned requirement" not in text


class TestDecompositionOnlyAuthority:
    def test_worker_alone_may_set_decomposition_only(self):
        assert (
            _permission("change-dag-worker").get("dag_set_decomposition_only") == "allow"
        )

    def test_setter_explicitly_denied_to_author_nyx_and_reviewer(self):
        for agent in ("change-dag-author", "nyx", "change-dag-reviewer"):
            assert (
                _permission(agent).get("dag_set_decomposition_only") == "deny"
            ), f"{agent} must explicitly deny dag_set_decomposition_only"


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
        assert not _can_spawn("change-dag-worker", "change-dag-reviewer")
        assert "change-dag-reviewer" not in _task_map("change-dag-worker")

    def test_final_reviewer_is_completed_dag_safe_to_run_contract(self):
        text = (AGENTS / "change-dag-reviewer.md").read_text(encoding="utf-8")
        reference = (
            SKILLS / "dispatching-agents" / "references" / "change-dag-reviewer.md"
        ).read_text(encoding="utf-8")
        for surface in (text, reference):
            assert "completed" in surface.lower()
            assert "resolved=true" in surface
            assert "executable=true" in surface
            assert "BLOCK_RUN" in surface
            assert "ALLOW_WITH_FOLLOWUP" in surface
            assert "ALLOW" in surface
            assert "execution consequence" in surface.lower()
            assert "route" in surface.lower()
            assert "perfection gate" in surface.lower()

    def test_final_reviewer_does_not_make_ordinary_defects_automatic_blocks(self):
        text = (AGENTS / "change-dag-reviewer.md").read_text(encoding="utf-8")
        assert "safely repairable against the real repository after execution" in text
        assert "Do not turn an ordinary correctness defect" in text
        assert "invalid lower assumptions/dependency" in text
        assert "dangerous destructive/irreversible behavior" in text
        assert "materially worsening safety/repairability" in text

    def test_final_reviewer_preserves_external_read_only_boundary(self):
        text = (AGENTS / "change-dag-reviewer.md").read_text(encoding="utf-8")
        reference = (
            SKILLS / "dispatching-agents" / "references" / "change-dag-reviewer.md"
        ).read_text(encoding="utf-8")
        for surface in (text, reference):
            assert "Nyx" in surface
            assert "independent" in surface
            assert (
                "never spawns" in surface
                or "never spawn" in surface
                or "no spawning" in surface
            )
            assert "never write" in surface.lower() or "never stored" in surface.lower()
            assert "gate archival" in surface


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
        assert "never spawns another worker" in text or "never call each other" in text or "Do not dispatch any agent other than" in text

    def test_dispatching_skill_routes_through_controller(self):
        text = (SKILLS / "dispatching-agents" / "SKILL.md").read_text(encoding="utf-8")
        assert "change-dag-worker" in text
        assert "controller" in text.lower()
        assert "dispatched only by the controller" in text

    def test_author_contract_names_controller_handoff(self):
        text = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
        assert "controller" in text.lower()
        assert "handoff" in text
        assert "do not own frontier" in text

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

    def test_recovery_routes_to_controller_then_nyx_lifecycle_retry(self):
        author = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
        nyx = (AGENTS / "nyx.md").read_text(encoding="utf-8")
        assert "recovery" in author.lower()
        assert "dag_start" in nyx
        assert "retry" in nyx.lower()

    def test_qa_is_independent_and_never_reopens_completed_dag(self):
        nyx = (AGENTS / "nyx.md").read_text(encoding="utf-8")
        assert "never reopens a completed DAG" in nyx
        orchestrate = (COMMANDS / "ecc" / "orchestrate.md").read_text(encoding="utf-8")
        assert "never reopen" in orchestrate


class TestServiceDerivedDecomposition:
    """Pins the service-derived decomposition model across active surfaces.

    Progress comes from ``dag_decomposition_frontier`` (which reports a resolved
    frontier) and per-node scope comes from ``dag_decomposition_scope``. The
    Author must not hand-compute depths or keep a processed-frontier registry,
    and the dispatch contract must not copy semantic packets into the child.
    """

    def test_controller_owns_frontier_derivation(self):
        author = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
        plugin = (REPO_ROOT / "config" / "plugins" / "tools.ts").read_text(encoding="utf-8")
        assert "dag_decomposition_frontier" not in author
        assert "dag_decomposition_frontier:" not in plugin
        assert "controller" in author.lower()
        assert "deepest-frontier" in author

    def test_worker_retrieves_its_own_scope(self):
        text = (AGENTS / "change-dag-worker.md").read_text(encoding="utf-8")
        assert "dag_decomposition_scope" in text

    def test_worker_dispatch_reference_retrieves_scope(self):
        text = (
            SKILLS / "dispatching-agents" / "references" / "change-dag-worker.md"
        ).read_text(encoding="utf-8")
        assert "dag_decomposition_scope" in text

    def test_no_copied_semantic_packet_fields(self):
        paths = (
            AGENTS / "change-dag-author.md",
            AGENTS / "change-dag-worker.md",
            SKILLS / "dispatching-agents" / "references" / "change-dag-author.md",
            SKILLS / "dispatching-agents" / "references" / "change-dag-worker.md",
        )
        offenders: list[str] = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for field in ("semantic_scope:", "ancestor_intent:", "NO_DIRECT_WORK"):
                if field in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {field}")
        assert not offenders, "stale copied semantic packet fields: " + ", ".join(
            offenders
        )

    def test_no_manual_construction_frontier_wording(self):
        offenders: list[str] = []
        for path in _documented_surfaces():
            text = path.read_text(encoding="utf-8")
            for phrase in STALE_FRONTIER_PHRASES:
                if phrase in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {phrase}")
        assert not offenders, "stale manual-frontier wording: " + ", ".join(offenders)

    def test_run_sibling_rule_is_explicit(self):
        text = (AGENTS / "change-dag-author.md").read_text(encoding="utf-8")
        assert "no `create`/`edit`/`remove`/`move` siblings" in text
