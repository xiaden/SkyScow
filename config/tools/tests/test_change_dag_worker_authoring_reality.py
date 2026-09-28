"""End-to-end authoring reality: the original dogfood failure shape.

A real Change DAG worker once thrashed because it tried to edit a file produced
by a *same-frontier peer*: the base was invisible to it, so it hand-rewrote a
unified diff roughly fifteen times and polled whole-DAG ``dag_validate`` until it
gave up. The worker had no way to know the file it wanted to edit was not part of
its reality.

This file pins the corrected behaviour as one narrative through the real
``dag_read`` / ``dag_add_edit`` surfaces:

1. defective shape -- the producer is a same-frontier peer, so the editor's base
   lens excludes it. The read reports the file absent and the structured edit is
   refused with ``edit_base_unavailable``; nothing is persisted and no global
   validation is consulted.
2. repaired shape -- the producer is accepted strictly-lower work, so the read
   reports the file present with ``accepted_lower`` provenance, the structured
   edit succeeds, and re-reading shows the worker's own ``owned`` work.

It also pins the two structural rules the Author depends on: ``edit`` is the only
composable direct terminal kind, and the exclusive terminals
(``create``/``move``/``remove``/``run``) cannot share a semantic parent with any
other terminal child -- the correct repair is semantic decomposition.
"""
from __future__ import annotations

import json
from pathlib import Path

from common.helpers.change_dag import atomic_write_json, dag_json_path, direct_terminal_errors
from common.tools.dag_add_edit import dag_add_edit
from common.tools.dag_read import dag_read

REPORT = "report.txt"
PRODUCED = "hello\nworld\n"
PEER_ONLY = "peer only\n"


def _write_bundle(root: Path, slug: str, dag: dict, state: dict | None = None) -> None:
    bundle = root / "artifacts" / "change-dags" / "pending" / slug
    bundle.mkdir(parents=True)
    atomic_write_json(bundle / "DAG.json", dag)
    atomic_write_json(bundle / "EXECUTION_STATE.json", state or {})
    (bundle / "WORK_LOG.jsonl").write_text("", encoding="utf-8")


def _workspace(tmp_path: Path, slug: str, dag: dict, files: dict[str, str] | None = None) -> Path:
    root = tmp_path / "workspace"
    root.mkdir(parents=True)
    for name, content in (files or {}).items():
        (root / name).write_text(content, encoding="utf-8")
    _write_bundle(root, slug, dag)
    return root


def _semantic(requirement: str, requires: list[str] | None = None, **extra) -> dict:
    node: dict = {"type": "semantic", "requirement": requirement}
    if requires:
        node["requires"] = list(requires)
    node.update(extra)
    return node


def _create(path: str, content: str) -> dict:
    return {"type": "create", "path": path, "content": content}


def _dag_text(root: Path, slug: str) -> str:
    return dag_json_path(root, slug).read_text(encoding="utf-8")


def _added_node_id(result: dict) -> str:
    assert "error" not in result, result
    return json.loads(result["output"])["node_id"]


# ---------------------------------------------------------------------------
# The original failure shape
# ---------------------------------------------------------------------------


def _defective_dag(slug: str = "peer") -> dict:
    """N8 produces the file, but N7 is a depth-2 peer of N3 -- invisible to N3."""
    return {
        "slug": slug,
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": _semantic("root", ["N2"], decomposition_only=True),
            "N2": _semantic("group", ["N3", "N7"]),
            "N3": _semantic("assigned"),
            "N7": _semantic("peer", ["N8"]),
            "N8": _create(REPORT, PEER_ONLY),
        },
    }


def _repaired_dag(slug: str = "lower") -> dict:
    """The producer is accepted strictly-lower work, causally reachable by N3."""
    return {
        "slug": slug,
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": _semantic("root", ["N2"], decomposition_only=True),
            "N2": _semantic("group", ["N3", "N4"]),
            "N3": _semantic("assigned"),
            "N4": _semantic("deeper branch", ["N9"]),
            "N9": _semantic("deepest", ["N6"]),
            "N6": _create(REPORT, PRODUCED),
        },
    }


