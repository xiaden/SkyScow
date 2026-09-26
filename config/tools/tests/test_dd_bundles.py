"""Focused tests for per-DD bundle lifecycle and module boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from common.helpers.dd_md import (
    DD_STATUSES,
    DesignDocument,
    dd_bundle_slug,
    generate_dd,
    parse_dd,
    validate_slug,
    validate_status,
)
from common.tools.dd_archive import dd_archive
from common.tools.dd_create import dd_create
from common.tools.dd_read import dd_read


def create_args(workspace: Path, slug: str = "sample-dd") -> dict[str, object]:
    return {
        "title": "Sample DD",
        "slug": slug,
        "status": "Draft",
        "author": "tester",
        "scope": "scope",
        "problem_statement": "problem",
        "architecture": "architecture",
        "workspace_root": workspace,
    }


def test_create_writes_bundle_root(workspace):
    result = dd_create(**create_args(workspace))
    assert json.loads(result["output"])["path"] == "artifacts/designs/pending/sample-dd/DD.md"
    assert (workspace / "artifacts/designs/pending/sample-dd/DD.md").exists()


def test_read_prefers_pending_and_returns_bundle_path(workspace):
    dd_create(**create_args(workspace))
    completed = workspace / "artifacts/designs/completed/sample-dd/DD.md"
    completed.parent.mkdir(parents=True)
    completed.write_text("# Completed — Design Document\n**Status:** Completed\n", encoding="utf-8")
    result = json.loads(dd_read("DD-sample-dd.md", workspace_root=workspace)["output"])
    assert result["location"] == "pending"
    assert result["path"] == "artifacts/designs/pending/sample-dd/DD.md"


def test_archive_moves_complete_bundle_and_updates_status(workspace):
    dd_create(**create_args(workspace))
    bundle = workspace / "artifacts/designs/pending/sample-dd"
    (bundle / "README.md").write_text("bundle\n", encoding="utf-8")
    (bundle / "PART-A-scope.md").write_text("part\n", encoding="utf-8")
    result = json.loads(dd_archive("sample-dd", workspace_root=workspace)["output"])
    destination = workspace / "artifacts/designs/completed/sample-dd"
    assert result["path"] == "artifacts/designs/completed/sample-dd/DD.md"
    assert not bundle.exists()
    assert (destination / "README.md").exists()
    assert "**Status:** Completed" in (destination / "DD.md").read_text(encoding="utf-8")


def test_archive_ignores_pending_legacy_plans(workspace):
    dd_create(**create_args(workspace))
    pending_plan = workspace / "artifacts/plans/pending/TASK-sample-dd-build.md"
    pending_plan.parent.mkdir(parents=True)
    pending_plan.write_text("plan", encoding="utf-8")
    assert "output" in dd_archive("sample-dd", workspace_root=workspace)


def test_archive_rejects_pending_dag_and_accepts_completed_dag(workspace):
    linked = [{
        "title": "DAG",
        "path": "artifacts/change-dags/pending/linked/DAG.json",
        "description": "linked change dag",
    }]
    dd_create(**create_args(workspace), related_documents=linked)
    dag = workspace / "artifacts/change-dags/pending/linked/DAG.json"
    dag.parent.mkdir(parents=True)
    dag.write_text("{}", encoding="utf-8")

    rejected = dd_archive("sample-dd", workspace_root=workspace)
    assert rejected["error"] == "linked_dags_incomplete"
    assert rejected["linked_dags"] == ["linked"]
    assert (workspace / "artifacts/designs/pending/sample-dd/DD.md").is_file()

    (workspace / "artifacts/change-dags/completed").mkdir(parents=True, exist_ok=True)
    dag.parent.rename(workspace / "artifacts/change-dags/completed/linked")

    archived = dd_archive("sample-dd", workspace_root=workspace)
    assert json.loads(archived["output"])["archived"] is True
    assert (workspace / "artifacts/designs/completed/sample-dd/DD.md").is_file()
    assert not (workspace / "artifacts/designs/pending/sample-dd").exists()


def test_archive_ignores_unlinked_pending_dag(workspace):
    dd_create(**create_args(workspace))
    dag = workspace / "artifacts/change-dags/pending/unlinked/DAG.json"
    dag.parent.mkdir(parents=True)
    dag.write_text("{}", encoding="utf-8")
    result = dd_archive("sample-dd", workspace_root=workspace)
    assert json.loads(result["output"])["archived"] is True

def test_create_returns_invalid_input_error_envelopes(workspace):
    invalid_inputs = (
        ({"slug": "Invalid-Slug"}, "invalid_slug"),
        ({"status": "In Review"}, "invalid_status"),
        ({"title": "   "}, "invalid_title"),
    )

    for overrides, expected_error in invalid_inputs:
        args = create_args(workspace)
        args.update(overrides)
        result = dd_create(**args)
        assert result["error"] == expected_error
        assert "message" in result
        assert "output" not in result

    assert not (workspace / "artifacts/designs/pending").exists()


def test_slug_and_status_validation_preserve_contracts():
    assert validate_slug("valid-slug") is None
    assert validate_slug("a") is not None
    assert validate_slug("Invalid-slug") is not None
    assert validate_slug("bad_") is not None
    assert validate_slug("") == "Slug cannot be empty"

    for status in ("Draft", "Approved", "Completed", "Superseded", "Rejected"):
        assert status in DD_STATUSES
        assert validate_status(status) is None
    assert validate_status("In Review") is not None
    assert validate_status("Accepted") is not None


def test_bundle_slug_accepts_supported_name_forms_and_rejects_invalid_names():
    assert dd_bundle_slug("sample-dd") == "sample-dd"
    assert dd_bundle_slug("DD-sample-dd") == "sample-dd"
    assert dd_bundle_slug("DD-sample-dd.md") == "sample-dd"

    for invalid in ("../sample-dd", "DD-bad_name.md", "DD-a.md"):
        try:
            dd_bundle_slug(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected invalid bundle name: {invalid}")


def test_generated_bundle_markdown_round_trips_through_parser():
    document = DesignDocument(
        title="Round Trip",
        status="Approved",
        author="tester",
        created="2026-04-01",
        revised="2026-04-02",
        related_documents=[{"title": "Plan", "path": "plan.md", "description": "related"}],
        sections={"Scope": "bundle scope", "Constraints": "keep status"},
    )

    parsed = parse_dd(generate_dd(document))
    assert parsed == document


def test_read_resolves_completed_bundle_when_pending_is_absent(workspace):
    dd_create(**create_args(workspace))
    pending = workspace / "artifacts/designs/pending/sample-dd"
    completed = workspace / "artifacts/designs/completed/sample-dd"
    completed.parent.mkdir(parents=True)
    pending.rename(completed)

    result = json.loads(dd_read("sample-dd", workspace_root=workspace)["output"])
    assert result["location"] == "completed"
    assert result["path"] == "artifacts/designs/completed/sample-dd/DD.md"
    assert result["title"] == "Sample DD"


def test_real_module_boundary_create_read_archive(tmp_path):
    workspace = tmp_path / "module-workspace"
    workspace.mkdir()
    args = create_args(workspace)
    args["workspace_root"] = str(workspace)
    env = {"PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PATH": __import__("os").environ["PATH"]}
    create = subprocess.run(
        [sys.executable, "-m", "common.tools.dd_create"],
        input=json.dumps(args), text=True, capture_output=True, check=True, env=env,
    )
    assert json.loads(json.loads(create.stdout)["output"])["path"].endswith("sample-dd/DD.md")
    read = subprocess.run(
        [sys.executable, "-m", "common.tools.dd_read"],
        input=json.dumps({"name": "sample-dd", "workspace_root": str(workspace)}),
        text=True, capture_output=True, check=True, env=env,
    )
    assert json.loads(json.loads(read.stdout)["output"])["location"] == "pending"
    archive = subprocess.run(
        [sys.executable, "-m", "common.tools.dd_archive"],
        input=json.dumps({"name": "sample-dd", "workspace_root": str(workspace)}),
        text=True, capture_output=True, check=True, env=env,
    )
    assert json.loads(json.loads(archive.stdout)["output"])["archived"] is True


def test_create_rejects_duplicate_slug_without_overwriting_pending_bundle(workspace):
    first = dd_create(**create_args(workspace))
    assert "output" in first
    document = workspace / "artifacts/designs/pending/sample-dd/DD.md"
    original = document.read_text(encoding="utf-8")

    result = dd_create(**create_args(workspace, slug="sample-dd"))

    assert result["error"] == "already_exists"
    assert document.read_text(encoding="utf-8") == original


def test_archive_rejects_completed_bundle_collision_and_preserves_pending_bundle(workspace):
    dd_create(**create_args(workspace))
    pending_bundle = workspace / "artifacts/designs/pending/sample-dd"
    pending_document = pending_bundle / "DD.md"
    completed_bundle = workspace / "artifacts/designs/completed/sample-dd"
    completed_bundle.mkdir(parents=True)
    (completed_bundle / "DD.md").write_text("existing completed bundle\n", encoding="utf-8")

    result = dd_archive("sample-dd", workspace_root=workspace)

    assert result["error"] == "already_exists"
    assert pending_bundle.exists()
    assert "**Status:** Draft" in pending_document.read_text(encoding="utf-8")
    assert (completed_bundle / "DD.md").read_text(encoding="utf-8") == "existing completed bundle\n"


def test_archive_force_replaces_completed_bundle(workspace):
    dd_create(**create_args(workspace))
    pending_bundle = workspace / "artifacts/designs/pending/sample-dd"
    completed_bundle = workspace / "artifacts/designs/completed/sample-dd"
    completed_bundle.mkdir(parents=True)
    (completed_bundle / "DD.md").write_text("old completed bundle\n", encoding="utf-8")
    (completed_bundle / "old-sibling.txt").write_text("old\n", encoding="utf-8")

    result = dd_archive("sample-dd", force=True, workspace_root=workspace)

    destination = workspace / "artifacts/designs/completed/sample-dd"
    assert json.loads(result["output"])["archived"] is True
    assert not pending_bundle.exists()
    assert "**Status:** Completed" in (destination / "DD.md").read_text(encoding="utf-8")
    assert not (destination / "old-sibling.txt").exists()




def test_archive_retries_after_completed_bundle_collision_is_cleared(workspace):
    dd_create(**create_args(workspace))
    pending_bundle = workspace / "artifacts/designs/pending/sample-dd"
    pending_document = pending_bundle / "DD.md"
    completed_bundle = workspace / "artifacts/designs/completed/sample-dd"
    completed_bundle.mkdir(parents=True)
    (completed_bundle / "DD.md").write_text("existing completed bundle\n", encoding="utf-8")

    first_result = dd_archive("sample-dd", workspace_root=workspace)
    assert first_result["error"] == "already_exists"
    completed_bundle.rename(workspace / "artifacts/designs/completed/sample-dd-old")

    retry_result = dd_archive("sample-dd", workspace_root=workspace)

    destination = workspace / "artifacts/designs/completed/sample-dd"
    assert json.loads(retry_result["output"])["archived"] is True
    assert not pending_bundle.exists()
    assert "**Status:** Completed" in destination.joinpath("DD.md").read_text(encoding="utf-8")
    assert not pending_document.exists()


def test_archive_requires_completed_linked_dag(tmp_path: Path):
    workspace = tmp_path / "workspace"
    bundle = workspace / "artifacts/designs/pending/graph-dd"
    bundle.mkdir(parents=True)
    (bundle / "DD.md").write_text("# Graph DD — Design Document\n\n**Status:** Approved\n**Author:** test\n**Created:** 2026-01-01\n\n**Related Documents:**\n- [DAG](artifacts/change-dags/pending/missing-graph/DAG.json) — linked\n\n---\n", encoding="utf-8")
    result = dd_archive("graph-dd", workspace_root=workspace)
    assert result["error"] == "linked_dags_incomplete"


def _declare_prerequisite(workspace: Path, slug: str = "prereq-dd") -> Path:
    dd_create(**create_args(workspace, slug))
    path = workspace / "artifacts/designs/pending" / slug / "DD.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n**Prerequisite disposition:** complete TASK-prerequisite-dd-build.md before archive.\n",
        encoding="utf-8",
    )
    return path


def test_archive_blocks_declared_pending_plan(workspace):
    _declare_prerequisite(workspace)
    pending = workspace / "artifacts/plans/pending/TASK-prerequisite-dd-build.md"
    pending.parent.mkdir(parents=True)
    pending.write_text("pending", encoding="utf-8")

    result = dd_archive("prereq-dd", workspace_root=workspace)
    assert result["error"] == "prerequisite_unsatisfied"
    assert (workspace / "artifacts/designs/pending/prereq-dd/DD.md").is_file()


def test_archive_accepts_declared_completed_plan(workspace):
    _declare_prerequisite(workspace)
    completed = workspace / "artifacts/plans/completed/TASK-prerequisite-dd-build.md"
    completed.parent.mkdir(parents=True)
    completed.write_text("completed", encoding="utf-8")

    result = dd_archive("prereq-dd", workspace_root=workspace)
    assert json.loads(result["output"])["archived"] is True
    assert (workspace / "artifacts/designs/completed/prereq-dd/DD.md").is_file()


def test_archive_without_prerequisite_or_dag_remains_unblocked(workspace):
    dd_create(**create_args(workspace, "ordinary-dd"))
    result = dd_archive("ordinary-dd", workspace_root=workspace)
    assert json.loads(result["output"])["archived"] is True


def test_archive_blocks_unresolvable_declared_prerequisite(workspace):
    _declare_prerequisite(workspace, "unresolvable-dd")
    path = workspace / "artifacts/designs/pending/unresolvable-dd/DD.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "TASK-prerequisite-dd-build.md", "capture-request-context"
        ),
        encoding="utf-8",
    )

    result = dd_archive("unresolvable-dd", workspace_root=workspace)
    assert result["error"] == "prerequisite_unsatisfied"
    assert (workspace / "artifacts/designs/pending/unresolvable-dd/DD.md").is_file()


def test_archive_requires_shared_slug_dag_then_accepts_completed(workspace):
    slug = "shared-slug-dd"
    related = [{"title": "DAG", "path": f"artifacts/change-dags/pending/{slug}/DAG.json", "description": "execution"}]
    dd_create(**create_args(workspace, slug), related_documents=related)

    blocked = dd_archive(slug, workspace_root=workspace)
    assert blocked["error"] == "linked_dags_incomplete"
    assert (workspace / "artifacts/designs/pending" / slug).is_dir()

    dag = workspace / "artifacts/change-dags/completed" / slug / "DAG.json"
    dag.parent.mkdir(parents=True)
    dag.write_text("{}", encoding="utf-8")
    archived = dd_archive(slug, workspace_root=workspace)
    assert json.loads(archived["output"])["archived"] is True
