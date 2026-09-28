"""Focused tests for the Change DAG shared ops layer and thin tool modules."""
from __future__ import annotations

import json

from common.helpers.change_dag import (
    NODE_ID_PATTERN,
    atomic_write_json,
    dag_json_path,
    read_json,
    state_json_path,
    work_log_path,
)
from common.helpers.change_dag_control import (
    acquire_lock,
    release_lock,
    remove_marker,
    write_marker,
)
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import (
    add_requirement,
    add_work,
    remove_node,
    set_decomposition_only,
    update_node,
)
from common.helpers.change_dag_ops_views import preview, show, validate
from common.helpers.change_dag_state import write_state
from common.tools.dag_show import dag_show
from common.tools.dag_status import dag_status
from common.tools.dag_set_decomposition_only import dag_set_decomposition_only

PATCH = "@@ -1 +1 @@\n-a\n+b\n"


def _payload(result: dict) -> dict:
    return json.loads(result["output"])


def _ids(result: dict) -> dict:
    return _payload(result)["node_ids_by_handle"]


def _two_node_dag(workspace) -> None:
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "done", "requires": ["impl"]},
                "impl": {"requirement": "impl"},
            },
        },
    )


def _three_level_dag(workspace) -> None:
    # BFS canonical IDs: root=N1, mid=N2, leaf=N3 (all semantic).
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["mid"]},
                "mid": {"requirement": "mid", "requires": ["leaf"]},
                "leaf": {"requirement": "leaf"},
            },
        },
    )


# ---------------------------------------------------------------------------
# create_dag
# ---------------------------------------------------------------------------
def test_create_dag_valid_and_invalid_writes_nothing(workspace):
    invalid = create_dag(workspace, "bad", {"root": "r", "nodes": {"r": {"requirement": ""}}})
    assert invalid["error"] == "invalid_semantic_graph"
    assert not dag_json_path(workspace, "bad").exists()

    missing = create_dag(
        workspace,
        "bad2",
        {"root": "r", "nodes": {"r": {"requirement": "x", "requires": ["ghost"]}}},
    )
    assert missing["error"] == "invalid_semantic_graph"
    assert not dag_json_path(workspace, "bad2").exists()

    orphan = create_dag(
        workspace,
        "bad3",
        {"root": "r", "nodes": {"r": {"requirement": "x"}, "orphan": {"requirement": "y"}}},
    )
    assert orphan["error"] == "invalid_semantic_graph"
    assert not dag_json_path(workspace, "bad3").exists()

    good = create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "done", "requires": ["impl"]},
                "impl": {"requirement": "impl"},
            },
        },
    )
    data = _payload(good)
    assert data["root_node_id"] == "N1"
    assert data["node_ids_by_handle"] == {"root": "N1", "impl": "N2"}
    assert dag_json_path(workspace, "demo").exists()
    assert state_json_path(workspace, "demo").exists()
    assert work_log_path(workspace, "demo").exists()

    duplicate = create_dag(
        workspace,
        "demo",
        {"root": "root", "nodes": {"root": {"requirement": "again"}}},
    )
    assert duplicate["error"] == "already_exists"


# ---------------------------------------------------------------------------
# add_requirement
# ---------------------------------------------------------------------------
def test_add_requirement_unresolved_leaf_and_insert_between_rewiring(workspace):
    _two_node_dag(workspace)

    inserted = add_requirement(workspace, "demo", "inserted", ["N1"], ["N2"])
    new_id = _payload(inserted)["node_id"]
    assert new_id == "N3"
    dag = read_json(dag_json_path(workspace, "demo"))
    assert dag["nodes"]["N1"]["requires"] == ["N3"]
    assert dag["nodes"]["N3"]["requires"] == ["N2"]

    leaf = add_requirement(workspace, "demo", "a new open requirement", ["N3"])
    leaf_id = _payload(leaf)["node_id"]
    assert leaf_id == "N4"
    dag = read_json(dag_json_path(workspace, "demo"))
    assert "requires" not in dag["nodes"][leaf_id]
    assert dag["nodes"]["N3"]["requires"] == ["N2", leaf_id]


