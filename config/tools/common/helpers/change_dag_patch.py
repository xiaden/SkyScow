"""Custom in-Python unified-diff parsing and application for Change DAG edits.

Safety-critical: this module never shells out to ``patch`` / ``git apply`` and
never uses ``file_helpers.atomic_write`` (which is a plain non-atomic
``write_bytes``). Patches are applied with exact context and zero fuzz; EOL
style is detected and preserved; per-file replacement is atomic via
``mkstemp`` + flush + ``fsync`` + ``os.replace``.

Line numbers in a unified diff always refer to the LF-normalized original text.
"""
from __future__ import annotations

import difflib
import os
import re
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "PatchError",
    "PatchContextError",
    "Hunk",
    "FilePatch",
    "detect_eol",
    "normalize_eol",
    "parse_unified_diff",
    "validate_hunk_ranges",
    "apply_file_patch",
    "apply_patches",
    "atomic_replace",
    "read_text_preserving",
    "apply_structured_replacements",
    "generate_unified_diff",
]

_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_BINARY_PROBE_BYTES = 8192


class PatchError(Exception):
    """Base class for patch parse/application failures."""


class StructuredReplacementError(PatchError):
    """A structured exact replacement cannot be applied."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class PatchContextError(PatchError):
    """A context/removed line did not exactly match the target text."""

    def __init__(self, path: str, hunk_index: int, message: str) -> None:
        super().__init__(message)
        self.path = path
        self.hunk_index = hunk_index
        self.message = message


def apply_structured_replacements(text: str, replacements: object) -> str:
    """Apply ordered, zero-fuzz exact replacements to ``text``.

    Each ``old`` value must be a non-empty string occurring exactly once in the
    text produced by the preceding replacement.  The returned text is the
    worker's desired self-view; no diff syntax is accepted here.
    """
    if not isinstance(replacements, list) or not replacements:
        raise StructuredReplacementError(
            "invalid_replacements", "replacements must be a non-empty array"
        )
    current = text
    for index, replacement in enumerate(replacements):
        if not isinstance(replacement, dict):
            raise StructuredReplacementError(
                "invalid_replacements", f"replacement {index} must be an object"
            )
        old = replacement.get("old")
        new = replacement.get("new")
        if not isinstance(old, str) or not old:
            raise StructuredReplacementError(
                "invalid_replacements", f"replacement {index}.old must be a non-empty string"
            )
        if not isinstance(new, str):
            raise StructuredReplacementError(
                "invalid_replacements", f"replacement {index}.new must be a string"
            )
        count = current.count(old)
        if count == 0:
            raise StructuredReplacementError(
                "edit_context_missing", f"replacement {index}.old was not found"
            )
        if count != 1:
            raise StructuredReplacementError(
                "edit_context_ambiguous",
                f"replacement {index}.old occurs {count} times; expected exactly once",
            )
        current = current.replace(old, new, 1)
    if current == text:
        raise StructuredReplacementError(
            "edit_no_change", "structured replacements produce no change"
        )
    return current


def _diff_lines(text: str) -> list[str]:
    """LF-normalized lines matching the patch parser's coordinate model."""
    lines = normalize_eol(text).split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def generate_unified_diff(base: str, desired: str, path: str) -> str:
    """Generate and self-validate one canonical internal edit patch."""
    if not isinstance(path, str) or not path:
        raise PatchError("edit path must be a non-empty string")
    diff = difflib.unified_diff(
        _diff_lines(base),
        _diff_lines(desired),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="\n",
    )
    patch = "".join(line if line.endswith("\n") else line + "\n" for line in diff)
    if not patch:
        raise PatchError("generated diff is empty")
    parsed = parse_unified_diff(patch)
    if len(parsed) != 1 or parsed[0].path != path:
        raise PatchError("generated diff target does not match declared path")
    validate_hunk_ranges(parsed[0], path=path)
    if apply_patches(base, parsed, path=path) != desired:
        raise PatchError("generated diff does not round-trip to desired content")
    return patch


