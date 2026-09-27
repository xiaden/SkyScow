from __future__ import annotations

import re
from pathlib import Path

from common.helpers.change_dag import (
    allocate_node_id,
    ancestor_map,
    atomic_write_json,
    dag_json_path,
    decomposition_only_errors,
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
    semantic_node_resolved,
    state_json_path,
    structure_errors,
    unresolved_semantic_nodes,
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


def semantic(requirement: str = "r", requires=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if requires is not None:
        node["requires"] = requires
    return node


def root_semantic(requirement: str = "r", requires=None) -> dict:
    """The root is immutable and always decomposition_only."""
    node = semantic(requirement, requires)
    node["decomposition_only"] = True
    return node


def edit(path: str = "x.txt") -> dict:
    return {"type": "edit", "path": path, "patch": "@@ -1 +1 @@\n-a\n+b\n"}


def run(command=None) -> dict:
    return {"type": "run", "command": command or ["pytest"]}


TERMINAL_NODES = {
    "create": {"type": "create", "path": "x.txt", "content": "x\n"},
    "edit": {"type": "edit", "path": "x.txt", "patch": "@@ -1 +1 @@\n-a\n+b\n"},
    "remove": {"type": "remove", "path": "x.txt"},
    "move": {"type": "move", "from_path": "x.txt", "to_path": "y.txt"},
    "run": {"type": "run", "command": ["pytest"]},
}


def test_valid_semantic_graph_passes_validation():
    dag = dag_with(
        {
            "N1": root_semantic("validate change", ["N2", "N5"]),
            "N2": semantic("implementation is complete", ["N4"]),
            "N5": semantic("verification is complete", ["N3"]),
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
    dag["nodes"]["N1"]["requires"] = ["N2", "N99"]
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
            "N1": root_semantic("validate", ["N6"]),
            "N6": semantic("verification", ["N2", "N5"]),
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
            "N1": root_semantic("root", ["N2", "N3"]),
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


def test_unresolved_semantic_node_is_legal_but_unresolved():
    dag = dag_with(
        {
            "N1": root_semantic("root", ["N2", "N4"]),
            "N2": semantic("permission is obtained"),  # unresolved semantic node
            "N4": semantic("change applied", ["N3"]),
            "N3": edit("done.py"),
        }
    )
    assert validate_dag(dag) == []
    assert structure_errors(dag) == []
    assert is_resolved(dag) is False
    assert unresolved_semantic_nodes(dag) == ["N2"]
    # The root is decomposition_only, so it is locally resolved.
    assert semantic_node_resolved(dag, "N1") is True
    assert semantic_node_resolved(dag, "N2") is False


def test_resolved_graph_when_every_semantic_node_is_locally_resolved():
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": edit()})
    assert is_resolved(dag) is True
    assert unresolved_semantic_nodes(dag) == []


def test_empty_semantic_node_is_unresolved():
    dag = dag_with({"N1": semantic("root")})
    assert semantic_node_resolved(dag, "N1") is False
    assert is_resolved(dag) is False
    assert unresolved_semantic_nodes(dag) == ["N1"]


def test_semantic_children_without_decomposition_flag_are_unresolved():
    dag = dag_with(
        {
            "N1": root_semantic("root", ["N2"]),
            "N2": semantic("deferred"),
        }
    )
    assert validate_dag(dag) == []
    # The root is always decomposition_only, so it is locally resolved; the
    # semantic child without its own decomposition flag stays unresolved.
    assert semantic_node_resolved(dag, "N1") is True
    assert semantic_node_resolved(dag, "N2") is False
    assert is_resolved(dag) is False
    assert unresolved_semantic_nodes(dag) == ["N2"]


def test_semantic_children_with_decomposition_flag_resolve():
    dag = dag_with(
        {
            "N1": {
                "type": "semantic",
                "requirement": "root",
                "requires": ["N2", "N3"],
                "decomposition_only": True,
            },
            "N2": semantic("child a"),
            "N3": semantic("child b"),
        }
    )
    assert validate_dag(dag) == []
    assert semantic_node_resolved(dag, "N1") is True
    # Local resolution is not inherited: the semantic children stay unresolved.
    assert is_resolved(dag) is False
    assert unresolved_semantic_nodes(dag) == ["N2", "N3"]


def test_direct_ordinary_terminal_work_resolves():
    for kind, node in TERMINAL_NODES.items():
        dag = dag_with({"N1": semantic("root", ["N2"]), "N2": dict(node)})
        assert semantic_node_resolved(dag, "N1") is True, kind
        assert is_resolved(dag) is True, kind


def test_run_with_semantic_siblings_resolves_subject_to_run_invariant():
    dag = dag_with(
        {
            "N1": root_semantic("root", ["N4"]),
            "N4": semantic("verification", ["N2", "N3"]),
            "N2": semantic("reviewed"),
            "N3": run(["pytest"]),
        }
    )
    assert validate_dag(dag) == []  # run barrier allows semantic siblings of a run
    # N4 directly requires the run, so it is locally resolved.
    assert semantic_node_resolved(dag, "N4") is True
    # N2 remains an unresolved semantic node.
    assert is_resolved(dag) is False
    assert unresolved_semantic_nodes(dag) == ["N2"]


def test_decomposition_only_with_terminal_child_is_invalid_not_resolved():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": {
                "type": "semantic",
                "requirement": "claimed decomposed",
                "requires": ["N3"],
                "decomposition_only": True,
            },
            "N3": edit(),
        }
    )
    assert decomposition_only_errors(dag)
    assert semantic_node_resolved(dag, "N2") is False


def test_global_resolution_requires_every_reachable_semantic_node_resolved():
    unresolved = dag_with(
        {
            "N1": semantic("root", ["N2", "N4"]),
            "N2": semantic("branch", ["N3"]),
            "N3": edit("a.py"),
            "N4": semantic("still open"),
        }
    )
    assert is_resolved(unresolved) is False
    assert unresolved_semantic_nodes(unresolved) == ["N1", "N4"]

    resolved = dag_with(
        {
            "N1": {
                "type": "semantic",
                "requirement": "root",
                "requires": ["N2", "N4"],
                "decomposition_only": True,
            },
            "N2": semantic("branch", ["N3"]),
            "N3": edit("a.py"),
            "N4": semantic("converged", ["N3"]),
        }
    )
    assert validate_dag(resolved) == []
    assert is_resolved(resolved) is True
    assert unresolved_semantic_nodes(resolved) == []


def test_shared_descendant_resolution_uses_one_identity():
    dag = dag_with(
        {
            "N1": {
                "type": "semantic",
                "requirement": "root",
                "requires": ["N2", "N3"],
                "decomposition_only": True,
            },
            "N2": semantic("left", ["N4"]),
            "N3": semantic("right", ["N4"]),
            "N4": edit("shared.py"),
        }
    )
    assert validate_dag(dag) == []
    assert is_resolved(dag) is True
    assert unresolved_semantic_nodes(dag) == []


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


# ---------------------------------------------------------------------------
# decomposition_only: persisted semantic authoring intent
# ---------------------------------------------------------------------------
def test_decomposition_only_true_with_semantic_children_is_valid():
    dag = dag_with(
        {
            "N1": root_semantic("root", ["N2"]),
            "N2": {
                "type": "semantic",
                "requirement": "fully decomposed",
                "requires": ["N3", "N4"],
                "decomposition_only": True,
            },
            "N3": semantic("child a"),
            "N4": semantic("child b"),
        }
    )
    assert validate_dag(dag) == []
    assert structure_errors(dag) == []
    assert decomposition_only_errors(dag) == []


def test_decomposition_only_is_rejected_on_terminal_nodes():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": {"type": "edit", "path": "x.txt", "patch": "@@ -1 +1 @@\n-a\n+b\n", "decomposition_only": True},
        }
    )
    errors = validate_dag(dag)
    assert errors
    assert any("decomposition_only" in error for error in errors)


