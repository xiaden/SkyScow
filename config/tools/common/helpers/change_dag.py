"""Core Change DAG model: validation, derived properties, and persistence.

The Change DAG is the declarative definition of the work required to satisfy a
root requirement. It contains no runtime execution state and no execution
history. ``requires`` is the only graph edge; it means ALL-of and expresses
what must become true for a semantic requirement to be fulfilled.

This module is intentionally stdlib-only except for a *guarded optional*
``jsonschema`` import used to enforce the shipped JSON Schema shape. When
``jsonschema`` is unavailable a minimal internal shape check is used so the
module never gains a hard runtime dependency.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

CHANGE_DAGS_DIR = "artifacts/change-dags"
PENDING_DIR = "artifacts/change-dags/pending"
ARCHIVED_DIR = "artifacts/change-dags/archived"
DAG_FILENAME = "DAG.json"
STATE_FILENAME = "EXECUTION_STATE.json"
WORK_LOG_FILENAME = "WORK_LOG.jsonl"
NODE_SEQ_FILENAME = ".node_seq"

NODE_ID_PATTERN = re.compile(r"^N[0-9]+$")
ANCHOR_COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{7,64}$")
TERMINAL_STATES = ("not_satisfied", "in_progress", "satisfied", "failed")
TERMINAL_TYPES = ("create", "edit", "remove", "move", "run")
# Direct terminal children that are exclusive: when a semantic node owns any of
# these, it may own no other terminal child. ``edit`` is composable and is not
# listed here. This is authoring structure only and grants no runtime
# run-barrier semantics to create/move/remove.
EXCLUSIVE_TERMINAL_TYPES = ("create", "remove", "move", "run")
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
    "semantic": {"type", "requirement", "requires", "decomposition_only"},
    "create": {"type", "path", "content"},
    "edit": {"type", "path", "patch"},
    "remove": {"type", "path"},
    "move": {"type", "from_path", "to_path", "overwrite"},
    "run": {"type", "command", "exclusive"},
}
_ROOT_KEYS = {"slug", "anchor_commit", "root", "nodes"}


# ---------------------------------------------------------------------------
# Canonical node paths
# ---------------------------------------------------------------------------
# Compiled files are grouped, coordinated, and reported by one canonical
# workspace-relative identity. Two spellings that name the same repository file
# (``foo.py``, ``./foo.py``, ``src/../foo.py``) must never compile independently.
_PATH_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def canonical_path(path: Any) -> str:
    """Return the canonical workspace-relative identity of a DAG file path.

    Normalization is purely lexical -- no filesystem or symlink inspection -- and
    drops ``.`` components, resolves ``..``, collapses redundant separators, and
    renders the result with ``/`` separators.

    Raises :class:`ValueError` for forms that cannot be represented consistently
    as a workspace-relative DAG path: non-strings, empty strings, NUL bytes,
    backslash separators, absolute or drive-qualified paths, home-relative ``~``
    paths, directory-like trailing separators, and ``..`` that escapes the root.
    """
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    if not path:
        raise ValueError("path must be a non-empty string")
    if "\x00" in path:
        raise ValueError("path must not contain NUL bytes")
    if "\\" in path:
        raise ValueError(f"path must use '/' separators, not backslashes: {path!r}")
    if path.startswith("/") or _PATH_DRIVE_RE.match(path):
        raise ValueError(f"path must be workspace-relative, not absolute: {path!r}")
    if path.startswith("~"):
        raise ValueError(f"path must be workspace-relative, not home-relative: {path!r}")
    if path.endswith("/"):
        raise ValueError(f"path must name a file, not a directory: {path!r}")
    parts: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ValueError(f"path escapes the workspace root: {path!r}")
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        raise ValueError(f"path does not name a file: {path!r}")
    return "/".join(parts)


def node_path_fields(kind: str | None) -> tuple[str, ...]:
    """Path-bearing fields of a mechanical node type."""
    if kind in ("create", "edit", "remove"):
        return ("path",)
    if kind == "move":
        return ("from_path", "to_path")
    return ()


# ---------------------------------------------------------------------------
# Paths and IO
# ---------------------------------------------------------------------------
def _safe_slug(slug: Any) -> str:
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("slug must be non-empty")
    if slug in {".", ".."} or "/" in slug or "\\" in slug:
        raise ValueError(f"invalid slug: {slug!r}")
    return slug


def bundle_dir(workspace_root: Path, slug: str, archived: bool = False) -> Path:
    safe = _safe_slug(slug)
    base = ARCHIVED_DIR if archived else PENDING_DIR
    return Path(workspace_root) / base / safe


def dag_json_path(workspace_root: Path, slug: str, archived: bool = False) -> Path:
    return bundle_dir(workspace_root, slug, archived) / DAG_FILENAME


def state_json_path(workspace_root: Path, slug: str, archived: bool = False) -> Path:
    return bundle_dir(workspace_root, slug, archived) / STATE_FILENAME


def work_log_path(workspace_root: Path, slug: str, archived: bool = False) -> Path:
    return bundle_dir(workspace_root, slug, archived) / WORK_LOG_FILENAME


def locate_dag(workspace_root: Path, slug: str) -> tuple[Path | None, str | None]:
    """Locate a DAG bundle as ``pending`` or ``archived``.

    The archive location means only that the bundle was retired from the pending
    working set. It is deliberately not named "completed": membership in the
    archive is not evidence that execution succeeded or was verified.
    """
    pending = dag_json_path(workspace_root, slug, False)
    if pending.is_file():
        return pending, "pending"
    archived = dag_json_path(workspace_root, slug, True)
    if archived.is_file():
        return archived, "archived"
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


def canonical_dag_digest(dag: Any) -> str:
    """Return the deterministic identity of the canonical DAG object."""
    encoded = json.dumps(dag, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
    refs = node.get("requires")
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


def decomposition_only_errors(dag: Any) -> list[str]:
    """Structural invariant for a node that declares no direct terminal work.

    ``decomposition_only`` is persisted authoring intent, not runtime state: the
    node's obligation is fully decomposed into the semantic requirements it
    directly ``requires``. It is therefore legal only on a semantic node that
    directly requires at least one child, and every direct child must itself be
    semantic. A direct create/edit/remove/move/run child is structurally invalid.
    """
    errors: list[str] = []
    nodes = node_map(dag)
    for node_id in sorted(nodes):
        if node_type(dag, node_id) != SEMANTIC_TYPE:
            continue
        if nodes[node_id].get("decomposition_only") is not True:
            continue
        children = direct_children(dag, node_id)
        if not children:
            errors.append(
                f"decomposition_only semantic node {node_id} must directly require "
                "at least one semantic child"
            )
            continue
        for child in children:
            child_type = node_type(dag, child)
            if child_type is not None and child_type != SEMANTIC_TYPE:
                errors.append(
                    f"decomposition_only semantic node {node_id} has a non-semantic child: "
                    f"{child} ({child_type})"
                )
    return errors


def root_invariant_errors(dag: Any) -> list[str]:
    """The root semantic node never owns direct terminal work.

    The root is the overall intent and always decomposes into semantic
    requirements only: it must carry ``decomposition_only=true``, directly
    require at least one child, and every direct child must be semantic. This is
    an explicit root-specific invariant. The generic
    :func:`decomposition_only_errors` rule only constrains nodes that opt in, so
    a root that silently omits the flag would otherwise validate.
    """
    errors: list[str] = []
    nodes = node_map(dag)
    root = dag.get("root") if isinstance(dag, dict) else None
    if not isinstance(root, str) or root not in nodes:
        return errors  # a missing/invalid root is reported by structure_errors
    if node_type(dag, root) != SEMANTIC_TYPE:
        return errors  # a non-semantic root is reported by structure_errors
    if nodes[root].get("decomposition_only") is not True:
        errors.append(f"root semantic node {root} must have decomposition_only=true")
    children = direct_children(dag, root)
    if not children:
        errors.append(
            f"root semantic node {root} must directly require at least one semantic child"
        )
    for child in children:
        child_type = node_type(dag, child)
        if child_type is not None and child_type != SEMANTIC_TYPE:
            errors.append(
                f"root semantic node {root} must not directly require terminal work: "
                f"{child} ({child_type})"
            )
    return errors


def direct_terminal_errors(dag: Any) -> list[str]:
    """Direct-terminal composition invariant for every semantic node.

    Over a semantic node's *direct* children:

    * semantic children are always allowed, in any number;
    * ``edit`` children are composable: any number may coexist with each other
      and with semantic children;
    * ``create``, ``remove``, ``move`` and ``run`` are *exclusive*: when a
      semantic node has any exclusive terminal child, that child must be its
      only terminal child.

    So ``edit + edit``, ``create + semantic``, ``run + semantic`` and
    ``edit + semantic`` validate, while ``create + edit``, ``run + edit``,
    ``create + create`` and ``move + remove`` do not. This is an authoring
    structural rule only; it grants no runtime run-barrier semantics to
    ``create``/``remove``/``move``.
    """
    errors: list[str] = []
    nodes = node_map(dag)
    for node_id in sorted(nodes):
        if node_type(dag, node_id) != SEMANTIC_TYPE:
            continue
        children = direct_children(dag, node_id)
        terminal_children = [
            child for child in children if node_type(dag, child) in TERMINAL_TYPES
        ]
        exclusive_children = [
            child
            for child in terminal_children
            if node_type(dag, child) in EXCLUSIVE_TERMINAL_TYPES
        ]
        if not exclusive_children or len(terminal_children) == 1:
            continue
        run_children = [child for child in terminal_children if node_type(dag, child) == "run"]
        if len(run_children) > 1:
            errors.append(
                f"semantic node {node_id} has multiple direct run children: {', '.join(run_children)}"
            )
        for exclusive in exclusive_children:
            exclusive_type = node_type(dag, exclusive)
            for child in terminal_children:
                if child == exclusive:
                    continue
                child_type = node_type(dag, child)
                if exclusive_type == "run" and child_type == "run":
                    continue  # reported once as multiple direct run children
                if exclusive_type == "run":
                    errors.append(
                        f"semantic node {node_id} has a non-semantic child beside a run child: "
                        f"{child} ({child_type})"
                    )
                else:
                    errors.append(
                        f"semantic node {node_id} has exclusive terminal child {exclusive} "
                        f"({exclusive_type}) beside sibling terminal {child} ({child_type})"
                    )
    seen: set[str] = set()
    deduped: list[str] = []
    for error in errors:
        if error not in seen:
            seen.add(error)
            deduped.append(error)
    return deduped


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


def semantic_node_resolved(dag: Any, node_id: str) -> bool:
    """Whether a semantic node's authoring obligation is locally expressed.

    A semantic node is locally resolved in exactly one of two ways:

    1. it declares ``decomposition_only=true`` and directly requires one or more
       semantic children only; or
    2. it directly requires at least one terminal work node.

    A node with no ``requires`` is unresolved. Semantic children alone, without
    the decomposition flag, do not resolve the node. A ``decomposition_only``
    node with a direct terminal child is structurally invalid and is not a
    resolution shortcut.

    This is derived authoring state only. It never affects runtime satisfaction,
    compiler traversal, execution ordering, or executable/preflight meaning.
    """
    node = node_map(dag).get(node_id)
    if not isinstance(node, dict) or node.get("type") != SEMANTIC_TYPE:
        return False
    children = direct_children(dag, node_id)
    if not children:
        return False
    if node.get("decomposition_only") is True:
        return all(node_type(dag, child) == SEMANTIC_TYPE for child in children)
    return any(node_type(dag, child) in TERMINAL_TYPES for child in children)


def is_resolved(dag: Any) -> bool:
    """Whether every reachable semantic node is locally resolved."""
    reachable = reachable_from_root(dag)
    return all(
        semantic_node_resolved(dag, node_id)
        for node_id in reachable
        if node_type(dag, node_id) == SEMANTIC_TYPE
    )


def unresolved_semantic_nodes(dag: Any) -> list[str]:
    """Reachable semantic nodes whose authoring obligation is not locally resolved.

    Replaces the earlier ``unresolved_leaves`` concept: an unresolved semantic
    node may already have semantic children and need not be a graph leaf.
    """
    reachable = reachable_from_root(dag)
    unresolved = [
        node_id
        for node_id in reachable
        if node_type(dag, node_id) == SEMANTIC_TYPE
        and not semantic_node_resolved(dag, node_id)
    ]
    return sorted(unresolved, key=_numeric_id)


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
            if "requires" in node:
                refs = node["requires"]
                if not isinstance(refs, list) or not refs:
                    errors.append(f"node {node_id} requires field must be a non-empty array")
                elif any(not isinstance(ref, str) or not ref for ref in refs):
                    errors.append(f"node {node_id} requires entries must be non-empty strings")
                elif len(set(refs)) != len(refs):
                    errors.append(f"node {node_id} requires entries must be unique")
            if "decomposition_only" in node and not isinstance(node["decomposition_only"], bool):
                errors.append(f"node {node_id} decomposition_only must be a boolean")
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
            if "overwrite" in node and not isinstance(node["overwrite"], bool):
                errors.append(f"node {node_id} overwrite must be a boolean")
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
                errors.append(f"node {node_id} requires references a missing node: {child}")

    reachable = reachable_from_root(dag)
    for node_id in sorted(nodes):
        if node_id not in reachable:
            errors.append(f"node {node_id} is not reachable from root")

    cycle = _find_cycle(dag)
    if cycle is not None:
        errors.append(f"requires path returns to an ancestor (cycle): {' -> '.join(cycle)}")

    for node_id in sorted(nodes):
        if not NODE_ID_PATTERN.match(node_id):
            errors.append(f"node {node_id} has invalid id; expected N<number>")

    for node_id in sorted(nodes):
        for field in node_path_fields(node_type(dag, node_id)):
            raw = nodes[node_id].get(field)
            if not isinstance(raw, str) or not raw:
                continue  # shape errors already report missing/non-string values
            try:
                canonical_path(raw)
            except ValueError as exc:
                errors.append(
                    f"node {node_id} {field} is not a usable workspace-relative path: {exc}"
                )

    errors.extend(direct_terminal_errors(dag))
    errors.extend(decomposition_only_errors(dag))
    errors.extend(root_invariant_errors(dag))
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
