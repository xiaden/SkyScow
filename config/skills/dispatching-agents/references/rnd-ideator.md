# RnD-Ideator

Dispatch RnD-Ideator to generate creative solutions and explore the design space for a problem.

## When to Dispatch

**Dispatch when:**
- You need creative brainstorming — "what are possible ways to solve X?"
- You're in early exploration before committing to an approach
- You want ranked ideas with feasibility assessments
- You need to break out of a narrow solution mindset ("are we missing options?")

**Do NOT dispatch when:**
- You need concrete implementation analysis — use `rnd-architect` instead
- You need a full design document — use `rnd-manager`; DDAuthor is Manager-only after selected evidence and dispositions
- The solution is obvious from existing patterns — implement directly
- You need effort sizing — use `rnd-estimator` instead

## Dispatch Template

```
Generate creative approaches for [PROBLEM].

Context files to read:
- [any relevant code, ADRs, or design docs]

problem: "[concise description]"
constraints: "[hard boundaries — tech stack, budget, timeline]"
success criteria: "[what does a good solution look like?]"

Generate ranked ideas with feasibility assessments. Read-only — ideation only, no implementation.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[PROBLEM]` | The problem to ideate on | "Real-time collaborative editing for notes" |
| `problem` | Concise problem description | "Multiple users need to edit the same note simultaneously without conflicts." |
| `constraints` | Hard boundaries | "Must use existing WebSocket infrastructure. Cannot add operational dependencies." |
| `success criteria` | What a good solution looks like | "Sub-second conflict resolution, no data loss, works offline-first" |

## Expected Output

- Ranked list of creative approaches
- Feasibility assessment per approach (HIGH/MEDIUM/LOW)
- Key tradeoffs and risks per approach
- Recommended top 1-2 approaches for deeper analysis

This agent is **read-only** — it returns ideas, does not execute or implement.

## Dispatch Variants

### Adversarial Design Flow

When spawned by `rnd-refiner` in the adversarial design flow, RnD-Ideator reads the shared adversarial log and performs only the Manager-selected bounded proposal or refinement. In this mode, supply the log path and selected node:

```
Read [LOG_PATH] and return one complete bounded proposal payload or Manager-authorized refinement payload with web-cited evidence. Recommendations are observational: do not select an approach, create requirements, or authorize implementation; the RnD-Manager decides. Return one complete bounded proposal payload with minimal control metadata; Refiner validates and appends it. Recommend, without deciding, the four outcomes where material concerns arise.
```

## GitHub Actions context (when relevant)

If the dispatched work touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence is needed (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); this agent ideates, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the ideation depends on run/artifact results, require the agent to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
