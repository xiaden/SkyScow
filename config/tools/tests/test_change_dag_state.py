from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.helpers.change_dag_state import (
    append_work_log, log_checkpoint, log_file_operation, log_reconciliation, log_run,
    read_state, read_work_log, set_node_state, state_with_defaults, write_state,
)


def dag() -> dict:
    return {"root": "N1", "nodes": {"N1": {"type": "semantic", "satisfied_by": ["N2"]}, "N2": {"type": "edit", "path": "x", "patch": "p"}}}


def test_state_round_trip_and_validation(tmp_path: Path):
    assert read_state(tmp_path, "x") == {}
    write_state(tmp_path, "x", {"N2": "satisfied"})
    assert read_state(tmp_path, "x") == {"N2": "satisfied"}
    with pytest.raises(ValueError):
        write_state(tmp_path, "x", {"bad": "satisfied"})
    with pytest.raises(ValueError):
        set_node_state({}, "N2", "bad")


def test_defaults_and_log_append(tmp_path: Path):
    assert state_with_defaults(dag(), {"N2": "satisfied"}) == {"N1": "not_satisfied", "N2": "satisfied"}
    append_work_log(tmp_path, "x", {"n": 1})
    append_work_log(tmp_path, "x", {"n": 2})
    assert read_work_log(tmp_path, "x") == [{"n": 1}, {"n": 2}]
    with (tmp_path / "artifacts/change-dags/pending/x/WORK_LOG.jsonl").open("a") as f:
        f.write("broken\n")
    with pytest.raises(ValueError, match="line 3"):
        read_work_log(tmp_path, "x")


def test_log_builders_shapes():
    assert log_file_operation(["N2"], "edit", path="x", result="success")["file"] == "x"
    assert log_run("N2", ["pytest"], result="success")["operation"] == "run"
    assert log_reconciliation("N2", "in_progress", "failed", reason="x")["operation"] == "reconcile"
    assert log_checkpoint("x", sha=None, committed=False, inherited={}, message="m")["nodes"] == []
    assert read_work_log(Path("/tmp/definitely-missing"), "x") == []
