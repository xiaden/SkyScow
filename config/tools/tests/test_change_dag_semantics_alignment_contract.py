"""Alignment contract: Change DAG semantic-node doctrine has one authority.

The canonical ``change-dag-semantics`` skill defines what a semantic node is,
MEANING vs SCALE, parent/child completeness, sibling/causal semantics, and the
semantic/terminal boundary. Author, Worker, and Semantic Researcher surfaces link
that skill instead of restating divergent doctrine, and no new node type or
schema field is introduced.

Assertions are structural/lexical contract markers rather than full prose
snapshots so legitimate role-specific wording can still evolve.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS = REPO_ROOT / "config" / "skills"
AGENTS = REPO_ROOT / "config" / "agents"

CANONICAL_SKILL = SKILLS / "change-dag-semantics" / "SKILL.md"
SEMANTIC_GENERATION = (
    SKILLS / "decomposing-design-documents" / "references" / "semantic-generation.md"
)
DECOMPOSE_SKILL = SKILLS / "decomposing-design-documents" / "SKILL.md"
PROTOCOL = (
    SKILLS / "decomposing-design-documents" / "references" / "subagent-protocol.md"
)
AUTHOR = AGENTS / "change-dag-author.md"
WORKER = AGENTS / "change-dag-worker.md"
RESEARCHER = AGENTS / "change-dag-semantic-researcher.md"
AUTHOR_DISPATCH = SKILLS / "dispatching-agents" / "references" / "change-dag-author.md"
WORKER_DISPATCH = SKILLS / "dispatching-agents" / "references" / "change-dag-worker.md"
RESEARCHER_DISPATCH = (
    SKILLS / "dispatching-agents" / "references" / "change-dag-semantic-researcher.md"
)
SCHEMA = REPO_ROOT / "config" / "tools" / "common" / "schemas" / "CHANGE_DAG_SCHEMA.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _norm(path: Path) -> str:
    stripped = re.sub(r"[*`]", "", _read(path))
    return " ".join(stripped.split()).lower()


def test_canonical_semantic_skill_exists_and_validates():
    assert CANONICAL_SKILL.is_file()
    frontmatter = yaml.safe_load(_read(CANONICAL_SKILL).split("---", 2)[1])
    assert frontmatter["name"] == CANONICAL_SKILL.parent.name == "change-dag-semantics"
    assert isinstance(frontmatter.get("description"), str)
    assert frontmatter["description"].strip()


def test_author_references_canonical_semantic_skill():
    for path in (AUTHOR, AUTHOR_DISPATCH):
        assert "change-dag-semantics" in _read(path), path


def test_worker_references_canonical_skill_for_decomposition_only():
    for path in (WORKER, WORKER_DISPATCH):
        text = _read(path)
        assert "change-dag-semantics" in text, path
        # The simple LOWER path is explicitly independent of semantic-node doctrine.
        assert "does not need semantic-node doctrine" in text, path


def test_semantic_researcher_doctrine_is_governed_by_the_same_skill():
    for path in (RESEARCHER, RESEARCHER_DISPATCH):
        assert "change-dag-semantics" in _read(path), path


def test_meaning_and_scale_are_both_on_worker_surfaces():
    for path in (WORKER, WORKER_DISPATCH):
        text = _read(path)
        assert "MEANING" in text, path
        assert "SCALE" in text, path


def test_scale_partition_preserves_the_predicate_under_narrower_scopes():
    for path in (CANONICAL_SKILL, WORKER, WORKER_DISPATCH):
        text = _read(path)
        assert "All API consumers use canonical lookup semantics." in text, path
        assert "All background consumers use canonical lookup semantics." in text, path
        assert "All CLI consumers use canonical lookup semantics." in text, path


def test_completeness_invariant_is_canonical_and_referenced():
    assert (
        "satisfaction(all direct semantic children) implies satisfaction(parent)"
        in _norm(CANONICAL_SKILL)
    )
    # The invariant is scoped to a `decomposition_only` parent.
    assert "decomposition_only" in _norm(CANONICAL_SKILL)
    # The Author-specific reference keeps the lossless/exhaustive application.
    assert "children collectively imply the parent" in _norm(SEMANTIC_GENERATION)
    for path in (WORKER, WORKER_DISPATCH):
        assert "completeness invariant" in _read(path), path
    # The decomposition surfaces link the canonical model rather than restating it.
    assert "change-dag-semantics" in _read(DECOMPOSE_SKILL)
    assert "change-dag-semantics" in _read(PROTOCOL)


def test_file_count_alone_is_not_a_semantic_criterion():
    assert "file count alone is not a semantic criterion" in _norm(CANONICAL_SKILL)
    # Consumers link the canonical rule instead of duplicating its sentence.
    for path in (WORKER, WORKER_DISPATCH):
        assert "file count alone is not a semantic criterion" not in _norm(path), path


def test_repository_identities_may_bound_subject_scope():
    author = _norm(AUTHOR)
    assert (
        "naming an established repository or domain subject is valid when it bounds "
        "the postcondition" in author
    )
    # The old categorical prohibition is gone.
    assert (
        "do not name a file, class, function, module, command, test file, or mechanism"
        not in author
    )
    # The canonical skill states the same subject-identity rule.
    assert (
        "naming an established repository or domain subject is valid when it bounds "
        "the postcondition" in _norm(CANONICAL_SKILL)
    )
    # The Author's procedure carries the same rule. A procedure that still told the
    # Author to rewrite any non-request/DD-authoritative subject would contradict the
    # canonical model the Author is instructed to follow.
    procedure = _norm(SEMANTIC_GENERATION)
    assert (
        "naming an established repository or domain subject is valid when it bounds "
        "the postcondition" in procedure
    )
    assert "not explicitly authoritative, rewrite it" not in procedure
    assert "avoid assuming a file / symbol / mechanism" not in procedure


def test_implementation_actions_are_not_semantic_nodes():
    assert "implementation actions, not semantic scale partitions" in _norm(CANONICAL_SKILL)
    assert "not an implementation action" in _norm(AUTHOR)
    for path in (WORKER, WORKER_DISPATCH):
        assert '"Edit foo.py."' in _read(path), path


def test_sibling_authoring_independence_and_causal_requires_remain():
    question = (
        "could b be correctly authored if a's implementation had not yet been "
        "proposed or accepted"
    )
    assert question in _norm(CANONICAL_SKILL)
    assert question in _norm(AUTHOR)
    for path in (AUTHOR, AUTHOR_DISPATCH, PROTOCOL):
        assert "requires" in _read(path), path


def test_no_new_node_type_or_schema_field_was_introduced():
    # The canonical skill explicitly rejects a `workset` node type.
    assert "do not introduce a workset node type" in _norm(CANONICAL_SKILL)
    schema_raw = _read(SCHEMA)
    assert "workset" not in schema_raw
    assert '"kind"' not in schema_raw
    schema = json.loads(schema_raw)
    node_types = {
        variant["properties"]["type"]["const"]
        for variant in schema["properties"]["nodes"]["additionalProperties"]["oneOf"]
    }
    assert node_types == {"semantic", "create", "edit", "remove", "move", "run"}
