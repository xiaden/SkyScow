"""Regression tests for semantic-boundary projected source inspection."""
from __future__ import annotations

from pathlib import Path

import json

from common.helpers.change_dag import atomic_write_json
from common.helpers.change_dag_ops_views import preview
from common.tools.dag_grep import dag_grep
from common.tools.dag_read import dag_read
from common.tools.dag_search import dag_search


def _write_bundle(root: Path, slug: str, dag: dict, state: dict | None = None) -> None:
    bundle = root / "artifacts" / "change-dags" / "pending" / slug
    bundle.mkdir(parents=True)
    atomic_write_json(bundle / "DAG.json", dag)
    atomic_write_json(bundle / "EXECUTION_STATE.json", state or {})
    (bundle / "WORK_LOG.jsonl").write_text("", encoding="utf-8")


def _dag() -> dict:
    return {
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "requires": ["N2", "N3"]},
            "N2": {"type": "semantic", "requirement": "lower", "requires": ["N4"]},
            "N3": {"type": "semantic", "requirement": "assigned", "requires": ["N5"]},
            "N4": {"type": "semantic", "requirement": "lower detail", "requires": ["N6"]},
            "N5": {"type": "create", "path": "assigned.txt", "content": "assigned\n"},
            "N6": {"type": "create", "path": "generated.txt", "content": "lower\n"},
        },
        "slug": "demo",
    }


def _setup(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "source.txt").write_text("live lower\n", encoding="utf-8")
    _write_bundle(root, "demo", _dag())
    return root


def test_projected_tools_expose_only_deeper_work(tmp_path):
    root = _setup(tmp_path)
    read = dag_read("demo", "N3", "generated.txt", workspace_root=root)
    assert read["present"] is True
    assert read["content"] == "lower\n"
    assert dag_read("demo", "N3", "assigned.txt", workspace_root=root)["present"] is False


def test_read_range_and_grep_are_compact(tmp_path):
    root = _setup(tmp_path)
    (root / "source.txt").write_text("one\ntarget here\nthree\n", encoding="utf-8")
    read = dag_read("demo", "N3", "source.txt", 2, 2, workspace_root=root)
    assert read == {
        "slug": "demo", "node_id": "N3", "path": "source.txt", "present": True,
        "start_line": 2, "end_line": 2, "content": "target here\n",
    }
    grep = dag_grep("demo", "N3", "target", workspace_root=root)
    assert grep["matches"] == [{"path": "source.txt", "line": 2}]
    assert "snippet" not in grep["matches"][0]


def test_remove_and_move_projection_updates_both_paths(tmp_path):
    root = _setup(tmp_path)
    dag = _dag()
    dag["nodes"]["N6"] = {"type": "move", "from_path": "source.txt", "to_path": "moved.txt"}
    _write_bundle(root, "move", {**dag, "slug": "move"})
    assert dag_read("move", "N3", "source.txt", workspace_root=root)["present"] is False
    assert dag_read("move", "N3", "moved.txt", workspace_root=root)["present"] is True


def test_search_ranks_and_reports_compact_scores(tmp_path):
    root = _setup(tmp_path)
    (root / "other.txt").write_text("lower lower lower\n", encoding="utf-8")
    results = dag_search("demo", "N3", "lower", path="other.txt", workspace_root=root)["results"]
    assert results == [{"path": "other.txt", "score": 12.0}]
    assert all(set(entry) == {"path", "score"} for entry in results)


def test_search_ignores_a_removed_path(tmp_path):
    root = _setup(tmp_path)
    dag = _dag()
    dag["nodes"]["N6"] = {"type": "remove", "path": "source.txt"}
    _write_bundle(root, "removed", {**dag, "slug": "removed"})
    assert dag_search("removed", "N3", "live", path="source.txt", workspace_root=root)["results"] == []


def test_projection_agrees_with_authoring_preview(tmp_path):
    root = _setup(tmp_path)
    (root / "source.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
    dag = _dag()
    dag["nodes"]["N6"] = {
        "type": "edit", "path": "source.txt",
        "patch": "--- a/source.txt\n+++ b/source.txt\n@@ -2,1 +2,1 @@\n-two\n+TWO\n",
    }
    _write_bundle(root, "edited", {**dag, "slug": "edited"})
    view = json.loads(preview(root, "edited", path="source.txt", node_id="N3")["output"])
    read = dag_read("edited", "N3", "source.txt", workspace_root=root)
    assert view["effective_source"] == "one\nTWO\nthree\n"
    assert read["content"] == view["effective_source"]
    assert view["live_source"] != view["effective_source"]


def test_invalid_paths_are_rejected(tmp_path):
    root = _setup(tmp_path)
    assert dag_read("demo", "N3", "../secret", workspace_root=root)["error"] == "invalid_path"
    assert dag_grep("demo", "N3", "[", workspace_root=root)["error"] == "invalid_pattern"


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "config" / "plugins" / "tools.ts"
TOOLS_PKG = REPO_ROOT / "config" / "tools" / "common" / "tools"
PROJECTED_TOOLS = ("dag_read", "dag_grep", "dag_search")


class TestProjectedToolsRegistered:
    def test_plugin_registers_each_projected_tool(self):
        text = PLUGIN.read_text(encoding="utf-8")
        for tool in PROJECTED_TOOLS:
            assert f"{tool}: tool(" in text, f"{tool} is not registered in tools.ts"
            assert f"common.tools.{tool}" in text, f"{tool} lost its runner dispatch"

    def test_python_modules_exist(self):
        for tool in PROJECTED_TOOLS:
            assert (TOOLS_PKG / f"{tool}.py").exists(), f"{tool}.py is missing"