def detect_eol(text: str) -> str:
    """Return ``"\\r\\n"`` when the text contains CRLF, else ``"\\n"``."""
    return "\r\n" if "\r\n" in text else "\n"


def normalize_eol(text: str) -> str:
    """Convert all CRLF/CR line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


@dataclass
class Hunk:
    """One ``@@`` hunk. ``lines`` are raw body lines including the marker."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str] = field(default_factory=list)


@dataclass
class FilePatch:
    """A single-file unified diff (one ``---``/``+++`` pair plus hunks)."""

    path: str
    hunks: list[Hunk] = field(default_factory=list)


def _derive_path(header: str) -> str:
    """Derive a workspace path from a ``+++`` header, stripping one a/ b/."""
    value = header.split("\t", 1)[0].strip()
    if value in {"a/", "b/"}:
        return value
    if value.startswith("a/") or value.startswith("b/"):
        return value[2:]
    return value


def _parse_hunk(lines: list[str], index: int, path: str) -> tuple[Hunk, int]:
    header = lines[index]
    match = _HUNK_HEADER_RE.match(header)
    if match is None:
        raise PatchError(f"malformed hunk header in {path or 'patch'}: {header!r}")
    old_start = int(match.group(1))
    old_count = int(match.group(2)) if match.group(2) is not None else 1
    new_start = int(match.group(3))
    new_count = int(match.group(4)) if match.group(4) is not None else 1
    body: list[str] = []
    old_seen = 0
    new_seen = 0
    cursor = index + 1
    total = len(lines)
    while cursor < total and (old_seen < old_count or new_seen < new_count):
        line = lines[cursor]
        if line == "" and cursor == total - 1:
            break
        if line.startswith("\\"):
            raise PatchError(f"unsupported '\\ No newline' marker in {path or 'patch'}")
        marker = line[:1]
        if marker == " ":
            body.append(line)
            old_seen += 1
            new_seen += 1
        elif marker == "-":
            body.append(line)
            old_seen += 1
        elif marker == "+":
            body.append(line)
            new_seen += 1
        else:
            raise PatchError(
                f"malformed hunk body line in {path or 'patch'}: {line!r}"
            )
        cursor += 1
    if old_seen != old_count or new_seen != new_count:
        raise PatchError(
            f"hunk line counts do not match header in {path or 'patch'}: "
            f"expected -{old_count}/+{new_count}, got -{old_seen}/+{new_seen}"
        )
    hunk = Hunk(old_start, old_count, new_start, new_count, body)
    return hunk, cursor


def validate_hunk_ranges(file_patch: FilePatch, *, path: str = "") -> None:
    """Reject hunks whose original-coordinate ranges overlap.

    Every hunk is mapped to a 0-based half-open interval over the *original*
    (pre-patch) text:

    * ``old_count > 0`` occupies ``[old_start - 1, old_start - 1 + old_count)``.
    * ``old_count == 0`` is a pure insertion anchored after original line
      ``old_start``; it is modeled as the empty interval
      ``[old_start, old_start)``.

    Consecutive hunks must be non-overlapping, i.e. ``next_start >=
    previous_end``. That permits adjacent hunks (``next_start == previous_end``)
    and a zero-``old_count`` insertion exactly at a previous hunk's boundary,
    while rejecting a hunk that claims original text produced by an earlier hunk
    of the same patch (an original-coordinate dependency). This is the single
    gate that keeps preview-time composition and apply-time application from
    disagreeing. Raises :class:`PatchError` naming the path and both indexes.

    Two pure insertions (``old_count == 0``) at the *same* anchor are also
    rejected: their relative order is undefined, and preview composition and
    application would otherwise order them oppositely. ``apply_file_patch`` must
    never write a result the compiler cannot reproduce byte-for-byte. This
    mirrors the same-anchor rule in
    :func:`change_dag_compiler_reconcile._spans_conflict`.

    Descending hunks are not treated as an overlap here; they are left to the
    ascending-order check in :func:`apply_file_patch` so the semantics for
    out-of-order patches are unchanged (a repeated insertion anchor is unordered
    regardless of hunk order, so it is rejected here first).
    """
    effective_path = path or file_patch.path
    previous_index: int | None = None
    previous_end = 0
    insertion_anchors: dict[int, int] = {}
    for index, hunk in enumerate(file_patch.hunks):
        if hunk.old_count == 0:
            start = hunk.old_start
            end = hunk.old_start
            earlier = insertion_anchors.get(hunk.old_start)
            if earlier is not None:
                raise PatchError(
                    f"duplicate insertion anchor in {effective_path}: hunk {earlier} "
                    f"and hunk {index} both insert at old_start={hunk.old_start}; "
                    f"same-anchor pure insertions have no defined order"
                )
            insertion_anchors[hunk.old_start] = index
        else:
            start = hunk.old_start - 1
            end = hunk.old_start - 1 + hunk.old_count
        if previous_index is not None:
            previous = file_patch.hunks[previous_index]
            if hunk.old_start < previous.old_start:
                return
            if start < previous_end:
                raise PatchError(
                    f"overlapping hunks in {effective_path}: hunk {previous_index} "
                    f"(old_start={previous.old_start}, old_count={previous.old_count}) "
                    f"and hunk {index} (old_start={hunk.old_start}, "
                    f"old_count={hunk.old_count}) overlap in original coordinates"
                )
        previous_index = index
        previous_end = end


