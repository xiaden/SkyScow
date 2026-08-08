"""MCP tool: Revert a step from complete back to pending in a task plan."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..helpers.plan_md import parse_plan, plan_to_dict, unmark_step

PLANS_PENDING_DIR = "artifacts/plans/pending"


def _normalize_plan_name(plan_name: str) -> str:
    """Normalize plan name, stripping .md if present."""
    if plan_name.endswith(".md"):
        return plan_name[:-3]
    return plan_name


def _validate_plan_name(plan_name: str) -> str | None:
    """Validate plan name. Returns error message or None if valid."""
    if "/" in plan_name or "\\" in plan_name or ".." in plan_name:
        return f"Invalid plan_name '{plan_name}': path separators and traversal not allowed"
    return None


def _resolve_plan_path(plan_name: str, workspace_root: Path) -> Path:
    """Resolve plan name to full path in pending directory only."""
    normalized = _normalize_plan_name(plan_name)
    return workspace_root / PLANS_PENDING_DIR / f"{normalized}.md"


def plan_unmark_step(
    plan_name: str,
    step_id: str,
    workspace_root: Path,
    agent: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Revert a step from complete back to pending.

    Prepends an [UNMARKED by <agent>: <reason>] notice to the step's annotations.
    Multiple unmarks accumulate via the existing append behavior.

    Args:
        plan_name: Plan name (with or without .md extension).
        step_id: Step ID in P<n>-S<m> format (e.g., "P1-S3").
        workspace_root: Workspace root path (injected by MCP server).
        agent: Name of the agent performing the unmark (e.g., "exec-manager", "qa-reviewer").
        reason: Optional reason for unmarking the step.

    Returns:
        Response with step_id, was_unmarked, and previous_status.

    """
    # Validate plan name
    error = _validate_plan_name(plan_name)
    if error:
        return {"error": "invalid_plan_name", "message": error}

    # Validate agent
    if not agent or not agent.strip():
        return {"error": "invalid_agent", "message": "Agent name cannot be empty"}

    # Resolve path
    plan_path = _resolve_plan_path(plan_name, workspace_root)

    # Check file exists
    if not plan_path.exists():
        return {
            "error": "plan_not_found",
            "message": f"Plan not found: {plan_name}",
            "expected_path": str(plan_path.relative_to(workspace_root)),
        }

    # Parse plan
    markdown = plan_path.read_bytes().decode("utf-8")
    plan = parse_plan(markdown)
    plan_dict = plan_to_dict(plan)

    # Check if plan has phases/steps
    if not plan_dict.get("phases"):
        return {
            "error": "not_a_task_plan",
            "message": "This file has no phases or steps.",
        }

    # Determine previous state from the plan dict
    previous_status = "already_pending"
    for phase in plan_dict.get("phases", []):
        for step in phase.get("steps", []):
            if step.get("id", "").upper() == step_id.upper():
                previous_status = "complete" if step.get("done") else "already_pending"
                break

    # Unmark
    updated_markdown, was_unmarked = unmark_step(plan, step_id, agent, reason)

    # Write back if changed
    if was_unmarked:
        plan_path.write_bytes(updated_markdown.encode("utf-8"))

    import json as _json

    return {
        "output": _json.dumps(
            {
                "step_id": step_id,
                "was_unmarked": was_unmarked,
                "previous_status": previous_status,
            }
        ),
        "title": "Unmark Step",
        "metadata": {"target": step_id},
    }


if __name__ == "__main__":
    import json
    import sys

    args = json.loads(sys.stdin.read())
    result = plan_unmark_step(
        plan_name=args["plan_name"],
        step_id=args["step_id"],
        workspace_root=Path(args["workspace_root"]),
        agent=args["agent"],
        reason=args.get("reason"),
    )
    print(json.dumps(result))
