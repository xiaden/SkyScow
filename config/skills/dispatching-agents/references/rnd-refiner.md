# RnD-Refiner

Dispatch RnD-Refiner to run the full adversarial design refinement pipeline — pairing creative agents with adversary critics across multiple turns to produce an evidence-grounded, battle-tested design.

## When to Dispatch

**Dispatch when:**
- You need a rigorously validated design — not just one person's ideas
- The design space is complex and benefits from adversarial critique
- You want evidence-grounded design decisions (web-cited evidence, postmortems, known failures)
- RnD-Manager delegates adversarial refinement instead of linear ideation

**Do NOT dispatch when:**
- The design is straightforward and doesn't benefit from adversarial review — use `rnd-dd-author` directly
- You need a quick brainstorming session — use `rnd-ideator` directly
- You need implementation analysis — use `rnd-architect` directly
- The feature is trivial (single module, well-understood pattern)

## Dispatch Template

```
Run adversarial design refinement for [FEATURE].

**Your job is to spawn adversarial agents across 8 turns:**
- Turn 1-2: RnD-Ideator (approach proposals)
- Turn 3-4: RnD-CounterIdeator (adversarial critique of approaches)
- Turn 5-6: RnD-Improver (implementation patterns for chosen approaches)
- Turn 7-8: RnD-CounterImprover (adversarial critique of patterns)
Do NOT design the feature yourself — orchestrate the adversarial pipeline.

Requirements: [user requirements or path to requirements doc]
Librarian briefing: [paste briefing or "see attached context"]
Prior decisions to respect: [key constraints]
Output: Refined design document in artifacts/designs/pending/
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[FEATURE]` | Feature to design with adversarial refinement | "Real-time collaborative editing" |
| `Requirements` | What needs to be built | "Support OAuth2 + MFA, see ASR-012" |
| `Librarian briefing` | Artifact context | Paste briefing or "see attached context" |
| `Prior decisions` | Key constraints from prior ADRs | "Must use existing AuthService (ADR-003)" |

The bolded turn-by-turn spawn instructions are **required** — RnD-Refiner orchestrates the adversarial pipeline, not implements designs itself.

## Expected Output

- A shared design document in `artifacts/designs/pending/`
- Approach proposals with web-cited evidence
- Adversarial critiques ranked by context relevance
- Implementation patterns with risk assessments
- Validated final design ready for planning

## How the Adversarial Pipeline Works

1. **Ideation (Turns 1-2):** RnD-Ideator proposes creative approaches with evidence
2. **Counter-Ideation (Turns 3-4):** RnD-CounterIdeator critiques each approach — searching for documented failures, postmortems, and pitfalls
3. **Improvement (Turns 5-6):** RnD-Improver designs implementation patterns for the surviving approaches
4. **Counter-Improvement (Turns 7-8):** RnD-CounterImprover critiques patterns — edge cases, integration risks, library-specific gotchas

Each turn appends to the shared DD file. The result is a design that has survived adversarial scrutiny — measurably better than a single-pass design.
