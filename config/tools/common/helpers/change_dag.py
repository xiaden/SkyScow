"""Core Change DAG model: validation, derived properties, and persistence.

The Change DAG is the declarative definition of the work required to satisfy a
root requirement. It contains no runtime execution state and no execution
history. ``satisfied_by`` is the only graph edge and means ALL-of.

This module is intentionally stdlib-only except for a *guarded optional*
``jsonschema`` import used to enforce the shipped JSON Schema shape. When
``jsonschema`` is unavailable a minimal internal shape check is used so the
module never gains a hard runtime dependency.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

CHANGE_DAGS_DIR = "artifacts/change-dags"
PENDING_DIR = "artifacts/change-dags/pending"
COMPLETED_DIR = "artifacts/change-dags/completed"
DAG_FILENAME = "DAG.json"
STATE_FILENAME = "EXECUTION_STATE.json"
WORK_LOG_FILENAME = "WORK_LOG.jsonl"
NODE_SEQ_FILENAME = ".node_seq"

NODE_ID_PATTERN = re.compile(r"^N[0-9]+$")
ANCHOR_COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{7,64}$")
TERMINAL_STATES = ("not_satisfied", "in_progress", "satisfied", "failed")
TERMINAL_TYPES = ("create", "edit", "remove", "move", "run")
SEMANTIC_TYPE = "semantic"

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "CHANGE_DAG_SCHEMA.json"

# Node shape used only by the internal fallback checker (jsonschema absent).
_NODE_REQUIRED: dict[str, set[str]] = {
    "semantic": {"type", "requirement"},
    "create": {"type", "path", "content"},
    "edit": {"type", "path", "patch"},
    "remove": {"type", "path"},
    "move": {"type", "from_path", "to_path"},
    "run": {"type", "command"},
}
_NODE_ALLOWED: dict[str, set[str]] = {
    "semantic": {"type", "requirement", "satisfied_by"},
    "create": {"type", "path", "content"},
    "edit": {"type", "path", "patch"},
    "remove": {"type", "path"},
    "move": {"type", "from_path", "to_path"},
    "run": {"type", "command", "exclusive"},
}
_ROOT_KEYS = {"slug", "anchor_commit", "root", "nodes"}


# ---------------------------------------------------------------------------
# Paths and IO
# ---------------------------------------------------------------------------
def _safe_slug(slug: Any) -> str:
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("slug must be non-empty")
    if slug in {".", ".."} or "/" in slug or "\\" in slug:
        raise ValueError(f"invalid slug: {slug!r}")
    return slug


def bundle_dir(workspace_root: Path, slug: str, completed: bool = False) -> Path:
    safe = _safe_slug(slug)
    base = COMPLETED_DIR if completed else PENDING_DIR
    return Path(workspace_root) / base / safe


def dag_json_path(workspace_root: Path, slug: str, completed: bool = False) -> Path:
    return bundle_dir(workspace_root, slug, completed) / DAG_FILENAME


def state_json_path(workspace_root: Path, slug: str, completed: bool = False) -> Path:
    return bundle_dir(workspace_root, slug, completed) / STATE_FILENAME


def work_log_path(workspace_root: Path, slug: str, completed: bool = False) -> Path:
    return bundle_dir(workspace_root, slug, completed) / WORK_LOG_FILENAME


def locate_dag(workspace_root: Path, slug: str) -> tuple[Path | None, str | None]:
    pending = dag_json_path(workspace_root, slug, False)
    if pending.is_file():
        return pending, "pending"
    completed = dag_json_path(workspace_root, slug, True)
    if completed.is_file():
        return completed, "completed"
    return None, None


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid json file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"json file is not an object: {path}")
    return data


def read_dag(workspace_root: Path, slug: str) -> tuple[dict[str, Any], Path, str]:
    path, location = locate_dag(workspace_root, slug)
    if path is None or location is None:
        raise FileNotFoundError(f"change dag not found: {slug}")
    return read_json(path), path, location


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON via mkstemp + flush + fsync + os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
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


def _atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def resolve_anchor_commit(workspace_root: Path) -> str:
    """Return current Git HEAD; fall back to a 7-hex constant on any failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace_root), "rev-parse", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            if ANCHOR_COMMIT_PATTERN.match(sha):
                return sha
    except OSError:
        pass
    return "0" * 7


