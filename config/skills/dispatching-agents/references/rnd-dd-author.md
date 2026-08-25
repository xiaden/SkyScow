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
```

## Amendment template

```text
Amend the existing DD at [DD PATH] to address these PatternEnforcer findings:
[findings]

Do not start a new workflow or spawn agents. Preserve the existing evidence
trail and return the same DD path plus a change summary for revalidation.
```

## Completion

Return the DD path, source artifact paths, completed-section status, summary,
and blockers. PatternEnforcer approval is performed by RnD-Manager after your
work; do not claim that gate yourself.
