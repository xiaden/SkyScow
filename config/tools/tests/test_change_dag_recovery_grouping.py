"""F8: interruption recovery reconciles a composed atomic operation as one unit.

A single ``CompiledOp`` maps to one atomic repository mutation, so every
``op.nodes`` contributor shares its outcome. The executor records bounded
pre-apply operation evidence (base + expected content fingerprints); recovery
reads that evidence and reconciles the whole group as present, absent, or
coherently ambiguous. An atomic operation must never be split into partial
success.

Fixtures follow the real patterns in ``test_dag_runner.py`` (``make_repo``,
``write_raw_dag``).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag  # noqa: E402
from common.helpers.change_dag_compiler_runtime import node_present  # noqa: E402
from common.helpers import change_dag_state as state_helper  # noqa: E402
from common.tools.dag_executor import reconcile_interrupted, run_execution  # noqa: E402


def make_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / ".keep").write_text("keep\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    return tmp_path


def write_raw_dag(root: Path, slug: str, dag: dict) -> None:
    bundle = root / "artifacts/change-dags/pending" / slug
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "DAG.json").write_text(json.dumps(dag), encoding="utf-8")


def edit(path: str, old: str, new: str) -> dict:
    return {"type": "edit", "path": path, "patch": f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,1 @@\n-{old}\n+{new}\n"}


def composed_edit_dag(slug: str = "composed") -> dict:
    """Deeper N5 (a->b) then shallower N4 (b->c): one atomic edit op to 'c'."""
    return {
        "slug": slug,
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "satisfied_by": ["N2"]},
            "N2": {"type": "semantic", "requirement": "implementation", "satisfied_by": ["N3", "N4"]},
            "N3": {"type": "semantic", "requirement": "deeper", "satisfied_by": ["N5"]},
            "N4": edit("f.txt", "b", "c"),
            "N5": edit("f.txt", "a", "b"),
        },
    }


def single_edit_dag(slug: str = "single") -> dict:
    return {
        "slug": slug,
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "satisfied_by": ["N2"]},
            "N2": edit("f.txt", "a", "b"),
        },
    }


def _fp(text: str) -> dict:
    data = text.encode("utf-8")
    return {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def _starts(root: Path, slug: str) -> list[dict]:
    return [
        entry for entry in state_helper.read_work_log(root, slug)
        if entry.get("operation") == "apply" and entry.get("phase") == "start"
    ]


def _resolved(result: dict) -> dict[str, str]:
    return {entry["nodes"][0]: entry["resolved"] for entry in result["reconciled"]}


def _run_to_completion(root: Path, slug: str, dag: dict, expected: str) -> None:
    (root / "f.txt").write_text("a\n", encoding="utf-8")
    write_raw_dag(root, slug, dag)
    result = run_execution(root, slug)
    assert result["state"] == "root_satisfied"
    assert (root / "f.txt").read_text(encoding="utf-8") == expected


# ---------------------------------------------------------------------------
# Operation-level evidence contract
# ---------------------------------------------------------------------------
def test_composed_edit_is_one_operation_with_bounded_evidence(tmp_path: Path):
    root = make_repo(tmp_path)
    _run_to_completion(root, "composed", composed_edit_dag("composed"), "c\n")

    starts = _starts(root, "composed")
    assert len(starts) == 1, "one atomic CompiledOp must emit exactly one evidence entry"
    entry = starts[0]
    assert set(entry["nodes"]) == {"N4", "N5"}
    assert entry["action"] == "edit"
    assert entry["path"] == "f.txt"
    assert entry["expected_fingerprint"] == _fp("c\n")
    assert entry["base_fingerprint"] == _fp("a\n")


def test_reproduced_before_per_node_recovery_splits_the_composed_op(tmp_path: Path):
    """Root-cause demonstration: independent node reconciliation is incoherent."""
    root = make_repo(tmp_path)
    (root / "f.txt").write_text("c\n", encoding="utf-8")
    write_raw_dag(root, "composed", composed_edit_dag("composed"))
    dag = change_dag.read_dag(root, "composed")[0]

    # The single atomic operation fully landed, yet per-node classification
    # disagrees: N4 (b->c) proves present in "c" while N5 (a->b) does not.
    n4 = node_present(dag, "N4", root)
    n5 = node_present(dag, "N5", root)
    assert n4 == "present"
    assert n5 != "present"
    # This mismatch is exactly the fabricated partial success the grouping fixes.


# ---------------------------------------------------------------------------
# Interruption after replacement, before terminal state persistence
# ---------------------------------------------------------------------------
def test_composed_op_interrupted_after_application_is_consistent(tmp_path: Path):
    root = make_repo(tmp_path)
    _run_to_completion(root, "composed", composed_edit_dag("composed"), "c\n")

    # Simulate interruption before terminal state persisted: only the state is
    # rewound; the applied file and the pre-apply evidence remain.
    state_helper.write_state(root, "composed", {"N4": "in_progress", "N5": "in_progress"})
    result = reconcile_interrupted(root, "composed")

    assert _resolved(result) == {"N4": "satisfied", "N5": "satisfied"}
    state = state_helper.read_state(root, "composed")
    assert state["N4"] == "satisfied" and state["N5"] == "satisfied"
    # The atomic operation did land and must not be replayed.
    assert (root / "f.txt").read_text(encoding="utf-8") == "c\n"


def test_composed_op_interrupted_before_application_is_consistent(tmp_path: Path):
    root = make_repo(tmp_path)
    _run_to_completion(root, "composed", composed_edit_dag("composed"), "c\n")

    # Simulate interruption after evidence was recorded but before the mutation:
    # the file is still at the recorded base.
    (root / "f.txt").write_text("a\n", encoding="utf-8")
    state_helper.write_state(root, "composed", {"N4": "in_progress", "N5": "in_progress"})
    result = reconcile_interrupted(root, "composed")

    assert _resolved(result) == {"N4": "not_satisfied", "N5": "not_satisfied"}
    state = state_helper.read_state(root, "composed")
    assert state["N4"] == "not_satisfied" and state["N5"] == "not_satisfied"


def test_composed_op_external_change_is_coherently_ambiguous(tmp_path: Path):
    root = make_repo(tmp_path)
    _run_to_completion(root, "composed", composed_edit_dag("composed"), "c\n")

    # An unrelated external change leaves content matching neither the base nor the
    # expected result: the whole group is ambiguous, never partial success.
    (root / "f.txt").write_text("external\n", encoding="utf-8")
    state_helper.write_state(root, "composed", {"N4": "in_progress", "N5": "in_progress"})
    result = reconcile_interrupted(root, "composed")

    assert _resolved(result) == {"N4": "failed", "N5": "failed"}
    state = state_helper.read_state(root, "composed")
    assert state["N4"] == "failed" and state["N5"] == "failed"


# ---------------------------------------------------------------------------
# Single-node operations keep their ordinary recovery
# ---------------------------------------------------------------------------
def test_single_node_edit_recovery_is_unchanged(tmp_path: Path):
    root = make_repo(tmp_path)
    _run_to_completion(root, "single", single_edit_dag("single"), "b\n")

    starts = _starts(root, "single")
    assert len(starts) == 1 and starts[0]["nodes"] == ["N2"]

    # Applied, state rewound -> satisfied.
    state_helper.write_state(root, "single", {"N2": "in_progress"})
    assert _resolved(reconcile_interrupted(root, "single")) == {"N2": "satisfied"}

    # Not applied, state rewound -> not_satisfied.
    (root / "f.txt").write_text("a\n", encoding="utf-8")
    state_helper.write_state(root, "single", {"N2": "in_progress"})
    assert _resolved(reconcile_interrupted(root, "single")) == {"N2": "not_satisfied"}


# ---------------------------------------------------------------------------
# MOVE recovery is preserved (recorded source fingerprint still authoritative)
# ---------------------------------------------------------------------------
def test_move_recovery_still_requires_recorded_fingerprint(tmp_path: Path):
    root = make_repo(tmp_path)
    dag = {
        "slug": "move",
        "anchor_commit": "a" * 40,
        "root": "N1",
        "nodes": {
            "N1": {"type": "semantic", "requirement": "root", "satisfied_by": ["N2"]},
            "N2": {"type": "move", "from_path": "old.txt", "to_path": "new.txt"},
        },
    }
    write_raw_dag(root, "move", dag)
    state_helper.append_work_log(root, "move", state_helper.log_move_start(
        ["N2"], from_path="old.txt", to_path="new.txt", overwrite=False,
        source_fingerprint=_fp("payload\n"),
    ))

    # Destination content matches the recorded source fingerprint -> satisfied.
    (root / "new.txt").write_text("payload\n", encoding="utf-8")
    state_helper.write_state(root, "move", {"N2": "in_progress"})
    assert _resolved(reconcile_interrupted(root, "move")) == {"N2": "satisfied"}

    # Mismatched destination -> ambiguous -> failed; recovery never guesses.
    (root / "new.txt").write_text("other\n", encoding="utf-8")
    state_helper.write_state(root, "move", {"N2": "in_progress"})
    assert _resolved(reconcile_interrupted(root, "move")) == {"N2": "failed"}
