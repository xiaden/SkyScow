"""Count model tokens for workspace file subsections."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from ..helpers.file_helpers import resolve_file_path

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


def _error(error: str, message: str) -> dict[str, str]:
    return {"error": error, "message": message}


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 1:
        return None
    return value


def _read_subsection(path: Path, start_line: int, end_line: int) -> str:
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


def _assemble_sections(sections: list[str]) -> str:
    return SECTION_SEPARATOR.join(sections)


def _weighted_tokens(source_tokens: int, section_count: int, file_count: int) -> int:
    cognitive_weight = 1 + 0.03 * (section_count - 1) + 0.015 * (file_count - 1)
    return math.ceil(source_tokens * cognitive_weight)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_path(path: Path) -> Path | None:
    if not path.is_file():
        return None
    if _sha256(path) != DEEPSEEK_TOKENIZER_SHA256:
        return None
    return path


def _download_tokenizer() -> Path:
    cache_path = DEEPSEEK_TOKENIZER_CACHE_PATH
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if _verified_path(cache_path) is not None:
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

        if _sha256(temporary_path) != DEEPSEEK_TOKENIZER_SHA256:
            raise ValueError("Downloaded DeepSeek tokenizer failed SHA-256 verification")
        os.replace(temporary_path, cache_path)
        return cache_path
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _resolve_tokenizer_path() -> Path:
    verified_system_path = _verified_path(DEEPSEEK_TOKENIZER_PATH)
    if verified_system_path is not None:
        return verified_system_path
    return _download_tokenizer()


def _load_tokenizers() -> tuple[Any, Any]:
    import tiktoken
    from tokenizers import Tokenizer

    return (
        tiktoken.get_encoding("o200k_base"),
        Tokenizer.from_file(str(_resolve_tokenizer_path())),
    )


def context_tokens(files: list[dict[str, Any]], workspace_root: Path) -> dict[str, Any]:
    """Count assembled file subsections for GPT and DeepSeek V4.

    Each requested range is read as UTF-8, stripped of only its final line
    ending, and joined with one blank line. ``weighted_tokens`` applies the
    planner's cognitive-weight formula using the number of ranges and unique
    files supplied.
    """
    if not isinstance(files, list) or not files:
        return _error("invalid_files", "files must be a non-empty array")

    workspace_root = workspace_root.resolve()
    sections: list[str] = []
    resolved_paths: set[Path] = set()

    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            return _error("invalid_file", f"files[{index}] must be an object")

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

        try:
            sections.append(_read_subsection(resolved, start_line, end_line))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return _error("read_error", f"{file_path}: {exc}")
        resolved_paths.add(resolved)

    source = _assemble_sections(sections)
    try:
        o200k, deepseek = _load_tokenizers()
        source_tokens = {
            "o200k": len(o200k.encode(source, disallowed_special=())),
            "DS_V4_F_0731": len(
                deepseek.encode(source, add_special_tokens=False).ids
            ),
        }
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        return _error("tokenizer_error", str(exc))

    section_count = len(sections)
    file_count = len(resolved_paths)
    return {
        model: {
            "source_tokens": count,
            "weighted_tokens": _weighted_tokens(count, section_count, file_count),
        }
        for model, count in source_tokens.items()
    }


if __name__ == "__main__":
    arguments = json.loads(input())
    result = context_tokens(
        files=arguments.get("files"),
        workspace_root=Path(arguments["workspace_root"]),
    )
    print(json.dumps(result, separators=(",", ":")))