def test_add_requirement_rejects_bad_child_and_non_semantic_parent(workspace):
    _two_node_dag(workspace)
    add_work(workspace, "demo", "edit", ["N2"], path="x.txt", patch=PATCH)

    bad_child = add_requirement(workspace, "demo", "r", ["N1"], ["N3"])
    assert bad_child["error"] == "invalid_child"
    non_semantic = add_requirement(workspace, "demo", "r", ["N3"])
    assert non_semantic["error"] == "invalid_parent"


# ---------------------------------------------------------------------------
# add_work / run policy
# ---------------------------------------------------------------------------
def test_add_work_run_barrier_rejection(workspace):
    _two_node_dag(workspace)
    assert add_work(workspace, "demo", "edit", ["N2"], path="x.txt", patch=PATCH).get("error") is None

    outcome = add_work(workspace, "demo", "run", ["N2"], command=["pytest"])
    assert outcome["error"] == "invalid_graph"
    assert any("run" in message for message in outcome["errors"])


def test_add_work_run_command_policy_rejection(workspace):
    _two_node_dag(workspace)
    outcome = add_work(workspace, "demo", "run", ["N2"], command=["git", "commit", "-m", "x"])
    assert outcome["error"] == "run_command_rejected"


# ---------------------------------------------------------------------------
# update_node
# ---------------------------------------------------------------------------
def test_update_node_satisfied_terminal_immutable_failed_mutable(workspace):
    _two_node_dag(workspace)
    add_work(workspace, "demo", "edit", ["N2"], path="x.txt", patch=PATCH)

    write_state(workspace, "demo", {"N3": "satisfied"})
    rejected = update_node(workspace, "demo", "N3", path="y.txt")
    assert rejected["error"] == "immutable_node"

    write_state(workspace, "demo", {"N3": "failed"})
    allowed = update_node(workspace, "demo", "N3", path="y.txt")
    assert allowed.get("output") is not None
    dag = read_json(dag_json_path(workspace, "demo"))
    assert dag["nodes"]["N3"]["path"] == "y.txt"


# ---------------------------------------------------------------------------
# remove_node
# ---------------------------------------------------------------------------
def test_remove_node_preserves_shared_descendants(workspace):
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "r", "requires": ["left", "right"]},
                "left": {"requirement": "l", "requires": ["shared"]},
                "right": {"requirement": "rt", "requires": ["shared"]},
                "shared": {"requirement": "s"},
            },
        },
    )
    # BFS canonical IDs: root=N1, left=N2, right=N3, shared=N4.
    add_work(workspace, "demo", "edit", ["N4"], path="x.txt", patch=PATCH)

    result = remove_node(workspace, "demo", "N2")
    payload = _payload(result)
    assert payload["removed"] == ["N2"]
    assert payload["gc"] == []
    dag = read_json(dag_json_path(workspace, "demo"))
    assert "N2" not in dag["nodes"]
    assert "N4" in dag["nodes"]
    assert "N5" in dag["nodes"]
    assert dag["nodes"]["N1"]["requires"] == ["N3"]


def test_remove_node_gcs_mutable_unreachable_descendants(workspace):
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "r", "requires": ["mid", "other"]},
                "mid": {"requirement": "m", "requires": ["leaf"]},
                "other": {"requirement": "o"},
                "leaf": {"requirement": "l"},
            },
        },
    )
    # BFS canonical IDs: root=N1, mid=N2, other=N3, leaf=N4. Removing mid leaves
    # the root a valid semantic child (other) and GCs the unreachable leaf.
    result = remove_node(workspace, "demo", "N2")
    payload = _payload(result)
    assert payload["removed"] == ["N2", "N4"]
    assert payload["gc"] == ["N4"]
    dag = read_json(dag_json_path(workspace, "demo"))
    assert set(dag["nodes"]) == {"N1", "N3"}
    assert dag["nodes"]["N1"]["requires"] == ["N3"]


