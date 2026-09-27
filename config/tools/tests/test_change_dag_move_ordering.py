"""F3: dependent moves execute deeper construction work first."""
from __future__ import annotations

from pathlib import Path

from common.helpers.change_dag_compiler import apply_compiled, compile_operations


def semantic(requirement: str, children: list[str]) -> dict:
    return {"type": "semantic", "requirement": requirement, "satisfied_by": children}


def move(source: str, destination: str, overwrite: bool = False) -> dict:
    return {"type": "move", "from_path": source, "to_path": destination, "overwrite": overwrite}


def dag(nodes: dict) -> dict:
    return {"slug": "moves", "anchor_commit": "a" * 40, "root": "N1", "nodes": nodes}


def test_deeper_move_frees_destination_before_shallower_move_consumes_it(tmp_path: Path):
    (tmp_path / "a").write_text("A\n", encoding="utf-8")
    (tmp_path / "b").write_text("B\n", encoding="utf-8")
    graph = dag({
        "N1": semantic("root", ["N2"]),
        "N2": semantic("aggregate", ["N3", "N11"]),
        "N3": semantic("deep", ["N10"]),
        "N10": move("b", "c"),
        "N11": move("a", "b", overwrite=True),
    })

    ops, conflicts, blocked = compile_operations(graph, {}, tmp_path)
    assert not conflicts and not blocked
    assert [op.nodes for op in ops] == [["N10"], ["N11"]]
    assert [result["ok"] for result in apply_compiled(ops, tmp_path)] == [True, True]
    assert not (tmp_path / "a").exists()
    assert (tmp_path / "b").read_text(encoding="utf-8") == "A\n"
    assert (tmp_path / "c").read_text(encoding="utf-8") == "B\n"


def test_independent_moves_keep_deterministic_order_and_content(tmp_path: Path):
    for name, content in (("a", "A\n"), ("b", "B\n")):
        (tmp_path / name).write_text(content, encoding="utf-8")
    graph = dag({
        "N1": semantic("root", ["N2"]),
        "N2": semantic("aggregate", ["N10", "N11"]),
        "N10": move("a", "x"),
        "N11": move("b", "y"),
    })

    ops, conflicts, blocked = compile_operations(graph, {}, tmp_path)
    assert not conflicts and not blocked
    assert [op.nodes for op in ops] == [["N10"], ["N11"]]
    assert all(result["ok"] for result in apply_compiled(ops, tmp_path))
    assert (tmp_path / "x").read_text(encoding="utf-8") == "A\n"
    assert (tmp_path / "y").read_text(encoding="utf-8") == "B\n"


def test_non_overwrite_destination_collision_remains_runtime_failure(tmp_path: Path):
    (tmp_path / "a").write_text("A\n", encoding="utf-8")
    (tmp_path / "x").write_text("existing\n", encoding="utf-8")
    graph = dag({
        "N1": semantic("root", ["N2"]),
        "N2": semantic("move", ["N10"]),
        "N10": move("a", "x"),
    })

    ops, conflicts, _blocked = compile_operations(graph, {}, tmp_path)
    assert ops == []
    assert conflicts[0].scope == "runtime"
    assert (tmp_path / "a").read_text(encoding="utf-8") == "A\n"
