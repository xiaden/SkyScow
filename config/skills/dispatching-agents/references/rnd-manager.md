# RnD-Manager

Dispatch RnD-Manager when a request needs architectural design, a formal DD,
options and tradeoffs, or R&D scope validation. RnD-Manager is the sole owner
of the complete DD workflow and must orchestrate its workers.

## Formal DD dispatch

```text
Design [FEATURE] and produce a formal DD.

You are the sole DD workflow owner. Run the complete canonical process; do not
create the DD yourself and do not allow DDAuthor to orchestrate other agents.

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

Once DD_REQUIRED is selected, the selected R&D stages are process requirements for producing a trustworthy DD; they are not product requirements and do not become downstream implementation gates. Completion requires the route's recorded DD, decision evidence, and requirement-conformance result. The user request, not an agent summary or DD, is the authoritative product specification.
```

5. **RnD-DDAuthor** writes the formal DD from the authoritative ledger and
   selected architectural decisions. Upstream artifacts are evidence and
   provenance, not additional requirements.
6. **RnD-PatternEnforcer** performs the final requirement-conformance check and
   may identify a real contradiction or missing invariant. It may not require
   tests, docs, citations, or evidence artifacts solely because its checklist
   names them.
7. **RnD-Manager** validates the DD and returns `READY_FOR_PLANNING` only when
   requirements and accepted architecture are coherent.

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