def test_remove_node_rejects_root(workspace):
    _two_node_dag(workspace)
    assert remove_node(workspace, "demo", "N1")["error"] == "root_immutable"


# ---------------------------------------------------------------------------
# preview / validate
# ---------------------------------------------------------------------------
def test_preview_reports_compile_conflict_with_both_node_ids(workspace):
    _two_node_dag(workspace)
    add_work(workspace, "demo", "create", ["N2"], path="new.txt", content="one\n")
    add_work(workspace, "demo", "create", ["N2"], path="new.txt", content="two\n")

    result = preview(workspace, "demo")
    payload = _payload(result)
    assert payload["conflicts"], payload
    conflict = payload["conflicts"][0]
    assert set(conflict["nodes"]) == {"N3", "N4"}
    assert conflict["reason"].startswith("compile_conflict:")
    assert payload["executable"] is False


def test_validate_reports_derived_schema_executable_resolved(workspace):
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "r", "requires": ["open", "impl"]},
                "open": {"requirement": "still open"},
                "impl": {"requirement": "impl"},
            },
        },
    )
    # BFS: root=N1, open=N2, impl=N3.
    add_work(workspace, "demo", "create", ["N3"], path="new.txt", content="x\n")

    first = _payload(validate(workspace, "demo"))
    assert first["schema_valid"] is True
    assert first["executable"] is False
    assert first["resolved"] is False
    assert first["unresolved_semantic_nodes"] == ["N2"]
    unresolved = [issue for issue in first["issues"] if issue["kind"] == "unresolved"]
    assert len(unresolved) == 1
    assert unresolved[0]["nodes"] == ["N2"]

    add_work(workspace, "demo", "create", ["N3"], path="new.txt", content="y\n")
    second = _payload(validate(workspace, "demo"))
    assert second["schema_valid"] is True
    assert second["executable"] is False
    assert any(issue["kind"] == "compile_conflict" for issue in second["issues"])


def test_validate_resolved_true_when_every_semantic_node_locally_resolved(workspace):
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "r", "requires": ["impl"]},
                "impl": {"requirement": "impl"},
            },
        },
    )
    # BFS: root=N1, impl=N2. The root decomposes into a semantic child, and impl
    # directly requires terminal work, so every semantic node is locally resolved.
    add_work(workspace, "demo", "create", ["N2"], path="new.txt", content="x\n")
    payload = _payload(validate(workspace, "demo"))
    assert payload["schema_valid"] is True
    assert payload["executable"] is True
    assert payload["resolved"] is True


def test_dag_status_reports_unresolved_semantic_nodes(workspace):
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "r", "requires": ["deferred"]},
                "deferred": {"requirement": "still open"},
            },
        },
    )
    # BFS: root=N1, deferred=N2. The root is always decomposition_only, so it is
    # locally resolved; only the deferred semantic leaf is unresolved.
    payload = dag_status("demo", workspace_root=workspace)
    assert payload["unresolved_semantic_nodes"] == ["N2"]

    add_work(workspace, "demo", "create", ["N2"], path="new.txt", content="x\n")
    payload = dag_status("demo", workspace_root=workspace)
    # N2 now directly requires terminal work, so every semantic node is resolved.
    assert payload["unresolved_semantic_nodes"] == []


def test_dag_status_terminal_map_contains_terminal_nodes_only(workspace):
    _two_node_dag(workspace)
    # BFS: root=N1, impl=N2; the terminal edit lands under N2 as N3.
    added = _payload(add_work(workspace, "demo", "edit", ["N2"], path="x.txt", patch=PATCH))
    terminal_id = added["node_id"]
    # A raw state may carry semantic entries; the projection must drop them.
    write_state(workspace, "demo", {"N1": "failed", "N2": "not_satisfied", terminal_id: "satisfied"})

    payload = dag_status("demo", workspace_root=workspace)

    assert payload["terminal"] == {terminal_id: "satisfied"}
    assert payload["failed"] == []
    assert payload["reachable"] == ["N1", "N2", terminal_id]
    # Semantic satisfaction stays derived, not projected as terminal state.
    assert payload["root_satisfied"] is True


