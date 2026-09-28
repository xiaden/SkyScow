"""Pure functions for parsing and generating Architecturally Significant Requirement (ASR) markdown.

This module handles markdown mechanics only — no file I/O beyond next_asr_number(),
no logging, no MCP logic.

ASR markdown format:
    # ASR-NNNN
    **Priority:** 0
    **Status:** Active
    **Created:** 2026-04-08
    **Updated:** 2026-04-08

    ## Requirement
    ...

    ## Notes
    ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# --- Constants ---

ASR_STATUSES_EXACT: frozenset[str] = frozenset({"Active", "Archived"})
SUPERSEDED_PATTERN: re.Pattern[str] = re.compile(r"^Superseded by ASR-\d{4}$")

# Committed ASRs are repository governance knowledge owned by a workspace-local
# skill (not shipped harness configuration). Legacy ``artifacts/requirements``
# is no longer a canonical ASR store and is never read as a fallback.
ASR_SKILL_NAME = "system-requirements"
ASR_SKILL_DIR = f".opencode/skills/{ASR_SKILL_NAME}"
ASR_REFERENCES_DIR = f"{ASR_SKILL_DIR}/references"

# Deterministic status -> references/ subdirectory for committed ASRs. Every
# "Superseded by ASR-NNNN" status resolves to the superseded directory.
ASR_STATUS_DIRS: dict[str, str] = {
    "Active": "active",
    "Archived": "archived",
}
ASR_SUPERSEDED_DIR = "superseded"

# Legacy pre-migration committed corpus. It is never read as a canonical
# fallback; a legacy-only workspace must migrate explicitly (see
# common.tools.governance_migrate).
LEGACY_REQUIREMENTS_DIR = "artifacts/requirements"

ASR_PREFIX = "ASR-"

# --- Regex patterns ---

TITLE_PATTERN: re.Pattern[str] = re.compile(r"^#\s+ASR-(\d+)\s*$")
META_PATTERN: re.Pattern[str] = re.compile(r"^\*\*(\w[\w\s]*):\*\*\s*(.*)$")
SECTION_PATTERN: re.Pattern[str] = re.compile(r"^##\s+(.+)$")


# --- Dataclass ---


@dataclass
class ASR:
    """Structured representation of an Architecturally Significant Requirement."""

    number: int
    priority: int
    status: str
    created: str
    updated: str
    requirement: str
    notes: str = ""


# --- Helpers ---


def today_iso() -> str:
    """Return today's date as ISO 8601 string."""
    return date.today().isoformat()


def _unescape_literal_newlines(text: str) -> str:
    """Replace literal two-character escape sequences with actual characters.

    Handles ``\\n`` → newline (``\\x0a``) and ``\\t`` → tab (``\\x09``).
    This is needed because MCP transport serializes real newlines as the
    literal two-character sequence ``\\n``.
    """
    return text.replace("\\n", "\n").replace("\\t", "\t")


# --- Canonical storage layout ---


def asr_skill_root(workspace_root: Path) -> Path:
    """Return the workspace-local ``system-requirements`` skill root."""
    return workspace_root / ASR_SKILL_DIR


def asr_references_root(workspace_root: Path) -> Path:
    """Return the canonical ``references/`` root for committed ASRs."""
    return workspace_root / ASR_REFERENCES_DIR


def resolve_asr_status_dir(status: str) -> str:
    """Return the references/ subdirectory name for a committed ASR status.

    ``Active``/``Archived`` map directly; every ``Superseded by ASR-NNNN``
    status maps to ``superseded``. Raises ValueError otherwise.
    """
    sub = ASR_STATUS_DIRS.get(status)
    if sub is not None:
        return sub
    if SUPERSEDED_PATTERN.match(status):
        return ASR_SUPERSEDED_DIR
    raise ValueError(
        f"ASR status '{status}' has no canonical storage directory "
        f"(expected one of {sorted(ASR_STATUS_DIRS)} or 'Superseded by ASR-NNNN')"
    )


def asr_status_dir(workspace_root: Path, status: str) -> Path:
    """Resolve the canonical directory for a committed ASR with ``status``."""
    return asr_references_root(workspace_root) / resolve_asr_status_dir(status)


def asr_status_dirs(workspace_root: Path) -> list[Path]:
    """Return every canonical ASR status directory in deterministic order."""
    subs = sorted(set(ASR_STATUS_DIRS.values()) | {ASR_SUPERSEDED_DIR})
    return [asr_references_root(workspace_root) / sub for sub in subs]


