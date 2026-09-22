"""Persistent implementation-graph state and safe mutation helpers."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

PENDING_DIR = "artifacts/implementation/pending"
COMPLETED_DIR = "artifacts/implementation/completed"
GRAPH_FILENAME = "GRAPH.json"
SCHEMA_VERSION = "1.0"
STATUSES = frozenset({"PENDING", "ACTIVE", "COMPLETE", "BLOCKED", "SUPERSEDED"})
QA_STATUSES = frozenset({"PENDING", "PASS", "FAIL"})
SAFE_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")


def _safe_part(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty")
    value = value.strip()
    if value in {".", ".."} or any(ch not in SAFE_ID_CHARS for ch in value):
        raise ValueError(f"invalid {label}")
    return value


def graph_path(workspace_root: Path, graph_id: str, completed: bool = False) -> Path:
    safe_id = _safe_part(graph_id, "graph_id")
    base = COMPLETED_DIR if completed else PENDING_DIR
    return workspace_root / base / safe_id / GRAPH_FILENAME


def locate_graph(workspace_root: Path, graph_id: str) -> tuple[Path | None, str | None]:
    pending = graph_path(workspace_root, graph_id, False)
    if pending.is_file():
        return pending, "pending"
    completed = graph_path(workspace_root, graph_id, True)
    if completed.is_file():
        return completed, "completed"
    return None, None


def _node_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("nodes must be an array")
    result: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise ValueError("each node must be an object with an id")
        if node["id"] in result:
            raise ValueError(f"duplicate node id: {node['id']}")
        result[node["id"]] = node
    return result


def _ids(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} must be an array of non-empty strings")
    return list(dict.fromkeys(value))


def validate_graph(graph: Any, workspace_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(graph, dict):
        return ["graph must be an object"]
    if graph.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    for key in ("graph_id", "title", "source", "requirements", "contracts", "nodes", "final_qa"):
        if key not in graph:
            errors.append(f"missing graph field: {key}")
    try:
        node_map = _node_map(graph)
    except ValueError as exc:
        errors.append(str(exc))
        node_map = {}
    reqs = graph.get("requirements", [])
    req_ids: set[str] = set()
    if not isinstance(reqs, list):
        errors.append("requirements must be an array")
    else:
        for req in reqs:
            if not isinstance(req, dict) or not isinstance(req.get("id"), str):
                errors.append("requirements must have string ids")
            elif req["id"] in req_ids:
                errors.append(f"duplicate requirement id: {req['id']}")
            else:
                req_ids.add(req["id"])
    contracts = graph.get("contracts", [])
    contract_ids: set[str] = set()
    if not isinstance(contracts, list):
        errors.append("contracts must be an array")
    else:
        for contract in contracts:
            if not isinstance(contract, dict) or not isinstance(contract.get("id"), str):
                errors.append("contracts must have string ids")
                continue
            cid = contract["id"]
            if cid in contract_ids:
                errors.append(f"duplicate contract id: {cid}")
            contract_ids.add(cid)
            producer = contract.get("producer")
            if producer is not None and producer not in node_map:
                errors.append(f"contract {cid} producer does not exist: {producer}")
            consumers = contract.get("consumers", [])
            if not isinstance(consumers, list):
                errors.append(f"contract {cid} consumers must be an array")
                consumers = []
            for consumer in consumers:
                if consumer not in node_map:
                    errors.append(f"contract {cid} consumer does not exist: {consumer}")
                elif cid not in node_map[consumer].get("consumes", []):
                    errors.append(f"contract {cid} consumer mismatch: {consumer} does not consume it")
            if producer is not None and producer in node_map and cid not in node_map[producer].get("produces", []):
                errors.append(f"contract {cid} producer mismatch: {producer} does not produce it")
    for node_id, node in node_map.items():
        if not node_id.startswith("I") or not node_id[1:].isdigit():
            errors.append(f"node {node_id} has invalid id; expected I<number>")
        status = node.get("status", "PENDING")
        if status not in STATUSES:
            errors.append(f"node {node_id} has invalid status: {status}")
        try:
            deps = _ids(node.get("depends_on", []), f"node {node_id}.depends_on")
            for dep in deps:
                if dep == node_id:
                    errors.append(f"node {node_id} depends on itself")
                elif dep not in node_map:
                    errors.append(f"node {node_id} dependency does not exist: {dep}")
        except ValueError as exc:
            errors.append(str(exc))
        for field, valid_ids in (("satisfies", req_ids), ("consumes", contract_ids), ("produces", contract_ids)):
            try:
                refs = _ids(node.get(field, []), f"node {node_id}.{field}")
                for ref in refs:
                    if ref not in valid_ids:
                        errors.append(f"node {node_id}.{field} references unknown id: {ref}")
            except ValueError as exc:
                errors.append(str(exc))
        if not isinstance(node.get("obligation"), str) or not node["obligation"].strip():
            errors.append(f"node {node_id} must have a non-empty obligation")
        if status == "ACTIVE" and (not isinstance(node.get("claim"), dict) or not isinstance(node.get("claim", {}).get("id"), str) or not node.get("claim", {}).get("id")):
            errors.append(f"active node {node_id} claim must have an id")
        claim = node.get("claim")
        if claim is not None and not isinstance(claim, dict):
            errors.append(f"node {node_id}.claim must be an object or null")
        if status == "ACTIVE" and not claim:
            errors.append(f"active node {node_id} must have a claim")
        if status != "ACTIVE" and claim is not None:
            errors.append(f"non-active node {node_id} cannot have a claim")
    # Kahn cycle check
    indegree = {node_id: 0 for node_id in node_map}
    outgoing = {node_id: [] for node_id in node_map}
    for node_id, node in node_map.items():
        for dep in node.get("depends_on", []):
            if dep in node_map:
                indegree[node_id] += 1
                outgoing[dep].append(node_id)
    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        current = queue.pop()
        visited += 1
        for child in outgoing[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if visited != len(node_map):
        errors.append("graph dependencies contain a cycle")
    qa = graph.get("final_qa")
    if not isinstance(qa, dict) or qa.get("status", "PENDING") not in QA_STATUSES:
        errors.append("final_qa.status must be PENDING, PASS, or FAIL")
    if workspace_root is not None:
        source = graph.get("source", {})
        if isinstance(source, dict):
            request_context = source.get("request_context")
            if request_context:
                candidate = workspace_root / request_context
                if not candidate.is_file():
                    errors.append(f"request context is not readable: {request_context}")
    return errors


def normalize_graph(graph: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(graph)
    result.setdefault("schema_version", SCHEMA_VERSION)
    result.setdefault("revision", 1)
    result.setdefault("requirements", [])
    result.setdefault("contracts", [])
    result.setdefault("nodes", [])
    result.setdefault("final_qa", {"status": "PENDING"})
    for node in result["nodes"]:
        node.setdefault("depends_on", [])
        node.setdefault("satisfies", [])
        node.setdefault("acceptance", [])
        node.setdefault("consumes", [])
        node.setdefault("produces", [])
        node.setdefault("context_hints", {})
        node.setdefault("status", "PENDING")
        node.setdefault("claim", None)
        node.setdefault("evidence", [])
        node.setdefault("provenance", [])
        node.setdefault("blocker", None)
    return result


def read_graph(workspace_root: Path, graph_id: str) -> tuple[dict[str, Any], Path, str]:
    path, location = locate_graph(workspace_root, graph_id)
    if path is None or location is None:
        raise FileNotFoundError(f"graph not found: {graph_id}")
    try:
        graph = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid graph file: {exc}") from exc
    return normalize_graph(graph), path, location


def graph_digest(graph: dict[str, Any]) -> str:
    payload = json.dumps(graph, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def workspace_fingerprint(workspace_root: Path) -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["git", "-C", str(workspace_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        head = result.stdout.strip() if result.returncode == 0 else ""
    except OSError:
        head = ""
    return hashlib.sha256(head.encode()).hexdigest()


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def mutate_graph(workspace_root: Path, graph_id: str, mutate: Callable[[dict[str, Any]], Any], *, invalidate_qa: bool = True, increment_revision: bool = True) -> tuple[dict[str, Any], Path, str]:
    graph, path, location = read_graph(workspace_root, graph_id)
    if location != "pending":
        raise ValueError("completed graphs are immutable")
    lock_path = path.with_name(".GRAPH.lock")
    with open(lock_path, "a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        graph, path, location = read_graph(workspace_root, graph_id)
        mutate(graph)
        errors = validate_graph(graph, workspace_root)
        if errors:
            raise ValueError("; ".join(errors[:8]))
        if increment_revision:
            graph["revision"] = int(graph.get("revision", 0)) + 1
        if invalidate_qa:
            graph["final_qa"] = {"status": "PENDING", "invalidated_by": "graph_mutation"}
        atomic_write(path, graph)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return graph, path, location


def node_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _node_map(graph)


def derived_ready(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = node_map(graph)
    return [
        node for node in graph["nodes"]
        if node.get("status") == "PENDING"
        and all(nodes.get(dep, {}).get("status") in {"COMPLETE", "SUPERSEDED"} for dep in node.get("depends_on", []))
    ]


def output(payload: Any, title: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"output": json.dumps(payload, ensure_ascii=False, sort_keys=True), "title": title, "metadata": metadata or {}}
