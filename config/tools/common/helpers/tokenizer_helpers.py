"""Shared tokenizer loading, verification, assembly, and weighting helpers.

Public boundary for tokenizer behavior shared by the ``context_tokens`` and
``context_budget`` tools. These helpers preserve the verified artifact /
download / cache behavior of the original ``context_tokens`` implementation:

- A pinned DeepSeek V4 Flash 0731 tokenizer artifact with a known SHA-256.
- Resolution order: verified system artifact first, then a verified user
  cache, then a verified download. Every byte path is SHA-256 verified before
  use; a failed verification falls through to the next source.
- ``weighted_tokens`` applies the planner's cognitive-weight formula using the
  number of ranges (sections) and unique files supplied.

Contract: do not change the counting contract here. ``context_tokens`` counts
must remain byte-for-byte identical after any refactor of this module.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

DEEPSEEK_TOKENIZER_PATH = Path(
    os.environ.get(
        "HOLYCODE_DEEPSEEK_TOKENIZER_PATH",
        "/usr/local/share/holycode/tokenizers/deepseek-v4-flash-0731/tokenizer.json",
    )
)
DEEPSEEK_TOKENIZER_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
DEEPSEEK_TOKENIZER_SHA256 = (
    "8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf"
)
DEEPSEEK_TOKENIZER_URL = (
    "https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/resolve/"
    f"{DEEPSEEK_TOKENIZER_REVISION}/tokenizer.json?download=true"
)
DEEPSEEK_TOKENIZER_CACHE_PATH = Path(
    os.environ.get(
        "HOLYCODE_DEEPSEEK_TOKENIZER_CACHE",
        str(
            Path.home()
            / ".cache/holycode/tokenizers/deepseek-v4-flash-0731/tokenizer.json"
        ),
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


def sha256(path: Path) -> str:
    """Return the lowercase SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_path(path: Path) -> Path | None:
    """Return ``path`` if it is a file whose SHA-256 matches the pinned digest.

    Returns None when the path is missing or fails verification.
    """
    if not path.is_file():
        return None
    if sha256(path) != DEEPSEEK_TOKENIZER_SHA256:
        return None
    return path


def download_tokenizer() -> Path:
    """Download the pinned DeepSeek tokenizer to the user cache, verified.

    Reuses an already-verified cache file. Writes through a temporary file and
    atomically replaces the cache only after SHA-256 verification.

    Returns:
        Path to the verified cached tokenizer file.

    Raises:
        ValueError: If the download fails SHA-256 verification.
    """
    cache_path = DEEPSEEK_TOKENIZER_CACHE_PATH
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if verified_path(cache_path) is not None:
        return cache_path
    if cache_path.exists():
        cache_path.unlink()

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=cache_path.parent,
            prefix=".tokenizer-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            request = urllib.request.Request(
                DEEPSEEK_TOKENIZER_URL,
                headers={"User-Agent": "HolyCode/context_tokens"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)

        if sha256(temporary_path) != DEEPSEEK_TOKENIZER_SHA256:
            raise ValueError("Downloaded DeepSeek tokenizer failed SHA-256 verification")
        os.replace(temporary_path, cache_path)
        return cache_path
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def resolve_tokenizer_path() -> Path:
    """Resolve a verified tokenizer path: system artifact, then download.

    Preference order (matching the original context_tokens contract):
    1. Verified system artifact (shipped in the image).
    2. Verified download into the user cache.
    """
    verified_system_path = verified_path(DEEPSEEK_TOKENIZER_PATH)
    if verified_system_path is not None:
        return verified_system_path
    return download_tokenizer()


def load_tokenizers() -> tuple[Any, Any]:
    """Load the o200k (tiktoken) and DeepSeek V4 Flash 0731 tokenizers.

    Returns:
        Tuple of (o200k_encoding, deepseek_tokenizer). The DeepSeek tokenizer
        is loaded from the verified path resolved by ``resolve_tokenizer_path``.

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
