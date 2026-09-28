"""Contract tests: R&D discovery ownership (issue #62).

Pins one coherent rule across the active routing/dispatch surfaces:

    config/agents/nyx.md
    config/skills/dispatching-agents/SKILL.md
    config/skills/dispatching-agents/references/rnd-manager.md
    docs/architecture/rnd-and-design.md

The rule: Nyx routes architectural work to RnD-Manager for R&D evaluation
*without* first completing a broad repository/history/API discovery pass.
Nyx's pre-R&D responsibility is bounded — recognize R&D evaluation is warranted,
preserve the authoritative request, capture request_context, pass already-known
constraints/evidence, and surface a concrete blocker/user decision. RnD-Manager
owns selection of the design-evidence graph (governance skills, Support-Librarian,
Support-Researcher, other R&D capabilities). Already-known evidence is passed
downstream rather than discarded, and no active universal rule requires the
caller to duplicate the selected specialist's pre-dispatch investigation.

These tests fail loudly if any surface reintroduces an unconditional
"caller must investigate everything / inspect logs before every dispatch"
requirement, restores "full research" as Nyx's ARCHITECTURAL-tier obligation,
or drops the producer/selector ownership boundary.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
NYX = "config/agents/nyx.md"
DISPATCH = "config/skills/dispatching-agents/SKILL.md"
RND_REF = "config/skills/dispatching-agents/references/rnd-manager.md"
DOC = "docs/architecture/rnd-and-design.md"

ACTIVE_SURFACES = (NYX, DISPATCH, RND_REF, DOC)


def _raw(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _norm(relative: str) -> str:
    return " ".join(_raw(relative).split())


class TestArchitecturalTierRoutesInsteadOfResearching:
    """A request can be dispatched to RnD-Manager without a broad pass first."""

    def test_architectural_tier_is_evaluation_depth_not_full_research(self):
        text = _norm(NYX)
        assert "R&D evaluation depth, not a duplicate discovery pass" in text
        assert "route to RnD-Manager, which owns the selected design-evidence graph" in text
        assert (
            "Do not complete broad repository/history/API research before the handoff"
            in text
        )

    def test_nyx_no_longer_owns_full_research_for_architectural_work(self):
        text = _raw(NYX)
        assert "Full research: logs, skills, codebase exploration" not in text

    def test_matrix_row_states_evidence_graph_ownership(self):
        assert "selects the design-evidence graph" in _norm(NYX)


class TestPreRndResponsibilityIsBounded:
    def test_pre_rnd_responsibility_section_exists(self):
        assert "Pre-R&D Responsibility" in _raw(NYX)

    def test_five_bounded_obligations_are_named(self):
        text = _norm(NYX)
        assert "recognize that R&D evaluation is warranted" in text
        assert "preserve the authoritative user request" in text
        assert "capture the required `request_context`" in text
        assert "pass already-known constraints and evidence" in text
        assert "identify a concrete blocker or user decision if one exists" in text

    def test_nyx_is_not_required_to_pre_complete_discovery(self):
        text = _norm(NYX)
        assert (
            "does **not** need to independently complete broad repository exploration"
            in text
        )
        assert "broad historical log/DD discovery" in text
        assert "full integration tracing" in text
        assert "external/API research before RnD-Manager" in text


class TestCompleteHandoffStillCarriesRequestAndContext:
    def test_nyx_preserves_request_and_captures_context(self):
        text = _norm(NYX)
        assert "preserve the authoritative user request" in text
        assert "capture the required `request_context`" in text

    def test_dispatch_skill_requires_verbatim_request_and_context_path(self):
        text = _norm(DISPATCH)
        assert "include the original user request verbatim" in text
        assert "artifacts/requests/CTX_*.md" in text
        assert "request_context.path" in text

    def test_caller_reference_carries_request_and_context_fields(self):
        text = _norm(RND_REF)
        assert "Authoritative user request:" in text
        assert "request_context.path:" in text
        assert "complete handoff" in text


class TestRndManagerOwnsEvidenceSelection:
    def test_caller_reference_names_evidence_ownership(self):
        text = _norm(RND_REF)
        assert "RnD-Manager owns selection of the design-evidence graph" in text
        assert "Support-Librarian when historical/process context matters" in text
        assert "Support-Researcher when repository/API facts are missing" in text

    def test_dispatch_skill_keeps_graph_selection_with_manager(self):
        assert "selection of the design-evidence graph" in _norm(DISPATCH)

    def test_architecture_doc_records_manager_evidence_ownership(self):
        text = _norm(DOC)
        assert "RnD-Manager owns selection of the design-evidence graph" in text


class TestAlreadyKnownEvidenceIsPassedNotDiscarded:
    def test_evidence_is_an_input_not_a_discard(self):
        text = _norm(RND_REF)
        assert "Already-known caller evidence is an input" in text
        assert "must not discard it" in text

    def test_nyx_rule_is_no_duplicate_discovery_not_hidden_context(self):
        text = _norm(NYX)
        assert "do not require duplicate discovery" in text
        assert "not hide useful context" in text

    def test_doc_records_passed_not_discarded(self):
        assert "already-known evidence is passed rather than discarded" in _norm(DOC)


class TestNoUniversalDuplicatedPreDispatchDiscovery:
    def test_dispatch_skill_drops_caller_redo_investigation_rule(self):
        text = _raw(DISPATCH)
        assert "Do your own investigation and check logs" not in text
        assert "Do your own investigation" not in text

    def test_dispatch_skill_states_handoff_is_not_duplication(self):
        text = _norm(DISPATCH)
        assert (
            "mean duplicating the selected specialist's core investigation" in text
        )
        assert "pass what you already know" in text

    def test_all_surfaces_agree_governance_is_loaded_once(self):
        for relative in ACTIVE_SURFACES:
            assert "independently read the same governance corpus" in _norm(relative), (
                f"governance single-load rule missing from {relative}"
            )

    def test_no_caller_investigate_everything_rule_remains(self):
        for relative in ACTIVE_SURFACES:
            text = _norm(relative)
            assert "investigate everything" not in text
            assert "inspect logs before every dispatch" not in text
