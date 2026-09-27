"""Regression tests for deterministic same-file edit collision classification."""
from __future__ import annotations

import json
from pathlib import Path

from common.helpers.change_dag_compiler import compile_operations, preflight
from common.helpers.change_dag_ops import add_work, create_dag, preview


def dag_with(nodes: dict) -> dict:
    return {"slug": "collision", "anchor_commit": "a" * 40, "root": "N1", "nodes": nodes}


def semantic(requirement: str, children: list[str] | None = None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if children is not None:
        node["satisfied_by"] = children
    return node


def edit(path: str, patch: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch}


def patch(path: str, old: str, new: str, *, line: int = 1) -> str:
    return (
        f"--- a/{path}\n+++ b/{path}\n"
        f"@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"
    )


def collision_dag(first: str, second: str) -> dict:
    return dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N10", "N11"]),
            "N10": edit("f.txt", first),
            "N11": edit("f.txt", second),
        }
    )


def test_deterministic_same_file_collision_is_intra_dag_and_read_only(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "f.txt"
    target.write_text("foo\n", encoding="utf-8")
    dag = collision_dag(patch("f.txt", "foo", "bar"), patch("f.txt", "foo", "baz"))

    result = preflight(dag, {}, workspace)

    assert result["executable"] is False
    assert result["runtime_failures"] == []
    issue = next(issue for issue in result["issues"] if issue["kind"] == "context_conflict")
    assert set(issue["nodes"]) == {"N10", "N11"}
    assert "N11" in issue["message"]
    assert target.read_text(encoding="utf-8") == "foo\n"

    ops, conflicts, blocked = compile_operations(dag, {}, workspace)
    assert ops == []
    assert blocked == []
    assert len(conflicts) == 1
    assert conflicts[0].scope == "intra_dag"
    assert set(conflicts[0].nodes) == {"N10", "N11"}


def test_compatible_same_file_edits_compose_without_false_conflict(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\nb\n", encoding="utf-8")
    dag = collision_dag(patch("f.txt", "a", "A"), patch("f.txt", "b", "B", line=2))

    result = preflight(dag, {}, workspace)
    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert result["executable"] is True
    assert result["issues"] == []
    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].applied == "A\nB\n"


def test_same_frontier_peer_dependency_is_a_deterministic_conflict(tmp_path: Path):
    # N11's patch only applies after N10's peer edit. Same-frontier peers are
    # interpreted against the common base, so numeric node order must not turn
    # that into accepted causality.
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\n", encoding="utf-8")
    dag = collision_dag(patch("f.txt", "a", "A"), patch("f.txt", "A", "AA"))

    result = preflight(dag, {}, workspace)
    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert result["executable"] is False
    assert result["runtime_failures"] == []
    assert ops == []
    assert len(conflicts) == 1
    assert conflicts[0].scope == "intra_dag"
    assert set(conflicts[0].nodes) == {"N10", "N11"}
    assert conflicts[0].reason.startswith("context_conflict:")


def test_genuine_live_drift_remains_runtime_applicability_evidence(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "f.txt"
    target.write_text("baz\n", encoding="utf-8")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N10"]),
            "N10": edit("f.txt", patch("f.txt", "foo", "bar")),
        }
    )

    result = preflight(dag, {}, workspace)
    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)

    assert result["executable"] is True
    assert result["issues"] == []
    assert any(entry["kind"] == "runtime_failure" for entry in result["runtime_failures"])
    assert conflicts and conflicts[0].scope == "runtime"
    assert ops == []
    assert target.read_text(encoding="utf-8") == "baz\n"


def test_three_node_collision_attributes_the_overlapping_peers(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "f.txt").write_text("a\nb\n", encoding="utf-8")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N10", "N11", "N12"]),
            "N10": edit("f.txt", patch("f.txt", "a", "A")),
            "N11": edit("f.txt", patch("f.txt", "b", "B", line=2)),
            "N12": edit("f.txt", patch("f.txt", "b", "C", line=2)),
        }
    )

    result = preflight(dag, {}, workspace)
    assert result["executable"] is False
    conflict = next(conflict for conflict in result["conflicts"] if conflict["scope"] == "intra_dag")
    # N10 changes an independent region; only the two peers that rewrite the same
    # base line conflict with each other.
    assert set(conflict["nodes"]) == {"N11", "N12"}
    assert "N12" in conflict["reason"]


def test_preview_uses_same_intra_dag_classification_as_preflight(workspace):
    assert create_dag(
        workspace,
        "collision",
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "satisfied_by": ["implementation"]},
                "implementation": {"requirement": "implementation"},
            },
        },
    )["output"]
    first = patch("f.txt", "foo", "bar")
    second = patch("f.txt", "foo", "baz")
    (workspace / "f.txt").write_text("foo\n", encoding="utf-8")
    add_work(workspace, "collision", "edit", ["N2"], path="f.txt", patch=first)
    add_work(workspace, "collision", "edit", ["N2"], path="f.txt", patch=second)

    payload = json.loads(preview(workspace, "collision")["output"])

    assert payload["executable"] is False
    conflict = next(item for item in payload["conflicts"] if item["scope"] == "intra_dag")
    assert conflict["reason"].startswith("context_conflict:")
    assert set(conflict["nodes"]) == {"N3", "N4"}
    assert any(issue["kind"] == "context_conflict" for issue in payload["issues"])
    assert payload["runtime_failures"] == []
