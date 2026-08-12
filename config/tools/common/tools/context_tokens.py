"""Count model tokens for workspace file subsections.

The tokenizer artifact verification / download / cache machinery moved to
``common.helpers.tokenizer_helpers`` (the shared tokenizer boundary). This
module keeps its public ``context_tokens`` contract unchanged: same input
validation, same o200k / DS_V4_F_0731 counts, same weighting formula, same
error codes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..helpers.file_helpers import resolve_file_path
from ..helpers.tokenizer_helpers import (
    DEEPSEEK_TOKENIZER_CACHE_PATH,
    DEEPSEEK_TOKENIZER_PATH,
    DEEPSEEK_TOKENIZER_REVISION,
    DEEPSEEK_TOKENIZER_SHA256,
    DEEPSEEK_TOKENIZER_URL,
    SECTION_SEPARATOR,
    assemble_sections,
    load_tokenizers,
    read_subsection,
    weighted_tokens,
)

# Backward-compatible aliases: canonical definitions live in tokenizer_helpers.
__all__ = [
    "DEEPSEEK_TOKENIZER_CACHE_PATH",
    "DEEPSEEK_TOKENIZER_PATH",
    "DEEPSEEK_TOKENIZER_REVISION",
    "DEEPSEEK_TOKENIZER_SHA256",
    "DEEPSEEK_TOKENIZER_URL",
    "SECTION_SEPARATOR",
]


def _error(error: str, message: str) -> dict[str, str]:
    return {"error": error, "message": message}


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 1:
        return None
    return value


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
            sections.append(read_subsection(resolved, start_line, end_line))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return _error("read_error", f"{file_path}: {exc}")
        resolved_paths.add(resolved)

    source = assemble_sections(sections)
    try:
        o200k, deepseek = load_tokenizers()
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
            "weighted_tokens": weighted_tokens(count, section_count, file_count),
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
