# RnD-Architect

Dispatch RnD-Architect to get implementation options and tradeoff analysis for a specific problem.

## When to Dispatch

**Dispatch when:**
- You need concrete implementation approaches with tradeoffs for a single decision
- You're evaluating "how would we build X?" without needing a full design document
- You need a focused technical analysis (not creative ideation — use `rnd-ideator` for that)
- You want a tradeoffs matrix to present to stakeholders

**Do NOT dispatch when:**
- You need a full design document — use `rnd-manager` or `rnd-dd-author` instead
- You need creative brainstorming — use `rnd-ideator` instead
- You need effort sizing — use `rnd-estimator` instead
- The problem has no design ambiguity — implement directly
- You need adversarial refinement — use `rnd-refiner` instead

## Dispatch Template

```
Analyze implementation approaches for [PROBLEM].

Context files to read:
- [any relevant code, ADRs, or design docs]

problem: "[concise description of the design problem]"
constraints: "[any hard constraints — tech stack, budget, timeline]"
evaluation criteria: "[2-4 criteria to rank approaches by]"

Return 2-4 concrete approaches with tradeoffs. Read-only — analysis only, no implementation.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[PROBLEM]` | The design problem to analyze | "Caching strategy for library scan results" |
| `problem` | Concise description of the design problem | "Library scan results are recomputed on every query. Need a caching layer that balances freshness with performance." |
| `constraints` | Hard boundaries | "Must work within existing SQLite backend. Cannot add Redis dependency." |
| `evaluation criteria` | 2-4 criteria to rank approaches by | "Latency (<10ms p95), staleness tolerance (<5s), implementation complexity" |

## Expected Output

- 2-4 concrete implementation approaches
- Tradeoffs matrix comparing approaches against evaluation criteria
- Recommended approach with rationale
- File paths and code structure suggestions

This agent is **read-only** — it returns analysis, does not execute or implement.

## Dispatch Variants

### With Pre-Existing Artifact Context

```
Analyze implementation approaches for [PROBLEM].

Context: [paste Librarian briefing or relevant ADR summaries]

problem: "[description]"
constraints: "[constraints including prior ADR decisions]"
evaluation criteria: "[2-4 criteria]"

Return 2-4 concrete approaches with tradeoffs. Read-only.
```

## GitHub Actions context (when relevant)

If the dispatched work touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence is needed (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); this agent analyzes, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the analysis depends on run/artifact results, require the agent to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
