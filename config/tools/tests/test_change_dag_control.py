from __future__ import annotations

import re
import subprocess
from pathlib import Path

from common.helpers.change_dag import atomic_write_json, canonical_dag_digest
from common.helpers.change_dag_control import (
    acquire_construction_lock, acquire_lock, active_dag, capture_inherited_state, checkpoint_commit,
    checkpoint_identity, construction_lock_path, dequeue_next, inspect_current_state,
    enqueue, lock_acquirable, marker_stale, queue_list, queue_remove, read_marker,
    release_lock, remove_marker, write_marker,
)
from common.helpers.change_dag_controller import ConstructionController, ControllerDecision, ReviewOutcome, route_review_outcome
from common.tools.dag_construction_state import dag_construction_state



def test_lock_and_marker(tmp_path: Path):
    ok, fd = acquire_lock(tmp_path)
    assert ok and fd is not None and not lock_acquirable(tmp_path)
    write_marker(tmp_path, "demo", 99999999)
    assert read_marker(tmp_path)["slug"] == "demo"
    assert not marker_stale(tmp_path) and active_dag(tmp_path) == "demo"
    release_lock(fd)
    assert lock_acquirable(tmp_path) and marker_stale(tmp_path) and active_dag(tmp_path) is None
    remove_marker(tmp_path)
    assert read_marker(tmp_path) is None


def test_construction_lock_namespace_is_disjoint_from_mutation_and_prefix_safe(tmp_path: Path):
    from common.helpers.change_dag_control import mutation_lock
    with mutation_lock(tmp_path, "x"):
        ok, fd = acquire_construction_lock(tmp_path, "x.construction")
        assert ok and fd is not None
        release_lock(fd)
    assert construction_lock_path(tmp_path, "x") != construction_lock_path(tmp_path, "x.construction")


def test_construction_lock_is_exclusive_and_has_no_owner_metadata(tmp_path: Path):
    ok, fd = acquire_construction_lock(tmp_path, "demo")
    assert ok and fd is not None
    try:
        second, second_fd = acquire_construction_lock(tmp_path, "demo")
        assert not second and second_fd is None
        lock_path = construction_lock_path(tmp_path, "demo")
        assert lock_path.is_file() and lock_path.read_bytes() == b""
        assert not (lock_path.parent / "CONTROLLER_STATE.json").exists()
    finally:
        release_lock(fd)
    ok, fd = acquire_construction_lock(tmp_path, "demo")
    assert ok and fd is not None
    release_lock(fd)


def test_queue_fifo_and_duplicates(tmp_path: Path):
    assert enqueue(tmp_path, "a") == 1
    assert enqueue(tmp_path, "b", retry=True) == 2
    assert enqueue(tmp_path, "a", retry=True) == 1
    assert queue_list(tmp_path) == [{"slug": "a", "retry": False}, {"slug": "b", "retry": True}]
    assert queue_remove(tmp_path, "b")
    assert dequeue_next(tmp_path) == {"slug": "a", "retry": False}
    assert dequeue_next(tmp_path) is None


def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "base.txt").write_text("base")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    return tmp_path


def test_checkpoint_identity_is_deterministic_and_frontier_sensitive():
    dag = {
        "slug": "demo", "anchor_commit": "a" * 40, "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "requires": ["N2"], "decomposition_only": True},
            "N2": {"type": "semantic", "requirement": "open"},
        },
    }
    first = checkpoint_identity(dag)
    equivalent = {"nodes": dag["nodes"], "root": "N1", "anchor_commit": "a" * 40, "slug": "demo"}
    assert first == checkpoint_identity(equivalent)
    dag["nodes"]["N2"]["requirement"] = "changed"
    assert first != checkpoint_identity(dag)


def test_checkpoint_identity_changes_when_frontier_changes():
    dag = {
        "slug": "demo", "anchor_commit": "a" * 40, "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "requires": ["N2"], "decomposition_only": True},
            "N2": {"type": "semantic", "requirement": "open"},
        },
    }
    first = checkpoint_identity(dag)
    dag["nodes"]["N2"]["state"] = "satisfied"
    assert first != checkpoint_identity(dag)


def test_current_state_inspection_uses_only_dag_and_derived_frontier(tmp_path: Path):
    bundle = tmp_path / "artifacts/change-dags/pending/demo"
    bundle.mkdir(parents=True)
    dag = {
        "slug": "demo", "anchor_commit": "a" * 40, "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "requires": ["N2"], "decomposition_only": True},
            "N2": {"type": "semantic", "requirement": "open"},
        },
    }
    (bundle / "DAG.json").write_text(__import__("json").dumps(dag), encoding="utf-8")
    (bundle / "DAG_MUTATIONS.jsonl").write_text("not consulted\n", encoding="utf-8")
    state = inspect_current_state(tmp_path, "demo")
    assert state["dag_digest"] == canonical_dag_digest(dag)
    assert state["frontier"]["frontier"]["depth"] == 1
    assert not (tmp_path / "CONTROLLER_STATE.json").exists()


