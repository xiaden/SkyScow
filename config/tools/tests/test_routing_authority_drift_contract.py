"""Anti-drift contract: exactly one general owner-selection authority.

After the routing-authority extraction, general owner selection lives in exactly
one place: ``config/skills/work-routing/SKILL.md``. Nyx bootstraps into it,
``dispatching-agents`` consumes its decision to build a handoff, and specialist
agents declare only their own capability boundaries.

These tests fail loudly if that split drifts:

1. Nyx recreates a general routing matrix.
2. Nyx recreates the weighted Change DAG threshold formula.
3. ``dispatching-agents`` recreates a global routing decision tree.
4. ``making-editing-agents`` recommends unfamiliarity/session history as generic
   routing policy.
5. another active general-purpose routing skill appears alongside ``work-routing``
   without an explicit scoped role.
6. ``work-routing`` disappears while Nyx still references it.

Assertions are structural or lexical markers rather than exact prose where a
structure can be asserted.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "config" / "skills"
AGENTS_DIR = REPO_ROOT / "config" / "agents"
INSTRUCTIONS_DIR = REPO_ROOT / "config" / "instructions"
COMMANDS_DIR = REPO_ROOT / "config" / "commands"

NYX = "config/agents/nyx.md"
DISPATCH = "config/skills/dispatching-agents/SKILL.md"
WORK_ROUTING = "config/skills/work-routing/SKILL.md"
MEA = "config/skills/making-editing-agents/SKILL.md"
MEA_PATTERNS = "config/skills/making-editing-agents/references/patterns.md"

# Structural markers of a re-created owner-selection matrix.
MATRIX_MARKERS = (
    "Ownership Matrix",
    "Delegation Matrix",
    "Delegation Checklist",
    "START HERE",
    "Route instead to",
    "Then the owner is",
)
# Task-tier vocabulary that belongs to work-routing, not to an agent file.
TIER_MARKERS = (
    "**MECHANICAL**",
    "**STANDARD**",
    "**ARCHITECTURAL**",
    "MECHANICAL work and genuinely bounded",
)
# General owner-selection size thresholds.
THRESHOLD_MARKERS = ("weighted_chars", "0.03", "0.015", "32K", "80K")
# Unfamiliarity / session-history conditions that must never become generic routing rules.
UNFAMILIARITY_TRIGGERS = (
    "unfamiliar system (5+ files)",
    "Starting work in unfamiliar area",
    "before working in unfamiliar areas",
    "Check Delegation Matrix",
)
# Description markers that would claim general owner-selection authority.
GENERAL_AUTHORITY_MARKERS = (
    "canonical authority for routing",
    "canonical authority for who owns the next",
    "owner-selection",
    "owner selection",
    "who owns the next",
    "routing authority",
    "routing ownership",
)
# Routing-adjacent skills that must declare an explicit scoped role rather than
# claim general authority.
SCOPED_ROUTING_ROLES = {
    "work-routing": "general owner selection",
    "gg-router": "Git/GitHub",
    "dispatching-agents": "work-routing",
    "gathering-artifacts": "process-artifact",
}


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _norm(relative: str) -> str:
    return " ".join(_read(relative).split())


def _skill_paths() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])


class TestNyxDoesNotRecreateRoutingMatrix:
    def test_no_owner_selection_matrix(self):
        text = _read(NYX)
        offenders = [m for m in MATRIX_MARKERS if m in text]
        assert not offenders, f"Nyx re-created routing-matrix markers: {offenders}"

    def test_no_task_tier_policy(self):
        text = _read(NYX)
        offenders = [m for m in TIER_MARKERS if m in text]
        assert not offenders, f"Nyx restates task-tier policy: {offenders}"

    def test_no_first_match_owner_rule(self):
        text = _norm(NYX)
        assert "first match" not in text
        assert "first-match" not in text

    def test_nyx_still_binds_to_the_canonical_skill(self):
        text = _read(NYX)
        assert "work-routing" in text
        assert "dispatching-agents" in text


class TestNyxDoesNotRecreateThresholdFormula:
    def test_no_weighted_formula_or_bands(self):
        text = _read(NYX)
        offenders = [m for m in THRESHOLD_MARKERS if m in text]
        assert not offenders, f"Nyx re-created size-threshold policy: {offenders}"


class TestDispatchingAgentsDoesNotRecreateGlobalDecisionTree:
    def test_no_owner_selection_matrix(self):
        text = _read(DISPATCH)
        offenders = [m for m in MATRIX_MARKERS if m in text]
        assert not offenders, f"dispatching-agents re-created routing markers: {offenders}"

    def test_no_threshold_bands(self):
        text = _read(DISPATCH)
        offenders = [m for m in THRESHOLD_MARKERS if m in text]
        assert not offenders, f"dispatching-agents restates size thresholds: {offenders}"

    def test_defers_owner_selection(self):
        text = _norm(DISPATCH)
        assert "work-routing" in text
        assert "does **not** answer **who** owns the next step" in text


class TestMakingEditingAgentsDoesNotPropagateGenericRouting:
    def test_references_the_canonical_split(self):
        assert "work-routing" in _read(MEA)
        assert "work-routing" in _read(MEA_PATTERNS)

    def test_no_unfamiliarity_or_session_history_dispatch_rules(self):
        combined = _norm(MEA) + " " + _norm(MEA_PATTERNS)
        offenders = [t for t in UNFAMILIARITY_TRIGGERS if t in combined]
        assert not offenders, (
            "making-editing-agents still teaches generic routing triggers: "
            f"{offenders}"
        )

    def test_teaches_capability_boundary_instead_of_a_global_matrix(self):
        lower = (_read(MEA) + " " + _read(MEA_PATTERNS)).lower()
        assert "capability boundary" in lower
        assert "delegation decision matrix" not in lower
        assert "check delegation matrix" not in lower


class TestSingleGeneralRoutingAuthority:
    def test_only_work_routing_claims_general_owner_selection(self):
        claimants = []
        for path in _skill_paths():
            desc = str(_frontmatter(path).get("description", "")).lower()
            if any(m in desc for m in GENERAL_AUTHORITY_MARKERS):
                claimants.append(path.parent.name)
        assert claimants == ["work-routing"], (
            f"general routing authority claimed by: {claimants}"
        )

    def test_routing_named_skills_are_explicitly_scoped(self):
        allowed = set(SCOPED_ROUTING_ROLES)
        offenders = [
            p.parent.name
            for p in _skill_paths()
            if ("routing" in p.parent.name or "router" in p.parent.name)
            and p.parent.name not in allowed
        ]
        assert not offenders, f"unscoped routing skill(s): {offenders}"

    def test_scoped_routing_skills_declare_their_scope(self):
        for name, scope in SCOPED_ROUTING_ROLES.items():
            if name == "work-routing":
                continue
            path = SKILLS_DIR / name / "SKILL.md"
            assert path.is_file(), f"scoped routing skill {name} is missing"
            desc = str(_frontmatter(path).get("description", ""))
            assert scope in desc, f"{name} must declare scope {scope!r}"


class TestWorkRoutingAuthorityIsPresent:
    def test_skill_exists_and_is_named(self):
        path = SKILLS_DIR / "work-routing" / "SKILL.md"
        assert path.is_file(), "canonical work-routing skill is missing"
        assert _frontmatter(path)["name"] == "work-routing"

    def test_nyx_reference_resolves_to_the_skill(self):
        assert "work-routing" in _read(NYX)
        assert (SKILLS_DIR / "work-routing" / "SKILL.md").is_file()

    def test_every_active_reference_has_a_target(self):
        surfaces = [
            *AGENTS_DIR.glob("*.md"),
            *SKILLS_DIR.glob("**/*.md"),
            *INSTRUCTIONS_DIR.glob("*.md"),
            *COMMANDS_DIR.glob("**/*.md"),
        ]
        referencing = [
            p for p in surfaces if "work-routing" in p.read_text(encoding="utf-8")
        ]
        assert referencing, "no active surface references the work-routing skill"
        assert (SKILLS_DIR / "work-routing" / "SKILL.md").is_file()
