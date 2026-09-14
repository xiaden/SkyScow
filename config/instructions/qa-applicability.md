# QA Applicability

This file is the **single canonical owner of QA lens applicability**: *which* QA lens runs and the
**observable repository/task fact** that triggered it. It decides **WHEN** a lens applies and **WHAT**
observable fact triggered it.

It does not own **HOW** a lens reviews: specialist review procedures and checklists stay in the
specialist agents and skills. This file's trigger and quality-condition lists define **WHAT**
observable fact is required for a lens to apply, not the specialist's review HOW.

Two vocabularies are owned elsewhere and are referenced, never restated:

- Security-lens triggers are owned by
  `/home/opencode/.config/opencode/skills/security-review/SKILL.md`. This file refers to that skill's
  canonical surface list and never restates the 14-surface list. A matched security surface makes
  focused security review **REQUIRED** per that skill.
- Gate evidence labels (`LOCAL_PASS`, `LOCAL_UNAVAILABLE`, `CI_DEFERRED`, `CI_PASS`) are owned by
  `/home/opencode/.config/opencode/skills/ci-lint-test-gates/SKILL.md`.

## Observable facts only

Every conditional rule in this file keys on an observable repository or task fact: which files and
symbols changed, imports and callers, runtime role, schemas, operations, and the repository's actual
capabilities. QA applicability is never decided by subjective impression.

The following phrases must never be used, here or downstream, as a trigger for a lens or as a reason
a lens does or does not apply:

- "this seems simple"
- "probably unnecessary"
- "the diff is small"
- "correctness review should be enough"
- "I am confident"
- "there is probably no journey"
- "this code looks isolated"
- "low-risk"
- "when appropriate"
- "enough context"

If a lens is not selected, the reason must be an observable fact plus evidence (see
"Evidence-based `NOT_APPLICABLE`").

## Baseline correctness (always)

For every **meaningful implementation change**, independent correctness review is REQUIRED. It is
never made conditional on subjective complexity, diff size, confidence, or perceived risk, and it is
never waived because another lens applies. Correctness is the independent baseline: boundary, journey,
domain-risk, tests, and docs remain separate lenses, and none of those lenses is excused by another
lens's `PASS`. Specialist lenses must not be merged into correctness; correctness remains its own
required lens.

A **meaningful implementation change** is a change that alters observable behavior:

- executable behavior (code that runs),
- runtime behavior (startup, supervision, container/build runtime, process behavior),
- configuration behavior (shipped config, manifests, environment, or defaults that change behavior), or
- policy behavior (agent, skill, command, or instruction text that changes what agents do).

Documentation-only, comment-only, and non-executable-static-metadata changes are **not** a blanket
exemption from specialist review. Each specialist lens independently evaluates its own observable
trigger: any such change that fires a lens's trigger — for example an explicitly requested
documentation change, an operator-facing contract, or a changed agent/tool/skill contract — still
makes that lens **REQUIRED**; it is never made `NOT_APPLICABLE` merely because the change is
documentation, a comment, or non-executable static metadata.

Correctness remains **REQUIRED** for every meaningful implementation or policy behavior, and
`correctness.required` is `true` for every such change (see the meaningful-implementation-change list
above). Agent, skill, command, or instruction text that changes what agents do is **policy behavior**:
it is a meaningful implementation change, so correctness is **REQUIRED**, and it may additionally
require Docs QA when it changes an agent/tool/skill contract.

## Boundary applicability

Boundary review examines state transitions, failure and recovery paths, and degraded states.

Boundary is REQUIRED when the changed surface contains any of these observable triggers:

- persistence or state mutation,
- retries,
- queues,
- job lifecycle,
- process or service lifecycle,
- filesystem mutation,
- cleanup or finalization,
- resumability,
- caching or state synchronization,
- timeout or recovery,
- transactional or partial-success behavior.

A state-transition or degraded-state surface exists -> Boundary REQUIRED. No such surface exists ->
Boundary `NOT_APPLICABLE` **with evidence**.

A model may not declare a state "impossible" without repository-derived evidence. The evidence must
come from the repository (code, config, manifests, schemas, or runtime definitions), not from
assumption.

