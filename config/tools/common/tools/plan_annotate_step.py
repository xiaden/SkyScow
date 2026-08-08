"""MCP tool: Add or edit an annotation on a plan step without changing completion status."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..helpers.plan_md import annotate_step, parse_plan, plan_to_dict

PLANS_PENDING_DIR = "artifacts/plans/pending"

# Regex for validating annotation marker (single alphanumeric word)
_MARKER_PATTERN = re.compile(r"^[A-Za-z0-9]+$")


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


def _validate_annotation(marker: str, text: str) -> dict[str, str] | None:
    """Validate annotation marker and text. Returns error dict or None if valid."""
    if not marker or not _MARKER_PATTERN.match(marker):
        return {
            "error": "invalid_annotation_marker",
            "message": (
                f"Marker '{marker}' must be a single alphanumeric word (pattern: [A-Za-z0-9]+)"
            ),
        }
    if not text or not text.strip():
        return {"error": "empty_annotation_text", "message": "Annotation text cannot be empty"}
    if "- [" in text:
        return {
            "error": "invalid_annotation_text",
            "message": "Annotation text cannot contain checkbox syntax ('- [')",
        }
    return None


def _validate_op(op: str) -> dict[str, str] | None:
    """Validate operation. Returns error dict or None if valid."""
    if op not in ("add", "edit"):
        return {
            "error": "invalid_op",
            "message": f"op must be 'add' or 'edit', got '{op}'",
        }
    return None


def plan_annotate_step(
    plan_name: str,
    step_id: str,
    op: str,
    workspace_root: Path,
    annotation_marker: str,
    annotation_text: str,
) -> dict[str, Any]:
    """Add or edit an annotation on a plan step without changing its completion status.

    Args:
        plan_name: Plan name (with or without .md extension).
        step_id: Step ID in P<n>-S<m> format (e.g., "P1-S3").
        op: "add" to append or "edit" to replace.
        workspace_root: Workspace root path (injected by MCP server).
        annotation_marker: Marker for the annotation (e.g., "Notes", "Blocked", "Warning").
        annotation_text: The annotation text.

    Returns:
        Response with step_id, op, and annotation_written.

    """
    # Validate plan name
    error = _validate_plan_name(plan_name)
    if error:
        return {"error": "invalid_plan_name", "message": error}

    # Validate op
    op_error = _validate_op(op)
    if op_error:
        return op_error

    # Validate annotation
    ann_error = _validate_annotation(annotation_marker, annotation_text)
    if ann_error:
        return ann_error

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

    # Apply annotation
    updated_markdown, annotation_written = annotate_step(
        plan, step_id, op, annotation_text, annotation_marker
    )

    # Write back if changed
    if annotation_written:
        plan_path.write_bytes(updated_markdown.encode("utf-8"))

    import json as _json

    return {
        "output": _json.dumps(
            {
                "step_id": step_id,
                "op": op,
                "annotation_written": annotation_written,
                "marker": annotation_marker,
            }
        ),
        "title": "Annotate Step",
        "metadata": {"target": step_id},
    }


if __name__ == "__main__":
    import json
    import sys

    args = json.loads(sys.stdin.read())
    result = plan_annotate_step(
        plan_name=args["plan_name"],
        step_id=args["step_id"],
        op=args["op"],
        workspace_root=Path(args["workspace_root"]),
        annotation_marker=args["annotation_marker"],
        annotation_text=args["annotation_text"],
    )
    print(json.dumps(result))
