"""Contract tests: free-text ADR/ASR corpus search is not an active capability.

ADRs and ASRs are canonical workspace-local governance skills. Discovery happens
through each skill's own ``SKILL.md`` index and records are read by identity
(``adr_read`` / ``asr_read``); there is no arbitrary corpus-search tool.

These tests read the shipped registry, the Python tool modules, and the active
instruction surfaces directly, so re-adding ``adr_search`` or ``asr_search`` as
a registered, implemented, or instructed capability fails loudly.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "config" / "plugins" / "tools.ts"
AGENTS = REPO_ROOT / "config" / "agents"
SKILLS = REPO_ROOT / "config" / "skills"
COMMANDS = REPO_ROOT / "config" / "commands"
DOCS = REPO_ROOT / "docs"
GOVERNANCE_SKILLS = REPO_ROOT / ".opencode" / "skills"
TOOLS_PKG = REPO_ROOT / "config" / "tools" / "common" / "tools"

REMOVED_TOOLS = ("adr_search", "asr_search")
RETAINED_TOOLS = ("adr_suggest", "adr_commit", "adr_read", "asr_create", "asr_read")


def _active_surfaces() -> list[Path]:
    return [
        *sorted(AGENTS.glob("*.md")),
        *sorted(SKILLS.glob("*/SKILL.md")),
        *sorted(SKILLS.glob("*/references/*.md")),
        *sorted(COMMANDS.glob("*.md")),
        *sorted(COMMANDS.glob("**/*.md")),
        *sorted(GOVERNANCE_SKILLS.glob("*/SKILL.md")),
        *sorted(DOCS.glob("**/*.md")),
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
    ]


def _agent_permission(agent_name: str) -> dict:
    raw = (AGENTS / f"{agent_name}.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(raw.split("---", 2)[1])
    permission = frontmatter.get("permission")
    assert isinstance(permission, dict), f"{agent_name} has no permission block"
    return permission


class TestRemovedSearchToolsUnregistered:
    def test_plugin_does_not_register_search_tools(self):
        text = PLUGIN.read_text(encoding="utf-8")
        for tool in REMOVED_TOOLS:
            assert f"{tool}: tool(" not in text, f"{tool} is registered in tools.ts"
            assert f"common.tools.{tool}" not in text, (
                f"tools.ts still dispatches common.tools.{tool}"
            )

    def test_plugin_still_registers_retained_adr_asr_tools(self):
        text = PLUGIN.read_text(encoding="utf-8")
        for tool in RETAINED_TOOLS:
            assert f"{tool}: tool(" in text, f"retained tool {tool} disappeared"
            assert f"common.tools.{tool}" in text, (
                f"retained tool {tool} lost its runner dispatch"
            )


class TestRemovedToolModulesGone:
    def test_python_modules_deleted(self):
        for tool in REMOVED_TOOLS:
            assert not (TOOLS_PKG / f"{tool}.py").exists(), (
                f"{tool}.py still exists under config/tools/common/tools"
            )

    def test_retained_modules_present(self):
        for tool in RETAINED_TOOLS:
            module = TOOLS_PKG / f"{tool}.py"
            assert module.exists(), f"retained module {module.name} is missing"


class TestNoActiveReferences:
    def test_no_agent_permission_declares_removed_tools(self):
        offenders: list[str] = []
        for path in sorted(AGENTS.glob("*.md")):
            permission = _agent_permission(path.stem)
            for tool in REMOVED_TOOLS:
                if tool in permission:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {tool}")
        assert not offenders, "removed tool permissions: " + ", ".join(offenders)

    def test_no_active_instruction_calls_removed_tools(self):
        offenders: list[str] = []
        for path in _active_surfaces():
            text = path.read_text(encoding="utf-8")
            for tool in REMOVED_TOOLS:
                if tool in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {tool}")
        assert not offenders, "active references to removed tools: " + ", ".join(
            offenders
        )
