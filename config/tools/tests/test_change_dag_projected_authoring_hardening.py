"""Regression coverage for the hardened projected authoring tools.

Covers the review findings on the terminal mutation APIs and the DAG-lensed
inspection tools:

* update paths obey the same terminal-authorability contract as adds, so
  create/remove/move updates are validated against the semantic owner's accepted
  base (BASE) instead of only structural DAG validation;
* an edit's stored patch can never diverge from its node path, and retargeting
  is fresh intent rather than transplanting the old file's patch;
* unavailable-base failures carry candidate producer IDs without exposing
  producer content;
* the public tool descriptions distinguish BASE from the SELF view;
* provenance describes the whole returned window, not only non-live stretches;
* a broad grep/search fails visibly when applicable projected work cannot be
  reproduced, while same-frontier peers never poison the call;
* grep/search reconcile live truth with projected truth per affected path.
"""
from __future__ import annotations

import json
from pathlib import Path

from common.helpers import change_dag
from common.helpers.change_dag_ops_create import create_dag
from common.helpers.change_dag_ops_mutation import add_work, update_node
from common.helpers.change_dag_patch import apply_patches, parse_unified_diff
from common.tools.dag_grep import dag_grep
from common.tools.dag_read import dag_read
from common.tools.dag_search import dag_search

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parents[1]
SLUG = "hardening"
ANCHOR = "a" * 40


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    return root


def _seed(root: Path, name: str, text: str) -> None:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _two_level(root: Path, slug: str = SLUG) -> None:
    """root -> impl, the smallest graph that can host terminal work."""
    result = create_dag(
        root,
        slug,
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["impl"]},
                "impl": {"requirement": "implementation"},
            },
        },
    )
    assert result.get("error") is None, result


def _split(root: Path, slug: str = SLUG) -> None:
    """root -> [left, right]: two same-frontier semantic branches."""
    result = create_dag(
        root,
        slug,
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["left", "right"]},
                "left": {"requirement": "left branch"},
                "right": {"requirement": "right branch"},
            },
        },
    )
    assert result.get("error") is None, result


def _nodes(root: Path, slug: str = SLUG) -> dict:
    dag, _path, _location = change_dag.read_dag(root, slug)
    return change_dag.node_map(dag)


def _dag_text(root: Path, slug: str = SLUG) -> str:
    return change_dag.dag_json_path(root, slug).read_text(encoding="utf-8")


def _edit(path: str, line_no: int, old: str, new: str) -> dict:
    return {
        "type": "edit",
        "path": path,
        "patch": f"--- a/{path}\n+++ b/{path}\n@@ -{line_no},1 +{line_no},1 @@\n-{old}\n+{new}\n",
    }


def _blueprint(**fields):
    """A pending bundle written without going through the mutation API.

    Structural validation is deliberately bypassed so a malformed persisted
    patch can be planted and the tooling's failure reporting exercised.
    """
    root = fields.pop("root")
    slug = fields.pop("slug", SLUG)
    files = fields.pop("files", {})
    nodes = fields.pop("nodes")
    for name, text in files.items():
        _seed(root, name, text)
    dag = {"slug": slug, "anchor_commit": ANCHOR, "root": "N1", "nodes": nodes}
    bundle = root / "artifacts" / "change-dags" / "pending" / slug
    bundle.mkdir(parents=True, exist_ok=True)
    change_dag.atomic_write_json(bundle / "DAG.json", dag)
    change_dag.atomic_write_json(bundle / "EXECUTION_STATE.json", {})
    (bundle / "WORK_LOG.jsonl").write_text("", encoding="utf-8")
    return root


def _corrupt_patch(root: Path, node_id: str, slug: str = SLUG, text: str = "not a diff") -> None:
    """Overwrite one node's persisted patch with malformed content."""
    dag, _path, _location = change_dag.read_dag(root, slug)
    dag["nodes"][node_id]["patch"] = text
    change_dag.atomic_write_json(change_dag.dag_json_path(root, slug), dag)