# ---------------------------------------------------------------------------
# Running immutability
# ---------------------------------------------------------------------------
def test_mutations_rejected_while_dag_running(workspace):
    _two_node_dag(workspace)
    acquired, fd = acquire_lock(workspace)
    assert acquired
    try:
        write_marker(workspace, "demo", 99999999)
        assert add_work(workspace, "demo", "edit", ["N2"], path="x.txt", patch=PATCH)["error"] == "dag_running_immutable"
        assert add_requirement(workspace, "demo", "r", ["N2"])["error"] == "dag_running_immutable"
        assert remove_node(workspace, "demo", "N2")["error"] == "dag_running_immutable"
        assert update_node(workspace, "demo", "N2", requirement="changed")["error"] == "dag_running_immutable"
        assert set_decomposition_only(workspace, "demo", "N2", True)["error"] == "dag_running_immutable"
    finally:
        remove_marker(workspace)
        release_lock(fd)
    # create is intentionally not gated by running immutability
    created = create_dag(
        workspace,
        "other",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "ok", "requires": ["child"]},
                "child": {"requirement": "child"},
            },
        },
    )
    assert created.get("output") is not None


# ---------------------------------------------------------------------------
# ID discipline
# ---------------------------------------------------------------------------
def test_node_ids_are_canonical_and_monotonic(workspace):
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "r", "requires": ["a", "b"]},
                "a": {"requirement": "a"},
                "b": {"requirement": "b"},
            },
        },
    )
    dag = read_json(dag_json_path(workspace, "demo"))
    allocated = sorted(int(node_id[1:]) for node_id in dag["nodes"])
    assert allocated == [1, 2, 3]
    for node_id in dag["nodes"]:
        assert NODE_ID_PATTERN.fullmatch(node_id)

    previous = 3
    for index in range(4):
        result = add_work(workspace, "demo", "create", ["N3"], path=f"f{index}.txt", content="x\n")
        node_id = _payload(result)["node_id"]
        assert NODE_ID_PATTERN.fullmatch(node_id)
        numeric = int(node_id[1:])
        assert numeric > previous
        previous = numeric

    final = read_json(dag_json_path(workspace, "demo"))
    numeric_ids = [int(node_id[1:]) for node_id in final["nodes"]]
    assert len(numeric_ids) == len(set(numeric_ids))



# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------
def test_show_full_view_lists_every_node_with_derived_depth(workspace):
    _three_level_dag(workspace)
    add_work(workspace, "demo", "edit", ["N3"], path="x.txt", patch=PATCH)

    payload = _payload(show(workspace, "demo"))
    assert payload["slug"] == "demo"
    assert payload["root"] == "N1"
    assert isinstance(payload["anchor_commit"], str) and payload["anchor_commit"]
    assert [node["id"] for node in payload["nodes"]] == ["N1", "N2", "N3", "N4"]
    assert {node["id"]: node["depth"] for node in payload["nodes"]} == {
        "N1": 0,
        "N2": 1,
        "N3": 2,
        "N4": 3,
    }
    assert payload["nodes"][0]["type"] == "semantic"
    assert payload["nodes"][-1]["type"] == "edit"


def test_show_node_scoped_view_selects_only_that_node(workspace):
    _three_level_dag(workspace)

    payload = _payload(show(workspace, "demo", node_id="N2"))
    assert [node["id"] for node in payload["nodes"]] == ["N2"]
    assert payload["nodes"][0]["depth"] == 1


