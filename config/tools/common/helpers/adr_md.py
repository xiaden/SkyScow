"""Pure functions for parsing and generating Architecture Decision Record (ADR) markdown files.

This module owns ADR markdown parsing/generation plus the committed-record storage
layout: path resolution across status directories and the supersession transition.
It performs no logging and no MCP logic.

ADR markdown format:
    # ADR-NNN: {title}
    **Status:** Proposed
    **Date:** 2026-04-01
    **Tags:** persistence, arangodb
    **Source Log:** rnd-ddauthor#L42

    ## Context
    ...

    ## Decision
    ...

    ## Consequences
    ...
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

# --- Constants ---

ADR_STATUSES: frozenset[str] = frozenset({"Proposed", "Accepted", "Deprecated", "Superseded"})
SOURCE_LOG_PATTERN: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]#L\d+$")

# Committed ADRs are repository governance knowledge owned by a workspace-local
# skill (not shipped harness configuration). Legacy ``artifacts/decisions`` is
# no longer a canonical ADR store and is never read as a fallback.
ADR_SKILL_NAME = "architecture-decisions"
ADR_SKILL_DIR = f".opencode/skills/{ADR_SKILL_NAME}"
ADR_REFERENCES_DIR = f"{ADR_SKILL_DIR}/references"

# Deterministic status -> references/ subdirectory for committed ADRs.
# "Proposed" is deliberately absent: an unapproved ADR is a staged draft, not
# governing knowledge, and must never land in the skill's references.
ADR_STATUS_DIRS: dict[str, str] = {
    "Accepted": "accepted",
    "Deprecated": "deprecated",
    "Superseded": "superseded",
}

# Status applied to a governing ADR when a newer ADR supersedes it.
ADR_SUPERSEDED_STATUS = "Superseded"

# Unapproved ADR drafts are process artifacts staged outside the governance
# skill and its governing index.
DRAFTS_DIR = "artifacts/decisions/drafts"

# Legacy pre-migration committed corpus. It is never read as a canonical
# fallback; a legacy-only workspace must migrate explicitly (see
# common.tools.governance_migrate).
LEGACY_DECISIONS_DIR = "artifacts/decisions"

ADR_PREFIX = "ADR-"

# --- Regex patterns ---

TITLE_PATTERN: re.Pattern[str] = re.compile(r"^#\s+ADR-(\d+):\s+(.+)$")
DRAFT_TITLE_PATTERN: re.Pattern[str] = re.compile(r"^#\s+ADR-DRAFT:\s+(.+)$")
META_PATTERN: re.Pattern[str] = re.compile(r"^\*\*(\w[\w\s]*):\*\*\s*(.*)$")
SECTION_PATTERN: re.Pattern[str] = re.compile(r"^##\s+(.+)$")

# Standard section order
_STANDARD_SECTIONS = ("Context", "Decision", "Consequences")


# --- Dataclass ---


@dataclass
class ADR:
    """Structured representation of an Architecture Decision Record."""

    number: int
    title: str
    status: str
    date: str
    tags: list[str] = field(default_factory=list)
    source_log: str | None = None
    supersedes: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)


# --- Helpers ---


def _slugify(title: str) -> str:
    """Convert a title to a URL-safe slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    # Collapse multiple hyphens
    slug = re.sub(r"-{2,}", "-", slug)
    return slug


def _unescape_literal_newlines(text: str) -> str:
    """Replace literal two-character escape sequences with actual characters.

    Handles ``\\n`` → newline (``\\x0a``) and ``\\t`` → tab (``\\x09``).
    This is needed because MCP transport serializes real newlines as the
    literal two-character sequence ``\\n``.
    """
    return text.replace("\\n", "\n").replace("\\t", "\t")


# --- Canonical storage layout ---


def adr_skill_root(workspace_root: Path) -> Path:
    """Return the workspace-local ``architecture-decisions`` skill root."""
    return workspace_root / ADR_SKILL_DIR


