"""Report Change DAG execution and derived progress."""
from __future__ import annotations
import json
from pathlib import Path
from ..helpers import change_dag, change_dag_compiler as compiler, change_dag_control as control, change_dag_state as state_helper

def _one(slug: str, root: Path) -> dict:
    if control.marker_stale(root):
        marker = control.read_marker(root)
        if marker:
            from .dag_executor import reconcile_interrupted
            reconcile_interrupted(root, marker["slug"])
        control.remove_marker(root)
    dag, _, _ = change_dag.read_dag(root, slug)
    state = state_helper.state_with_defaults(dag, state_helper.read_state(root, slug))
    sat = change_dag.derived_satisfaction(dag, state)
    queued = control.queue_list(root)
    queue_pos = next((i + 1 for i, item in enumerate(queued) if item["slug"] == slug), None)
    active = control.active_dag(root)
    return {"state": "queued" if queue_pos else ("running" if active == slug else ("root_satisfied" if sat.get(dag["root"], False) else "idle")), "queue_position": queue_pos, "terminal": state, "failed": [n for n,v in state.items() if v == "failed"], "in_progress": [n for n,v in state.items() if v == "in_progress"], "reachable": sorted(change_dag.reachable_from_root(dag), key=change_dag._numeric_id), "unresolved_leaves": change_dag.unresolved_leaves(dag), "root_satisfied": bool(sat.get(dag["root"], False)), "active_run_nodes": [n for n in compiler.ready_run_nodes(dag, state, root) if state.get(n) == "in_progress"]}

def dag_status(slug: str | None = None, *, workspace_root: Path) -> dict:
    root = Path(workspace_root)
    if slug is None:
        return {"active_dag": control.active_dag(root), "queued_dags": control.queue_list(root)}
    return _one(slug, root)

if __name__ == "__main__":
    args = json.loads(__import__("sys").stdin.read())
    print(json.dumps(dag_status(args.get("slug"), workspace_root=Path(args["workspace_root"]))))
