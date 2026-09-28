"""Contract tests: Nyx delegates routing ownership to ``work-routing``.

Nyx is the stable top-level controller. It owns orchestration and return
transitions, the request-context capture operation, Change DAG lifecycle control,
and global completion/evidence constraints. It is *not* the routing manual:
owner-selection policy is defined once, in
``config/skills/work-routing/SKILL.md``.

These tests fail loudly if Nyx regrows a local copy of the routing doctrine — a
second Direct-Work policy, the Change DAG size formula, Researcher/Librarian
selection rules, or the R&D route-return decision table.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
NYX = "config/agents/nyx.md"
WORK_ROUTING = "config/skills/work-routing/SKILL.md"


def _raw(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _norm(relative: str) -> str:
    return " ".join(_raw(relative).split())


class TestNyxBindsToWorkRouting:
    def test_nyx_requires_work_routing_before_owner_selection(self):
        text = _norm(NYX)
        assert (
            "Before selecting ownership for implementation, investigation, design, "
            "decomposition, or QA work" in text
        )
        assert (
            "load the `work-routing` skill and follow it as the canonical "
            "owner-selection policy" in text
        )

    def test_nyx_names_work_routing_as_single_authority(self):
        text = _norm(NYX)
        assert "single authority" in text
        assert "does not duplicate routing rules locally" in text

    def test_work_routing_is_the_canonical_owner_selection_policy(self):
        text = _norm(WORK_ROUTING)
        assert "canonical authority for routing ownership" in text
        assert "who owns the next meaningful unit of work" in text

    def test_nyx_defers_dispatch_construction_to_dispatching_agents(self):
        text = _norm(NYX)
        assert "dispatching-agents" in text


class TestNyxHasNoSecondDirectWorkPolicy:
    def test_direct_work_policy_block_is_gone(self):
        text = _raw(NYX)
        assert "Direct-Work Invariant" not in text
        assert "MECHANICAL work and genuinely bounded STANDARD work stay" not in text
        assert "no specialist row is matched" not in text

    def test_direct_work_conditions_are_not_restated(self):
        text = _norm(NYX)
        assert "the requested behavior is clear" not in text
        assert (
            "the implementation surface is already known, or bounded localization "
            "can establish it" not in text
        )
        assert "no architectural or design decision is required" not in text

    def test_task_tier_definitions_are_not_duplicated(self):
        text = _raw(NYX)
        assert "**MECHANICAL** (typo fixes, formatting" not in text
        assert "**STANDARD** (bug fixes, single-module features" not in text
        assert "**ARCHITECTURAL** (new patterns, cross-module features" not in text


class TestNyxHasNoChangeDagThresholdFormula:
    def test_weighted_context_formula_is_gone(self):
        text = _raw(NYX)
        assert "weighted_chars" not in text
        assert "0.03" not in text
        assert "0.015" not in text

    def test_threshold_bands_are_gone(self):
        text = _norm(NYX)
        assert "< 32K (TRIVIAL or SMALL)" not in text
        assert "≥ 32K (MEDIUM)" not in text
        assert "≥ 80K (LARGE)" not in text


class TestNyxDoesNotSelectResearcherOrLibrarian:
    def test_researcher_selection_rules_are_gone(self):
        text = _norm(NYX)
        assert "Support-Researcher" not in text
        assert "deep multi-file dependency tracing" not in text
        assert (
            "Support-Researcher only when unresolved substantive investigation remains"
            not in text
        )

    def test_librarian_route_rule_is_gone(self):
        text = _norm(NYX)
        assert (
            "Prior process artifacts (logs, dead ends, prior DDs) materially "
            "constrain the route" not in text
        )
        assert "Support-Librarian" not in text

    def test_researcher_scope_signal_table_is_gone(self):
        text = _norm(NYX)
        assert "BROADER_SAME_REQUIREMENT" not in text
        assert "Researcher Scope Signal" not in text
        assert "scope_signal" not in text


class TestNyxDoesNotOwnRndRouteDecisionTable:
    def test_route_return_tuple_table_is_gone(self):
        text = _norm(NYX)
        assert "`route: DAG_ONLY`, `status: DONE`, `phase: READY_FOR_AUTHORING`" not in text
        assert "`route: DD_REQUIRED`, `status: DONE`, `phase: READY_FOR_AUTHORING`" not in text
        assert "Consume exactly the `route`" not in text

    def test_pre_rnd_obligations_block_is_gone(self):
        assert "Pre-R&D Responsibility" not in _raw(NYX)

    def test_delegation_checklist_is_gone(self):
        text = _raw(NYX)
        assert "Delegation Checklist" not in text
        assert "### START HERE" not in text


class TestNyxStillOwnsRequestContextCapture:
    def test_capture_operation_is_owned_by_nyx(self):
        text = _norm(NYX)
        assert "capture_request_context" in text
        assert "request_context" in text
        assert "artifacts/requests/CTX_*.md" in text

    def test_nyx_states_it_owns_the_capture_operation(self):
        text = _norm(NYX)
        assert "Nyx owns the capture operation" in text

    def test_capture_precedes_authoring_dispatches(self):
        text = _norm(NYX)
        assert "Before dispatching `RnD-Manager`" in text
        assert "`Change-DAG-Author` for Change DAG creation or amendment" in text


class TestNyxStillOwnsChangeDagLifecycle:
    def test_lifecycle_tools_are_owned(self):
        text = _raw(NYX)
        for tool in ("dag_start", "dag_status", "dag_stop", "dag_archive"):
            assert tool in text, f"Nyx must retain {tool} lifecycle ownership"

    def test_lifecycle_skill_is_the_procedure_owner(self):
        text = _norm(NYX)
        assert "loads the `change-dag-lifecycle` skill before operating them" in text
        assert "the detailed lifecycle procedure lives there" in text

    def test_qa_never_reopens_a_completed_dag(self):
        assert "never reopens a completed DAG" in _raw(NYX)
