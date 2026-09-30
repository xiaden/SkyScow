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
from .change_dag_control import checkpoint_identity
from .caller_identity import current_caller_identity, current_internal_metadata, take_caller_identity
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
            elif func.__name__ == "add_requirement":
                # Semantic refinement is local to the assigned node. Do not
                # silently rewrite a caller's parent: reject graph surgery that
                # names any other semantic scope.
                parents = args[1] if len(args) > 1 else None
                if parents != [worker_binding.node_id]:
                    return _error("worker_scope_mismatch", "parent_ids must contain only the bound worker node")
                child_ids = args[2] if len(args) > 2 else None
                if child_ids is not None:
                    try:
                        dag, _path, _location = change_dag.read_dag(root, slug)
                        allowed_children = set(change_dag.direct_children(dag, worker_binding.node_id))
                    except (FileNotFoundError, ValueError) as exc:
                        return _error("dag_read_failed", str(exc))
                    if not isinstance(child_ids, list) or any(child not in allowed_children for child in child_ids):
                        return _error("worker_scope_mismatch", "selected children are outside the bound worker scope")
            elif func.__name__ == "set_decomposition_only":
                args = (worker_binding.node_id, *args[1:])
            elif func.__name__ in {"link_requirement", "unlink_requirement"}:
                return _error("worker_scope_forbidden", f"{func.__name__} is not allowed for workers")
        repair_binding: dict[str, Any] | None = None
        if identity and identity.get("agent") == "change-dag-semantic-repairer":
            repair_binding = (current_internal_metadata() or {}).get("semantic_repair_binding")
            if not isinstance(repair_binding, dict) or repair_binding.get("session_id") != identity.get("session"):
                return _error("semantic_repair_unbound", "semantic repair mutation requires a bound repair capability")
            if repair_binding.get("slug") != slug:
                return _error("semantic_repair_scope_violation", "semantic repair mutation is outside the bound DAG")
            if func.__name__ not in {"add_requirement", "update_node", "link_requirement", "unlink_requirement", "set_decomposition_only"}:
                return _error("semantic_repair_scope_violation", "semantic repairer may mutate semantic graph only")
            if func.__name__ == "update_node":
                try:
                    repair_dag, _path, _location = change_dag.read_dag(root, slug)
                    if change_dag.node_type(repair_dag, args[0]) != change_dag.SEMANTIC_TYPE:
                        return _error("semantic_repair_scope_violation", "semantic repairer may update semantic nodes only")
                except (IndexError, FileNotFoundError, ValueError) as exc:
                    return _error("semantic_repair_scope_violation", str(exc))
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
        except ValueError as exc:
            if repair_binding is not None:
                return _error("semantic_repair_scope_violation", str(exc))
            return invoke()
        with lock:
            # Check the ephemeral repair capability only while holding the same
            # lock as the mutation. This closes the check/apply race and lets
            # the caller advance its binding after each successful mutation.
            if repair_binding is not None:
                try:
                    current_dag, _path, _location = change_dag.read_dag(root, slug)
                    if checkpoint_identity(current_dag) != repair_binding.get("checkpoint_identity"):
                        return _error("semantic_repair_scope_violation", "semantic repair capability is stale")
                except (FileNotFoundError, ValueError) as exc:
                    return _error("semantic_repair_scope_violation", str(exc))
            result = invoke()
            if repair_binding is not None and isinstance(result, dict) and "error" not in result:
                try:
                    updated_dag, _path, _location = change_dag.read_dag(root, slug)
                    metadata = result.setdefault("metadata", {})
                    if isinstance(metadata, dict):
                        metadata["semantic_repair_checkpoint_identity"] = checkpoint_identity(updated_dag)
                except (FileNotFoundError, ValueError) as exc:
                    return _error("semantic_repair_scope_violation", f"mutation succeeded but checkpoint could not be refreshed: {exc}")
            return result

    return wrapper
