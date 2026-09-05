# RnD-CounterIdeator

Dispatch RnD-CounterIdeator to provide adversarial critique of proposed design approaches — searching for documented failures, postmortems, and pitfalls.

## When to Dispatch

**Dispatch when:**
- RnD-Refiner delegates adversarial critique in the adversarial design flow (Turns 3-4)
- You have proposed approaches and want them stress-tested against real-world failure data
- You need evidence-grounded "why this might fail" analysis

**Do NOT dispatch when:**
- You need creative proposals — use `rnd-ideator` instead
- You need implementation analysis — use `rnd-architect` instead
- You need pattern critique — use `rnd-counter-improver` instead
- You're doing a standard design review — this is for adversarial refinement only

## Dispatch Template

```
Critique the proposed approaches in [DD_PATH].

Read the approach proposals. Search for documented failures, postmortems, and known pitfalls matching each approach. Rank criticisms by context relevance. Append critique sections to the DD.

White-hat adversary — success is measured by how much the final design improves, not how many problems are found. Read-only.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[DD_PATH]` | Path to the shared design document with approach proposals | `artifacts/designs/pending/collab-editing.md` |

## Expected Output

- Adversarial critique appended to the shared DD
- Documented failures and postmortems matching proposed approaches
- Pitfalls ranked by context relevance
- Concrete risks with evidence citations

This agent is part of the `rnd-refiner` adversarial pipeline. It is typically spawned by RnD-Refiner, not dispatched directly. Direct dispatch is rare and only for standalone adversarial review of existing proposals.

## How It Works

RnD-CounterIdeator reads approach proposals from the shared DD, web-searches for documented failures and postmortems that match each approach, ranks criticisms by how relevant they are to the specific context, and appends critique sections. It's a white-hat adversary — its success metric is how much the final design improves, not how many problems it finds.

## GitHub Actions context (when relevant)

If the dispatched work touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence is needed (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); this agent critiques, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the critique depends on run/artifact results, require the agent to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
