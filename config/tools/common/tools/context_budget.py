"""Measure supplied files and project worker/manager context budgets.

Production-hardened entry point for the ``context_budget`` MCP tool.

Contracts
---------
- **Files-only input.** ``files`` is a non-empty list of
  ``{path, start_line, end_line}`` objects. Unknown top-level keys, non-string
  paths, non-positive or inverted line ranges, traversal attempts, and
  unreadable files are rejected with stable compact errors. No other input
  shape is accepted; there is no policy or metadata injection channel.
- **Model metadata from frontmatter only.** Agent markdown files (path
  contains an ``agents`` segment and ends in ``.md``) contribute their
  frontmatter ``model:`` value through ``budget_policy.frontmatter_model``.
  Model selection is allowlisted with a deterministic ``DS_V4_F_0731``
  fallback (see ``budget_policy.select_tokenizer_model``).
- **Structured plan parsing.** Files whose path contains a ``plans`` segment
  and end in ``.md`` are parsed with ``plan_md.parse_plan`` over their full
  content (the requested range is ignored for parsing). Explicit phases must
  be sequentially numbered starting at 1 and each contain at least one usable
  flat step; violations yield ``plan_validation`` errors. A plan with no
  explicit phases falls back to worker-limit phase estimation.
- **Fixed policy.** All limits come from the shipped
  ``config/agent-context-budgets.yaml`` via ``budget_policy.load_policy``.
  Agent frontmatter is never consulted for policy.
- **Compact output.** Stable JSON keys, bounded titles and error messages,
  per-phase measurements, and normal/worst-case manager projections. Raw file
  contents, agent frontmatter bodies, and policy file text are never emitted.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from ..helpers.budget_policy import frontmatter_model, load_policy, select_tokenizer_model
from ..helpers.file_helpers import resolve_file_path
from ..helpers.plan_md import parse_plan
from ..helpers.tokenizer_helpers import (
    assemble_sections,
    load_tokenizers,
    read_subsection,
    weighted_tokens,
)

_ALLOWED_ENTRY_KEYS = frozenset({"path", "start_line", "end_line"})
_MESSAGE_LIMIT = 300
_TITLE_LIMIT = 120


def _error(error: str, message: str) -> dict[str, str]:
    message = str(message)
    if len(message) > _MESSAGE_LIMIT:
        message = message[:_MESSAGE_LIMIT] + "..."
    return {"error": error, "message": message}


def _bounded_title(title: str) -> str:
    title = title.strip()
    if len(title) > _TITLE_LIMIT:
        return title[:_TITLE_LIMIT] + "..."
    return title


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 1:
        return None
    return value


def _has_dir_segment(resolved: Path, segment: str) -> bool:
    return segment in resolved.parts


def _is_plan_file(resolved: Path) -> bool:
    return resolved.suffix == ".md" and _has_dir_segment(resolved, "plans")


def _is_agent_file(resolved: Path) -> bool:
    return resolved.suffix == ".md" and _has_dir_segment(resolved, "agents")


def _read_full(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _phase_scopes(raw_lines: list[str], heading_lines: list[int]) -> list[str]:
    """Slice raw plan lines into per-phase content scopes.

    ``heading_lines`` are 1-based heading line numbers; scopes run from each
    heading up to the next heading (or end of file).
    """
    scopes: list[str] = []
    for index, heading in enumerate(heading_lines):
        start = heading - 1
        end = heading_lines[index + 1] - 1 if index + 1 < len(heading_lines) else len(
            raw_lines
        )
        scopes.append("".join(raw_lines[start:end]))
    return scopes


def _count_tokens(tokenizers: tuple[Any, Any], model: str, text: str) -> int:
    if model == "o200k":
        return len(tokenizers[0].encode(text, disallowed_special=()))
    return len(tokenizers[1].encode(text, add_special_tokens=False).ids)


def _validate_explicit_phases(plan: Any, plan_path: Path) -> dict[str, str] | None:
    """Return a compact error when explicit phases are not usable."""
    numbers = [phase.number for phase in plan.phases]
    if numbers != list(range(1, len(numbers) + 1)):
        return _error(
            "plan_validation",
            f"{plan_path}: phase numbers must be sequential starting at 1 "
            f"(got {numbers})",
        )
    for phase in plan.phases:
        if not phase.steps:
            return _error(
                "plan_validation",
                f"{plan_path}: phase {phase.number} ({phase.title}) has no steps",
            )
    return None


def _analyze_plan(
    plan_path: Path,
    content: str,
    tokenizers: tuple[Any, Any],
    model: str,
    worker_phase_limit: int,
) -> tuple[dict[str, str] | None, int, list[dict[str, Any]]]:
    """Parse and validate a plan; return (error, phase_count, phases_detail)."""
    try:
        plan = parse_plan(content)
    except (ValueError, ImportError) as exc:
        return _error("plan_parse", f"{plan_path}: {exc}"), 0, []

    validation_error = _validate_explicit_phases(plan, plan_path)
    if validation_error is not None:
        return validation_error, 0, []

    if not plan.phases:
        return None, 0, []

    scopes = _phase_scopes(plan.raw_lines, [phase.heading_line for phase in plan.phases])
    detail: list[dict[str, Any]] = []
    for phase, scope in zip(plan.phases, scopes):
        phase_tokens = _count_tokens(tokenizers, model, scope)
        detail.append(
            {
                "plan": plan_path.name,
                "number": phase.number,
                "title": _bounded_title(phase.title),
                "tokens": phase_tokens,
                "within_worker_limit": phase_tokens <= worker_phase_limit,
                "steps": len(phase.steps),
                "complete_steps": sum(1 for step in phase.steps if step.checked),
            }
        )
    return None, len(plan.phases), detail


def _build_planning(
    policy: dict[str, Any],
    weighted: int,
    phases: int,
    explicit_phases: bool,
    phases_detail: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute minimums, projections, and status from the fixed policy."""
    worker_limit = policy["worker_phase_limit"]
    operational_limit = policy["manager_operational_limit"]
    physical_limit = policy["physical_limit"]
    multiplier = policy["correction_multiplier"]

    overhead = (
        policy["phase_reread_tokens"]
        + policy["worker_return_tokens"]
        + policy["qa_return_tokens"]
    )
    minimum_phases = max(1, math.ceil(weighted / worker_limit))
    normal = weighted + phases * overhead
    worst = weighted + phases * overhead * multiplier
    minimum_plans = max(1, math.ceil(worst / operational_limit))

    if worst > physical_limit:
        status = "PHYSICAL_LIMIT_EXCEEDED"
    elif worst > operational_limit:
        status = "SPLIT_REQUIRED"
    else:
        status = "VALID"

    return {
        "phases": phases,
        "explicit_phases": explicit_phases,
        "phases_detail": phases_detail,
        "minimum_phases": minimum_phases,
        "minimum_plans": minimum_plans,
        "normal_manager_tokens": normal,
        "worst_case_manager_tokens": worst,
        "status": status,
    }


