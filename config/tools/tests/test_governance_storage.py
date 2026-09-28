"""Focused tests for the canonical ADR/ASR governance storage foundation.

These pin the workspace-local storage model for committed records:

* ADRs — ``.opencode/skills/architecture-decisions/references/{accepted,deprecated,superseded}/``
* ASRs — ``.opencode/skills/system-requirements/references/{active,archived,superseded}/``

Coverage: path constants, deterministic status-to-directory resolution,
cross-directory lookup/enumeration, numbering that spans every status
directory, the commit/create write paths, and that the legacy
``artifacts/decisions`` / ``artifacts/requirements`` stores are neither written
to nor read as a fallback.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from common.helpers import adr_md, asr_md
from common.helpers.adr_md import ADR, generate_adr, make_adr_filename
from common.helpers.asr_md import ASR, generate_asr, make_asr_filename
from common.tools.adr_commit import adr_commit
from common.tools.adr_read import adr_read
from common.tools.adr_suggest import adr_suggest
from common.tools.asr_create import asr_create
from common.tools.asr_read import asr_read


def _write_adr(workspace: Path, *, number: int, status: str, title: str = "Use edges") -> Path:
    """Write a committed ADR into its canonical status directory."""
    adr = ADR(
        number=number,
        title=title,
        status=status,
        date="2026-01-01",
        tags=["storage"],
        sections={"Context": "ctx", "Decision": "dec", "Consequences": "con"},
    )
    target = adr_md.adr_status_dir(workspace, status) / make_adr_filename(number, title)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(generate_adr(adr), encoding="utf-8")
    return target


def _write_asr(workspace: Path, *, number: int, status: str, priority: int = 1) -> Path:
    """Write a committed ASR into its canonical status directory."""
    asr = ASR(
        number=number,
        priority=priority,
        status=status,
        created="2026-01-01",
        updated="2026-01-01",
        requirement=f"requirement {number}",
    )
    target = asr_md.asr_status_dir(workspace, status) / make_asr_filename(number)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(generate_asr(asr), encoding="utf-8")
    return target


class TestAdrStorageLayout:
    def test_skill_roots(self, workspace: Path):
        assert adr_md.adr_skill_root(workspace) == (
            workspace / ".opencode/skills/architecture-decisions"
        )
        assert adr_md.adr_references_root(workspace) == (
            workspace / ".opencode/skills/architecture-decisions/references"
        )

    def test_status_dir_mapping(self, workspace: Path):
        refs = adr_md.adr_references_root(workspace)
        assert adr_md.adr_status_dir(workspace, "Accepted") == refs / "accepted"
        assert adr_md.adr_status_dir(workspace, "Deprecated") == refs / "deprecated"
        assert adr_md.adr_status_dir(workspace, "Superseded") == refs / "superseded"

    def test_proposed_has_no_committed_directory(self, workspace: Path):
        with pytest.raises(ValueError):
            adr_md.adr_status_dir(workspace, "Proposed")

    def test_iter_and_find_across_status_dirs(self, workspace: Path):
        accepted = _write_adr(workspace, number=1, status="Accepted")
        deprecated = _write_adr(workspace, number=2, status="Deprecated")
        superseded = _write_adr(workspace, number=3, status="Superseded")

        assert set(adr_md.iter_adr_records(workspace)) == {accepted, deprecated, superseded}
        assert adr_md.find_adr_number(workspace, 2) == deprecated
        assert adr_md.find_adr_number(workspace, 9) is None

    def test_next_number_scans_every_status_dir(self, workspace: Path):
        _write_adr(workspace, number=1, status="Accepted")
        _write_adr(workspace, number=5, status="Deprecated")
        assert adr_md.next_adr_number(workspace) == 6


class TestAdrCommitStorage:
    def _commit(self, workspace: Path, status: str = "Accepted") -> dict:
        return adr_commit(
            title="Use edges",
            status=status,
            tags=["storage"],
            context="ctx",
            decision="dec",
            consequences="con",
            workspace_root=workspace,
        )

    def test_accepted_commit_writes_references_accepted(self, workspace: Path):
        result = self._commit(workspace, "Accepted")
        assert "output" in result, result
        payload = json.loads(result["output"])
        assert payload["path"] == (
            ".opencode/skills/architecture-decisions/references/accepted/ADR-001-use-edges.md"
        )
        assert (workspace / payload["path"]).is_file()
        assert not (workspace / "artifacts/decisions/ADR-001-use-edges.md").exists()

    def test_deprecated_commit_writes_references_deprecated(self, workspace: Path):
        result = self._commit(workspace, "Deprecated")
        payload = json.loads(result["output"])
        assert payload["path"].endswith("references/deprecated/ADR-001-use-edges.md")

    def test_proposed_commit_is_rejected_and_writes_nothing(self, workspace: Path):
        result = self._commit(workspace, "Proposed")
        assert result["error"] == "uncommittable_status"
        assert not adr_md.adr_references_root(workspace).exists()

    def test_commit_numbering_spans_status_dirs(self, workspace: Path):
        _write_adr(workspace, number=4, status="Deprecated")
        result = self._commit(workspace, "Accepted")
        payload = json.loads(result["output"])
        assert payload["number"] == 5


class TestAdrDraftStaging:
    def test_suggest_stages_outside_the_skill(self, workspace: Path):
        result = adr_suggest(
            title="Stage me",
            status="Proposed",
            tags=["storage"],
            context="ctx",
            decision="dec",
            consequences="con",
            workspace_root=workspace,
        )
        payload = json.loads(result["output"])
        assert payload["draft_path"] == "artifacts/decisions/drafts/DRAFT-stage-me.md"
        assert (workspace / payload["draft_path"]).is_file()
        # An unapproved draft must not create the governing references tree.
        assert not adr_md.adr_references_root(workspace).exists()

    def test_commit_from_draft_lands_in_status_dir_and_consumes_draft(self, workspace: Path):
        suggested = adr_suggest(
            title="Stage me",
            status="Proposed",
            tags=["storage"],
            context="ctx",
            decision="dec",
            consequences="con",
            workspace_root=workspace,
        )
        draft_id = json.loads(suggested["output"])["draft_id"]

        result = adr_commit(draft_id=draft_id, status="Accepted", workspace_root=workspace)
        payload = json.loads(result["output"])
        assert payload["path"].endswith("references/accepted/ADR-001-stage-me.md")
        assert (workspace / payload["path"]).is_file()
        assert not list((workspace / "artifacts/decisions/drafts").glob("DRAFT-*.md"))


class TestAdrReadSearch:
    def test_read_locates_across_status_dirs(self, workspace: Path):
        _write_adr(workspace, number=7, status="Superseded")
        result = adr_read(name="7", workspace_root=workspace)
        payload = json.loads(result["output"])
        assert payload["number"] == 7
        assert payload["path"].endswith("references/superseded/ADR-007-use-edges.md")

    def test_read_missing_reports_references_root(self, workspace: Path):
        result = adr_read(name="42", workspace_root=workspace)
        assert result["error"] == "adr_not_found"
        assert result["searched"] == ".opencode/skills/architecture-decisions/references"


class TestAsrStorageLayout:
    def test_skill_roots(self, workspace: Path):
        assert asr_md.asr_skill_root(workspace) == workspace / ".opencode/skills/system-requirements"
        assert asr_md.asr_references_root(workspace) == (
            workspace / ".opencode/skills/system-requirements/references"
        )

    def test_status_dir_mapping(self, workspace: Path):
        refs = asr_md.asr_references_root(workspace)
        assert asr_md.asr_status_dir(workspace, "Active") == refs / "active"
        assert asr_md.asr_status_dir(workspace, "Archived") == refs / "archived"
        assert asr_md.asr_status_dir(workspace, "Superseded by ASR-0002") == refs / "superseded"

    def test_invalid_status_raises(self, workspace: Path):
        with pytest.raises(ValueError):
            asr_md.asr_status_dir(workspace, "Bogus")

    def test_iter_and_find_across_status_dirs(self, workspace: Path):
        active = _write_asr(workspace, number=1, status="Active")
        archived = _write_asr(workspace, number=2, status="Archived")

        assert set(asr_md.iter_asr_records(workspace)) == {active, archived}
        assert asr_md.find_asr_number(workspace, 2) == archived
        assert asr_md.find_asr_number(workspace, 9) is None


class TestAsrCreateReadSearch:
    def test_create_writes_active_then_superseded(self, workspace: Path):
        first = asr_create(priority=1, requirement="r1", workspace_root=workspace)
        assert json.loads(first["output"])["path"].endswith("references/active/ASR-0001.md")

        second = asr_create(
            priority=0,
            requirement="r2",
            status="Superseded by ASR-0001",
            workspace_root=workspace,
        )
        assert json.loads(second["output"])["path"].endswith(
            "references/superseded/ASR-0002.md"
        )
        assert not (workspace / "artifacts/requirements/ASR-0001.md").exists()

    def test_next_number_scans_every_status_dir(self, workspace: Path):
        _write_asr(workspace, number=3, status="Archived")
        result = asr_create(priority=1, requirement="r", workspace_root=workspace)
        assert json.loads(result["output"])["number"] == 4

    def test_read_locates_across_status_dirs(self, workspace: Path):
        _write_asr(workspace, number=2, status="Superseded by ASR-0001")
        result = asr_read(name="ASR-0002", workspace_root=workspace)
        payload = json.loads(result["output"])
        assert payload["number"] == 2
        assert payload["path"].endswith("references/superseded/ASR-0002.md")


class TestAdrSupersession:
    def _commit_superseding(self, workspace: Path, tokens: list[str]) -> dict:
        return adr_commit(
            title="Use nodes",
            status="Accepted",
            tags=["storage"],
            context="ctx",
            decision="dec",
            consequences="con",
            supersedes=tokens,
            workspace_root=workspace,
        )

    def test_supersession_moves_prior_accepted_out_of_accepted(self, workspace: Path):
        old = _write_adr(workspace, number=1, status="Accepted", title="Use edges")

        result = self._commit_superseding(workspace, ["ADR-001"])
        payload = json.loads(result["output"])

        moved = adr_md.adr_status_dir(workspace, "Superseded") / "ADR-001-use-edges.md"
        assert not old.exists()
        assert moved.is_file()
        assert payload["superseded"] == [
            {
                "number": 1,
                "from": (
                    ".opencode/skills/architecture-decisions/references/"
                    "accepted/ADR-001-use-edges.md"
                ),
                "to": (
                    ".opencode/skills/architecture-decisions/references/"
                    "superseded/ADR-001-use-edges.md"
                ),
            }
        ]

        read = json.loads(adr_read(name="1", workspace_root=workspace)["output"])
        assert read["number"] == 1
        assert read["status"] == "Superseded"
        assert read["path"].endswith("references/superseded/ADR-001-use-edges.md")

    def test_supersession_leaves_one_canonical_copy(self, workspace: Path):
        _write_adr(workspace, number=1, status="Accepted", title="Use edges")
        self._commit_superseding(workspace, ["1"])

        copies = sorted(adr_md.adr_references_root(workspace).glob("**/ADR-001-*.md"))
        assert len(copies) == 1
        assert copies[0].parent.name == "superseded"
        assert not (
            adr_md.adr_status_dir(workspace, "Accepted") / "ADR-001-use-edges.md"
        ).exists()

    def test_unknown_supersede_target_is_rejected_without_writing(self, workspace: Path):
        result = self._commit_superseding(workspace, ["ADR-042"])
        assert result["error"] == "supersedes_not_found"
        assert not adr_md.adr_references_root(workspace).exists()

    def test_malformed_supersede_token_is_rejected(self, workspace: Path):
        result = self._commit_superseding(workspace, ["not-an-adr"])
        assert result["error"] == "invalid_supersedes"
        assert not adr_md.adr_references_root(workspace).exists()

    def test_supersede_target_already_superseded_is_noop(self, workspace: Path):
        existing = _write_adr(workspace, number=1, status="Superseded", title="Use edges")
        result = self._commit_superseding(workspace, ["ADR-001"])
        payload = json.loads(result["output"])
        assert "superseded" not in payload
        assert existing.is_file()


class TestAsrArchivedPlacement:
    def test_create_archived_lands_in_archived(self, workspace: Path):
        result = asr_create(
            priority=2, requirement="r", status="Archived", workspace_root=workspace
        )
        assert json.loads(result["output"])["path"].endswith(
            "references/archived/ASR-0001.md"
        )

    def test_read_archived_across_status_dirs(self, workspace: Path):
        _write_asr(workspace, number=4, status="Archived")
        result = asr_read(name="ASR-0004", workspace_root=workspace)
        payload = json.loads(result["output"])
        assert payload["status"] == "Archived"
        assert payload["path"].endswith("references/archived/ASR-0004.md")


class TestAdrDeprecatedRead:
    def test_read_deprecated_across_status_dirs(self, workspace: Path):
        _write_adr(workspace, number=8, status="Deprecated", title="Use edges")
        result = adr_read(name="ADR-008", workspace_root=workspace)
        payload = json.loads(result["output"])
        assert payload["status"] == "Deprecated"
        assert payload["path"].endswith("references/deprecated/ADR-008-use-edges.md")


class TestUnknownIdentity:
    def test_adr_read_unknown_number_fails_deterministically(self, workspace: Path):
        result = adr_read(name="999", workspace_root=workspace)
        assert result["error"] == "adr_not_found"
        assert result["searched"] == ".opencode/skills/architecture-decisions/references"

    def test_adr_read_unknown_slug_fails(self, workspace: Path):
        result = adr_read(name="ADR-999", workspace_root=workspace)
        assert result["error"] == "adr_not_found"

    def test_asr_read_unknown_number_fails_deterministically(self, workspace: Path):
        result = asr_read(name="ASR-0999", workspace_root=workspace)
        assert result["error"] == "asr_not_found"
        assert result["searched"] == ".opencode/skills/system-requirements/references"