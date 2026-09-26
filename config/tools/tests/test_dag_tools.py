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
from common.helpers.change_dag_ops import (
    add_requirement,
    add_work,
    create_dag,
    preview,
    remove_node,
    show,
    update_node,
    validate,
)
from common.helpers.change_dag_state import write_state
from common.tools.dag_show import dag_show

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
                "root": {"requirement": "done", "satisfied_by": ["impl"]},
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
                "root": {"requirement": "root", "satisfied_by": ["mid"]},
                "mid": {"requirement": "mid", "satisfied_by": ["leaf"]},
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
        {"root": "r", "nodes": {"r": {"requirement": "x", "satisfied_by": ["ghost"]}}},
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
                "root": {"requirement": "done", "satisfied_by": ["impl"]},
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
    assert dag["nodes"]["N1"]["satisfied_by"] == ["N3"]
    assert dag["nodes"]["N3"]["satisfied_by"] == ["N2"]

    leaf = add_requirement(workspace, "demo", "a new open requirement", ["N3"])
    leaf_id = _payload(leaf)["node_id"]
    assert leaf_id == "N4"
    dag = read_json(dag_json_path(workspace, "demo"))
    assert "satisfied_by" not in dag["nodes"][leaf_id]
    assert dag["nodes"]["N3"]["satisfied_by"] == ["N2", leaf_id]


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
                "root": {"requirement": "r", "satisfied_by": ["left", "right"]},
                "left": {"requirement": "l", "satisfied_by": ["shared"]},
                "right": {"requirement": "rt", "satisfied_by": ["shared"]},
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
    assert dag["nodes"]["N1"]["satisfied_by"] == ["N3"]


def test_remove_node_gcs_mutable_unreachable_descendants(workspace):
    create_dag(
        workspace,
        "demo",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "r", "satisfied_by": ["mid"]},
                "mid": {"requirement": "m", "satisfied_by": ["leaf"]},
                "leaf": {"requirement": "l"},
            },
        },
    )
    result = remove_node(workspace, "demo", "N2")
    payload = _payload(result)
    assert payload["removed"] == ["N2", "N3"]
    assert payload["gc"] == ["N3"]
    dag = read_json(dag_json_path(workspace, "demo"))
    assert set(dag["nodes"]) == {"N1"}
    assert "satisfied_by" not in dag["nodes"]["N1"]


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
                "root": {"requirement": "r", "satisfied_by": ["open", "impl"]},
                "open": {"requirement": "still open"},
                "impl": {"requirement": "impl"},
            },
        },
    )
    # BFS: root=N1, open=N2, impl=N3.
    add_work(workspace, "demo", "create", ["N3"], path="new.txt", content="x\n")

    first = _payload(validate(workspace, "demo"))
    assert first["schema_valid"] is True
    assert first["executable"] is True
    assert first["resolved"] is False

    add_work(workspace, "demo", "create", ["N3"], path="new.txt", content="y\n")
    second = _payload(validate(workspace, "demo"))
    assert second["schema_valid"] is True
    assert second["executable"] is False
    assert any(issue["kind"] == "compile_conflict" for issue in second["issues"])


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
    finally:
        remove_marker(workspace)
        release_lock(fd)
    # create is intentionally not gated by running immutability
    created = create_dag(
        workspace,
        "other",
        {"root": "root", "nodes": {"root": {"requirement": "ok"}}},
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
                "root": {"requirement": "r", "satisfied_by": ["a", "b"]},
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
# completed/ archived bundles are immutable
# ---------------------------------------------------------------------------
def _completed_dag(workspace, slug: str) -> dict:
    dag = {
        "slug": slug,
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "satisfied_by": ["N2"]},
            "N2": {"type": "edit", "path": "x.txt", "patch": PATCH},
        },
    }
    atomic_write_json(dag_json_path(workspace, slug, True), dag)
    write_state(workspace, slug, {"N2": "satisfied"}, completed=True)
    return dag


def test_mutations_of_completed_dag_are_rejected_and_write_nothing(workspace):
    dag = _completed_dag(workspace, "archived")

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
            "N1": {"type": "semantic", "requirement": "root", "satisfied_by": ["N2"]},
            "N2": {"type": "semantic", "requirement": "mid", "satisfied_by": ["N3", "N5"]},
            "N3": {"type": "semantic", "requirement": "sub", "satisfied_by": ["N4"]},
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
    assert persisted["nodes"]["N1"]["satisfied_by"] == ["N2"]
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
