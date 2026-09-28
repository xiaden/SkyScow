"""Regression tests for canonical Change DAG path identity.

The compiler groups, coordinates, and reports work by path string. Spellings
that name the same repository file -- ``foo.py``, ``./foo.py``,
``src/../foo.py`` -- must share one canonical workspace-relative identity.
Without it two DAG operations compile independently against one live file and
collide only at application time, appearing as runtime drift instead of a
deterministic intra-DAG coordination result.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag
from common.helpers.change_dag_compiler_lowering import compile_operations
from common.helpers.change_dag_compiler_phase import preflight
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import add_work, update_node
from common.helpers.change_dag_ops_views import preview


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def dag_with(nodes, root="N1", slug="demo"):
    rooted_nodes = dict(nodes)
    rooted_nodes[root] = {**rooted_nodes[root], "decomposition_only": True}
    return {"slug": slug, "anchor_commit": "a" * 40, "root": root, "nodes": rooted_nodes}


def semantic(requirement="r", requires=None):
    node = {"type": "semantic", "requirement": requirement}
    if requires:
        node["requires"] = requires
    return node


def patch(path, old, new, *, line=1):
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"


def edit(path, patch_text):
    return {"type": "edit", "path": path, "patch": patch_text}


def create(path, content):
    return {"type": "create", "path": path, "content": content}


def move(from_path, to_path):
    return {"type": "move", "from_path": from_path, "to_path": to_path}


def peer_dag(first, second):
    return dag_with({
        "N1": semantic(requires=["N2"]),
        "N2": semantic(requires=["N10", "N11"]),
        "N10": first,
        "N11": second,
    })


def workspace(tmp_path, **files):
    for name, content in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# The canonicalization rule itself
# ---------------------------------------------------------------------------
def test_canonical_path_normalizes_equivalent_spellings():
    assert change_dag.canonical_path("foo.py") == "foo.py"
    assert change_dag.canonical_path("./foo.py") == "foo.py"
    assert change_dag.canonical_path("src/../foo.py") == "foo.py"
    assert change_dag.canonical_path("a//b.py") == "a/b.py"
    assert change_dag.canonical_path("a/./b.py") == "a/b.py"
    assert change_dag.canonical_path("src/a/../../x") == "x"
    assert change_dag.canonical_path("pkg/mod.py") == "pkg/mod.py"


def test_canonical_path_rejects_unrepresentable_forms():
    for bad in (
        "", ".", "..", "../x", "src/../../x", "/abs/x", "C:x", "~user/x",
        "dir/", "a\\b.py", "a\x00b", None, 7,
    ):
        with pytest.raises(ValueError):
            change_dag.canonical_path(bad)


# ---------------------------------------------------------------------------
# 1-2. Equivalent spellings share one compiler identity
# ---------------------------------------------------------------------------
def test_edit_spellings_share_one_path_identity(tmp_path):
    root = workspace(tmp_path, **{"foo.py": "a\nb\n"})
    dag = peer_dag(
        edit("foo.py", patch("foo.py", "a", "A")),
        edit("./foo.py", patch("./foo.py", "b", "B", line=2)),
    )
    ops, conflicts, blocked = compile_operations(dag, {}, root)
    assert conflicts == []
    assert blocked == []
    assert len(ops) == 1
    assert ops[0].path == "foo.py"
    assert set(ops[0].nodes) == {"N10", "N11"}
    assert ops[0].applied == "A\nB\n"


def test_parent_component_spelling_shares_identity(tmp_path):
    root = workspace(tmp_path, **{"foo.py": "a\nb\n"})
    (tmp_path / "src").mkdir()
    dag = peer_dag(
        edit("foo.py", patch("foo.py", "a", "A")),
        edit("src/../foo.py", patch("src/../foo.py", "b", "B", line=2)),
    )
    ops, conflicts, _blocked = compile_operations(dag, {}, root)
    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].path == "foo.py"
    assert ops[0].applied == "A\nB\n"


# ---------------------------------------------------------------------------
# 3. Alias spellings across kinds are coordinated as one file
# ---------------------------------------------------------------------------
def test_create_and_edit_alias_compile_as_one_file(tmp_path):
    root = workspace(tmp_path)
    dag = peer_dag(
        create("./new.py", "old\n"),
        edit("new.py", patch("new.py", "old", "new")),
    )
    ops, conflicts, _blocked = compile_operations(dag, {}, root)
    assert conflicts == []
    assert len(ops) == 1
    assert ops[0].op == "create"
    assert ops[0].path == "new.py"
    assert ops[0].applied == "new\n"


# ---------------------------------------------------------------------------
# 4. Move destination aliases coordinate deterministically
# ---------------------------------------------------------------------------
def test_move_destination_alias_collides_with_edit(tmp_path):
    root = workspace(tmp_path, **{"source.py": "x\n", "target.py": "t\n"})
    dag = peer_dag(
        move("source.py", "./target.py"),
        edit("target.py", patch("target.py", "t", "T")),
    )
    ops, conflicts, _blocked = compile_operations(dag, {}, root)
    assert ops == []
    dest = [c for c in conflicts if "move destination collides with other work" in c.reason]
    assert len(dest) == 1
    assert set(dest[0].nodes) == {"N10", "N11"}
    assert dest[0].scope == "intra_dag"


def test_move_source_alias_matches_edit_coordination(tmp_path):
    root = workspace(tmp_path, **{"src/mod.py": "x\n", "dest.py": ""})
    dag = peer_dag(
        move("src/mod.py", "dest.py"),
        edit("./src/mod.py", patch("./src/mod.py", "x", "y")),
    )
    ops, conflicts, _blocked = compile_operations(dag, {}, root)
    assert ops == []
    assert any("move source is also edited/removed" in c.reason for c in conflicts)


# ---------------------------------------------------------------------------
# 5-8. Plain spellings, boundaries, and validation stay compatible
# ---------------------------------------------------------------------------
def test_plain_spellings_are_unchanged(tmp_path):
    root = workspace(tmp_path, **{"pkg/mod.py": "a\n"})
    dag = dag_with({
        "N1": semantic(requires=["N2"]),
        "N2": semantic(requires=["N3", "N4"]),
        "N3": edit("pkg/mod.py", patch("pkg/mod.py", "a", "b")),
        "N4": create("pkg/other.py", "new\n"),
    })
    ops, conflicts, _blocked = compile_operations(dag, {}, root)
    assert conflicts == []
    assert sorted(op.path for op in ops) == ["pkg/mod.py", "pkg/other.py"]


def test_authoring_boundary_canonicalizes_and_rejects(tmp_path):
    root = workspace(tmp_path)
    assert create_dag(root, "identity", {"root": "r", "nodes": {"r": {"requirement": "root", "requires": ["semantic"]}, "semantic": {"requirement": "authoring"}}}
                      ).get("error") is None

    (tmp_path / "foo.py").write_text("a\n", encoding="utf-8")
    assert add_work(root, "identity", "edit", ["N2"], path="./src/../foo.py",
                    replacements=[{"old": "a", "new": "b"}]).get("error") is None
    dag, _path, _location = change_dag.read_dag(root, "identity")
    assert change_dag.node_map(dag)["N3"]["path"] == "foo.py"

    before = dict(change_dag.node_map(dag))
    for bad in ("/etc/passwd", "../escape.py", "a\\b.py", "~/.bashrc", "dir/"):
        rejected = add_work(root, "identity", "create", ["N2"], path=bad, content="x\n")
        assert rejected["error"] == "invalid_path", bad
        assert rejected["message"].startswith("path: "), bad
    dag, _path, _location = change_dag.read_dag(root, "identity")
    assert dict(change_dag.node_map(dag)) == before


def test_update_node_canonicalizes_and_rejects_unusable_paths(tmp_path):
    root = workspace(tmp_path, **{"x.py": "a\n"})
    assert create_dag(root, "identity", {"root": "r", "nodes": {"r": {"requirement": "root", "requires": ["semantic"]}, "semantic": {"requirement": "authoring"}}}
                      ).get("error") is None
    assert add_work(root, "identity", "edit", ["N2"], path="x.py",
                    replacements=[{"old": "a", "new": "b"}]).get("error") is None

    rejected = update_node(root, "identity", "N3", path="../escape.py")
    assert rejected["error"] == "invalid_path"

    updated = update_node(root, "identity", "N3", path="./pkg/../y.py")
    assert updated.get("error") is None
    dag, _path, _location = change_dag.read_dag(root, "identity")
    assert change_dag.node_map(dag)["N3"]["path"] == "y.py"


def test_structure_validation_flags_unusable_paths(tmp_path):
    root = workspace(tmp_path)
    dag = dag_with({
        "N1": semantic(requires=["N2"]),
        "N2": edit("../escape.py", patch("../escape.py", "a", "b")),
    })
    errors = change_dag.structure_errors(dag)
    assert any("not a usable workspace-relative path" in error for error in errors)

    result = preflight(dag, {}, root)
    assert result["executable"] is False
    assert any(issue["kind"] == "structure" for issue in result["issues"])


def test_compiler_reports_unusable_path_without_splitting_identity(tmp_path):
    root = workspace(tmp_path, **{"foo.py": "a\n"})
    dag = peer_dag(
        edit("foo.py", patch("foo.py", "a", "A")),
        edit("../foo.py", patch("../foo.py", "a", "C")),
    )
    ops, conflicts, _blocked = compile_operations(dag, {}, root)
    assert [op.nodes for op in ops] == [["N10"]]
    assert all(conflict.scope == "intra_dag" for conflict in conflicts)
    assert any("not a usable workspace-relative path" in conflict.reason for conflict in conflicts)


# ---------------------------------------------------------------------------
# 7. Preview uses canonical identity and never duplicates one file
# ---------------------------------------------------------------------------
def test_preview_uses_canonical_identity_and_does_not_duplicate(tmp_path):
    root = workspace(tmp_path, **{"foo.py": "a\nb\n"})
    assert create_dag(root, "identity", {"root": "r", "nodes": {"r": {"requirement": "root", "requires": ["semantic"]}, "semantic": {"requirement": "authoring"}}}
                      ).get("error") is None
    add_work(root, "identity", "edit", ["N2"], path="foo.py",
             replacements=[{"old": "a", "new": "A"}])
    add_work(root, "identity", "edit", ["N2"], path="./foo.py",
             replacements=[{"old": "b", "new": "B"}])

    payload = json.loads(preview(root, "identity")["output"])
    assert [op["path"] for op in payload["ops"]] == ["foo.py"]
    assert set(payload["ops"][0]["nodes"]) == {"N3", "N4"}
    assert payload["conflicts"] == []
    assert payload["executable"] is True

    scoped = json.loads(preview(root, "identity", path="./foo.py")["output"])
    assert [op["path"] for op in scoped["ops"]] == ["foo.py"]

    assert preview(root, "identity", path="../escape.py")["error"] == "invalid_path"
