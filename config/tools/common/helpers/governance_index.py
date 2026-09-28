"""Deterministic generation of the workspace-local governance skill indexes.

The committed ADR/ASR records under
``.opencode/skills/<skill>/references/<status>/`` are the single source of
truth for repository governance. Each governance skill's ``SKILL.md`` is a
*derived* index: it is regenerated from those records and never feeds back into
them. Only governing records appear in the loaded index — Accepted ADRs and
Active ASRs — while deprecated, superseded, and archived records stay
discoverable by path and are explicitly non-governing.

``rebuild_governance_indexes`` is the one canonical rebuild used by every ADR
and ASR corpus mutation and by the legacy migration. Both indexes are rendered
fully in memory before either is written, so a record mutation can fail closed
rather than publish a record against a stale index.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path
from typing import Any

from . import adr_md, asr_md

ADR_GOVERNING_STATUS = "Accepted"
ASR_GOVERNING_STATUS = "Active"

_SKILL_FILE = "SKILL.md"
_MAX_IDENTITY_CHARS = 160
_EMPTY_CELL = "—"


class GovernanceIndexError(RuntimeError):
    """Raised when a governance index cannot be built or written coherently."""


# --- Rendering helpers ---


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _identity(text: str) -> str:
    """Derive a concise, single-line identity from record body text."""
    collapsed = _collapse(text)
    if not collapsed:
        return _EMPTY_CELL
    if len(collapsed) <= _MAX_IDENTITY_CHARS:
        return collapsed
    return collapsed[: _MAX_IDENTITY_CHARS - 3].rstrip() + "..."


def _cell(text: str) -> str:
    """Normalize a value for a single Markdown table cell."""
    collapsed = _collapse(text)
    return collapsed.replace("|", "\\|") if collapsed else _EMPTY_CELL


def _relative(workspace_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(workspace_root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# --- ADR index ---

_ADR_FRONTMATTER = [
    "---",
    "name: architecture-decisions",
    (
        'description: "Workspace-local index of committed Architecture Decision '
        "Records (ADRs). The loaded surface lists only governing Accepted ADRs; "
        "deprecated and superseded records are historical and non-governing. Load "
        'when reading or writing ADRs or reasoning about the canonical ADR layout."'
    ),
    "---",
]

_ADR_TOOLING = [
    "- `adr_commit` writes a committed ADR to its status directory, rejects",
    "  statuses without one, and moves each declared superseded ADR from",
    "  `accepted/` to `superseded/`.",
    "- `adr_read` locates a committed record by identity across every status directory.",
    "- `governance_migrate` imports a legacy `artifacts/decisions/ADR-*.md` corpus.",
    "- Numbering scans every status directory so IDs never collide.",
]


def _load_adr_entries(workspace_root: Path) -> list[tuple[Path, adr_md.ADR]]:
    entries: list[tuple[Path, adr_md.ADR]] = []
    for path in adr_md.iter_adr_records(workspace_root):
        rel = _relative(workspace_root, path)
        try:
            adr = adr_md.parse_adr(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise GovernanceIndexError(f"cannot parse ADR record {rel}: {exc}") from exc
        try:
            expected_dir = adr_md.resolve_adr_status_dir(adr.status)
        except ValueError as exc:
            raise GovernanceIndexError(
                f"ADR record {rel} declares unmappable status {adr.status!r}"
            ) from exc
        if path.parent.name != expected_dir:
            raise GovernanceIndexError(
                f"ADR record {rel} is stored in '{path.parent.name}/' but declares "
                f"status {adr.status!r} (expected '{expected_dir}/')"
            )
        entries.append((path, adr))
    return entries


def build_adr_index(workspace_root: Path) -> tuple[str, dict[str, Any]]:
    """Render the ``architecture-decisions`` SKILL.md index and its summary."""
    entries = _load_adr_entries(workspace_root)
    governing = sorted(
        ((p, a) for p, a in entries if a.status == ADR_GOVERNING_STATUS),
        key=lambda item: item[1].number,
    )
    historical_count = len(entries) - len(governing)

    lines: list[str] = list(_ADR_FRONTMATTER)
    lines.append("")
    lines.append("# Architecture Decisions")
    lines.append("")
    lines.append(
        "Workspace-local index of **committed** Architecture Decision Records. "
        "The reference records under `references/` are the single source of truth; "
        "this file is generated from them and must not be edited by hand."
    )
    lines.append("")
    lines.append("## Status semantics")
    lines.append("")
    lines.append("| Area | Meaning |")
    lines.append("|---|---|")
    lines.append(
        "| `references/accepted/` | **Governing.** Accepted ADRs constrain "
        "current and future work. |"
    )
    lines.append(
        "| `references/deprecated/` | **Historical, non-governing.** Retained for "
        "context only. |"
    )
    lines.append(
        "| `references/superseded/` | **Historical lineage, non-governing.** Kept so "
        "replaced decisions stay traceable. |"
    )
    lines.append("")
    lines.append(
        "`Proposed` is not committed: an unapproved ADR is staged under "
        "`artifacts/decisions/drafts/` and never appears in this index."
    )
    lines.append("")
    lines.append("## Governing decisions (Accepted)")
    lines.append("")
    lines.append(
        f"**{len(governing)}** governing record(s); "
        f"{historical_count} historical record(s) under `references/`."
    )
    lines.append("")
    if governing:
        lines.append("| ID | Title | Tags | Decision | Reference |")
        lines.append("|---|---|---|---|---|")
        for path, adr in governing:
            lines.append(
                f"| ADR-{adr.number:03d} | {_cell(adr.title)} | "
                f"{_cell(', '.join(adr.tags))} | "
                f"{_identity(adr.sections.get('Decision', ''))} | "
                f"`{_relative(workspace_root, path)}` |"
            )
    else:
        lines.append("_No governing (Accepted) ADRs yet._")
    lines.append("")
    lines.append("## Reading historical records")
    lines.append("")
    lines.append(
        "Read a deprecated or superseded record only when replacing a decision, "
        "investigating its rationale or lineage, or when explicitly requested. "
        "Historical records are not governing."
    )
    lines.append("")
    lines.append("## Reference layout")
    lines.append("")
    lines.append("```")
    lines.append(".opencode/skills/architecture-decisions/")
    lines.append("├── SKILL.md")
    lines.append("└── references/")
    lines.append("    ├── accepted/     # governing")
    lines.append("    ├── deprecated/   # historical, non-governing")
    lines.append("    └── superseded/   # historical lineage, non-governing")
    lines.append("```")
    lines.append("")
    lines.append("## Tooling")
    lines.append("")
    lines.extend(_ADR_TOOLING)
    lines.append("")
    lines.append(
        "Legacy `artifacts/decisions/ADR-*.md` is not a canonical store and is not "
        "read as a fallback; a legacy-only workspace must run `governance_migrate`."
    )
    lines.append("")

    summary = {
        "path": _relative(
            workspace_root, adr_md.adr_skill_root(workspace_root) / _SKILL_FILE
        ),
        "governing": len(governing),
        "historical": historical_count,
        "total": len(entries),
    }
    return "\n".join(lines), summary


# --- ASR index ---

_ASR_FRONTMATTER = [
    "---",
    "name: system-requirements",
    (
        'description: "Workspace-local index of committed Architecturally '
        "Significant Requirements (ASRs). The loaded surface lists only governing "
        "Active ASRs; archived and superseded records are historical and "
        "non-governing. Load when reading or writing ASRs or reasoning about the "
        'canonical ASR layout."'
    ),
    "---",
]

_ASR_TOOLING = [
    "- `asr_create` writes a committed ASR to the directory for its status.",
    "- `asr_read` locates a committed record by identity across every status directory.",
    "- `governance_migrate` imports a legacy `artifacts/requirements/ASR-*.md` corpus.",
    "- Numbering scans every status directory so IDs never collide.",
]


def _load_asr_entries(workspace_root: Path) -> list[tuple[Path, asr_md.ASR]]:
    entries: list[tuple[Path, asr_md.ASR]] = []
    for path in asr_md.iter_asr_records(workspace_root):
        rel = _relative(workspace_root, path)
        try:
            asr = asr_md.parse_asr(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise GovernanceIndexError(f"cannot parse ASR record {rel}: {exc}") from exc
        try:
            expected_dir = asr_md.resolve_asr_status_dir(asr.status)
        except ValueError as exc:
            raise GovernanceIndexError(
                f"ASR record {rel} declares unmappable status {asr.status!r}"
            ) from exc
        if path.parent.name != expected_dir:
            raise GovernanceIndexError(
                f"ASR record {rel} is stored in '{path.parent.name}/' but declares "
                f"status {asr.status!r} (expected '{expected_dir}/')"
            )
        entries.append((path, asr))
    return entries


def build_asr_index(workspace_root: Path) -> tuple[str, dict[str, Any]]:
    """Render the ``system-requirements`` SKILL.md index and its summary."""
    entries = _load_asr_entries(workspace_root)
    governing = sorted(
        ((p, a) for p, a in entries if a.status == ASR_GOVERNING_STATUS),
        key=lambda item: (item[1].priority, item[1].number),
    )
    historical_count = len(entries) - len(governing)

    lines: list[str] = list(_ASR_FRONTMATTER)
    lines.append("")
    lines.append("# System Requirements")
    lines.append("")
    lines.append(
        "Workspace-local index of **committed** Architecturally Significant "
        "Requirements. The reference records under `references/` are the single "
        "source of truth; this file is generated from them and must not be edited "
        "by hand."
    )
    lines.append("")
    lines.append("## Status semantics")
    lines.append("")
    lines.append("| Area | Meaning |")
    lines.append("|---|---|")
    lines.append(
        "| `references/active/` | **Governing.** Active ASRs constrain current and "
        "future work. |"
    )
    lines.append(
        "| `references/archived/` | **Retired, non-governing.** No longer in force; "
        "kept for context. |"
    )
    lines.append(
        "| `references/superseded/` | **Replaced, non-governing.** Every "
        "`Superseded by ASR-NNNN` status lives here. |"
    )
    lines.append("")
    lines.append("## Governing requirements (Active)")
    lines.append("")
    lines.append(
        f"**{len(governing)}** governing record(s); "
        f"{historical_count} historical record(s) under `references/`."
    )
    lines.append("")
    if governing:
        lines.append("| ID | Priority | Requirement | Reference |")
        lines.append("|---|---|---|---|")
        for path, asr in governing:
            lines.append(
                f"| ASR-{asr.number:04d} | {asr.priority} | "
                f"{_identity(asr.requirement)} | "
                f"`{_relative(workspace_root, path)}` |"
            )
    else:
        lines.append("_No governing (Active) ASRs yet._")
    lines.append("")
    lines.append("## Reading historical records")
    lines.append("")
    lines.append(
        "Read an archived or superseded record only when replacing a requirement, "
        "investigating its lineage, or when explicitly requested. Historical "
        "records are not governing."
    )
    lines.append("")
    lines.append("## Reference layout")
    lines.append("")
    lines.append("```")
    lines.append(".opencode/skills/system-requirements/")
    lines.append("├── SKILL.md")
    lines.append("└── references/")
    lines.append("    ├── active/       # governing")
    lines.append("    ├── archived/     # retired, non-governing")
    lines.append("    └── superseded/   # replaced, non-governing")
    lines.append("```")
    lines.append("")
    lines.append("## Tooling")
    lines.append("")
    lines.extend(_ASR_TOOLING)
    lines.append("")
    lines.append(
        "Legacy `artifacts/requirements/ASR-*.md` is not a canonical store and is "
        "not read as a fallback; a legacy-only workspace must run "
        "`governance_migrate`."
    )
    lines.append("")

    summary = {
        "path": _relative(
            workspace_root, asr_md.asr_skill_root(workspace_root) / _SKILL_FILE
        ),
        "governing": len(governing),
        "historical": historical_count,
        "total": len(entries),
    }
    return "\n".join(lines), summary


# --- Atomic rebuild ---


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` via a same-directory temp file + replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f"{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def rebuild_governance_indexes(workspace_root: Path) -> dict[str, Any]:
    """Regenerate both governance SKILL.md indexes from the reference corpus.

    Both indexes are rendered before either is written. Returns a summary keyed
    by ``"adr"`` and ``"asr"``; raises :class:`GovernanceIndexError` when a
    record is malformed or an index cannot be written.
    """
    adr_content, adr_summary = build_adr_index(workspace_root)
    asr_content, asr_summary = build_asr_index(workspace_root)

    adr_path = adr_md.adr_skill_root(workspace_root) / _SKILL_FILE
    asr_path = asr_md.asr_skill_root(workspace_root) / _SKILL_FILE

    try:
        _atomic_write(adr_path, adr_content)
        _atomic_write(asr_path, asr_content)
    except OSError as exc:
        raise GovernanceIndexError(f"failed to write governance index: {exc}") from exc

    return {"adr": adr_summary, "asr": asr_summary}
