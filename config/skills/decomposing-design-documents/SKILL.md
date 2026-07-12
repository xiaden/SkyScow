---
name: decomposing-design-documents
description: Use when decomposing a design document into dependency-ordered implementation plans. Handles the full pipeline from design document to validated, cross-referenced plan files with minimal drift. Trigger when **any** of the following are true, with user requests (4) taking priority over the other conditions: (1) the feature involves 3+ implementation parts, (2) it spans multiple architectural layers, (3) it requires coordination across multiple sessions, or (4) the user explicitly asks to break down a design doc into implementation plans. Not for single plans or simple tasks — use the Exec-Planner subagent directly for those.
applyTo: artifacts/plans/**, artifacts/designs/**
---

# Decomposing Design Documents

Pipeline for turning requirements or a design document into a set of validated, dependency-ordered implementation plans. Each plan is self-contained, references concrete codebase patterns, and declares its contracts for downstream plans.

```
Requirements → [DDAuthor] → Design Doc → Decompose → Initialize Ledger → Plan in Rounds → Cross-Validate
     ↓               ↓             ↓            ↓              ↓                    ↓                ↓
  Optional    DD Author agent   Already has  parts/README  CONTRACTS.md    artifacts/plans/pending/TASK-*-{A..Z}.md  Fixes
              for new features    one?
```

### Phase Quick Reference

| Phase | Action | Output |
 | --- | --- | --- |
| 0 (Optional) | Dispatch DDAuthor if no design doc exists | `artifacts/designs/pending/DD-{feature}.md` |
| 1 | Decompose design doc into lettered parts | `artifacts/designs/parts/{feature}/README.md` |
| 2 | Create contracts ledger | `artifacts/designs/parts/{feature}/CONTRACTS.md` |
| 3 | Dispatch Planner per part, validate, update ledger | `artifacts/plans/pending/TASK-{feature}-{letter}-*.md` |
| 4 | Cross-validate all plans for gaps and conflicts | Fixes applied to plan files |

## Agent Integration

This skill may dispatch agents from the `.opencode/agents/` hierarchy:

 | Agent | When Used |
 | ------- | ----------- |
 | `DDAuthor` | Phase 0: When requirements exist but no design doc |
 | `Planner` | Phase 3: For each plan in dependency order |

See [.opencode/agents/](.opencode/agents/) for agent specifications.

---

## Hard Rules

These exist because every one was violated during real usage and caused drift or errors.

### Planning Integrity
_(Ensure every plan is authored correctly, ordered correctly, and scoped to a single subagent dispatch)_

1. **Never write plans directly.** Always dispatch to the Planner agent. Direct plan authoring skips codebase research and produces layer violations, wrong method signatures, and missing patterns.
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
_(Ensure plans account for the full implementation workflow: TDD → review → verify → commit)_

7. **Every plan must include the full verification loop.** Lint alone is insufficient — plans must include explicit steps for type checking, test execution (with coverage targets), and build verification. A plan without these steps is incomplete.
8. **Every plan must account for quality gates.** Plans must include steps for code review and security review. Review before commit — the planner must not assume implementation is done after writing code.
9. **Plans touching auth, data, or I/O must include security review steps.** The security checklist (OWASP top 10, input validation, secret management) applies — plans that skip this create downstream rework.

---

## Phase 0: Create Design Document (Optional)

**Entry criteria:** Requirements exist but no design document has been created yet.
**Exit criteria:** Design document created, reviewed by user, and ready for decomposition.

**Skip this phase if:** A complete and reviewed design document already exists at `artifacts/designs/pending/DD-{feature}.md`

If the user has requirements but no design doc, dispatch the DDAuthor agent:

```yaml
# Dispatch to DDAuthor agent
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

**After DDAuthor returns, handle each status:**

| Status | Action |
| --- | --- |
| `DONE` | Design doc created at `artifacts/designs/pending/DD-{feature}.md`. Present to user for review; once approved, proceed to Phase 1. |
| `NEEDS_DECISION` | Present DDAuthor's questions to the user. Collect answers. Re-dispatch with answers appended to requirements. Do not proceed to Phase 1 until `DONE` is returned. |
| `BLOCKED` | Critical information is missing and cannot be inferred. Stop execution and discuss the blocker with the user. Do not re-dispatch until the blocker is resolved. |

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
 | Risk surface | Parts touching security, auth, or data integrity → flag for mandatory security review in plan. High-risk parts should be planned first to surface issues early. |
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
```

**No separate spec files per part.** The scope summary + design doc provide context. The plan's Problem Statement section serves as the spec. Eliminating the spec→plan hop prevents lossy translation.

Present the README to the user for review before proceeding.

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

### 3a. Dispatch Planner Agent

For each part in the round, dispatch the Planner agent. See [references/subagent-protocol.md](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/subagent-protocol.md) for the full dispatch protocol including prompt structure, critical rules, and common mistakes.

```yaml
# Dispatch to Planner agent (see .opencode/agents/planner.md)
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
   - **Missing verification steps** — type checking, lint, test execution, coverage, build
   - **Missing quality gate steps** — code review and security review. Plans touching auth/data/I/O must include security review
   - **Coding standards violations** — mutation patterns, hardcoded values, missing error handling
   - **References to methods not in the contracts ledger or existing codebase**
   - **Step count** (>12 steps → consider splitting)
   - **TDD compliance** — plans for new features should specify test-before-implementation (RED → GREEN → REFACTOR) with coverage targets

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
  | **Quality gates** | Every plan includes code review, security review, and verification loop steps. No plan assumes implementation is complete without these gates |
 | **Coverage** | Every design doc section maps to at least one plan |
 | **Gaps** | Methods needed downstream but never created upstream |
 | **Overlap** | Two plans creating the same artifact |
 | **Verification consistency** | All plans use the same verification pattern (type check → lint → test → coverage → build). Inconsistent verification across plans indicates drift |

Fix issues by editing plan files directly. Update CONTRACTS.md if fixes change any contracts.

Present the cross-validation results to the user with specific issues and fixes applied.

---

## After Planning: Quality Handoff

**The planning pipeline produces validated plans. The implementation workflow takes over from here.**

```
Plans → Implementation (TDD) → Code Review → Security Review → Verification → Commit
```

Each plan must account for this full pipeline — not just the coding steps:

 | Phase | Requirement | Plan Must Include |
 | --- | --- | --- |
 | **TDD** | 80% coverage, RED → GREEN → REFACTOR | Test-before-implementation steps with coverage targets |
 | **Code Review** | Mandatory after writing code | Explicit code review step; use code-reviewer agent |
 | **Security Review** | OWASP top 10, no hardcoded secrets | Security review step for auth/data/I/O parts |
 | **Verification** | Type check + lint + test + coverage + build | Verification step at end of each plan phase |
 | **Commit** | Conventional commits, no console.log | Cleanup and commit step |

**Plans that skip these gates create rework.** The Planner agent should embed them as explicit steps, not rely on out-of-band processes. When reviewing plans during Phase 3b and Phase 4, treat missing quality gate steps the same as missing implementation steps — they are equally required.

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
- [ ] Every plan includes full verification loop steps (type check, lint, test, coverage, build) **→ Verification loop**
- [ ] Every plan includes code review and security review steps **→ Quality gates**
- [ ] Plans touching auth, data, or I/O have mandatory security review steps **→ Security mandate**
- [ ] No plans contain hardcoded values, mutation patterns, or console.log references **→ Coding standards**
- [ ] TDD steps (RED → GREEN → REFACTOR) present for new feature implementation **→ Coverage requirement**

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
