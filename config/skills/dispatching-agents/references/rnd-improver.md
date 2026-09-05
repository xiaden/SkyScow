# RnD-Improver

Dispatch RnD-Improver to analyze existing code and suggest concrete improvements, or to propose implementation patterns for a chosen design approach.

## When to Dispatch

**Dispatch when:**
- You want to improve existing code and need structured suggestions
- An implementation plan needs concrete patterns — "how should we implement approach A?"
- You're evaluating whether an existing module could be restructured for better maintainability
- RnD-Refiner delegates pattern design to this agent in the adversarial design flow

**Do NOT dispatch when:**
- You need creative ideation — use `rnd-ideator` instead
- You need implementation options analysis — use `rnd-architect` instead
- You need complexity analysis — use `rnd-complexity-advisor` instead
- You need a full design document — use `rnd-dd-author` instead
- The improvements are obvious (typos, renaming, simple refactors) — do it yourself

## Dispatch Template

```
Analyze [CODE AREA] and suggest improvements.

Context files to read:
- [paths to code files]
- [any relevant ADRs, patterns, or design docs]

scope: "[files/modules to analyze]"
focus areas: "[specific areas to improve — e.g., error handling, performance, readability, testability]"

Suggest concrete improvements with implementation patterns. Read-only — analysis only.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[CODE AREA]` | What to analyze and improve | "Payment processing pipeline" |
| `scope` | Files/modules to analyze | "src/services/payment/, src/workflows/checkout/" |
| `focus areas` | Specific improvement dimensions | "Error handling (current: untyped errors), testability (current: no DI), performance (N+1 queries)" |

## Expected Output

- Concrete improvement suggestions with rationale
- Implementation patterns for each suggestion
- Effort estimate per improvement (TRIVIAL/SMALL/MEDIUM)
- Priority ranking (quick wins vs. structural changes)

This agent is **read-only** — it returns suggestions, does not modify code.

## Dispatch Variants

### Pattern Design for Chosen Approach

When RnD-Refiner delegates pattern design after an approach is chosen:

```
Propose implementation patterns for the chosen approach in [DD_PATH].

Context: [DD_PATH] and relevant codebase files.

Propose concrete implementation patterns with mandatory web-cited evidence. Append to DD across two turns.
```

## GitHub Actions context (when relevant)

If the dispatched work touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence is needed (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); this agent suggests, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the suggestions depend on run/artifact results, require the agent to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
