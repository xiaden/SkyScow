"""Contract tests: RnD route ownership and return semantics.

Pins one authority chain across the active R&D routing surfaces:

    Nyx          -> decides whether R&D evaluation is required (never
                    predeclares DD_REQUIRED)
    RnD-Manager  -> owns the evidence-based route
                    (DAG_ONLY / DD_REQUIRED / RESEARCH_ONLY) and returns the
                    result to Nyx
    Nyx          -> dispatches Change-DAG-Author after a successful handoff

Surfaces pinned:
    config/agents/nyx.md
    config/agents/rnd-manager.md
    config/skills/dispatching-agents/references/rnd-manager.md   (caller reference)
    config/skills/dispatching-agents/SKILL.md
    config/commands/ecc/orchestrate.md
    docs/architecture/rnd-and-design.md
    config/agents/support-researcher.md
    config/agents/support-debugger.md

These tests fail loudly if the removed PLAN_ONLY / Exec-Planner / Exec-Manager
architecture is reintroduced, if Nyx predeclares DD_REQUIRED, if architectural
novelty is downgraded by known edit locations, if DAG_ONLY/DD_REQUIRED success is
expressed as a fieldless readiness word, or if RnD-Manager is told to spawn the
downstream authoring peer it is not permitted to spawn.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

NYX = "config/agents/nyx.md"
RND = "config/agents/rnd-manager.md"
RND_REF = "config/skills/dispatching-agents/references/rnd-manager.md"
DISPATCH = "config/skills/dispatching-agents/SKILL.md"
ORCH = "config/commands/ecc/orchestrate.md"
DOC = "docs/architecture/rnd-and-design.md"
RESEARCHER = "config/agents/support-researcher.md"
DEBUGGER = "config/agents/support-debugger.md"

ACTIVE_RND_PATH = (NYX, RND, RND_REF, DISPATCH, ORCH, DOC, RESEARCHER, DEBUGGER)

STALE_TOKENS = (
    "Exec-Planner",
    "Exec-Manager",
    "PLAN_ONLY",
    "READY_FOR_PLANNING",
    "READY_FOR_DECOMPOSITION",
)


def _raw(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _norm(relative: str) -> str:
    return " ".join(_raw(relative).split())


class TestArchitecturalNoveltyCannotBypassEvaluation:
    """Known edit locations are discovery input, not an architectural downgrade."""

    def test_known_locations_never_downgrade_architectural_novelty(self):
        text = _norm(NYX)
        assert "Known edit locations are a discovery input, not a scope downgrade" in text
        assert "even when the exact files and functions are already named" in text
        assert "route to RnD-Manager for R&D evaluation" in text
        assert "may still return `DAG_ONLY`" in text

    def test_direct_path_requires_no_failed_architectural_condition(self):
        assert "only if no architectural/design condition fails" in _norm(NYX)

    def test_evaluation_route_is_request_level_not_dd(self):
        assert "Route to RnD-Manager for evidence-based R&D evaluation" in _norm(NYX)


class TestNyxDoesNotPredeclareDDRequired:
    def test_nyx_disclaims_route_predeclaration(self):
        text = _norm(NYX)
        assert "it does not predeclare the route" in text
        assert "Do not predeclare `DD_REQUIRED`" in text

    def test_explicit_user_dd_request_establishes_dd_required(self):
        assert "An explicit user DD request establishes `DD_REQUIRED`" in _norm(NYX)

    def test_callers_do_not_predeclare_the_route(self):
        assert "is never predeclared `DD_REQUIRED` by the caller" in _norm(RND_REF)


class TestDagOnlyReturnsToNyx:
    def test_manager_returns_dag_only_to_caller(self):
        text = _norm(RND)
        assert "`DAG_ONLY`: return to Nyx" in text
        assert "`route: DAG_ONLY`, `status: DONE`, `phase: READY_FOR_AUTHORING`" in text

    def test_manager_does_not_spawn_authoring_peer(self):
        text = _norm(RND)
        assert "Do not spawn Change-DAG-Author" in text
        assert "send the work to Change-DAG-Author" not in text

    def test_reference_states_no_direct_peer_dispatch(self):
        text = _norm(RND_REF)
        assert "never dispatches the downstream authoring peer" in text
        assert "Nyx owns that dispatch" in text


class TestDDRequiredCompletionTuple:
    def test_producer_uses_exact_tuple(self):
        assert (
            "`route: DD_REQUIRED`, `status: DONE`, `phase: READY_FOR_AUTHORING`"
            in _norm(RND)
        )

    def test_caller_reference_uses_same_tuple(self):
        assert (
            "`route: DD_REQUIRED`, `status: DONE`, `phase: READY_FOR_AUTHORING`"
            in _norm(RND_REF)
        )

    def test_producer_and_caller_agree_on_readiness_semantics(self):
        fragment = "`route: DD_REQUIRED`, `status: DONE`, `phase: READY_FOR_AUTHORING`"
        assert fragment in _norm(RND)
        assert fragment in _norm(RND_REF)


class TestResearchOnlyHasNoImplementationHandoff:
    def test_research_only_implies_no_authoring(self):
        assert (
            "It never implies DD creation, Change DAG creation, or implementation authorization"
            in _norm(RND)
        )

    def test_reference_research_only_authorizes_neither(self):
        assert "authorizes neither a DD nor a Change DAG" in _norm(RND_REF)


class TestNoStaleArchitectureReferences:
    def test_stale_tokens_absent_from_active_rnd_path(self):
        for relative in ACTIVE_RND_PATH:
            text = _raw(relative)
            for token in STALE_TOKENS:
                assert token not in text, f"{token!r} still present in {relative}"

    def test_readiness_is_never_a_fieldless_status(self):
        assert "never a fieldless readiness word" in _norm(NYX)
        assert "never a fieldless word" in _norm(RND_REF)
