"""Contract tests: the Support-Researcher selection and scope-signal boundary.

Pins one coherent rule across the routing surfaces after the Nyx extraction:

    config/skills/work-routing/SKILL.md                               -- routing authority
    config/agents/support-researcher.md                               -- producer contract
    config/skills/dispatching-agents/references/support-researcher.md -- dispatch reference

``config/skills/dispatching-agents/SKILL.md`` is dispatch mechanics only and does
not restate researcher-selection or escalation policy. Nyx no longer carries that
policy either; it binds to ``work-routing`` (pinned in
``test_nyx_routing_binding_contract.py``).

The rule: unfamiliarity and session history never select Support-Researcher.
Unresolved substantive investigation — after bounded/local evidence, a relevant
skill/governance check, and materially useful historical context — does. When
research finds a broader implementation surface for the same user requirement,
the router re-evaluates routing/tier rather than asking the user; a genuinely new
requested behavior still uses the existing user-decision (Scope Creep) gate,
which Nyx retains.

These tests fail loudly if a surface reintroduces first-touch/unfamiliarity
research routing, restores the ceremonial Tier 1 -> 2 -> 3 gate, drops the
scope-signal producer/consumer contract, or re-duplicates the escalation ladder
into the dispatch-mechanics skill.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
NYX = "config/agents/nyx.md"
ROUTING = "config/skills/work-routing/SKILL.md"
DISPATCH = "config/skills/dispatching-agents/SKILL.md"
RESEARCHER_AGENT = "config/agents/support-researcher.md"
RESEARCHER_REF = "config/skills/dispatching-agents/references/support-researcher.md"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class TestUnfamiliarityDoesNotSelectResearcher:
    def test_routing_negates_unfamiliarity_and_session_triggers(self):
        text = _read(ROUTING)
        assert "Session history is not a routing input" in text
        assert "Unfamiliarity, first-touch, or session history is not a trigger" in text

    def test_nyx_no_longer_carries_researcher_selection(self):
        text = _read(NYX)
        assert "Support-Researcher" not in text
        assert "Unfamiliarity, first-touch, or session history is not a trigger" not in text

    def test_dispatch_skill_defers_researcher_selection(self):
        text = _read(DISPATCH)
        assert "Support-Researcher is not the default for unfamiliar code" not in text
        assert "Unfamiliarity or session history is never a trigger" not in text
        assert "work-routing" in text

    def test_reference_rejects_unfamiliarity_and_session_triggers(self):
        assert "unfamiliarity and session history are not triggers" in _read(RESEARCHER_REF)


class TestSubstantiveInvestigationKeepsResearcherValid:
    def test_routing_names_real_investigation_criteria(self):
        text = _read(ROUTING)
        assert "deep multi-file dependency tracing" in text
        assert "unclear integration ownership" in text
        assert "external/API facts that must be verified" in text
        assert "complex repository behavior that bounded localization cannot resolve" in text

    def test_dispatch_skill_does_not_restate_investigation_criteria(self):
        text = _read(DISPATCH)
        assert "deep multi-file dependency tracing" not in text
        assert "unclear integration ownership" not in text


class TestBroaderSameRequirementReRoutes:
    def test_routing_re_routes_without_asking_user(self):
        text = _read(ROUTING)
        assert "BROADER_SAME_REQUIREMENT" in text
        assert "Re-evaluate routing/tier from the new evidence" in text
        assert "Change-DAG-Author or RnD-Manager" in text
        assert "Do not ask the user merely because more files/layers are needed" in text


class TestInherentBreadthIsNotScopeCreep:
    def test_scope_creep_boundary_distinguishes_breadth_from_expansion(self):
        text = _read(NYX)
        assert "Inherent implementation breadth discovered for the same requirement" in text
        assert "is not scope creep" in text
        assert "Scope creep requires newly requested behavior or changed product semantics" in text

    def test_researcher_agent_marks_broader_surface_as_not_scope_creep(self):
        assert "this is not scope creep" in _read(RESEARCHER_AGENT)


class TestNewRequirementKeepsUserGate:
    def test_routing_keeps_scope_creep_consumer_gate(self):
        text = _read(ROUTING)
        assert "NEW_REQUIREMENT" in text
        assert "Apply the Scope Creep stop condition" in text
        assert "question the user before absorbing it" in text

    def test_nyx_retains_the_user_decision_stop_condition(self):
        text = _read(NYX)
        assert "**Scope Creep**" in text
        assert "question before absorbing it" in text

    def test_researcher_agent_defines_new_requirement_signal(self):
        assert "NEW_REQUIREMENT" in _read(RESEARCHER_AGENT)


class TestProgressiveResearchIsProportional:
    def test_routing_removes_ceremonial_tier_gate(self):
        text = _read(ROUTING)
        assert "Do NOT jump to Tier 3 without running Tier 1 and Tier 2 first" not in text
        assert "(if Tier 1 returns hits)" not in text
        assert "Research is proportional, not ceremonial" in text

    def test_escalation_order_lives_only_on_the_routing_authority(self):
        text = _read(ROUTING)
        assert "bounded/local evidence first" in text
        assert (
            "Support-Researcher only when unresolved substantive investigation remains"
            in text
        )
        assert "bounded/local evidence first" not in _read(DISPATCH)

    def test_governance_skills_are_direct_knowledge_sources(self):
        assert (
            "Governance skills are direct knowledge sources, not Librarian research"
            in _read(ROUTING)
        )


class TestProducerConsumerScopeSignalContract:
    def test_researcher_agent_emits_named_scope_signal(self):
        text = _read(RESEARCHER_AGENT)
        assert "## Scope Signal" in text
        assert "scope_signal: WITHIN_BRIEF | BROADER_SAME_REQUIREMENT | NEW_REQUIREMENT" in text
        assert "Always emit this section" in text

    def test_routing_consumes_scope_signal_deterministically(self):
        text = _read(ROUTING)
        assert "Researcher Scope Signal (consumer action)" in text
        assert "returns a named `scope_signal`" in text
        assert "WITHIN_BRIEF" in text

    def test_nyx_no_longer_consumes_scope_signal(self):
        text = _read(NYX)
        assert "scope_signal" not in text
        assert "WITHIN_BRIEF" not in text

    def test_dispatch_reference_surfaces_scope_signal(self):
        assert "scope_signal" in _read(RESEARCHER_REF)
