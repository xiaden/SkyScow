from __future__ import annotations

import re
from pathlib import Path

from common.helpers.change_dag import (
    allocate_node_id,
    ancestor_map,
    atomic_write_json,
    dag_json_path,
    derived_depth,
    derived_satisfaction,
    direct_children,
    execution_order,
    is_acyclic,
    is_resolved,
    mutability,
    node_map,
    node_type,
    output,
    reachable_from_root,
    resolve_anchor_commit,
    satisfied_terminal_nodes,
    state_json_path,
    structure_errors,
    unresolved_leaves,
    validate_dag,
)

HEX = re.compile(r"^[0-9a-fA-F]{7,64}$")


def dag_with(nodes: dict, root: str = "N1", slug: str = "demo") -> dict:
    return {
        "slug": slug,
        "anchor_commit": "a" * 40,
        "root": root,
        "nodes": nodes,
    }


def semantic(requirement: str = "r", satisfied_by=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if satisfied_by is not None:
        node["satisfied_by"] = satisfied_by
    return node


def edit(path: str = "x.txt") -> dict:
    return {"type": "edit", "path": path, "patch": "@@ -1 +1 @@\n-a\n+b\n"}


def run(command=None) -> dict:
    return {"type": "run", "command": command or ["pytest"]}


def test_valid_semantic_graph_passes_validation():
    dag = dag_with(
        {
            "N1": semantic("validate change", ["N2", "N3"]),
            "N2": semantic("implementation is complete", ["N4"]),
            "N3": run(["pytest", "tests/db/test_query.py"]),
            "N4": edit("src/db/query.py"),
        }
    )
    assert validate_dag(dag) == []


def test_root_must_reference_a_semantic_node(tmp_path: Path):
    dag = dag_with({"N1": edit()}, root="N1")
    assert any("must be type semantic" in error for error in structure_errors(dag))

    dag = dag_with({"N1": semantic("root")}, root="N99")
    assert any("existing node" in error for error in structure_errors(dag))


def test_missing_reference_is_rejected():
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": edit()})
    dag["nodes"]["N1"]["satisfied_by"] = ["N2", "N99"]
    errors = structure_errors(dag)
    assert any("missing node: N99" in error for error in errors)


def test_unreachable_node_is_rejected():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": edit(),
            "N3": edit("orphan.txt"),
        }
    )
    errors = structure_errors(dag)
    assert any("N3 is not reachable" in error for error in errors)


def test_cycle_is_detected_and_reported():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("two", ["N3"]),
            "N3": semantic("three", ["N1"]),
        }
    )
    assert is_acyclic(dag) is False
    errors = structure_errors(dag)
    assert any("cycle" in error for error in errors)
    # a concrete cycle is named
    assert any("N1" in error and "N2" in error and "N3" in error for error in errors if "cycle" in error)


def test_run_barrier_rejects_edit_and_run_siblings():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N3"]),
            "N2": edit(),
            "N3": run(),
        }
    )
    errors = structure_errors(dag)
    assert any("non-semantic child beside a run child" in error for error in errors)


def test_run_barrier_rejects_two_run_siblings():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N3"]),
            "N2": run(["pytest"]),
            "N3": run(["mypy"]),
        }
    )
    errors = structure_errors(dag)
    assert any("multiple direct run children" in error for error in errors)


def test_run_barrier_allows_semantic_siblings_of_run():
    dag = dag_with(
        {
            "N1": semantic("validate", ["N2", "N5"]),
            "N2": semantic("implement", ["N3", "N4"]),
            "N3": edit("a.py"),
            "N4": edit("b.py"),
            "N5": run(["pytest"]),
        }
    )
    assert validate_dag(dag) == []


def test_longest_path_depth_with_convergence():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N3"]),
            "N2": semantic("left", ["N4"]),
            "N3": semantic("right", ["N4"]),
            "N4": edit("shared.py"),
        }
    )
    depths = derived_depth(dag)
    assert depths["N1"] == 0
    assert depths["N2"] == 1
    assert depths["N3"] == 1
    assert depths["N4"] == 2


def test_execution_order_is_deepest_first_then_id_ascending():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N3"]),
            "N2": semantic("left", ["N4"]),
            "N3": semantic("right", ["N5"]),
            "N4": edit("a.py"),
            "N5": edit("b.py"),
        }
    )
    assert execution_order(dag) == ["N4", "N5", "N2", "N3", "N1"]