def parse_unified_diff(patch: str) -> list[FilePatch]:
    """Parse a standard unified diff into one :class:`FilePatch` per file.

    Supports ``--- a/x`` / ``+++ b/x`` and bare ``--- x`` / ``+++ x`` headers.
    Raises :class:`PatchError` on malformed input.
    """
    if not isinstance(patch, str):
        raise PatchError("patch must be a string")
    lines = normalize_eol(patch).split("\n")
    files: list[FilePatch] = []
    index = 0
    total = len(lines)
    while index < total:
        line = lines[index]
        if line == "" and index == total - 1:
            break
        if not line.startswith("--- "):
            raise PatchError(f"expected '--- ' file header, found: {line!r}")
        if index + 1 >= total or not lines[index + 1].startswith("+++ "):
            raise PatchError("missing '+++ ' header after '--- ' header")
        path = _derive_path(lines[index + 1][4:])
        if not path:
            raise PatchError("empty path in '+++ ' header")
        cursor = index + 2
        hunks: list[Hunk] = []
        while cursor < total and lines[cursor].startswith("@@ "):
            hunk, cursor = _parse_hunk(lines, cursor, path)
            hunks.append(hunk)
        if not hunks:
            raise PatchError(f"file patch has no hunks: {path}")
        file_patch = FilePatch(path=path, hunks=hunks)
        validate_hunk_ranges(file_patch, path=path)
        files.append(file_patch)
        index = cursor
    if not files:
        raise PatchError("patch contains no file headers")
    return files


def _split_for_apply(text: str) -> tuple[list[str], bool]:
    """Split LF text into lines, dropping the synthetic trailing empty line."""
    trailing = text.endswith("\n")
    lines = text.split("\n")
    if trailing:
        lines = lines[:-1]
    return lines, trailing


