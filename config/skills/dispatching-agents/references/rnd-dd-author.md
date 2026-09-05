# RnD-DDAuthor

Dispatch RnD-DDAuthor only from RnD-Manager, after the complete canonical DD
workflow has produced all required upstream reports. DDAuthor authors or amends
the formal document; it is not an orchestrator.

## Dispatch template

```text
Author the formal DD for [FEATURE] from the supplied evidence.

You must not spawn agents or define a workflow. RnD-Manager already completed
the Librarian, Support-Researcher, full eight-turn Refiner, Architect,
ComplexityAdvisor, and final Estimator stages.

Authoritative user request: [verbatim, unabridged original user request]
Requirement ledger:
- R1: [exact wording] — mandatory | constraint | optional | open detail
- R2: [exact wording] — mandatory | constraint | optional | open detail
Requirements: [requirements]
Upstream artifact paths:
- Librarian: [path]
- Research: [path]
- Adversarial log: [path]
- Architecture/tradeoffs: [path]
- Complexity review: [path]
- Estimate: [path]

Write the DD under artifacts/designs/pending/. If a required input is missing,
return BLOCKED rather than researching around it or inventing content.

Before authoring or amending, compare the DD against every ledger item. Manager
synthesis and upstream reports are evidence, not authority to change the user
request. If they conflict with an explicit requirement, return NEEDS_DECISION or
BLOCKED and quote the requirement. Never convert “must use X when condition Y
holds” into “X is optional”; optional invocation, unavailability, advisory
confidence, or a per-run opt-out does not permit omitting the capability.
```

## Amendment template

```text
Amend the existing DD at [DD PATH] to address these PatternEnforcer findings:
[findings]

Do not start a new workflow or spawn agents. Preserve the existing evidence
trail and return the same DD path plus a change summary for revalidation. This
amendment may correct coverage, clarity, or consistency only. Any change to
behavior, defaults, CLI semantics, required capabilities, or definition of done
requires NEEDS_DECISION and user approval; do not implement it merely at
Manager's request.
```

## Completion

Return the DD path, source artifact paths, completed-section status, summary,
task-conformance status, and blockers. PatternEnforcer approval is performed by
RnD-Manager after your work; do not claim that gate yourself. `DONE` is
prohibited unless task-conformance is `PASS`; otherwise return `BLOCKED` or
`NEEDS_DECISION`.

## GitHub Actions context (when relevant)

If the dispatched work touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence the DD must reflect (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** the author reads evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); it writes the design artifact, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the DD depends on run/artifact results, require the author to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
