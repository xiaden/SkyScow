# Initial Semantic Graph Generation

Canonical procedure for turning an authoritative request or accepted DD into the
**initial semantic graph** of a Change DAG. This reference governs the
`change-dag-author` initial-generation pass. Other surfaces summarize and link
here rather than restating the doctrine.

General semantic-node doctrine — what a semantic node is, MEANING versus SCALE,
parent/child completeness, sibling/causal semantics, and the semantic/terminal
boundary — is defined once in the canonical `change-dag-semantics` skill
(`config/skills/change-dag-semantics/SKILL.md`). This reference covers only the
Author-specific initial-generation procedure and links that doctrine rather than
restating it.

## Core principle

The initial semantic graph is a **semantic skeleton, not an implementation
plan**. The Author answers:

```text
What materially distinct states must become true?
```

not:

```text
What files / functions / tests should I edit?
```

Implementation representation belongs to Worker lowering unless the
representation is itself authoritative input from the request or DD.

## The compilation procedure

Run the stages in order. Stages 1–4 and 6 shape the node set; stage 5 derives
the edges; stage 7 assembles the graph.

### Stage 1 — Extract obligations

From the authoritative request and accepted DD, identify every materially
distinct condition that must become true for the root request to be satisfied.
Do not create nodes yet; build a candidate set first.

Typical sources:

```text
explicit requested behavior
accepted DD invariants
required integration behavior
persistent / system guarantees
compatibility requirements
migration requirements
verification obligations
documentation obligations only when materially required
```

Do not create ceremonial categories merely because they exist conceptually. A
concern belongs only if satisfying the root actually requires it.

### Stage 2 — Normalize each obligation into a postcondition

Each candidate must be stated as an observable desired state.

```text
Good: Requirements are stored workspace-locally and survive process restart.
Bad:  Implement requirements_store.py.

Good: Current path-matching rules are applied consistently to requirement lookup.
Bad:  Add match_path() to requirements_store.py.

Good: Requirements-store lifecycle behavior has regression coverage.
Bad:  Extend test_requirements_store.py.

Good: Projected source inspection exposes boundary-owned work with provenance.
Bad:  Add provenance fields to change_dag_projection.py.
```

The rule:

> A semantic node states WHAT must be true, not HOW the repository will
> represent it, unless that representation is itself required by authoritative
> input.

Naming an established repository or domain subject is valid when it bounds the
postcondition — a service, package, consumer family, component, or contract whose
behavior the requirement constrains. Prescribing the implementation action, or
gratuitously choosing the representation that satisfies the postcondition, is not.
A file, symbol, or mechanism is not semantic merely because it is the artifact
expected to be edited; generalize that to the required behavior.

### Stage 3 — Remove duplicates and accidental restatements

For every candidate, ask whether it adds a distinct correctness obligation.
Reject:

```text
pure paraphrases
recursive restatements of the parent
implementation-detail variants of another obligation
"test X" where the real obligation is already "X is verified" and no separate
semantic dependency exists
```

Merge candidates that express the same required state. Do not create SCALE
children speculatively here merely because several implementation surfaces may
later satisfy one obligation; the Worker may still refine the SAME predicate by
lossless SCALE decomposition after repository discovery.

### Stage 4 — Split compound obligations

Split a candidate when it contains multiple independently meaningful states that
could require different reasoning or causal ordering.

```text
"The requirements store persists records and the read hook injects them."
```

becomes

```text
Requirements persist according to the required lifecycle.
Read operations expose applicable current requirements.
```

File count alone does not determine semantic decomposition. During INITIAL
Author generation do not speculate about implementation scale merely because
multiple files may exist; a MEANING split requires distinct required states.
Real repository breadth or context cost discovered later may justify lossless
SCALE decomposition of the SAME predicate by the Worker, under the canonical
semantic-node model.

### Stage 5 — Derive causal structure (separately from node generation)

Determine causality only after the candidate set is normalized. For every pair
where A and B might be siblings, ask the canonical operational question:

> Could B be correctly authored if A's implementation had not yet been proposed
> or accepted?

```text
YES -> A and B may remain independent siblings.
NO  -> B requires A.
```

Worked cases:

```text
A: requirements-store API semantics exist
B: read hook consumes those semantics
B cannot be correctly authored without A  ->  B requires A

A: deterministic path-matching semantics
B: workspace persistence semantics
each can be correctly authored without the other's proposed implementation
->  independent siblings are valid
```

Never infer ordering from node numbering, similar files, the same subsystem,
equal depth, or likely implementation order. Only genuine semantic authoring
dependency creates a `requires` edge, and only a missing `requires` edge makes
two nodes wrongly independent.

### Stage 6 — Check representation assumptions

Before emitting each node, ask whether the statement assumes an implementation
artifact exists.

```text
"extend existing X file"
"update Y class"
"change Z function"
"add coverage to test_foo.py"
"use SQLite table foo"
```

If the artifact or mechanism is not authoritative request/DD input, generalize
the node to the required behavior. Worker lowering discovers whether the
repository representation is `create`, `edit`, `move`, `remove`, `run`, or
further semantic decomposition. The initial Author must not pre-decide that.

### Stage 7 — Build the smallest useful semantic skeleton

The initial graph is only as deep as necessary to express distinct top-level
obligations, known causal relationships, and accepted architecture/DD
constraints.