def apply_file_patch(original: str, file_patch: FilePatch, *, path: str = "") -> str:
    """Apply one :class:`FilePatch` to ``original`` with exact context.

    All hunks are applied in order, each rebased by the net line delta of the
    previously applied hunks. Any context/removed line that does not match
    exactly raises :class:`PatchContextError`. The detected EOL of ``original``
    is restored on the result.
    """
    effective_path = path or file_patch.path
    eol = detect_eol(original)
    normalized = normalize_eol(original)
    lines, trailing = _split_for_apply(normalized)
    validate_hunk_ranges(file_patch, path=effective_path)
    offset = 0
    previous_start: int | None = None
    for hunk_index, hunk in enumerate(file_patch.hunks):
        if previous_start is not None and hunk.old_start < previous_start:
            raise PatchError(
                f"hunks are not in ascending order in {effective_path}: "
                f"{previous_start} then {hunk.old_start}"
            )
        previous_start = hunk.old_start
        # Unified-diff coordinates are 1-based over the original text. A hunk
        # that removes/keeps content starts at index old_start - 1. A hunk with
        # old_count == 0 is a pure insertion anchored *after* original line
        # old_start, i.e. at 0-based index old_start. new_start is a
        # resulting-file coordinate and is deliberately never used here:
        # combining it with the running offset would double-count earlier deltas.
        target = (
            hunk.old_start + offset
            if hunk.old_count == 0
            else hunk.old_start - 1 + offset
        )
        if target < 0:
            raise PatchContextError(
                effective_path, hunk_index, f"hunk {hunk_index} targets a negative line"
            )
        if hunk.old_count == 0 and target > len(lines):
            raise PatchContextError(
                effective_path,
                hunk_index,
                f"hunk {hunk_index} inserts past end of file: target index "
                f"{target} exceeds {len(lines)} lines",
            )
        position = target
        replacement: list[str] = []
        for raw in hunk.lines:
            marker = raw[:1]
            content = raw[1:]
            if marker == " ":
                if position >= len(lines) or lines[position] != content:
                    found = lines[position] if position < len(lines) else "<end of file>"
                    raise PatchContextError(
                        effective_path,
                        hunk_index,
                        f"context mismatch at line {position + 1}: "
                        f"expected {content!r}, found {found!r}",
                    )
                replacement.append(content)
                position += 1
            elif marker == "-":
                if position >= len(lines) or lines[position] != content:
                    found = lines[position] if position < len(lines) else "<end of file>"
                    raise PatchContextError(
                        effective_path,
                        hunk_index,
                        f"removed line mismatch at line {position + 1}: "
                        f"expected {content!r}, found {found!r}",
                    )
                position += 1
            elif marker == "+":
                replacement.append(content)
            else:  # pragma: no cover - parser rejects these
                raise PatchError(f"unsupported hunk line marker: {raw!r}")
        lines[target:position] = replacement
        offset += hunk.new_count - hunk.old_count
    result = "\n".join(lines)
    if trailing:
        result += "\n"
    if eol != "\n":
        result = result.replace("\n", eol)
    return result


def apply_patches(original: str, patches: list[FilePatch], *, path: str = "") -> str:
    """Sequentially apply ``patches``, each interpreted against the evolving text."""
    text = original
    for index, file_patch in enumerate(patches):
        effective_path = path or file_patch.path
        try:
            text = apply_file_patch(text, file_patch, path=effective_path)
        except PatchContextError as exc:
            raise PatchContextError(effective_path, index, exc.message) from exc
    return text


def atomic_replace(path: Path, data: bytes) -> None:
    """Atomically replace ``path`` with ``data`` (mkstemp + fsync + os.replace).

    When ``path`` already exists, its permission bits (including executable bits)
    are copied onto the temporary file before ``os.replace`` so the atomic
    replacement preserves the destination's mode. A create-new replacement keeps
    the ``mkstemp`` default mode; no new create-mode policy is introduced.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing_mode: int | None = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        existing_mode = None
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    replaced = False
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if existing_mode is not None:
            os.chmod(temp_name, existing_mode)
        os.replace(temp_name, path)
        replaced = True
    finally:
        if not replaced:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def read_text_preserving(path: Path) -> str:
    """Read UTF-8 text without universal-newline translation.

    Raises :class:`PatchError` when the file is missing, undecodable, or looks
    binary (a NUL byte in the first 8 KiB).
    """
    path = Path(path)
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise PatchError(f"file does not exist: {path}") from exc
    except OSError as exc:
        raise PatchError(f"cannot read file {path}: {exc}") from exc
    if b"\x00" in data[:_BINARY_PROBE_BYTES]:
        raise PatchError(f"refusing to read binary file: {path}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchError(f"file is not valid UTF-8: {path}") from exc
