"""Process-local authorization and session binding for Change-DAG workers."""
from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import change_dag
from .caller_identity import current_caller_identity
from .change_dag_decomposition import consume_branch_ref

WORKER_AGENT = "change-dag-worker"
_TOKEN_BYTES = 32
_LOCK = threading.RLock()


@dataclass(frozen=True)
class WorkerBinding:
    workspace: str
    slug: str
    node_id: str
    branch_ref: str
    agent: str
    session_id: str


_issued: dict[str, tuple[str, str, str, str]] = {}
_issued_nodes: dict[str, tuple[str, ...]] = {}
_bindings: dict[str, WorkerBinding] = {}


def _workspace_key(workspace_root: Path) -> str:
    return str(Path(workspace_root).resolve())


def _check_agent(agent: str) -> None:
    if agent != WORKER_AGENT:
        raise ValueError("unauthorized_agent: only change-dag-worker may resolve a worker session")


def issue_branch_ref(workspace_root: Path, slug: str, agent: str, session_id: str) -> str:
    """Compatibility helper for tests; production refs come from the frontier tool."""
    _check_agent(agent)
    if not isinstance(slug, str) or not slug or not isinstance(session_id, str) or not session_id:
        raise ValueError("invalid_request: slug and session_id are required")
    try:
        dag, _path, _location = change_dag.read_dag(Path(workspace_root), slug)
        unresolved = change_dag.unresolved_semantic_nodes(dag)
        depths = change_dag.derived_depth(dag)
        located = [node_id for node_id in unresolved if node_id in depths]
        depth = max((depths[node_id] for node_id in located), default=-1)
        candidates = tuple(sorted((node_id for node_id in located if depths[node_id] == depth), key=change_dag._numeric_id))
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(f"invalid_request: {exc}") from exc
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    with _LOCK:
        _issued[token] = (_workspace_key(workspace_root), slug, agent, session_id)
        _issued_nodes[token] = candidates
    return token


def _consume_branch_ref(workspace_root: Path, slug: str, agent: str, session_id: str, branch_ref: str) -> tuple[str, ...]:
    _check_agent(agent)
    if not isinstance(branch_ref, str) or not branch_ref:
        raise ValueError("invalid_branch_ref: opaque branch_ref is required")
    with _LOCK:
        issued = _issued.get(branch_ref)
        if issued is not None:
            _issued.pop(branch_ref, None)
            nodes = _issued_nodes.pop(branch_ref, ())
            expected = (_workspace_key(workspace_root), slug, agent, session_id)
            if issued != expected:
                raise ValueError("invalid_branch_ref: branch_ref does not authorize this request")
            return nodes
    try:
        dag, _path, _location = change_dag.read_dag(Path(workspace_root), slug)
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(f"invalid_branch_ref: {exc}") from exc
    node_ids = consume_branch_ref(branch_ref, slug, dag)
    if not node_ids:
        raise ValueError("invalid_branch_ref: branch_ref is unknown, stale, or already consumed")
    return node_ids


def resolve_worker(
    workspace_root: Path,
    slug: str,
    agent: str,
    session_id: str,
    branch_ref: str,
) -> dict[str, Any]:
    """Consume a branch reference, select one frontier node, and bind the session."""
    workspace = _workspace_key(workspace_root)
    with _LOCK:
        if session_id in _bindings:
            raise ValueError("session_rebind: session is already bound")
    candidate_ids = _consume_branch_ref(workspace_root, slug, agent, session_id, branch_ref)

    from .change_dag_ops_support import _load
    dag, _state, _location, err = _load(Path(workspace_root), slug)
    if err is not None:
        raise ValueError(f"{err.get('error', 'dag_error')}: {err.get('message', 'unable to load DAG')}")
    assert dag is not None
    node_ids = sorted(candidate_ids, key=change_dag._numeric_id)
    if not node_ids:
        node_ids = sorted(change_dag.unresolved_semantic_nodes(dag), key=change_dag._numeric_id)
    if not node_ids:
        raise ValueError("no_authorable_node: no current frontier node")
    node_id = node_ids[0]
    mutable, reason = change_dag.mutability(dag, _state, node_id)
    if not mutable:
        raise ValueError(f"node_not_mutable: {reason}")
    binding = WorkerBinding(workspace, slug, node_id, branch_ref, agent, session_id)
    with _LOCK:
        _bindings[session_id] = binding
    return {
        "workspace": workspace, "slug": slug, "node_id": node_id,
        "branch_ref": branch_ref, "session_id": session_id, "agent": agent,
    }