def context_budget(files: list[dict[str, Any]], workspace_root: Path) -> dict[str, Any]:
    """Measure supplied files and project worker/manager context budgets.

    Args:
        files: Non-empty list of ``{path, start_line, end_line}`` entries.
        workspace_root: Workspace root; all paths resolve inside it.

    Returns:
        A compact JSON-serializable result, or a stable ``{error, message}``
        object.
    """
    if not isinstance(files, list) or not files:
        return _error("invalid_files", "files must be a non-empty array")

    workspace_root = workspace_root.resolve()
    policy, policy_diagnostics = load_policy(workspace_root)

    sections: list[str] = []
    resolved_paths: set[Path] = set()
    plan_files: list[tuple[Path, str]] = []
    agent_models: list[str | None] = []

    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            return _error("invalid_file", f"files[{index}] must be an object")

        unsupported = set(entry) - _ALLOWED_ENTRY_KEYS
        if unsupported:
            return _error(
                "invalid_file",
                f"files[{index}] has unsupported keys: {sorted(unsupported)}",
            )

        file_path = entry.get("path")
        start_line = _integer(entry.get("start_line"))
        end_line = _integer(entry.get("end_line"))
        if not isinstance(file_path, str) or not file_path.strip():
            return _error("invalid_file", f"files[{index}].path must be non-empty")
        if start_line is None or end_line is None:
            return _error(
                "invalid_line_range",
                f"files[{index}] start_line and end_line must be positive integers",
            )
        if end_line < start_line:
            return _error(
                "invalid_line_range",
                f"files[{index}].end_line must be >= start_line",
            )

        resolved = resolve_file_path(file_path, workspace_root)
        if isinstance(resolved, dict):
            return _error("invalid_file", resolved.get("error", "Invalid file path"))
        resolved_paths.add(resolved)

        try:
            if _is_plan_file(resolved):
                content = _read_full(resolved)
                plan_files.append((resolved, content))
                sections.append(content)
            else:
                sections.append(read_subsection(resolved, start_line, end_line))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return _error("read_error", f"{file_path}: {exc}")

        if _is_agent_file(resolved):
            try:
                agent_models.append(frontmatter_model(_read_full(resolved)))
            except (OSError, UnicodeDecodeError):
                agent_models.append(None)

    source = assemble_sections(sections)
    model = select_tokenizer_model(agent_models)

    try:
        tokenizers = load_tokenizers()
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _error("tokenizer_error", str(exc))
    source_tokens = _count_tokens(tokenizers, model, source)
    weighted = weighted_tokens(source_tokens, len(sections), len(resolved_paths))

    explicit_phases = False
    phases = 0
    phases_detail: list[dict[str, Any]] = []

    if plan_files:
        for plan_path, content in plan_files:
            error, plan_phase_count, plan_detail = _analyze_plan(
                plan_path, content, tokenizers, model, policy["worker_phase_limit"]
            )
            if error is not None:
                return error
            if plan_phase_count:
                explicit_phases = True
                phases += plan_phase_count
                phases_detail.extend(plan_detail)

    if not explicit_phases:
        # Worker-limit fallback: estimate phases when the input carries no
        # explicit plan structure.
        phases = max(1, math.ceil(weighted / policy["worker_phase_limit"]))

    planning = _build_planning(
        policy, weighted, phases, explicit_phases, phases_detail
    )

    return {
        "model": model,
        "measured": {
            "source_tokens": source_tokens,
            "weighted_tokens": weighted,
        },
        "planning": planning,
        "policy": {
            "source": policy_diagnostics["source"],
            "worker_phase_limit": policy["worker_phase_limit"],
            "manager_operational_limit": policy["manager_operational_limit"],
            "physical_limit": policy["physical_limit"],
            "worker_return_tokens": policy["worker_return_tokens"],
            "fixer_return_tokens": policy["fixer_return_tokens"],
            "qa_return_tokens": policy["qa_return_tokens"],
            "phase_reread_tokens": policy["phase_reread_tokens"],
            "correction_multiplier": policy["correction_multiplier"],
        },
    }


if __name__ == "__main__":
    arguments = json.loads(input())
    result = context_budget(
        files=arguments.get("files"),
        workspace_root=Path(arguments["workspace_root"]),
    )
    print(json.dumps(result, separators=(",", ":")))
