"""Contract tests pinning the Change DAG initial semantic-generation doctrine.

The initial semantic graph is a semantic skeleton, not an implementation plan.
These tests pin the governing constraints on the Author's initial-generation
pass so the contract cannot silently regress toward implementation-action
wording or an assumed implementation artifact.

They assert the presence and absence of governing constraints in the active
contract surfaces. They deliberately do not attempt to test model judgment.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parents[1]

CANONICAL = REPO_ROOT / "config" / "skills" / "decomposing-design-documents" / "references" / "semantic-generation.md"
AUTHOR = REPO_ROOT / "config" / "agents" / "change-dag-author.md"
SKILL = REPO_ROOT / "config" / "skills" / "decomposing-design-documents" / "SKILL.md"
PROTOCOL = REPO_ROOT / "config" / "skills" / "decomposing-design-documents" / "references" / "subagent-protocol.md"
DISPATCH = REPO_ROOT / "config" / "skills" / "dispatching-agents" / "references" / "change-dag-author.md"
SCHEMA = REPO_ROOT / "config" / "tools" / "common" / "schemas" / "CHANGE_DAG_SCHEMA.json"

SEMANTIC_SKILL = REPO_ROOT / "config" / "skills" / "change-dag-semantics" / "SKILL.md"
WORKER = REPO_ROOT / "config" / "agents" / "change-dag-worker.md"
WORKER_DISPATCH = REPO_ROOT / "config" / "skills" / "dispatching-agents" / "references" / "change-dag-worker.md"
RESEARCHER = REPO_ROOT / "config" / "agents" / "change-dag-semantic-researcher.md"
RESEARCHER_DISPATCH = REPO_ROOT / "config" / "skills" / "dispatching-agents" / "references" / "change-dag-semantic-researcher.md"

SURFACES = (AUTHOR, SKILL, PROTOCOL, DISPATCH)

# Every authoring surface that governs semantic structure must link the single
# canonical `change-dag-semantics` skill rather than restating divergent doctrine.
SEMANTIC_LINK_SURFACES = (
    AUTHOR,
    SKILL,
    PROTOCOL,
    DISPATCH,
    WORKER,
    WORKER_DISPATCH,
    RESEARCHER,
    RESEARCHER_DISPATCH,
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Collapse whitespace, strip markdown emphasis and blockquote markers."""
    stripped = re.sub(r"[*`]", "", text)
    stripped = re.sub(r"(?m)^\s*>+\s?", "", stripped)
    return " ".join(stripped.split()).lower()


# ---------------------------------------------------------------------------
# canonical procedure
# ---------------------------------------------------------------------------
def test_every_generation_stage_is_documented():
    canonical = _norm(_read(CANONICAL))
    for stage in (
        "extract obligations",
        "normalize each obligation into a postcondition",
        "remove duplicates and accidental restatements",
        "split compound obligations",
        "derive causal structure (separately from node generation)",
        "check representation assumptions",
        "build the smallest useful semantic skeleton",
    ):
        assert stage in canonical, stage


def test_node_quality_gates_are_documented():
    canonical = _norm(_read(CANONICAL))
    for gate in (
        "postcondition",
        "distinctness",
        "boundary",
        "representation-independence",
        "authoring-independence",
        "causality",
        "necessity",
        "non-ceremony",
    ):
        assert gate in canonical, gate
    # Yes/no reasoning gates only -- no scoring system or numeric thresholds.
    assert "no scoring, no numeric thresholds" in canonical


def test_initial_graph_is_a_semantic_skeleton():
    for path in (CANONICAL, AUTHOR):
        assert "semantic skeleton, not an implementation plan" in _norm(_read(path)), path
    assert "what materially distinct states must become true" in _norm(_read(CANONICAL))
    assert "what files / functions / tests should i edit" in _norm(_read(CANONICAL))


def test_semantic_nodes_are_postconditions():
    canonical = _norm(_read(CANONICAL))
    assert "states what must be true, not how the repository will represent it" in canonical
    author = _norm(_read(AUTHOR))
    assert "postconditions only" in author
    assert "a node states what must be true, not how the repository will represent it" in author


def test_node_and_edge_derivation_are_separate_judgments():
    canonical = _norm(_read(CANONICAL))
    assert "determine causality only after the candidate set is normalized" in canonical
    author = _norm(_read(AUTHOR))
    assert "nodes and edges are separate judgments" in author
    assert "never infer a dependency" in author
    assert "or independence" in author


def test_sibling_independence_uses_the_authored_without_a_question():
    question = "could b be correctly authored if a's implementation had not yet been proposed or accepted"
    assert question in _norm(_read(CANONICAL))
    assert question in _norm(_read(AUTHOR))


def test_missing_independence_requires_an_edge():
    canonical = _norm(_read(CANONICAL))
    assert "no -> b requires a." in canonical
    assert "only genuine semantic authoring dependency creates a requires edge" in canonical
    # Node identity/depth is never a dependency signal.
    assert "never infer ordering from node numbering" in canonical
    for path in (SKILL, PROTOCOL, AUTHOR):
        assert "requires" in _norm(_read(path)), path


def test_shallow_initial_graph_and_later_worker_refinement():
    canonical = _norm(_read(CANONICAL))
    assert "bias toward a shallow initial graph" in canonical
    assert "workers refine nodes later when" in canonical
    assert "engineering judgment remains unresolved" in canonical
    assert "does not need to foresee all lower decomposition before dag_create" in canonical
    author = _norm(_read(AUTHOR))
    assert "shallow by default" in author
    assert "workers introduce deeper semantic requirements" in author


