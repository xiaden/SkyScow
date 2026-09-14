---
name: decomposing-design-documents
description: Turn an accepted design document into dependency-ordered implementation plans, contracts, and cross-validation. Use when the user asks to decompose a design into multiple coordinated plans; do not use for a single plan or plan execution—use Exec-Planner or feature-execution.
---

# Decomposing Design Documents

Pipeline for turning requirements or a design document into a set of validated, dependency-ordered implementation plans. Each plan is self-contained, references concrete codebase patterns, and declares its contracts for downstream plans.

```
Requirements → [RnD-Manager DD workflow → DDAuthor] → Design Doc → Decompose → Initialize Ledger → Plan in Rounds → Cross-Validate
     ↓               ↓             ↓            ↓              ↓                    ↓                ↓
  Optional    DD Author agent   Already has  parts/README  CONTRACTS.md    artifacts/plans/pending/TASK-*-{A..Z}.md  Fixes
              for new features    one?
```

### Phase Quick Reference

| Phase | Action | Output |
 | --- | --- | --- |
 | 0 (Optional) | Dispatch DDAuthor if no design doc exists | `artifacts/designs/pending/DD-{feature}.md` |
 | 0.5 | DD Acceptance Gate — confirm accepted status and compare the ledger against the verbatim user request | Recorded comparison; `REQUIREMENT_DRIFT` on omission/weakening |
 | 1 | Decompose design doc into lettered parts | `artifacts/designs/parts/{feature}/README.md` |
 | 2 | Create contracts ledger | `artifacts/designs/parts/{feature}/CONTRACTS.md` |
 | 3 | Dispatch Exec-Planner per part, validate, update ledger, close contract ownership | `artifacts/plans/pending/TASK-{feature}-{letter}-*.md` |
 | 4 | Cross-validate all plans for gaps and conflicts | Fixes applied to plan files |
 | 5 | Supersession sweep — retire superseded DDs/plans with back-pointers | Updated `Status`, back-pointers, clean `pending/` |

Phase 5 is the terminal archival/supersession phase. It is distinct from execution-plan phases and must run after cross-validation and QA readiness; a superseded artifact is removed from the executable set before any dispatch.

## Agent Integration

This skill may dispatch agents from the `.opencode/agents/` hierarchy:

 | Agent | When Used |
 | ------- | ----------- |
  | `RnD-Manager` | Phase 0: Run the complete DD workflow when requirements exist but no design doc |
 | `Exec-Planner` | Phase 3: For each plan in dependency order |

See [.opencode/agents/](.opencode/agents/) for agent specifications.

---

## Hard Rules

These exist because every one was violated during real usage and caused drift or errors.

### Planning Integrity
_(Ensure every plan is authored correctly, ordered correctly, and scoped to a single subagent dispatch)_

1. **Never write plans directly.** Always dispatch to the Exec-Planner agent. Direct plan authoring skips codebase research and produces layer violations, wrong method signatures, and missing patterns.
2. **Never plan out of dependency order.** A plan referencing methods from an unplanned upstream part will guess signatures.
3. **Never combine parts into one subagent call.** Each part gets its own dispatch with focused context.

### Validation & Ledger Rules
_(Govern quality gates and the anti-drift ledger)_

4. **Never skip the ledger update.** The contracts ledger is the only mechanism preventing cross-plan drift. Update it after every validated plan.
5. **Never batch-validate.** Validate each plan immediately after creation. Errors found after all plans exist require multi-file fixes.

### Session Rules
_(Govern continuity across context boundaries)_

6. **If context budget is exhausted, stop at the round boundary.** The ledger preserves all progress. A new session resumes cleanly.

