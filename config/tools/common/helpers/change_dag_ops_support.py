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
from .caller_identity import current_caller_identity, take_caller_identity
from .change_dag_mutation_log import append_mutation_event, mutation_logging_enabled


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
        state = change_dag_state.read_state(workspace_root, slug, archived=(location == "archived"))
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
        identity = current_caller_identity()
        root = Path(workspace_root)
        from .worker_resolution import WORKER_AGENT, worker_binding_for_call
        try:
            worker_binding = worker_binding_for_call(root, slug) if identity and identity.get("agent") == WORKER_AGENT else None
        except ValueError as exc:
            code, _, message = str(exc).partition(": ")
            return _error(code, message or code)
        if worker_binding is not None:
            if func.__name__ == "add_work":
                args = (args[0], [worker_binding.node_id], *args[2:])
            elif func.__name__ in {"update_node", "remove_node"}:
                args = (worker_binding.node_id, *args[1:])
            elif func.__name__ in {"add_requirement", "link_requirement", "unlink_requirement", "set_decomposition_only"}:
                return _error("worker_scope_forbidden", f"{func.__name__} is not allowed for workers")
        caller_identity = take_caller_identity()

        def invoke() -> dict[str, Any]:
            before: dict[str, Any] | None = None
            try:
                before, _path, _location = change_dag.read_dag(root, slug)
            except (FileNotFoundError, ValueError):
                pass
            result = func(root, slug, *args, **kwargs)
            success = isinstance(result, dict) and "error" not in result
            after: dict[str, Any] | None = None
            if success:
                try:
                    after, _path, _location = change_dag.read_dag(root, slug)
                except (FileNotFoundError, ValueError) as exc:
                    raise RuntimeError("mutation succeeded but DAG could not be re-read for provenance") from exc
            # A failed call against a nonexistent or malformed DAG is not a
            # mutation of an existing bundle; do not create an orphan log-only
            # directory. Successful creation still has no pre-state and is
            # intentionally recorded as the first event.
            should_log = before is not None or success
            logging_warning: str | None = None
            if should_log and mutation_logging_enabled():
                try:
                    append_mutation_event(
                        root,
                        slug,
                        operation=func.__name__,
                        success=success,
                        before=before,
                        after=after,
                        args=args,
                        kwargs=kwargs,
                        error=result if not success else None,
                        caller_identity=caller_identity,
                    )
                except Exception as exc:
                    logging_warning = f"mutation provenance was not recorded: {exc}"
            if logging_warning and success and isinstance(result, dict):
                metadata = result.setdefault("metadata", {})
                if isinstance(metadata, dict):
                    metadata["warning"] = logging_warning
            return result

        try:
            lock = change_dag_control.mutation_lock(root, slug)
        except ValueError:
            return invoke()
        with lock:
            return invoke()

    return wrapper
