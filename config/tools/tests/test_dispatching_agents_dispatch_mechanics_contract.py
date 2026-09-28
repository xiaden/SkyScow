"""Contract tests: ``dispatching-agents`` is dispatch mechanics, not routing.

``config/skills/dispatching-agents/SKILL.md`` answers *given a selected agent X,
how do I dispatch X correctly?* It must **not** act as a second routing authority:
owner selection, the direct-versus-delegated decision, the specialist matrix,
R&D/Change-DAG/QA owner choice, and Support-Librarian/Researcher selection belong
to ``config/skills/work-routing/SKILL.md``.

It must still carry the dispatch mechanics: per-agent reference index, required
handoff fields, request-context and requirement-ledger propagation, negative
constraints, exact output expectations, one-task-per-dispatch, and native ``task``
fan-out behavior.

These tests fail loudly if the dispatch skill re-acquires global routing doctrine
or if it drops the handoff mechanics it exists to provide.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DISPATCH = "config/skills/dispatching-agents/SKILL.md"
REFERENCE_DIR = "config/skills/dispatching-agents/references"

# Every dispatched agent must keep its per-agent reference indexed and on disk.
# This is a reference index, not an owner-selection matrix.
REFERENCE_AGENTS = [
    "change-dag-author",
    "change-dag-worker",
    "change-dag-reviewer",
    "rnd-manager",
    "rnd-refiner",
    "rnd-dd-author",
    "rnd-architect",
    "rnd-ideator",
    "rnd-estimator",
    "rnd-complexity-advisor",
    "rnd-improver",
    "rnd-counter-ideator",
    "rnd-counter-improver",
    "qa-push-manager",
    "qa-reviewer",
    "qa-reviewer-correctness",
    "qa-reviewer-boundary",
    "qa-reviewer-journey",
    "qa-reviewer-domainrisk",
    "qa-repo-review-manager",
    "qa-repo-reviewer-correctness",
    "qa-repo-reviewer-boundary",
    "qa-repo-reviewer-journey",
    "qa-repo-reviewer-domainrisk",
    "qa-test-analyzer",
    "qa-test-generator",
    "qa-docs-analyzer",
    "qa-docs-generator",
    "qa-reassertion",
    "qa-repo-review-authorized-pilot",
    "support-debugger",
    "support-librarian",
    "support-patternenforcer",
    "support-researcher",
]


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _norm(relative: str) -> str:
    return " ".join(_read(relative).split())


class TestDispatchMechanicsDeclaration:
    def test_identifies_itself_as_dispatch_mechanics(self):
        text = _norm(DISPATCH)
        assert "dispatch mechanics" in text
        assert "does **not** answer **who** owns the next step" in text

    def test_requires_prior_owner_selection(self):
        text = _norm(DISPATCH)
        assert "The caller must already have selected the owner" in text
        assert "work-routing" in text

    def test_reports_constraint_mismatch_without_silently_rerouting(self):
        text = _norm(DISPATCH)
        assert "must not silently reroute the task" in text
        assert "report the mismatch" in text


class TestGlobalRoutingTreeIsGone:
    def test_dispatch_decision_tree_heading_is_gone(self):
        assert "Dispatch Decision Tree" not in _read(DISPATCH)

    def test_no_task_to_specialist_tree(self):
        text = _read(DISPATCH)
        assert "Task at hand" not in text
        assert "Requires R&D evaluation" not in text
        assert "Requires creating/amending a Change DAG" not in text

    def test_no_research_escalation_owner_policy(self):
        text = _read(DISPATCH)
        assert "Support-Researcher is not the default for unfamiliar code" not in text
        assert "Unfamiliarity or session history is never a trigger" not in text


class TestDirectWorkPolicyNotDuplicated:
    def test_direct_work_invariant_is_absent(self):
        assert "Direct-Work Invariant" not in _norm(DISPATCH)

    def test_no_when_not_to_dispatch_hard_stops(self):
        text = _norm(DISPATCH)
        assert "When NOT to Dispatch" not in text
        assert "do the work directly" not in text


class TestSpecialistOwnerMatrixNotDuplicated:
    def test_no_owner_selection_headings(self):
        text = _norm(DISPATCH)
        assert "Ownership Matrix" not in text
        assert "Agent Selection" not in text

    def test_no_implementation_size_threshold_bands(self):
        text = _norm(DISPATCH)
        assert "weighted_chars" not in text
        assert "32K" not in text
        assert "80K" not in text

    def test_defers_owner_selection_to_routing(self):
        text = _norm(DISPATCH)
        assert "That policy lives in `work-routing`" in text


class TestAgentDispatchReferencesRemain:
    def test_every_agent_reference_is_indexed(self):
        text = _read(DISPATCH)
        for agent in REFERENCE_AGENTS:
            assert f"references/{agent}.md" in text, f"{agent} not indexed in SKILL.md"

    def test_every_agent_reference_file_exists(self):
        for agent in REFERENCE_AGENTS:
            assert (REPO_ROOT / REFERENCE_DIR / f"{agent}.md").is_file(), agent


class TestHandoffMechanicsRemain:
    def test_requirement_ledger_propagation_required(self):
        text = _norm(DISPATCH)
        assert "include the original user request verbatim" in text
        assert "immutable requirement ledger" in text

    def test_request_context_propagation_required(self):
        text = _norm(DISPATCH)
        assert "request_context.path" in text
        assert "artifacts/requests/CTX_*.md" in text

    def test_negative_constraints_and_output_expectations_required(self):
        text = _norm(DISPATCH)
        assert "Include negative constraints" in text
        assert "Be specific about output" in text

    def test_one_task_per_dispatch_required(self):
        assert "One task per dispatch" in _norm(DISPATCH)

    def test_native_task_mechanics_retained(self):
        text = _norm(DISPATCH)
        assert "native `task`" in text
        assert "run concurrently" in text
        assert "managers spawn workers and retain the session tree" in text

    def test_handoff_is_not_discovery_duplication(self):
        text = _norm(DISPATCH)
        assert "mean duplicating the selected specialist's core investigation" in text
        assert "pass what you already know" in text

    def test_governance_is_linked_by_identity(self):
        text = _norm(DISPATCH)
        assert "architecture-decisions" in text
        assert "system-requirements" in text