def test_show_include_ancestors_and_descendants(workspace):
    _three_level_dag(workspace)
    add_work(workspace, "demo", "edit", ["N3"], path="x.txt", patch=PATCH)

    ancestors = _payload(show(workspace, "demo", node_id="N2", include_ancestors=True))
    assert [node["id"] for node in ancestors["nodes"]] == ["N1", "N2"]

    descendants = _payload(show(workspace, "demo", node_id="N2", include_descendants=True))
    assert [node["id"] for node in descendants["nodes"]] == ["N2", "N3", "N4"]

    both = _payload(
        show(workspace, "demo", node_id="N3", include_ancestors=True, include_descendants=True)
    )
    assert [node["id"] for node in both["nodes"]] == ["N1", "N2", "N3", "N4"]


def test_show_unknown_node_returns_error(workspace):
    _three_level_dag(workspace)
    assert show(workspace, "demo", node_id="N99")["error"] == "unknown_node"


def test_dag_show_tool_module_delegates_to_ops(workspace):
    _three_level_dag(workspace)
    payload = _payload(dag_show("demo", "N2", True, True, workspace_root=workspace))
    assert [node["id"] for node in payload["nodes"]] == ["N1", "N2", "N3"]


# ---------------------------------------------------------------------------
# archived bundles are immutable
# ---------------------------------------------------------------------------
def _archived_dag(workspace, slug: str) -> dict:
    dag = {
        "slug": slug,
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "requires": ["N2"]},
            "N2": {"type": "edit", "path": "x.txt", "patch": PATCH},
        },
    }
    atomic_write_json(dag_json_path(workspace, slug, True), dag)
    write_state(workspace, slug, {"N2": "satisfied"}, archived=True)
    return dag


def test_mutations_of_archived_dag_are_rejected_and_write_nothing(workspace):
    dag = _archived_dag(workspace, "archived")

    add_work_result = add_work(workspace, "archived", "edit", ["N1"], path="y.txt", patch=PATCH)
    assert add_work_result["error"] == "dag_not_pending"
    assert "immutable" in add_work_result["message"]

    assert add_requirement(workspace, "archived", "new", ["N1"])["error"] == "dag_not_pending"
    assert update_node(workspace, "archived", "N1", requirement="changed")["error"] == "dag_not_pending"
    assert remove_node(workspace, "archived", "N2")["error"] == "dag_not_pending"

    assert read_json(dag_json_path(workspace, "archived", True)) == dag
    assert not dag_json_path(workspace, "archived", False).exists()


# ---------------------------------------------------------------------------
# remove_node refuses to strand immutable work
# ---------------------------------------------------------------------------
def test_remove_node_refuses_to_strand_immutable_work(workspace):
    dag = {
        "slug": "orphan",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "requires": ["N2"]},
            "N2": {"type": "semantic", "requirement": "mid", "requires": ["N3", "N5"]},
            "N3": {"type": "semantic", "requirement": "sub", "requires": ["N4"]},
            "N4": {"type": "edit", "path": "a.txt", "patch": PATCH},
            "N5": {"type": "edit", "path": "b.txt", "patch": PATCH},
        },
    }
    atomic_write_json(dag_json_path(workspace, "orphan"), dag)
    write_state(workspace, "orphan", {"N4": "satisfied"})

    result = remove_node(workspace, "orphan", "N2")
    assert result["error"] == "remove_would_orphan"
    assert "N3" in result["message"]

    persisted = read_json(dag_json_path(workspace, "orphan"))
    assert set(persisted["nodes"]) == {"N1", "N2", "N3", "N4", "N5"}
    assert persisted["nodes"]["N1"]["requires"] == ["N2"]
    assert persisted == dag


# ---------------------------------------------------------------------------
# update_node validation branches
# ---------------------------------------------------------------------------
def test_update_node_rejects_disallowed_run_command(workspace):
    _two_node_dag(workspace)
    add_work(workspace, "demo", "run", ["N2"], command=["pytest"])

    rejected = update_node(workspace, "demo", "N3", command=["git", "commit", "-m", "x"])
    assert rejected["error"] == "run_command_rejected"

    allowed = update_node(workspace, "demo", "N3", command=["pytest", "-q"])
    assert allowed.get("output") is not None
    assert read_json(dag_json_path(workspace, "demo"))["nodes"]["N3"]["command"] == ["pytest", "-q"]


