"""Initial Change DAG creation from a handle-space semantic graph.

Creation reasons about an external semantic graph whose nodes are user-facing
handles, before any canonical DAG node ID exists. That is a different model from
mutation of an already-persisted DAG, so creation lives apart from the mutation
domain. Its validation must not be merged into :func:`change_dag.validate_dag`;
the two operate on different representations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import change_dag
from . import change_dag_state
from .change_dag_ops_support import _error, _locked_mutation, _persist


def _handle_cycle(root: str, nodes: dict[str, Any]) -> list[str] | None:
    color: dict[str, int] = {}
    path: list[str] = []

    def visit(handle: str) -> list[str] | None:
        color[handle] = 1
        path.append(handle)
        node = nodes.get(handle)
        refs = node.get("requires") if isinstance(node, dict) else None
        if isinstance(refs, list):
            for child in refs:
                if not isinstance(child, str) or child not in nodes:
                    continue
                state = color.get(child, 0)
                if state == 1:
                    return path[path.index(child):] + [child]
                if state == 0:
                    found = visit(child)
                    if found is not None:
                        return found
        color[handle] = 2
        path.pop()
        return None

    return visit(root)


def _bfs_order(root: str, nodes: dict[str, Any]) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()
    queue = [root]
    while queue:
        handle = queue.pop(0)
        if handle in seen or handle not in nodes:
            continue
        seen.add(handle)
        order.append(handle)
        node = nodes[handle]
        refs = node.get("requires") if isinstance(node, dict) else None
        if isinstance(refs, list):
            for child in sorted(ref for ref in refs if isinstance(ref, str)):
                if child not in seen:
                    queue.append(child)
    return order


def _validate_semantic_graph(semantic_graph: Any) -> tuple[list[str], list[str]]:
    if not isinstance(semantic_graph, dict):
        return ["semantic_graph must be an object"], []
    root = semantic_graph.get("root")
    nodes = semantic_graph.get("nodes")
    errors: list[str] = []
    if not isinstance(root, str) or not root:
        errors.append("root must be a non-empty handle")
    if not isinstance(nodes, dict) or not nodes:
        errors.append("nodes must be a non-empty object")
    if errors:
        return errors, []

    for handle, node in nodes.items():
        if not isinstance(handle, str) or not handle:
            errors.append(f"invalid handle: {handle!r}")
            continue
        if not isinstance(node, dict):
            errors.append(f"node {handle} must be an object")
            continue
        requirement = node.get("requirement")
        if not isinstance(requirement, str) or not requirement:
            errors.append(f"node {handle} requirement must be a non-empty string")
        for extra in sorted(set(node) - {"requirement", "requires"}):
            errors.append(f"node {handle} has unexpected field: {extra}")
        refs = node.get("requires")
        if refs is not None:
            if not isinstance(refs, list) or not refs:
                errors.append(f"node {handle} requires field must be a non-empty array")
            else:
                for ref in refs:
                    if not isinstance(ref, str) or not ref:
                        errors.append(f"node {handle} requires entries must be non-empty strings")
                    elif ref not in nodes:
                        errors.append(f"node {handle} requires references a missing handle: {ref}")
                if len(set(refs)) != len(refs):
                    errors.append(f"node {handle} requires entries must be unique")
    if errors:
        return errors, []
    assert isinstance(root, str)

    if root not in nodes:
        errors.append(f"root handle does not resolve: {root!r}")
        return errors, []

    # The root always decomposes into semantic requirements only. The canonical
    # root invariant is re-checked on the built DAG by change_dag.validate_dag;
    # this catches a root that supplies no children at all.
    root_refs = nodes[root].get("requires")
    if not isinstance(root_refs, list) or not root_refs:
        errors.append("root must directly require at least one semantic child")

    reachable = set(_bfs_order(root, nodes))
    for handle in nodes:
        if handle not in reachable:
            errors.append(f"node {handle} is not reachable from root")
    if errors:
        return errors, []

    cycle = _handle_cycle(root, nodes)
    if cycle is not None:
        errors.append(f"requires path returns to an ancestor (cycle): {' -> '.join(cycle)}")
        return errors, []

    return [], _bfs_order(root, nodes)


@_locked_mutation
def create_dag(workspace_root: Path, slug: str, semantic_graph: Any) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    try:
        change_dag.bundle_dir(workspace_root, slug)
    except ValueError as exc:
        return _error("invalid_slug", str(exc))
    if (
        change_dag.dag_json_path(workspace_root, slug).exists()
        or change_dag.dag_json_path(workspace_root, slug, True).exists()
    ):
        return _error("already_exists", f"change dag already exists: {slug}")

    errors, order = _validate_semantic_graph(semantic_graph)
    if errors:
        return _error("invalid_semantic_graph", "; ".join(errors), errors=errors)

    nodes = semantic_graph["nodes"]
    root_handle = semantic_graph["root"]
    anchor = change_dag.resolve_anchor_commit(workspace_root)
    handles: dict[str, str] = {}
    ordering_dag: dict[str, Any] = {"slug": slug, "anchor_commit": anchor, "root": "", "nodes": {}}
    for handle in order:
        node_id = change_dag.allocate_node_id(ordering_dag, workspace_root, slug)
        handles[handle] = node_id
        ordering_dag["nodes"][node_id] = {"type": change_dag.SEMANTIC_TYPE}

    built: dict[str, Any] = {}
    for handle in order:
        node = nodes[handle]
        entry: dict[str, Any] = {"type": change_dag.SEMANTIC_TYPE, "requirement": node["requirement"]}
        refs = node.get("requires")
        if refs:
            entry["requires"] = [handles[ref] for ref in refs]
        if handle == root_handle:
            # The root is always decomposition-only. The service sets it here;
            # callers never supply it in the semantic graph.
            entry["decomposition_only"] = True
        built[handles[handle]] = entry

    dag = {"slug": slug, "anchor_commit": anchor, "root": handles[root_handle], "nodes": built}
    dag_errors = change_dag.validate_dag(dag)
    if dag_errors:
        return _error("invalid_dag", "; ".join(dag_errors), errors=dag_errors)

    _persist(dag, workspace_root, slug)
    change_dag_state.write_state(workspace_root, slug, {})
    work_log = change_dag.work_log_path(workspace_root, slug)
    work_log.parent.mkdir(parents=True, exist_ok=True)
    if not work_log.exists():
        work_log.write_text("", encoding="utf-8")

    return change_dag.output(
        {
            "slug": slug,
            "anchor_commit": anchor,
            "root_node_id": handles[root_handle],
            "node_ids_by_handle": handles,
        },
        "Create Change DAG",
    )