## Journey applicability

Journey review examines end-to-end observable flows that cross component or runtime boundaries.

Journey is REQUIRED when the changed surface contains any of these observable triggers:

- startup / bootstrap / entrypoint,
- service lifecycle,
- Docker or container runtime,
- shell or process orchestration,
- API request/response,
- UI -> API -> persistence,
- CLI -> service or library,
- persistence round-trips,
- async jobs,
- configuration loading or application,
- event or message processing,
- identifier or data propagation across modules,
- registration or plugin wiring,
- restart / resume.

An observable flow crosses a component or runtime boundary -> Journey REQUIRED.

The following do NOT trigger Journey on their own:

- multiple changed files (file count alone is not a boundary crossing),
- green unit or integration tests (passing isolated tests do not excuse a journey review).

Journey review must look for at least:

- dropped fields,
- stale identifiers,
- missing registration,
- disconnected wiring,
- incorrect sequencing,
- output not reflected downstream,
- restart/retry divergence,
- locally-correct components failing as a flow.

## Domain-risk lens selection

Domain-risk lenses are selected from observable technical surfaces. The numeric bound is a **maximum
of three concurrent DomainRisk reviewer invocations**, not a maximum of three valid lenses: every
matched lens is dispatched, and no matched lens is dropped because of the cap. Candidate lenses, in
canonical order:

| Lens | Select when the observable changed surface involves |
| --- | --- |
| Security | Any surface owned by `/home/opencode/.config/opencode/skills/security-review/SKILL.md` (defer to that skill; do not restate its surface list here) |
| Persistence | storage, schemas, migrations, queries, state durability |
| Concurrency | shared state, locks, parallel execution, races, ordering |
| Filesystem/path | file reads/writes, path resolution, temp files, mounts |
| Protocol/API | wire formats, endpoints, contracts, serialization |
| Frontend state | UI state, rendering, client-side data flow |
| Performance | only when the changed surface introduces or alters hot loops, large-data operations, query behavior, network round trips, allocation-heavy paths, or latency-sensitive behavior |
| Process/configuration | process lifecycle, supervision, environment, shipped configuration |

The canonical lens order is fixed and defined once here, at table order: Security, Persistence,
Concurrency, Filesystem/path, Protocol/API, Frontend state, Performance, Process/configuration. This
order is the only scheduling order used for batch composition. Scheduling order conveys no severity
and no priority.

Batching rule for matched lenses:

- **Zero matched lenses** -> no DomainRisk reviewer invocations.
- **One to three matched lenses** -> all matched lenses are dispatched together in one parallel batch.
- **More than three matched lenses** -> every matched lens is dispatched in deterministic consecutive
  batches of at most three, taken in canonical order, until every matched lens has completed.

Security remains mandatory and cannot be omitted because of the concurrency cap: a matched security
surface is always dispatched. Reviewers inside a batch are independent, never consume one another's
output, and no lens is dispatched more than once.

Record for each selected lens the lens name and the observable trigger. Record lenses that were **not**
selected only where needed to explain why an otherwise plausible lens does not apply.

## Tests applicability

Tests review is REQUIRED when the changed surface contains any of these observable triggers:

- executable behavior changed,
- a regression can be expressed as a test,
- a public or internal contract changed,
- a relevant repository test suite exists,
- existing tests changed or may have become stale.

Raw coverage percentages are never the trigger. Coverage is diagnostic only and this file imposes no
universal coverage percentage; a repository-defined coverage gate is honored when one exists (see
`/home/opencode/.config/opencode/instructions/validation-mandate.md`).

Generation gating — a test is generated only when all of the following hold:

- there is a concrete behavioral gap that can be meaningfully exercised,
- the generated test has a meaningful behavioral oracle,
- the test must run (an unexecuted test is not evidence),
- the test must be independently re-evaluated, not accepted merely because it was generated,
- the test must not merely reproduce the implementation,
- excessive mocking is avoided when a real caller or path can be exercised.

Do not generate artificial tests for documentation-only edits, non-executable static metadata, or
changes whose appropriate evidence is a build, smoke, or runtime check.

## Documentation applicability

