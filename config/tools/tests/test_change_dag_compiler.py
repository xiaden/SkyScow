"""Focused tests for the Change DAG compiler and run-command policy."""
from __future__ import annotations

from pathlib import Path

from common.helpers.change_dag import unresolved_leaves
from common.helpers.change_dag_compiler import (
    Blocked,
    CompiledOp,
    Conflict,
    apply_compiled,
    compile_operations,
    node_present,
    preflight,
    ready_run_nodes,
    summarize,
)
from common.helpers.change_dag_policy import describe_allowlist, validate_run_command


# ---------------------------------------------------------------------------
# Small DAG builders matching the frozen node shapes.
# ---------------------------------------------------------------------------
def dag_with(nodes: dict, root: str = "N1") -> dict:
    return {"slug": "demo", "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def semantic(requirement: str = "r", satisfied_by=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if satisfied_by is not None:
        node["satisfied_by"] = satisfied_by
    return node


def edit(path: str, patch: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch}


def create(path: str, content: str) -> dict:
    return {"type": "create", "path": path, "content": content}


def remove(path: str) -> dict:
    return {"type": "remove", "path": path}


def move(from_path: str, to_path: str) -> dict:
    return {"type": "move", "from_path": from_path, "to_path": to_path}


def run(command=None) -> dict:
    return {"type": "run", "command": command or ["pytest"]}


def _write(workspace: Path, name: str, content: str) -> Path:
    path = workspace / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Coalescing / conflicts
# ---------------------------------------------------------------------------
def test_same_file_two_edits_coalesce_into_one_op(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "f.txt", "line1\nline2\nline3\n")
    first = "--- a/f.txt\n+++ b/f.txt\n@@ -1,1 +1,2 @@\n line1\n+inserted\n"
    second = "--- a/f.txt\n+++ b/f.txt\n@@ -4,1 +4,1 @@\n-line3\n+line3b\n"
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N3", "N4"]),
            "N3": edit("f.txt", first),
            "N4": edit("f.txt", second),
        }
    )
    ops, conflicts, blocked = compile_operations(dag, {}, workspace)
    assert conflicts == []
    assert blocked == []
    assert len(ops) == 1
    assert ops[0].op == "edit"
    assert ops[0].path == "f.txt"
    assert set(ops[0].nodes) == {"N3", "N4"}

    results = apply_compiled(ops, workspace)
    assert all(result["ok"] for result in results)
    assert (workspace / "f.txt").read_text(encoding="utf-8") == "line1\ninserted\nline2\nline3b\n"


def test_incompatible_create_plus_edit_conflicts_and_writes_nothing(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    bad_edit = "--- a/f.txt\n+++ b/f.txt\n@@ -1,1 +1,1 @@\n-goodbye\n+hi\n"
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N3", "N4"]),
            "N3": create("f.txt", "hello\n"),
            "N4": edit("f.txt", bad_edit),
        }
    )
    ops, conflicts, blocked = compile_operations(dag, {}, workspace)
    assert ops == []
    assert conflicts
    assert conflicts[0].path == "f.txt"
    assert conflicts[0].reason.startswith("context_conflict")
    assert set(conflicts[0].nodes) == {"N3", "N4"}
    # nothing was written because apply_compiled was never given an op
    assert apply_compiled(ops, workspace) == []
    assert not (workspace / "f.txt").exists()


def test_create_plus_compatible_edit_compiles(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    patch = "--- a/g.txt\n+++ b/g.txt\n@@ -1,1 +1,1 @@\n-old\n+new\n"
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("implementation", ["N3", "N4"]),
            "N3": create("g.txt", "old\n"),
            "N4": edit("g.txt", patch),
        }
    )
    ops, conflicts, blocked = compile_operations(dag, {}, workspace)
    assert conflicts == []
    assert len(ops) == 1 and ops[0].op == "create"
    results = apply_compiled(ops, workspace)
    assert results[0]["ok"] is True
    assert (workspace / "g.txt").read_text(encoding="utf-8") == "new\n"


def test_create_target_already_exists_is_conflict(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "exists.txt", "old\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N3"]),
            "N3": create("exists.txt", "new\n"),
        }
    )
    ops, conflicts, _ = compile_operations(dag, {}, workspace)
    assert ops == []
    assert any("already exists" in conflict.reason for conflict in conflicts)


def test_edit_and_remove_same_path_conflicts(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "f.py", "x\n")
    patch = "--- a/f.py\n+++ b/f.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N3", "N4"]),
            "N3": edit("f.py", patch),
            "N4": remove("f.py"),
        }
    )
    ops, conflicts, _ = compile_operations(dag, {}, workspace)
    assert ops == []
    assert conflicts and conflicts[0].path == "f.py"
    assert (workspace / "f.py").exists()


