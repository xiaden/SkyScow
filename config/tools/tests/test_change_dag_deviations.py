"""Regression tests for the audited Change DAG implementation deviations.

Covers: bounded context partitioning evidence, dag_preview compiled context,
real run barriers, live-drift-as-runtime-failure, FIFO queue safety, Work Log
compiled-operation evidence, inherited worktree evidence, ready-run
concurrency/exclusive semantics, and authoring mutation atomicity.
"""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag  # noqa: E402
from common.helpers import change_dag_control as control  # noqa: E402
from common.helpers.change_dag_ops_create import create_dag  # noqa: E402
from common.helpers.change_dag_ops_mutation import add_requirement  # noqa: E402
from common.helpers import change_dag_state as state_helper  # noqa: E402
from common.helpers.change_dag_compiler_lowering import compile_operations  # noqa: E402
from common.helpers.change_dag_compiler_phase import preflight  # noqa: E402
from common.tools import dag_executor  # noqa: E402
from common.tools.dag_executor import run_execution  # noqa: E402


# ---------------------------------------------------------------------------
# Builders / fixtures
# ---------------------------------------------------------------------------
def dag_with(nodes: dict, root: str = "N1", slug: str = "demo") -> dict:
    return {"slug": slug, "anchor_commit": "a" * 40, "root": root, "nodes": nodes}


def semantic(requirement: str = "r", requires=None) -> dict:
    node = {"type": "semantic", "requirement": requirement}
    if requires is not None:
        node["requires"] = requires
    return node


def edit(path: str, patch: str) -> dict:
    return {"type": "edit", "path": path, "patch": patch}


def run(command=None) -> dict:
    return {"type": "run", "command": command or ["pytest"]}


def make_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / ".keep").write_text("keep\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    return tmp_path


def write_bundle(root: Path, slug: str, dag: dict) -> None:
    bundle = root / "artifacts/change-dags/pending" / slug
    bundle.mkdir(parents=True)
    (bundle / "DAG.json").write_text(json.dumps(dag))
    (bundle / "EXECUTION_STATE.json").write_text("{}")
    (bundle / "WORK_LOG.jsonl").write_text("")


# ---------------------------------------------------------------------------
# dag_preview / compiled context recomposition
# ---------------------------------------------------------------------------
def test_edit_op_exposes_compiled_patch_and_applied_context(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("alpha\nbeta\n")
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1,1 +1,1 @@\n-alpha\n+ALPHA\n"
    dag = dag_with({"N1": semantic("root", ["N2"]), "N2": edit("f.txt", patch)})

    ops, conflicts, blocked = compile_operations(dag, {}, workspace)
    assert conflicts == [] and blocked == []
    op = ops[0]
    # A fresh bounded author context can read what the file will look like after
    # accepted lower work without materialising a projected worktree.
    assert op.patch_text and "-alpha" in op.patch_text
    assert op.applied == "ALPHA\nbeta\n"


def test_multiple_lower_edits_compose_in_applied_context(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "f.txt").write_text("l1\nl2\nl3\n")
    first = "--- a/f.txt\n+++ b/f.txt\n@@ -1,1 +1,2 @@\n l1\n+ins\n"
    # Same-frontier peers are authored against the common base: line 3, not the
    # shifted line 4.
    second = "--- a/f.txt\n+++ b/f.txt\n@@ -3,1 +3,1 @@\n-l3\n+l3b\n"
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("impl", ["N3", "N4"]),
            "N3": edit("f.txt", first),
            "N4": edit("f.txt", second),
        }
    )
    ops, _conflicts, _blocked = compile_operations(dag, {}, workspace)
    op = ops[0]
    assert op.applied == "l1\nins\nl2\nl3b\n"
    assert op.patch_text and "+ins" in op.patch_text and "+l3b" in op.patch_text


# ---------------------------------------------------------------------------
# Run barriers split execution
# ---------------------------------------------------------------------------
def _barrier_patch(name: str = "x.txt") -> str:
    return f"--- a/{name}\n+++ b/{name}\n@@ -1,1 +1,1 @@\n-a\n+b\n"


def test_mechanical_above_unsatisfied_run_barrier_is_deferred(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "x.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2"]),
            "N2": semantic("aggregate", ["N3", "N7"]),
            "N3": semantic("verified", ["N4"]),
            "N4": semantic("inner", ["N5"]),
            "N5": run(["pytest"]),
            "N7": edit("x.txt", _barrier_patch()),
        }
    )
    ops, _conflicts, blocked = compile_operations(dag, {}, workspace)
    assert {entry.node_id for entry in blocked} == {"N7"}
    assert all(op.path != "x.txt" for op in ops)

    # After the barrier run succeeds the upper work becomes applicable.
    ops2, _conflicts2, blocked2 = compile_operations(dag, {"N5": "satisfied"}, workspace)
    assert any(op.path == "x.txt" for op in ops2)
    assert all(entry.node_id != "N7" for entry in blocked2)

