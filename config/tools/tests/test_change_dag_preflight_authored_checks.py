"""F9-A: preflight reports authored defects even behind blocked runs."""
from __future__ import annotations

from pathlib import Path

from common.helpers.change_dag_compiler_phase import preflight


def semantic(requirement: str, children: list[str]) -> dict:
    return {"type": "semantic", "requirement": requirement, "satisfied_by": children}


def run(command=None) -> dict:
    return {"type": "run", "command": command or ["python3", "-m", "compileall", "-q", "."]}


def edit(path: str, patch: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch}


def patch(path: str, old: str = "a", new: str = "b") -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,1 @@\n-{old}\n+{new}\n"


def dag(nodes: dict) -> dict:
    return {"slug": "preflight", "anchor_commit": "a" * 40, "root": "N1", "nodes": nodes}


def blocked_barrier_graph(higher: dict, lower: dict | None = None) -> dict:
    return dag({
        "N1": semantic("root", ["N2"]),
        "N2": semantic("aggregate", ["N3", "N7"]),
        "N3": semantic("barrier branch", ["N4"]),
        "N4": semantic("inner", ["N5", "N6"]),
        "N5": run(),
        "N6": semantic("lower", ["N8"]),
        "N8": lower or edit("f.txt", patch("f.txt", "x", "b")),
        "N7": higher,
    })


def test_malformed_higher_edit_is_not_hidden_by_blocked_run(tmp_path: Path):
    (tmp_path / "f.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "g.txt").write_text("a\n", encoding="utf-8")

    result = preflight(blocked_barrier_graph(edit("g.txt", "NOT A PATCH")), {}, tmp_path)

    assert result["executable"] is False
    assert any(issue["kind"] == "compile_conflict" and issue["nodes"] == ["N7"] for issue in result["issues"])
    assert any(entry["kind"] == "runtime_failure" and entry["nodes"] == ["N8"] for entry in result["runtime_failures"])


def test_patch_target_mismatch_and_multifile_are_authored_conflicts(tmp_path: Path):
    (tmp_path / "f.txt").write_text("a\n", encoding="utf-8")
    mismatch = patch("other.txt")
    multifile = patch("f.txt") + patch("other.txt")

    for invalid in (mismatch, multifile):
        result = preflight(blocked_barrier_graph(edit("g.txt", invalid)), {}, tmp_path)
        assert result["executable"] is False
        assert any(issue["kind"] == "compile_conflict" for issue in result["issues"])


def test_malformed_move_create_remove_and_run_policy_are_authored_conflicts(tmp_path: Path):
    cases = (
        {"type": "move", "from_path": "", "to_path": "x", "overwrite": False},
        {"type": "create", "path": "x", "content": 7},
        {"type": "remove", "path": ""},
        run(["git", "commit", "-m", "bad"]),
    )
    for invalid in cases:
        result = preflight(blocked_barrier_graph(invalid), {}, tmp_path)
        assert result["executable"] is False
        assert any(issue["kind"] == "compile_conflict" for issue in result["issues"])


def test_live_drift_stays_runtime_admission(tmp_path: Path):
    (tmp_path / "f.txt").write_text("drifted\n", encoding="utf-8")
    graph = dag({
        "N1": semantic("root", ["N2"]),
        "N2": semantic("edit", ["N3"]),
        "N3": edit("f.txt", patch("f.txt", "a", "b")),
    })

    result = preflight(graph, {}, tmp_path)
    assert result["executable"] is True
    assert result["issues"] == []
    assert any(entry["kind"] == "runtime_failure" for entry in result["runtime_failures"])
