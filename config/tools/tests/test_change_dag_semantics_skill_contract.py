"""Contract tests for the canonical Change DAG semantic-node doctrine."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = REPO_ROOT / "config" / "skills" / "change-dag-semantics"
SKILL_PATH = SKILL_DIR / "SKILL.md"


def _raw() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def _norm() -> str:
    return " ".join(_raw().split())


def test_frontmatter_and_directory_identity():
    raw = _raw()
    frontmatter = yaml.safe_load(raw.split("---", 2)[1])
    assert frontmatter["name"] == SKILL_DIR.name == "change-dag-semantics"
    assert set(frontmatter) == {"name", "description"}
    assert isinstance(frontmatter["description"], str)
    assert "Use when" in frontmatter["description"]
    assert "do not use for" in frontmatter["description"]


def test_definition_and_subject_identity_rule():
    text = _norm()
    assert (
        "A postcondition over a bounded subject scope whose satisfaction contributes "
        "directly to satisfying its parent/root obligation."
    ) in text
    assert (
        "Naming an established repository or domain subject is valid when it bounds "
        "the postcondition. Prescribing the implementation action, or gratuitously "
        "choosing the representation that satisfies it, is not."
    ) in text
    lowered = _raw().lower()
    assert "never mention a file" not in lowered
    assert "do not name a file" not in lowered


def test_meaning_and_scale_decomposition_are_distinguished():
    text = _norm()
    assert "## Two decomposition reasons" in text
    assert "### MEANING" in text
    assert "### SCALE" in text
    assert "multiple distinct required states" in text
    for example in (
        "All API consumers use canonical lookup semantics.",
        "All background consumers use canonical lookup semantics.",
        "All CLI consumers use canonical lookup semantics.",
    ):
        assert example in text
    assert "File count alone is not a semantic criterion." in text


def test_completeness_and_causality_rules_are_canonical():
    text = _norm()
    assert "satisfaction(all direct semantic children) implies satisfaction(parent)" in text
    assert "Could B be correctly authored if A's implementation had not yet been proposed or accepted?" in text
    assert "SCALE siblings are not automatically dependent" in text


def test_actions_are_not_semantic_nodes():
    text = _norm()
    assert "INVALID: “Edit src/query_service.py.”" in text
    assert "implementation actions, not semantic scale partitions" in text
    assert "A semantic node may recursively refine until exact lowering is safely bounded." in text


def test_no_new_node_type_or_taxonomy_is_introduced():
    text = _norm()
    assert "Do not introduce a `workset` node type" in text
    assert "kind:" not in _raw()
    assert not any(
        f"kind: {value}" in _raw()
        for value in ("behavior", "persistence", "integration", "verification")
    )


def test_current_mixed_children_and_run_barrier_rules_are_present():
    text = _norm()
    assert "at most one direct `run` child" in text
    assert "When it directly requires a `run`, every other required child must be semantic" in text
    assert "`edit` is the only composable direct terminal kind" in text
    assert "`create`/`remove`/`move`/`run` are exclusive" in text