def test_move_source_also_edited_conflicts(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "a.py", "x\n")
    patch = "--- a/a.py\n+++ b/a.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N3", "N4"]),
            "N3": edit("a.py", patch),
            "N4": move("a.py", "b.py"),
        }
    )
    ops, conflicts, _ = compile_operations(dag, {}, workspace)
    assert ops == []
    assert any(conflict.path == "a.py" for conflict in conflicts)


def test_move_and_remove_are_coordinated(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "a.py", "data\n")
    _write(workspace, "c.py", "gone\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N3", "N4"]),
            "N3": move("a.py", "b.py"),
            "N4": remove("c.py"),
        }
    )
    ops, conflicts, _ = compile_operations(dag, {}, workspace)
    assert conflicts == []
    results = apply_compiled(ops, workspace)
    assert all(result["ok"] for result in results)
    assert not (workspace / "a.py").exists()
    assert (workspace / "b.py").read_text(encoding="utf-8") == "data\n"
    assert not (workspace / "c.py").exists()


def test_move_destination_collision_conflicts(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "a.py", "data\n")
    _write(workspace, "b.py", "taken\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N3"]),
            "N3": move("a.py", "b.py"),
        }
    )
    ops, conflicts, _ = compile_operations(dag, {}, workspace)
    assert ops == []
    assert any("destination" in conflict.reason for conflict in conflicts)


# ---------------------------------------------------------------------------
# apply_compiled
# ---------------------------------------------------------------------------
def test_apply_compiled_context_mismatch_writes_nothing(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "f.txt", "a\nb\nc\n")
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -2,1 +2,1 @@\n-b\n+B\n"
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N3"]),
            "N3": edit("f.txt", patch),
        }
    )
    ops, conflicts, _ = compile_operations(dag, {}, workspace)
    assert conflicts == []
    # Live state drifts after compilation.
    _write(workspace, "f.txt", "a\nX\nc\n")
    results = apply_compiled(ops, workspace)
    assert results[0]["ok"] is False
    assert results[0]["error"] == "context_mismatch"
    assert (workspace / "f.txt").read_text(encoding="utf-8") == "a\nX\nc\n"


def test_apply_compiled_create_does_not_overwrite(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    op = CompiledOp(nodes=["N9"], op="create", path="new.txt", content="hi\n")
    _write(workspace, "new.txt", "existing\n")
    results = apply_compiled([op], workspace)
    assert results[0]["ok"] is False
    assert results[0]["error"] == "context_mismatch"
    assert (workspace / "new.txt").read_text(encoding="utf-8") == "existing\n"


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------
def test_preflight_executable_with_unresolved_leaf_and_dirty_tree(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "f.txt", "a\nb\nc\n")
    _write(workspace, "dirty_untracked.txt", "noise\n")
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -2,1 +2,1 @@\n-b\n+B\n"
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N3"]),
            "N2": semantic("needs a product decision"),  # unresolved leaf
            "N3": edit("f.txt", patch),
        }
    )
    assert unresolved_leaves(dag) == ["N2"]
    result = preflight(dag, {}, workspace)
    assert result["executable"] is True
    assert result["issues"] == []
    assert result["conflicts"] == []


def test_preflight_not_executable_on_non_applying_patch(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "f.txt", "a\nb\n")
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1,1 +1,1 @@\n-zzz\n+yyy\n"
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N3"]),
            "N3": edit("f.txt", patch),
        }
    )
    result = preflight(dag, {}, workspace)
    assert result["executable"] is False
    assert any(issue["kind"] == "context_conflict" for issue in result["issues"])


def test_preflight_not_executable_on_structure_error(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = dag_with({"N1": semantic("root", ["N99"])})
    result = preflight(dag, {}, workspace)
    assert result["executable"] is False
    assert any(issue["kind"] == "structure" for issue in result["issues"])


def test_preflight_allows_unresolved_semantic_leaves(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": semantic("undecided")})
    result = preflight(dag, {}, workspace)
    assert result["executable"] is True
    assert result["issues"] == []


# ---------------------------------------------------------------------------
# run frontier
# ---------------------------------------------------------------------------
def test_ready_run_nodes_respects_run_barrier(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write(workspace, "x.txt", "a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("verify", ["N3", "N4"]),
            "N3": semantic("implement", ["N5"]),
            "N4": run(["pytest", "-q"]),
            "N5": edit("x.txt", "--- a/x.txt\n+++ b/x.txt\n@@ -1,1 +1,1 @@\n-a\n+b\n"),
        }
    )
    assert ready_run_nodes(dag, {}, workspace) == []
    assert ready_run_nodes(dag, {"N5": "satisfied"}, workspace) == ["N4"]


def test_ready_run_nodes_skips_satisfied_and_failed(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("verify", ["N3", "N4"]),
            "N3": semantic("implement", ["N5"]),
            "N4": run(["pytest"]),
            "N5": edit("x.txt", "--- a/x.txt\n+++ b/x.txt\n@@ -1,1 +1,1 @@\n-a\n+b\n"),
        }
    )
    assert ready_run_nodes(dag, {"N5": "satisfied", "N4": "satisfied"}, workspace) == []
    assert ready_run_nodes(dag, {"N5": "satisfied", "N4": "failed"}, workspace) == []


# ---------------------------------------------------------------------------
# node_present reconciliation
# ---------------------------------------------------------------------------
def test_node_present_create_outcomes(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": create("made.txt", "hello\n"),
        }
    )
    assert node_present(dag, "N2", workspace) == "absent"
    _write(workspace, "made.txt", "hello\n")
    assert node_present(dag, "N2", workspace) == "present"
    _write(workspace, "made.txt", "different\n")
    assert node_present(dag, "N2", workspace) == "ambiguous"


