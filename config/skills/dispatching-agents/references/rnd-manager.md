# RnD-Manager

Dispatch RnD-Manager when a request needs architectural design, a formal DD,
options and tradeoffs, or R&D scope validation. RnD-Manager is the sole owner
of the selected DD graph and must orchestrate only the capabilities it selects.

## Formal DD dispatch

```text
Design [FEATURE] and produce a formal DD.

You are the sole DD workflow owner. Compose the smallest sufficient local graph
for this request; do not create the DD yourself and do not allow DDAuthor to
orchestrate other agents.

request_context.path: [artifacts/requests/CTX_<two-word-slug>.md]
Read this conversation snapshot before extracting requirements. It is the
primary-source evidence; `handoff_goal` is operational direction and cannot
replace it. If the path is missing or unreadable, return BLOCKED.

Authoritative user request: [verbatim, unabridged original user request]
Requirement ledger:
- R1: [exact wording] — mandatory | constraint | optional | open detail
The original user request is the sole source of product requirements. Preserve a
verbatim copy and an immutable requirement ledger. Research, adversarial review,
architecture options, complexity analysis, estimates, PatternEnforcer findings,
and verification evidence inform decisions but do not independently create
requirements or implementation gates. Promote a finding only when it is
explicitly adopted into the ledger, an accepted architectural invariant, or a
necessary dependency/contract for satisfying one.
   amendment.

Once DD_REQUIRED is selected, the Manager selects only the R&D capabilities
needed for a trustworthy DD. Selected stages are process evidence, not product
requirements or downstream implementation gates. Completion requires the recorded
DD, routing trace, decision evidence, and requirement-conformance result. The user
request, not an agent summary or DD, remains authoritative.
```

5. **RnD-Manager decision gate** consumes the selected reports and any adversarial
continuation payload. Independently compare CTX, the immutable ledger, accepted
constraints, and selected evidence. Give every material finding exactly one of
`MITIGATE`, `ACCEPT_RISK`, `NOT_APPLICABLE`, or `DEFER_TO_OWNER`, preserving
provenance and applicability. `implementation_authorization` may contain only
Manager-approved `MITIGATE` entries. Return `NEEDS_DECISION` before any resume
when authority or user choice is unresolved; never simulate this gate inside
Refiner.
6. **RnD-DDAuthor** records the accepted handoff in the formal DD. It preserves
requirements and provenance but does not repair, reinterpret, promote, or
complete an incomplete handoff.
7. **PatternEnforcer**, when selected, reports read-only impact evidence to the
owning manager/author; it is not the requirement or design decision gate.
8. **RnD-Manager** returns `READY_FOR_DECOMPOSITION` only after the independent gate,
DD recording, and mandatory lifecycle checks are coherent.

## Research-only dispatch

```text
Research [TOPIC] for [PURPOSE].

Do not create a DD. Dispatch only the bounded workers needed for the question,
then return an analysis report with evidence, constraints, and recommendation.
```

## Required output
RnD-Manager must return route, status, phase, artifact paths, routing trace,
recommendation, any adversarial continuation, disposition mapping,
implementation authorization, blockers, and requirement conformance:

```yaml
routing_trace: []
adversarial_continuation:
  subgraph: external | repository | null
  phase: COMPLETE | PAUSED_FOR_MANAGER | NOT_SELECTED
  log_path: null
  sessions: []
  findings: []
  result: GOOD_ENOUGH | NO_MATERIAL_CONCERNS | FINDINGS | null
manager_dispositions:
  - finding_ref: "{finding identifier}"
    disposition: MITIGATE | ACCEPT_RISK | NOT_APPLICABLE | DEFER_TO_OWNER
    provenance: "{source and evidence reference}"
    rationale: "{independent rationale and applicability}"
implementation_authorization: []
continuation_status: COMPLETE | READY_FOR_MANAGER | NEEDS_DECISION
```

`implementation_authorization` contains only Manager-approved `MITIGATE` entries;
an empty list is valid. Every material finding must have a resolved disposition
before a bounded follow-up or DD authoring.
For a DD, report the selected capabilities, routing trace, and any selected
PatternEnforcer outcome. `DONE` means verified completion, not dispatch.

If any design decision would remove, weaken, defer, disable, invert, or change
the semantics of an explicit requirement, or if authority for a material choice
is ambiguous, return `NEEDS_DECISION`, quote the affected requirement/choice,
provide sources and rationale, and ask the user. Do not instruct DDAuthor to
repair or encode the unresolved change.

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