Docs review is REQUIRED when the changed surface contains any of these observable triggers:

- public API,
- CLI flags or commands,
- environment variables,
- configuration syntax,
- startup behavior,
- installation or deployment behavior,
- public schemas,
- agent/tool/skill contracts,
- user workflows,
- explicitly requested documentation.

Clarifying observable cases:

- a README typo with no contract change may be Docs `NOT_APPLICABLE` or lightweight;
- installation or deployment documentation for a changed CLI flag or command requires Docs;
- a change to an agent, tool, or skill contract requires Docs.

Universal documentation analysis is forbidden for purely internal implementation detail.

`UNNECESSARY` is not permitted when an observable public or operator contract changed.

When documentation is generated, it must be verified against authoritative code, config, and
manifests rather than trusting fluent generated prose.

## Evidence-based `NOT_APPLICABLE`

A lens may be marked `NOT_APPLICABLE` only on an observable fact plus evidence.

Valid example:

> Journey `NOT_APPLICABLE`: changed symbol is a pure internal transform; no callers outside the
> module; no runtime or user flow changed.

Invalid examples (never sufficient):

- "change is simple"
- "documentation probably does not need updating"
- any reliance on model confidence.

## Analyzer and generator contract

An analyzer runs whenever its applicability trigger fires. Whether the generator then runs is decided
by the analyzer's tier — an analyzer running never by itself forces the generator to run.

- `PASS` and `MINOR_PASS` mean the generator is `NOT_REQUIRED`.
- `MINOR_DISPATCH` and `MAJOR_DISPATCH` require the generator.
- An implementation or systemic escalation does not automatically run the generator.

This section owns tier → generator routing. The "Generation gating" list under "Tests applicability"
owns generation quality gating and remains in force: generator output must still be independently
re-evaluated, not accepted merely because it was generated. The two are complementary and do not
conflict.

The owning manager enforces this contract. It rejects a missing required analyzer, a dispatch-tier
analyzer without generator output, and generator output that has not been independently verified. It
does **not** reject a `PASS`/`MINOR_PASS` run because no generator ran, nor a correct analyzer
escalation that has no generator.

Exactly one generation cycle occurs per analyzer run. The existing tier vocabulary — `PASS`,
`MINOR_PASS`, `MINOR_DISPATCH`, `MAJOR_DISPATCH`, `MAJOR_RAISE` — is preserved unchanged: no tier is
renamed and no tier is invented.

## Canonical classification record

Applicability is recorded once in this shape (the ledger example, not a mandatory serialization
schema):

```text
correctness.required: true
boundary.required: <bool>   boundary.triggers: [...]
journey.required: <bool>    journey.triggers: [...]
domain_risk.lenses: [{ name: <lens>, trigger: <observable fact> }, ...]
tests.required: <bool>      tests.triggers: [...]
docs.required: <bool>       docs.triggers: [...]
```

The record is derivable from observable facts. This file owns the **rules** only: it defines WHEN a
lens applies and the observable fact that triggers it. It does not compute applicability at runtime.

The **owning QA manager** computes the classification **once per run for the actual subject**, records
it in the existing run/review context, and dispatches from that record. Specialists and analyzers
**read the record and do not re-decide it**. Ownership is per subject:

- plan or change run -> the owning QA manager;
- publication candidate -> `QA-PushManager`;
- whole-tree review -> `QA-RepoReviewManager`.

No new agent, subsystem, or persistent metadata store is created solely to carry applicability: the
computation reuses the manager that already owns the run and the run/review context that already
exists. **Downstream orchestration must not re-decide the record:** consumers read the recorded
classification and dispatch accordingly.

## Whole-tree applicability

For a complete-tree subject (a repository or publication review of the whole tree), these same rules
apply against the tree's observable surfaces rather than a diff. Correctness is permanent. Boundary
and journey apply when the tree contains the corresponding observable surfaces — the normal case for
a complete tree — and each is recorded with its trigger.

## Dedupe and reference rule

Every downstream agent, skill, and command must reference this file for WHEN a lens applies and for
its observable trigger. Downstream surfaces must not restate trigger logic; they own HOW the lens
reviews. Specialist checklists must not be moved into this file.
