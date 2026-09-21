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
- T1: RnD-Ideator (expand credible approaches using external/world evidence)
- T2: RnD-CounterIdeator (falsify external/architectural assumptions, or substantively validate them)
- T3: RnD-Ideator (refine surviving externally supported approaches)
- T4: RnD-CounterIdeator (validate remaining external assumptions, or substantively validate them)
- T5: RnD-Improver (collapse the survivor through repository architecture and behavior)
- T6: RnD-CounterImprover (challenge claimed repository fit and unnecessary mechanisms, then return a concrete continuation payload to RnD-Manager)
- T7: RnD-Improver (resume the exact persistent `improver_session` only after Manager disposition; apply only listed Manager-approved bounded corrections)
- T8: RnD-CounterImprover (resume the exact persistent `counter_improver_session` after T7; verify corrected repository fit, or substantively validate it)
T1–T4 expand and challenge external architecture; T5–T8 reduce and challenge repository fit. Do NOT design the feature yourself — orchestrate the adversarial pipeline.

Requirements: [user requirements or path to requirements doc]
Librarian briefing: [paste briefing or "see attached context"]
Prior decisions to respect: [key constraints]
Output: root-level ADVERSARIAL.md and DD.md in the per-DD bundle under
artifacts/designs/pending/{slug}/. RnD-DDAuthor writes the final DD later.
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

## How the Adversarial Pipeline Works

The standard route has exactly eight turns, but the route is evidence-gathering, not a new authority layer, proposal phase, ledger, state machine, or implementation gate:

1. **Approach generation:** expand credible approaches with external evidence.
2. **Approach critique:** challenge external and architectural assumptions with documented failures.
3. **Approach refinement:** address valid criticisms and drop failures.
4. **Surviving concerns:** validate remaining external assumptions.
5. **Repository-native adaptation:** collapse the survivor through local architecture, behavior, and constraints.
6. **Repository-fit challenge:** test actual paths and unnecessary mechanisms.
7. **Bounded correction:** apply only accepted, repository-native corrections.
8. **Final repository-fit validation:** record applicable risks and human questions, or validate the realization as good enough.

Each turn appends to the shared adversarial log. The result is evidence
for DDAuthor's final DD, not a final DD itself. Refiner and all adversarial agents are observational/recommendatory until the RnD-Manager gate; only Manager-approved `MITIGATE` may authorize the smallest sufficient correction. `ACCEPT_RISK`, `NOT_APPLICABLE`, and `DEFER_TO_OWNER` preserve or route without implementation. T6 pauses after its completed risk/good-enough result and returns `log_path`, the existing `improver_session`, the existing `counter_improver_session`, all findings, and the continuation requirement to RnD-Manager; it must not directly dispatch T7. Manager resumes this same Refiner session with an actual disposition mapping, and Refiner resumes the same Improver session for T7. A Counter turn is substantive when it either supports a material concern or performs a credible attempt to falsify the proposal and concludes `NO_MATERIAL_CONCERNS` / `GOOD_ENOUGH`; credible validation is successful adversarial work, not a failed turn. The route requires exactly eight turns; no turn is skipped or abbreviated, and no turn-count, citation, or evidence completeness becomes a downstream plan obligation.

## GitHub Actions context (when relevant)

If the adversarial process touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence the adversarial turns need (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** the turns read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); they critique/refine, they do not implement or execute the workflow.
- **Result-iteration requirement:** when the process depends on run/artifact results, require the turns to state how collected results feed the next iteration (`gg-actions`).

## Execution boundary contract

At T6, the Refiner pauses and returns this concrete payload to RnD-Manager; it does
not dispatch T7:

```yaml
t6_continuation:
  phase: T6_PAUSED
  log_path: "artifacts/designs/pending/{slug}/ADVERSARIAL.md"
  improver_session: "{existing persistent session id}"
  counter_improver_session: "{existing persistent session id}"
  findings: []
  result: GOOD_ENOUGH | NO_MATERIAL_CONCERNS | FINDINGS
  requires_manager_disposition: true
```

After a real Manager response, T7 consumes the concrete mapping below and resumes
these same sessions:

```yaml
t7_input:
  manager_dispositions:
    - finding_ref: "{T6 finding identifier}"
      disposition: MITIGATE | ACCEPT_RISK | NOT_APPLICABLE | DEFER_TO_OWNER
      provenance: "{source and evidence reference}"
      rationale: "{Manager rationale and applicability}"
  implementation_authorization:
    - finding_ref: "{T6 finding identifier}"
      correction: "{Manager-approved MITIGATE correction}"
  resume_same_refiner_session: true
```

Only listed Manager-approved `MITIGATE` entries authorize corrections; an empty
`implementation_authorization` is valid. Missing or ambiguous disposition authority
returns `NEEDS_DECISION`; neither T6 findings nor recommendations authorize T7.

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
