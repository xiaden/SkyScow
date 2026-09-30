"""Validate and route typed construction review evidence through the controller core."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.change_dag_controller import ConstructionController, ControllerDecision, ReviewOutcome


def dag_construction_review(
    slug: str,
    checkpoint_identity: str,
    outcome: str,
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    attached = ConstructionController.attach(workspace_root, slug)
    if isinstance(attached, ControllerDecision):
        return {"slug": slug, "checkpoint_identity": checkpoint_identity, "outcome": outcome, "route": attached.route, "decision": attached.kind}
    try:
        decision = attached.submit_review(ReviewOutcome(outcome, checkpoint_identity))
        return {
            "slug": slug,
            "checkpoint_identity": checkpoint_identity,
            "outcome": outcome,
            "route": decision.route,
            "decision": decision.kind,
            "message": decision.message,
        }
    finally:
        attached.close()


if __name__ == "__main__":
    args = json.loads(input())
    try:
        print(json.dumps(dag_construction_review(
            args["slug"], args["checkpoint_identity"], args["outcome"], workspace_root=Path(args["workspace_root"])
        )))
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(json.dumps({"error": "construction_review_invalid", "message": str(exc)}))
