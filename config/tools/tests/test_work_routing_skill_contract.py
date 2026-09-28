"""Contract tests: the canonical ``work-routing`` skill.

``config/skills/work-routing/SKILL.md`` is the single canonical authority for *who
owns the next meaningful unit of work*. Routing policy now lives only here;
``config/agents/nyx.md`` and ``config/skills/dispatching-agents/SKILL.md`` were
cleaned of the duplicated policy and defer to this skill.

These tests fail loudly if this skill drops or reinterprets a canonical routing
concept, or if the routing authority drifts.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = "config/skills/work-routing/SKILL.md"


def _raw() -> str:
    return (REPO_ROOT / SKILL_PATH).read_text(encoding="utf-8")


def _norm() -> str:
    return " ".join(_raw().split())


class TestFrontmatter:
    def test_name_matches_directory(self):
        frontmatter = yaml.safe_load(_raw().split("---", 2)[1])
        assert frontmatter["name"] == "work-routing"

    def test_description_is_present_and_states_the_trigger(self):
        frontmatter = yaml.safe_load(_raw().split("---", 2)[1])
        description = frontmatter.get("description")
        assert isinstance(description, str) and description.strip()
        # Discovery signal must say when to load the skill.
        assert "who owns the next unit of work" in description
        assert "before choosing execution" in description


class TestSkillResponsibilityBoundary:
    """The skill answers ownership; it does not own dispatch/DD/DAG/QA internals."""

    def test_states_the_one_question_it_answers(self):
        assert "who owns the next meaningful unit of work" in _norm()

    def test_states_what_it_does_not_define(self):
        text = _norm()
        assert "how to construct a native `task` prompt" in text
        assert "agent-specific handoff schemas" in text
        assert "Change DAG tool operation" in text
        assert "Design Document internals" in text
        assert "QA implementation detail or Git/GitHub mechanics" in text

    def test_routing_selects_the_owner_but_does_not_build_the_dispatch(self):
        assert "Routing selects the owner" in _norm()


class TestDirectWorkInvariant:
    def test_mechanical_and_bounded_standard_stay_direct(self):
        text = _norm()
        assert "MECHANICAL work and genuinely bounded STANDARD work stay" in text

    def test_direct_work_conditions_are_named(self):
        text = _norm()
        assert "the requested behavior is clear" in text
        assert "the implementation surface is already known, or bounded localization can establish it" in text
        assert "no architectural or design decision is required" in text
        assert "no specialist-owned investigation is actually necessary" in text

    def test_direct_capable_examples_are_present(self):
        text = _norm()
        assert "one-line configuration correction" in text
        assert "known single-file edit" in text

    def test_direct_work_precedes_specialist_rows(self):
        text = _norm()
        assert "no specialist row is matched" in text
        assert "A first-match specialist row never overrides this invariant" in text
        assert "no row below applies" in text

    def test_session_history_is_not_a_routing_input(self):
        text = _norm()
        assert "Session history is not a routing input" in text
        assert "was not edited previously" in text

    def test_architectural_novelty_is_never_downgraded_by_known_locations(self):
        text = _norm()
        assert "Known edit locations are a discovery input, not a scope downgrade" in text
        assert "even when the exact files and functions are already named" in text
        assert "may still return `DAG_ONLY`" in text


class TestBoundedLocalization:
    def test_localization_answers_the_four_questions(self):
        text = _norm()
        assert "where does the requested behavior live?" in text
        assert "is this still one bounded local change?" in text
        assert "does it cross enough implementation surface to justify Change-DAG-Author?" in text
        assert "does it reveal architectural/design uncertainty requiring R&D evaluation?" in text

    def test_localization_is_bounded_not_a_scan(self):
        text = _norm()
        assert "It is not broad implementation exploration" in text
        assert "a repository-wide scan is a routing failure" in text

    def test_large_surface_and_design_uncertainty_route_away(self):
        text = _norm()
        assert "If it reveals a large implementation surface, route to Change-DAG-Author" in text
        assert "if it reveals design uncertainty, route to RnD-Manager" in text


class TestChangeDagThreshold:
    def test_weighted_context_formula_is_preserved(self):
        assert (
            "weighted_chars = char_count × (1 + 0.03 × (sections - 1) + 0.015 × max(files - 1, 0))"
            in _norm()
        )

    def test_threshold_bands_are_preserved(self):
        text = _norm()
        assert "< 32K (TRIVIAL or SMALL)" in text
        assert "≥ 32K (MEDIUM)" in text
        assert "≥ 80K (LARGE)" in text

    def test_small_work_stays_direct_large_work_routes_to_author_or_rnd(self):
        text = _norm()
        assert "Edit directly — the Direct-Work Invariant applies" in text
        assert "Change-DAG-Author authors the Change DAG" in text
        assert "Route to RnD-Manager for evidence-based R&D evaluation" in text

    def test_estimator_inputs_are_never_fabricated(self):
        text = _norm()
        assert "never fabricate estimator inputs" in text
        assert "do not invent char/section/file counts" in text
        assert "do not fabricate precision" in text


class TestRndRouting:
    def test_router_does_not_predeclare_the_route(self):
        text = _norm()
        assert "does not predeclare the route" in text
        assert "Do not predeclare `DD_REQUIRED`" in text

    def test_explicit_user_dd_request_establishes_dd_required(self):
        assert "An explicit user DD request establishes `DD_REQUIRED`" in _norm()

    def test_all_three_routes_are_named(self):
        text = _norm()
        assert "`DAG_ONLY` / `DD_REQUIRED` / `RESEARCH_ONLY`" in text
        assert "RESEARCH_ONLY` does not authorize implementation" in text

    def test_readiness_is_a_tuple_not_a_fieldless_word(self):
        text = _norm()
        assert "never a fieldless readiness word" in text
        assert "`route: DAG_ONLY`, `status: DONE`, `phase: READY_FOR_AUTHORING`" in text
        assert "`route: DD_REQUIRED`, `status: DONE`, `phase: READY_FOR_AUTHORING`" in text

    def test_router_dispatches_change_dag_author_after_handoff(self):
        assert "Dispatch Change-DAG-Author" in _norm()


class TestPreRndResponsibility:
    def test_section_and_five_obligations_exist(self):
        text = _norm()
        assert "Pre-R&D Responsibility" in text
        assert "recognize that R&D evaluation is warranted" in text
        assert "preserve the authoritative user request" in text
        assert "capture the required `request_context`" in text
        assert "pass already-known constraints and evidence" in text
        assert "identify a concrete blocker or user decision if one exists" in text

    def test_router_is_not_required_to_pre_complete_discovery(self):
        text = _norm()
        assert "does **not** need to independently complete broad repository exploration" in text
        assert "broad historical log/DD discovery" in text
        assert "full integration tracing" in text
        assert "external/API research before RnD-Manager" in text

    def test_evidence_is_passed_not_discarded(self):
        text = _norm()
        assert "do not require duplicate discovery" in text
        assert "not hide useful context" in text


class TestProgressiveResearch:
    def test_escalation_order_is_preserved(self):
        text = _norm()
        assert "Research is proportional, not ceremonial" in text
        assert "bounded/local evidence first" in text
        assert "Support-Researcher only when unresolved substantive investigation remains." in text

    def test_investigation_criteria_are_named(self):
        text = _norm()
        assert "deep multi-file dependency tracing" in text
        assert "unclear integration ownership" in text
        assert "external/API facts that must be verified" in text
        assert "complex repository behavior that bounded localization cannot resolve" in text

    def test_unfamiliarity_does_not_select_the_researcher(self):
        assert "Unfamiliarity, first-touch, or session history is not a trigger" in _norm()

    def test_governance_is_a_direct_knowledge_source(self):
        text = _norm()
        assert "Governance skills are direct knowledge sources, not Librarian research" in text
        assert "architecture-decisions" in text
        assert "system-requirements" in text

    def test_removed_corpus_search_tools_are_absent(self):
        text = _raw()
        assert "adr_search" not in text
        assert "asr_search" not in text


class TestResearcherScopeSignalConsumption:
    def test_scope_signal_is_consumed_deterministically(self):
        text = _norm()
        assert "scope_signal" in text
        assert "WITHIN_BRIEF" in text
        assert "BROADER_SAME_REQUIREMENT" in text
        assert "NEW_REQUIREMENT" in text

    def test_broader_same_requirement_re_routes_without_asking(self):
        text = _norm()
        assert "Re-evaluate routing/tier from the new evidence" in text
        assert "route to Change-DAG-Author or RnD-Manager as the surface requires" in text
        assert "Do not ask the user merely because more files/layers are needed" in text

    def test_new_requirement_keeps_the_user_gate(self):
        text = _norm()
        assert "Apply the Scope Creep stop condition" in text
        assert "question the user before absorbing it" in text

    def test_within_brief_continues_the_route(self):
        assert "Continue the planned route." in _norm()


class TestOwnerSelection:
    def test_matrix_covers_the_specialist_owners(self):
        text = _norm()
        for owner in (
            "RnD-Manager",
            "Change-DAG-Author",
            "Change-DAG-Reviewer",
            "QA-Reviewer",
            "Support-Debugger",
            "Support-Researcher",
            "Support-Librarian",
        ):
            assert owner in text, f"owner {owner!r} missing from the routing matrix"

    def test_librarian_row_is_reason_based(self):
        text = _norm()
        assert (
            "Prior process artifacts (logs, dead ends, prior DDs) materially constrain the route"
            in text
        )
        assert "historical/process context only" in text

    def test_qa_and_support_ownership_is_stated(self):
        text = _norm()
        assert "QA-Reviewer** is the primary post-change QA owner" in text
        assert "Support-Debugger** owns root-cause analysis" in text
        assert "Support-Librarian** owns historical/process-artifact navigation only" in text

    def test_unmatched_work_routes_to_change_dag_author(self):
        assert "No row matches" in _norm()

    def test_ownership_exclusions_redirect_to_owners(self):
        text = _norm()
        assert "The router does not perform work it routes" in text
        assert "Design features or create design documents" in text
        assert "Perform QA review" in text