def _controller_workspace(tmp_path: Path, *, resolved: bool = False) -> tuple[Path, dict]:
    root = tmp_path / "workspace"
    bundle = root / "artifacts/change-dags/pending/demo"
    bundle.mkdir(parents=True)
    dag = {
        "slug": "demo", "anchor_commit": "a" * 40, "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "requires": ["N2"], "decomposition_only": True},
            "N2": {"type": "semantic", "requirement": "open"},
        },
    }
    if resolved:
        dag["nodes"]["N2"] = {"type": "semantic", "requirement": "terminal", "requires": ["N3"]}
        dag["nodes"]["N3"] = {"type": "edit", "path": "x.txt", "patch": "@@ -1 +1 @@\\n-a\\n+b\\n"}
    atomic_write_json(bundle / "DAG.json", dag)
    return root, dag


def test_plugin_construction_state_boundary_attaches_controller_and_requires_review(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path)
    state = dag_construction_state("demo", workspace_root=root)
    assert state["decision"]["kind"] == "review_required"
    assert state["decision"]["checkpoint_identity"]
    assert state["dag_checkpoint_identity"]
    accepted = dag_construction_state("demo", state["decision"]["checkpoint_identity"], workspace_root=root)
    assert accepted["decision"]["kind"] == "admit_worker"
    assert accepted["decision"]["branch_claim"]["nodes"] == ["N2"]


