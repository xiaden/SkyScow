"""Focused regression tests for first-class Change DAG MOVE nodes."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag, change_dag_compiler as compiler, change_dag_state as state_helper
from common.helpers.change_dag_ops import add_work, create_dag, preview, update_node
from common.tools import dag_executor


def _dag(root: Path, slug: str = "move") -> dict:
    result = create_dag(root, slug, {"root": "root", "nodes": {"root": {"requirement": "move"}}})
    assert "error" not in result
    return change_dag.read_dag(root, slug)[0]


def _write(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _move_op(root: Path, *, overwrite: bool = False) -> compiler.CompiledOp:
    return compiler.CompiledOp(
        nodes=["N2"], op="move", path="old.txt", from_path="old.txt",
        to_path="new.txt", overwrite=overwrite,
    )


def _bundle(root: Path, slug: str, dag: dict, state: dict[str, str]) -> None:
    bundle = root / "artifacts" / "change-dags" / "pending" / slug
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "DAG.json").write_text(json.dumps(dag), encoding="utf-8")
    (bundle / "EXECUTION_STATE.json").write_text(json.dumps(state), encoding="utf-8")
    (bundle / "WORK_LOG.jsonl").write_text("", encoding="utf-8")


SOURCE_TEXT = "source\n"


def _recorded_fingerprint(root: Path, content: str) -> dict | None:
    """A fingerprint captured from the intended source content pre-rename."""
    scratch = root / ".pre-rename-source"
    scratch.write_text(content, encoding="utf-8")
    fingerprint = compiler.source_fingerprint(scratch)
    scratch.unlink()
    return fingerprint


def _interrupted(root: Path, *, overwrite: bool, source: str | None, destination: str | None, recorded: bool = True) -> str:
    dag = {
        "slug": "interrupted",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "move", "satisfied_by": ["N2"]},
            "N2": {"type": "move", "from_path": "old.txt", "to_path": "new.txt", "overwrite": overwrite},
        },
    }
    _bundle(root, "interrupted", dag, {"N2": "in_progress"})
    if source is not None:
        _write(root, "old.txt", source)
    if destination is not None:
        _write(root, "new.txt", destination)
    fingerprint = _recorded_fingerprint(root, SOURCE_TEXT) if recorded else None
    state_helper.append_work_log(root, "interrupted", state_helper.log_move_start(
        ["N2"], from_path="old.txt", to_path="new.txt", overwrite=overwrite,
        source_fingerprint=fingerprint,
    ))
    dag_executor.reconcile_interrupted(root, "interrupted")
    return state_helper.read_state(root, "interrupted")["N2"]


def test_non_overwrite_move_uses_native_rename_and_preserves_content(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    _write(root, "old.txt", "source\n")
    result = compiler.apply_compiled([_move_op(root)], root)
    assert result[0]["ok"] is True
    assert not (root / "old.txt").exists()
    assert (root / "new.txt").read_text(encoding="utf-8") == "source\n"
    assert result[0]["overwrite"] is False


def test_non_overwrite_destination_collision_is_recoverable(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    _write(root, "old.txt", "source\n")
    _write(root, "new.txt", "existing\n")
    result = compiler.apply_compiled([_move_op(root)], root)
    assert result[0]["error"] == "context_mismatch"
    assert (root / "old.txt").read_text(encoding="utf-8") == "source\n"
    assert (root / "new.txt").read_text(encoding="utf-8") == "existing\n"


def test_overwrite_move_uses_native_replace(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    _write(root, "old.txt", "A\n")
    _write(root, "new.txt", "B\n")
    result = compiler.apply_compiled([_move_op(root, overwrite=True)], root)
    assert result[0]["ok"] is True
    assert not (root / "old.txt").exists()
    assert (root / "new.txt").read_text(encoding="utf-8") == "A\n"


def test_missing_source_fails_without_touching_destination(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    _write(root, "new.txt", "existing\n")
    result = compiler.apply_compiled([_move_op(root)], root)
    assert result[0]["error"] == "context_mismatch"
    assert (root / "new.txt").read_text(encoding="utf-8") == "existing\n"


@pytest.mark.parametrize("overwrite, primitive", [(False, "rename"), (True, "replace")])
def test_native_rename_failure_has_no_copy_fallback(tmp_path: Path, monkeypatch, overwrite: bool, primitive: str):
    root = tmp_path / "workspace"
    root.mkdir()
    _write(root, "old.txt", "source\n")
    operation = _move_op(root, overwrite=overwrite)

    def fail(*_args, **_kwargs):
        raise OSError("EXDEV")

    monkeypatch.setattr(os, primitive, fail)
    result = compiler.apply_compiled([operation], root)
    assert result[0]["error"] == "io_error"
    assert (root / "old.txt").read_text(encoding="utf-8") == "source\n"
    assert not (root / "new.txt").exists()


def test_schema_and_typed_authoring_default_and_validate_overwrite(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    _dag(root)
    added = add_work(root, "move", "move", ["N1"], from_path="old.txt", to_path="new.txt")
    assert "error" not in added
    dag = change_dag.read_dag(root, "move")[0]
    assert dag["nodes"]["N2"]["overwrite"] is False
    assert change_dag.validate_dag(dag) == []
    updated = update_node(root, "move", "N2", overwrite=True)
    assert "error" not in updated
    assert change_dag.read_dag(root, "move")[0]["nodes"]["N2"]["overwrite"] is True
    rejected = update_node(root, "move", "N2", overwrite="yes")
    assert rejected["error"] == "invalid_field"


def test_preview_scopes_move_by_both_paths_and_keeps_node_scope(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    _dag(root)
    _write(root, "old.txt", "source\n")
    add_work(root, "move", "move", ["N1"], from_path="old.txt", to_path="new.txt", overwrite=True)

    whole = json.loads(preview(root, "move")["output"])
    assert len(whole["ops"]) == 1
    assert whole["ops"][0] == {
        "nodes": ["N2"],
        "op": "move",
        "path": "old.txt",
        "from_path": "old.txt",
        "to_path": "new.txt",
        "overwrite": True,
        "segment": 0,
        "execution_phase": 0,
    }

    for scoped_path in ("old.txt", "./old.txt", "new.txt", "dir/../new.txt"):
        scoped = json.loads(preview(root, "move", path=scoped_path)["output"])
        assert scoped["ops"] == [whole["ops"][0]]

    unrelated = json.loads(preview(root, "move", path="other.txt")["output"])
    assert unrelated["ops"] == []

    node_scoped = json.loads(preview(root, "move", node_id="N2")["output"])
    assert node_scoped["mode"] == "node"
    assert node_scoped["ops"] == [whole["ops"][0]]


def test_move_work_log_evidence_includes_paths_overwrite_and_result():
    success = state_helper.log_file_operation(
        ["N2"], "move", path="old.txt", from_path="old.txt", to_path="new.txt",
        overwrite=True, result="success",
    )
    failure = state_helper.log_file_operation(
        ["N2"], "move", path="old.txt", from_path="old.txt", to_path="new.txt",
        overwrite=False, result="failure", detail="EXDEV",
    )
    for entry, overwrite, result in ((success, True, "success"), (failure, False, "failure")):
        assert entry["operation"] == "move"
        assert entry["from_path"] == "old.txt"
        assert entry["to_path"] == "new.txt"
        assert entry["overwrite"] is overwrite
        assert entry["result"] == result


def _git_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)
    _write(root, ".keep", "")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    return root


def _move_dag(*, overwrite: bool) -> dict:
    return {
        "slug": "move",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "move", "satisfied_by": ["N2"]},
            "N2": {"type": "move", "from_path": "old.txt", "to_path": "new.txt", "overwrite": overwrite},
        },
    }


def test_executor_records_move_recovery_and_completion_evidence(tmp_path: Path):
    root = _git_repo(tmp_path)
    _write(root, "old.txt", SOURCE_TEXT)
    _bundle(root, "logmove", _move_dag(overwrite=True), {})
    result = dag_executor.run_execution(root, "logmove")
    assert result["state"] == "root_satisfied"
    entries = [entry for entry in state_helper.read_work_log(root, "logmove") if entry["operation"] == "move"]
    starts = [entry for entry in entries if entry.get("phase") == "start"]
    completes = [entry for entry in entries if entry.get("phase") != "start"]
    assert len(starts) == 1 and len(completes) == 1
    assert starts[0]["from_path"] == "old.txt" and starts[0]["to_path"] == "new.txt"
    assert starts[0]["overwrite"] is True
    assert starts[0]["source_fingerprint"]["sha256"]
    assert completes[0]["result"] == "success" and completes[0]["overwrite"] is True
    assert (root / "new.txt").read_text(encoding="utf-8") == SOURCE_TEXT


def test_executor_records_failed_move_evidence(tmp_path: Path):
    root = _git_repo(tmp_path)
    _write(root, "old.txt", SOURCE_TEXT)
    _write(root, "new.txt", "existing\n")
    _bundle(root, "failmove", _move_dag(overwrite=False), {})
    result = dag_executor.run_execution(root, "failmove")
    assert result["state"] == "idle"
    entries = [entry for entry in state_helper.read_work_log(root, "failmove") if entry["operation"] == "move"]
    assert entries and entries[-1]["result"] == "failure"
    assert entries[-1]["overwrite"] is False
    assert entries[-1]["from_path"] == "old.txt" and entries[-1]["to_path"] == "new.txt"
    assert (root / "old.txt").read_text(encoding="utf-8") == SOURCE_TEXT
    assert (root / "new.txt").read_text(encoding="utf-8") == "existing\n"


def test_interrupted_non_overwrite_reconciliation_is_conservative(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    assert _interrupted(root, overwrite=False, source=SOURCE_TEXT, destination=None) == "not_satisfied"
    root = tmp_path / "destination"
    root.mkdir()
    assert _interrupted(root, overwrite=False, source=None, destination=SOURCE_TEXT) == "satisfied"
    root = tmp_path / "both"
    root.mkdir()
    assert _interrupted(root, overwrite=False, source=SOURCE_TEXT, destination=SOURCE_TEXT) == "failed"
    root = tmp_path / "neither"
    root.mkdir()
    assert _interrupted(root, overwrite=False, source=None, destination=None) == "failed"
    root = tmp_path / "unrelated"
    root.mkdir()
    assert _interrupted(root, overwrite=False, source=None, destination="unrelated\n") == "failed"
    root = tmp_path / "no-evidence"
    root.mkdir()
    # A matching destination is not proof when no pre-rename evidence was recorded.
    assert _interrupted(root, overwrite=False, source=None, destination=SOURCE_TEXT, recorded=False) == "failed"


def test_interrupted_overwrite_requires_matching_fingerprint(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    # Destination existence alone proves nothing: the destination may pre-exist.
    assert _interrupted(root, overwrite=True, source=None, destination="old-destination\n") == "failed"
    root = tmp_path / "matching"
    root.mkdir()
    assert _interrupted(root, overwrite=True, source=None, destination=SOURCE_TEXT) == "satisfied"
    root = tmp_path / "no-evidence"
    root.mkdir()
    assert _interrupted(root, overwrite=True, source=None, destination=SOURCE_TEXT, recorded=False) == "failed"
