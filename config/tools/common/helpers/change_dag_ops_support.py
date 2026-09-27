"""Shared low-level substrate for the Change DAG operations surface.

Contains only behavior used by more than one operations domain: the error
payload constructor, numeric node-ID ordering, DAG/state loading, atomic
persistence, and the per-DAG mutation-lock decorator. Domain-specific helpers
(handle-space validation, candidate construction, read-only projections) stay
with their owning modules; this is not a generic utility bucket.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

from . import change_dag
from . import change_dag_control
from . import change_dag_state


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {"error": code, "message": message}
    payload.update(extra)
    return payload


def _numeric(node_id: str) -> int:
    return change_dag._numeric_id(node_id)


def _load(workspace_root: Path, slug: str) -> tuple[dict[str, Any] | None, dict[str, str] | None, str | None, dict[str, Any] | None]:
    try:
        dag, _path, location = change_dag.read_dag(workspace_root, slug)
    except FileNotFoundError as exc:
        return None, None, None, _error("dag_not_found", str(exc))
    except ValueError as exc:
        return None, None, None, _error("dag_read_failed", str(exc))
    try:
        state = change_dag_state.read_state(workspace_root, slug, completed=(location == "completed"))
    except ValueError as exc:
        return None, None, None, _error("state_read_failed", str(exc))
    return dag, state, location, None


def _persist(dag: dict[str, Any], workspace_root: Path, slug: str) -> None:
    change_dag.atomic_write_json(change_dag.dag_json_path(workspace_root, slug), dag)


def _locked_mutation(func):
    """Serialize a graph mutation against concurrent authoring invocations.

    Node-ID allocation, reference rewiring, validation, and persistence all run
    under one short-lived per-DAG lock so a stale read cannot silently overwrite
    another accepted mutation. Node IDs remain monotonic and are never reused.
    """

    @functools.wraps(func)
    def wrapper(workspace_root: Path, slug: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        root = Path(workspace_root)
        try:
            lock = change_dag_control.mutation_lock(root, slug)
        except ValueError:
            return func(root, slug, *args, **kwargs)
        with lock:
            return func(root, slug, *args, **kwargs)

    return wrapper
