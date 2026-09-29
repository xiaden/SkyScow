"""Decomposition-frontier derivation for Change DAG construction.

Answers exactly the manager-facing question "which unresolved semantic branches
are currently the deepest branches ready for bounded worker authoring?" from the
canonical DAG graph and the existing resolution semantics. This is derived
authoring guidance only: it never affects runtime satisfaction, compiler
traversal, execution ordering, or executable/preflight meaning, and it never
infers a dependency the graph does not already express through ``requires``.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any

from . import change_dag
from .change_dag_ops_support import _error, _load, _numeric


# This service is deliberately process-local and bounded. Refs are capabilities for
# the next authoring call, not DAG state; Task C can replace this implementation
# without changing the frontier payload or its consumer-facing API.
_BRANCH_REF_LIMIT = 256
_BRANCH_REF_TTL_SECONDS = 15 * 60
_BRANCH_REFS: OrderedDict[str, tuple[float, str, str, tuple[str, ...]]] = OrderedDict()


def _dag_fingerprint(dag: Any) -> str:
    encoded = json.dumps(dag, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _prune_branch_refs(now: float | None = None) -> None:
    now = time.monotonic() if now is None else now
    expired = [ref for ref, entry in _BRANCH_REFS.items() if now - entry[0] >= _BRANCH_REF_TTL_SECONDS]
    for ref in expired:
        _BRANCH_REFS.pop(ref, None)
    while len(_BRANCH_REFS) > _BRANCH_REF_LIMIT:
        _BRANCH_REFS.popitem(last=False)


def _branch_components(dag: Any, frontier_nodes: list[str]) -> list[tuple[str, ...]]:
    """Partition frontier nodes by their graph-local branch incidence.

    A branch is seeded by the immediate semantic parents of the current
    frontier. Frontier siblings sharing a parent therefore start in one
    component, while root children remain separate because the root is a
    boundary, not a branch vertex. From those seeds, walk forward through the
    affected graph: convergence, shared descendants, and cross-links join the
    affected parent groups, but unrelated reachable subgraphs cannot join them.
    This is linear in the affected graph and never enumerates root-to-frontier
    paths.
    """
    root = dag.get("root")
    reachable = change_dag.reachable_from_root(dag)
    frontier = [node_id for node_id in frontier_nodes if node_id in reachable]
    if not frontier:
        return []

    parents: dict[str, list[str]] = {node_id: [] for node_id in frontier}
    for node_id in reachable:
        for child in change_dag.direct_children(dag, node_id):
            if child in parents:
                parents[child].append(node_id)

    component_parent = {node_id: node_id for node_id in frontier}

    def find(node_id: str) -> str:
        while component_parent[node_id] != node_id:
            component_parent[node_id] = component_parent[component_parent[node_id]]
            node_id = component_parent[node_id]
        return node_id

    def ensure(node_id: str) -> None:
        component_parent.setdefault(node_id, node_id)

    def union(left: str, right: str) -> None:
        ensure(left)
        ensure(right)
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            component_parent[right_root] = left_root

    # The first union is the required frontier-incidence seed. The root is a
    # boundary: do not let it join otherwise independent root branches.
    stack: list[str] = []
    queued: set[str] = set()
    for node_id in frontier:
        for parent_node in parents.get(node_id, ()):
            if parent_node == root:
                continue
            union(node_id, parent_node)
            if parent_node not in queued:
                queued.add(parent_node)
                stack.append(parent_node)

    # Walk forward from frontier nodes and their immediate parents. This catches
    # shared descendants and cross-links without traversing unrelated branches.
    queued.update(frontier)
    stack.extend(frontier)
    while stack:
        node_id = stack.pop()
        for child in change_dag.direct_children(dag, node_id):
            if child == root or child not in reachable:
                continue
            union(node_id, child)
            if child not in queued:
                queued.add(child)
                stack.append(child)

    groups: dict[str, list[str]] = {}
    for node_id in frontier:
        groups.setdefault(find(node_id), []).append(node_id)
    return [tuple(sorted(nodes, key=change_dag._numeric_id)) for nodes in groups.values()]


def _issue_branch_refs(dag: Any, components: list[tuple[str, ...]]) -> list[dict[str, Any]]:
    fingerprint = _dag_fingerprint(dag)
    _prune_branch_refs()
    result = []
    for nodes in sorted(components, key=lambda group: change_dag._numeric_id(group[0])):
        ref = secrets.token_urlsafe(24)
        _BRANCH_REFS[ref] = (time.monotonic(), str(dag.get("slug", "")), fingerprint, nodes)
        result.append({"branch_ref": ref, "available_work": len(nodes)})
    _prune_branch_refs()
    return result


def validate_branch_ref(ref: str, slug: str, dag: Any) -> bool:
    """Return whether an unconsumed ref belongs to this unchanged DAG and slug."""
    _prune_branch_refs()
    entry = _BRANCH_REFS.get(ref)
    return bool(entry and entry[1] == slug and entry[2] == _dag_fingerprint(dag))


def consume_branch_ref(ref: str, slug: str, dag: Any) -> tuple[str, ...] | None:
    """Validate and consume a ref, returning its ephemeral semantic node IDs once."""
    if not validate_branch_ref(ref, slug, dag):
        return None
    return _BRANCH_REFS.pop(ref)[3]


def decomposition_frontier(dag: Any) -> dict[str, Any]:
    """Return the deepest unresolved frontier as opaque, ephemeral branch refs.

    The unresolved-node/depth derivation is unchanged. Branch components are
    graph connected components after removing the root, so convergence and
    cross-links collapse without path enumeration. Refs are process-local,
    single-use capabilities and no ref or component is persisted.
    """
    unresolved = change_dag.unresolved_semantic_nodes(dag)
    if not unresolved:
        return {"resolved": True, "frontier": None}
    depths = change_dag.derived_depth(dag)
    located = [node_id for node_id in unresolved if node_id in depths]
    if not located:
        return {"resolved": False, "frontier": None}
    frontier_depth = max(depths[node_id] for node_id in located)
    frontier_nodes = [node_id for node_id in located if depths[node_id] == frontier_depth]
    return {
        "resolved": False,
        "frontier": {
            "depth": frontier_depth,
            "branches": _issue_branch_refs(dag, _branch_components(dag, frontier_nodes)),
        },
    }


def decomposition_frontier_view(workspace_root: Path, slug: str) -> dict[str, Any]:
    """Read-only tool projection: load ``slug`` and return its frontier."""
    workspace_root = Path(workspace_root)
    dag, _state, _location, err = _load(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None
    return change_dag.output(
        decomposition_frontier(dag),
        "Change DAG Decomposition Frontier",
        {"slug": slug},
    )


def _bounded_node_ref(dag: Any, node_id: str, scope: str) -> dict[str, Any]:
    """Bounded, graph-local identity for one neighbouring node.

    Only the node's canonical ID, its type, and the semantic requirement or
    terminal path/command identity that makes the neighbour recognisable are
    returned. Proposed content, patches, execution state, and repository
    evidence are never included.
    """
    node = change_dag.node_map(dag)[node_id]
    kind = node.get("type")
    ref: dict[str, Any] = {"id": node_id, "type": kind}
    if kind == change_dag.SEMANTIC_TYPE:
        ref["requirement"] = node.get("requirement")
    elif kind in ("create", "edit", "remove"):
        ref["path"] = node.get("path")
    elif kind == "move":
        ref["from_path"] = node.get("from_path")
        ref["to_path"] = node.get("to_path")
    elif kind == "run":
        ref["command"] = node.get("command")
    ref["scope"] = scope
    return ref


def decomposition_scope(dag: Any, node_id: str) -> dict[str, Any]:
    """Bounded graph-local decomposition context for one assigned semantic node.

    Answers exactly the Worker question "what exact semantic node do I own, what
    immediately surrounds it, and where am I in the decomposition?" from the
    canonical DAG graph alone: the target node, all immediate semantic parents,
    the deduplicated union of the other direct ``requires`` children of those
    parents, and the target's own direct children.

    This is derived authoring context only. It performs no repository discovery,
    compiles no patches, and includes no whole-DAG dump, no transitive ancestor
    tree, no prior worker summary, and no same-frontier peer authoring input. It
    never affects runtime satisfaction, compiler traversal, execution ordering,
    or executable/preflight meaning.
    """
    nodes = change_dag.node_map(dag)
    if node_id not in nodes:
        return _error("unknown_node", f"node not found: {node_id}")
    if change_dag.node_type(dag, node_id) != change_dag.SEMANTIC_TYPE:
        return _error(
            "invalid_target_node",
            "decomposition scope requires a semantic node; "
            f"{node_id} is {change_dag.node_type(dag, node_id)!r}",
        )

    # Immediate semantic parents: every node that directly requires the target.
    # A shared descendant legitimately has more than one, so this is never
    # modelled as a single parent.
    parents = sorted(
        (
            parent
            for parent in nodes
            if node_id in change_dag.direct_children(dag, parent)
        ),
        key=_numeric,
    )

    # Sibling union: the other direct ``requires`` children of every immediate
    # parent, deduplicated by canonical node identity. A shared child of two
    # parents appears once. The Worker may understand these; it does not own them.
    sibling_ids: set[str] = set()
    for parent in parents:
        for child in change_dag.direct_children(dag, parent):
            if child != node_id and child in nodes:
                sibling_ids.add(child)

    children = [
        child for child in change_dag.direct_children(dag, node_id) if child in nodes
    ]

    depths = change_dag.derived_depth(dag)
    return {
        "target": {
            "id": node_id,
            "requirement": nodes[node_id].get("requirement"),
            "depth": depths.get(node_id),
            "decomposition_only": nodes[node_id].get("decomposition_only") is True,
            "resolved": change_dag.semantic_node_resolved(dag, node_id),
            "scope": "assigned",
        },
        "parents": [
            {
                "id": parent,
                "requirement": nodes[parent].get("requirement"),
                "scope": "context_only",
            }
            for parent in parents
        ],
        "siblings": [
            _bounded_node_ref(dag, sibling, "out_of_scope")
            for sibling in sorted(sibling_ids, key=_numeric)
        ],
        "children": [
            _bounded_node_ref(dag, child, "context_only")
            for child in sorted(children, key=_numeric)
        ],
    }


def semantic_search(
    dag: Any, query: str, limit: int = 20
) -> dict[str, Any]:
    """Search reachable semantic requirements without exposing work nodes."""
    nodes = change_dag.node_map(dag)
    depths = change_dag.derived_depth(dag)
    reachable = change_dag.reachable_from_root(dag)
    query_text = query.casefold()
    tokens = {token for token in query_text.split() if token}
    matches: list[tuple[int, str]] = []
    for node_id, node in nodes.items():
        if node.get("type") != change_dag.SEMANTIC_TYPE or node_id not in reachable:
            continue
        requirement = node.get("requirement")
        if not isinstance(requirement, str):
            continue
        text = requirement.casefold()
        score = sum(1 for token in tokens if token in text)
        if query_text and query_text in text:
            score += 1
        if score:
            matches.append((score, node_id))
    matches.sort(key=lambda item: (-item[0], _numeric(item[1])))
    return {
        "results": [
            {
                "node_id": node_id,
                "requirement": nodes[node_id].get("requirement"),
                "depth": depths[node_id],
            }
            for _score, node_id in matches[: max(0, limit)]
            if node_id in depths
        ]
    }


def semantic_search_view(
    workspace_root: Path, slug: str, query: str, limit: int = 20
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    dag, _state, _location, err = _load(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None
    payload = semantic_search(dag, query, limit)
    return change_dag.output(
        {"slug": slug, "query": query, **payload},
        "Change DAG Semantic Search",
        {"slug": slug, "query": query},
    )


def semantic_context(dag: Any, node_ids: list[str]) -> dict[str, Any]:
    """Return compact semantic-only context for requested reachable nodes."""
    if len(node_ids) > 25:
        return _error("too_many_nodes", "node_ids must contain no more than 25 nodes")
    nodes = change_dag.node_map(dag)
    reachable = change_dag.reachable_from_root(dag)
    for node_id in node_ids:
        if node_id not in nodes:
            return _error("unknown_node", f"node not found: {node_id}")
        if nodes[node_id].get("type") != change_dag.SEMANTIC_TYPE:
            return _error(
                "invalid_target_node",
                f"semantic context requires a semantic node; {node_id} is {nodes[node_id].get('type')!r}",
            )
        if node_id not in reachable:
            return _error("invalid_target_node", f"node is not reachable from the DAG root: {node_id}")

    depths = change_dag.derived_depth(dag)
    requested = set(node_ids)
    parent_ids: set[str] = set()
    require_ids: set[str] = set()
    for parent_id, parent in nodes.items():
        if parent.get("type") != change_dag.SEMANTIC_TYPE or parent_id not in reachable:
            continue
        children = change_dag.direct_children(dag, parent_id)
        if any(child in requested for child in children):
            parent_ids.add(parent_id)
    for node_id in node_ids:
        require_ids.update(
            child for child in change_dag.direct_children(dag, node_id)
            if child in nodes and nodes[child].get("type") == change_dag.SEMANTIC_TYPE
            and child in reachable
        )

    ancestor_ids: set[str] = set()
    frontier = set(parent_ids)
    while frontier:
        ancestor_ids.update(frontier)
        next_frontier: set[str] = set()
        for candidate in frontier:
            for parent_id, parent in nodes.items():
                if parent.get("type") == change_dag.SEMANTIC_TYPE and parent_id in reachable and candidate in change_dag.direct_children(dag, parent_id):
                    next_frontier.add(parent_id)
        frontier = next_frontier - ancestor_ids
    return {
        "nodes": [
            {
                "id": node_id,
                "requirement": nodes[node_id].get("requirement"),
                "depth": depths.get(node_id),
                "decomposition_only": nodes[node_id].get("decomposition_only") is True,
                "resolved": change_dag.semantic_node_resolved(dag, node_id),
            }
            for node_id in sorted(requested, key=_numeric)
        ],
        "parents": [
            {"id": node_id, "requirement": nodes[node_id].get("requirement")}
            for node_id in sorted(parent_ids, key=_numeric)
        ],
        "requires": [
            {"id": node_id, "type": "semantic", "requirement": nodes[node_id].get("requirement")}
            for node_id in sorted(require_ids, key=_numeric)
        ],
        "ancestors": [
            {"id": node_id, "requirement": nodes[node_id].get("requirement"), "depth": depths.get(node_id)}
            for node_id in sorted(ancestor_ids - parent_ids, key=_numeric)
        ],
    }


def semantic_context_view(
    workspace_root: Path, slug: str, node_ids: list[str]
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    dag, _state, _location, err = _load(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None
    payload = semantic_context(dag, node_ids)
    if "error" in payload:
        return payload
    return change_dag.output(
        {"slug": slug, **payload},
        "Change DAG Semantic Context",
        {"slug": slug, "node_ids": node_ids},
    )


def decomposition_scope_view(
    workspace_root: Path, slug: str, node_id: str
) -> dict[str, Any]:
    """Read-only tool projection: load ``slug`` and return the node's scope."""
    workspace_root = Path(workspace_root)
    dag, _state, _location, err = _load(workspace_root, slug)
    if err is not None:
        return err
    assert dag is not None
    payload = decomposition_scope(dag, node_id)
    if "error" in payload:
        return payload
    return change_dag.output(
        payload,
        "Change DAG Decomposition Scope",
        {"slug": slug, "node_id": node_id},
    )
