"""Frontier-bounded Change DAG authoring-context preview.

Whole-DAG preview answers "what does the currently specified DAG eventually do?"
and stays available for preflight, review, and global inspection. The combined
``dag_preview(slug, path=..., node_id=<semantic node>)`` form answers a different
question: "what effective content may an author working on this semantic boundary
legitimately use as accepted prior context for this path?" That view is bounded to
live source plus accepted work strictly *deeper* on the construction frontier --
same-frontier peer proposals, the boundary node's own proposal, and
shallower/future work are excluded. Construction depth is an authoring boundary,
never the run-barrier execution phase, and nothing is written or executed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers.change_dag_ops_views import preview  # noqa: E402


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def dag_with(nodes: dict, root: str = "N1", slug: str = "demo") -> dict:
    return {"slug": slug, "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def semantic(requirement: str, requires=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if requires is not None:
        node["requires"] = requires
    return node


def edit(path: str, patch_text: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch_text}


def create(path: str, content: str) -> dict:
    return {"type": "create", "path": path, "content": content}


def remove(path: str) -> dict:
    return {"type": "remove", "path": path}


def move(from_path: str, to_path: str, overwrite: bool = False) -> dict:
    return {"type": "move", "from_path": from_path, "to_path": to_path, "overwrite": overwrite}


def run(command: list[str]) -> dict:
    return {"type": "run", "command": command}


def patch(path: str, old: str, new: str, line: int = 1) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n"


def insert_after(path: str, line: int, context: str, added: str) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -{line},1 +{line},2 @@\n {context}\n+{added}\n"


def make_workspace(tmp_path: Path, files: dict[str, str]) -> Path:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    for rel, content in files.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return workspace


def write_bundle(root: Path, slug: str, dag: dict, state: dict | None = None) -> None:
    bundle = root / "artifacts/change-dags/pending" / slug
    bundle.mkdir(parents=True)
    (bundle / "DAG.json").write_text(json.dumps(dag))
    (bundle / "EXECUTION_STATE.json").write_text(json.dumps(state or {}))
    (bundle / "WORK_LOG.jsonl").write_text("")


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    }


def payload(workspace: Path, *args, **kwargs) -> dict:
    return json.loads(preview(workspace, *args, **kwargs)["output"])


# ---------------------------------------------------------------------------
# 1. same frontier -> same base, independent of peer completion / node id order
# ---------------------------------------------------------------------------
def test_same_frontier_peer_edit_is_excluded_from_authoring_context(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "a\nb\nc\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N10", "N11"]),
            "N10": semantic("peer-a", ["N20"]),
            "N20": edit("f.txt", patch("f.txt", "a", "A")),
            "N11": semantic("peer-b", ["N21"]),
            "N21": edit("f.txt", patch("f.txt", "c", "C", line=3)),
        }
    )
    write_bundle(workspace, "demo", dag)

    peer_b = payload(workspace, "demo", path="f.txt", node_id="N11")
    assert peer_b["mode"] == "authoring_context"
    assert peer_b["boundary_depth"] == 2
    assert peer_b["effective_source"] == "a\nb\nc\n"
    assert peer_b["contributing_nodes"] == []

    # Swapping which peer owns which edit (and its insertion order) must not
    # change the base the other peer sees.
    swapped = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N10", "N11"]),
            "N10": semantic("peer-b", ["N20"]),
            "N20": edit("f.txt", patch("f.txt", "c", "C", line=3)),
            "N11": semantic("peer-a", ["N21"]),
            "N21": edit("f.txt", patch("f.txt", "a", "A")),
        }
    )
    write_bundle(workspace, "swap", swapped)
    peer_b_swapped = payload(workspace, "swap", path="f.txt", node_id="N10")
    assert peer_b_swapped["effective_source"] == peer_b["effective_source"]
    assert peer_b_swapped["contributing_nodes"] == []


# ---------------------------------------------------------------------------
# 2. deeper accepted work is visible to a higher authoring boundary
# ---------------------------------------------------------------------------
def test_higher_authoring_consumes_deeper_accepted_work(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "a\nb\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("top", ["N5"]),
            "N5": semantic("lower", ["N10"]),
            "N10": edit("f.txt", patch("f.txt", "a", "b")),
        }
    )
    write_bundle(workspace, "demo", dag)

    higher = payload(workspace, "demo", path="f.txt", node_id="N2")
    assert higher["boundary_depth"] == 1
    assert higher["effective_source"] == "b\nb\n"
    assert higher["contributing_nodes"] == ["N10"]

    # The construction layer that owns N10 sees only its own frontier: not itself.
    own = payload(workspace, "demo", path="f.txt", node_id="N5")
    assert own["boundary_depth"] == 2
    assert own["effective_source"] == "a\nb\n"
    assert own["contributing_nodes"] == []


# ---------------------------------------------------------------------------
# 3. same-frontier insertion must not shift a peer's authoring base
# ---------------------------------------------------------------------------
def test_same_frontier_insertion_does_not_shift_peer_base(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "head\ntail\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N10", "N11"]),
            "N10": semantic("inserter", ["N20"]),
            "N20": edit("f.txt", insert_after("f.txt", 1, "head", "inserted")),
            "N11": semantic("author", ["N21"]),
            "N21": edit("f.txt", patch("f.txt", "tail", "TAIL", line=2)),
        }
    )
    write_bundle(workspace, "demo", dag)

    author = payload(workspace, "demo", path="f.txt", node_id="N11")
    assert author["effective_source"] == "head\ntail\n"
    assert author["contributing_nodes"] == []


# ---------------------------------------------------------------------------
# 4. shallower/future work never contaminates a deeper authoring context
# ---------------------------------------------------------------------------
def test_shallower_future_work_is_excluded(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "a\nb\nc\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("a", ["N3"]),
            "N3": semantic("b", ["N4", "N14"]),
            "N4": semantic("boundary", ["N10"]),
            "N14": edit("f.txt", patch("f.txt", "a", "SHALLOW")),  # frontier 2
            "N10": edit("f.txt", patch("f.txt", "c", "C", line=3)),  # frontier 3 (own)
        }
    )
    write_bundle(workspace, "demo", dag)

    boundary = payload(workspace, "demo", path="f.txt", node_id="N4")
    assert boundary["boundary_depth"] == 3
    assert boundary["effective_source"] == "a\nb\nc\n"
    assert boundary["contributing_nodes"] == []
    assert boundary["excluded_later_work"] == {"same_frontier_nodes": 1, "shallower_nodes": 1}


# ---------------------------------------------------------------------------
# 5. lower create / 6. move / 7. remove are accepted lower context
# ---------------------------------------------------------------------------
def test_lower_create_is_visible_to_higher_authoring(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"keep.txt": "k\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("boundary", ["N5"]),
            "N5": semantic("lower", ["N10"]),
            "N10": create("new.txt", "hello\n"),
        }
    )
    write_bundle(workspace, "demo", dag)

    boundary = payload(workspace, "demo", path="new.txt", node_id="N2")
    assert boundary["effective_source"] == "hello\n"
    assert boundary["live_present"] is False
    assert boundary["live_source"] is None
    assert [entry["op"] for entry in boundary["creates"]] == ["create"]
    assert boundary["contributing_nodes"] == ["N10"]


def test_lower_move_is_visible_to_higher_authoring(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"old.txt": "x\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("boundary", ["N5"]),
            "N5": semantic("lower", ["N10"]),
            "N10": move("old.txt", "new.txt"),
        }
    )
    write_bundle(workspace, "demo", dag)

    destination = payload(workspace, "demo", path="new.txt", node_id="N2")
    assert destination["effective_source"] == "x\n"
    assert [entry["op"] for entry in destination["moves"]] == ["move"]

    source = payload(workspace, "demo", path="old.txt", node_id="N2")
    assert source["effective_source"] is None


def test_lower_remove_makes_path_absent_for_higher_authoring(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"dead.txt": "y\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("boundary", ["N5"]),
            "N5": semantic("lower", ["N10"]),
            "N10": remove("dead.txt"),
        }
    )
    write_bundle(workspace, "demo", dag)

    boundary = payload(workspace, "demo", path="dead.txt", node_id="N2")
    assert boundary["live_source"] == "y\n"
    assert boundary["effective_source"] is None
    assert [entry["op"] for entry in boundary["removes"]] == ["remove"]


# ---------------------------------------------------------------------------
# 8. convergence: a shared deeper node contributes once to both branches
# ---------------------------------------------------------------------------
def test_shared_deeper_descendant_is_visible_to_both_higher_branches(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "a\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("top", ["N3", "N4"]),
            "N3": semantic("branch-a", ["N5"]),
            "N4": semantic("branch-b", ["N5"]),
            "N5": semantic("shared", ["N10"]),
            "N10": edit("f.txt", patch("f.txt", "a", "b")),
        }
    )
    write_bundle(workspace, "demo", dag)

    branch_a = payload(workspace, "demo", path="f.txt", node_id="N3")
    branch_b = payload(workspace, "demo", path="f.txt", node_id="N4")
    assert branch_a["effective_source"] == "b\n"
    assert branch_b["effective_source"] == "b\n"
    assert branch_a["contributing_nodes"] == ["N10"]
    assert branch_b["contributing_nodes"] == ["N10"]


# ---------------------------------------------------------------------------
# 9 + 10. whole-DAG inspection survives and intentionally differs
# ---------------------------------------------------------------------------
def _layered_dag() -> dict:
    """deeper (frontier 4, accepted) + two frontier-3 peers + shallower frontier-2."""
    return dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("a", ["N3"]),
            "N3": semantic("b", ["N4", "N12", "N14"]),
            "N4": semantic("boundary", ["N10", "N5"]),
            "N10": edit("f.txt", patch("f.txt", "c", "C", line=3)),  # own, frontier 3
            "N5": semantic("deep", ["N20"]),
            "N20": edit("f.txt", patch("f.txt", "d", "D", line=4)),  # frontier 4
            "N12": semantic("peer", ["N13"]),
            "N13": edit("f.txt", patch("f.txt", "b", "B", line=2)),  # frontier 3
            "N14": edit("f.txt", patch("f.txt", "a", "A")),  # shallower, frontier 2
        }
    )


def test_whole_dag_view_still_shows_eventual_transformation(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "a\nb\nc\nd\n"})
    write_bundle(workspace, "demo", _layered_dag())

    whole = payload(workspace, "demo")
    assert whole["mode"] == "whole_dag"
    assert whole["ops"][0]["applied"] == "A\nB\nC\nD\n"

    path_only = payload(workspace, "demo", path="f.txt")
    assert path_only["mode"] == "path"
    assert path_only["ops"][0]["applied"] == "A\nB\nC\nD\n"


def test_authoring_view_and_whole_dag_view_differ(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "a\nb\nc\nd\n"})
    write_bundle(workspace, "demo", _layered_dag())

    authoring = payload(workspace, "demo", path="f.txt", node_id="N4")
    assert authoring["mode"] == "authoring_context"
    assert authoring["boundary_depth"] == 3
    # accepted deeper work only: the frontier-4 edit lands, nothing else does.
    assert authoring["effective_source"] == "a\nb\nc\nD\n"
    assert authoring["contributing_nodes"] == ["N20"]
    assert authoring["excluded_later_work"] == {"same_frontier_nodes": 2, "shallower_nodes": 1}
    # later work exists in the DAG but its content is not leaked into the view
    assert "C" not in authoring["effective_source"]
    assert "B" not in authoring["effective_source"]

    whole = payload(workspace, "demo")
    assert whole["ops"][0]["applied"] == "A\nB\nC\nD\n"


# ---------------------------------------------------------------------------
# 11 + 12. no repository writes, no command execution
# ---------------------------------------------------------------------------
def test_authoring_preview_never_writes_or_runs(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "a\nb\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("boundary", ["N5"]),
            "N5": semantic("lower", ["N6", "N10"]),
            "N6": run(["python3", "-c", "import pathlib;pathlib.Path('SIDE_EFFECT').write_text('x')"]),
            "N10": edit("f.txt", patch("f.txt", "a", "b")),
        }
    )
    write_bundle(workspace, "demo", dag)
    before = snapshot(workspace)

    result = preview(workspace, "demo", path="f.txt", node_id="N2")
    body = json.loads(result["output"])
    assert body["effective_source"] == "b\nb\n"
    # run nodes are neither mechanical context nor executed
    assert all(entry["op"] != "run" for entry in body["ops"])
    assert not (workspace / "SIDE_EFFECT").exists()
    assert "__pycache__" not in {part for path in workspace.rglob("*") for part in path.parts}
    assert snapshot(workspace) == before


# ---------------------------------------------------------------------------
# node requirement: reject non-semantic / unknown boundaries
# ---------------------------------------------------------------------------
def test_authoring_preview_rejects_non_semantic_boundary(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "a\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N10"]),
            "N10": edit("f.txt", patch("f.txt", "a", "b")),
        }
    )
    write_bundle(workspace, "demo", dag)

    mechanical = preview(workspace, "demo", path="f.txt", node_id="N10")
    assert mechanical["error"] == "invalid_boundary_node"

    unknown = preview(workspace, "demo", path="f.txt", node_id="N999")
    assert unknown["error"] == "unknown_node"


# ---------------------------------------------------------------------------
# conflicts that prevent a deterministic lower context are surfaced
# ---------------------------------------------------------------------------
def test_conflicting_deeper_peers_are_reported(tmp_path: Path):
    workspace = make_workspace(tmp_path, {"f.txt": "a\nb\n"})
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("boundary", ["N5"]),
            "N5": semantic("lower", ["N20", "N21"]),
            "N20": edit("f.txt", patch("f.txt", "a", "X")),
            "N21": edit("f.txt", patch("f.txt", "a", "Y")),
        }
    )
    write_bundle(workspace, "demo", dag)

    boundary = payload(workspace, "demo", path="f.txt", node_id="N2")
    assert boundary["conflicts"], "expected a deterministic-context conflict"
    assert boundary["conflicts"][0]["reason"].startswith("context_conflict:")
    assert set(boundary["conflicts"][0]["nodes"]) == {"N20", "N21"}
