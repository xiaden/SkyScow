"""Validated, writer-isolated durable QA round records.

Field contract for a terminal QA round record:

- ``task_family``: existing task-family identity (never minted here).
- ``round``: positive integer QA round number.
- ``writer``: one of ``qa-test-generator``, ``qa-docs-generator``, ``exec-fixer``.
- ``agent``: non-empty valid agent name that produced the record.
- ``subject``: stable single-finding identity. A string, or an object whose
  ``kind`` plus at least one of ``file``/``module``/``symbol``/``contract``/
  ``behavior``/``interface`` is populated.
- ``decision``: ``REPAIRED``, ``UNNECESSARY``, ``BLOCKED``, or ``ESCALATED``
  for generators; ``exec-fixer`` may write only ``REPAIRED``.
- ``evidence``: repository-derived evidence (required).
- ``verification``: actual verification performed (required).
- ``changed_files``/``changed_symbols``: lists of non-empty strings; they may
  be empty only for a no-change outcome, and ``REPAIRED`` requires at least one
  changed file or symbol.
- ``source_kind``/``source_ref``: explicit provenance. Generators require
  ``analyzer-finding``; ``exec-fixer`` requires ``fixer-issue``. ``source_ref``
  is a non-empty stable finding/issue reference.
- ``repair``: required repair text for ``exec-fixer`` records.

Stable record identity is ``(task_family, round, writer, stable subject
identity)``. A repeated identity is rejected fail-closed on read and on write,
while distinct findings, distinct writers, and independent writer concurrency
remain allowed. Missing history is empty history. Progress, chain-of-thought,
speculation, and analyzer-never-produced findings are rejected.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .log_jsonl import validate_agent_name

LOGS_DIR = "artifacts/logs"
QA_ROUNDS_DIR = "qa-rounds"
WRITERS = frozenset({"qa-test-generator", "qa-docs-generator", "exec-fixer"})
GENERATOR_DECISIONS = frozenset({"REPAIRED", "UNNECESSARY", "BLOCKED", "ESCALATED"})
SAFE_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
FORBIDDEN_KEYS = frozenset({"progress", "thoughts", "chain_of_thought", "speculation"})
SUBJECT_IDENTITY_KEYS = ("kind", "file", "module", "symbol", "contract", "behavior", "interface")
# A subject object is a kind plus at least one identifying descriptor; a
# kind-only subject is too weak to distinguish two same-kind findings.
SUBJECT_DESCRIPTOR_KEYS = ("file", "module", "symbol", "contract", "behavior", "interface")
SOURCE_KINDS = {"analyzer-finding", "fixer-issue"}


def _populated_subject_keys(subject: dict[str, Any]) -> tuple[str, ...]:
    """Return populated identifying keys of a subject object in fixed order."""
    return tuple(
        key
        for key in SUBJECT_IDENTITY_KEYS
        if isinstance(subject.get(key), str) and subject[key].strip()
    )


def _require_subject_object(subject: dict[str, Any]) -> tuple[str, ...]:
    """Require a non-empty ``kind`` plus one other identifying descriptor."""
    populated = _populated_subject_keys(subject)
    if "kind" not in populated or not any(
        key in populated for key in SUBJECT_DESCRIPTOR_KEYS
    ):
        raise ValueError(
            "subject must have a kind and at least one identifying key"
        )
    return populated


def resolve_task_family(*, dd_family: str = "", plan_set_family: str = "", standalone: str = "", task_family: str = "") -> str:
    """Select an existing task-family identity, never manufacturing one.

    Resolution precedence is ``dd_family``, then ``plan_set_family``, then
    ``task_family``, then ``standalone``; the first non-empty stripped value
    wins.

    Args:
        dd_family: Design-document family candidate.
        plan_set_family: Plan-set family candidate.
        standalone: Standalone family candidate.
        task_family: Task family candidate.

    Returns:
        The stripped selected identity.

    Raises:
        ValueError: If no non-empty candidate is supplied.
    """
    for value in (dd_family, plan_set_family, task_family, standalone):
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError("an existing task-family identity is required")


def safe_key(value: str, label: str = "key") -> str:
    """Normalize and validate a path-safe family or writer key.

    Surrounding whitespace is removed. Empty values, ``.``/``..``, and values
    containing characters outside the safe key pattern are rejected so the key
    cannot escape its intended artifact namespace.

    Args:
        value: Candidate key to normalize.
        label: Name used in the validation error message.

    Returns:
        The stripped, path-safe key.

    Raises:
        ValueError: If the stripped value is empty, a traversal marker, or
            contains an unsafe character.
    """
    value = value.strip()
    if not value or value in {".", ".."} or not SAFE_PART.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def record_path(workspace_root: Path, task_family: str, round_number: int, writer: str) -> Path:
    """Build the deterministic, writer-isolated QA round-record path.

    Records are stored below ``artifacts/logs/qa-rounds/{family}/round-{N}``;
    each supported writer gets a separate JSONL file rather than sharing a
    sequence or file.

    Args:
        workspace_root: Workspace containing the existing artifacts directory.
        task_family: Existing task-family identity used as the namespace.
        round_number: Positive QA round number.
        writer: One of the supported QA writers.

    Returns:
        The writer-specific JSONL path for the requested family and round.

    Raises:
        ValueError: If a key is unsafe, the writer is unsupported, or the round
            is not a positive integer.
    """
    family = safe_key(task_family, "task family")
    writer = safe_key(writer, "writer")
    if writer not in WRITERS:
        raise ValueError("unsupported writer")
    if isinstance(round_number, bool) or not isinstance(round_number, int) or round_number < 1:
        raise ValueError("round must be a positive integer")
    return workspace_root / LOGS_DIR / QA_ROUNDS_DIR / family / f"round-{round_number}" / f"{writer}.jsonl"


def subject_identity(subject: Any) -> tuple[Any, ...]:
    """Return the stable, hashable identity of a record subject.

    Strings are normalized by stripping whitespace. Objects contribute their
    populated identifying keys in a fixed order so two records describing the
    same finding hash equally regardless of JSON key order.
    """
    if isinstance(subject, str):
        normalized = subject.strip()
        if not normalized:
            raise ValueError("subject cannot be empty")
        return ("text", normalized)
    if isinstance(subject, dict):
        populated = _require_subject_object(subject)
        return ("object", tuple((key, subject[key].strip()) for key in populated))
    raise ValueError("subject must be a string or object")


def record_identity(record: dict[str, Any]) -> tuple[Any, ...]:
    """Return the stable identity ``(task_family, round, writer, subject)``.

    A second terminal record with this identity is a duplicate and must fail
    closed; distinct findings, writers, and rounds remain distinct.
    """
    return (
        record["task_family"],
        record["round"],
        record["writer"],
        subject_identity(record["subject"]),
    )


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a terminal QA round record.

    A record identifies one stable finding with its task family, round, writer,
    agent, subject, repository-derived evidence, actual verification, changed
    files/symbols, and explicit provenance. Generator writers may use
    ``REPAIRED``, ``UNNECESSARY``, ``BLOCKED``, or ``ESCALATED``; ``exec-fixer``
    may write only ``REPAIRED`` and must include the repair performed.
    Progress, chain-of-thought, speculation, and similar non-terminal material
    are rejected.

    Args:
        record: Candidate terminal record object.

    Returns:
        A shallow copy with normalized task-family and writer keys.

    Raises:
        ValueError: If the record is malformed, lacks a stable subject,
            agent, evidence, verification, changed fields, or provenance, uses
            an invalid decision or writer, or contains forbidden
            progress/speculation data.
    """
    if not isinstance(record, dict):
        # The terminal-record contract reject type is ValueError: load_records
        # re-wraps it as "malformed QA history" and the write/read bridges map
        # ValueError to invalid_qa_record, so TypeError would change the contract.
        raise ValueError("record must be an object")  # noqa: TRY004
    if FORBIDDEN_KEYS.intersection(record):
        raise ValueError("progress, speculation, and chain-of-thought are not record data")
    required = {
        "task_family",
        "round",
        "writer",
        "agent",
        "subject",
        "decision",
        "evidence",
        "verification",
        "changed_files",
        "changed_symbols",
        "source_kind",
        "source_ref",
    }
    missing = required - record.keys()
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    family = safe_key(record["task_family"], "task family")
    writer = safe_key(record["writer"], "writer")
    if writer not in WRITERS:
        raise ValueError("unsupported writer")
    round_number = record["round"]
    if isinstance(round_number, bool) or not isinstance(round_number, int) or round_number < 1:
        raise ValueError("round must be a positive integer")
    agent = record["agent"]
    if not isinstance(agent, str):
        # ValueError, not TypeError: the record schema is a fail-closed contract
        # mapped to invalid_qa_record by qa_record_write/qa_record_read.
        raise ValueError("agent must be a string")  # noqa: TRY004
    agent_error = validate_agent_name(agent)
    if agent_error:
        raise ValueError(agent_error)
    subject = record["subject"]
    if isinstance(subject, str):
        if not subject.strip():
            raise ValueError("subject cannot be empty")
    elif isinstance(subject, dict):
        _require_subject_object(subject)
    else:
        # ValueError, not TypeError: the malformed-record contract above.
        raise ValueError("subject must be a string or object")  # noqa: TRY004
    decision = record["decision"]
    allowed = GENERATOR_DECISIONS if writer != "exec-fixer" else frozenset({"REPAIRED"})
    if decision not in allowed:
        raise ValueError("invalid decision for writer")
    if not isinstance(record["evidence"], str) or not record["evidence"].strip():
        raise ValueError("repository-derived evidence is required")
    if not isinstance(record["verification"], str) or not record["verification"].strip():
        raise ValueError("actual verification is required")
    changed_files = record["changed_files"]
    changed_symbols = record["changed_symbols"]
    for field_name, value in (("changed_files", changed_files), ("changed_symbols", changed_symbols)):
        if not isinstance(value, list):
            # ValueError, not TypeError: list-shape failures stay record errors.
            raise ValueError(f"{field_name} must be a list")  # noqa: TRY004
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(f"{field_name} entries must be non-empty strings")
    if decision == "REPAIRED" and not (changed_files or changed_symbols):
        raise ValueError("REPAIRED requires at least one changed file or symbol")
    if decision == "UNNECESSARY" and not record["evidence"].strip():
        raise ValueError("UNNECESSARY requires evidence")
    source_kind = record["source_kind"]
    if source_kind not in SOURCE_KINDS:
        raise ValueError("source_kind must be analyzer-finding or fixer-issue")
    expected_kind = "fixer-issue" if writer == "exec-fixer" else "analyzer-finding"
    if source_kind != expected_kind:
        raise ValueError(f"{writer} records require source_kind '{expected_kind}'")
    source_ref = record["source_ref"]
    if not isinstance(source_ref, str) or not source_ref.strip():
        raise ValueError("source_ref must be a non-empty stable finding or issue reference")
    if writer == "exec-fixer" and not isinstance(record.get("repair"), str | type(None)):
        raise ValueError("fixer repair must be text")
    if writer == "exec-fixer" and not str(record.get("repair", "")).strip():
        raise ValueError("fixer records require repair performed")
    result = dict(record)
    result["task_family"] = family
    result["writer"] = writer
    return result


def load_records(path: Path, *, task_family: str, writer: str) -> list[dict[str, Any]]:
    """Load and strictly validate one writer's QA record history.

    A missing file represents empty history. Existing lines must each satisfy
    the terminal record schema and match the requested task family and writer;
    malformed, duplicate-identity, cross-family, or writer-mismatched history
    fails closed.

    Args:
        path: Writer-isolated JSONL history file.
        task_family: Expected existing task-family identity.
        writer: Expected writer for this history file.

    Returns:
        Validated records in file order, or an empty list when the file is absent.

    Raises:
        ValueError: If the file cannot be parsed, a record is invalid, a stable
            record identity repeats, or any record belongs to another family or
            writer.
    """
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            checked = validate_record(obj)
            if checked["task_family"] != task_family or checked["writer"] != writer:
                raise ValueError("cross-family or writer-mismatched history")
            identity = record_identity(checked)
            if identity in seen:
                raise ValueError("duplicate record identity")
            seen.add(identity)
            records.append(checked)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError(f"malformed QA history: {exc}") from exc
    return records
