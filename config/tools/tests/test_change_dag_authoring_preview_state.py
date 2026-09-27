"""F10: authoring preview respects execution state without projecting twice."""
from __future__ import annotations

import json
from pathlib import Path

from common.helpers.change_dag_ops import preview


def semantic(requirement: str, children=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if children is not None:
        node["satisfied_by"] = children
    return node


def edit(path: str, patch_text: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch_text}


def patch(path: str, old: str, new: str) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,1 @@\n-{old}\n+{new}\n"


def insert(path: str) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,2 @@\n a\n+ins\n"


def bundle(root: Path, slug: str, dag: dict, state: dict[str, str]) -> None:
    path = root / "artifacts/change-dags/pending" / slug
    path.mkdir(parents=True)
    (path / "DAG.json").write_text(json.dumps(dag), encoding="utf-8")
    (path / "EXECUTION_STATE.json").write_text(json.dumps(state), encoding="utf-8")
    (path / "WORK_LOG.jsonl").write_text("", encoding="utf-8")


def body(root: Path, slug: str = "preview") -> dict:
    return json.loads(preview(root, slug, path="f.txt", node_id="N2")["output"])


def graph(lower: dict) -> dict:
    return {
        "slug": "preview",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("higher boundary", ["N5"]),
            "N5": semantic("lower work", ["N10"]),
            "N10": lower,
        },
    }


def test_satisfied_insertion_is_not_reprojected(tmp_path: Path):
    (tmp_path / "f.txt").write_text("a\nins\n", encoding="utf-8")
    bundle(tmp_path, "preview", graph(edit("f.txt", insert("f.txt"))), {"N10": "satisfied"})

    result = body(tmp_path)
    assert result["effective_source"] == "a\nins\n"
    assert result["ops"] == []
    assert result["conflicts"] == []


def test_satisfied_replacement_is_not_replayed_against_live_content(tmp_path: Path):
    (tmp_path / "f.txt").write_text("new\n", encoding="utf-8")
    bundle(tmp_path, "preview", graph(edit("f.txt", patch("f.txt", "old", "new"))), {"N10": "satisfied"})

    result = body(tmp_path)
    assert result["effective_source"] == "new\n"
    assert result["ops"] == []
    assert result["conflicts"] == []


def test_failed_lower_work_still_projects_and_preview_is_read_only(tmp_path: Path):
    target = tmp_path / "f.txt"
    target.write_text("a\n", encoding="utf-8")
    graph_data = graph(edit("f.txt", insert("f.txt")))
    bundle(tmp_path, "preview", graph_data, {"N10": "failed"})
    before = target.read_bytes()

    result = body(tmp_path)
    assert result["effective_source"] == "a\nins\n"
    assert result["contributing_nodes"] == ["N10"]
    assert target.read_bytes() == before


def test_same_frontier_and_shallower_work_remain_excluded(tmp_path: Path):
    (tmp_path / "f.txt").write_text("a\n", encoding="utf-8")
    graph_data = {
        "slug": "preview",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": semantic("root", ["N2", "N11"]),
            "N2": semantic("boundary", ["N10"]),
            "N10": edit("f.txt", insert("f.txt")),
            "N11": edit("f.txt", patch("f.txt", "a", "shallower")),
        },
    }
    bundle(tmp_path, "preview", graph_data, {})

    result = body(tmp_path)
    assert result["effective_source"] == "a\n"
    assert result["contributing_nodes"] == []
    assert result["excluded_later_work"]["same_frontier_nodes"] == 1
    assert result["excluded_later_work"]["shallower_nodes"] == 1
