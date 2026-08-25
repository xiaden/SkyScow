# RnD-Manager

Dispatch RnD-Manager when a request needs architectural design, a formal DD,
options and tradeoffs, or R&D scope validation. RnD-Manager is the sole owner
of the complete DD workflow and must orchestrate its workers.

## Formal DD dispatch

```text
Design [FEATURE] and produce a formal DD.

You are the sole DD workflow owner. Run the complete canonical process; do not
create the DD yourself and do not allow DDAuthor to orchestrate other agents.

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
8. Support-PatternEnforcer: validate coverage; route material gaps to DDAuthor
   and rerun this gate after amendment.

Once DD_REQUIRED is selected, no stage may be skipped or shortened.
Completion requires the DD, adversarial log, research, architecture,
complexity review, estimate, and PatternEnforcer approval.
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
and blockers. For a DD, it must also report all eight adversarial turns and the
PatternEnforcer gate. `DONE` means verified completion, not dispatch.

## Do not dispatch when

- implementation is straightforward and has no design ambiguity;
- the request is pure codebase research (use Support-Researcher);
- the request is a single bounded analysis (use RnD-Architect or RnD-Ideator).
