"""Focused regression tests: one edit node is exactly one file operation.

The Change DAG edit-node boundary must accept exactly one ``FilePatch`` per edit
node. A patch with two or more file sections, a header target that does not
canonicalize to the node's declared path, or an unsupported special form is a
deterministic compile/preflight/preview failure: no op is lowered and nothing is
written. The generic :func:`parse_unified_diff` multi-file support is unchanged;
the one-file contract lives at the edit-node boundary.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers.change_dag_compiler_lowering import compile_operations  # noqa: E402
from common.helpers.change_dag_compiler_phase import preflight  # noqa: E402
from common.helpers.change_dag_compiler_runtime import apply_compiled  # noqa: E402
from common.helpers.change_dag_ops_views import preview  # noqa: E402
from common.helpers.change_dag_patch import parse_unified_diff  # noqa: E402


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def dag_with(nodes: dict, root: str = "N1", slug: str = "demo") -> dict:
    # The root is always decomposition_only; fixtures only supply the graph.
    nodes.setdefault(root, {}).setdefault("decomposition_only", True)
    return {"slug": slug, "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def semantic(requirement: str = "r", requires=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if requires is not None:
        node["requires"] = requires
    return node


def edit(path: str, patch: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch}


def single_edit_dag(path: str, patch: str) -> dict:
    return dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N3"]),
            "N3": edit(path, patch),
        }
    )


def one_file(path: str, old: str, new: str) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,1 @@\n-{old}\n+{new}\n"


def make_workspace(tmp_path: Path, files: dict[str, str]) -> Path:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    for rel, content in files.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return workspace


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    }


def write_bundle(root: Path, slug: str, dag: dict, state: dict | None = None) -> None:
    bundle = root / "artifacts/change-dags/pending" / slug
    bundle.mkdir(parents=True)
    (bundle / "DAG.json").write_text(json.dumps(dag))
    (bundle / "EXECUTION_STATE.json").write_text(json.dumps(state or {}))
    (bundle / "WORK_LOG.jsonl").write_text("")


def payload(workspace: Path, *args, **kwargs) -> dict:
    return json.loads(preview(workspace, *args, **kwargs)["output"])


# ---------------------------------------------------------------------------
# 1. Normal one-file edit remains accepted
# ---------------------------------------------------------------------------
def test_normal_single_file_edit_is_accepted_and_applies(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"foo.py": "old\n"})
    dag = single_edit_dag("foo.py", one_file("foo.py", "old", "new"))

    ops, conflicts, blocked = compile_operations(dag, {}, workspace)
    assert conflicts == []
    assert blocked == []
    assert len(ops) == 1
    assert ops[0].op == "edit"
    assert ops[0].path == "foo.py"

    results = apply_compiled(ops, workspace)
    assert all(result["ok"] for result in results)
    assert (workspace / "foo.py").read_text(encoding="utf-8") == "new\n"


def test_a_b_headers_and_lexical_spellings_canonicalize_to_declared_path(tmp_path: Path):
    # The existing path convention: a/ and b/ prefixes and lexical ./../
    # components normalize, so all of these match a declared ``foo.py``.
    workspace = make_workspace(tmp_path, {"foo.py": "old\n"})
    patch = "--- a/./foo.py\n+++ b/sub/../foo.py\n@@ -1,1 +1,1 @@\n-old\n+new\n"
    dag = single_edit_dag("foo.py", patch)

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)
    assert conflicts == []
    assert len(ops) == 1 and ops[0].path == "foo.py"
    assert apply_compiled(ops, workspace)[0]["ok"]
    assert (workspace / "foo.py").read_text(encoding="utf-8") == "new\n"


# ---------------------------------------------------------------------------
# 2. Two file sections are a deterministic compile failure; nothing is written
# ---------------------------------------------------------------------------
def test_two_file_sections_are_rejected_without_writing(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"foo.py": "old\n", "bar.py": "b\n"})
    patch = one_file("foo.py", "old", "new") + one_file("bar.py", "b", "B")
    dag = single_edit_dag("foo.py", patch)
    before = snapshot(workspace)

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)
    assert ops == []
    assert any(
        conflict.reason.startswith("compile_conflict: malformed patch")
        and "2 file sections" in conflict.reason
        for conflict in conflicts
    )
    # No op was lowered, so nothing can be applied and the tree is untouched.
    assert apply_compiled(ops, workspace) == []
    assert snapshot(workspace) == before


# ---------------------------------------------------------------------------
# 3. Multi-file patch rejected even when both sections happen to fit the target
# ---------------------------------------------------------------------------
def test_coincidentally_fitting_sections_still_rejected(tmp_path: Path):
    # Declared ``f.txt`` and every section also targets ``f.txt``, so treating
    # the patch as extra hunks would silently apply. The one-node/one-file
    # contract rejects it on the section count alone.
    workspace = make_workspace(tmp_path, {"f.txt": "a\nb\nc\n"})
    patch = one_file("f.txt", "a", "A") + one_file("f.txt", "c", "C")
    dag = single_edit_dag("f.txt", patch)

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)
    assert ops == []
    assert any("2 file sections" in conflict.reason for conflict in conflicts)
    assert snapshot(workspace)["f.txt"] == b"a\nb\nc\n"


# ---------------------------------------------------------------------------
# 4. Declared/header path mismatch is rejected
# ---------------------------------------------------------------------------
def test_declared_header_path_mismatch_is_rejected(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"foo.py": "old\n", "bar.py": "b\n"})
    dag = single_edit_dag("foo.py", one_file("bar.py", "old", "new"))
    before = snapshot(workspace)

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)
    assert ops == []
    assert any(
        conflict.reason.startswith("compile_conflict: malformed patch")
        and "does not match declared path 'foo.py'" in conflict.reason
        for conflict in conflicts
    )
    assert apply_compiled(ops, workspace) == []
    assert snapshot(workspace) == before


# ---------------------------------------------------------------------------
# 5. Unsupported special forms (e.g. /dev/null) are rejected, not expanded
# ---------------------------------------------------------------------------
def test_dev_null_target_is_rejected(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"foo.py": "old\n"})
    patch = "--- a/foo.py\n+++ /dev/null\n@@ -1,1 +0,0 @@\n-old\n"
    # The parser itself is generic and yields one FilePatch; the edit-node
    # boundary rejects the special form.
    assert len(parse_unified_diff(patch)) == 1
    dag = single_edit_dag("foo.py", patch)

    ops, conflicts, _blocked = compile_operations(dag, {}, workspace)
    assert ops == []
    assert any(
        conflict.reason.startswith("compile_conflict: malformed patch")
        and "not a usable workspace-relative path" in conflict.reason
        for conflict in conflicts
    )
    assert snapshot(workspace)["foo.py"] == b"old\n"


# ---------------------------------------------------------------------------
# 6. preflight, whole-DAG preview, and authoring preview agree
# ---------------------------------------------------------------------------
def test_preflight_and_preview_surface_same_deterministic_conflict(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"foo.py": "old\n", "bar.py": "b\n"})
    patch = one_file("foo.py", "old", "new") + one_file("bar.py", "b", "B")
    dag = single_edit_dag("foo.py", patch)
    write_bundle(workspace, "demo", dag)

    pre = preflight(dag, {}, workspace)
    assert pre["executable"] is False
    assert any(
        issue["kind"] == "compile_conflict"
        and issue["message"].startswith("compile_conflict: malformed patch")
        and "2 file sections" in issue["message"]
        for issue in pre["issues"]
    )

    whole = payload(workspace, "demo")
    assert whole["mode"] == "whole_dag"
    assert whole["executable"] is False
    assert whole["ops"] == []
    assert any(
        issue["message"].startswith("compile_conflict: malformed patch")
        for issue in whole["issues"]
    )
    assert any(
        conflict["reason"].startswith("compile_conflict: malformed patch")
        for conflict in whole["conflicts"]
    )

    # A frontier-bounded authoring view lowers through the same boundary.
    layered = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("boundary", ["N5"]),
            "N5": semantic("lower", ["N10"]),
            "N10": edit("foo.py", patch),
        }
    )
    write_bundle(workspace, "layered", layered)
    authoring = payload(workspace, "layered", path="foo.py", node_id="N2")
    assert authoring["mode"] == "authoring_context"
    assert any(
        conflict["reason"].startswith("compile_conflict: malformed patch")
        for conflict in authoring["conflicts"]
    )
