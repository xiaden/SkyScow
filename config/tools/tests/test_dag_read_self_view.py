"""Self-view projection: BASE plus the boundary node's own terminal work.

``dag_read`` exposes what the worker itself just authored (its direct terminal
children) on top of the accepted strictly-lower work it may rely on, while
still excluding same-frontier peers, shallower work, future work, and unowned
sibling proposals. Provenance names which lens produced each range.
"""
from __future__ import annotations

from pathlib import Path

from common.helpers.change_dag import atomic_write_json, direct_terminal_errors
from common.helpers.change_dag_projection import projected_self_source, projected_source
from common.tools.dag_read import dag_read


def _write_bundle(root: Path, slug: str, dag: dict, state: dict | None = None) -> None:
    bundle = root / "artifacts" / "change-dags" / "pending" / slug
    bundle.mkdir(parents=True)
    atomic_write_json(bundle / "DAG.json", dag)
    atomic_write_json(bundle / "EXECUTION_STATE.json", state or {})
    (bundle / "WORK_LOG.jsonl").write_text("", encoding="utf-8")


def _dag(*, owned: dict, lower: dict | None = None, peer: bool = False,
         shallow: bool = False, peer_owned: dict | None = None, slug: str = "self") -> dict:
    """Structurally valid graph: boundary N3 (depth 2), owned child N5."""
    nodes: dict[str, dict] = {
        "N1": {"type": "semantic", "requirement": "root", "decomposition_only": True,
               "requires": ["N2"]},
        "N2": {"type": "semantic", "requirement": "group", "requires": ["N3", "N4"]},
        "N3": {"type": "semantic", "requirement": "assigned", "requires": ["N5"]},
        "N4": {"type": "semantic", "requirement": "deeper branch", "requires": ["N9"]},
        "N9": {"type": "semantic", "requirement": "deepest", "requires": ["N6"]},
        "N5": owned,
        "N6": lower or {"type": "create", "path": "deep.txt", "content": "deep\n"},
    }
    if peer:
        # Depth-2 peer semantic node: its terminal has frontier 2 == boundary
        # depth, so it is same-frontier and must stay invisible.
        nodes["N7"] = {"type": "semantic", "requirement": "peer", "requires": ["N8"]}
        nodes["N8"] = peer_owned or {"type": "create", "path": "peer.txt", "content": "peer\n"}
        nodes["N2"]["requires"].append("N7")
    if shallow:
        # Terminal directly under N2: frontier 1 < boundary depth, shallower.
        nodes["N10"] = {"type": "create", "path": "shallow.txt", "content": "shallow\n"}
        nodes["N2"]["requires"].append("N10")
    return {"root": "N1", "nodes": nodes, "slug": slug}


def _workspace(tmp_path: Path, slug: str, dag: dict, files: dict[str, str]) -> Path:
    root = tmp_path / "workspace"
    root.mkdir(parents=True)
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    _write_bundle(root, slug, dag)
    return root


def _only(ranges: list[dict]) -> dict:
    assert len(ranges) == 1, ranges
    return ranges[0]


FOUR = "one\ntwo\nthree\nfour\n"


def _edit_line(path: str, line_no: int, old: str, new: str) -> dict:
    return {
        "type": "edit",
        "path": path,
        "patch": (
            f"--- a/{path}\n+++ b/{path}\n@@ -{line_no},1 +{line_no},1 @@\n-{old}\n+{new}\n"
        ),
    }


# --- inclusion / exclusion -------------------------------------------------


def test_fixture_graphs_respect_the_exclusive_terminal_rule():
    for dag in (
        _dag(owned=_edit_line("source.txt", 2, "two", "TWO")),
        _dag(owned={"type": "create", "path": "owned.txt", "content": "own\n"}, peer=True),
        _dag(owned={"type": "remove", "path": "source.txt"}, shallow=True),
    ):
        assert direct_terminal_errors(dag) == []


def test_untouched_live_file_reports_single_live_range(tmp_path):
    root = _workspace(tmp_path, "self", _dag(owned=_edit_line("source.txt", 2, "beta", "BETA")),
                      {"source.txt": "alpha\nbeta\n", "plain.txt": "p\nq\n"})
    live = dag_read("self", "N3", "plain.txt", workspace_root=root)
    assert live["present"] is True
    assert live["content"] == "p\nq\n"
    assert live["provenance"] == [{"lines": [1, 2], "node_ids": [], "relation": "live"}]


