"""Regression tests: shipped skill frontmatter stays unambiguously valid YAML.

Covers the OpenCode failure mode where a skill whose plain-scalar
``description`` contains an unquoted ``: `` is discovered by one code path but
silently dropped from the runtime skill registry, plus the surrounding
frontmatter invariants enforced by ``scripts/validate_skills.py``.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "skills"
SHIPPED_SKILLS = REPO_ROOT / "config" / "skills"

_spec = importlib.util.spec_from_file_location(
    "validate_skills", REPO_ROOT / "scripts" / "validate_skills.py"
)
assert _spec is not None and _spec.loader is not None
validate_skills_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_skills_module)
validate_skills = validate_skills_module.validate_skills


def _write_skill(
    root: Path, dir_name: str, frontmatter: str, body: str = "# Body\n"
) -> Path:
    skill_dir = root / dir_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")
    return path


def _copy_fixture(root: Path, fixture: str) -> Path:
    """Copy a fixture skill directory into ``root`` and return its SKILL.md."""
    destination = root / fixture
    shutil.copytree(FIXTURES / fixture, destination)
    return destination / "SKILL.md"


class TestShippedSkills:
    def test_all_shipped_skills_have_valid_frontmatter(self):
        assert validate_skills(SHIPPED_SKILLS) == []

    def test_expected_skill_count(self):
        assert len(list(SHIPPED_SKILLS.glob("*/SKILL.md"))) >= 31

    def test_gg_core_and_gg_repos_descriptions_are_parseable(self):
        """The two skills this regression was filed against must load."""
        for name in ("gg-core", "gg-repos"):
            raw = (SHIPPED_SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
            frontmatter = raw.split("---", 2)[1]
            data = yaml.safe_load(frontmatter)
            assert data["name"] == name
            description = data.get("description")
            assert isinstance(description, str) and description.strip()


class TestScalarStyles:
    def test_unquoted_colon_plain_scalar_is_rejected(self, tmp_path):
        _copy_fixture(tmp_path, "unquoted-colon")
        problems = validate_skills(tmp_path)
        assert problems
        assert any("not valid YAML" in problem for problem in problems)

    def test_quoted_description_is_accepted(self, tmp_path):
        _copy_fixture(tmp_path, "quoted-description")
        assert validate_skills(tmp_path) == []

    def test_block_scalar_description_is_accepted(self, tmp_path):
        _copy_fixture(tmp_path, "block-description")
        assert validate_skills(tmp_path) == []


class TestStructuralRules:
    def test_missing_frontmatter_fails(self, tmp_path):
        skill_dir = tmp_path / "no-frontmatter"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
        problems = validate_skills(tmp_path)
        assert any("missing '---' YAML frontmatter" in problem for problem in problems)

    def test_missing_name_fails(self, tmp_path):
        _write_skill(tmp_path, "no-name", "description: A valid description.\n")
        problems = validate_skills(tmp_path)
        assert any("'name'" in problem for problem in problems)

    def test_missing_description_fails(self, tmp_path):
        _write_skill(tmp_path, "no-description", "name: no-description\n")
        problems = validate_skills(tmp_path)
        assert any("'description'" in problem for problem in problems)

    def test_name_directory_mismatch_fails(self, tmp_path):
        _write_skill(tmp_path, "actual-dir", "name: other-name\ndescription: Desc.\n")
        problems = validate_skills(tmp_path)
        assert any("does not match directory" in problem for problem in problems)

    def test_unsafe_name_fails(self, tmp_path):
        _write_skill(tmp_path, "Bad_Name", "name: Bad_Name\ndescription: Desc.\n")
        problems = validate_skills(tmp_path)
        assert any("not OpenCode-compatible" in problem for problem in problems)

    def test_duplicate_names_fail(self, tmp_path):
        _write_skill(tmp_path, "dup-a", "name: duplicate\ndescription: Desc.\n")
        _write_skill(tmp_path, "dup-b", "name: duplicate\ndescription: Desc.\n")
        problems = validate_skills(tmp_path)
        assert any("duplicate skill name" in problem for problem in problems)

    def test_empty_root_fails(self, tmp_path):
        problems = validate_skills(tmp_path)
        assert any("no '*/SKILL.md' files found" in problem for problem in problems)
