# RnD-ComplexityAdvisor

Dispatch RnD-ComplexityAdvisor to analyze whether code is simpler than it could be — identifying over-engineering, unnecessary abstraction, and structural bloat.

## When to Dispatch

**Dispatch when:**
- You suspect a module or feature is over-engineered
- You're reviewing a new design and want a complexity sanity check
- An implementation introduces abstractions that feel heavy for the problem size
- You're refactoring and want to validate that the new structure is genuinely simpler
- Before committing to a complex architecture — "is there a simpler way?"

**Do NOT dispatch when:**
- You need implementation options — use `rnd-architect` instead
- You need creative ideation — use `rnd-ideator` instead
- The code is trivially simple (obvious from reading it)
- You need a full code review — use QA agents instead

## Dispatch Template

```
Analyze structural complexity of [CODE AREA].

Context files to read:
- [paths to relevant code files]
- [any relevant ADRs or design docs as reference for existing patterns]

scope: "[files/modules/layers to analyze]"
concerns: "[specific concerns — e.g., 'too many layers', 'unnecessary indirection', 'over-abstracted']"

Compare against existing project patterns. Identify over-engineering and unnecessary abstraction. Read-only.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[CODE AREA]` | What to analyze | "Library scan workflow pipeline" |
| `scope` | Files/modules to analyze | "src/workflows/scan/, src/services/scanner/" |
| `concerns` | Specific complexity concerns | "5-layer call chain for a single scan operation — suspect over-abstraction" |

## Expected Output

- Complexity assessment: is the code simpler than it could be?
- Specific instances of over-engineering or unnecessary abstraction
- Comparison against existing project patterns (are we using patterns others don't?)
- Concrete simplification recommendations with rationale

This agent is **read-only** — it returns analysis, does not modify code.

## GitHub Actions context (when relevant)

If the dispatched work touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence is needed (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); this agent analyzes, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the analysis depends on run/artifact results, require the agent to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
