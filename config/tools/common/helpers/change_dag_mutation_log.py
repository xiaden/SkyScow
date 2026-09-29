"""Append-only construction provenance for Change DAG mutations."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import change_dag

MUTATION_LOG_FILENAME = "DAG_MUTATIONS.jsonl"
_SECRET_WORDS = ("secret", "token", "password", "credential", "api_key", "apikey")


def mutation_log_path(workspace_root: Path, slug: str) -> Path:
    return change_dag.bundle_dir(workspace_root, slug) / MUTATION_LOG_FILENAME


def dag_digest(dag: dict[str, Any] | None) -> str | None:
    if dag is None:
        return None
    encoded = json.dumps(dag, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _safe(value: Any, key: str | None = None) -> Any:
    if key and any(word in key.lower() for word in _SECRET_WORDS):
        return "[REDACTED]"
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, str) and len(value) > 4096:
            return value[:4096] + "...[truncated]"
        return value
    if isinstance(value, dict):
        return {str(k): _safe(v, str(k)) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value[:256]]
    return repr(value)[:4096]


def sanitized_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    return {"args": [_safe(value) for value in args], "kwargs": _safe(kwargs)}


def _changed_nodes(before: dict[str, Any] | None, after: dict[str, Any] | None) -> list[str]:
    before_nodes = (before or {}).get("nodes", {})
    after_nodes = (after or {}).get("nodes", {})
    changed = {
        node_id for node_id in set(before_nodes) | set(after_nodes)
        if before_nodes.get(node_id) != after_nodes.get(node_id)
    }
    before_edges, after_edges = _edge_sets(before), _edge_sets(after)
    for parent, child in before_edges ^ after_edges:
        changed.update((parent, child))
    return sorted(changed, key=change_dag._numeric_id)


def _edge_sets(dag: dict[str, Any] | None) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for parent, node in (dag or {}).get("nodes", {}).items():
        for child in node.get("requires", []) if isinstance(node, dict) else []:
            result.add((parent, child))
    return result


def _direct_snapshots(dag: dict[str, Any] | None, ids: list[str]) -> dict[str, dict[str, Any]]:
    nodes = (dag or {}).get("nodes", {})
    return {node_id: nodes[node_id] for node_id in ids if node_id in nodes}


def _edge_delta(before: dict[str, Any] | None, after: dict[str, Any] | None) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    added = sorted(_edge_sets(after) - _edge_sets(before))
    removed = sorted(_edge_sets(before) - _edge_sets(after))
    return ([{"parent_id": p, "child_id": c} for p, c in added],
            [{"parent_id": p, "child_id": c} for p, c in removed])


def _next_sequence(path: Path) -> int:
    if not path.exists():
        return 1
    sequence = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            sequence = max(sequence, int(json.loads(line).get("sequence", 0)))
        except (ValueError, TypeError, json.JSONDecodeError):
            continue
    return sequence + 1


def append_mutation_event(
    workspace_root: Path,
    slug: str,
    *,
    operation: str,
    success: bool,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    error: dict[str, Any] | None = None,
) -> None:
    """Append one event; callers invoke this while holding the DAG mutation lock.

    DAG.json is written first. If this append fails, the mutation remains persisted
    but the caller receives the logging exception rather than a false success.
    """
    path = mutation_log_path(workspace_root, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    before_ids = set((before or {}).get("nodes", {}))
    after_ids = set((after or {}).get("nodes", {}))
    changed = _changed_nodes(before, after) if success else []
    affected = changed
    additions, removals = _edge_delta(before, after) if success else ([], [])
    event: dict[str, Any] = {
        "sequence": _next_sequence(path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "tool": operation,
        "success": success,
        "before_digest": dag_digest(before),
        "affected_node_ids": affected,
        "before_nodes": _direct_snapshots(before, changed),
        "after_nodes": _direct_snapshots(after, changed) if success else {},
        "requires_added": additions,
        "requires_removed": removals,
        "operation_args": sanitized_args(args, kwargs),
    "caller_identity": None,
    }
    if success:
        event["after_digest"] = dag_digest(after)
    else:
        event["error"] = {
            "code": str((error or {}).get("error", "mutation_failed")),
            "reason": str((error or {}).get("message", "mutation failed")),
        }
    serialized = json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(serialized)
        stream.flush()
        os.fsync(stream.fileno())
