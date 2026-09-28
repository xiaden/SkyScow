"""Focused tests for governance index generation and legacy migration.

Coverage:

* deterministic governing indexes (Accepted ADRs / Active ASRs);
* historical records excluded from the governing index;
* rebuild stability and reference-derivation direction;
* an explicit, all-or-nothing legacy ``artifacts/decisions`` /
  ``artifacts/requirements`` migration: mixed statuses, ID preservation,
  destination collisions, malformed records, duplicate identities, ambiguous
  statuses, source removal on success, source retention on failure, and
  exactly-one destination per source.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from common.helpers import adr_md, asr_md
from common.helpers.adr_md import ADR, generate_adr, make_adr_filename
from common.helpers.asr_md import ASR, generate_asr, make_asr_filename
from common.helpers.governance_index import (
    GovernanceIndexError,
    rebuild_governance_indexes,
)
from common.tools.adr_commit import adr_commit
from common.tools.adr_read import adr_read
from common.tools.asr_create import asr_create
from common.tools.asr_read import asr_read
from common.tools.governance_migrate import migrate_legacy_governance

ADR_SKILL = ".opencode/skills/architecture-decisions/SKILL.md"
ASR_SKILL = ".opencode/skills/system-requirements/SKILL.md"


def _read(workspace: Path, rel: str) -> str:
    return (workspace / rel).read_text(encoding="utf-8")


def _write_adr(
    workspace: Path,
    *,
    number: int,
    status: str,
    title: str = "Use edges",
    tags: tuple[str, ...] = ("storage",),
    decision: str | None = None,
) -> Path:
    adr = ADR(
        number=number,
        title=title,
        status=status,
        date="2026-01-01",
        tags=list(tags),
        sections={
            "Context": "ctx",
            "Decision": decision or f"decision {number}",
            "Consequences": "con",
        },
    )
    target = adr_md.adr_status_dir(workspace, status) / make_adr_filename(number, title)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(generate_adr(adr), encoding="utf-8")
    return target


def _write_asr(
    workspace: Path,
    *,
    number: int,
    status: str,
    priority: int = 1,
    requirement: str | None = None,
) -> Path:
    asr = ASR(
        number=number,
        priority=priority,
        status=status,
        created="2026-01-01",
        updated="2026-01-01",
        requirement=requirement or f"requirement {number}",
    )
    target = asr_md.asr_status_dir(workspace, status) / make_asr_filename(number)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(generate_asr(asr), encoding="utf-8")
    return target


def _write_legacy_adr(
    workspace: Path, *, number: int, status: str, title: str = "Legacy edges"
) -> Path:
    adr = ADR(
        number=number,
        title=title,
        status=status,
        date="2026-01-01",
        tags=["legacy"],
        sections={"Context": "c", "Decision": "d", "Consequences": "e"},
    )
    target = workspace / "artifacts/decisions" / make_adr_filename(number, title)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(generate_adr(adr), encoding="utf-8")
    return target


def _write_legacy_asr(workspace: Path, *, number: int, status: str = "Active") -> Path:
    asr = ASR(
        number=number,
        priority=1,
        status=status,
        created="2026-01-01",
        updated="2026-01-01",
        requirement=f"legacy requirement {number}",
    )
    target = workspace / "artifacts/requirements" / make_asr_filename(number)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(generate_asr(asr), encoding="utf-8")
    return target


class TestGoverningIndex:
    def test_adr_index_lists_only_accepted(self, workspace: Path):
        _write_adr(workspace, number=1, status="Accepted", title="Use edges")
        _write_adr(workspace, number=2, status="Deprecated", title="Use nodes")
        _write_adr(workspace, number=3, status="Superseded", title="Use tables")

        summary = rebuild_governance_indexes(workspace)
        text = _read(workspace, ADR_SKILL)

        assert "ADR-001" in text
        assert "ADR-002" not in text
        assert "ADR-003" not in text
        assert "references/accepted/ADR-001-use-edges.md" in text
        assert summary["adr"] == {
            "path": ADR_SKILL,
            "governing": 1,
            "historical": 2,
            "total": 3,
        }

    def test_asr_index_lists_only_active(self, workspace: Path):
        _write_asr(workspace, number=1, status="Active")
        _write_asr(workspace, number=2, status="Archived")
        _write_asr(workspace, number=3, status="Superseded by ASR-0001")

        summary = rebuild_governance_indexes(workspace)
        text = _read(workspace, ASR_SKILL)

        assert "ASR-0001" in text
        assert "ASR-0002" not in text
        assert "ASR-0003" not in text
        assert summary["asr"]["governing"] == 1
        assert summary["asr"]["historical"] == 2

    def test_index_includes_navigation_metadata(self, workspace: Path):
        _write_adr(
            workspace,
            number=5,
            status="Accepted",
            title="Adopt widget",
            tags=("widget", "protocol"),
            decision="Adopt the widget protocol for all transports.",
        )
        rebuild_governance_indexes(workspace)
        text = _read(workspace, ADR_SKILL)

        assert "ADR-005" in text
        assert "Adopt widget" in text
        assert "widget" in text and "protocol" in text
        assert "Adopt the widget protocol" in text
        assert (
            "`.opencode/skills/architecture-decisions/references/accepted/"
            "ADR-005-adopt-widget.md`" in text
        )

    def test_explains_status_semantics(self, workspace: Path):
        rebuild_governance_indexes(workspace)
        adr_text = _read(workspace, ADR_SKILL)
        asr_text = _read(workspace, ASR_SKILL)

        assert "governing" in adr_text.lower()
        assert "non-governing" in adr_text.lower()
        assert "references/superseded/" in adr_text
        assert "retired" in asr_text.lower()
        assert "replaced" in asr_text.lower()

    def test_empty_index_is_explicit(self, workspace: Path):
        rebuild_governance_indexes(workspace)
        assert "_No governing (Accepted) ADRs yet._" in _read(workspace, ADR_SKILL)
        assert "_No governing (Active) ASRs yet._" in _read(workspace, ASR_SKILL)

    def test_rebuild_is_stable(self, workspace: Path):
        _write_adr(workspace, number=1, status="Accepted")
        _write_asr(workspace, number=1, status="Active")

        first = rebuild_governance_indexes(workspace)
        adr_bytes = (workspace / ADR_SKILL).read_bytes()
        asr_bytes = (workspace / ASR_SKILL).read_bytes()

        second = rebuild_governance_indexes(workspace)

        assert first == second
        assert (workspace / ADR_SKILL).read_bytes() == adr_bytes
        assert (workspace / ASR_SKILL).read_bytes() == asr_bytes

    def test_index_derived_from_references_not_vice_versa(self, workspace: Path):
        path = _write_adr(workspace, number=1, status="Accepted", title="Original")
        rebuild_governance_indexes(workspace)
        skill = workspace / ADR_SKILL
        assert "Original" in skill.read_text(encoding="utf-8")

        # Change only the reference record. The generated index is stale until
        # it is rebuilt.
        before = skill.read_text(encoding="utf-8")
        renamed = ADR(
            number=1,
            title="Renamed",
            status="Accepted",
            date="2026-01-01",
            tags=["storage"],
            sections={"Context": "ctx", "Decision": "renamed decision", "Consequences": "con"},
        )
        path.write_text(generate_adr(renamed), encoding="utf-8")
        assert skill.read_text(encoding="utf-8") == before

        rebuild_governance_indexes(workspace)
        after = skill.read_text(encoding="utf-8")
        assert "Renamed" in after

        # Rebuilding never mutates the reference corpus.
        assert path.read_text(encoding="utf-8") == generate_adr(renamed)

        # The index is reproducible: delete it and rebuild identical bytes.
        skill.unlink()
        rebuild_governance_indexes(workspace)
        assert skill.read_text(encoding="utf-8") == after

    def test_rebuild_rejects_malformed_record(self, workspace: Path):
        bad = (
            adr_md.adr_status_dir(workspace, "Accepted") / "ADR-001-bad.md"
        )
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("# not an adr\n**Status:** Accepted\n", encoding="utf-8")

        with pytest.raises(GovernanceIndexError):
            rebuild_governance_indexes(workspace)

    def test_rebuild_rejects_status_directory_mismatch(self, workspace: Path):
        path = adr_md.adr_status_dir(workspace, "Accepted") / "ADR-001-mismatch.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            generate_adr(
                ADR(
                    number=1,
                    title="Mismatch",
                    status="Deprecated",
                    date="2026-01-01",
                    tags=["x"],
                    sections={"Context": "c", "Decision": "d", "Consequences": "e"},
                )
            ),
            encoding="utf-8",
        )
        with pytest.raises(GovernanceIndexError):
            rebuild_governance_indexes(workspace)


class TestMutationRegeneratesIndex:
    def test_adr_commit_regenerates_index(self, workspace: Path):
        result = adr_commit(
            title="Use edges",
            status="Accepted",
            tags=["storage"],
            context="ctx",
            decision="dec",
            consequences="con",
            workspace_root=workspace,
        )
        assert "output" in result, result
        payload = json.loads(result["output"])
        assert payload["index"]["adr"]["governing"] == 1
        assert "ADR-001" in _read(workspace, ADR_SKILL)

    def test_asr_create_regenerates_index(self, workspace: Path):
        result = asr_create(priority=1, requirement="r", workspace_root=workspace)
        payload = json.loads(result["output"])
        assert payload["index"]["asr"]["governing"] == 1
        assert "ASR-0001" in _read(workspace, ASR_SKILL)

    def test_supersession_moves_record_out_of_governing_index(self, workspace: Path):
        _write_adr(workspace, number=1, status="Accepted", title="Use edges")

        result = adr_commit(
            title="Use nodes",
            status="Accepted",
            tags=["storage"],
            context="ctx",
            decision="dec",
            consequences="con",
            supersedes=["ADR-001"],
            workspace_root=workspace,
        )
        payload = json.loads(result["output"])
        assert payload["superseded"][0]["number"] == 1

        text = _read(workspace, ADR_SKILL)
        assert "ADR-002" in text
        assert "ADR-001" not in text

    def test_adr_commit_fails_closed_when_index_cannot_rebuild(self, workspace: Path):
        bad = adr_md.adr_status_dir(workspace, "Deprecated") / "ADR-001-bad.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("# not an adr\n", encoding="utf-8")

        result = adr_commit(
            title="Use edges",
            status="Accepted",
            tags=["storage"],
            context="ctx",
            decision="dec",
            consequences="con",
            workspace_root=workspace,
        )
        assert result["error"] == "index_rebuild_failed"
        assert not list(adr_md.adr_status_dir(workspace, "Accepted").glob("ADR-*.md"))

    def test_asr_create_fails_closed_when_index_cannot_rebuild(self, workspace: Path):
        bad = adr_md.adr_status_dir(workspace, "Accepted") / "ADR-001-bad.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("# not an adr\n", encoding="utf-8")

        result = asr_create(priority=1, requirement="r", workspace_root=workspace)
        assert result["error"] == "index_rebuild_failed"
        assert not list(asr_md.asr_references_root(workspace).glob("**/ASR-*.md"))


class TestLegacyOnlyWorkspace:
    def test_adr_read_reports_migration_required(self, workspace: Path):
        _write_legacy_adr(workspace, number=1, status="Accepted")
        result = adr_read(name="1", workspace_root=workspace)
        assert result["error"] == "migration_required"
        assert result["legacy_dir"] == "artifacts/decisions"

    def test_asr_read_reports_migration_required(self, workspace: Path):
        _write_legacy_asr(workspace, number=1, status="Active")
        result = asr_read(name="1", workspace_root=workspace)
        assert result["error"] == "migration_required"
        assert result["legacy_dir"] == "artifacts/requirements"


class TestLegacyMigration:
    def test_mixed_status_migration(self, workspace: Path):
        legacy_adr_ok = _write_legacy_adr(workspace, number=1, status="Accepted")
        legacy_adr_hist = _write_legacy_adr(workspace, number=2, status="Deprecated")
        legacy_asr_ok = _write_legacy_asr(workspace, number=1, status="Active")
        legacy_asr_hist = _write_legacy_asr(
            workspace, number=2, status="Superseded by ASR-0001"
        )

        report = migrate_legacy_governance(workspace)

        assert report["migrated"] == 4
        assert report["adr"] == 2
        assert report["asr"] == 2
        assert not legacy_adr_ok.exists()
        assert not legacy_adr_hist.exists()
        assert not legacy_asr_ok.exists()
        assert not legacy_asr_hist.exists()

        assert (adr_md.adr_status_dir(workspace, "Accepted") / legacy_adr_ok.name).is_file()
        assert (
            adr_md.adr_status_dir(workspace, "Deprecated") / legacy_adr_hist.name
        ).is_file()
        assert (asr_md.asr_status_dir(workspace, "Active") / legacy_asr_ok.name).is_file()
        assert (
            asr_md.asr_status_dir(workspace, "Superseded by ASR-0001")
            / legacy_asr_hist.name
        ).is_file()

        adr_text = _read(workspace, ADR_SKILL)
        asr_text = _read(workspace, ASR_SKILL)
        assert "ADR-001" in adr_text and "ADR-002" not in adr_text
        assert "ASR-0001" in asr_text and "ASR-0002" not in asr_text

    def test_ids_preserved(self, workspace: Path):
        _write_legacy_adr(workspace, number=7, status="Accepted", title="Seven")
        _write_legacy_asr(workspace, number=42, status="Active")

        migrate_legacy_governance(workspace)

        adr_matches = list(
            adr_md.adr_references_root(workspace).glob("**/ADR-007-*.md")
        )
        assert [p.name for p in adr_matches] == ["ADR-007-seven.md"]
        asr_matches = list(asr_md.asr_references_root(workspace).glob("**/ASR-0042.md"))
        assert len(asr_matches) == 1

    def test_exactly_one_destination_per_source(self, workspace: Path):
        sources = [
            _write_legacy_adr(workspace, number=number, status=status)
            for number, status in (
                (1, "Accepted"),
                (2, "Deprecated"),
                (3, "Superseded"),
            )
        ]
        report = migrate_legacy_governance(workspace)
        assert report["migrated"] == 3

        for source in sources:
            matches = list(
                adr_md.adr_references_root(workspace).glob(f"**/{source.name}")
            )
            assert len(matches) == 1

    def test_success_removes_legacy_source(self, workspace: Path):
        legacy = _write_legacy_adr(workspace, number=1, status="Accepted")

        report = migrate_legacy_governance(workspace)

        assert report["migrated"] == 1
        assert report["removed_legacy"] == ["artifacts/decisions/ADR-001-legacy-edges.md"]
        assert not legacy.exists()
        assert not (workspace / "artifacts/decisions").exists()

    def test_dry_run_does_not_mutate(self, workspace: Path):
        legacy = _write_legacy_adr(workspace, number=1, status="Accepted")

        report = migrate_legacy_governance(workspace, dry_run=True)

        assert report["dry_run"] is True
        assert report["migrated"] == 0
        assert legacy.is_file()
        assert not adr_md.adr_references_root(workspace).exists()

    def test_no_legacy_corpus_is_a_noop(self, workspace: Path):
        report = migrate_legacy_governance(workspace)
        assert report["migrated"] == 0
        assert not adr_md.adr_references_root(workspace).exists()

    def test_destination_collision_fails_and_leaves_source(self, workspace: Path):
        _write_adr(workspace, number=1, status="Accepted", title="Legacy edges")
        legacy = _write_legacy_adr(workspace, number=1, status="Accepted")

        report = migrate_legacy_governance(workspace)

        assert report["error"] == "migration_preflight_failed"
        assert any("collision" in message for message in report["messages"])
        assert legacy.is_file()
        assert not (workspace / ADR_SKILL).exists()

    def test_malformed_record_fails_and_leaves_source(self, workspace: Path):
        bad = workspace / "artifacts/decisions/ADR-001-broken.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("# not an ADR\n", encoding="utf-8")

        report = migrate_legacy_governance(workspace)

        assert report["error"] == "migration_preflight_failed"
        assert bad.is_file()
        assert not adr_md.adr_references_root(workspace).exists()
        assert not asr_md.asr_references_root(workspace).exists()

    def test_duplicate_identity_fails_and_leaves_source(self, workspace: Path):
        first = _write_legacy_adr(workspace, number=1, status="Accepted", title="A")
        second = _write_legacy_adr(workspace, number=1, status="Deprecated", title="B")

        report = migrate_legacy_governance(workspace)

        assert report["error"] == "migration_preflight_failed"
        assert any("duplicate" in message.lower() for message in report["messages"])
        assert first.is_file() and second.is_file()

    def test_ambiguous_status_fails_and_leaves_source(self, workspace: Path):
        legacy = workspace / "artifacts/decisions/ADR-001-proposed.md"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(
            generate_adr(
                ADR(
                    number=1,
                    title="Proposed thing",
                    status="Proposed",
                    date="2026-01-01",
                    tags=["x"],
                    sections={"Context": "c", "Decision": "d", "Consequences": "e"},
                )
            ),
            encoding="utf-8",
        )

        report = migrate_legacy_governance(workspace)

        assert report["error"] == "migration_preflight_failed"
        assert any("ambiguous status" in message for message in report["messages"])
        assert legacy.is_file()

    def test_index_failure_rolls_back_and_leaves_legacy(self, workspace: Path):
        legacy = _write_legacy_adr(workspace, number=2, status="Accepted")

        # A malformed canonical record makes the index rebuild fail after the
        # destination write, exercising the rollback path.
        bad = adr_md.adr_status_dir(workspace, "Accepted") / "ADR-001-bad.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("# not an adr\n", encoding="utf-8")

        report = migrate_legacy_governance(workspace)

        assert report["error"] == "migration_failed"
        assert legacy.is_file()
        assert not (adr_md.adr_status_dir(workspace, "Accepted") / legacy.name).exists()
