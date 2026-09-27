from __future__ import annotations

import contextlib
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common.helpers import change_dag_control as control
from common.tools import dag_executor


def _slugs(root: Path) -> list[str]:
    return [entry["slug"] for entry in control.queue_list(root)]


def test_duplicate_admission_preserves_fifo_position_and_original_request(tmp_path: Path):
    assert control.enqueue(tmp_path, "a") == 1
    assert control.enqueue(tmp_path, "b", retry=False) == 2
    assert control.enqueue(tmp_path, "c") == 3

    assert control.enqueue(tmp_path, "b", retry=True) == 2
    assert control.queue_list(tmp_path) == [
        {"slug": "a", "retry": False},
        {"slug": "b", "retry": False},
        {"slug": "c", "retry": False},
    ]
    assert _slugs(tmp_path).count("b") == 1


def test_concurrent_unique_admission_keeps_every_request_once(tmp_path: Path):
    slugs = [f"dag-{index}" for index in range(40)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda slug: control.enqueue(tmp_path, slug), slugs))

    admitted = _slugs(tmp_path)
    assert len(admitted) == len(slugs)
    assert set(admitted) == set(slugs)
    assert len(admitted) == len(set(admitted))


def test_removing_non_head_preserves_remaining_order(tmp_path: Path):
    for slug in ("a", "b", "c", "d"):
        control.enqueue(tmp_path, slug)

    assert control.queue_remove(tmp_path, "c") is True
    assert _slugs(tmp_path) == ["a", "b", "d"]


def test_handoff_holds_queue_lock_so_removed_head_cannot_pop_following_entry(tmp_path: Path, monkeypatch):
    for slug in ("a", "b", "c"):
        control.enqueue(tmp_path, slug)

    queue_gate = threading.Lock()
    handoff_locked = threading.Event()
    remove_attempted = threading.Event()
    launch_started = threading.Event()
    allow_launch = threading.Event()
    launch_result: list[bool] = []
    remove_result: list[bool] = []
    admission_done = threading.Event()

    calls = 0
    calls_guard = threading.Lock()

    @contextlib.contextmanager
    def controlled_queue_lock(_root: Path):
        nonlocal calls
        with calls_guard:
            calls += 1
            call_number = calls
        if call_number == 1:
            handoff_locked.set()
        else:
            remove_attempted.set()
        queue_gate.acquire()
        try:
            yield None
        finally:
            queue_gate.release()

    class FakeChild:
        pid = 32101

    def fake_popen(*args, **kwargs):
        launch_started.set()
        assert allow_launch.wait(2)
        return FakeChild()

    monkeypatch.setattr(control, "queue_lock", controlled_queue_lock)
    monkeypatch.setattr(dag_executor.subprocess, "Popen", fake_popen)

    def launch() -> None:
        launch_result.append(dag_executor._launch_next(tmp_path))

    def remove_selected_head() -> None:
        remove_result.append(control.queue_remove(tmp_path, "a"))

    def admit_following_request() -> None:
        control.enqueue(tmp_path, "d")
        admission_done.set()

    launch_thread = threading.Thread(target=launch)
    remove_thread = threading.Thread(target=remove_selected_head)
    admission_thread = threading.Thread(target=admit_following_request)
    launch_thread.start()
    assert handoff_locked.wait(2)
    assert launch_started.wait(2)

    remove_thread.start()
    admission_thread.start()
    assert remove_attempted.wait(2)
    # Both mutations have reached the queue lock and cannot pass the selected
    # head while the launch handoff is paused.
    assert not admission_done.wait(0.05)

    allow_launch.set()
    launch_thread.join(2)
    remove_thread.join(2)
    admission_thread.join(2)

    assert launch_result == [True]
    assert remove_result == [False]
    assert admission_done.is_set()
    assert _slugs(tmp_path) == ["b", "c", "d"]
    control.remove_marker(tmp_path)


def test_failed_launch_keeps_selected_head_first(tmp_path: Path, monkeypatch):
    control.enqueue(tmp_path, "a")
    control.enqueue(tmp_path, "b")

    def fail_popen(*args, **kwargs):
        raise OSError("spawn failed")

    monkeypatch.setattr(dag_executor.subprocess, "Popen", fail_popen)

    assert dag_executor._launch_next(tmp_path) is False
    assert _slugs(tmp_path) == ["a", "b"]
    assert control.lock_acquirable(tmp_path)


def test_marker_failure_terminates_child_and_keeps_selected_head(tmp_path: Path, monkeypatch):
    control.enqueue(tmp_path, "a")
    control.enqueue(tmp_path, "b")
    stopped: list[int] = []

    class FakeChild:
        pid = 32102

    monkeypatch.setattr(dag_executor.subprocess, "Popen", lambda *args, **kwargs: FakeChild())
    monkeypatch.setattr(control, "write_marker", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("marker failed")))
    monkeypatch.setattr(control, "stop_process_group", lambda pid: stopped.append(pid) or True)

    assert dag_executor._launch_next(tmp_path) is False
    assert stopped == [32102]
    assert _slugs(tmp_path) == ["a", "b"]
    assert control.read_marker(tmp_path) is None
    assert control.lock_acquirable(tmp_path)


def test_successful_handoff_removes_exactly_launched_head(tmp_path: Path, monkeypatch):
    control.enqueue(tmp_path, "a")
    control.enqueue(tmp_path, "b")

    class FakeChild:
        pid = 32103

    monkeypatch.setattr(dag_executor.subprocess, "Popen", lambda *args, **kwargs: FakeChild())

    assert dag_executor._launch_next(tmp_path) is True
    assert _slugs(tmp_path) == ["b"]
    assert control.read_marker(tmp_path) == {"slug": "a", "pid": 32103}
    control.remove_marker(tmp_path)
