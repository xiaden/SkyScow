# RnD-Refiner

Dispatch RnD-Refiner to run only a Manager-selected bounded adversarial subgraph.
Pair creative agents with adversary critics when the selected external or
repository challenge is materially useful; do not require a ceremonial pipeline.

## When to Dispatch

**Dispatch when:**
- You need a rigorously validated design — not just one person's ideas
- The design space is complex and benefits from adversarial critique
- You want evidence-grounded design decisions (web-cited evidence, postmortems, known failures)
- RnD-Manager delegates adversarial refinement instead of linear ideation

**Do NOT dispatch when:**
- The design is straightforward and doesn't benefit from adversarial review — report the skip to `rnd-manager`; only the Manager may select `rnd-dd-author` after the required evidence and acceptance gates
- You need a quick brainstorming session — use `rnd-ideator` directly
- You need implementation analysis — use `rnd-architect` directly
- The feature is trivial (single module, well-understood pattern)

## Dispatch Template

```
Run adversarial design refinement for [FEATURE].

**Your job is to execute the selected bounded subgraph:**
- External: Ideator proposal → Counter-Ideator challenge, with optional Manager-authorized follow-up.
- Repository: Improver adaptation → Counter-Improver fit challenge, with optional Manager-authorized follow-up.
- Both: run the selected pairs in dependency order; independent Manager-owned evidence gathering remains outside this agent.
Stop a pair on credible `GOOD_ENOUGH`/`NO_MATERIAL_CONCERNS`. Return material findings to RnD-Manager before any correction. Do NOT design the feature yourself — execute only the selected subgraph.

Requirements: [user requirements or path to requirements doc]
Librarian briefing: [paste briefing or "see attached context"]
Prior decisions to respect: [key constraints]
Output: append evidence to `ADVERSARIAL.md` in the existing per-DD bundle when
this is a selected DD subgraph; do not create DD artifacts for plan-only or
research-only routes. RnD-DDAuthor writes the final DD later when `DD_REQUIRED`.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[FEATURE]` | Feature to design with adversarial refinement | "Real-time collaborative editing" |
| `Requirements` | What needs to be built | "Support OAuth2 + MFA, see ASR-012" |
| `Librarian briefing` | Artifact context | Paste briefing or "see attached context" |
| `Prior decisions` | Key constraints from prior ADRs | "Must use existing AuthService (ADR-003)" |

The selected subgraph, dependency edges, iteration cap, and Manager-return contract are **required** — RnD-Refiner executes the bounded graph and does not implement designs or invent additional nodes.

## Expected Output

## Selected subgraph execution

The route is bounded evidence-gathering, not a new authority layer, proposal phase, ledger, state machine, or implementation gate:

- `external`: execute `Ideator → Counter-Ideator`; an optional follow-up requires an explicit Manager disposition and remains limited to the named finding.
- `repository`: execute `Improver → Counter-Improver`; an optional follow-up requires an explicit Manager disposition and remains limited to the named finding.
- `both`: execute both pairs in dependency order; do not add a pair because another pair produced a finding.

Run only the nodes named by `selected_nodes` and stop at `iteration_cap`. Each selected node appends evidence to the shared adversarial log. A credible `NO_MATERIAL_CONCERNS` / `GOOD_ENOUGH` result terminates that pair immediately. Material findings return to RnD-Manager before any correction or resume. Only Manager-approved `MITIGATE` may authorize the smallest sufficient correction; `ACCEPT_RISK`, `NOT_APPLICABLE`, and `DEFER_TO_OWNER` preserve or route without implementation. The result is evidence for DDAuthor's final DD, not a final DD itself.

## GitHub Actions context (when relevant)

If the adversarial process touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence the selected interactions need (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** the turns read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); they critique/refine, they do not implement or execute the workflow.
- **Result-iteration requirement:** when the process depends on run/artifact results, require the selected interaction to state how collected results feed any bounded follow-up (`gg-actions`).

## Execution boundary contract

When a selected evaluator finds a disposition-required issue, the Refiner pauses and returns this concrete payload to RnD-Manager; it does not dispatch correction:

```yaml
continuation:
  phase: PAUSED_FOR_MANAGER
  log_path: "artifacts/designs/pending/{slug}/ADVERSARIAL.md"
  sessions: []
  findings: []
  result: FINDINGS
  requires_manager_disposition: true
```

After a real Manager response, a bounded follow-up consumes the concrete mapping below and resumes only the same selected sessions:

```yaml
manager_follow_up:
  manager_dispositions:
    - finding_ref: "{finding identifier}"
      disposition: MITIGATE | ACCEPT_RISK | NOT_APPLICABLE | DEFER_TO_OWNER
      provenance: "{source and evidence reference}"
      rationale: "{Manager rationale and applicability}"
  implementation_authorization:
    - finding_ref: "{finding identifier}"
      correction: "{Manager-approved MITIGATE correction}"
  resume_selected_sessions: true
```

Only listed Manager-approved `MITIGATE` entries authorize corrections; an empty
`implementation_authorization` is valid. Missing or ambiguous disposition authority
returns `NEEDS_DECISION`; findings or recommendations never authorize a follow-up.

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch. Record selected/skipped capability rationale in the Manager-owned trace.