def _layered(
    root: Path,
    terminal: dict[str, dict],
    *,
    files: dict[str, str] | None = None,
    slug: str = SLUG,
) -> Path:
    """Boundary N3 (depth 2) over strictly-deeper work hosted at depth 4.

    ``terminal`` maps a host node id to one terminal node, so every host node
    owns exactly one exclusive terminal and the graph stays structurally valid.
    """
    nodes = {
        "N1": {"type": "semantic", "requirement": "root", "requires": ["N2"], "decomposition_only": True},
        "N2": {"type": "semantic", "requirement": "group", "requires": ["N3", "N4"]},
        "N3": {"type": "semantic", "requirement": "assigned"},
        "N4": {"type": "semantic", "requirement": "deeper", "requires": ["N5"]},
        "N5": {"type": "semantic", "requirement": "deepest", "requires": sorted(terminal)},
    }
    for host, node in terminal.items():
        nodes[host] = {
            "type": "semantic",
            "requirement": f"host {host}",
            "requires": [node["_id"]],
        }
        nodes[node["_id"]] = {key: value for key, value in node.items() if key != "_id"}
    return _blueprint(root=root, slug=slug, nodes=nodes, files=files or {})


# ---------------------------------------------------------------------------
# 1. update paths obey the terminal-authorability contract
# ---------------------------------------------------------------------------
def test_update_create_rejects_existing_target(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    assert add_work(root, SLUG, "create", ["N2"], path="fresh.txt", content="x\n").get("error") is None
    before = _dag_text(root)

    _seed(root, "taken.txt", "taken\n")
    rejected = update_node(root, SLUG, "N3", path="taken.txt")
    assert rejected["error"] == "create_target_exists"
    assert _dag_text(root) == before


def test_update_create_content_only_stays_legal(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    assert add_work(root, SLUG, "create", ["N2"], path="fresh.txt", content="x\n").get("error") is None
    assert update_node(root, SLUG, "N3", content="y\n").get("error") is None
    assert _nodes(root)["N3"]["content"] == "y\n"


def test_update_remove_rejects_absent_target(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    _seed(root, "gone.txt", "body\n")
    assert add_work(root, SLUG, "remove", ["N2"], path="gone.txt").get("error") is None
    before = _dag_text(root)

    rejected = update_node(root, SLUG, "N3", path="never.txt")
    assert rejected["error"] == "remove_target_unavailable"
    assert _dag_text(root) == before


def test_update_move_rejects_absent_source(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    _seed(root, "m.txt", "body\n")
    assert add_work(root, SLUG, "move", ["N2"], from_path="m.txt", to_path="n.txt").get("error") is None
    before = _dag_text(root)

    rejected = update_node(root, SLUG, "N3", from_path="never.txt")
    assert rejected["error"] == "move_source_unavailable"
    assert _dag_text(root) == before


def test_update_move_rejects_conflicting_destination(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    _seed(root, "m.txt", "body\n")
    assert add_work(root, SLUG, "move", ["N2"], from_path="m.txt", to_path="n.txt").get("error") is None
    _seed(root, "taken.txt", "taken\n")
    before = _dag_text(root)

    rejected = update_node(root, SLUG, "N3", to_path="taken.txt")
    assert rejected["error"] == "move_destination_conflict"
    assert _dag_text(root) == before

    # Changing only ``overwrite`` still revalidates the whole resulting move.
    assert update_node(root, SLUG, "N3", to_path="taken.txt", overwrite=True).get("error") is None


# ---------------------------------------------------------------------------
# 2. edit retargeting
# ---------------------------------------------------------------------------
def test_same_path_update_uses_the_existing_self_view(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    _seed(root, "f.txt", "one\ntwo\nthree\n")
    assert add_work(root, SLUG, "edit", ["N2"], path="f.txt",
                    replacements=[{"old": "two", "new": "TWO"}]).get("error") is None

    updated = update_node(root, SLUG, "N3", replacements=[{"old": "three", "new": "THREE"}])
    assert updated.get("error") is None
    node = _nodes(root)["N3"]
    assert node["path"] == "f.txt"
    # One consolidated BASE-relative patch reproduces both replacements.
    assert apply_patches("one\ntwo\nthree\n", parse_unified_diff(node["patch"]), path="f.txt") == \
        "one\nTWO\nTHREE\n"


def test_edit_path_change_requires_replacements(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    _seed(root, "a.txt", "alpha\n")
    _seed(root, "b.txt", "beta\n")
    assert add_work(root, SLUG, "edit", ["N2"], path="a.txt",
                    replacements=[{"old": "alpha", "new": "ALPHA"}]).get("error") is None
    before = _dag_text(root)

    rejected = update_node(root, SLUG, "N3", path="b.txt")
    assert rejected["error"] == "edit_path_change_requires_replacements"
    assert _dag_text(root) == before


def test_edit_retarget_uses_the_new_base_and_never_transplants(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    _seed(root, "a.txt", "alpha\n")
    _seed(root, "b.txt", "beta\n")
    assert add_work(root, SLUG, "edit", ["N2"], path="a.txt",
                    replacements=[{"old": "alpha", "new": "ALPHA"}]).get("error") is None

    retargeted = update_node(root, SLUG, "N3", path="b.txt",
                             replacements=[{"old": "beta", "new": "BETA"}])
    assert retargeted.get("error") is None
    node = _nodes(root)["N3"]
    assert node["path"] == "b.txt"
    # The regenerated patch targets the new file; the old file's patch is gone.
    assert "b.txt" in node["patch"]
    assert "a.txt" not in node["patch"] and "alpha" not in node["patch"]
    assert apply_patches("beta\n", parse_unified_diff(node["patch"]), path="b.txt") == "BETA\n"


def test_edit_retarget_to_missing_base_is_atomic(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    _seed(root, "a.txt", "alpha\n")
    assert add_work(root, SLUG, "edit", ["N2"], path="a.txt",
                    replacements=[{"old": "alpha", "new": "ALPHA"}]).get("error") is None
    before = _dag_text(root)

    rejected = update_node(root, SLUG, "N3", path="missing.txt",
                           replacements=[{"old": "x", "new": "y"}])
    assert rejected["error"] == "edit_base_unavailable"
    assert _dag_text(root) == before


def test_stored_patch_always_targets_the_node_path(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    _seed(root, "a.txt", "alpha\n")
    _seed(root, "b.txt", "beta\n")
    assert add_work(root, SLUG, "edit", ["N2"], path="a.txt",
                    replacements=[{"old": "alpha", "new": "ALPHA"}]).get("error") is None

    for node_id in ("N3",):
        node = _nodes(root)[node_id]
        assert node["path"] in node["patch"]

    assert update_node(root, SLUG, "N3", path="b.txt",
                       replacements=[{"old": "beta", "new": "BETA"}]).get("error") is None
    node = _nodes(root)["N3"]
    assert node["path"] in node["patch"]
    assert parse_unified_diff(node["patch"])[0].path == node["path"]


# ---------------------------------------------------------------------------
# 3. producer evidence
# ---------------------------------------------------------------------------
def test_same_frontier_peer_is_not_a_visible_base(tmp_path):
    root = _workspace(tmp_path)
    _split(root)
    # N4 is a create under the sibling branch N2, i.e. same frontier as N3.
    assert add_work(root, SLUG, "create", ["N2"], path="shared.txt",
                    content="SECRET_BODY\n").get("error") is None

    read = dag_read(SLUG, "N3", "shared.txt", workspace_root=root)
    assert read["present"] is False
    assert read["content"] is None

    rejected = add_work(root, SLUG, "edit", ["N3"], path="shared.txt",
                        replacements=[{"old": "SECRET_BODY", "new": "edited"}])
    assert rejected["error"] == "edit_base_unavailable"
    # The producer is named as diagnostic structure...
    assert rejected["candidate_producers"] == ["N4"]
    # ...and its content is never exposed.
    assert "SECRET_BODY" not in json.dumps(rejected)


def test_producer_evidence_is_absent_when_nothing_produces_the_path(tmp_path):
    root = _workspace(tmp_path)
    _two_level(root)
    rejected = add_work(root, SLUG, "edit", ["N2"], path="nobody.txt",
                        replacements=[{"old": "a", "new": "b"}])
    assert rejected["error"] == "edit_base_unavailable"
    assert "candidate_producers" not in rejected


# ---------------------------------------------------------------------------
# 4. public tool contracts
# ---------------------------------------------------------------------------
def test_plugin_descriptions_distinguish_base_from_self_view():
    text = (REPO_ROOT / "config" / "plugins" / "tools.ts").read_text(encoding="utf-8")

    # The SELF view includes the boundary node's own persisted work...
    assert text.count("boundary node's own persisted terminal work") >= 3
    assert text.count("SELF view") >= 3
    # ...and peers remain excluded.
    assert "Same-frontier peers" in text
    assert "stay excluded" in text
    # The narrower BASE lens is named as internal validation input only.
    assert "used internally to validate a new mutation" in text
    # The previously contradictory wording is gone.
    assert "the boundary node's own work, and shallower/future work" not in text
    assert "Excludes same-frontier peers, the boundary node's own work" not in text


# ---------------------------------------------------------------------------
# 5. provenance completeness
# ---------------------------------------------------------------------------
def test_provenance_covers_a_mixed_window_without_gaps(tmp_path):
    root = _workspace(tmp_path)
    _layered(
        root,
        {
            "N10": {**_edit("f.txt", 1, "one", "ONE"), "_id": "N6"},
            "N13": {"type": "create", "path": "new.txt", "content": "one fresh\n", "_id": "N11"},
        },
        files={"f.txt": "one\ntwo\nthree\n", "new.txt": "one fresh\n"},
    )
    # The boundary's own edit sits at the boundary depth, so only the deeper edit
    # is accepted-lower work while the boundary-authored one is owned.
    read = dag_read(SLUG, "N3", "f.txt", workspace_root=root)
    assert read["present"] is True

    ranges = read["provenance"]
    assert ranges, ranges
    # Complete, sorted, non-overlapping coverage of the returned window.
    assert ranges[0]["lines"][0] == 1
    assert ranges[-1]["lines"][1] == 3
    for left, right in zip(ranges, ranges[1:]):
        assert left["lines"][1] + 1 == right["lines"][0]
        assert left["lines"][1] >= left["lines"][0]
    assert {entry["relation"] for entry in ranges} <= {"live", "accepted_lower", "owned"}


def test_provenance_is_complete_for_a_purely_live_window(tmp_path):
    root = _workspace(tmp_path)
    _layered(root, {"N10": {**_edit("f.txt", 1, "one", "ONE"), "_id": "N6"}},
             files={"f.txt": "one\ntwo\nthree\n", "unrelated.txt": "body\n"})
    read = dag_read(SLUG, "N3", "unrelated.txt", workspace_root=root)
    assert read["provenance"] == [{"lines": [1, 1], "node_ids": [], "relation": "live"}]


def test_range_read_clips_provenance_to_the_window(tmp_path):
    root = _workspace(tmp_path)
    _layered(
        root,
        {
            "N10": {**_edit("f.txt", 1, "one", "ONE"), "_id": "N6"},
            "N13": {"type": "create", "path": "other.txt", "content": "x\n", "_id": "N11"},
        },
        files={"f.txt": "one\ntwo\nthree\n", "other.txt": "x\n"},
    )
    read = dag_read(SLUG, "N3", "f.txt", 2, 3, workspace_root=root)
    assert read["content"] == "two\nthree\n"
    assert read["provenance"] == [{"lines": [2, 3], "node_ids": [], "relation": "live"}]


# ---------------------------------------------------------------------------
# 6. broad search must fail closed on unreproducible applicable work
# ---------------------------------------------------------------------------
def test_broad_search_fails_visibly_on_unreproducible_lower_work(tmp_path):
    root = _workspace(tmp_path)
    _layered(root, {"N10": {**_edit("f.txt", 1, "one", "ONE"), "_id": "N6"}},
             files={"f.txt": "one\ntwo\nthree\n"})
    _corrupt_patch(root, "N6")

    grep = dag_grep(SLUG, "N3", "two", workspace_root=root)
    assert grep["error"] == "projection_failed"
    assert [entry["path"] for entry in grep["failures"]] == ["f.txt"]

    search = dag_search(SLUG, "N3", "two", workspace_root=root)
    assert search["error"] == "projection_failed"
    assert [entry["path"] for entry in search["failures"]] == ["f.txt"]

    # Path-scoped calls stay surgical and report the same failure.
    assert dag_grep(SLUG, "N3", "two", path="f.txt", workspace_root=root)["error"] == "projection_failed"


def test_broad_search_fails_visibly_on_unreproducible_owned_work(tmp_path):
    root = _workspace(tmp_path)
    _layered(root, {"N10": {**_edit("f.txt", 1, "one", "ONE"), "_id": "N6"}},
             files={"f.txt": "one\ntwo\nthree\n"})
    _corrupt_patch(root, "N6")

    # Corrupt the boundary's own work as well and confirm the failure is still
    # reported rather than falling back to live content.
    owned = _edit("g.txt", 1, "one", "ONE")
    _blueprint(
        root=root,
        slug="owned",
        nodes={
            "N1": {"type": "semantic", "requirement": "root", "requires": ["N2"], "decomposition_only": True},
            "N2": {"type": "semantic", "requirement": "assigned", "requires": ["N3"]},
            "N3": {**_edit("g.txt", 1, "one", "OWNED"), "patch": "not a diff"},
        },
        files={"g.txt": "one\ntwo\n"},
    )
    assert owned["path"] == "g.txt"
    result = dag_search("owned", "N2", "one", workspace_root=root)
    assert result["error"] == "projection_failed"
    assert [entry["path"] for entry in result["failures"]] == ["g.txt"]


def test_same_frontier_peer_conflict_does_not_poison_search(tmp_path):
    root = _workspace(tmp_path)
    _split(root)
    _seed(root, "g.txt", "one\ntwo\n")
    assert add_work(root, SLUG, "edit", ["N2"], path="g.txt",
                    replacements=[{"old": "one", "new": "ONE"}]).get("error") is None
    # N4 is a same-frontier peer of the N3 boundary, so its broken work is
    # outside N3's SELF view and must not poison N3's search.
    _corrupt_patch(root, "N4")

    grep = dag_grep(SLUG, "N3", "one", workspace_root=root)
    assert "error" not in grep, grep
    assert grep["matches"] == [{"path": "g.txt", "line": 1}]
    assert dag_search(SLUG, "N3", "one", workspace_root=root).get("error") is None


# ---------------------------------------------------------------------------
# 7. grep/search reconcile live truth with projected truth
# ---------------------------------------------------------------------------
def _reconciliation(root: Path) -> Path:
    return _layered(
        root,
        {
            "N10": {**_edit("f.txt", 1, "one", "XX"), "_id": "N6"},
            "N11": {"type": "create", "path": "new.txt", "content": "one fresh\n", "_id": "N7"},
            "N12": {"type": "remove", "path": "old.txt", "_id": "N8"},
            "N13": {"type": "move", "from_path": "src.txt", "to_path": "dst.txt", "_id": "N9"},
        },
        files={
            "f.txt": "one\ntwo\nthree\n",
            "old.txt": "one obsolete\n",
            "src.txt": "one moved\n",
            "extra.txt": "one unrelated\n",
        },
    )


def test_grep_replaces_live_truth_per_affected_path(tmp_path):
    root = _reconciliation(_workspace(tmp_path))
    result = dag_grep(SLUG, "N3", "one", workspace_root=root)
    assert "error" not in result, result
    # f.txt's live match is gone (edited to "XX"); old.txt is removed; src.txt
    # moved to dst.txt; the created file and the move destination appear; the
    # unaffected live match survives.
    assert result["matches"] == [
        {"path": "dst.txt", "line": 1},
        {"path": "extra.txt", "line": 1},
        {"path": "new.txt", "line": 1},
    ]


def test_grep_sees_projected_edit_content(tmp_path):
    root = _reconciliation(_workspace(tmp_path))
    result = dag_grep(SLUG, "N3", "XX", workspace_root=root)
    assert result["matches"] == [{"path": "f.txt", "line": 1}]


def test_search_merges_live_and_projected_candidates(tmp_path):
    root = _reconciliation(_workspace(tmp_path))
    ranked = dag_search(SLUG, "N3", "one", workspace_root=root)
    assert "error" not in ranked, ranked
    paths = {entry["path"] for entry in ranked["results"]}
    assert paths == {"dst.txt", "extra.txt", "new.txt"}

    # The limit is applied after the authoritative merge, never to a live top-N
    # computed before projected candidates were added.
    limited = dag_search(SLUG, "N3", "one", limit=1, workspace_root=root)
    assert len(limited["results"]) == 1
    assert limited["results"][0]["path"] == ranked["results"][0]["path"]


def test_search_ignores_a_projected_removal(tmp_path):
    root = _reconciliation(_workspace(tmp_path))
    result = dag_search(SLUG, "N3", "obsolete", workspace_root=root)
    assert result["results"] == []


def test_created_path_is_visible_to_path_scoped_calls(tmp_path):
    root = _reconciliation(_workspace(tmp_path))
    read = dag_read(SLUG, "N3", "new.txt", workspace_root=root)
    assert read["present"] is True
    assert read["content"] == "one fresh\n"
    assert read["provenance"] == [{"lines": [1, 1], "node_ids": ["N7"], "relation": "accepted_lower"}]