```text
Prefer:
  root
  ├── storage semantics
  ├── lookup / applicability semantics
  ├── read integration semantics
  ├── DAG integration semantics
  └── verification semantics

Over an initial graph that guesses:
  schema
  SQLite pragmas
  a specific helper
  a specific hook file
  a specific unit-test file
  a specific fixture
  a specific parser
  a specific command
```

Workers are allowed and expected to introduce deeper semantic requirements when
real repository discovery shows a node is still too broad. The Author does not
need to foresee all lower decomposition before `dag_create`.

## Required node-quality gates

Before `dag_create`, every proposed semantic node must pass all of these. These
are yes/no reasoning gates — no scoring, no numeric thresholds.

```text
POSTCONDITION              Can it be stated as a condition that will be true
                           when satisfied?
DISTINCTNESS               Does it add meaning not already represented by its
                           parent or siblings?
BOUNDARY                   Is it one coherent required state rather than a
                           bundle of unrelated obligations? It may be broader
                           than one Worker context; the Worker can refine it by
                           lossless SCALE decomposition.
REPRESENTATION-INDEPENDENCE Does it state a postcondition over a bounded subject
                           (an established repository subject may bound it)
                           rather than prescribing the implementation action or
                           gratuitously choosing the representation?
AUTHORING-INDEPENDENCE     If it is a sibling, can it be correctly authored
                           without another sibling's accepted result?
CAUSALITY                  If it cannot, is that dependency expressed with
                           requires?
NECESSITY                  Would removing this node lose part of the root
                           requirement?
NON-CEREMONY               Was it created because the root actually needs it,
                           not because a generic category like docs/tests/
                           migration exists?
```

## Decomposition reasons

Decompose for **MEANING** or for **SCALE**; neither is a generation-time
obligation. SCALE decomposition must be lossless and exhaustive: children
collectively imply the parent. A broad initial node is acceptable when it remains
one coherent required state; it is not a generation-time failure merely because
one Worker may later refine it. The canonical MEANING/SCALE model, the
completeness invariant, and the subject-scope rules are in
`change-dag-semantics`.

## Author pre-sizing

The Author does not pre-size every initial semantic node for one Worker context.
Known semantic distinctions and known causal structure belong in the initial
graph; unknown implementation breadth is intentionally deferred. A coherent
postcondition may remain broad at `dag_create` time — a Worker may later
recursively SCALE-decompose it after repository discovery. See
`change-dag-semantics` for the canonical MEANING/SCALE model and completeness
invariant.

## Initial graph depth

Bias toward a shallow initial graph. Before `dag_create` the Author's job is the
semantic skeleton plus its causal structure — not complete implementation
decomposition.

Workers refine nodes later when:

```text
repository discovery reveals multiple distinct responsibilities
a node cannot be lowered safely as one responsibility
a causal prerequisite becomes visible
engineering judgment remains unresolved
```

## Discovery boundary before `dag_create`

> Before initial `dag_create`, perform only discovery necessary to identify
> semantic obligations and causal relationships.

Do not spend time before `dag_create` determining:

```text
exact patch contents
exact test command feasibility
runtime executable presence
precise source line ranges
detailed helper placement
specific fixture design
unified-diff mechanics
exact create / edit choice unless artifact existence is itself semantically
  relevant
```

Discovery before `dag_create` should answer questions such as:

```text
Does this subsystem already exist?
Are there multiple callers / integrations that change the semantic obligation?
Does authoritative architecture constrain the solution?
Does one obligation clearly depend on another?
Is a claimed existing capability / artifact actually real?
```

Stop discovery once the semantic skeleton and the causal graph are grounded.

## Recovery: interpreting a blocked Worker

The Author already owns causal repair after Worker feedback — align it with this
procedure. When a Worker reports:

```text
edit_base_unavailable
candidate_producers: [N14]
```

ask whether the semantic obligation genuinely depends on the producer
obligation:

```text
If yes -> repair the graph: add the requires relationship, or decompose the
          producing obligation so the dependency is explicit.
If no  -> the Worker's chosen exact representation is wrong; do not add an edge.
```

Do not mechanically add an edge because a candidate producer exists. The
semantic relationship remains authoritative; a candidate producer is diagnostic
evidence, not a dependency.

## What this is not

Do not introduce a semantic taxonomy. Do not add schema fields such as
`kind: behavior | persistence | integration | verification`. Do not require
fixed node families such as implementation, tests, docs, or migration. The DAG
schema stays generic: the constraint lives in this generation algorithm, not in
a mandatory ontology.

## Worked example

```text
REQUEST
Add durable requirements storage and make reads surface applicable
requirements.

BAD INITIAL GRAPH
- create requirements_store.py
- add SQLite schema
- edit tools.ts
- extend test_requirements_store.py

BETTER INITIAL SEMANTIC GRAPH
- requirements have durable workspace-local persistence
- applicability / path-matching semantics are deterministic
- reads surface applicable current requirements
- requirement lifecycle mutations enforce their authority rules
- required behavior is regression-verified
```

Causal analysis is a separate judgment over that graph. If "reads surface
applicable requirements" cannot be correctly authored before the accepted
requirements lookup semantics are known, express that with `requires` — do not
leave them as siblings merely because they touch different files.

This example is illustrative, not a required fixed decomposition for every task.
