"""Regression tests for semantic-boundary projected source inspection."""
from __future__ import annotations

from pathlib import Path

import json

from common.helpers.change_dag import atomic_write_json
from common.helpers.change_dag_ops_views import preview
from common.helpers.change_dag_projection import live_paths, projected_source
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


def test_live_paths_uses_git_files_and_excludes_ignored(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    calls = []

    class Result:
        returncode = 0
        stdout = b"tracked.txt\x00dir/name.txt\x00weird name.txt\x00"

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return Result()

    monkeypatch.setattr("common.helpers.change_dag_projection.subprocess.run", fake_run)
    assert live_paths(root) == ["dir/name.txt", "tracked.txt", "weird name.txt"]
    assert calls[0][0] == ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    assert calls[0][1]["shell"] is False


def test_projected_tools_expose_only_deeper_work(tmp_path):
    root = _setup(tmp_path)
    read = dag_read("demo", "N3", "generated.txt", workspace_root=root)
    assert read["present"] is True
    assert read["content"] == "lower\n"
    assert dag_read("demo", "N3", "assigned.txt", workspace_root=root)["present"] is True


def test_read_range_and_grep_are_compact(tmp_path):
    root = _setup(tmp_path)
    (root / "source.txt").write_text("one\ntarget here\nthree\n", encoding="utf-8")
    read = dag_read("demo", "N3", "source.txt", 2, 2, workspace_root=root)
    assert read == {
        "slug": "demo", "node_id": "N3", "path": "source.txt", "present": True,
         "start_line": 2, "end_line": 2, "content": "target here\n",
         "provenance": [{"lines": [2, 2], "node_ids": [], "relation": "live"}],
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


def test_malformed_applicable_work_is_reported_not_silently_live(tmp_path):
    """When strictly-deeper work cannot be reproduced, say so.

    Returning live content as if it were the accepted projection would send the
    worker to author against text that deeper work intends to replace.
    """
    root = _setup(tmp_path)
    (root / "source.txt").write_text("live\n", encoding="utf-8")
    (root / "other.txt").write_text("unrelated\n", encoding="utf-8")
    dag = _dag()
    dag["nodes"]["N6"] = {"type": "edit", "path": "source.txt", "patch": "not a diff"}
    _write_bundle(root, "broken", {**dag, "slug": "broken"})

    read = dag_read("broken", "N3", "source.txt", workspace_root=root)
    assert read["error"] == "projection_failed"
    assert read["path"] == "source.txt"
    assert read["nodes"] == ["N6"]
    assert dag_grep(
        "broken", "N3", "live", path="source.txt", workspace_root=root
    )["error"] == "projection_failed"
    assert dag_search(
        "broken", "N3", "live", path="source.txt", workspace_root=root
    )["error"] == "projection_failed"
    # The failure is scoped to the affected path, not the whole DAG...
    assert dag_read("broken", "N3", "other.txt", workspace_root=root)["content"] == "unrelated\n"
    # ...but a BROAD search must report that its truth is incomplete rather
    # than silently omitting the path it could not reproduce.
    broad = dag_grep("broken", "N3", "unrelated", workspace_root=root)
    assert broad["error"] == "projection_failed"
    assert [entry["path"] for entry in broad["failures"]] == ["source.txt"]


def test_base_view_excludes_boundary_owned_work(tmp_path):
    """BASE projection ignores the boundary's own work; the self view does not."""
    root = _setup(tmp_path)
    (root / "source.txt").write_text("live\n", encoding="utf-8")
    dag = _dag()
    dag["nodes"]["N5"] = {"type": "edit", "path": "source.txt", "patch": "not a diff"}
    _write_bundle(root, "owned", {**dag, "slug": "owned"})

    base, error = projected_source(root, "owned", "N3")
    assert error is None and base is not None
    assert base.content("source.txt") == "live\n"
    # The self view includes that malformed proposal, so it reports the failure
    # rather than returning live content as if it were the self projection.
    assert dag_read("owned", "N3", "source.txt", workspace_root=root)["error"] == "projection_failed"


def test_read_clamps_end_beyond_eof_and_provenance(tmp_path):
    root = _setup(tmp_path)
    (root / "source.txt").write_text("one\ntwo\n", encoding="utf-8")
    result = dag_read("demo", "N3", "source.txt", 2, 99, workspace_root=root)
    assert result["start_line"] == 2
    assert result["end_line"] == 2
    assert result["content"] == "two\n"
    assert result["provenance"] == [{"lines": [2, 2], "node_ids": [], "relation": "live"}]


def test_read_rejects_invalid_and_out_of_range_start(tmp_path):
    root = _setup(tmp_path)
    for start, end in ((0, 1), (1, 0), (2, 1), (99, 100)):
        result = dag_read("demo", "N3", "source.txt", start, end, workspace_root=root)
        assert result["error"] == "invalid_range"


def test_large_live_read_streams_bounded_range(tmp_path, monkeypatch):
    root = _setup(tmp_path)
    target = root / "source.txt"
    target.write_text("\n".join(f"line {i}" for i in range(1, 8)) + "\n", encoding="utf-8")
    monkeypatch.setattr("common.tools.dag_read.change_dag_patch.MAX_MATERIALIZED_TEXT_BYTES", 10)
    result = dag_read("demo", "N3", "source.txt", 6, 99, workspace_root=root)
    assert result["content"] == "line 6\nline 7\n"
    assert result["end_line"] == 7


def test_large_full_read_reports_range_required(tmp_path, monkeypatch):
    root = _setup(tmp_path)
    (root / "source.txt").write_text("line\n" * 10, encoding="utf-8")
    monkeypatch.setattr("common.tools.dag_read.change_dag_patch.MAX_MATERIALIZED_TEXT_BYTES", 10)
    result = dag_read("demo", "N3", "source.txt", workspace_root=root)
    assert result["error"] == "range_required"


def test_broad_grep_streams_late_match_in_large_live_file(tmp_path, monkeypatch):
    root = _setup(tmp_path)
    (root / "late.txt").write_text("quiet\n" * 10 + "needle\n", encoding="utf-8")
    monkeypatch.setattr("common.helpers.change_dag_patch.MAX_MATERIALIZED_TEXT_BYTES", 10)
    result = dag_grep("demo", "N3", "needle", workspace_root=root)
    assert {tuple(match.values()) for match in result["matches"]} == {("late.txt", 11)}


def test_broad_search_reports_oversized_candidate_explicitly(tmp_path, monkeypatch):
    root = _setup(tmp_path)
    (root / "large.txt").write_text("needle\n" * 10, encoding="utf-8")
    monkeypatch.setattr("common.helpers.change_dag_patch.MAX_MATERIALIZED_TEXT_BYTES", 10)
    result = dag_search("demo", "N3", "needle", workspace_root=root)
    assert result["error"] == "search_incomplete"
    assert result["path"] == "large.txt"


def test_projected_oversized_path_reports_incomplete(tmp_path, monkeypatch):
    root = _setup(tmp_path)
    (root / "source.txt").write_text("live\n", encoding="utf-8")
    monkeypatch.setattr("common.helpers.change_dag_patch.MAX_MATERIALIZED_TEXT_BYTES", 10)
    dag = _dag()
    dag["nodes"]["N6"] = {"type": "create", "path": "projected.txt", "content": "needle\n" * 10}
    _write_bundle(root, "projected-large", {**dag, "slug": "projected-large"})
    result = dag_search("projected-large", "N3", "needle", workspace_root=root)
    assert result["error"] == "search_incomplete"
    assert result["path"] == "projected.txt"
