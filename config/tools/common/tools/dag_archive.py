"""Retire a Change DAG bundle from the pending working set.

Archival is lifecycle cleanup, not certification. A DAG may be archived because
execution completed, failed, was abandoned, was superseded, was cancelled, or
became obsolete; the move itself implies none of those. Archival therefore does
not require ``resolved``, ``executable``, root satisfaction, an absence of
failed nodes, or QA -- those are recorded as disposition facts, not admission
gates.

Only operational-integrity gates apply: a bundle is never moved while an
executor owns it (running) or while a queued admission could still launch it.
The bundle keeps a truthful disposition record (``ARCHIVE.json``) written before
the move, so historical state survives the retirement.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ..helpers import change_dag
from ..helpers import change_dag_compiler_phase as compiler_phase
from ..helpers import change_dag_control as control
from ..helpers import change_dag_state as state_helper

ARCHIVE_RECORD_FILENAME = "ARCHIVE.json"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _state_at_archive(dag_path: Path, root: Path, slug: str) -> dict:
    """Summarize the artifact's state at retirement using canonical helpers.

    Every value is derived from the canonical graph/state/validation model. If
    the artifact is malformed, archival still proceeds and the failure to inspect
    is recorded rather than becoming an archive refusal.
    """
    summary: dict = {
        "schema_valid": None,
        "resolved": None,
        "executable": None,
        "root_satisfied": None,
        "failed_nodes": [],
        "in_progress_nodes": [],
        "not_satisfied_nodes": [],
    }
    try:
        dag = change_dag.read_json(dag_path)
        state = state_helper.state_with_defaults(dag, state_helper.read_state(root, slug))
        satisfaction = change_dag.derived_satisfaction(dag, state)
        summary.update(
            {
                "schema_valid": not change_dag.schema_errors(dag),
                "resolved": change_dag.is_resolved(dag),
                "executable": compiler_phase.preflight(dag, state, root)["executable"],
                "root_satisfied": bool(satisfaction.get(dag.get("root"), False)),
                "failed_nodes": sorted(
                    (node for node, value in state.items() if value == "failed"),
                    key=change_dag._numeric_id,
                ),
                "in_progress_nodes": sorted(
                    (node for node, value in state.items() if value == "in_progress"),
                    key=change_dag._numeric_id,
                ),
                "not_satisfied_nodes": sorted(
                    (node for node, value in state.items() if value == "not_satisfied"),
                    key=change_dag._numeric_id,
                ),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive; malformed artifacts are still archivable
        summary["inspection_error"] = str(exc)
    return summary


def dag_archive(slug: str, reason: str, force: bool = False, *, workspace_root: Path) -> dict:
    root = Path(workspace_root)
    if not isinstance(reason, str) or not reason.strip():
        return {"error": "reason_required", "message": "dag_archive requires a non-empty reason for retiring the DAG"}
    try:
        path, location = change_dag.locate_dag(root, slug)
    except ValueError as exc:
        return {"error": "invalid_slug", "message": str(exc)}
    if path is None or location is None:
        return {"error": "not_found", "message": f"change dag not found: {slug}"}
    if location != "pending":
        return {"error": "already_archived", "message": f"change dag {slug!r} is already archived"}

    # Operational-integrity gates only. Never move a bundle while an executor can
    # still write into it or while a queued admission can launch it.
    if control.active_dag(root) == slug:
        return {"error": "dag_running", "message": f"change dag {slug!r} is currently executing; call dag_stop before archiving"}
    if any(entry["slug"] == slug for entry in control.queue_list(root)):
        return {"error": "dag_queued", "message": f"change dag {slug!r} is queued behind another execution; call dag_stop to cancel it before archiving"}

    # Serialize retirement against the same per-DAG lock used by construction
    # mutations. This prevents a mutation from persisting into a recreated
    # pending bundle while archive moves the original bundle.
    with control.mutation_lock(root, slug):
        current_path, current_location = change_dag.locate_dag(root, slug)
        if current_path is None or current_location != "pending":
            return {"error": "already_archived", "message": f"change dag {slug!r} is no longer pending"}
        path = current_path
        bundle = path.parent
        destination = root / change_dag.ARCHIVED_DIR / change_dag._safe_slug(slug)
        if destination.exists() and not force:
            return {"error": "already_exists", "message": str(destination)}

        state_at_archive = _state_at_archive(path, root, slug)
        artifacts_moved = sorted(
            {entry.name for entry in bundle.iterdir() if entry.is_file()} | {ARCHIVE_RECORD_FILENAME}
        )
        record = {
            "archived_at": _utc_timestamp(),
            "reason": reason.strip(),
            "state_at_archive": state_at_archive,
            "artifacts_moved": artifacts_moved,
        }
        change_dag.atomic_write_json(bundle / ARCHIVE_RECORD_FILENAME, record)

        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(bundle), str(destination))
        return {
            "archived": True,
            "path": str(destination.relative_to(root)),
            "reason": record["reason"],
            "state_at_archive": state_at_archive,
            "artifacts_moved": artifacts_moved,
        }


if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(dag_archive(args["slug"], args.get("reason"), args.get("force", False), workspace_root=Path(args["workspace_root"]))))
