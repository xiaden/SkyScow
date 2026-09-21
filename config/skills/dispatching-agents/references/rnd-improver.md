# RnD-Improver

Dispatch RnD-Improver to analyze existing code and suggest concrete improvements, or, in adversarial mode, to adapt a production-backed approach into the smallest repository-native realization.

## When to Dispatch

**Dispatch when:**
- You want to improve existing code and need structured suggestions
- An implementation plan needs repository-native realization guidance — "how should approach A fit this repository?"
- RnD-Refiner needs repository-fit adaptation after the selected external evidence is sufficient
- You're evaluating whether an existing module could be restructured for better maintainability
- RnD-Refiner delegates repository-native adaptation to this agent in the adversarial design flow

**Do NOT dispatch when:**
- You need creative ideation — use `rnd-ideator` instead
- You need implementation options analysis — use `rnd-architect` instead
- You need complexity analysis — use `rnd-complexity-advisor` instead
- You need a full design document — use `rnd-manager`; DDAuthor is Manager-only after selected evidence and dispositions
- The improvements are obvious (typos, renaming, simple refactors) — do it yourself

## Dispatch Template

```
Analyze [CODE AREA] and suggest improvements.

Context files to read:
- [paths to code files]
- [any relevant ADRs, patterns, or design docs]

scope: "[files/modules to analyze]"
focus areas: "[specific areas to improve — e.g., error handling, performance, readability, testability]"

Suggest concrete improvements with repository-native realization guidance. In adversarial mode, act as an evidence-backed architecture adapter: prefer existing repository mechanisms, the smallest sufficient adaptation, and explicitly allow `no additional mechanism required`. Evidence earns consideration; it does not earn implementation. On a bounded follow-up, resume the exact persistent Improver session only when RnD-Manager supplies a concrete mapping: only listed Manager-approved `MITIGATE` dispositions may change the realization; preserve `ACCEPT_RISK` and `NOT_APPLICABLE`, leave `DEFER_TO_OWNER` unchanged, and return `NEEDS_DECISION` for missing or ambiguous authority rather than inferring from findings, closure, severity, ownership, or recommendations. Read-only — analysis only.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[CODE AREA]` | What to analyze and improve | "Payment processing pipeline" |
| `scope` | Files/modules to analyze | "src/services/payment/, src/workflows/checkout/" |
| `focus areas` | Specific improvement dimensions | "Error handling (current: untyped errors), testability (current: no DI), performance (N+1 queries)" |

## Expected Output

- Concrete improvement suggestions with rationale
- In adversarial mode, the smallest repository-native realization, reused mechanisms, bounded adapters, and omitted machinery with rationale
- Implementation patterns only where repository evidence shows they are necessary
- Effort estimate per improvement (TRIVIAL/SMALL/MEDIUM)
- Priority ranking (quick wins vs. structural changes)

This agent is **read-only** — it returns suggestions, does not modify code.

## Dispatch Variants

### Repository-Native Adaptation for Chosen Approach

When RnD-Refiner delegates repository-native adaptation after the Manager selects the repository pair:

```
Adapt the chosen production-backed approach using the shared adversarial log at [LOG_PATH] and the selected design context.

Context: [LOG_PATH] and the relevant repository architecture, behavior, files, abstractions, ADRs, dependencies, lifecycle, and runtime boundaries. Identify what the repository already supplies, what conflicts, and the smallest bounded adapter or substitution required. Specialize, simplify, substitute, reuse, or remove parts of the surviving approach as local evidence warrants. Do not broaden capability or invent mechanisms for every implementation dimension; `no additional mechanism required` is valid and desirable. Use external citations only when they materially verify an adaptation or consequential technology/API claim. Append to the shared log for one selected bounded interaction. On a follow-up, resume the exact persistent Improver session only with the concrete Manager mapping; only listed Manager-approved `MITIGATE` items authorize correction. Preserve non-change dispositions and return `NEEDS_DECISION` for missing or ambiguous authority rather than inferring authorization.
```

## GitHub Actions context (when relevant)

If the dispatched work touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence is needed (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); this agent suggests, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the suggestions depend on run/artifact results, require the agent to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