def adr_references_root(workspace_root: Path) -> Path:
    """Return the canonical ``references/`` root for committed ADRs."""
    return workspace_root / ADR_REFERENCES_DIR


def resolve_adr_status_dir(status: str) -> str:
    """Return the references/ subdirectory name for a committed ADR status.

    Raises ValueError for a status with no committed-record directory (for
    example ``Proposed``, which is staged as a draft instead).
    """
    sub = ADR_STATUS_DIRS.get(status)
    if sub is None:
        raise ValueError(
            f"ADR status '{status}' has no canonical storage directory "
            f"(expected one of {sorted(ADR_STATUS_DIRS)})"
        )
    return sub


def adr_status_dir(workspace_root: Path, status: str) -> Path:
    """Resolve the canonical directory for a committed ADR with ``status``."""
    return adr_references_root(workspace_root) / resolve_adr_status_dir(status)


def adr_status_dirs(workspace_root: Path) -> list[Path]:
    """Return every canonical ADR status directory in deterministic order."""
    return [
        adr_references_root(workspace_root) / sub
        for sub in sorted(ADR_STATUS_DIRS.values())
    ]


def iter_adr_records(workspace_root: Path) -> list[Path]:
    """Enumerate committed ADR files across every canonical status directory."""
    records: list[Path] = []
    for status_dir in adr_status_dirs(workspace_root):
        if status_dir.is_dir():
            records.extend(sorted(status_dir.glob(f"{ADR_PREFIX}*.md")))
    return records


def legacy_adr_records(workspace_root: Path) -> list[Path]:
    """Enumerate the legacy ``artifacts/decisions/ADR-*.md`` corpus, if any.

    This is a migration signal, not a canonical store: callers must not read
    these records as a fallback for the governance skill references.
    """
    legacy_dir = workspace_root / LEGACY_DECISIONS_DIR
    if not legacy_dir.is_dir():
        return []
    return sorted(legacy_dir.glob(f"{ADR_PREFIX}*.md"))


def find_adr_in_status_dir(workspace_root: Path, status: str, number: int) -> Path | None:
    """Locate a committed ADR by numeric ID within one status directory."""
    status_dir = adr_status_dir(workspace_root, status)
    if not status_dir.is_dir():
        return None
    matches = sorted(status_dir.glob(f"{ADR_PREFIX}{number:03d}-*.md"))
    if matches:
        return matches[0]
    exact = status_dir / f"{ADR_PREFIX}{number:03d}.md"
    return exact if exact.is_file() else None


def find_adr_number(workspace_root: Path, number: int) -> Path | None:
    """Locate a committed ADR by numeric ID across every status directory."""
    for status in sorted(ADR_STATUS_DIRS):
        found = find_adr_in_status_dir(workspace_root, status, number)
        if found is not None:
            return found
    return None


_ADR_ID_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"(?:ADR-)?0*(\d+)(?:-.*)?", re.IGNORECASE
)
_STATUS_LINE_PATTERN: re.Pattern[str] = re.compile(r"^\*\*Status:\*\*.*$", re.MULTILINE)


def adr_number_from_token(token: str) -> int | None:
    """Extract the numeric ADR ID from an identifier token.

    Accepts ``ADR-007``, ``007``, ``7``, ``ADR-007-some-slug``, and an optional
    trailing ``.md``. Returns ``None`` when no ADR number can be derived.
    """
    text = token.strip()
    if text.lower().endswith(".md"):
        text = text[:-3]
    match = _ADR_ID_TOKEN_PATTERN.fullmatch(text)
    if match is None:
        return None
    return int(match.group(1))


def set_adr_status(markdown: str, status: str) -> str:
    """Return ADR markdown with only its ``**Status:**`` metadata line replaced.

    This is the minimal metadata correction used by supersession; it preserves
    the rest of the record byte-for-byte. Raises ValueError when the record has
    no Status metadata line.
    """
    if _STATUS_LINE_PATTERN.search(markdown) is None:
        raise ValueError("ADR markdown has no '**Status:**' metadata line")
    return _STATUS_LINE_PATTERN.sub(f"**Status:** {status}  ", markdown, count=1)


