"""Policy loading and model-selection contracts for the context budget tool.

Owns two responsibilities:

1. Loading ``config/agent-context-budgets.yaml`` — the single shipped policy
   source. Resolution order (first hit wins):
     1. ``HOLYCODE_CONTEXT_BUDGET_POLICY`` environment override (testing).
     2. ``<workspace_root>/config/agent-context-budgets.yaml`` (repo layout).
     3. ``~/.config/opencode/agent-context-budgets.yaml`` (installed image
        layout).
     4. Built-in defaults (identical to the shipped file values).

   Absent or malformed policy never raises: it resolves to the built-in
   defaults plus a diagnostic. Agent frontmatter is never consulted for
   policy; custom ``context_budget:`` frontmatter blocks are ignored.

2. Deterministic model-to-tokenizer selection. Only allowlisted model
   identifiers select a supported tokenizer; unknown, missing, mixed, or
   unsafe model metadata falls back to ``DS_V4_F_0731``. Model metadata is
   read strictly from the frontmatter block of supplied agent markdown files
   via ``frontmatter_model`` — never by executing or interpreting arbitrary
   markdown/config content.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - environment always ships PyYAML
    _yaml = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "DS_V4_F_0731"

# Allowlisted model identifiers -> supported tokenizer. Only models whose
# tokenizer behavior is verified belong here. gpt-5.6-luna is intentionally
# absent (unverified), so agents declaring it deterministically fall back.
MODEL_TOKENIZER_MAP: dict[str, str] = {
    "omniroute/opencode-go/deepseek-v4-flash": "DS_V4_F_0731",
}

DEFAULT_POLICY: dict[str, Any] = {
    "model": DEFAULT_MODEL,
    "worker_phase_limit": 48_000,
    "manager_operational_limit": 96_000,
    "physical_limit": 128_000,
    "worker_return_tokens": 8_000,
    "fixer_return_tokens": 8_000,
    "qa_return_tokens": 12_000,
    "phase_reread_tokens": 8_000,
    "correction_multiplier": 3,
}

# Keys that must be positive integers in the policy file.
_INTEGER_KEYS = (
    "worker_phase_limit",
    "manager_operational_limit",
    "physical_limit",
    "worker_return_tokens",
    "fixer_return_tokens",
    "qa_return_tokens",
    "phase_reread_tokens",
    "correction_multiplier",
)

POLICY_FILE_NAME = "agent-context-budgets.yaml"
POLICY_ENV_VAR = "HOLYCODE_CONTEXT_BUDGET_POLICY"

# Allowlist for frontmatter ``model:`` values: identifiers only, no quoting,
# no whitespace, no interpolation. Anything else is untrusted and ignored.
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_FRONTMATTER_MODEL_RE = re.compile(r"^\s*model\s*:\s*(.+?)\s*$", re.MULTILINE)


def policy_candidates(workspace_root: Path) -> list[tuple[str, Path]]:
    """Ordered (source_label, path) policy candidates, most preferred first."""
    candidates: list[tuple[str, Path]] = []
    env_override = os.environ.get(POLICY_ENV_VAR)
    if env_override:
        candidates.append(("env", Path(env_override)))
    candidates.append(
        ("workspace", workspace_root.resolve() / "config" / POLICY_FILE_NAME)
    )
    candidates.append(("home", Path.home() / ".config" / "opencode" / POLICY_FILE_NAME))
    return candidates


def load_policy(
    workspace_root: Path | str | None = None,
    policy_path: Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and validate the context budget policy.

    Args:
        workspace_root: Workspace root used to locate the shipped policy file.
            May be None, in which case only the env override, home layout, and
            defaults are considered.
        policy_path: Explicit policy path. When given, it is the only file
            consulted (used by tests); otherwise the standard candidate chain
            applies.

    Returns:
        ``(policy, diagnostics)`` where ``policy`` is a validated dict
        containing exactly the ``DEFAULT_POLICY`` keys (merged over any
        present file values) and ``diagnostics`` describes the source and any
        warnings. Never raises for missing or malformed files.

    Raises:
        ValueError: If ``policy_path`` is given but does not exist.
    """
    policy = dict(DEFAULT_POLICY)
    diagnostics: dict[str, Any] = {"source": "defaults", "warnings": []}

    candidates = [("explicit", Path(policy_path))] if policy_path is not None else policy_candidates(
        Path(workspace_root) if workspace_root is not None else Path.cwd()
    )
    source_label: str | None = None
    source_path: Path | None = None
    for label, candidate in candidates:
        if candidate.is_file():
            source_label, source_path = label, candidate
            break
    if policy_path is not None and source_path is None:
        raise ValueError(f"Policy file not found: {policy_path}")
    if source_path is None:
        diagnostics["warnings"].append(
            "no policy file found in candidates; using built-in defaults"
        )
        return policy, diagnostics
    diagnostics["source"] = (
        str(source_path.resolve()) if policy_path is not None else source_label
    )

    if _yaml is None:  # pragma: no cover
        diagnostics["source"] = "defaults"
        diagnostics["warnings"].append("PyYAML unavailable; using built-in defaults")
        return policy, diagnostics

    try:
        raw = _yaml.safe_load(source_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - malformed policy must not raise
        diagnostics["source"] = "defaults"
        diagnostics["warnings"].append(f"malformed policy file: {exc}")
        return policy, diagnostics

    if not isinstance(raw, dict):
        diagnostics["source"] = "defaults"
        diagnostics["warnings"].append("policy file must contain a mapping")
        return policy, diagnostics

    for key in _INTEGER_KEYS:
        if key in raw:
            value = raw[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                diagnostics["warnings"].append(
                    f"invalid {key}={value!r}; using default {policy[key]}"
                )
            else:
                policy[key] = value
    if "model" in raw and isinstance(raw["model"], str) and _MODEL_RE.match(raw["model"]):
        policy["model"] = raw["model"]

    diagnostics["source"] = (
        str(source_path.resolve()) if policy_path is not None else source_label
    )
    return policy, diagnostics


def frontmatter_model(content: str) -> str | None:
    """Extract a trusted ``model:`` value from the frontmatter block.

    Only the leading frontmatter block (delimited by the first two ``---``
    lines) is considered. Malformed, quoted, whitespace-containing, or
    otherwise untrusted values return None (fallback behavior).

    Args:
        content: Full text of a candidate agent markdown file.

    Returns:
        The model identifier when a trusted value is present, else None.
    """
    if not content.startswith("---"):
        return None
    closing = content.find("\n---", 3)
    if closing == -1:
        return None
    frontmatter = content[3:closing]
    match = _FRONTMATTER_MODEL_RE.search(frontmatter)
    if match is None:
        return None
    value = match.group(1).strip()
    if not _MODEL_RE.match(value):
        return None
    return value


def select_tokenizer_model(agent_models: list[str | None]) -> str:
    """Select the tokenizer model for a set of agent model declarations.

    Rules (deterministic):
    - Exactly one distinct allowlisted model -> that tokenizer.
    - Zero allowlisted models, or several distinct allowlisted models
      (mixed), or any unsafe declaration -> ``DEFAULT_MODEL`` fallback.

    Args:
        agent_models: Model identifiers extracted from agent frontmatter
            (None for files without a trusted value).

    Returns:
        Tokenizer identifier, always one of ``MODEL_TOKENIZER_MAP`` values or
        ``DEFAULT_MODEL``.
    """
    known = {MODEL_TOKENIZER_MAP[model] for model in agent_models if model in MODEL_TOKENIZER_MAP}
    if len(known) == 1:
        return next(iter(known))
    return DEFAULT_MODEL
