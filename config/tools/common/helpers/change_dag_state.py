"""Execution state and append-only Change DAG work-log helpers."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import change_dag


def _valid_node(node_id: str) -> None:
    if not isinstance(node_id, str) or change_dag.NODE_ID_PATTERN.fullmatch(node_id) is None:
        raise ValueError(f"invalid node id: {node_id!r}")


def _valid_value(value: str) -> None:
    if value not in change_dag.TERMINAL_STATES:
        raise ValueError(f"invalid terminal state: {value!r}")


def read_state(workspace_root: Path, slug: str, completed: bool = False) -> dict[str, str]:
    path = change_dag.state_json_path(workspace_root, slug, completed)
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid execution state {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"execution state must be an object: {path}")
    result: dict[str, str] = {}
    for node_id, status in value.items():
        _valid_node(node_id)
        _valid_value(status)
        result[node_id] = status
    return result


def write_state(workspace_root: Path, slug: str, state: dict[str, str], completed: bool = False) -> None:
    if not isinstance(state, dict):
        raise ValueError("state must be a dictionary")
    for node_id, status in state.items():
        _valid_node(node_id)
        _valid_value(status)
    change_dag.atomic_write_json(change_dag.state_json_path(workspace_root, slug, completed), dict(state))


def set_node_state(state: dict[str, str], node_id: str, value: str) -> None:
    _valid_node(node_id)
    _valid_value(value)
    state[node_id] = value


def state_with_defaults(dag: dict[str, Any], state: dict[str, str]) -> dict[str, str]:
    return {node_id: state.get(node_id, "not_satisfied") for node_id in change_dag.reachable_from_root(dag)}


def append_work_log(workspace_root: Path, slug: str, entry: dict[str, Any], completed: bool = False) -> None:
    if not isinstance(entry, dict):
        raise ValueError("work-log entry must be an object")
    path = change_dag.work_log_path(workspace_root, slug, completed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()


def read_work_log(workspace_root: Path, slug: str, completed: bool = False) -> list[dict[str, Any]]:
    path = change_dag.work_log_path(workspace_root, slug, completed)
    if not path.exists():
        return []
    result: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read work log {path}: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed work-log line {line_number}: {exc}") from exc
        if not isinstance(entry, dict):
            raise ValueError(f"malformed work-log line {line_number}: expected object")
        result.append(entry)
    return result


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log_file_operation(nodes: list[str], operation: str, *, path: str, result: str, detail: str = "", applied: bool = True) -> dict[str, Any]:
    if operation not in {"create", "edit", "remove", "move"} or result not in {"success", "failure"}:
        raise ValueError("invalid file operation or result")
    return {"timestamp": _timestamp(), "nodes": list(nodes), "operation": operation, "file": path, "result": result, "applied": applied, "detail": detail}


def log_run(node_id: str, command: list[str], *, stdout: str = "", stderr: str = "", exit_code: int | None = None, result: str) -> dict[str, Any]:
    _valid_node(node_id)
    return {"timestamp": _timestamp(), "nodes": [node_id], "operation": "run", "command": list(command), "stdout": stdout, "stderr": stderr, "exit_code": exit_code, "result": result}


def log_reconciliation(node_id: str, previous: str, resolved: str, *, reason: str, evidence: str = "") -> dict[str, Any]:
    _valid_node(node_id)
    _valid_value(previous)
    _valid_value(resolved)
    return {"timestamp": _timestamp(), "nodes": [node_id], "operation": "reconcile", "previous": previous, "resolved": resolved, "reason": reason, "evidence": evidence}


def log_checkpoint(slug: str, *, sha: str | None, committed: bool, inherited: dict[str, Any], message: str) -> dict[str, Any]:
    return {"timestamp": _timestamp(), "nodes": [], "operation": "checkpoint", "sha": sha, "committed": committed, "inherited": inherited, "message": message}
