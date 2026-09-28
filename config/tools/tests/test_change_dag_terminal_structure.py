"""Direct-terminal structural invariant for the Change DAG authoring model.

Over a semantic node's *direct* children:

* semantic children are always allowed, in any number;
* ``edit`` children are composable: any number may coexist with each other and
  with semantic children;
* ``create``, ``remove``, ``move`` and ``run`` are exclusive: when a semantic
  node owns any exclusive terminal child, that child must be its only terminal
  child.

This is authoring structure only; it does not give ``create``/``remove``/
``move`` any runtime run-barrier semantics.
"""
from __future__ import annotations

from common.helpers.change_dag import (
    EXCLUSIVE_TERMINAL_TYPES,
    TERMINAL_TYPES,
    direct_terminal_errors,
    structure_errors,
    validate_dag,
)


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


def root_semantic(requirement: str = "root", requires=None) -> dict:
    node = semantic(requirement, requires)
    node["decomposition_only"] = True
    return node


def create(path: str = "new.txt", content: str = "x\n") -> dict:
    return {"type": "create", "path": path, "content": content}


def edit(path: str = "x.txt") -> dict:
    return {"type": "edit", "path": path, "patch": "@@ -1 +1 @@\n-a\n+b\n"}


def remove(path: str = "x.txt") -> dict:
    return {"type": "remove", "path": path}


def move(from_path: str = "x.txt", to_path: str = "y.txt") -> dict:
    return {"type": "move", "from_path": from_path, "to_path": to_path}


def run(command=None) -> dict:
    return {"type": "run", "command": command or ["pytest"]}


def sibling_dag(parent_children: dict[str, dict]) -> dict:
    """Root -> N2 with the supplied direct children keyed by node id.

    N1 is the root; N2 is the semantic node under test. Every supplied child is a
    direct requirement of N2, so the fixture isolates the direct-terminal rule.
    """
    child_ids = list(parent_children)
    nodes = {
        "N1": root_semantic("validate", ["N2"]),
        "N2": semantic("implementation", child_ids),
    }
    nodes.update(parent_children)
    return dag_with(nodes)


# ---------------------------------------------------------------------------
# Valid shapes
# ---------------------------------------------------------------------------
def test_edit_plus_edit_is_valid():
    dag = sibling_dag({"N3": edit("a.txt"), "N4": edit("b.txt")})
    assert validate_dag(dag) == []


def test_create_alone_is_valid():
    dag = sibling_dag({"N3": create("new.txt", "x\n")})
    assert validate_dag(dag) == []


def test_create_beside_semantic_is_valid():
    dag = dag_with(
        {
            "N1": root_semantic("validate", ["N2"]),
            "N2": semantic("implementation", ["N3", "N4"]),
            "N3": semantic("deeper", ["N5"]),
            "N4": create("new.txt", "x\n"),
            "N5": edit("a.txt"),
        }
    )
    assert validate_dag(dag) == []


def test_run_beside_semantic_is_valid():
    dag = dag_with(
        {
            "N1": root_semantic("validate", ["N2"]),
            "N2": semantic("verification", ["N3", "N4"]),
            "N3": semantic("deeper", ["N5"]),
            "N4": run(["pytest"]),
            "N5": edit("a.txt"),
        }
    )
    assert validate_dag(dag) == []


def test_edit_beside_semantic_is_valid():
    dag = dag_with(
        {
            "N1": root_semantic("validate", ["N2"]),
            "N2": semantic("implementation", ["N3", "N4"]),
            "N3": semantic("deeper", ["N5"]),
            "N4": edit("b.txt"),
            "N5": edit("a.txt"),
        }
    )
    assert validate_dag(dag) == []


def test_multiple_edits_and_semantic_compose_together():
    dag = dag_with(
        {
            "N1": root_semantic("validate", ["N2"]),
            "N2": semantic("implementation", ["N3", "N4", "N5"]),
            "N3": semantic("deeper", ["N6"]),
            "N4": edit("b.txt"),
            "N5": edit("c.txt"),
            "N6": edit("a.txt"),
        }
    )
    assert validate_dag(dag) == []


# ---------------------------------------------------------------------------
# Invalid shapes: exclusive terminal beside a sibling terminal
# ---------------------------------------------------------------------------
def test_create_beside_edit_is_rejected():
    dag = sibling_dag({"N3": create("new.txt", "x\n"), "N4": edit("a.txt")})
    errors = structure_errors(dag)
    assert any("exclusive terminal child" in error and "create" in error for error in errors)


def test_move_beside_edit_is_rejected():
    dag = sibling_dag({"N3": move("a.txt", "b.txt"), "N4": edit("a.txt")})
    errors = structure_errors(dag)
    assert any("exclusive terminal child" in error and "move" in error for error in errors)


def test_remove_beside_edit_is_rejected():
    dag = sibling_dag({"N3": remove("a.txt"), "N4": edit("a.txt")})
    errors = structure_errors(dag)
    assert any("exclusive terminal child" in error and "remove" in error for error in errors)


def test_run_beside_edit_is_rejected_with_legacy_message():
    dag = sibling_dag({"N3": run(["pytest"]), "N4": edit("a.txt")})
    errors = structure_errors(dag)
    assert any("non-semantic child beside a run child" in error for error in errors)


def test_two_creates_are_rejected():
    dag = sibling_dag({"N3": create("new.txt", "x\n"), "N4": create("new.txt", "y\n")})
    errors = structure_errors(dag)
    assert any("exclusive terminal child" in error and "create" in error for error in errors)


def test_move_beside_remove_is_rejected():
    dag = sibling_dag({"N3": move("a.txt", "b.txt"), "N4": remove("c.txt")})
    errors = structure_errors(dag)
    assert any("exclusive terminal child" in error for error in errors)


def test_two_runs_are_rejected_with_legacy_message():
    dag = sibling_dag({"N3": run(["pytest"]), "N4": run(["mypy"])})
    errors = structure_errors(dag)
    assert any("multiple direct run children" in error for error in errors)


def test_run_beside_create_is_rejected():
    dag = sibling_dag({"N3": run(["pytest"]), "N4": create("new.txt", "x\n")})
    errors = structure_errors(dag)
    assert any("non-semantic child beside a run child" in error for error in errors)
    assert any("exclusive terminal child" in error and "create" in error for error in errors)


def test_exclusive_beside_any_sibling_terminal_is_rejected():
    exclusive_terminals = {
        "create": lambda: create("new.txt", "x\n"),
        "move": lambda: move("a.txt", "b.txt"),
        "remove": lambda: remove("a.txt"),
        "run": lambda: run(["pytest"]),
    }
    for exclusive_type, make_exclusive in exclusive_terminals.items():
        for sibling_type, make_sibling in exclusive_terminals.items():
            if sibling_type == exclusive_type:
                continue
            dag = sibling_dag({"N3": make_exclusive(), "N4": make_sibling()})
            assert structure_errors(dag), f"{exclusive_type} + {sibling_type} must be rejected"


# ---------------------------------------------------------------------------
# Validator/constant shape
# ---------------------------------------------------------------------------
def test_direct_terminal_errors_is_the_generalized_validator():
    dag = sibling_dag({"N3": create("new.txt", "x\n"), "N4": edit("a.txt")})
    errors = direct_terminal_errors(dag)
    assert any("exclusive terminal child" in error for error in errors)


def test_edit_is_terminal_but_not_exclusive():
    assert "edit" in TERMINAL_TYPES
    assert "edit" not in EXCLUSIVE_TERMINAL_TYPES
    assert set(EXCLUSIVE_TERMINAL_TYPES) == {"create", "remove", "move", "run"}
