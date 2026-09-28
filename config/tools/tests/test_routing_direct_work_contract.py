"""Contract tests: the direct-work / localization routing boundary.

Pins one coherent rule across the two canonical routing surfaces:

    config/agents/nyx.md                        -- the routing authority
    config/skills/dispatching-agents/SKILL.md   -- the dispatch-side hard stops

The rule: MECHANICAL and genuinely bounded STANDARD work stays direct when the
requested behavior is clear and the surface is known or bounded-localizable; an
unknown location permits a bounded localization pass, not a dispatch; session
history is never a routing input. A first-match specialist row never overrides
the direct path.

These tests fail loudly if either surface reintroduces first-touch Librarian
routing, an absolute no-read-before-routing gate, or a first-match-always-
delegates rule that disagrees with the other surface.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
NYX = "config/agents/nyx.md"
DISPATCH = "config/skills/dispatching-agents/SKILL.md"
INVARIANT = "Direct-Work Invariant"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class TestDirectWorkInvariantIsShared:
    def test_invariant_named_on_both_surfaces(self):
        assert INVARIANT in _read(NYX)
        assert INVARIANT in _read(DISPATCH)

    def test_nyx_direct_work_precedes_specialist_rows(self):
        text = _read(NYX)
        assert "no specialist row is matched" in text
        assert "Session history is not a routing input" in text
        assert "no row below applies" in text

    def test_dispatch_skill_agrees_on_precedence(self):
        text = _read(DISPATCH)
        assert "no first-match specialist row overrides it" in text
        assert "never a dispatch reason" in text
        assert "take precedence over a first-match routing row" in text


class TestMechanicalKnownTargetStaysDirect:
    def test_mechanical_and_bounded_standard_are_direct_capable(self):
        text = _read(NYX)
        assert "MECHANICAL work and genuinely bounded STANDARD work stay" in text
        assert "one-line configuration correction" in text
        assert "known single-file edit" in text

    def test_first_touch_librarian_route_is_gone(self):
        text = _read(NYX)
        assert "Starting work in a module area" not in text
        assert "edited this session" not in text

    def test_session_history_is_not_a_routing_input(self):
        text = _read(NYX)
        assert "Session history is not a routing input" in text
        assert "was not edited previously" in text

    def test_librarian_row_is_reason_based(self):
        text = _read(NYX)
        assert (
            "Prior process artifacts (logs, dead ends, prior DDs) materially constrain the route"
            in text
        )
        assert "Support-Librarian (historical/process context only)" in text


class TestBoundedDiagnosisStaysDirect:
    def test_obvious_failure_diagnosis_is_direct(self):
        assert "obvious failure diagnosable from a small bounded read" in _read(NYX)

    def test_dispatch_skill_keeps_small_diagnosis_hard_stop(self):
        text = _read(DISPATCH)
        assert "diagnose a failure from reading 2" in text
        assert "Read the files and fix directly" in text


class TestBoundedLocalizationPermitted:
    def test_unknown_location_permits_bounded_localization(self):
        text = _read(NYX)
        assert "## Bounded Localization" in text
        assert "where does the requested behavior live?" in text
        assert "is this still one bounded local change?" in text

    def test_localization_is_bounded_not_a_scan(self):
        text = _read(NYX)
        assert "It is not broad implementation exploration" in text
        assert "a repository-wide scan is a routing failure" in text

    def test_absolute_no_read_gate_is_removed(self):
        text = _read(NYX)
        assert "already crossed the delegation threshold" not in text
        assert "Estimate scope by reading source files" not in text
        assert "Before reading files, writing code, or executing any command" not in text


class TestLargeSurfaceRoutesToDagAuthor:
    def test_localization_revealing_large_surface_routes_to_author(self):
        text = _read(NYX)
        assert (
            "If it reveals a large implementation surface, route to Change-DAG-Author"
            in text
        )

    def test_estimate_consumes_localization_evidence(self):
        text = _read(NYX)
        assert "bounded localization pass produced" in text
        assert "invent char/section/file counts" in text
        assert "do not fabricate precision" in text