def test_representation_assumptions_are_guarded():
    canonical = _norm(_read(CANONICAL))
    for assumed in (
        "extend existing x file",
        "update y class",
        "change z function",
        "add coverage to test_foo.py",
        "use sqlite table foo",
    ):
        assert assumed in canonical, assumed
    assert "generalize the node to the required behavior" in canonical
    assert "must not pre-decide that" in canonical


def test_pre_dag_create_discovery_is_bounded():
    canonical = _norm(_read(CANONICAL))
    assert (
        "discovery necessary to identify semantic obligations and causal relationships"
        in canonical
    )
    for excluded in (
        "exact patch contents",
        "exact test command feasibility",
        "runtime executable presence",
        "precise source line ranges",
        "detailed helper placement",
        "specific fixture design",
        "unified-diff mechanics",
    ):
        assert excluded in canonical, excluded
    author = _norm(_read(AUTHOR))
    assert "perform only the discovery necessary to identify" in author


def test_recovery_interpretation_is_aligned():
    canonical = _norm(_read(CANONICAL))
    assert "edit_base_unavailable" in canonical
    assert "candidate_producers" in canonical
    assert "do not mechanically add an edge because a candidate producer exists" in canonical
    assert "the worker's chosen exact representation is wrong" in canonical


# ---------------------------------------------------------------------------
# absence of mandatory ontology
# ---------------------------------------------------------------------------
def test_no_mandatory_semantic_taxonomy():
    canonical = _norm(_read(CANONICAL))
    assert "do not introduce a semantic taxonomy" in canonical
    assert "not in a mandatory ontology" in canonical
    for path in SURFACES:
        text = _norm(_read(path))
        for kind in ("kind: behavior", "kind: persistence", "kind: integration", "kind: verification"):
            assert kind not in text, (path, kind)
    # The DAG schema stays generic: no node-kind taxonomy field was introduced.
    assert '"kind"' not in _read(SCHEMA)


def test_no_mandatory_node_families():
    canonical = _norm(_read(CANONICAL))
    assert (
        "do not require fixed node families such as implementation, tests, docs, or migration"
        in canonical
    )
    author = _norm(_read(AUTHOR))
    assert "no taxonomy" in author
    assert "do not emit fixed families such as implementation/tests/docs/migration" in author


# ---------------------------------------------------------------------------
# anti-regression: implementation-action wording
# ---------------------------------------------------------------------------
def test_implementation_action_examples_are_labeled_as_bad():
    canonical = _norm(_read(CANONICAL))
    assert "bad initial graph" in canonical
    assert "better initial semantic graph" in canonical
    # The exact dogfood failure mode is pinned as a BAD example.
    assert "extend test_requirements_store.py" in canonical
    assert "create requirements_store.py" in canonical


def test_author_contract_keeps_the_good_bad_contrast():
    author = _norm(_read(AUTHOR))
    assert 'over "extend the accepted requirements-store test file"' in author
    assert "unless that file's existence is genuinely authoritative input" in author
    assert "not an implementation action" in author


# ---------------------------------------------------------------------------
# one canonical authority, linked from every surface
# ---------------------------------------------------------------------------
def test_every_authoring_surface_links_the_canonical_procedure():
    for path in SURFACES:
        assert "semantic-generation.md" in _read(path), path


def test_no_competing_duplicate_doctrine():
    """Surfaces summarize and link; they do not restate the full procedure."""
    for path in (SKILL, PROTOCOL, DISPATCH):
        text = _norm(_read(path))
        # The stage-by-stage procedure lives only in the canonical reference.
        assert "normalize each obligation into a postcondition" not in text, path
        assert "remove duplicates and accidental restatements" not in text, path
        assert "split compound obligations" not in text, path


# ---------------------------------------------------------------------------
# BASE vs SELF lens wording
# ---------------------------------------------------------------------------
def test_base_and_self_lenses_are_distinguished():
    skill = _norm(_read(SKILL))
    assert "self view" in skill
    assert "base plus the boundary node's own persisted terminal work" in skill
    assert "base is live repository plus strictly-deeper accepted work" in skill

    protocol = _norm(_read(PROTOCOL))
    assert "self view (base plus the boundary node's own persisted terminal work)" in protocol
    assert "peer proposals are excluded from both" in protocol

    # No surface still describes worker context as strictly-deeper accepted work
    # alone, without the boundary-owned work and the BASE/SELF distinction.
    for path in (SKILL, PROTOCOL):
        text = _norm(_read(path))
        assert "reason from live repository plus strictly-deeper accepted work only" not in text, path
        assert "reasoning from live repository plus strictly-deeper accepted work;" not in text, path


# ---------------------------------------------------------------------------
# the canonical semantic-node skill is governed, not silently duplicated
# ---------------------------------------------------------------------------
def test_canonical_semantic_skill_exists_and_names_itself():
    assert SEMANTIC_SKILL.is_file()
    frontmatter = yaml.safe_load(_read(SEMANTIC_SKILL).split("---", 2)[1])
    assert frontmatter["name"] == "change-dag-semantics"
    assert isinstance(frontmatter.get("description"), str)


def test_authoring_surfaces_link_the_canonical_semantic_skill():
    for path in SEMANTIC_LINK_SURFACES:
        assert "change-dag-semantics" in _read(path), path


def test_canonical_semantic_skill_does_not_carry_the_staged_generation_procedure():
    """The staged pipeline stays in semantic-generation.md; the canonical skill
    states the node model, not the Author-specific derivation procedure."""
    text = _norm(_read(SEMANTIC_SKILL))
    assert "normalize each obligation into a postcondition" not in text
    assert "remove duplicates and accidental restatements" not in text
    assert "split compound obligations" not in text
