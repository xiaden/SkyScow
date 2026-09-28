"""Contract: Nyx's conditional-loading table only names skills that ship.

Issue #45: Nyx offered to load ``troubleshooting`` and ``error-ownership`` for
failed-fix and diagnostic work. Neither skill exists. Those behaviors are owned
by existing canonical surfaces:

- failed-fix / diagnostic escalation: ``work-routing`` selects Support-Debugger
  (its own 5-phase Observation -> Hypothesis -> Verification -> Research -> Plan
  procedure lives in ``config/agents/support-debugger.md``);
- lint/test/diagnostic causality: ``config/instructions/validation-mandate.md``
  plus Nyx's always-on Error ownership constraint.

The primary check is structural: every skill named in the table's "How Loaded"
column must resolve to a shipped skill directory, so a future edit cannot
reintroduce a load for a skill that does not exist.
"""

from __future__ import annotations

import re
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parents[1]

NYX = REPO_ROOT / "config" / "agents" / "nyx.md"
SKILLS_ROOT = REPO_ROOT / "config" / "skills"
WORK_ROUTING = SKILLS_ROOT / "work-routing" / "SKILL.md"
SUPPORT_DEBUGGER_AGENT = REPO_ROOT / "config" / "agents" / "support-debugger.md"
SUPPORT_DEBUGGER_DISPATCH = (
    SKILLS_ROOT / "dispatching-agents" / "references" / "support-debugger.md"
)

LOADED_SKILL = re.compile(r"Load\s+`([A-Za-z0-9_-]+)`\s+skill")
REMOVED_SKILL_NAMES = ("troubleshooting", "error-ownership")


def _nyx_text() -> str:
    return NYX.read_text(encoding="utf-8")


def _conditional_loading_rows() -> list[tuple[str, str]]:
    """Return ``(how_loaded, full_row)`` for each row of the loading table."""
    lines = _nyx_text().splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == "## Conditional Loading"
    )
    rows: list[tuple[str, str]] = []
    for line in lines[start:]:
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or set(cells[0]) <= {"-"}:
            continue
        rows.append((cells[1], line))
    return rows


def test_every_named_loading_skill_is_shipped():
    named: list[str] = []
    for how_loaded, _row in _conditional_loading_rows():
        named.extend(LOADED_SKILL.findall(how_loaded))

    assert named, "conditional-loading table named no loadable skills"
    missing = [
        name for name in named if not (SKILLS_ROOT / name / "SKILL.md").is_file()
    ]
    assert missing == [], f"conditional loading names unshipped skills: {missing}"


def test_removed_skill_names_are_not_offered_as_loads():
    text = _nyx_text()
    for name in REMOVED_SKILL_NAMES:
        assert f"`{name}` skill" not in text
        assert not (SKILLS_ROOT / name).exists()

    table = "\n".join(row for _how, row in _conditional_loading_rows())
    for name in REMOVED_SKILL_NAMES:
        assert name not in table


def test_error_ownership_points_to_the_validation_mandate():
    text = _nyx_text()
    assert "validation-mandate.md" in text

    ownership = [line for line in text.splitlines() if "Error ownership" in line]
    assert ownership, "Nyx must keep an always-on Error ownership constraint"
    assert any("validation-mandate.md" in line for line in ownership)


def test_support_debugger_route_remains_available():
    assert SUPPORT_DEBUGGER_AGENT.is_file()
    assert SUPPORT_DEBUGGER_DISPATCH.is_file()

    routing = WORK_ROUTING.read_text(encoding="utf-8")
    routes_failed_fixes = [
        line
        for line in routing.splitlines()
        if "Support-Debugger" in line and ("fix attempt" in line or "root cause" in line)
    ]
    assert routes_failed_fixes, (
        "work-routing must still route unresolved debugging to Support-Debugger"
    )
