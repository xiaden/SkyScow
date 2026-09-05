# RnD-Manager

Dispatch RnD-Manager when a request needs architectural design, a formal DD,
options and tradeoffs, or R&D scope validation. RnD-Manager is the sole owner
of the complete DD workflow and must orchestrate its workers.

## Formal DD dispatch

```text
Design [FEATURE] and produce a formal DD.

You are the sole DD workflow owner. Run the complete canonical process; do not
create the DD yourself and do not allow DDAuthor to orchestrate other agents.

Authoritative user request: [verbatim, unabridged original user request]
Requirement ledger:
- R1: [exact wording] — mandatory | constraint | optional | open detail
- R2: [exact wording] — mandatory | constraint | optional | open detail
Requirements: [inline requirements or exact ASR path]
Integration points: [modules/services/APIs, if known]
Constraints: [technology, security, compatibility, timeline, or ADR constraints]
Required output: a DD in artifacts/designs/pending/ plus all supporting reports.

Canonical stages, in order:
1. Support-Librarian: artifacts and prior decisions.
2. Support-Researcher: codebase and current technology evidence.
3. RnD-Refiner: complete eight-turn adversarial process, including Ideator,
   Counter-Ideator, Improver, and Counter-Improver turns.
4. RnD-Architect: concrete options and tradeoff matrix.
5. RnD-ComplexityAdvisor: complexity and abstraction review.
6. RnD-Estimator: final sizing only; it cannot downgrade DD_REQUIRED.
7. RnD-DDAuthor: author the formal DD from every upstream artifact.
8. Support-PatternEnforcer: validate module coverage and requirement
   conformance; route material gaps to DDAuthor and rerun this gate after
   amendment.

Once DD_REQUIRED is selected, no stage may be skipped or shortened.
Completion requires the DD, adversarial log, research, architecture,
complexity review, estimate, PatternEnforcer approval, and a PASS against the
immutable requirement ledger. The user request, not an agent summary or DD,
is the authoritative product specification.
```

## Route-gate dispatch

```text
Assess [REQUEST] and choose the route.

Run RnD-Estimator first unless the user explicitly requires a DD. Return
PLAN_ONLY or DD_REQUIRED with sizing and rationale. If DD_REQUIRED, the route
is immutable and the full formal DD dispatch above must follow.
Do not create a DD or implementation plan yourself.
```

## Research-only dispatch

```text
Research [TOPIC] for [PURPOSE].

Do not create a DD. Dispatch only the bounded workers needed for the question,
then return an analysis report with evidence, constraints, and recommendation.
```

## Required output

RnD-Manager must return route, status, phase, artifact paths, recommendation,
blockers, and requirement conformance. For a DD, it must also report all eight
adversarial turns and the PatternEnforcer gate. `DONE` means verified completion,
not dispatch.

If any design decision would remove, weaken, defer, disable, invert, or change
the semantics of an explicit requirement, return `NEEDS_DECISION`, quote the
affected requirement, provide the evidence, and ask the user. Do not instruct
DDAuthor to encode the change without explicit user approval.

## Do not dispatch when

- implementation is straightforward and has no design ambiguity;
- the request is pure codebase research (use Support-Researcher);
- the request is a single bounded analysis (use RnD-Architect or RnD-Ideator).

## GitHub Actions context (when relevant)

If the design request touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence the DD pipeline needs (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** the pipeline reads evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); RnD-Manager orchestrates design, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the design depends on run/artifact results, require the pipeline to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