def test_update_node_rejects_field_not_valid_for_kind(workspace):
    _two_node_dag(workspace)
    add_work(workspace, "demo", "edit", ["N2"], path="x.txt", patch=PATCH)
    assert update_node(workspace, "demo", "N3", command=["pytest"])["error"] == "invalid_field"


def test_update_node_run_rejects_non_run_field(workspace):
    _two_node_dag(workspace)
    add_work(workspace, "demo", "run", ["N2"], command=["pytest"])
    assert update_node(workspace, "demo", "N3", path="x.txt")["error"] == "invalid_field"


def test_update_node_requires_at_least_one_field(workspace):
    _two_node_dag(workspace)
    assert update_node(workspace, "demo", "N2")["error"] == "invalid_arguments"


# ---------------------------------------------------------------------------
# set_decomposition_only
# ---------------------------------------------------------------------------
def test_set_decomposition_only_true_then_false_roundtrip(workspace):
    _two_node_dag(workspace)
    # A leaf cannot be declared fully decomposed: it directly requires nothing.
    assert set_decomposition_only(workspace, "demo", "N2", True)["error"] == "invalid_graph"

    child = add_requirement(workspace, "demo", "child", ["N2"])
    assert _payload(child)["node_id"] == "N3"

    declared = set_decomposition_only(workspace, "demo", "N2", True)
    assert _payload(declared)["decomposition_only"] is True
    assert read_json(dag_json_path(workspace, "demo"))["nodes"]["N2"]["decomposition_only"] is True

    reopened = set_decomposition_only(workspace, "demo", "N2", False)
    assert _payload(reopened)["decomposition_only"] is False
    assert read_json(dag_json_path(workspace, "demo"))["nodes"]["N2"]["decomposition_only"] is False


def test_set_decomposition_only_rejects_non_semantic_unknown_and_non_boolean(workspace):
    _two_node_dag(workspace)
    add_work(workspace, "demo", "edit", ["N2"], path="x.txt", patch=PATCH)

    assert set_decomposition_only(workspace, "demo", "N3", True)["error"] == "invalid_node"
    assert set_decomposition_only(workspace, "demo", "N99", True)["error"] == "unknown_node"
    assert set_decomposition_only(workspace, "demo", "N2", "yes")["error"] == "invalid_arguments"


def test_set_decomposition_only_rejects_terminal_child(workspace):
    _two_node_dag(workspace)
    add_work(workspace, "demo", "edit", ["N2"], path="x.txt", patch=PATCH)

    result = set_decomposition_only(workspace, "demo", "N2", True)
    assert result["error"] == "invalid_graph"
    assert any("non-semantic child" in message for message in result["errors"])
    assert "decomposition_only" not in read_json(dag_json_path(workspace, "demo"))["nodes"]["N2"]


def test_set_decomposition_only_rejects_archived_dag(workspace):
    _archived_dag(workspace, "archived")
    result = set_decomposition_only(workspace, "archived", "N1", True)
    assert result["error"] == "dag_not_pending"


def test_dag_set_decomposition_only_tool_module_delegates_to_ops(workspace):
    _two_node_dag(workspace)
    add_requirement(workspace, "demo", "child", ["N2"])
    payload = _payload(dag_set_decomposition_only("demo", "N2", True, workspace_root=workspace))
    assert payload["node_id"] == "N2"
    assert payload["decomposition_only"] is True


# ---------------------------------------------------------------------------
# Root invariant: creation, immutability, and non-root behavior
# ---------------------------------------------------------------------------
def test_create_dag_persists_root_decomposition_only(workspace):
    _two_node_dag(workspace)
    dag = read_json(dag_json_path(workspace, "demo"))
    assert dag["root"] == "N1"
    assert dag["nodes"]["N1"]["type"] == "semantic"
    assert dag["nodes"]["N1"]["decomposition_only"] is True
    # Callers never supply it; the service sets it at creation time. Non-root
    # semantic nodes do not receive it.
    assert "decomposition_only" not in dag["nodes"]["N2"]