def test_accepted_lower_edit_is_attributed_to_the_lower_node(tmp_path):
    lower = _edit_line("source.txt", 2, "two", "TWO")
    root = _workspace(tmp_path, "self", _dag(owned=_edit_line("source.txt", 4, "four", "FOUR"),
                                             lower=lower),
                      {"source.txt": FOUR})
    read = dag_read("self", "N3", "source.txt", workspace_root=root)
    assert read["content"] == "one\nTWO\nthree\nFOUR\n"
    relations = {(r["relation"], tuple(r["lines"])): r["node_ids"] for r in read["provenance"]}
    assert relations[("accepted_lower", (2, 2))] == ["N6"]
    assert relations[("owned", (4, 4))] == ["N5"]


def test_accepted_lower_create_is_visible(tmp_path):
    lower = {"type": "create", "path": "created.txt", "content": "made\n"}
    root = _workspace(tmp_path, "self", _dag(owned=_edit_line("source.txt", 1, "a", "A"),
                                             lower=lower),
                      {"source.txt": "a\n"})
    read = dag_read("self", "N3", "created.txt", workspace_root=root)
    assert read["present"] is True
    assert read["content"] == "made\n"
    assert _only(read["provenance"]) == {
        "lines": [1, 1], "node_ids": ["N6"], "relation": "accepted_lower",
    }


def test_owned_edit_is_attributed_without_peer_or_lower(tmp_path):
    owned = _edit_line("source.txt", 2, "two", "TWO")
    root = _workspace(tmp_path, "self", _dag(owned=owned), {"source.txt": FOUR})
    read = dag_read("self", "N3", "source.txt", workspace_root=root)
    assert read["content"] == "one\nTWO\nthree\nfour\n"
    assert _only(read["provenance"]) == {
        "lines": [2, 2], "node_ids": ["N5"], "relation": "owned",
    }


def test_owned_create_is_visible(tmp_path):
    owned = {"type": "create", "path": "owned.txt", "content": "own\n"}
    root = _workspace(tmp_path, "self", _dag(owned=owned), {})
    read = dag_read("self", "N3", "owned.txt", workspace_root=root)
    assert read["present"] is True
    assert read["content"] == "own\n"
    assert _only(read["provenance"]) == {
        "lines": [1, 1], "node_ids": ["N5"], "relation": "owned",
    }


def test_owned_remove_reports_removal_provenance(tmp_path):
    owned = {"type": "remove", "path": "source.txt"}
    root = _workspace(tmp_path, "self", _dag(owned=owned), {"source.txt": "gone\n"})
    read = dag_read("self", "N3", "source.txt", workspace_root=root)
    assert read["present"] is False
    assert read["content"] is None
    assert _only(read["provenance"]) == {
        "lines": [], "node_ids": ["N5"], "relation": "owned",
    }


def test_accepted_lower_remove_reports_removal_provenance(tmp_path):
    lower = {"type": "remove", "path": "source.txt"}
    root = _workspace(tmp_path, "self",
                      _dag(owned={"type": "create", "path": "owned.txt", "content": "own\n"},
                           lower=lower),
                      {"source.txt": "gone\n"})
    read = dag_read("self", "N3", "source.txt", workspace_root=root)
    assert read["present"] is False
    assert read["content"] is None
    assert _only(read["provenance"]) == {
        "lines": [], "node_ids": ["N6"], "relation": "accepted_lower",
    }


def test_owned_move_moves_both_provenances(tmp_path):
    owned = {"type": "move", "from_path": "source.txt", "to_path": "moved.txt"}
    root = _workspace(tmp_path, "self", _dag(owned=owned), {"source.txt": "moved body\n"})
    source = dag_read("self", "N3", "source.txt", workspace_root=root)
    assert source["present"] is False
    assert _only(source["provenance"]) == {
        "lines": [], "node_ids": ["N5"], "relation": "owned",
    }
    destination = dag_read("self", "N3", "moved.txt", workspace_root=root)
    assert destination["present"] is True
    assert destination["content"] == "moved body\n"
    assert _only(destination["provenance"])["relation"] == "owned"
    assert _only(destination["provenance"])["node_ids"] == ["N5"]


