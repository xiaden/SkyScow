"""Contract tests: ADR/ASR governance is consumed through workspace-local skills.

The canonical migration makes governance a *workspace-local skill capability*
(``architecture-decisions`` and ``system-requirements``) instead of a corpus that
agents search or that Support-Librarian discovers. Support-Librarian is narrowed to
historical/process-artifact navigation; exact records are read by identity with
``adr_read`` / ``asr_read``.

These tests pin the consumer contracts (not the storage/tooling layer) so a partial
revert that reintroduces corpus search, legacy-directory capability gating, or
Librarian-owned governance discovery fails loudly.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "config" / "agents"
SKILLS = REPO_ROOT / "config" / "skills"
COMMANDS = REPO_ROOT / "config" / "commands"
INSTRUCTIONS = REPO_ROOT / "config" / "instructions"
PLUGIN = REPO_ROOT / "config" / "plugins" / "tools.ts"
TOOLS_PKG = REPO_ROOT / "config" / "tools" / "common" / "tools"

REMOVED_TOOLS = ("adr_search", "asr_search")
LEGACY_DIRS = ("artifacts/decisions", "artifacts/requirements")
ARCHITECTURE_SKILL = "architecture-decisions"
REQUIREMENTS_SKILL = "system-requirements"
WORKSPACE_SKILLS = REPO_ROOT / ".opencode" / "skills"
# The generated governance-skill indexes legitimately describe the legacy corpus for
# migration; every *other* workspace-local skill is an active contract surface.
GOVERNANCE_SKILL_DIRS = {ARCHITECTURE_SKILL, REQUIREMENTS_SKILL}


def _non_governance_workspace_skills() -> list[Path]:
    return [
        path
        for path in sorted(WORKSPACE_SKILLS.glob("*/SKILL.md"))
        if path.parent.name not in GOVERNANCE_SKILL_DIRS
    ]

# Active consumer surfaces that must no longer treat legacy artifact directories as
# the ADR/ASR capability gate. Storage/tooling under config/tools and the generated
# workspace-local governance SKILL.md indexes legitimately describe legacy dirs for
# migration, so they are intentionally excluded.
LEGACY_GATE_SURFACES = (
    *sorted(AGENTS.glob("*.md")),
    *sorted(SKILLS.glob("**/*.md")),
    *sorted(SKILLS.glob("**/*.json")),
    *sorted(COMMANDS.glob("**/*.md")),
    *sorted(INSTRUCTIONS.glob("*.md")),
    *_non_governance_workspace_skills(),
)

# Contracts whose governance consumption must name the architecture skill.
ARCHITECTURE_CONTRACTS = (
    "config/agents/nyx.md",
    "config/agents/rnd-architect.md",
    "config/agents/rnd-ideator.md",
    "config/agents/qa-reviewer.md",
    "config/agents/rnd-manager.md",
    "config/agents/support-researcher.md",
    "config/agents/support-librarian.md",
    "config/skills/gathering-artifacts/SKILL.md",
    "config/skills/gathering-artifacts/references/examples.md",
    "config/skills/artifact-logging/SKILL.md",
    "config/skills/dispatching-agents/SKILL.md",
    "config/skills/dispatching-agents/references/support-librarian.md",
    "config/skills/capture-subsystem/SKILL.md",
    "config/commands/correct.md",
    "config/commands/bulk_correct.md",
    "config/commands/ecc/orchestrate.md",
    "docs/architecture/rnd-and-design.md",
    "README.md",
)

# Contracts whose governance consumption must name the requirements skill.
REQUIREMENTS_CONTRACTS = (
    "config/agents/nyx.md",
    "config/agents/rnd-architect.md",
    "config/agents/rnd-ideator.md",
    "config/agents/qa-reviewer.md",
    "config/agents/rnd-manager.md",
    "config/agents/support-researcher.md",
    "config/agents/support-librarian.md",
    "config/skills/gathering-artifacts/SKILL.md",
    "config/skills/gathering-artifacts/references/examples.md",
    "config/skills/artifact-logging/SKILL.md",
    "config/skills/dispatching-agents/SKILL.md",
    "config/skills/dispatching-agents/references/support-librarian.md",
    "config/commands/correct.md",
    "config/commands/bulk_correct.md",
    "config/commands/ecc/orchestrate.md",
    "docs/architecture/rnd-and-design.md",
    "README.md",
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _frontmatter(relative: str) -> dict:
    raw = _read(relative)
    return yaml.safe_load(raw.split("---", 2)[1])


class TestSupportLibrarianNoLongerOwnsGovernance:
    def test_no_adr_or_asr_permissions(self):
        permission = _frontmatter("config/agents/support-librarian.md")["permission"]
        assert isinstance(permission, dict)
        offenders = [k for k in permission if k.startswith(("adr_", "asr_"))]
        assert not offenders, f"Support-Librarian still holds governance perms: {offenders}"

    def test_no_corpus_search_tools_in_contract(self):
        text = _read("config/agents/support-librarian.md")
        for tool in REMOVED_TOOLS:
            assert tool not in text, f"Support-Librarian contract references {tool}"

    def test_contract_is_process_scoped(self):
        text = _read("config/agents/support-librarian.md")
        lower = text.lower()
        assert "historical" in lower or "process-artifact" in lower
        assert "adr review" not in lower and "asr review" not in lower

    def test_redirects_governance_to_local_skills(self):
        text = _read("config/agents/support-librarian.md")
        assert ARCHITECTURE_SKILL in text
        assert REQUIREMENTS_SKILL in text


class TestNoCorpusSearchInActiveContracts:
    def test_no_active_contract_calls_removed_tools(self):
        offenders: list[str] = []
        for path in LEGACY_GATE_SURFACES:
            text = path.read_text(encoding="utf-8")
            for tool in REMOVED_TOOLS:
                if tool in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {tool}")
        assert not offenders, "active references to removed tools: " + ", ".join(offenders)


class TestGovernanceSkillReferences:
    def test_architecture_contracts_reference_architecture_skill(self):
        missing = [
            rel
            for rel in ARCHITECTURE_CONTRACTS
            if ARCHITECTURE_SKILL not in _read(rel)
        ]
        assert not missing, (
            "architecture-relevant contracts do not refer to the "
            f"`{ARCHITECTURE_SKILL}` skill: {missing}"
        )

    def test_requirements_contracts_reference_requirements_skill(self):
        missing = [
            rel
            for rel in REQUIREMENTS_CONTRACTS
            if REQUIREMENTS_SKILL not in _read(rel)
        ]
        assert not missing, (
            "ASR-relevant contracts do not refer to the "
            f"`{REQUIREMENTS_SKILL}` skill: {missing}"
        )


class TestLegacyDirectoryGatingRemoved:
    def test_no_active_contract_gates_on_legacy_dirs(self):
        offenders: list[str] = []
        for path in LEGACY_GATE_SURFACES:
            text = path.read_text(encoding="utf-8")
            for legacy in LEGACY_DIRS:
                if legacy in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {legacy}")
        assert not offenders, (
            "active contracts still reference legacy artifact directories as "
            f"governance capability: {offenders}"
        )

    def test_legacy_capability_gate_phrase_is_gone(self):
        offenders: list[str] = []
        for path in LEGACY_GATE_SURFACES:
            text = path.read_text(encoding="utf-8")
            if "Before using ADR/ASR features" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))
        assert not offenders, (
            f"legacy ADR/ASR capability gate remains in: {offenders}"
        )


class TestExactIdentityReadsRemainValid:
    def test_identity_read_tools_exist_and_are_registered(self):
        plugin = PLUGIN.read_text(encoding="utf-8")
        for tool in ("adr_read", "asr_read"):
            assert (TOOLS_PKG / f"{tool}.py").exists(), f"{tool}.py is missing"
            assert f"{tool}: tool(" in plugin, f"{tool} is not registered"
            assert f"common.tools.{tool}" in plugin, f"{tool} lost its runner dispatch"

    def test_consumers_use_identity_reads(self):
        for rel in (
            "config/skills/gathering-artifacts/SKILL.md",
            "config/skills/artifact-logging/SKILL.md",
        ):
            text = _read(rel)
            assert "adr_read" in text, f"{rel} no longer documents identity reads"
        assert "asr_read" in _read("config/skills/gathering-artifacts/SKILL.md")


class TestLibrarianStaysConditional:
    def test_gathering_artifacts_keeps_librarian_conditional(self):
        text = _read("config/skills/gathering-artifacts/SKILL.md")
        assert "Support-Librarian" in text
        assert ARCHITECTURE_SKILL in text
        assert REQUIREMENTS_SKILL in text
        # Governance is not delegated to the Librarian.
        assert "Don't delegate governance to the Librarian" in text