def test_create_dag_rejects_semantic_root_without_requires(workspace):
    result = create_dag(
        workspace,
        "leafroot",
        {"root": "r", "nodes": {"r": {"requirement": "root"}}},
    )
    assert result["error"] == "invalid_semantic_graph"
    assert any(
        "root must directly require at least one semantic child" in message
        for message in result["errors"]
    )
    assert not dag_json_path(workspace, "leafroot").exists()


def test_set_decomposition_only_rejects_root_true_and_false(workspace):
    _two_node_dag(workspace)
    for value in (True, False):
        result = set_decomposition_only(workspace, "demo", "N1", value)
        assert result["error"] == "root_immutable"
    dag = read_json(dag_json_path(workspace, "demo"))
    assert dag["nodes"]["N1"]["decomposition_only"] is True


def test_add_requirement_non_root_semantic_has_no_decomposition_flag(workspace):
    _two_node_dag(workspace)
    added = add_requirement(workspace, "demo", "child", ["N2"])
    node_id = _payload(added)["node_id"]
    dag = read_json(dag_json_path(workspace, "demo"))
    assert dag["nodes"][node_id]["type"] == "semantic"
    assert "decomposition_only" not in dag["nodes"][node_id]


# ---------------------------------------------------------------------------
# decomposition_only mutation authority (canonical change_dag.mutability)
# ---------------------------------------------------------------------------
def _dag_json(workspace) -> dict:
    return read_json(dag_json_path(workspace, "demo"))


def _semantic_with_satisfied_terminal(workspace) -> tuple[str, str]:
    """N1(root) -> N2(semantic) -> N3(edit), with N3 satisfied at runtime.

    Returns ``(semantic_id, terminal_id)``.
    """
    _two_node_dag(workspace)
    added = add_work(workspace, "demo", "edit", ["N2"], path="f.txt", patch=PATCH)
    terminal_id = _payload(added)["node_id"]
    write_state(workspace, "demo", {terminal_id: "satisfied"})
    return "N2", terminal_id


def test_set_decomposition_only_allows_unsatisfied_non_root_semantic(workspace):
    _two_node_dag(workspace)
    add_requirement(workspace, "demo", "child", ["N2"])

    assert set_decomposition_only(workspace, "demo", "N2", True).get("error") is None
    assert _dag_json(workspace)["nodes"]["N2"]["decomposition_only"] is True

    # true -> false reopens the judgment and preserves the existing children.
    assert set_decomposition_only(workspace, "demo", "N2", False).get("error") is None
    dag = _dag_json(workspace)
    assert dag["nodes"]["N2"]["decomposition_only"] is False
    assert dag["nodes"]["N2"]["requires"] == ["N3"]


def test_set_decomposition_only_rejects_satisfied_semantic_subtree(workspace):
    semantic_id, _terminal = _semantic_with_satisfied_terminal(workspace)
    before = _dag_json(workspace)

    # Mutability is consulted before the value is even considered, so every call
    # is rejected -- including apparent no-ops. This tool is mutation authority,
    # not an idempotent read/check.
    for value in (True, True, False, False):
        result = set_decomposition_only(workspace, "demo", semantic_id, value)
        assert result["error"] == "immutable_node"
        assert result["message"] == "semantic subtree fully satisfied"
        assert _dag_json(workspace) == before


def test_set_decomposition_only_failed_region_remains_mutable(workspace):
    _two_node_dag(workspace)
    added = add_work(workspace, "demo", "edit", ["N2"], path="f.txt", patch=PATCH)
    terminal_id = _payload(added)["node_id"]
    write_state(workspace, "demo", {terminal_id: "failed"})

    # A failed (unsatisfied) subtree stays mutable under canonical semantics, so
    # the failure is not the setter's mutability error.
    assert set_decomposition_only(workspace, "demo", "N2", False).get("error") is None
    assert _dag_json(workspace)["nodes"]["N2"]["decomposition_only"] is False