def supersede_adr_record(workspace_root: Path, number: int) -> Path:
    """Transition an accepted ADR to superseded, preserving its ID.

    Moves ``references/accepted/ADR-NNN-*.md`` into ``references/superseded/``
    and corrects only its ``Status`` metadata. The record is moved, never
    copied, so exactly one canonical file remains for the ID.

    Raises FileNotFoundError when no accepted ADR has ``number``, and
    FileExistsError when a superseded record with that ID already exists.
    """
    source = find_adr_in_status_dir(workspace_root, "Accepted", number)
    if source is None:
        raise FileNotFoundError(f"No accepted ADR with number {number}")
    superseded_dir = adr_status_dir(workspace_root, "Superseded")
    superseded_dir.mkdir(parents=True, exist_ok=True)
    destination = superseded_dir / source.name
    if destination.exists():
        raise FileExistsError(f"Superseded ADR already present: {destination.name}")
    source.rename(destination)
    try:
        destination.write_text(
            set_adr_status(
                destination.read_text(encoding="utf-8"), ADR_SUPERSEDED_STATUS
            ),
            encoding="utf-8",
        )
    except OSError:
        # Restore the accepted record rather than leave a moved-but-uncorrected
        # file behind the caller's back.
        with contextlib.suppress(OSError):
            destination.rename(source)
        raise
    return destination


# --- Validation ---


def validate_status(status: str) -> str | None:
    """Validate an ADR status. Returns error message or None if valid."""
    if status not in ADR_STATUSES:
        return f"Invalid status '{status}': must be one of {sorted(ADR_STATUSES)}"
    return None


def validate_source_log(source_log: str) -> str | None:
    """Validate a source log reference. Returns error message or None if valid."""
    if not source_log:
        return None
    if not SOURCE_LOG_PATTERN.match(source_log):
        return (
            f"Invalid source_log '{source_log}': "
            "must match pattern '{agent-name}#L{{number}}' (e.g., 'rnd-ddauthor#L42')"
        )
    return None


# --- Generation ---


def generate_adr(adr: ADR) -> str:
    """Generate ADR markdown from an ADR dataclass."""
    lines: list[str] = []

    # Title
    if adr.number == 0:
        lines.append(f"# ADR-DRAFT: {adr.title}")
    else:
        lines.append(f"# ADR-{adr.number:03d}: {adr.title}")
    lines.append("")

    # Metadata
    lines.append(f"**Status:** {adr.status}  ")
    lines.append(f"**Date:** {adr.date}  ")
    lines.append(f"**Tags:** {', '.join(adr.tags)}  ")
    if adr.source_log:
        lines.append(f"**Source Log:** {adr.source_log}  ")
    if adr.supersedes:
        lines.append(f"**Supersedes:** {', '.join(adr.supersedes)}  ")
    lines.append("")

    # Sections: standard order first, then extras, References last
    written: set[str] = set()
    for heading in _STANDARD_SECTIONS:
        if heading in adr.sections:
            lines.append(f"## {heading}")
            lines.append("")
            content = adr.sections[heading].strip()
            if content:
                lines.append(content)
                lines.append("")
            written.add(heading)

    # Extra sections (not standard and not References)
    for heading, content in adr.sections.items():
        if heading in written or heading == "References":
            continue
        lines.append(f"## {heading}")
        lines.append("")
        if content.strip():
            lines.append(content.strip())
            lines.append("")
        written.add(heading)

    # References last
    if "References" in adr.sections:
        lines.append("## References")
        lines.append("")
        ref_content = adr.sections["References"].strip()
        if ref_content:
            lines.append(ref_content)
            lines.append("")

    return "\n".join(lines)


# --- Parsing ---


