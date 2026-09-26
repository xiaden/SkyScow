"""Archive a completed Change DAG bundle; QA is intentionally independent."""
from __future__ import annotations
import json, shutil
from pathlib import Path
from ..helpers import change_dag, change_dag_state as state_helper

def dag_archive(slug: str, force: bool = False, *, workspace_root: Path) -> dict:
    root = Path(workspace_root)
    try:
        dag, source, location = change_dag.read_dag(root, slug)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": "not_found", "message": str(exc)}
    if location != "pending":
        return {"error": "already_archived", "message": "DAG is already completed"}
    state = state_helper.state_with_defaults(dag, state_helper.read_state(root, slug))
    satisfaction = change_dag.derived_satisfaction(dag, state)
    if not satisfaction.get(dag["root"], False) or any(v in {"failed", "in_progress"} for v in state.values()):
        return {"error": "incomplete_dag", "message": "root must be satisfied and no terminal node may be failed or in_progress"}
    destination = root / change_dag.COMPLETED_DIR / slug
    if destination.exists() and not force:
        return {"error": "already_exists", "message": str(destination)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.move(str(source.parent), str(destination))
    return {"archived": True, "path": str(destination.relative_to(root))}

if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(dag_archive(args["slug"], args.get("force", False), workspace_root=Path(args["workspace_root"]))))