def test_shared_descendant_retains_one_identity():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N3"]),
            "N2": semantic("left", ["N4"]),
            "N3": semantic("right", ["N4"]),
            "N4": edit("shared.py"),
        }
    )
    assert validate_dag(dag) == []
    assert list(node_map(dag)).count("N4") == 1
    assert direct_children(dag, "N2") == ["N4"]
    assert direct_children(dag, "N3") == ["N4"]
    assert execution_order(dag).count("N4") == 1
    assert ancestor_map(dag)["N4"] == {"N1", "N2", "N3"}
    assert reachable_from_root(dag) == {"N1", "N2", "N3", "N4"}


def test_unresolved_leaf_is_legal_but_unresolved():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N3"]),
            "N2": semantic("permission is obtained"),  # unresolved leaf
            "N3": edit("done.py"),
        }
    )
    assert validate_dag(dag) == []
    assert structure_errors(dag) == []
    assert is_resolved(dag) is False
    assert unresolved_leaves(dag) == ["N2"]


def test_resolved_graph_when_every_semantic_has_children():
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": edit()})
    assert is_resolved(dag) is True
    assert unresolved_leaves(dag) == []


def test_node_id_pattern_and_monotonic_no_reuse(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": edit()})

    first = allocate_node_id(dag, workspace, "demo")
    assert first == "N3"
    second = allocate_node_id(dag, workspace, "demo")
    assert second == "N4"
    # Simulate the newly allocated nodes being removed from the DAG: the persisted
    # high-water mark must keep allocation monotonic and never reuse an ID.
    third = allocate_node_id(dag, workspace, "demo")
    assert int(third[1:]) > int(second[1:])
    assert third == "N5"

    # A raised persisted high-water mark raises the floor.
    seq = workspace / "artifacts/change-dags/pending/demo/.node_seq"
    seq.write_text("10\n", encoding="utf-8")
    fourth = allocate_node_id(dag, workspace, "demo")
    assert fourth == "N11"


def test_invalid_dag_creation_writes_nothing(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    def create_if_valid(slug: str, candidate: dict) -> bool:
        if validate_dag(candidate):
            return False
        atomic_write_json(dag_json_path(workspace, slug), candidate)
        return True

    bad = dag_with({"N1": edit()}, root="N999")
    assert create_if_valid("bad-dag", bad) is False
    assert not dag_json_path(workspace, "bad-dag").exists()
    assert not dag_json_path(workspace, "bad-dag").parent.exists()
    assert not state_json_path(workspace, "bad-dag").exists()


def test_anchor_commit_resolution_is_hex(tmp_path: Path):
    sha = resolve_anchor_commit(tmp_path)
    assert isinstance(sha, str)
    assert HEX.match(sha)


def test_derived_satisfaction_and_mutability():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N3", "N4"]),
            "N3": edit("a.py"),
            "N4": edit("b.py"),
        }
    )
    state = {"N3": "satisfied", "N4": "failed"}
    satisfaction = derived_satisfaction(dag, state)
    assert satisfaction["N3"] is True
    assert satisfaction["N4"] is False
    assert satisfaction["N2"] is False
    assert satisfaction["N1"] is False
    assert satisfied_terminal_nodes(dag, state) == ["N3"]

    assert mutability(dag, state, "N3") == (False, "satisfied terminal work is immutable")
    assert mutability(dag, state, "N4") == (True, "mutable")
    assert mutability(dag, state, "N2")[0] is True
    assert mutability(dag, state, "N1") == (False, "root is immutable")

    all_satisfied = {"N3": "satisfied", "N4": "satisfied"}
    assert mutability(dag, all_satisfied, "N2") == (False, "semantic subtree fully satisfied")
    assert mutability(dag, all_satisfied, "N3") == (False, "satisfied terminal work is immutable")
    assert derived_satisfaction(dag, all_satisfied)["N1"] is True


def test_root_is_never_removable_and_unknown_node_is_not_mutable():
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": edit()})
    assert mutability(dag, {}, "N1") == (False, "root is immutable")
    mutable, reason = mutability(dag, {}, "N99")
    assert mutable is False
    assert "unknown node" in reason


def test_node_helpers_and_output_shape():
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": edit()})
    assert node_type(dag, "N1") == "semantic"
    assert node_type(dag, "N2") == "edit"
    assert direct_children(dag, "N2") == []
    result = output({"ok": True}, "Done")
    assert result["title"] == "Done"
    assert result["metadata"] == {}
    assert '"ok"' in result["output"]