def parse_adr(markdown: str) -> ADR:
    """Parse ADR markdown into an ADR dataclass.

    Raises ValueError on malformed input.
    """
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    lines = markdown.split("\n")

    number = 0
    title = ""
    status = ""
    adr_date = ""
    tags: list[str] = []
    source_log: str | None = None
    supersedes: list[str] = []
    sections: dict[str, str] = {}

    current_section: str | None = None
    section_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Title
        if not title:
            m = TITLE_PATTERN.match(stripped)
            if m:
                number = int(m.group(1))
                title = m.group(2).strip()
                continue
            m = DRAFT_TITLE_PATTERN.match(stripped)
            if m:
                number = 0
                title = m.group(1).strip()
                continue

        # Section heading
        m = SECTION_PATTERN.match(stripped)
        if m:
            # Save previous section
            if current_section is not None:
                sections[current_section] = "\n".join(section_lines).strip()
            current_section = m.group(1).strip()
            section_lines = []
            continue

        # Metadata (before first section)
        if current_section is None:
            m = META_PATTERN.match(stripped)
            if m:
                key = m.group(1).strip()
                value = m.group(2).strip()
                if key == "Status":
                    status = value
                elif key == "Date":
                    adr_date = value
                elif key == "Tags":
                    tags = [t.strip() for t in value.split(",") if t.strip()]
                elif key == "Source Log":
                    source_log = value if value else None
                elif key == "Supersedes":
                    supersedes = [s.strip() for s in value.split(",") if s.strip()]
                continue

        # Content within a section
        if current_section is not None:
            section_lines.append(line)

    # Save last section
    if current_section is not None and section_lines:
        sections[current_section] = "\n".join(section_lines).strip()

    if not title:
        raise ValueError("Could not find ADR title (expected '# ADR-NNN: {title}')")

    return ADR(
        number=number,
        title=title,
        status=status,
        date=adr_date,
        tags=tags,
        source_log=source_log,
        supersedes=supersedes,
        sections=sections,
    )


def parse_adr_metadata(markdown: str) -> dict[str, Any]:
    """Parse only the ADR header metadata — stops at first ## heading.

    Returns dict with number, title, status, date, tags, source_log.
    For search performance: avoids parsing section bodies.
    """
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    lines = markdown.split("\n")

    number = 0
    title = ""
    status = ""
    adr_date = ""
    tags: list[str] = []
    source_log: str | None = None
    supersedes: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Stop at first section heading
        if SECTION_PATTERN.match(stripped):
            break

        # Title
        if not title:
            m = TITLE_PATTERN.match(stripped)
            if m:
                number = int(m.group(1))
                title = m.group(2).strip()
                continue
            m = DRAFT_TITLE_PATTERN.match(stripped)
            if m:
                number = 0
                title = m.group(1).strip()
                continue

        # Metadata
        m = META_PATTERN.match(stripped)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            if key == "Status":
                status = value
            elif key == "Date":
                adr_date = value
            elif key == "Tags":
                tags = [t.strip() for t in value.split(",") if t.strip()]
            elif key == "Source Log":
                source_log = value if value else None
            elif key == "Supersedes":
                supersedes = [s.strip() for s in value.split(",") if s.strip()]

    return {
        "number": number,
        "title": title,
        "status": status,
        "date": adr_date,
        "tags": tags,
        "source_log": source_log,
        "supersedes": supersedes,
    }


def next_adr_number(workspace_root: Path) -> int:
    """Find the next ADR number by scanning every canonical status directory."""
    max_num = 0
    for record in iter_adr_records(workspace_root):
        m = re.match(r"ADR-(\d+)", record.stem)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num + 1


def make_adr_filename(number: int, title: str) -> str:
    """Generate the filename for an ADR."""
    slug = _slugify(title)
    return f"{ADR_PREFIX}{number:03d}-{slug}.md"


def today_iso() -> str:
    """Return today's date in ISO format."""
    return date.today().isoformat()