def iter_asr_records(workspace_root: Path) -> list[Path]:
    """Enumerate committed ASR files across every canonical status directory."""
    records: list[Path] = []
    for status_dir in asr_status_dirs(workspace_root):
        if status_dir.is_dir():
            records.extend(sorted(status_dir.glob(f"{ASR_PREFIX}*.md")))
    return records


def legacy_asr_records(workspace_root: Path) -> list[Path]:
    """Enumerate the legacy ``artifacts/requirements/ASR-*.md`` corpus, if any.

    This is a migration signal, not a canonical store: callers must not read
    these records as a fallback for the governance skill references.
    """
    legacy_dir = workspace_root / LEGACY_REQUIREMENTS_DIR
    if not legacy_dir.is_dir():
        return []
    return sorted(legacy_dir.glob(f"{ASR_PREFIX}*.md"))


def find_asr_number(workspace_root: Path, number: int) -> Path | None:
    """Locate a committed ASR by numeric ID across every status directory."""
    filename = f"{ASR_PREFIX}{number:04d}.md"
    for status_dir in asr_status_dirs(workspace_root):
        candidate = status_dir / filename
        if candidate.is_file():
            return candidate
    return None


# --- Validation ---


def validate_status(status: str) -> str | None:
    """Validate an ASR status. Returns error message or None if valid."""
    if status in ASR_STATUSES_EXACT or SUPERSEDED_PATTERN.match(status):
        return None
    return (
        f"Invalid status '{status}': must be one of {sorted(ASR_STATUSES_EXACT)} "
        "or match 'Superseded by ASR-NNNN'"
    )


def validate_priority(priority: int) -> str | None:
    """Validate an ASR priority. Returns error message or None if valid."""
    if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
        return f"Invalid priority '{priority}': must be a non-negative integer"
    return None


# --- Generation ---


def generate_asr(asr: ASR) -> str:
    """Generate ASR markdown from an ASR dataclass."""
    lines: list[str] = []

    lines.append(f"# ASR-{asr.number:04d}")
    lines.append("")

    # Metadata
    lines.append(f"**Priority:** {asr.priority}  ")
    lines.append(f"**Status:** {asr.status}  ")
    lines.append(f"**Created:** {asr.created}  ")
    lines.append(f"**Updated:** {asr.updated}  ")
    lines.append("")

    lines.append("## Requirement")
    lines.append("")
    lines.append(asr.requirement.strip())
    lines.append("")

    notes = asr.notes.strip()
    if notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(notes)
        lines.append("")

    return "\n".join(lines)


def make_asr_filename(number: int) -> str:
    """Build the canonical filename for an ASR."""
    return f"ASR-{number:04d}.md"


def next_asr_number(workspace_root: Path) -> int:
    """Find the next ASR number by scanning every canonical status directory."""
    numbers: list[int] = []
    for record in iter_asr_records(workspace_root):
        m = re.match(r"^ASR-(\d+)\.md$", record.name)
        if m:
            numbers.append(int(m.group(1)))
    return max(numbers, default=0) + 1


# --- Parsing ---


def parse_asr(markdown: str) -> ASR:
    """Parse ASR markdown into an ASR dataclass.

    Uses regex line-by-line parsing. Raises ValueError on malformed input.
    """
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    lines = markdown.split("\n")

    number = 0
    priority_raw = ""
    status = ""
    created = ""
    updated = ""
    requirement_lines: list[str] = []
    notes_lines: list[str] = []
    state = "header"

    for line in lines:
        stripped = line.strip()

        if state == "header":
            m = TITLE_PATTERN.match(line)
            if m:
                number = int(m.group(1))
                continue
            m = META_PATTERN.match(line)
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip().rstrip()
                if val.endswith("  "):
                    val = val[:-2].rstrip()
                if key == "Priority":
                    priority_raw = val
                elif key == "Status":
                    status = val
                elif key == "Created":
                    created = val
                elif key == "Updated":
                    updated = val
                continue
            if stripped == "## Requirement":
                state = "requirement"
                continue
            if stripped == "## Notes":
                state = "notes"
                continue
        elif state == "requirement":
            if stripped == "## Notes":
                state = "notes"
                continue
            requirement_lines.append(line)
        elif state == "notes":
            notes_lines.append(line)

    requirement = "\n".join(requirement_lines).strip()
    notes = "\n".join(notes_lines).strip()

    if number == 0:
        raise ValueError("ASR number not found in markdown")
    if not requirement:
        raise ValueError("Requirement section not found or empty")

    try:
        priority = int(priority_raw)
    except ValueError as exc:
        raise ValueError("Priority must be an integer") from exc

    return ASR(
        number=number,
        priority=priority,
        status=status or "Active",
        created=created,
        updated=updated,
        requirement=requirement,
        notes=notes,
    )
