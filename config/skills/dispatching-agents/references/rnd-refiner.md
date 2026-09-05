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

**Your job is to spawn adversarial agents across 8 sequential turns:**
- Turn 1: RnD-Ideator (approach proposals)
- Turn 2: RnD-CounterIdeator (adversarial critique of approaches)
- Turn 3: RnD-Ideator (refine surviving approaches)
- Turn 4: RnD-CounterIdeator (surface surviving concerns)
- Turn 5: RnD-Improver (implementation patterns)
- Turn 6: RnD-CounterImprover (pattern risks)
- Turn 7: RnD-Improver (final patterns and mitigations)
- Turn 8: RnD-CounterImprover (open risks and human questions)
Do NOT design the feature yourself — orchestrate the adversarial pipeline.

Requirements: [user requirements or path to requirements doc]
Librarian briefing: [paste briefing or "see attached context"]
Prior decisions to respect: [key constraints]
Output: adversarial log in artifacts/designs/process/ plus the input skeleton in
artifacts/designs/pending/. RnD-DDAuthor writes the final DD later.
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

1. **Approach generation (Turn 1):** RnD-Ideator proposes creative approaches with evidence.
2. **Approach critique (Turn 2):** RnD-CounterIdeator searches for documented failures, postmortems, and pitfalls.
3. **Approach refinement (Turn 3):** RnD-Ideator addresses valid criticisms and drops failures.
4. **Surviving concerns (Turn 4):** RnD-CounterIdeator identifies unresolved risks.
5. **Pattern generation (Turn 5):** RnD-Improver designs implementation patterns.
6. **Pattern critique (Turn 6):** RnD-CounterImprover identifies edge cases and integration risks.
7. **Pattern refinement (Turn 7):** RnD-Improver addresses valid pattern critiques.
8. **Final counter-review (Turn 8):** RnD-CounterImprover records open risks and human questions.

Each turn appends to the shared adversarial log. The result is evidence for
DDAuthor's final DD, not a final DD itself.

## GitHub Actions context (when relevant)

If the adversarial process touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence the adversarial turns need (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** the turns read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); they critique/refine, they do not implement or execute the workflow.
- **Result-iteration requirement:** when the process depends on run/artifact results, require the turns to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
