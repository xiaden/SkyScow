"""Service-owned Change-DAG worker resolution and session binding."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.caller_identity import set_caller_identity, take_caller_identity
from ..helpers.worker_resolution import resolve_worker


def dag_worker_resolve(
    slug: str,
    branch_ref: str,
    caller_agent: str | None = None,
    session_id: str | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    identity = take_caller_identity()
    if identity is None:
        if caller_agent is None or session_id is None:
            return {"error": "unbound_worker_session", "message": "service caller identity is required"}
        identity = {"agent": caller_agent, "session": session_id}
    try:
        return resolve_worker(workspace_root, slug, identity["agent"], identity["session"], branch_ref)
    except ValueError as exc:
        code, _, message = str(exc).partition(": ")
        return {"error": code, "message": message or code}


if __name__ == "__main__":
    args = json.loads(input())
    set_caller_identity(args)
    print(json.dumps(dag_worker_resolve(
        args["slug"], args["branch_ref"], workspace_root=Path(args["workspace_root"]),
    )))