def test_node_present_edit_outcomes(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1,2 +1,2 @@\n a\n-b\n+B\n"
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": edit("f.txt", patch)})
    _write(workspace, "f.txt", "a\nb\n")
    assert node_present(dag, "N2", workspace) == "absent"
    _write(workspace, "f.txt", "a\nB\n")
    assert node_present(dag, "N2", workspace) == "present"
    _write(workspace, "f.txt", "zzz\n")
    assert node_present(dag, "N2", workspace) == "ambiguous"


def test_node_present_remove_and_move_outcomes(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    remove_dag = dag_with({"N1": semantic("root", ["N2"]), "N2": remove("gone.txt")})
    _write(workspace, "gone.txt", "x\n")
    assert node_present(remove_dag, "N2", workspace) == "absent"
    (workspace / "gone.txt").unlink()
    assert node_present(remove_dag, "N2", workspace) == "present"

    move_dag = dag_with({"N1": semantic("root", ["N2"]), "N2": move("from.txt", "to.txt")})
    _write(workspace, "from.txt", "x\n")
    assert node_present(move_dag, "N2", workspace) == "absent"
    (workspace / "from.txt").unlink()
    _write(workspace, "to.txt", "x\n")
    assert node_present(move_dag, "N2", workspace) == "present"
    (workspace / "to.txt").unlink()
    assert node_present(move_dag, "N2", workspace) == "ambiguous"


def test_node_present_semantic_is_ambiguous(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": semantic("thing")})
    assert node_present(dag, "N1", workspace) == "ambiguous"


# ---------------------------------------------------------------------------
# summarize / dataclasses
# ---------------------------------------------------------------------------
def test_summarize_counts_and_ids():
    op = CompiledOp(nodes=["N3", "N4"], op="edit", path="f.txt")
    conflict = Conflict(path="g.txt", nodes=["N5"], reason="compile_conflict: x")
    blocked = Blocked(node_id="N6", reason="ancestor failed")
    summary = summarize([op], [conflict], [blocked])
    assert summary["ops"] == 1
    assert summary["conflicts"] == 1
    assert summary["blocked"] == 1
    assert summary["paths"] == ["f.txt"]
    assert summary["nodes"] == ["N3", "N4"]
    assert summary["conflict_paths"] == ["g.txt"]
    assert summary["blocked_nodes"] == ["N6"]


# ---------------------------------------------------------------------------
# run-command policy
# ---------------------------------------------------------------------------
def test_run_policy_accepts_verification_commands():
    assert validate_run_command(["python3", "-m", "pytest", "-q"]) == (True, "")
    assert validate_run_command(["pytest"]) == (True, "")
    assert validate_run_command(["python3", "-m", "compileall", "."]) == (True, "")
    assert validate_run_command(["tsc", "--noEmit"]) == (True, "")
    assert validate_run_command(["cargo", "test"]) == (True, "")


def test_run_policy_rejects_forbidden_and_unlisted():
    allowed, reason = validate_run_command(["git", "commit", "-m", "x"])
    assert allowed is False and "git" in reason
    allowed, reason = validate_run_command(["gh", "pr", "create"])
    assert allowed is False
    allowed, _ = validate_run_command(["sh", "-c", "rm -rf /"])
    assert allowed is False
    allowed, _ = validate_run_command(["rm"])
    assert allowed is False
    allowed, _ = validate_run_command("rm")
    assert allowed is False
    allowed, _ = validate_run_command(["python3", "script.py"])
    assert allowed is False
    allowed, _ = validate_run_command(["pytest", ";", "rm"])
    assert allowed is False
    allowed, _ = validate_run_command([])
    assert allowed is False


def test_describe_allowlist_mentions_core_commands():
    lines = describe_allowlist()
    assert any("python3 -m pytest" in line for line in lines)
    assert any(line.startswith("pytest") for line in lines)
