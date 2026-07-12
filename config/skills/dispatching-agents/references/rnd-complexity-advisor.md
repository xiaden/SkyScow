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
