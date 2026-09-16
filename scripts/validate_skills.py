#!/usr/bin/env python3
"""Validate the YAML frontmatter of every shipped OpenCode skill.

OpenCode can discover a skill through one code path while its runtime
(model-facing) skill registry silently drops it. The confirmed trigger is an
unquoted ``": "`` sequence inside a plain scalar ``description``: a strict YAML
parser reads it as a nested mapping, the skill loses its description, and the
registry path that filters on a present description discards it.

This check uses a real YAML parser (PyYAML), not regex-only matching. It fails
when a skill has:

* no ``---`` frontmatter block;
* frontmatter that does not parse as YAML;
* frontmatter that is not a mapping;
* a missing or non-string ``name`` / ``description``;
* a ``name`` that does not match its containing directory;
* a ``name`` that is not OpenCode-compatible (lowercase, hyphen-separated,
  1-64 characters);
* a duplicate skill name;
* a ``description`` written as an ambiguous plain scalar.

Usage:
    python3 scripts/validate_skills.py [skills_root]

``skills_root`` defaults to this repository's ``config/skills``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_ROOT = ROOT / "config" / "skills"

FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(?P<body>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
# OpenCode naming expectations, per
# making-editing-skills/references/frontmatter-rules.md:
# lowercase alphanumerics separated by single hyphens, 1-64 characters.
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 64


def _one_line(value: object) -> str:
    """Collapse a multi-line parser message into a single report line."""
    return " ".join(str(value).split())


def _check_description_style(path: Path, frontmatter: str) -> list[str]:
    """Reject a ``description`` written as an ambiguous plain scalar.

    Quoted (``'...'``/``"..."``) and block (``>``/``|``) scalars are explicit
    and unambiguous. A plain scalar is only risky when the parser could read it
    differently from the visible text (for example a trailing `` #`` comment),
    so compare the parsed value against its source span.
    """
    try:
        node = yaml.compose(frontmatter)
    except yaml.YAMLError:
        return []  # already reported by the caller's parse check
    if not isinstance(node, yaml.MappingNode):
        return []
    for key_node, value_node in node.value:
        if key_node.value != "description":
            continue
        if value_node.style is not None:
            return []  # quoted or block scalar: explicit and unambiguous
        source = frontmatter[value_node.start_mark.index : value_node.end_mark.index]
        if source.strip() != value_node.value.strip():
            return [
                f"{path}: 'description' is an ambiguous plain scalar; "
                "quote it or use a '>-' block scalar"
            ]
        return []
    return []


def _check_skill(path: Path) -> tuple[str | None, list[str]]:
    """Return the declared ``name`` (if any) and every problem for one skill."""
    label = str(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"{label}: cannot read file ({_one_line(exc)})"]

    match = FRONTMATTER_RE.match(raw)
    if match is None:
        return None, [f"{label}: missing '---' YAML frontmatter block"]

    frontmatter = match.group("body")
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError as exc:
        return None, [
            f"{label}: frontmatter is not valid YAML; quote or block-fold any "
            f"scalar containing ': ' ({_one_line(exc)})"
        ]
    if not isinstance(data, dict):
        return None, [f"{label}: frontmatter must be a YAML mapping"]

    problems = _check_description_style(path, frontmatter)

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        problems.append(f"{label}: missing or non-string 'name'")
        name = None
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        problems.append(f"{label}: missing or non-string 'description'")

    if name is not None:
        expected = path.parent.name
        if name != expected:
            problems.append(
                f"{label}: 'name' ({name!r}) does not match directory ({expected!r})"
            )
        if len(name) > MAX_NAME_LENGTH or NAME_RE.match(name) is None:
            problems.append(
                f"{label}: 'name' ({name!r}) is not OpenCode-compatible "
                "(lowercase, hyphen-separated, 1-64 chars)"
            )
    return name, problems


def validate_skills(skills_root: Path = DEFAULT_SKILLS_ROOT) -> list[str]:
    """Return every frontmatter problem under ``skills_root`` (``[]`` == valid)."""
    skill_files = sorted(skills_root.glob("*/SKILL.md"))
    if not skill_files:
        return [f"{skills_root}: no '*/SKILL.md' files found"]

    problems: list[str] = []
    owners: dict[str, Path] = {}
    for path in skill_files:
        name, file_problems = _check_skill(path)
        problems.extend(file_problems)
        if name is not None:
            first_seen = owners.setdefault(name, path)
            if first_seen != path:
                problems.append(
                    f"{path}: duplicate skill name {name!r} "
                    f"(also declared by {first_seen})"
                )
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("usage: validate_skills.py [skills_root]", file=sys.stderr)
        return 2
    skills_root = Path(args[0]) if args else DEFAULT_SKILLS_ROOT

    problems = validate_skills(skills_root)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        print(
            f"Skill frontmatter validation failed: {len(problems)} problem(s)",
            file=sys.stderr,
        )
        return 1

    count = len(list(skills_root.glob("*/SKILL.md")))
    print(f"Skill frontmatter validation passed ({count} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
