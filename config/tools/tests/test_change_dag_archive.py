"""Archival retires a Change DAG from the pending working set.

Archival is lifecycle cleanup, not certification. A DAG is archivable after
success, failure, abandonment, supersession, or cancellation; only
operational-integrity gates (an executor owning the bundle, or a queued
admission that could still launch it) can refuse. The disposition record
captures the truth about the DAG at retirement.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag  # noqa: E402
from common.helpers import change_dag_control as control  # noqa: E402
from common.helpers.change_dag_ops_mutation import add_requirement  # noqa: E402
from common.tools.dag_archive import ARCHIVE_RECORD_FILENAME, dag_archive  # noqa: E402
from common.tools.dag_start import dag_start  # noqa: E402
from common.tools.dag_status import dag_status  # noqa: E402
from common.tools.dag_stop import dag_stop  # noqa: E402


def _dag(slug: str, nodes: dict, root: str = "N1") -> dict:
    return {"slug": slug, "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def _semantic(requirement: str, requires=None, decomposition_only=None) -> dict:
    node: dict = {"type": "semantic", "requirement": requirement}
    if requires is not None:
        node["requires"] = requires
    if decomposition_only is not None:
        node["decomposition_only"] = decomposition_only
    return node


def _edit(path: str = "f.txt") -> dict:
    return {"type": "edit", "path": path, "patch": f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,1 @@\n-a\n+b\n"}


def _create(path: str, content: str) -> dict:
    return {"type": "create", "path": path, "content": content}


def write_bundle(root: Path, slug: str, dag: dict, state: dict | None = None) -> Path:
    bundle = root / change_dag.PENDING_DIR / slug
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / change_dag.DAG_FILENAME).write_text(json.dumps(dag))
    (bundle / change_dag.STATE_FILENAME).write_text(json.dumps(state or {}))
    (bundle / change_dag.WORK_LOG_FILENAME).write_text("")
    return bundle


def test_archive_moves_mutation_provenance_with_bundle(tmp_path: Path):
    dag, state = _satisfied_dag("provenance")
    bundle = write_bundle(tmp_path, "provenance", dag, state)
    mutation_log = bundle / "DAG_MUTATIONS.jsonl"
    mutation_log.write_text('{"sequence": 1, "operation": "create_dag"}\n', encoding="utf-8")
    mutation_content = mutation_log.read_text(encoding="utf-8")

    result = dag_archive("provenance", "execution completed and artifact retired", workspace_root=tmp_path)

    assert result["archived"] is True
    assert "DAG_MUTATIONS.jsonl" in result["artifacts_moved"]
    archived_log = tmp_path / change_dag.ARCHIVED_DIR / "provenance" / "DAG_MUTATIONS.jsonl"
    assert archived_log.read_text(encoding="utf-8") == mutation_content


def _satisfied_dag(slug: str) -> tuple[dict, dict]:
    dag = _dag(slug, {
        "N1": _semantic("root", ["N2"], decomposition_only=True),
        "N2": _semantic("implementation is complete", ["N3"]),
        "N3": _edit(),
    })
    return dag, {"N3": "satisfied"}


def _failed_dag(slug: str) -> tuple[dict, dict]:
    dag = _dag(slug, {
        "N1": _semantic("root", ["N2"], decomposition_only=True),
        "N2": _semantic("implementation is complete", ["N3"]),
        "N3": _edit(),
    })
    return dag, {"N3": "failed"}


def _unresolved_dag(slug: str) -> dict:
    return _dag(slug, {
        "N1": _semantic("root", ["N2", "N3"], decomposition_only=True),
        "N2": _semantic("needs a product decision"),
        "N3": _semantic("implementation is complete", ["N4"]),
        "N4": _edit(),
    })


def _conflicting_dag(slug: str) -> dict:
    return _dag(slug, {
        "N1": _semantic("root", ["N2"], decomposition_only=True),
        "N2": _semantic("implementation is complete", ["N3", "N4"]),
        "N3": _create("new.txt", "x\n"),
        "N4": _create("new.txt", "y\n"),
    })


# ---------------------------------------------------------------------------
# Archival is not a correctness gate
# ---------------------------------------------------------------------------
def test_root_satisfied_dag_can_archive(tmp_path: Path):
    dag, state = _satisfied_dag("done")
    write_bundle(tmp_path, "done", dag, state)
    result = dag_archive("done", "execution completed and artifact retired", workspace_root=tmp_path)
    assert result["archived"] is True
    assert result["state_at_archive"]["root_satisfied"] is True
    assert result["state_at_archive"]["resolved"] is True
    assert result["state_at_archive"]["executable"] is True


def test_failed_dag_can_archive(tmp_path: Path):
    dag, state = _failed_dag("broke")
    write_bundle(tmp_path, "broke", dag, state)
    result = dag_archive("broke", "failed and no longer being pursued", workspace_root=tmp_path)
    assert result["archived"] is True
    assert result["state_at_archive"]["root_satisfied"] is False
    assert result["state_at_archive"]["failed_nodes"] == ["N3"]


def test_unresolved_dag_can_archive(tmp_path: Path):
    write_bundle(tmp_path, "abandoned", _unresolved_dag("abandoned"))
    result = dag_archive("abandoned", "unresolved and abandoned", workspace_root=tmp_path)
    assert result["archived"] is True
    assert result["state_at_archive"]["resolved"] is False
    assert result["state_at_archive"]["executable"] is False
    assert result["state_at_archive"]["failed_nodes"] == []


def test_non_executable_conflicting_dag_can_archive(tmp_path: Path):
    write_bundle(tmp_path, "conflict", _conflicting_dag("conflict"))
    result = dag_archive("conflict", "superseded by parser-v2", workspace_root=tmp_path)
    assert result["archived"] is True
    assert result["state_at_archive"]["resolved"] is True
    assert result["state_at_archive"]["executable"] is False


# ---------------------------------------------------------------------------
# Reason is required
# ---------------------------------------------------------------------------
def test_reason_is_required(tmp_path: Path):
    dag, state = _satisfied_dag("needsreason")
    write_bundle(tmp_path, "needsreason", dag, state)
    for bad in ("", "   ", None):
        result = dag_archive("needsreason", bad, workspace_root=tmp_path)
        assert result["error"] == "reason_required"
    assert (tmp_path / change_dag.PENDING_DIR / "needsreason" / change_dag.DAG_FILENAME).is_file()


# ---------------------------------------------------------------------------
# Disposition record
# ---------------------------------------------------------------------------
def test_archive_record_captures_state_truthfully(tmp_path: Path):
    dag, state = _failed_dag("record")
    write_bundle(tmp_path, "record", dag, state)
    dag_archive("record", "operator cancelled work", workspace_root=tmp_path)

    record = json.loads(
        (tmp_path / change_dag.ARCHIVED_DIR / "record" / ARCHIVE_RECORD_FILENAME).read_text(encoding="utf-8")
    )
    assert record["reason"] == "operator cancelled work"
    assert record["archived_at"]
    assert record["state_at_archive"]["schema_valid"] is True
    assert record["state_at_archive"]["root_satisfied"] is False
    assert record["state_at_archive"]["resolved"] is True
    assert record["state_at_archive"]["failed_nodes"] == ["N3"]
    # Semantic nodes never appear in terminal execution-state lists.
    assert record["state_at_archive"]["not_satisfied_nodes"] == []


def test_archive_of_satisfied_dag_has_no_semantic_terminal_entries(tmp_path: Path):
    dag, state = _satisfied_dag("done")
    write_bundle(tmp_path, "done", dag, state)
    result = dag_archive("done", "execution completed and artifact retired", workspace_root=tmp_path)

    # root_satisfied is derived independently; the terminal-state lists must not
    # contradict it by listing semantic root/parent nodes as not_satisfied.
    summary = result["state_at_archive"]
    assert summary["root_satisfied"] is True
    assert summary["failed_nodes"] == []
    assert summary["in_progress_nodes"] == []
    assert summary["not_satisfied_nodes"] == []


def test_archive_terminal_lists_exclude_semantic_nodes(tmp_path: Path):
    dag = _dag("mixed", {
        "N1": _semantic("root", ["N2"], decomposition_only=True),
        "N2": _semantic("implementation is complete", ["N3", "N4", "N5", "N6"]),
        "N3": _edit(),
        "N4": _create("new.txt", "x\n"),
        "N5": _edit("g.txt"),
        "N6": {"type": "remove", "path": "gone.txt"},
    })
    # The raw state deliberately carries illegal semantic entries too: they must
    # be dropped, not projected into terminal execution-state lists.
    write_bundle(tmp_path, "mixed", dag, {
        "N1": "failed",
        "N2": "in_progress",
        "N3": "failed",
        "N4": "in_progress",
        "N5": "satisfied",
    })
    result = dag_archive("mixed", "abandoned after upstream design changed", workspace_root=tmp_path)

    summary = result["state_at_archive"]
    assert summary["failed_nodes"] == ["N3"]
    assert summary["in_progress_nodes"] == ["N4"]
    assert summary["not_satisfied_nodes"] == ["N6"]
    assert summary["root_satisfied"] is False


def test_archive_record_lists_moved_artifacts(tmp_path: Path):
    dag, state = _satisfied_dag("moved")
    write_bundle(tmp_path, "moved", dag, state)
    result = dag_archive("moved", "execution completed and artifact retired", workspace_root=tmp_path)

    assert set(result["artifacts_moved"]) >= {
        change_dag.DAG_FILENAME,
        change_dag.STATE_FILENAME,
        change_dag.WORK_LOG_FILENAME,
        ARCHIVE_RECORD_FILENAME,
    }
    for name in result["artifacts_moved"]:
        assert (tmp_path / change_dag.ARCHIVED_DIR / "moved" / name).is_file()


# ---------------------------------------------------------------------------
# Operational-integrity gates
# ---------------------------------------------------------------------------
def test_running_dag_cannot_be_archived(tmp_path: Path):
    dag, state = _satisfied_dag("busy")
    write_bundle(tmp_path, "busy", dag, state)
    acquired, fd = control.acquire_lock(tmp_path)
    assert acquired
    control.write_marker(tmp_path, "busy", os.getpid())
    try:
        result = dag_archive("busy", "cancelled", workspace_root=tmp_path)
        assert result["error"] == "dag_running"
        assert (tmp_path / change_dag.PENDING_DIR / "busy" / change_dag.DAG_FILENAME).is_file()
    finally:
        control.remove_marker(tmp_path)
        control.release_lock(fd)


def test_queued_dag_must_be_cancelled_with_dag_stop_first(tmp_path: Path):
    dag, state = _satisfied_dag("queuee")
    write_bundle(tmp_path, "queuee", dag, state)
    acquired, fd = control.acquire_lock(tmp_path)
    assert acquired
    control.enqueue(tmp_path, "queuee")
    try:
        result = dag_archive("queuee", "cancelled", workspace_root=tmp_path)
        assert result["error"] == "dag_queued"
        assert (tmp_path / change_dag.PENDING_DIR / "queuee" / change_dag.DAG_FILENAME).is_file()

        # The documented remedy is dag_stop, which cancels the queued admission.
        assert dag_stop("queuee", workspace_root=tmp_path)["state"] == "idle"
        assert dag_archive("queuee", "cancelled", workspace_root=tmp_path)["archived"] is True
    finally:
        control.release_lock(fd)


# ---------------------------------------------------------------------------
# Archived means inactive and immutable
# ---------------------------------------------------------------------------
def test_archived_dag_cannot_be_mutated(tmp_path: Path):
    dag, state = _satisfied_dag("frozen")
    write_bundle(tmp_path, "frozen", dag, state)
    dag_archive("frozen", "operator cancelled work", workspace_root=tmp_path)
    result = add_requirement(tmp_path, "frozen", "new work", ["N1"])
    assert result["error"] == "dag_not_pending"


def test_archived_dag_cannot_be_started(tmp_path: Path):
    dag, state = _satisfied_dag("retired")
    write_bundle(tmp_path, "retired", dag, state)
    dag_archive("retired", "operator cancelled work", workspace_root=tmp_path)
    result = dag_start("retired", workspace_root=tmp_path)
    assert result["error"] == "dag_archived"


def test_archived_bundle_is_discoverable_for_inspection(tmp_path: Path):
    dag, state = _failed_dag("inspect")
    write_bundle(tmp_path, "inspect", dag, state)
    dag_archive("inspect", "failed and no longer being pursued", workspace_root=tmp_path)

    found, location = change_dag.locate_dag(tmp_path, "inspect")
    assert location == "archived"
    assert found is not None and found.is_file()
    loaded, _path, loaded_location = change_dag.read_dag(tmp_path, "inspect")
    assert loaded_location == "archived"
    assert loaded["slug"] == "inspect"

    status = dag_status("inspect", workspace_root=tmp_path)
    assert status["failed"] == ["N3"]
    assert status["root_satisfied"] is False


def test_archive_location_is_not_success_evidence(tmp_path: Path):
    dag, state = _failed_dag("notsuccess")
    write_bundle(tmp_path, "notsuccess", dag, state)
    result = dag_archive("notsuccess", "abandoned after upstream design changed", workspace_root=tmp_path)

    # The move succeeded, but nothing about the result claims execution success.
    assert result["archived"] is True
    assert result["path"].startswith(change_dag.ARCHIVED_DIR + "/")
    assert "completed" not in result["path"]
    assert result["state_at_archive"]["root_satisfied"] is False
    assert not (tmp_path / "artifacts/change-dags/completed").exists()
