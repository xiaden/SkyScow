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
- You need a full design document — use `rnd-manager` or `rnd-dd-author` instead
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

When spawned by `rnd-refiner` in the adversarial design flow, RnD-Ideator reads the shared DD file and appends approach proposals with mandatory web-cited evidence across two turns. In this mode, supply only the DD path:

```
Read [DD_PATH] and append approach proposals with web-cited evidence across two turns.
```
