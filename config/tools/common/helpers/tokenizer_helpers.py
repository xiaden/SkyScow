"""Shared tokenizer loading, assembly, and weighting helpers.

Public boundary for tokenizer behavior shared by the ``context_tokens`` and
``context_budget`` tools. The Docker image ships the pinned DeepSeek V4 Flash
0731 tokenizer at the configured path; runtime use requires that local artifact
and never downloads a replacement.

``weighted_tokens`` applies the planner's cognitive-weight formula using the
number of ranges (sections) and unique files supplied.

Contract: do not change the counting contract here. ``context_tokens`` counts
must remain byte-for-byte identical after any refactor of this module.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEEPSEEK_TOKENIZER_PATH = Path(
    os.environ.get(
        "SKYSCOW_DEEPSEEK_TOKENIZER_PATH",
        "/usr/local/share/skyscow/tokenizers/deepseek-v4-flash-0731/tokenizer.json",
    )
)
SECTION_SEPARATOR = "\n\n"


def assemble_sections(sections: list[str]) -> str:
    """Join file subsections with a single blank line separator."""
    return SECTION_SEPARATOR.join(sections)


def read_subsection(path: Path, start_line: int, end_line: int) -> str:
    """Read a 1-based inclusive line range from a UTF-8 file.

    Only the final line ending of the slice is stripped. Raises ValueError
    for empty files or when ``end_line`` exceeds the file length.
    """
    content = path.read_bytes().decode("utf-8")
    lines = content.splitlines(keepends=True)
    if not lines:
        raise ValueError(f"File is empty: {path}")
    if end_line > len(lines):
        raise ValueError(
            f"end_line ({end_line}) exceeds file length ({len(lines)} lines)"
        )

    selected = "".join(lines[start_line - 1 : end_line])
    if selected.endswith("\r\n"):
        return selected[:-2]
    if selected.endswith(("\r", "\n")):
        return selected[:-1]
    return selected


def weighted_tokens(source_tokens: int, section_count: int, file_count: int) -> int:
    """Apply the planner's cognitive-weight formula.

    Args:
        source_tokens: Raw token count of the assembled source.
        section_count: Number of supplied line ranges.
        file_count: Number of unique files among the ranges.

    Returns:
        Ceiling of source_tokens multiplied by the cognitive weight.
    """
    cognitive_weight = 1 + 0.03 * (section_count - 1) + 0.015 * (file_count - 1)
    return int(source_tokens * cognitive_weight + 0.999999)  # math.ceil equivalent


def resolve_tokenizer_path() -> Path:
    """Return the shipped tokenizer path or fail when the image is incomplete."""
    if not DEEPSEEK_TOKENIZER_PATH.is_file():
        raise FileNotFoundError(
            f"SkyScow tokenizer is missing: {DEEPSEEK_TOKENIZER_PATH}"
        )
    return DEEPSEEK_TOKENIZER_PATH


def load_tokenizers() -> tuple[Any, Any]:
    """Load the o200k (tiktoken) and DeepSeek V4 Flash 0731 tokenizers.

    Returns:
        Tuple of (o200k_encoding, deepseek_tokenizer). The DeepSeek tokenizer
        is loaded from the shipped path resolved by ``resolve_tokenizer_path``.

    Raises:
        FileNotFoundError, OSError, ValueError, RuntimeError: propagated to
        callers, which convert them into stable compact tool errors.
    """
    import tiktoken
    from tokenizers import Tokenizer

    return (
        tiktoken.get_encoding("o200k_base"),
        Tokenizer.from_file(str(resolve_tokenizer_path())),
    )