def test_same_frontier_peer_is_not_a_legal_authoring_base(tmp_path):
    root = _workspace(tmp_path, "peer", _defective_dag())
    before = _dag_text(root, "peer")

    read = dag_read("peer", "N3", REPORT, workspace_root=root)
    assert read["present"] is False
    assert read["content"] is None
    assert read["provenance"] == []

    result = dag_add_edit(
        "peer", ["N3"], REPORT, [{"old": "hello\n", "new": "HELLO\n"}], workspace_root=root
    )
    assert result["error"] == "edit_base_unavailable", result
    assert _dag_text(root, "peer") == before


def test_causal_repair_unblocks_the_same_edit(tmp_path):
    root = _workspace(tmp_path, "lower", _repaired_dag())

    read = dag_read("lower", "N3", REPORT, workspace_root=root)
    assert read["present"] is True
    assert read["content"] == PRODUCED
    assert any(
        entry["relation"] == "accepted_lower" and "N6" in entry["node_ids"]
        for entry in read["provenance"]
    ), read["provenance"]

    added = dag_add_edit(
        "lower", ["N3"], REPORT, [{"old": "hello\n", "new": "HELLO\n"}], workspace_root=root
    )
    node_id = _added_node_id(added)

    reread = dag_read("lower", "N3", REPORT, workspace_root=root)
    assert reread["content"] == "HELLO\nworld\n"
    assert any(
        entry["relation"] == "owned" and node_id in entry["node_ids"]
        for entry in reread["provenance"]
    ), reread["provenance"]
    assert any(
        entry["relation"] == "accepted_lower" for entry in reread["provenance"]
    ), reread["provenance"]


# ---------------------------------------------------------------------------
# Structural rules the Author relies on
# ---------------------------------------------------------------------------


def test_two_direct_edits_on_a_common_base_are_supportable(tmp_path):
    root = _workspace(tmp_path, "multi", _repaired_dag("multi"), {"other.txt": "x\ny\n"})

    first = dag_add_edit(
        "multi", ["N3"], REPORT, [{"old": "hello\n", "new": "HELLO\n"}], workspace_root=root
    )
    second = dag_add_edit(
        "multi", ["N3"], "other.txt", [{"old": "x\n", "new": "X\n"}], workspace_root=root
    )
    assert "error" not in first, first
    assert "error" not in second, second

    reread = dag_read("multi", "N3", REPORT, workspace_root=root)
    assert reread["content"] == "HELLO\nworld\n"

    dag = json.loads(_dag_text(root, "multi"))
    edits = [
        node_id
        for node_id, node in dag["nodes"].items()
        if node.get("type") == "edit" and node.get("path") == REPORT
    ]
    assert len(edits) == 1
    assert direct_terminal_errors(dag) == []


def test_create_beside_edit_is_structurally_rejected():
    dag = _repaired_dag("bad")
    dag["nodes"]["N3"] = _semantic("assigned", ["N5", "N12"])
    dag["nodes"]["N5"] = _create("a.txt", "a\n")
    dag["nodes"]["N12"] = {"type": "edit", "path": "a.txt", "patch": ""}
    errors = direct_terminal_errors(dag)
    assert errors and any("exclusive terminal" in error for error in errors), errors


def test_two_creates_are_structurally_rejected():
    dag = _repaired_dag("bad2")
    dag["nodes"]["N3"] = _semantic("assigned", ["N5", "N12"])
    dag["nodes"]["N5"] = _create("a.txt", "a\n")
    dag["nodes"]["N12"] = _create("b.txt", "b\n")
    errors = direct_terminal_errors(dag)
    assert errors and any("exclusive terminal" in error for error in errors), errors


def test_semantic_decomposition_around_separate_creates_is_valid():
    dag = {
        "slug": "decomposed",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": _semantic("root", ["N2"], decomposition_only=True),
            "N2": _semantic("both files exist", ["N3", "N4"], decomposition_only=True),
            "N3": _semantic("a.txt exists", ["N5"]),
            "N4": _semantic("b.txt exists", ["N6"]),
            "N5": _create("a.txt", "a\n"),
            "N6": _create("b.txt", "b\n"),
        },
    }
    assert direct_terminal_errors(dag) == []
