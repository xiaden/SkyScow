"""Read current construction identity for the native v1 adapter boundary."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_controller import ConstructionController, ControllerDecision
from ..helpers.change_dag_control import inspect_current_state


def dag_construction_state(
    slug: str,
    review_checkpoint_identity: str | None = None,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    """Attach the controller and expose the current review gate.

    Native v1 has no child-task lifecycle callback. This short-lived Python
    boundary therefore performs current-state/review gating only; the plugin's
    awaited native prompt owns the real in-process child admission lifetime.
    """
    state = inspect_current_state(workspace_root, slug)
    attached = ConstructionController.attach(workspace_root, slug)
    if isinstance(attached, ControllerDecision):
        return {
            "slug": slug,
            "dag_checkpoint_identity": state["checkpoint_identity"],
            "decision": {
                "kind": attached.kind,
                "checkpoint_identity": attached.checkpoint_identity,
                "route": attached.route,
                "message": attached.message,
            },
        }
    try:
        if review_checkpoint_identity is not None:
            decision = attached.accept_dag_review(review_checkpoint_identity)
        else:
            decision = attached.next_action()
        return {
            "slug": slug,
            "dag_checkpoint_identity": state["checkpoint_identity"],
            "decision": {
                "kind": decision.kind,
                "checkpoint_identity": state["checkpoint_identity"],
                "route": decision.route,
                "node_id": decision.node_id,
                "branch_claim": decision.branch_claim,
                "message": decision.message,
            },
        }
    finally:
        attached.close()


if __name__ == "__main__":
    args = json.loads(input())
    try:
        print(json.dumps(dag_construction_state(
            args["slug"], args.get("review_checkpoint_identity"), workspace_root=Path(args["workspace_root"])
        )))
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(json.dumps({"error": "construction_state_unavailable", "message": str(exc)}))
