# RnD-CounterImprover

Dispatch RnD-CounterImprover to provide adversarial critique of implementation patterns — searching for edge cases, integration risks, and library-specific gotchas.

## When to Dispatch

**Dispatch when:**
- RnD-Refiner delegates adversarial pattern critique in the adversarial design flow (Turns 7-8)
- You have proposed implementation patterns and want them stress-tested for real-world risks
- You need evidence-grounded "what could go wrong at implementation time" analysis

**Do NOT dispatch when:**
- You need approach-level critique — use `rnd-counter-ideator` instead
- You need pattern proposals — use `rnd-improver` instead
- You need implementation analysis — use `rnd-architect` instead
- You're doing a standard code review — use QA agents instead

## Dispatch Template

```
Critique the implementation patterns in [DD_PATH].

Read the pattern proposals. Search for edge cases, integration risks, and library-specific gotchas matching each pattern. Rank by context relevance. Append risk assessment sections to the DD.

White-hat adversary — success is measured by how much the final implementation plan improves. Read-only.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[DD_PATH]` | Path to the shared design document with implementation patterns | `artifacts/designs/pending/collab-editing.md` |

## Expected Output

- Risk assessment appended to the shared DD
- Edge cases and integration risks per pattern
- Library-specific gotchas with evidence citations
- Risks ranked by context relevance

This agent is part of the `rnd-refiner` adversarial pipeline. It is typically spawned by RnD-Refiner, not dispatched directly. Direct dispatch is rare and only for standalone adversarial review of existing implementation patterns.

## How It Works

RnD-CounterImprover reads implementation patterns from the shared DD, web-searches for edge cases, integration risks, and library-specific gotchas, ranks risks by context relevance, and appends risk assessment sections. It's a white-hat adversary — its success metric is how much the final implementation plan improves.

## GitHub Actions context (when relevant)

If the dispatched work touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence is needed (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); this agent critiques, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the risk assessment depends on run/artifact results, require the agent to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