def test_decomposition_only_true_requires_at_least_one_child():
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": {"type": "semantic", "requirement": "claimed decomposed", "decomposition_only": True},
        }
    )
    errors = structure_errors(dag)
    assert any("must directly require at least one semantic child" in error for error in errors)


def test_decomposition_only_true_rejects_each_terminal_child():
    for kind, node in TERMINAL_NODES.items():
        dag = dag_with(
            {
                "N1": semantic("root", ["N2"]),
                "N2": {
                    "type": "semantic",
                    "requirement": "claimed decomposed",
                    "requires": ["N3"],
                    "decomposition_only": True,
                },
                "N3": dict(node),
            }
        )
        errors = decomposition_only_errors(dag)
        assert any("has a non-semantic child: N3" in error for error in errors), (kind, errors)
        assert any(error for error in validate_dag(dag)), (kind, errors)


def test_decomposition_only_false_preserves_terminal_children():
    dag = dag_with(
        {
            "N1": root_semantic("root", ["N2"]),
            "N2": {
                "type": "semantic",
                "requirement": "not decomposition-only",
                "requires": ["N3"],
                "decomposition_only": False,
            },
            "N3": edit(),
        }
    )
    assert validate_dag(dag) == []
    assert decomposition_only_errors(dag) == []


# ---------------------------------------------------------------------------
# Root invariant: the root is immutable and always decomposition_only
# ---------------------------------------------------------------------------
def test_root_with_only_semantic_children_is_valid():
    dag = dag_with({"N1": root_semantic("root", ["N2"]), "N2": semantic("child")})
    assert validate_dag(dag) == []


def test_root_semantic_leaf_without_requires_is_rejected():
    dag = dag_with({"N1": semantic("root")})
    errors = structure_errors(dag)
    assert any(
        "must directly require at least one semantic child" in error for error in errors
    )


def test_root_directly_requiring_each_terminal_kind_is_rejected():
    for kind, node in TERMINAL_NODES.items():
        dag = dag_with({"N1": root_semantic("root", ["N2"]), "N2": dict(node)})
        errors = structure_errors(dag)
        assert any(
            "must not directly require terminal work" in error and "N2" in error
            for error in errors
        ), (kind, errors)
        assert validate_dag(dag), (kind, errors)


def test_root_missing_decomposition_only_fails_structure_validation():
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": semantic("child")})
    errors = structure_errors(dag)
    assert any("must have decomposition_only=true" in error for error in errors)