def require_worker_session(workspace_root: Path, slug: str, node_id: str, agent: str, session_id: str) -> WorkerBinding:
    """Authorize a later scoped tool call against the immutable session binding."""
    _check_agent(agent)
    with _LOCK:
        binding = _bindings.get(session_id)
    if binding is None:
        raise ValueError("session_unbound: worker session has no resolution binding")
    if (binding.workspace, binding.slug, binding.node_id, binding.agent) != (
        _workspace_key(workspace_root), slug, node_id, agent
    ):
        raise ValueError("session_scope_mismatch: scoped use is outside the bound worker scope")
    return binding


def worker_binding_for_call(workspace_root: Path, slug: str) -> WorkerBinding | None:
    """Return the service-bound scope, preserving direct calls without identity."""
    identity = current_caller_identity()
    if identity is None or identity.get("agent") != WORKER_AGENT:
        return None
    return require_worker_session(
        workspace_root, slug, "__bound_node__", WORKER_AGENT, identity["session"]
    ) if False else _binding_for_identity(workspace_root, slug, identity)


def _binding_for_identity(workspace_root: Path, slug: str, identity: dict[str, str]) -> WorkerBinding:
    with _LOCK:
        binding = _bindings.get(identity["session"])
    if binding is None:
        raise ValueError("session_unbound: worker session has no resolution binding")
    if binding.workspace != _workspace_key(workspace_root) or binding.slug != slug:
        raise ValueError("session_scope_mismatch: scoped use is outside the bound worker scope")
    return require_worker_session(workspace_root, slug, binding.node_id, WORKER_AGENT, identity["session"])


def worker_binding_for_call(workspace_root: Path, slug: str) -> WorkerBinding | None:
    """Return the service-bound worker scope; direct calls remain unscoped."""
    identity = current_caller_identity()
    if identity is None or identity.get("agent") != WORKER_AGENT:
        return None
    with _LOCK:
        binding = _bindings.get(identity["session"])
    if binding is None:
        raise ValueError("session_unbound: worker session has no resolution binding")
    if binding.workspace != _workspace_key(workspace_root) or binding.slug != slug:
        raise ValueError("session_scope_mismatch: scoped use is outside the bound worker scope")
    return binding


def authorize_worker_read(workspace_root: Path, slug: str, node_id: str) -> str:
    binding = worker_binding_for_call(workspace_root, slug)
    if binding is None:
        return node_id
    if node_id != binding.node_id:
        raise ValueError("worker_scope_mismatch: node_id is outside the bound worker scope")
    return binding.node_id


def authorize_worker_terminal(workspace_root: Path, slug: str, node_id: str | None = None) -> str:
    binding = worker_binding_for_call(workspace_root, slug)
    if binding is None:
        if node_id is None:
            raise ValueError("invalid_arguments: node_id is required")
        return node_id
    if node_id is not None and node_id != binding.node_id:
        raise ValueError("worker_scope_mismatch: node_id is outside the bound worker scope")
    return binding.node_id


def reject_worker_scope(workspace_root: Path, slug: str, scope: str) -> None:
    if worker_binding_for_call(workspace_root, slug) is not None:
        raise ValueError(f"worker_scope_forbidden: {scope} mutations are not allowed for workers")


def reset_worker_state() -> None:
    """Test-only process-local reset; no runtime persistence is involved."""
    with _LOCK:
        _issued.clear()
        _issued_nodes.clear()
        _bindings.clear()
