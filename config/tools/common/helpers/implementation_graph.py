"""Persistent implementation-graph state, validation, and safe mutation helpers."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import subprocess
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


def _ancestors(node_id: str, nodes: dict[str, dict[str, Any]]) -> set[str]:
    found: set[str] = set()
    stack = list(nodes.get(node_id, {}).get("depends_on", []))
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(nodes.get(current, {}).get("depends_on", []))
    return found


def _required_nodes(nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [node for node in nodes.values() if node.get("status") != "SUPERSEDED"]


def _schema_errors(graph: dict[str, Any]) -> list[str]:
    """Use the shipped schema when jsonschema is available, without making it a runtime dependency."""
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "IMPLEMENTATION_GRAPH_SCHEMA.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).check_schema(schema)
        return [error.message for error in jsonschema.Draft202012Validator(schema).iter_errors(graph)]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"implementation graph schema unavailable: {exc}"]


def validate_graph(graph: Any, workspace_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(graph, dict):
        return ["graph must be an object"]
    errors.extend(_schema_errors(graph))
    if graph.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    for key in ("graph_id", "title", "source", "requirements", "contracts", "nodes", "final_qa"):
        if key not in graph:
            errors.append(f"missing graph field: {key}")
    try:
        nodes = _node_map(graph)
    except ValueError as exc:
        errors.append(str(exc))
        nodes = {}

    reqs = graph.get("requirements", [])
    req_ids: set[str] = set()
    if not isinstance(reqs, list):
        errors.append("requirements must be an array")
    else:
        for req in reqs:
            if not isinstance(req, dict) or not isinstance(req.get("id"), str) or not req.get("id"):
                errors.append("requirements must have non-empty string ids")
                continue
            req_id = req["id"]
            if req_id in req_ids:
                errors.append(f"duplicate requirement id: {req_id}")
            req_ids.add(req_id)
        required_ids = {req["id"] for req in reqs if isinstance(req, dict) and req.get("required", True) is not False and isinstance(req.get("id"), str)}
        owned_ids = {req_id for node in nodes.values() if node.get("status") != "SUPERSEDED" for req_id in node.get("satisfies", [])}
        for req_id in sorted(required_ids - owned_ids):
            errors.append(f"required requirement is unmapped: {req_id}")

    contracts = graph.get("contracts", [])
    contract_ids: set[str] = set()
    contract_map: dict[str, dict[str, Any]] = {}
    if not isinstance(contracts, list):
        errors.append("contracts must be an array")
    else:
        for contract in contracts:
            if not isinstance(contract, dict) or not isinstance(contract.get("id"), str) or not contract.get("id"):
                errors.append("contracts must have non-empty string ids")
                continue
            cid = contract["id"]
            if cid in contract_ids:
                errors.append(f"duplicate contract id: {cid}")
            contract_ids.add(cid)
            contract_map[cid] = contract
            producer = contract.get("producer")
            if producer is not None and producer not in nodes:
                errors.append(f"contract {cid} producer does not exist: {producer}")
            consumers = contract.get("consumers", [])
            if not isinstance(consumers, list):
                errors.append(f"contract {cid} consumers must be an array")
                consumers = []
            for consumer in consumers:
                if consumer not in nodes:
                    errors.append(f"contract {cid} consumer does not exist: {consumer}")
                elif cid not in nodes[consumer].get("consumes", []):
                    errors.append(f"contract {cid} consumer mismatch: {consumer} does not consume it")
            if producer is not None and producer in nodes and cid not in nodes[producer].get("produces", []):
                errors.append(f"contract {cid} producer mismatch: {producer} does not produce it")

    for node_id, node in nodes.items():
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
                elif dep not in nodes:
                    errors.append(f"node {node_id} dependency does not exist: {dep}")
                elif status != "SUPERSEDED" and nodes[dep].get("status") == "SUPERSEDED":
                    errors.append(f"node {node_id} depends on superseded node: {dep}")
                elif status == "COMPLETE" and nodes[dep].get("status") != "COMPLETE":
                    errors.append(f"complete node {node_id} has incomplete predecessor: {dep}")
        except ValueError as exc:
            errors.append(str(exc))
        for field, valid_ids in (("satisfies", req_ids), ("consumes", contract_ids), ("produces", contract_ids)):
            try:
                for ref in _ids(node.get(field, []), f"node {node_id}.{field}"):
                    if ref not in valid_ids:
                        errors.append(f"node {node_id}.{field} references unknown id: {ref}")
            except ValueError as exc:
                errors.append(str(exc))
        if not isinstance(node.get("obligation"), str) or not node["obligation"].strip():
            errors.append(f"node {node_id} must have a non-empty obligation")
        claim = node.get("claim")
        if claim is not None and not isinstance(claim, dict):
            errors.append(f"node {node_id}.claim must be an object or null")
        if status == "ACTIVE" and (not isinstance(claim, dict) or not isinstance(claim.get("id"), str) or not claim["id"].strip()):
            errors.append(f"active node {node_id} claim must have a non-empty id")
        if status != "ACTIVE" and claim is not None:
            errors.append(f"non-active node {node_id} cannot retain a claim")

    # Contract producer/consumer dependency closure.
    for cid, contract in contract_map.items():
        producer = contract.get("producer")
        if producer in nodes:
            for consumer in contract.get("consumers", []):
                if consumer in nodes and producer not in _ancestors(consumer, nodes) and producer != consumer and not contract.get("external_source"):
                    errors.append(f"contract {cid} producer is not an ancestor of consumer: {producer} -> {consumer}")

    indegree = {node_id: 0 for node_id in nodes}
    outgoing = {node_id: [] for node_id in nodes}
    for node_id, node in nodes.items():
        for dep in node.get("depends_on", []):
            if dep in nodes:
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
    if visited != len(nodes):
        errors.append("graph dependencies contain a cycle")

    qa = graph.get("final_qa")
    if not isinstance(qa, dict) or qa.get("status", "PENDING") not in QA_STATUSES:
        errors.append("final_qa.status must be PENDING, PASS, or FAIL")
    elif qa.get("status") == "PASS":
        required = _required_nodes(nodes)
        if any(node.get("status") != "COMPLETE" for node in required):
            errors.append("terminal QA PASS requires all required nodes complete")
        if any(node.get("claim") is not None for node in nodes.values()):
            errors.append("terminal QA PASS cannot retain active claims")
        if not isinstance(qa.get("implementation_state_digest"), str) or not qa.get("implementation_state_digest"):
            errors.append("terminal QA PASS requires implementation_state_digest")
        if not isinstance(qa.get("workspace_fingerprint"), str) or not qa.get("workspace_fingerprint"):
            errors.append("terminal QA PASS requires workspace_fingerprint")

    if workspace_root is not None:
        source = graph.get("source", {})
        if isinstance(source, dict):
            for key in ("request_context", "design_doc"):
                value = source.get(key)
                if value:
                    candidate = workspace_root / value
                    if not candidate.is_file():
                        errors.append(f"{key} is not readable: {value}")
    return errors


def normalize_graph(graph: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(graph)
    result.setdefault("schema_version", SCHEMA_VERSION)
    legacy_revision = int(result.get("revision", 1))
    result.setdefault("structure_revision", legacy_revision)
    result.setdefault("state_revision", legacy_revision)
    result["revision"] = int(result.get("state_revision", legacy_revision))
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
        node.setdefault("changed_files", [])
        node.setdefault("deviations", [])
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


def _digest_payload(graph: dict[str, Any], *, implementation: bool) -> dict[str, Any]:
    payload = copy.deepcopy(graph)
    payload.pop("final_qa", None)
    if implementation:
        return payload
    payload.pop("state_revision", None)
    payload.pop("revision", None)
    payload["nodes"] = []
    for node in graph.get("nodes", []):
        structural = {key: copy.deepcopy(value) for key, value in node.items() if key not in {"status", "claim", "evidence", "changed_files", "provenance", "deviations", "blocker", "actual_contracts"}}
        payload["nodes"].append(structural)
    payload["structure_revision"] = graph.get("structure_revision", 1)
    return payload


def implementation_state_digest(graph: dict[str, Any]) -> str:
    payload = json.dumps(_digest_payload(graph, implementation=True), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def graph_structure_digest(graph: dict[str, Any]) -> str:
    payload = json.dumps(_digest_payload(graph, implementation=False), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def graph_digest(graph: dict[str, Any]) -> str:
    """Backward-compatible alias for the canonical implementation-state digest."""
    return implementation_state_digest(graph)


def _run_git(workspace_root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(workspace_root), *args], capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else b""


_IMPLEMENTATION_STATE_EXCLUDES = (
    ":(exclude)artifacts/implementation/**",
    ":(exclude)**/.GRAPH.lock",
)


def workspace_fingerprint(workspace_root: Path) -> str:
    """Hash HEAD, non-ignored worktree state, and relevant untracked content.

    Implementation graph files are state bookkeeping and are excluded so recording
    QA or archiving a graph cannot change the workspace evidence it is bound to.
    """
    pathspec = ["--", ":(top)**", *_IMPLEMENTATION_STATE_EXCLUDES]
    parts: list[bytes] = [b"skyscow-workspace-v3\0", _run_git(workspace_root, "rev-parse", "HEAD")]
    parts.extend(
        (
            _run_git(workspace_root, "diff", "--binary", "--cached", "--no-ext-diff", *pathspec),
            _run_git(workspace_root, "diff", "--binary", "--no-ext-diff", *pathspec),
            _run_git(workspace_root, "status", "--porcelain=v1", "-z", "--untracked-files=all", *pathspec),
        )
    )
    raw_paths = _run_git(workspace_root, "ls-files", "--others", "--exclude-standard", "-z", *pathspec)
    for raw_path in sorted(path for path in raw_paths.split(b"\0") if path):
        path = (workspace_root / raw_path.decode("utf-8", "surrogateescape")).resolve()
        parts.append(raw_path + b"\0")
        try:
            if path.is_symlink():
                parts.append(b"SYMLINK\0" + os.readlink(path).encode("utf-8", "surrogateescape"))
            elif path.is_file():
                parts.append(path.read_bytes())
        except OSError:
            parts.append(b"UNREADABLE\0")
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


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


def mutate_graph(workspace_root: Path, graph_id: str, mutate: Callable[[dict[str, Any]], Any], *, structural_change: bool = False, invalidate_qa: bool = True, increment_state: bool = True) -> tuple[dict[str, Any], Path, str]:
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
        if structural_change:
            graph["structure_revision"] = int(graph.get("structure_revision", 1)) + 1
        if increment_state:
            graph["state_revision"] = int(graph.get("state_revision", graph.get("revision", 1))) + 1
        graph["revision"] = graph["state_revision"]
        if invalidate_qa:
            graph["final_qa"] = {"status": "PENDING", "invalidated_by": "graph_mutation"}
        atomic_write(path, graph)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return graph, path, location


def node_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _node_map(graph)


def derived_ready(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = node_map(graph)
    return [node for node in graph["nodes"] if node.get("status") == "PENDING" and all(nodes.get(dep, {}).get("status") == "COMPLETE" for dep in node.get("depends_on", []))]


def output(payload: Any, title: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"output": json.dumps(payload, ensure_ascii=False, sort_keys=True), "title": title, "metadata": metadata or {}}
