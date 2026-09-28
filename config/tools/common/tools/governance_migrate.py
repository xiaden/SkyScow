"""Explicit, all-or-nothing migration of a legacy ADR/ASR corpus.

A workspace that predates the workspace-local governance skills keeps its
committed records under ``artifacts/decisions/ADR-*.md`` and
``artifacts/requirements/ASR-*.md``. This module moves that corpus into the
canonical skill references and regenerates both indexes in one deterministic
pass.

The migration is explicit: it is never run at container startup and it is not a
dual-read fallback. It is all-or-nothing: every source is parsed with the
canonical parsers and every destination preflighted before anything is written,
and the legacy source corpus is removed only after the destinations and both
indexes are known-good. Any failure leaves the legacy source corpus intact.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..helpers import adr_md, asr_md
from ..helpers.governance_index import GovernanceIndexError, rebuild_governance_indexes

_LEGACY_ADR_DIR = "artifacts/decisions"
_LEGACY_ASR_DIR = "artifacts/requirements"


@dataclass(frozen=True)
class _PlanEntry:
    """One source record and its canonical destination."""

    kind: str  # "adr" | "asr"
    number: int
    source: Path
    destination: Path


def _rel(workspace_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(workspace_root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _collect_plan(
    workspace_root: Path,
) -> tuple[list[_PlanEntry], list[str], int]:
    """Parse and classify every legacy source without mutating anything.

    Returns ``(plan, errors, source_total)``. ``errors`` is empty only when
    every source is parseable, uniquely identified, canonically statused, and
    free of destination collisions.
    """
    errors: list[str] = []
    plan: list[_PlanEntry] = []
    seen_adr: set[int] = set()
    seen_asr: set[int] = set()
    destinations: set[Path] = set()

    adr_sources = adr_md.legacy_adr_records(workspace_root)
    asr_sources = asr_md.legacy_asr_records(workspace_root)
    source_total = len(adr_sources) + len(asr_sources)

    for source in adr_sources:
        rel = _rel(workspace_root, source)
        try:
            adr = adr_md.parse_adr(source.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{rel}: parse error: {exc}")
            continue
        if adr.number <= 0:
            errors.append(f"{rel}: missing canonical ADR number")
            continue
        try:
            destination = adr_md.adr_status_dir(workspace_root, adr.status) / source.name
        except ValueError as exc:
            errors.append(f"{rel}: ambiguous status: {exc}")
            continue
        if adr.number in seen_adr:
            errors.append(f"{rel}: duplicate ADR identity ADR-{adr.number:03d}")
            continue
        if destination in destinations or destination.exists():
            errors.append(f"{rel}: destination collision at {_rel(workspace_root, destination)}")
            continue
        seen_adr.add(adr.number)
        destinations.add(destination)
        plan.append(_PlanEntry("adr", adr.number, source, destination))

    for source in asr_sources:
        rel = _rel(workspace_root, source)
        try:
            asr = asr_md.parse_asr(source.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{rel}: parse error: {exc}")
            continue
        try:
            destination = asr_md.asr_status_dir(workspace_root, asr.status) / source.name
        except ValueError as exc:
            errors.append(f"{rel}: ambiguous status: {exc}")
            continue
        if asr.number in seen_asr:
            errors.append(f"{rel}: duplicate ASR identity ASR-{asr.number:04d}")
            continue
        if destination in destinations or destination.exists():
            errors.append(f"{rel}: destination collision at {_rel(workspace_root, destination)}")
            continue
        seen_asr.add(asr.number)
        destinations.add(destination)
        plan.append(_PlanEntry("asr", asr.number, source, destination))

    return plan, errors, source_total


def migrate_legacy_governance(
    workspace_root: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Migrate a legacy ADR/ASR corpus into the canonical governance skills.

    Returns a JSON-serialisable report. On failure the legacy source corpus is
    left intact; on success every legacy committed record is moved exactly once
    and both SKILL.md indexes are regenerated.
    """
    plan, errors, source_total = _collect_plan(workspace_root)
    adr_count = sum(1 for entry in plan if entry.kind == "adr")
    asr_count = sum(1 for entry in plan if entry.kind == "asr")

    if errors:
        return {
            "error": "migration_preflight_failed",
            "messages": errors,
            "planned": {"adr": adr_count, "asr": asr_count, "total": len(plan)},
            "source_total": source_total,
        }

    if not plan:
        return {
            "migrated": 0,
            "adr": 0,
            "asr": 0,
            "message": "No legacy ADR/ASR corpus found; nothing to migrate.",
        }

    manifest = [
        {
            "kind": entry.kind,
            "number": entry.number,
            "from": _rel(workspace_root, entry.source),
            "to": _rel(workspace_root, entry.destination),
        }
        for entry in plan
    ]

    if dry_run:
        return {
            "dry_run": True,
            "migrated": 0,
            "planned": {"adr": adr_count, "asr": asr_count, "total": len(plan)},
            "source_total": source_total,
            "manifest": manifest,
        }

    written: list[Path] = []
    try:
        for entry in plan:
            entry.destination.parent.mkdir(parents=True, exist_ok=True)
            entry.destination.write_bytes(entry.source.read_bytes())
            written.append(entry.destination)

        index_summary = rebuild_governance_indexes(workspace_root)

        # Verify source count == successfully classified destination count.
        if len(written) != source_total or len(plan) != source_total:
            raise GovernanceIndexError(
                f"migration count mismatch: {source_total} source(s) but "
                f"{len(plan)} classified / {len(written)} written"
            )
        for entry in plan:
            if not entry.destination.is_file():
                raise GovernanceIndexError(
                    f"missing destination {_rel(workspace_root, entry.destination)}"
                )
    except (OSError, GovernanceIndexError) as exc:
        for destination in written:
            with contextlib.suppress(OSError):
                destination.unlink()
        return {
            "error": "migration_failed",
            "message": str(exc),
            "rolled_back": len(written),
            "legacy_intact": True,
        }

    # Destinations and both indexes are known-good: retire the legacy source.
    removed: list[str] = []
    for entry in plan:
        try:
            entry.source.unlink()
        except OSError as exc:
            return {
                "error": "migration_cleanup_failed",
                "message": (
                    "records were migrated but a legacy source could not be "
                    f"removed: {_rel(workspace_root, entry.source)}: {exc}"
                ),
                "manifest": manifest,
                "index": index_summary,
            }
        removed.append(_rel(workspace_root, entry.source))

    for legacy_dir in (
        workspace_root / _LEGACY_ADR_DIR,
        workspace_root / _LEGACY_ASR_DIR,
    ):
        # Only removes the legacy directory when it is empty; drafts under
        # artifacts/decisions/drafts keep it in place.
        with contextlib.suppress(OSError):
            legacy_dir.rmdir()

    return {
        "migrated": len(plan),
        "adr": adr_count,
        "asr": asr_count,
        "removed_legacy": removed,
        "manifest": manifest,
        "index": index_summary,
    }


if __name__ == "__main__":
    import json
    import sys

    args = json.loads(sys.stdin.read())
    result = migrate_legacy_governance(
        Path(args["workspace_root"]),
        dry_run=bool(args.get("dry_run", False)),
    )
    print(json.dumps(result))