### Quality Gate Integration
_(Ensure plans account for the implementation workflow selected by the changed surface and the repository's actual capabilities)_

7. **Every plan must state the verification steps selected by its changed surface and the repository's capabilities.** Do not assume a project test suite exists and do not default to generic commands (`npm test`, `npx tsc`); repository-defined commands take precedence. Select the verification burden from the observable surface and the repository's real capabilities, per `/home/opencode/.config/opencode/instructions/validation-mandate.md`. Coverage, when the repository supports it, is diagnostic or governed by the repository's own threshold — this doctrine prescribes no universal coverage percentage. A plan that omits the verification its surface requires is incomplete.
8. **Every plan must account for the quality gates its surface requires: code review always; security review only where an observable security-sensitive surface changed.** The planner must not assume implementation is done after writing code — review precedes commit.
9. **Plans that change an observable security-sensitive surface must include a security review step.** Select the checklist from `/home/opencode/.config/opencode/skills/security-review/SKILL.md`, which is the canonical owner; reference it, never restate or weaken it. Security-sensitive surfaces are observable facts: authentication/authorization, payments/financial logic, secrets/credentials, external or user input, persisted/sensitive data, deployment/security-header configuration, and agent/MCP/plugin/permission configuration. Plans without such a surface do not carry a mandatory security review step.

---

## Phase 0: Create Design Document (Optional)

**Entry criteria:** Requirements exist but no design document has been created yet.
**Exit criteria:** Design document created, reviewed by user, and ready for decomposition.

**Skip this phase if:** A complete and reviewed design document already exists at `artifacts/designs/pending/DD-{feature}.md`

If the user has requirements but no design doc, dispatch RnD-Manager for its
complete formal DD workflow. Do not dispatch DDAuthor directly; it is the final
authoring stage owned by Manager:

```yaml
# Dispatch to RnD-Manager
contextFiles:
  - AGENTS.md                                      # Architecture rules
  - {layer_instructions_file}  # Layer patterns

task:
  type: CREATE
  title: "{feature title}"
  requirements:
    - "{requirement 1 from user}"
    - "{requirement 2 from user}"
  researchFocus:
    - "existing patterns for {similar feature}"
    - "current {domain} implementation"
```

**After RnD-Manager returns, handle each status:**

| Status | Action |
| --- | --- |
| `DONE` | Design doc created at `artifacts/designs/pending/DD-{feature}.md`. Present to user for review; once approved, proceed to Phase 1. |
| `NEEDS_DECISION` | Present Manager's questions to the user. Collect answers. Re-dispatch with answers appended to requirements. Do not proceed to Phase 1 until `DONE` is returned. |
| `BLOCKED` | Critical information is missing or a DD stage failed. Stop execution and discuss the blocker with the user. Do not re-dispatch until the blocker is resolved. |

---

## Phase 1: Decompose

**Entry criteria:** A complete and reviewed design document exists at `artifacts/designs/pending/DD-{feature}.md`.
**Exit criteria:** `artifacts/designs/parts/{feature}/README.md` created and reviewed by user.

**Input:** Design document (e.g., `artifacts/designs/pending/DD-{feature}.md`)
**Output:** `artifacts/designs/parts/{feature}/README.md`

Read the design doc. Identify natural part boundaries:

 | Criterion | Rule |
 | --- | --- |
 | Layer boundaries | Parts touching different architectural layers → separate |
 | System boundaries | Backend vs plugin vs frontend → separate |
 | Dependency depth | No part depends on more than 2 others |
 | Session scope | Each part ≤ 12 plan steps (≤ 2 phases) |
 | Diamond avoidance | If parts A→C and B→C share most context → merge A+B |
 | Risk surface | Consult the canonical applicability classification in `/home/opencode/.config/opencode/instructions/qa-applicability.md`; for security applicability, use the canonical surfaces and triggers owned by `/home/opencode/.config/opencode/skills/security-review/SKILL.md`. When the security lens is matched, flag security review in the plan. High-risk parts should be planned first to surface issues early. |
 | Complexity | Estimate per part: TRIVIAL/SMALL/MEDIUM/LARGE/EPIC. Use for model routing and session budget planning. |

Assign letters (A, B, C...) in topological order. Group into execution rounds.

Create `artifacts/designs/parts/{feature}/README.md`:

```markdown
# {Feature} — Implementation Parts

## Parts

 | Part | Title | Depends On | Layers | 
 | --- | --- | --- | --- | 
 | A | {name} | None | persistence | 
 | B | {name} | A | workflow, service, interface | 
...

## Dependency Graph
{ASCII art}

## Execution Rounds
Round 1: A, G (no deps)
Round 2: B, D, E (depend on Round 1 outputs)
Round 3: F (depends on Round 2 outputs)

## Per-Part Scope

### Part A: {title}
{3-5 sentences: what this creates, files touched, contracts exposed downstream}

Detailed scope: See `PART-A-scope.md`
```

**Per-part scope documents.** Each part gets a detailed scope document in `artifacts/designs/parts/{feature}/PART-{letter}-scope.md` containing file paths, contracts, integration details, and testing requirements. These specs absorb implementation detail that does not belong in the DD.

Present the README to the user for review before proceeding.

### Phase 1 Validation: DD Content Audit

Before presenting the README, verify:
- [ ] DD contains zero non-design content (no file mappings, specifications, dependency graphs, contracts, or debate transcripts)
- [ ] DD is under 200 lines

If either fails, extract implementation details to part scope documents before proceeding.

---

## Phase 2: Initialize Contracts Ledger

**Entry criteria:** `artifacts/designs/parts/{feature}/README.md` exists and has been reviewed.
**Exit criteria:** `artifacts/designs/parts/{feature}/CONTRACTS.md` created with architecture rules and empty contract sections.

**Output:** `artifacts/designs/parts/{feature}/CONTRACTS.md`

The contracts ledger accumulates verified facts from completed plans. Downstream Exec-Planner subagents receive it as context, replacing guesswork with concrete signatures.

Create from template — see [references/ledger-format.md](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/ledger-format.md).

Initial content:

- Feature name and design doc reference
- Architectural rules relevant to this feature (extracted from `AGENTS.md`)
- Empty sections: Collections & Methods, API Contracts, DTOs, Decisions

**The ledger must exist before any Exec-Planner subagent is dispatched.**

---

## Phase 3: Plan in Rounds

**Entry criteria:** Both `README.md` and `CONTRACTS.md` exist under `artifacts/designs/parts/{feature}/`.
**Exit criteria:** All plans validated, `CONTRACTS.md` updated after each plan, all rounds complete.

For each execution round from the README:

### 3a. Dispatch Exec-Planner Agent

For each part in the round, dispatch the Exec-Planner agent. See [references/subagent-protocol.md](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/subagent-protocol.md) for the full dispatch protocol including prompt structure, critical rules, and common mistakes.

```yaml
# Dispatch to Exec-Planner agent (see .opencode/agents/exec-planner.md)
contextFiles:
  - artifacts/designs/pending/DD-{feature}.md              # Design doc
  - artifacts/designs/parts/{feature}/README.md            # Parts breakdown
  - artifacts/designs/parts/{feature}/CONTRACTS.md         # Current contracts
  - {layer_instructions_file}          # Per layer in this part

task:
  type: CREATE
  feature: "{feature}"
  part: "{letter}"
  partScope: "{scope from README}"              # 3-5 sentence scope summary
  priorContracts: true                          # Ledger has upstream methods
```

**Parallel dispatch** within a round is allowed — parts in the same round have no mutual dependencies. But only if token budget permits; otherwise dispatch sequentially within the round.

### 3b. Validate Plan

After receiving subagent output:

1. Save to `artifacts/plans/pending/TASK-{feature}-{letter}-{descriptor}.md`
2. Run `plan_read` — must parse without errors. Schema reference: [references/PLAN_MARKDOWN_SCHEMA.json](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/PLAN_MARKDOWN_SCHEMA.json)
3. Quick-scan for:
   - **Layer violations** — workflow receiving a service, component importing interface
   - **Missing verification steps** — the plan omits the verification its changed surface requires, or assumes generic commands (`npm test`, `npx tsc`) instead of repository-defined ones (see `/home/opencode/.config/opencode/instructions/validation-mandate.md`)
    - **Missing quality gate steps** — code review always; when the canonical applicability classification in `/home/opencode/.config/opencode/instructions/qa-applicability.md` marks the security lens as matched using the canonical surfaces and triggers owned by `/home/opencode/.config/opencode/skills/security-review/SKILL.md`, include security review and select its checklist
   - **Coding standards violations** — mutation patterns, hardcoded values, missing error handling
   - **References to methods not in the contracts ledger or existing codebase**
   - **Step count** (>12 steps → consider splitting)
   - **TDD compliance** — plans for behavioral changes should specify surface-dependent behavioral evidence; where the repository supports it, test-before-implementation (RED → GREEN → REFACTOR). Coverage thresholds are repository-defined, never a universal target

Fix issues before proceeding. Re-run `plan_read` after fixes.

### 3c. Update Contracts Ledger

After validating **each plan** (not after each round), update CONTRACTS.md:

 | What to record | Example |
 | --- | --- |
  | Methods created | `resolve_file_to_library(db: Database, file_id: str) -> LibraryFileDict` |
  | API endpoints | `POST /api/v1/navidrome/similar-track` — body: SimilarTracksRequest, auth: verify_key, returns: SimilarTracksResponse |
 | DTOs | `TasteProfile(nd_user, clusters, backbone_id, total_track_count, generated_at_ms)` |
 | Collections | `navidrome_play_history` — _key: `{nd_user}:{nd_id}`, indexes: [...] |
 | Decisions | "Workflows take `db: Database` directly, not service wrappers" |

### 3d. Proceed to Next Round

The next round's subagents receive the updated ledger. This is the anti-drift mechanism.

---

## Phase 4: Cross-Validate

**Entry criteria:** All parts have plans in `artifacts/plans/pending/TASK-{feature}-{A..Z}-*.md`, each individually validated.
**Exit criteria:** All cross-validation checks pass or issues are fixed; results presented to user.

After all plans exist and are individually valid:

 | Check | What to look for |
 | --- | --- |
 | **Dependency completeness** | Every method/API called by a plan is defined in a prior plan's steps |
 | **Contract consistency** | JSON shapes referenced by multiple plans (e.g., API response consumed by plugin AND generated by backend) match exactly |
 | **Layer compliance** | No workflow receives a service. No component imports interfaces. Check against project architecture rules |
  | **Quality gates** | Every plan includes a code review step and the verification steps its changed surface requires using repository-defined commands (`/home/opencode/.config/opencode/instructions/validation-mandate.md`); a security review step only where an observable security-sensitive surface changed (`/home/opencode/.config/opencode/skills/security-review/SKILL.md`). No plan assumes implementation is complete without these gates |
 | **Coverage** | Every design doc section maps to at least one plan |
 | **Gaps** | Methods needed downstream but never created upstream |
 | **Overlap** | Two plans creating the same artifact |
  | **Verification consistency** | Each plan states the verification its changed surface requires using repository-defined commands (`/home/opencode/.config/opencode/instructions/validation-mandate.md`). Drift is a plan that assumes a universal pattern or coverage target instead of the surface-selected evidence |

Fix issues by editing plan files directly. Update CONTRACTS.md if fixes change any contracts.

Present the cross-validation results to the user with specific issues and fixes applied.

---

## After Planning: Quality Handoff

**The planning pipeline produces validated plans. The implementation workflow takes over from here.**

```
Plans → Implementation (behavioral evidence where the change is behavioral) → Code Review → Security Review (only when a security-sensitive surface changed) → Verification → Commit
```

Each plan must account for this full pipeline — not just the coding steps:

 | Phase | Requirement | Plan Must Include |
 | --- | --- | --- |
 | **Behavioral Evidence** | Surface-dependent; RED → GREEN → REFACTOR where the repository supports it | Test-before-implementation steps with the behavioral evidence the changed surface requires; coverage thresholds are repository-defined |
 | **Code Review** | Mandatory after writing code | Explicit code review step; use code-reviewer agent |
 | **Security Review** | Conditional on an observable security-sensitive surface | Security review step only for plans whose changed surface is security-sensitive; checklist owned by `/home/opencode/.config/opencode/skills/security-review/SKILL.md` |
 | **Verification** | The verification steps the changed surface requires, using repository-defined commands; no universal coverage target (`/home/opencode/.config/opencode/instructions/validation-mandate.md`) | Verification step at end of each plan phase |
 | **Commit** | Conventional commits, no console.log | Cleanup and commit step |

**Plans that skip these gates create rework.** The Exec-Planner agent should embed them as explicit steps, not rely on out-of-band processes. When reviewing plans during Phase 3b and Phase 4, treat missing quality gate steps the same as missing implementation steps — they are equally required.

The `feature-execution` skill handles the execution side. If plans are produced without quality gate steps, the execution pipeline may need to inject them ad-hoc, which increases drift risk.

---

## Context Budget Management

Large features will exceed a single session. The skill is designed for this.

**The contracts ledger IS the continuity artifact.** When resuming in a new session:

1. Read `artifacts/designs/parts/{feature}/README.md` — execution rounds
2. Read `artifacts/designs/parts/{feature}/CONTRACTS.md` — all completed decisions
3. Check which plans exist in `artifacts/plans/pending/TASK-{feature}-*.md`
4. Resume at the next incomplete round

**Budget estimation:** Each Exec-Planner subagent dispatch consumes ~3-5k tokens of orchestrator context (prompt construction + result processing + ledger update). A 7-part feature needs ~25-35k tokens of orchestrator budget. Plan for 4-5 parts per session.

**If budget is tight within a round:**

- Finish the current plan dispatch + validation + ledger update
- Stop at the round boundary
- Do NOT write remaining plans directly to "save time"

---

## Validation Checklist

Before declaring feature planning complete:

- [ ] All parts have plans in `artifacts/plans/pending/TASK-{feature}-{A..Z}-*.md` **→ No gaps**
- [ ] All plans parse via `plan_read` **→ Schema compliance**
- [ ] CONTRACTS.md has entries for every method/API/DTO across all plans **→ Ledger complete**
- [ ] Cross-validation found no unresolved issues **→ Coherence**
- [ ] No plan references a method not defined in a prior plan **→ Dependency order correct**
- [ ] User has reviewed README and CONTRACTS.md **→ Alignment**
- [ ] Every plan includes the verification steps its changed surface requires, using repository-defined commands rather than assumed generic commands (`/home/opencode/.config/opencode/instructions/validation-mandate.md`) **→ Verification loop**
- [ ] Every plan includes a code review step, and a security review step only where an observable security-sensitive surface changed **→ Quality gates**
- [ ] Plans whose changed surface is security-sensitive have a security review step selected from `/home/opencode/.config/opencode/skills/security-review/SKILL.md` **→ Security mandate**
- [ ] No plans contain hardcoded values, mutation patterns, or console.log references **→ Coding standards**
- [ ] Plans for behavioral changes specify the surface-dependent behavioral evidence the repository supports (RED → GREEN → REFACTOR where applicable); no universal coverage target **→ Behavioral evidence**

---

## References

Reference files loaded on demand. Read when you need detail beyond the core workflow.

### [ledger-format.md](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/ledger-format.md)

CONTRACTS.md template and update rules. Use during Phase 2 (initialization) and Phase 3c (updating after each plan). Covers the full template with section-by-section format, field requirements, and the six update rules (append-only, full signatures, date-stamping, etc.).

### [subagent-protocol.md](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/subagent-protocol.md)

How to construct Exec-Planner subagent dispatch calls that produce correct, drift-free plans. Use during Phase 3a (dispatch). Covers prompt structure (TASK → DESIGN REF → CONTRACTS → OUTPUT → CONSTRAINTS), critical rules (inline ledger content, scope boundaries, one part per dispatch), and common subagent mistakes with fixes.

### [PLAN_MARKDOWN_SCHEMA.json](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/PLAN_MARKDOWN_SCHEMA.json)

JSON Schema for task plan markdown files. Use during Phase 3b (validation) to verify plan structure — required fields (`title`, `phases`), phase numbering, flat step lists (no nesting), and annotation format. The plan parser consumes this schema; `plan_read` failures often trace to schema violations.

### [ADR_MARKDOWN_SCHEMA.json](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/ADR_MARKDOWN_SCHEMA.json)

JSON Schema for Architecture Decision Record markdown files. Relevant when a plan's implementation spawns an ADR. Covers required metadata (`status`, `date`, `tags`), required sections (`Context`, `Decision`, `Consequences`), and optional fields (`source_log`, `supersedes`).


## Lifecycle and Contract Gates

### Phase 0.5: DD Acceptance Gate

Before decomposition, the DD must have a recognized accepted status (`Accepted` or `Complete (accepted)`). An `Accepted` DD may remain in `pending/` only when its metadata explicitly names the prerequisite disposition, owner, and next transition condition; without those fields it is stale/invalid and cannot be decomposed, executed, or archived as complete. A `Complete (accepted)` DD belongs in the accepted lifecycle location. Compare the DD requirement ledger against the verbatim original user request and record that comparison. If any ledger item is omitted, weakened, deferred, inverted, or contradicted, stop with `REQUIREMENT_DRIFT`; do not decompose.

### Phase 3 Contract Ownership Closure

Every plan's `Ownership` must name every file containing a call site of any symbol whose signature, return type, or behavior the plan changes. A handoff annotation is not ownership and cannot close a residual. Perform a call-graph/import check using the repository callgraph/import tooling (for example, `aft_callgraph` callers/impact plus language-aware import analysis) and record its evidence: list the resolved edges and the unresolved edges separately, then manually dispose of every unresolved edge (name the reason it is safe, or the follow-up that resolves it). Any signature or return-type change requires a non-mock integration test covering the real caller path — a test that exercises a mocked caller does not establish ownership closure.

### Phase 5: Supersession Sweep

When a later artifact supersedes a DD or plan, update the superseded file's `Status`, add a back-pointer, and remove it from the executable set. Do not leave superseded work in `pending/`.

### Anti-Churn and Ledger Rules

- Each feature has exactly one authoritative requirement ledger. Amendments append a dated amendment or fully supersede the ledger; never create duplicate section numbers or stacked contradictory clauses.
- Remediation reopens the owning plan, or is one bounded bridge with named predecessor and successor. Lettered/generational families (R, D2R, Q3-A..K) are permitted **only** under the successor-graph rules below.

### Successor-Graph Rules (generational families)

A generational family is allowed when every condition below holds; otherwise remediation must reopen the owning plan:

1. **Explicit successor graph.** Record each generation as an explicit predecessor → successor edge with a bounded scope (the specific symbols/files it reworks) and a rationale for why the predecessor's step cannot simply be reopened.
2. **No flat-model violation.** The successor edge must be representable: the successor depends on, and does not silently replace, the predecessor. Do not leave a successor for which no dependency edge can be drawn.
3. **Supersession metadata and back-pointers.** The predecessor's `Status` must be updated to `Superseded`, and both files must carry matching back-pointers (predecessor names the successor; successor names the predecessor).
4. **Exec-PlanGate approval.** A generational family counts toward its coordinated plan group and requires a recorded current `Exec-PlanGate: PASS` covering the successor graph before execution; without that approval the family is not executable.
- Validate plans individually at creation time; do not batch-validate.