def test_owned_and_accepted_lower_compose_in_one_file(tmp_path):
    lower = _edit_line("source.txt", 2, "two", "TWO")
    owned = _edit_line("source.txt", 4, "four", "FOUR")
    root = _workspace(tmp_path, "self", _dag(owned=owned, lower=lower), {"source.txt": FOUR})
    read = dag_read("self", "N3", "source.txt", workspace_root=root)
    assert read["content"] == "one\nTWO\nthree\nFOUR\n"
    relations = {(r["relation"], tuple(r["lines"])): r["node_ids"] for r in read["provenance"]}
    assert relations[("accepted_lower", (2, 2))] == ["N6"]
    assert relations[("owned", (4, 4))] == ["N5"]


def test_same_frontier_peer_is_excluded(tmp_path):
    root = _workspace(tmp_path, "self", _dag(owned=_edit_line("source.txt", 1, "a", "A"),
                                             peer=True),
                      {"source.txt": "a\n"})
    assert dag_read("self", "N3", "peer.txt", workspace_root=root)["present"] is False


def test_shallower_work_is_excluded(tmp_path):
    root = _workspace(tmp_path, "self", _dag(owned=_edit_line("source.txt", 1, "a", "A"),
                                             shallow=True),
                      {"source.txt": "a\n"})
    assert dag_read("self", "N3", "shallow.txt", workspace_root=root)["present"] is False


def test_unowned_sibling_proposal_is_excluded(tmp_path):
    """A peer's edit to the same path must not leak into the self view."""
    peer_owned = _edit_line("source.txt", 4, "four", "PEER")
    root = _workspace(tmp_path, "self", _dag(owned=_edit_line("source.txt", 2, "two", "TWO"),
                                             peer=True, peer_owned=peer_owned),
                      {"source.txt": FOUR})
    read = dag_read("self", "N3", "source.txt", workspace_root=root)
    assert read["content"] == "one\nTWO\nthree\nfour\n"
    assert _only(read["provenance"]) == {
        "lines": [2, 2], "node_ids": ["N5"], "relation": "owned",
    }


# --- range clipping --------------------------------------------------------


def test_line_range_read_clips_provenance(tmp_path):
    owned = _edit_line("source.txt", 2, "two", "TWO")
    root = _workspace(tmp_path, "self", _dag(owned=owned), {"source.txt": FOUR})
    head = dag_read("self", "N3", "source.txt", 1, 2, workspace_root=root)
    assert head["content"] == "one\nTWO\n"
    assert _only(head["provenance"]) == {
        "lines": [2, 2], "node_ids": ["N5"], "relation": "owned",
    }
    tail = dag_read("self", "N3", "source.txt", 3, 4, workspace_root=root)
    assert tail["content"] == "three\nfour\n"
    assert _only(tail["provenance"]) == {
        "lines": [3, 4], "node_ids": [], "relation": "live",
    }


# --- failure and isolation -------------------------------------------------


def test_malformed_deeper_work_still_reports_projection_failed(tmp_path):
    broken = {"type": "edit", "path": "source.txt", "patch": "not a diff"}
    root = _workspace(tmp_path, "self", _dag(owned=_edit_line("source.txt", 2, "two", "TWO"),
                                             lower=broken),
                      {"source.txt": FOUR})
    read = dag_read("self", "N3", "source.txt", workspace_root=root)
    assert read["error"] == "projection_failed"
    assert read["nodes"] == ["N6"]


def test_base_and_self_views_stay_separate(tmp_path):
    owned = _edit_line("source.txt", 2, "two", "TWO")
    lower = _edit_line("source.txt", 1, "one", "ONE")
    root = _workspace(tmp_path, "self", _dag(owned=owned, lower=lower), {"source.txt": FOUR})

    base, base_error = projected_source(root, "self", "N3")
    self_view, self_error = projected_self_source(root, "self", "N3")
    assert base_error is None and self_error is None
    assert base is not None and self_view is not None
    # BASE excludes the boundary's own work but keeps strictly-lower work.
    assert base.content("source.txt") == "ONE\ntwo\nthree\nfour\n"
    # SELF adds the boundary's own persisted work on top of BASE.
    assert self_view.content("source.txt") == "ONE\nTWO\nthree\nfour\n"