# ---------------------------------------------------------------------------
# Graph model / derived
# ---------------------------------------------------------------------------
def node_map(dag: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(dag, dict):
        return {}
    nodes = dag.get("nodes")
    if not isinstance(nodes, dict):
        return {}
    return {key: value for key, value in nodes.items() if isinstance(key, str) and isinstance(value, dict)}


def node_type(dag: Any, node_id: str) -> str | None:
    node = node_map(dag).get(node_id)
    if isinstance(node, dict) and isinstance(node.get("type"), str):
        return node["type"]
    return None


def direct_children(dag: Any, node_id: str) -> list[str]:
    node = node_map(dag).get(node_id)
    if not isinstance(node, dict) or node.get("type") != SEMANTIC_TYPE:
        return []
    refs = node.get("satisfied_by")
    if not isinstance(refs, list):
        return []
    return [ref for ref in refs if isinstance(ref, str)]


def reachable_from_root(dag: Any) -> set[str]:
    nodes = node_map(dag)
    root = dag.get("root") if isinstance(dag, dict) else None
    if not isinstance(root, str) or root not in nodes:
        return set()
    found: set[str] = set()
    stack = [root]
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(direct_children(dag, current))
    return found


def _parent_map(dag: Any) -> dict[str, set[str]]:
    nodes = node_map(dag)
    parents: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for node_id in nodes:
        for child in direct_children(dag, node_id):
            if child in nodes and child != node_id:
                parents[child].add(node_id)
    return parents


def ancestor_map(dag: Any) -> dict[str, set[str]]:
    nodes = node_map(dag)
    parents = _parent_map(dag)
    result: dict[str, set[str]] = {}
    for node_id in nodes:
        seen: set[str] = set()
        stack = list(parents.get(node_id, ()))
        while stack:
            current = stack.pop()
            if current in seen or current == node_id:
                continue
            seen.add(current)
            stack.extend(parents.get(current, ()))
        result[node_id] = seen
    return result


def _find_cycle(dag: Any) -> list[str] | None:
    nodes = node_map(dag)
    if not nodes:
        return None
    color = {node_id: 0 for node_id in nodes}  # 0=white, 1=gray, 2=black
    for start in nodes:
        if color[start] != 0:
            continue
        color[start] = 1
        path = [start]
        stack: list[tuple[str, Any]] = [(start, iter(direct_children(dag, start)))]
        while stack:
            node, iterator = stack[-1]
            advanced = False
            for child in iterator:
                if child not in nodes:
                    continue
                if color[child] == 1:
                    index = path.index(child)
                    return path[index:] + [child]
                if color[child] == 0:
                    color[child] = 1
                    path.append(child)
                    stack.append((child, iter(direct_children(dag, child))))
                    advanced = True
                    break
            if not advanced:
                color[node] = 2
                stack.pop()
                path.pop()
    return None


def is_acyclic(dag: Any) -> bool:
    return _find_cycle(dag) is None


def derived_depth(dag: Any) -> dict[str, int]:
    """Longest path from root. Unreachable nodes are excluded; cycles do not hang."""
    nodes = node_map(dag)
    root = dag.get("root") if isinstance(dag, dict) else None
    parents = _parent_map(dag)
    memo: dict[str, int | None] = {}

    def resolve(node_id: str, visiting: set[str]) -> int | None:
        if node_id in memo:
            return memo[node_id]
        if node_id in visiting:
            return None
        if node_id == root:
            memo[node_id] = 0
            return 0
        visiting.add(node_id)
        best: int | None = None
        for parent in parents.get(node_id, ()):
            parent_depth = resolve(parent, visiting)
            if parent_depth is not None:
                best = parent_depth + 1 if best is None else max(best, parent_depth + 1)
        visiting.discard(node_id)
        memo[node_id] = best
        return best

    result: dict[str, int] = {}
    for node_id in nodes:
        depth = resolve(node_id, set())
        if depth is not None:
            result[node_id] = depth
    return result


def _numeric_id(node_id: str) -> int:
    match = NODE_ID_PATTERN.match(node_id)
    if match:
        return int(node_id[1:])
    return 1 << 62


def execution_order(dag: Any) -> list[str]:
    depths = derived_depth(dag)
    return sorted(depths, key=lambda node_id: (-depths[node_id], _numeric_id(node_id)))


def run_barrier_errors(dag: Any) -> list[str]:
    errors: list[str] = []
    nodes = node_map(dag)
    for node_id in sorted(nodes):
        if node_type(dag, node_id) != SEMANTIC_TYPE:
            continue
        children = direct_children(dag, node_id)
        run_children = [child for child in children if node_type(dag, child) == "run"]
        if not run_children:
            continue
        if len(run_children) > 1:
            errors.append(
                f"semantic node {node_id} has multiple direct run children: {', '.join(run_children)}"
            )
        for child in children:
            if child in run_children:
                continue
            child_type = node_type(dag, child)
            if child_type is not None and child_type != SEMANTIC_TYPE:
                errors.append(
                    f"semantic node {node_id} has a non-semantic child beside a run child: {child} ({child_type})"
                )
    return errors


def allocate_node_id(dag: Any, workspace_root: Path, slug: str, completed: bool = False) -> str:
    """Allocate a monotonically increasing N<number> ID that is never reused."""
    nodes = node_map(dag)
    current_max = 0
    for node_id in nodes:
        match = NODE_ID_PATTERN.match(node_id)
        if match:
            current_max = max(current_max, int(node_id[1:]))
    seq_path = bundle_dir(workspace_root, slug, completed) / NODE_SEQ_FILENAME
    persisted = 0
    try:
        persisted = int(seq_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        persisted = 0
    next_number = max(current_max, persisted) + 1
    _atomic_write_text(seq_path, f"{next_number}\n")
    return f"N{next_number}"


def derived_satisfaction(dag: Any, state: Any) -> dict[str, bool]:
    nodes = node_map(dag)
    effective_state = state if isinstance(state, dict) else {}
    memo: dict[str, bool] = {}

    def resolve(node_id: str, visiting: set[str]) -> bool:
        if node_id in memo:
            return memo[node_id]
        if node_id in visiting:
            return False
        kind = node_type(dag, node_id)
        if kind in TERMINAL_TYPES:
            value = effective_state.get(node_id) == "satisfied"
        elif kind == SEMANTIC_TYPE:
            children = direct_children(dag, node_id)
            if not children:
                value = False
            else:
                visiting.add(node_id)
                value = all(resolve(child, visiting) for child in children)
                visiting.discard(node_id)
        else:
            value = False
        memo[node_id] = value
        return value

    return {node_id: resolve(node_id, set()) for node_id in nodes}


def is_resolved(dag: Any) -> bool:
    for node_id in node_map(dag):
        if node_type(dag, node_id) == SEMANTIC_TYPE and not direct_children(dag, node_id):
            return False
    return True


def unresolved_leaves(dag: Any) -> list[str]:
    leaves = [
        node_id
        for node_id in node_map(dag)
        if node_type(dag, node_id) == SEMANTIC_TYPE and not direct_children(dag, node_id)
    ]
    return sorted(leaves, key=_numeric_id)


def satisfied_terminal_nodes(dag: Any, state: Any) -> list[str]:
    satisfaction = derived_satisfaction(dag, state)
    return sorted(
        (
            node_id
            for node_id in node_map(dag)
            if node_type(dag, node_id) in TERMINAL_TYPES and satisfaction.get(node_id, False)
        ),
        key=_numeric_id,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _internal_schema_errors(dag: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(dag, dict):
        return ["dag must be an object"]
    for key in sorted(_ROOT_KEYS):
        if key not in dag:
            errors.append(f"missing root field: {key}")
    for key in sorted(set(dag) - _ROOT_KEYS):
        errors.append(f"unexpected root field: {key}")
    slug = dag.get("slug")
    if not isinstance(slug, str) or not slug:
        errors.append("slug must be a non-empty string")
    anchor = dag.get("anchor_commit")
    if not isinstance(anchor, str) or not ANCHOR_COMMIT_PATTERN.match(anchor):
        errors.append("anchor_commit must be a 7-64 character hex string")
    root = dag.get("root")
    if not isinstance(root, str) or not root:
        errors.append("root must be a non-empty string")
    nodes = dag.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        errors.append("nodes must be a non-empty object")
        return errors
    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            errors.append(f"node {node_id} must be an object")
            continue
        kind = node.get("type")
        if kind not in _NODE_ALLOWED:
            errors.append(f"node {node_id} has invalid type: {kind!r}")
            continue
        missing = _NODE_REQUIRED[kind] - set(node)
        for field in sorted(missing):
            errors.append(f"node {node_id} ({kind}) missing required field: {field}")
        for field in sorted(set(node) - _NODE_ALLOWED[kind]):
            errors.append(f"node {node_id} ({kind}) has unexpected field: {field}")
        if kind == "semantic":
            requirement = node.get("requirement")
            if not isinstance(requirement, str) or not requirement:
                errors.append(f"node {node_id} requirement must be a non-empty string")
            if "satisfied_by" in node:
                refs = node["satisfied_by"]
                if not isinstance(refs, list) or not refs:
                    errors.append(f"node {node_id} satisfied_by must be a non-empty array")
                elif any(not isinstance(ref, str) or not ref for ref in refs):
                    errors.append(f"node {node_id} satisfied_by entries must be non-empty strings")
                elif len(set(refs)) != len(refs):
                    errors.append(f"node {node_id} satisfied_by entries must be unique")
        elif kind == "create":
            if not isinstance(node.get("path"), str) or not node.get("path"):
                errors.append(f"node {node_id} path must be a non-empty string")
            if not isinstance(node.get("content"), str):
                errors.append(f"node {node_id} content must be a string")
        elif kind == "edit":
            if not isinstance(node.get("path"), str) or not node.get("path"):
                errors.append(f"node {node_id} path must be a non-empty string")
            if not isinstance(node.get("patch"), str) or not node.get("patch"):
                errors.append(f"node {node_id} patch must be a non-empty string")
        elif kind == "remove":
            if not isinstance(node.get("path"), str) or not node.get("path"):
                errors.append(f"node {node_id} path must be a non-empty string")
        elif kind == "move":
            for field in ("from_path", "to_path"):
                if not isinstance(node.get(field), str) or not node.get(field):
                    errors.append(f"node {node_id} {field} must be a non-empty string")
        elif kind == "run":
            command = node.get("command")
            if not isinstance(command, list) or not command:
                errors.append(f"node {node_id} command must be a non-empty array")
            elif any(not isinstance(part, str) for part in command):
                errors.append(f"node {node_id} command entries must be strings")
            if "exclusive" in node and not isinstance(node["exclusive"], bool):
                errors.append(f"node {node_id} exclusive must be a boolean")
    return errors


def schema_errors(dag: Any) -> list[str]:
    """JSON Schema shape errors, using guarded-optional jsonschema when present."""
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return _internal_schema_errors(dag)
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        return [error.message for error in validator.iter_errors(dag)]
    except (OSError, json.JSONDecodeError, ValueError):
        return _internal_schema_errors(dag)


def structure_errors(dag: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(dag, dict):
        return ["dag must be an object"]
    nodes = node_map(dag)

    root = dag.get("root")
    if not isinstance(root, str) or root not in nodes:
        errors.append(f"root does not reference an existing node: {root!r}")
    elif node_type(dag, root) != SEMANTIC_TYPE:
        errors.append(f"root node {root} must be type semantic")

    for node_id in sorted(nodes):
        for child in direct_children(dag, node_id):
            if child not in nodes:
                errors.append(f"node {node_id} satisfied_by references missing node: {child}")

    reachable = reachable_from_root(dag)
    for node_id in sorted(nodes):
        if node_id not in reachable:
            errors.append(f"node {node_id} is not reachable from root")

    cycle = _find_cycle(dag)
    if cycle is not None:
        errors.append(f"satisfied_by path returns to an ancestor (cycle): {' -> '.join(cycle)}")

    for node_id in sorted(nodes):
        if not NODE_ID_PATTERN.match(node_id):
            errors.append(f"node {node_id} has invalid id; expected N<number>")

    errors.extend(run_barrier_errors(dag))
    return errors


def validate_dag(dag: Any) -> list[str]:
    errors = schema_errors(dag) + structure_errors(dag)
    seen: set[str] = set()
    deduped: list[str] = []
    for error in errors:
        if error not in seen:
            seen.add(error)
            deduped.append(error)
    return deduped


def mutability(dag: Any, state: Any, node_id: str) -> tuple[bool, str]:
    nodes = node_map(dag)
    if node_id not in nodes:
        return False, f"unknown node: {node_id}"
    if isinstance(dag, dict) and node_id == dag.get("root"):
        return False, "root is immutable"
    kind = node_type(dag, node_id)
    if kind in TERMINAL_TYPES:
        effective_state = state if isinstance(state, dict) else {}
        status = effective_state.get(node_id, "not_satisfied")
        if status == "satisfied":
            return False, "satisfied terminal work is immutable"
        return True, "mutable"
    if kind == SEMANTIC_TYPE:
        children = direct_children(dag, node_id)
        if not children:
            return True, "mutable"
        satisfaction = derived_satisfaction(dag, state)
        if all(satisfaction.get(child, False) for child in children):
            return False, "semantic subtree fully satisfied"
        return True, "mutable"
    return False, f"unknown node type: {kind!r}"


def output(payload: Any, title: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "output": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "title": title,
        "metadata": metadata or {},
    }