def test_unrelated_branch_mechanical_progresses_independently(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "u.txt").write_text("a\n")
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N6"]),
            "N2": semantic("withbarrier", ["N3"]),
            "N3": semantic("inner", ["N4"]),
            "N4": run(["pytest"]),
            "N6": semantic("other", ["N7"]),
            "N7": edit("u.txt", _barrier_patch("u.txt")),
        }
    )
    ops, _conflicts, blocked = compile_operations(dag, {}, workspace)
    assert all(entry.node_id != "N7" for entry in blocked)
    assert any(op.path == "u.txt" for op in ops)


# ---------------------------------------------------------------------------
# Live drift is a recoverable runtime failure, not an admission gate
# ---------------------------------------------------------------------------
def test_live_drift_patch_mismatch_fails_only_affected_node(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("a\n")
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1,1 +1,1 @@\n-a\n+b\n"
    dag = dag_with(
        {
            "N1": {**semantic("root", ["N2"]), "decomposition_only": True},
            "N2": semantic("implementation", ["N3"]),
            "N3": edit("f.txt", patch),
        },
        slug="drift",
    )
    write_bundle(root, "drift", dag)

    # The authored patch is applicable at admission time...
    assert preflight(dag, {}, root)["executable"] is True
    # ...then the live repository drifts before the node is reached.
    (root / "f.txt").write_text("c\n")

    run_execution(root, "drift")

    assert state_helper.read_state(root, "drift")["N3"] == "failed"
    # No checkpoint on a failed/incomplete DAG.
    log = subprocess.run(["git", "log", "--format=%s"], cwd=root, text=True, capture_output=True, check=True)
    assert "checkpoint drift" not in log.stdout


# ---------------------------------------------------------------------------
# FIFO queue mutation safety
# ---------------------------------------------------------------------------
def test_concurrent_queue_admissions_preserve_all_entries(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    slugs = [f"s{i}" for i in range(24)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda slug: control.enqueue(root, slug), slugs))
    entries = [entry["slug"] for entry in control.queue_list(root)]
    assert sorted(entries) == sorted(slugs)
    assert len(entries) == len(set(entries))


def test_duplicate_queue_admission_is_idempotent(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    control.enqueue(root, "a")
    control.enqueue(root, "a")
    assert [entry["slug"] for entry in control.queue_list(root)] == ["a"]


def test_queue_remove_preserves_other_entries(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    for slug in ("a", "b", "c"):
        control.enqueue(root, slug)
    assert control.queue_remove(root, "b") is True
    assert [entry["slug"] for entry in control.queue_list(root)] == ["a", "c"]
    assert control.dequeue_next(root)["slug"] == "a"
    assert [entry["slug"] for entry in control.queue_list(root)] == ["c"]


# ---------------------------------------------------------------------------
# Work Log preserves the concrete attempted operation
# ---------------------------------------------------------------------------
def test_work_log_edit_entry_records_compiled_patch(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("a\n")
    patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1,1 +1,1 @@\n-a\n+b\n"
    dag = dag_with(
        {"N1": semantic("root", ["N2"]), "N2": edit("f.txt", patch)},
        slug="wl",
    )
    write_bundle(root, "wl", dag)

    run_execution(root, "wl")

    entries = state_helper.read_work_log(root, "wl")
    edit_entries = [entry for entry in entries if entry.get("operation") == "edit"]
    assert edit_entries, "no edit Work Log entry recorded"
    assert edit_entries[-1].get("patch") and "-a" in edit_entries[-1]["patch"]
    # ``applied`` remains the existing boolean execution flag; the concrete
    # compiled operation is preserved separately under ``patch``.
    assert edit_entries[-1].get("applied") is True


def test_inherited_worktree_evidence_is_concrete(tmp_path: Path):
    root = make_repo(tmp_path)
    (root / ".keep").write_text("keep\nchanged\n")
    (root / "new.txt").write_text("untracked\n")

    evidence = control.capture_inherited_state(root)

    assert "keep" in evidence["diff"] and "changed" in evidence["diff"]
    assert "new.txt" in evidence["untracked_files"]
    assert evidence["diff_digest"]


# ---------------------------------------------------------------------------
# Ready-run concurrency and exclusive semantics
# ---------------------------------------------------------------------------
def test_independent_nonexclusive_runs_launch_together(tmp_path: Path, monkeypatch):
    root = make_repo(tmp_path)
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N5"]),
            "N2": semantic("a", ["N3"]),
            "N3": run(["pytest"]),
            "N5": semantic("b", ["N6"]),
            "N6": run(["tsc", "--noEmit"]),
        },
        slug="conc",
    )
    write_bundle(root, "conc", dag)

    events: list[tuple[str, object]] = []

    class _FakeProc:
        pass

    def fake_launch(command, workspace_root):
        events.append(("launch", tuple(command)))
        return _FakeProc(), 4242, None

    def fake_collect(process, pgid):
        events.append(("collect", pgid))
        return 0, "", "", None

    monkeypatch.setattr(dag_executor, "_launch_run", fake_launch)
    monkeypatch.setattr(dag_executor, "_collect_run", fake_collect)

    run_execution(root, "conc")
    # Both ready non-exclusive runs are launched before either is collected.
    assert [kind for kind, _ in events[:2]] == ["launch", "launch"]
    assert len(events) == 4


def test_exclusive_run_does_not_overlap_other_runs(tmp_path: Path, monkeypatch):
    root = make_repo(tmp_path)
    dag = dag_with(
        {
            "N1": semantic("root", ["N2", "N5"]),
            "N2": semantic("a", ["N3"]),
            "N3": {"type": "run", "command": ["tsc", "--noEmit"], "exclusive": True},
            "N5": semantic("b", ["N6"]),
            "N6": run(["pytest"]),
        },
        slug="excl",
    )
    write_bundle(root, "excl", dag)

    events: list[tuple[str, object]] = []

    class _FakeProc:
        pass

    def fake_launch(command, workspace_root):
        events.append(("launch", tuple(command)))
        return _FakeProc(), 4242, None

    def fake_collect(process, pgid):
        events.append(("collect", pgid))
        return 0, "", "", None

    monkeypatch.setattr(dag_executor, "_launch_run", fake_launch)
    monkeypatch.setattr(dag_executor, "_collect_run", fake_collect)

    run_execution(root, "excl")
    # The exclusive run launches alone (launch then collect), never beside another.
    assert events[0] == ("launch", ("tsc", "--noEmit"))
    assert events[1][0] == "collect"


# ---------------------------------------------------------------------------
# Authoring mutation atomicity
# ---------------------------------------------------------------------------
def test_concurrent_node_additions_get_distinct_ids(tmp_path: Path):
    root = make_repo(tmp_path)
    created = create_dag(
        root,
        "mut",
        {
            "root": "h",
            "nodes": {
                "h": {"requirement": "root", "requires": ["seed"]},
                "seed": {"requirement": "seed"},
            },
        },
    )
    assert "error" not in created
    seeded_ids = set(json.loads(created["output"])["node_ids_by_handle"].values())

    errors: list[dict] = []
    lock = __import__("threading").Lock()

    def add(index: int) -> None:
        result = add_requirement(root, "mut", f"req {index}", ["N1"])
        if "error" in result:
            with lock:
                errors.append(result)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(add, range(20)))

    assert not errors, errors
    dag, _path, _location = change_dag.read_dag(root, "mut")
    nodes = change_dag.node_map(dag)
    added = [node_id for node_id in nodes if node_id not in seeded_ids]
    assert len(added) == 20
    assert len(set(added)) == 20



# ---------------------------------------------------------------------------
# A7: QA is DAG-independent — contract prose guards
# ---------------------------------------------------------------------------
REPO_ROOT = TOOLS.parents[1]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_qa_contract_supports_non_dag_work():
    qa = _read("config/agents/qa-reviewer.md")
    assert "QA never requires a Change DAG to exist" in qa
    assert "routed to Change-DAG-Author to amend the DAG" not in qa
    assert "never reopen" in qa


def test_orchestration_never_reopens_completed_dag():
    orchestrate = _read("config/commands/ecc/orchestrate.md")
    assert "never route a DAG gap to a raw edit" not in orchestrate
    assert "A completed DAG is never amended" in orchestrate


def test_author_contract_owns_frontier_loop_and_worker_dispatch():
    author = _read("config/agents/change-dag-author.md")
    assert "change-dag-worker" in author
    assert "dag_decomposition_frontier" in author
    assert "fresh Change-DAG-Author invocation" not in author
    assert "one bounded invocation per frontier" not in author


def test_author_contract_owns_blocked_worker_causal_repair():
    author = _read("config/agents/change-dag-author.md")
    assert "edit_base_unavailable" in author
    assert "lacks a causal edge or a proper semantic decomposition" in author
    assert "exposing peer work" in author
    assert "Final whole-DAG `dag_validate`" in author


def test_author_contract_teaches_exclusive_terminals():
    author = _read("config/agents/change-dag-author.md")
    assert "`edit` is composable" in author
    assert "exclusive" in author
    # the run-barrier phrasing is retained under the broader exclusive rule
    assert "no `create`/`edit`/`remove`/`move` siblings" in author