def test_plugin_construction_state_boundary_reports_busy_attachment(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    try:
        state = dag_construction_state("demo", workspace_root=root)
        assert state["decision"]["kind"] == "busy"
    finally:
        controller.close()


def test_controller_requires_review_then_derives_deterministic_admission(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    try:
        first = controller.next_action()
        assert first == ControllerDecision("review_required", first.checkpoint_identity)
        admitted = controller.accept_review(first.checkpoint_identity)
        assert admitted.kind == "admit_worker"
        assert admitted.node_id == "N2"
        assert admitted.branch_claim["nodes"] == ["N2"]
    finally:
        controller.close()


def test_controller_requires_exactly_one_fresh_review_after_completed_worker(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    try:
        first = controller.next_action()
        assert first.kind == "review_required"
        assert controller.submit_review(ReviewOutcome("PASS", first.checkpoint_identity)).kind == "admit_worker"
        assert controller.admit_worker().kind == "admit_worker"
        assert controller.complete_child().kind == "review_required"
        assert controller.next_action().kind == "review_required"
        second = controller.next_action()
        assert controller.submit_review(ReviewOutcome("PASS", second.checkpoint_identity)).kind == "admit_worker"
    finally:
        controller.close()


def test_completed_frontier_requires_re_review_after_identity_change(tmp_path: Path):
    root, dag = _controller_workspace(tmp_path)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    try:
        first = controller.next_action()
        controller.submit_review(ReviewOutcome("PASS", first.checkpoint_identity))
        controller.admit_worker()
        dag["nodes"]["N2"]["requirement"] = "changed"
        atomic_write_json(root / "artifacts/change-dags/pending/demo/DAG.json", dag)
        assert controller.complete_child().kind == "stale_checkpoint"
        fresh = controller.next_action()
        assert fresh.kind == "review_required"
        assert controller.submit_review(ReviewOutcome("PASS", fresh.checkpoint_identity)).kind == "admit_worker"
    finally:
        controller.close()


def test_controller_serializes_one_worker_admission_at_a_time(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    try:
        review = controller.next_action()
        controller.accept_review(review.checkpoint_identity)
        active = controller.admit_worker()
        assert active.kind == "admit_worker"
        assert controller.next_action().kind == "child_active"
        assert controller.admit_worker().kind == "child_active"
        assert controller.complete_child().kind == "review_required"
    finally:
        controller.close()


def test_review_outcomes_route_mechanically_without_dag_interpretation():
    assert route_review_outcome("PASS") == "advance"
    assert route_review_outcome("EXACT_WORK_DEFECT") == "exact_work_fixer"
    assert route_review_outcome("SEMANTIC_DEFECT") == "semantic_repair"
    assert route_review_outcome("GRAPH_DEFECT") == "semantic_repair"
    assert route_review_outcome("AUTHORITY_ISSUE") == "stop_escalate"
    assert route_review_outcome("BLOCKED") == "stop_review_required"


def test_non_pass_review_outcomes_are_typed_and_cannot_admit_or_mutate(tmp_path: Path):
    root, dag = _controller_workspace(tmp_path)
    before = __import__("json").dumps(dag, sort_keys=True)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    try:
        review = controller.next_action()
        for kind in ("EXACT_WORK_DEFECT", "SEMANTIC_DEFECT", "GRAPH_DEFECT", "AUTHORITY_ISSUE", "BLOCKED"):
            result = controller.submit_review(ReviewOutcome(kind, review.checkpoint_identity))
            assert result.kind == "review_required"
            assert result.route == route_review_outcome(kind)
            assert controller.next_action().kind == "review_required"
        assert __import__("json").dumps(dag, sort_keys=True) == before
    finally:
        controller.close()


def test_controller_rejects_stale_checkpoint_after_current_dag_changes(tmp_path: Path):
    root, dag = _controller_workspace(tmp_path)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    try:
        identity = controller.next_action().checkpoint_identity
        dag["nodes"]["N2"]["requirement"] = "changed"
        atomic_write_json(root / "artifacts/change-dags/pending/demo/DAG.json", dag)
        decision = controller.accept_review(identity)
        assert decision.kind == "stale_checkpoint"
    finally:
        controller.close()


def test_simulated_restart_discards_ephemeral_review_and_child_state(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path)
    first = ConstructionController.attach(root, "demo")
    assert isinstance(first, ConstructionController)
    review = first.next_action()
    assert first.submit_review(ReviewOutcome("PASS", review.checkpoint_identity)).kind == "admit_worker"
    assert first.admit_worker().kind == "admit_worker"
    # A process restart releases the kernel-owned lock; a new attachment has no
    # access to the old in-memory admission or review.
    first._closed = True
    import os
    os.close(first.lock_fd)
    first._lock_fd = None
    restarted = ConstructionController.attach(root, "demo")
    assert isinstance(restarted, ConstructionController)
    try:
        assert restarted.next_action().kind == "review_required"
    finally:
        restarted.close()


def test_invalid_current_dag_is_typed_blocked_without_lock_or_mutation(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path)
    (root / "artifacts/change-dags/pending/demo/DAG.json").write_text("{invalid", encoding="utf-8")
    decision = ConstructionController.attach(root, "demo")
    assert isinstance(decision, ControllerDecision)
    assert decision.kind == "blocked"
    assert decision.route == "stop_escalate"
    assert decision.checkpoint_identity is None
    assert not (root / "artifacts/change-dags/.control/dag-demo.construction.lock").exists()


def test_stale_old_checkpoint_cannot_admit_after_new_attachment(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path)
    first = ConstructionController.attach(root, "demo")
    assert isinstance(first, ConstructionController)
    old = first.next_action().checkpoint_identity
    first.close()
    second = ConstructionController.attach(root, "demo")
    assert isinstance(second, ConstructionController)
    try:
        assert second.admit_worker(old).kind == "stale_checkpoint"
        assert second.accept_review(old).kind == "stale_checkpoint"
    finally:
        second.close()


def test_controller_does_not_read_execution_history_or_task_history(tmp_path: Path, monkeypatch):
    root, _dag = _controller_workspace(tmp_path)
    for name in ("WORK_LOG.jsonl", "TASK_HISTORY.jsonl"):
        (root / "artifacts/change-dags/pending/demo" / name).write_text("not consulted\n", encoding="utf-8")
    original = Path.read_text

    def fail_history_read(path, *args, **kwargs):
        if path.name in {"WORK_LOG.jsonl", "TASK_HISTORY.jsonl"}:
            raise AssertionError(f"controller read {path.name}")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_history_read)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    controller.close()


def test_fresh_attachment_is_review_required_and_second_attachment_busy(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path)
    first = ConstructionController.attach(root, "demo")
    assert isinstance(first, ConstructionController)
    try:
        second = ConstructionController.attach(root, "demo")
        assert isinstance(second, ControllerDecision)
        assert second.kind == "busy"
        assert first.next_action().kind == "review_required"
    finally:
        first.close()


def test_controller_inspection_does_not_read_mutation_history(tmp_path: Path, monkeypatch):
    root, _dag = _controller_workspace(tmp_path)
    history = root / "artifacts/change-dags/pending/demo/DAG_MUTATIONS.jsonl"
    history.write_text("malformed history must not matter\\n", encoding="utf-8")
    original = Path.read_text

    def fail_history_read(path, *args, **kwargs):
        if path.name == "DAG_MUTATIONS.jsonl":
            raise AssertionError("controller read mutation history")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_history_read)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    controller.close()


def test_controller_reports_complete_from_current_frontier(tmp_path: Path):
    root, _dag = _controller_workspace(tmp_path, resolved=True)
    controller = ConstructionController.attach(root, "demo")
    assert isinstance(controller, ConstructionController)
    try:
        assert controller.next_action().kind == "review_required"
        assert controller.accept_review(controller.next_action().checkpoint_identity).kind == "complete"
    finally:
        controller.close()


def test_capture_and_checkpoint(tmp_path: Path):
    repo = git_repo(tmp_path)
    (repo / "change.txt").write_text("change")
    inherited = capture_inherited_state(repo)
    assert re.fullmatch(r"[0-9a-f]{40}", inherited["head"])
    assert "?? change.txt" in inherited["porcelain"]
    result = checkpoint_commit(repo, "demo", inherited)
    assert result["committed"] and re.fullmatch(r"[0-9a-f]{40}", result["sha"])
    assert result["inherited"] == inherited
    second = checkpoint_commit(repo, "demo", inherited)
    assert not second["committed"]
