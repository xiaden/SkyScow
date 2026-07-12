# Agent Instruction Patterns

## Contents
- [Pattern 1: Router-First Responsibilities](#pattern-1-router-first-responsibilities)
- [Pattern 2: Conditional Section Loading](#pattern-2-conditional-section-loading)
- [Pattern 3: Delegation Decision Matrix](#pattern-3-delegation-decision-matrix)
- [Pattern 4: REprompt Component Decomposition](#pattern-4-reprompt-component-decomposition)
- [Pattern 5: Scope Exclusions with Positive Routing](#pattern-5-scope-exclusions-with-positive-routing)
- [Pattern 6: Anti-Pattern Catalog](#pattern-6-anti-pattern-catalog)
- [Pattern 7: Position-Over-Content Layout](#pattern-7-position-over-content-layout)
- [Pattern 8: Contradiction Audit Template](#pattern-8-contradiction-audit-template)
- [Pattern 9: Constraint-Count Budget](#pattern-9-constraint-count-budget)
- [Pattern 10: Fade-Out Prevention via Event-Driven Re-Injection](#pattern-10-fade-out-prevention-via-event-driven-re-injection)

---

## Pattern 1: Router-First Responsibilities

### The Problem
Agent files that list execution before delegation prime the model to default to direct action. The agent treats delegation as an exception.

### The Fix
Reorder so routing/delegation comes first. Frame the agent as a router.

### Before (me-first)
```markdown
## Responsibilities
1. Execute implementation tasks following project conventions
2. Delegate specialized work to subagents (R&D, QA, execution management)
3. Own all lint errors regardless of when they were introduced
```

### After (router-first)
```markdown
## Primary Responsibility: Route Before Executing

This agent's first decision is always delegation: does a specialist exist for this task?

1. **Identify the right agent.** Match the task to subagent capabilities (see Delegation Matrix below).
   If a specialist matches → delegate. If no match → proceed to execution.
2. **Execute only what falls within scope.** Direct implementation only when no specialist exists
   or when the task is trivial (single-file, single-concern).
3. **Own errors within scope.** Fix lint errors, test failures, and diagnostics in files this agent
   touched — regardless of when they were introduced.
```

---

## Pattern 2: Conditional Section Loading

### The Problem
Monolithic agent files load all instructions into every session. Delegation rules, plan syntax, error ownership, troubleshooting, and layer conventions all sit in context regardless of whether the task is a one-line fix or a multi-phase feature.

### The Fix
Decompose into sections with condition predicates. Always-on: identity + delegation matrix. Conditional: everything else.

### Template
```markdown
## Always-On Sections (in every session)

### Identity
[One paragraph: who this agent is, its primary responsibility]

### Delegation Matrix
[Who handles what, with what autonomy — see Pattern 3]

### Core Constraints
[Hard rules that always apply: never skip context, stop on architectural concerns]

---

## Conditionally Loaded Sections

| Section | Condition Predicate | When Loaded |
|---------|-------------------|--------------|
| Plan Syntax Rules | Task involves `artifacts/plans/` or multi-phase work | Agent needs to create/edit plan files |
| Layer Conventions | Editing files in a governed directory | Auto-injected based on file path |
| Troubleshooting Procedure | 3+ consecutive failed attempts or explicit debug request | Diagnostic mode |
| ADR/Logging Rules | Task involves architectural decisions or multi-session work | Decision-tracking mode |
| Completion Gate | End of any implementation task | Verification mode |
```

### Implementation Note
If the agent platform doesn't support runtime conditional loading natively, implement it through skill references — split conditional sections into separate skills and have the agent load them on demand via the `skill` tool.

---

## Pattern 3: Delegation Decision Matrix

### The Problem
A single line — "Delegate specialized work to subagents" — gives the model no guidance on who handles what, with what autonomy, or how to verify completion.

### The Fix
A structured matrix with trigger conditions, capability matching, autonomy levels, and completion criteria.

### Template
```markdown
## Delegation Matrix

Before executing any task, check this matrix. If the task matches a row, delegate.

| Task Category | Subagent | Trigger Condition | Autonomy | Completion Evidence |
|--------------|----------|-------------------|----------|-------------------|
| Feature design, R&D | RnD-Manager | User asks "design," "explore," "think about" | Open-ended: agent decides approach | Design doc in artifacts/designs/ |
| Implementation plan creation | Exec-Planner | Multi-phase feature, 4+ coordinated edits | Read-only plan generation | Plan file in artifacts/plans/ |
| Plan execution | Exec-Manager | Existing plan file needs execution | Orchestrate workers | All plan steps marked complete |
| QA review | QA-Reviewer | Implementation complete, before merge | Full review, no edits | Review report with tiered status |
| Root cause analysis | Support-Debugger | 3+ failed fix attempts, unexplained failure | Read-only diagnosis | Diagnosis with suggested fix |
| Deep codebase research | Support-Researcher | Need to understand unfamiliar system (5+ files) | Read-only exploration | Structured findings with code locations |
| Log/ADR navigation | Support-Librarian | Starting work in unfamiliar area | Read-only curation | Curated summary of relevant artifacts |

### Autonomy Levels
- **Atomic execution:** Delegatee follows strict specification, returns structured output. Use for
  well-defined subtasks (plan creation, review, research).
- **Open-ended delegation:** Delegatee has authority to decompose objectives and pursue sub-goals.
  Use for design/R&D tasks where the approach isn't known upfront.
```

---

## Pattern 4: REprompt Component Decomposition

### The Problem
Agent files mix identity, rules, procedures, tool guidance, and mode switching into undifferentiated prose. The model can't distinguish "who I am" from "how I work" from "what tools I can use."

### The Fix
Decompose into the five REprompt components. Each component is independently auditable.

### Template
```markdown
---
# Component 1: Role Definition
---
**Identity:** Default operations agent for routine development tasks.
**Primary Objective:** Determine when to route to specialists vs. execute directly.
**Success Criteria:** Every task handled by the most capable agent available.

---
# Component 2: Knowledge
---
**Project Conventions:** [link to project ADRs, layer docs, coding standards]
**Subagent Capabilities:** See Delegation Matrix above.
**Architecture:** [layers, module boundaries, data flow — or link to capture-subsystem skills]

---
# Component 3: Available Tools
---
| Tool Category | Tools | Boundaries |
|--------------|-------|------------|
| Code editing | edit, write, ast_grep_replace | Never edit files outside scope without question |
| Code exploration | aft_search, aft_outline, aft_zoom, read | Prefer AFT tools over bash grep/find/cat |
| Delegation | task, delegate | Match subagent type to task category (see Matrix) |
| Verification | aft_inspect, bash (lint/test) | Run after every edit batch |
| Documentation | dd_create, adr_suggest, log_write | Only when making architectural decisions |

---
# Component 4: Context Information
---
**Team Composition:**
- RnD-Manager: Design and research (owns the "thinking" phase)
- Exec-Planner: Creates implementation plans (does not execute)
- Exec-Manager: Orchestrates plan execution (spawns workers)
- QA-Reviewer: Quality gate (post-implementation review)
- Support-Debugger: Root cause analysis (diagnostic, not execution)
- Support-Researcher: Deep codebase exploration (read-only)
- Support-Librarian: Artifact navigation (ADRs, logs, design docs)

**Available Skills:** [list of skills with trigger conditions]

---
# Component 5: Work Modes
---
| Mode | Trigger | Behavior |
|------|---------|----------|
| **Routing** | Task description received | Check Delegation Matrix → delegate or proceed |
| **Execution** | No specialist matches, task is in-scope | Direct implementation with layer conventions |
| **Diagnostic** | 3+ failed attempts, unexpected behavior | Load troubleshooting procedure, spawn Support-Debugger if needed |
| **Decision Recording** | Architectural choice made | Create ADR via adr_suggest → adr_commit workflow |
```

---

## Pattern 5: Scope Exclusions with Positive Routing

### The Problem
Scope exclusions are written as "do NOT do X" without saying where X should go instead. The model sees the negation but has no positive action to take.

### The Fix
Every exclusion includes a positive routing instruction — "X → use Y."

### Before (negation-only)
```markdown
**Scope Exclusions:**
- Do not design features or create design documents
- Do not orchestrate multi-plan feature execution
- Do not execute formal implementation plans
- Do not perform QA review
```

### After (negation + positive routing)
```markdown
**Scope Exclusions (with routing):**

| This agent does NOT... | Route instead to... | How |
|------------------------|---------------------|-----|
| Design features or create design documents | RnD-Manager | `task(subagent_type="rnd-manager")` |
| Orchestrate multi-plan feature execution | Director | `task(subagent_type="rw-director")` |
| Execute formal implementation plans | Exec-Manager | `task(subagent_type="exec-manager")` |
| Perform QA review | QA-Reviewer | `task(subagent_type="qa-reviewer")` |
| Create or amend plan files | Exec-Planner | `task(subagent_type="exec-planner")` |
| Root cause analysis on failures | Support-Debugger | `task(subagent_type="support-debugger")` |
| Deep codebase research | Support-Researcher | `delegate(agent="researcher")` |
```

---

## Pattern 6: Anti-Pattern Catalog

These patterns have been observed to cause misbehavior. When present, fix immediately.

### Anti-Pattern: Phantom Agent References
```markdown
# ❌ References an agent that doesn't exist
**MANDATORY: Use the Plan subagent for complex tasks.**
```
The agent "Plan" doesn't exist in the subagent registry. The model either fails to find it
or interprets the instruction as "create a plan file yourself."

**Fix:** Reference only agents that exist in the registry. Verify by cross-referencing
with the available subagent type list.

### Anti-Pattern: Unqualified Mandates
```markdown
# ❌ No condition — applies even when it shouldn't
Treat all lint errors as yours to fix, regardless of when they were introduced.
```
When an exec-planner creates a plan file and lint reports pre-existing errors in untouched
code, this instruction forces the planner to fix them — violating its read-only scope.

**Fix:** Add a scope condition.
```markdown
# ✅ Scoped to the agent's own domain
Treat lint errors as yours to fix when they appear in files you edited.
For errors in untouched files, log an observation and route to the appropriate agent.
```

### Anti-Pattern: Contradictory Instructions
```markdown
# ❌ These two instructions conflict
1. Delegate specialized work to subagents
2. Run the linter after every edit — zero new errors is the standard
```
If the agent delegates an edit to Exec-Worker, instruction 2 still applies (no scope
condition) — but the agent can't run the linter on work it didn't do. It either violates
delegation (runs lint itself, doubling work) or violates the lint rule.

**Fix:** Scope rules to the agent's own execution path.
```markdown
# ✅ Rules scoped by execution mode
When executing directly: run the linter after every edit batch.
When delegating: the delegatee is responsible for verification.
After delegation completes: verify the delegatee's reported results.
```

### Anti-Pattern: Identity by Negation
```markdown
# ❌ Defines the agent by what it doesn't do
**Scope Exclusions:** This agent does NOT design, plan, execute plans, review, or debug.
```
After reading this, the model knows what it shouldn't do but has no positive identity.

**Fix:** Define identity positively, then list exclusions as routing instructions.
```markdown
# ✅ Positive identity first
**Identity:** Default operations agent. Determines when plans are needed, when ADRs
should be created, and when to stop and discuss before the user makes poor architectural
decisions. Routes complex work to specialists; executes only routine tasks directly.

**Routing:** See Delegation Matrix for which specialist handles each task category.
```

### Anti-Pattern: Implicit Mode Switching
```markdown
# ❌ Modes are implied, not explicit
[Section about planning...]
[Section about execution...]
[Section about troubleshooting...]
```
The model doesn't know these are separate modes. It might apply troubleshooting
procedures during planning, or planning rules during execution.

**Fix:** Explicit mode boundaries with trigger conditions (see Pattern 4, Component 5).

---

## Pattern 7: Position-Over-Content Layout

### The Problem
Agent files arrange sections by human-logical order (identity → rules → procedures → reference) but LLMs attend to context by position, not logic. Long agent files place critical instructions (safety, delegation, identity) in the mid-context dead zone where they receive minimal attention. By token 50,000, agents reliably stop attending to system prompt instructions (Bento Labs, 2026).

### The Fix
Structure agent files so that *persistence requirement* determines position, not human readability.

### Template

```markdown
## Tier 0: Token 1 — Identity & Irrevocable Constraints
```
This must be short (~50 tokens). The model attends to token 1 for the full trajectory.
Contains: agent identity (who am I?), primary objective (what's my one job?), non-negotiable
constraints (what must I never do?).
```

## Tier 1: Token ~2-100 — Core Operating Rules
```
Core rules that must hold across the entire session: delegation priorities, stop-and-question
triggers, verification requirements. Keep under 500 tokens total.
```

## Tier 2: Token ~100+ — Task Framing & Scope
```
What kinds of tasks this agent handles, scope boundaries, routing preferences.
These can fade over long sessions — the delegation matrix (Tier 1) should already cover routing.
```

## Tier 3: Conditional — Load on Demand
```
Everything else: plan syntax, troubleshooting procedures, layer conventions,
logging rules, completion gates. These should NEVER be in always-on context.
Use skill references or conditional auto-injection instead.
```

### Implementation Rules

1. **Never exceed 2,000 tokens in always-on sections.** If the always-on section is 2,000+ tokens, it begins in the dead zone.
2. **Place non-negotiable constraints at position 1.** "Never expose secrets," "always verify before claiming done," "stop and question on architectural concerns."
3. **Never use wrapper qualifiers.** "This context may or may not be relevant" turns binding instructions into optional advice. Injected sections must carry the same authority framing as native content.
4. **Prefer `file://` references over embedded content.** "See `references/papers.md` for research backing" is better than embedding the full research in the agent file.

### Anti-Pattern: The Wrapper-Authority Problem
```markdown
# ❌ Harness injects instructions with a qualifier
The following project rules may or may not be relevant to your task:
[CLAUDE.md content]
```
The model reads "may or may not be relevant" and treats everything that follows as optional.
Production incidents (#45239, #28158): agents quote CLAUDE.md rules verbatim, then violate them.

**Fix:**
```markdown
# ✅ Instructions injected with native authority
## Project Rules (Binding)
[CLAUDE.md content]
```
Or better: inject as system-level content with no wrapper at all.

---

## Pattern 8: Contradiction Audit Template

### The Problem
Agent files accumulate instructions through multiple PRs over months. Each addition is individually sensible. Collectively, they produce contradictions — and the LLM resolves them silently through opaque heuristics. No error is raised. No warning is logged. "The agent that resolves the conflict cannot be the agent that detects it" (Arbiter, arXiv:2603.08993).

### The Fix
Run a contradiction audit before shipping any agent file change. Do not ask the agent to self-audit — use systematic block-pair analysis.

### The Audit Template

```markdown
## Agent File Contradiction Audit

### Step 1: Extract All Imperatives
List every "must," "always," "never," "do not," "should," "ensure," "verify" statement with
its section and approximate position.

Example:
| # | Imperative | Section | Position |
|---|-----------|---------|----------|
| 1 | "always use TodoWrite for multi-step tasks" | Process Requirements | Line 45 |
| 2 | "NEVER use TodoWrite for single-file edits" | Process Requirements | Line 52 |
| 3 | "Delegate specialized work to subagents" | Responsibilities | Line 8 |
| 4 | "Own all lint errors regardless of introduction" | Error Ownership | Line 15 |

### Step 2: Group by Scope Domain
Group imperatives that govern the same domain:

Example domains: Tools, Delegation, Verification, User Interaction, Filesystem, Output Format

### Step 3: Check Each Pair for Conflicts
For every pair within a scope domain, ask:

A. Can both be satisfied simultaneously?  
B. If one takes priority, does the agent file specify which?  
C. Does context state (session length, task type) change which applies?

### Step 4: Check for Harness Interference
A. Does any injection wrapper add a qualifier ("may or may not be relevant")?  
B. Do injected sections use different authority framing than native sections?  
C. Could an injected instruction be overridden by an instruction later in context (recency bias)?

### Step 5: Document Resolutions
For each conflict found, document: which imperative was kept, which was modified or removed,
and why. This prevents future PRs from reintroducing the contradictory version.
```

### Known Conflict Classes (from Arbiter, arXiv:2603.08993)

| Architecture | Characteristic Conflict |
|-------------|----------------------|
| Monolithic prompts | Growth-level bugs at subsystem boundaries — new sections contradict old sections no one remembers |
| Flat (sectionless) prompts | Simplicity trade-offs — imperative A and imperative B conflict but there are no section boundaries to help resolve |
| Modular prompts | Design-level bugs at composition seams — each module is internally consistent but modules contradict each other |

---

## Pattern 9: Constraint-Count Budget

### The Problem
Models reliably follow ~3 concurrent constraints (Tian Pan, 2026). Every "must," "always," "never," "ensure," and "verify" in an agent file is a constraint competing for model attention. Most agent files contain 20-50+ active constraints — far beyond what any model can satisfy. At 500 instructions, even GPT-4o is at 15.4%, and Llama 4 Scout at 6.7%.

### The Fix
Treat agent file editing as a constraint budget. Every imperative you add consumes budget; every imperative you remove frees it.

### The Budget Template

```markdown
## Constraint Budget: max 10 always-on, unlimited conditional

### Always-On Constraints (Tier 0-1, token position 1-100)
1. [Identity] I am ${AGENT_NAME}, a {router|executor|reviewer} for {domain}.
2. [Routing] Before executing, check: does a specialist exist? If yes → delegate.
3. [Safety] Stop and question on architectural concerns, half-migrations, scope creep.
4. [Verification] Never claim DONE without evidence. Run linter after every edit batch.
5. [Tools] Prefer aft_search over bash grep; aft_inspect after edits.
6. [Delegation] Use delegation matrix (see below) — match task category to subagent.
7. [Context] Read relevant ADRs and logs before working in unfamiliar areas.
8. [Output] Report completion with explicit evidence, not "should work."
9. [_empty_]
10. [_empty_]

### Conditional Constraints (loaded on demand)
- Plan syntax rules → loaded when task involves `artifacts/plans/`
- Troubleshooting procedure → loaded when 3+ failed attempts
- Layer conventions → auto-injected when editing files in governed directories
- ADR/Logging rules → loaded when making architectural decisions
- Completion gate checklist → loaded at end of implementation tasks

### Constraint Count: 8 + unlimited conditional
### Budget remaining: 2 slots
```

### Splitting Multi-Constraint Instructions
```markdown
# ❌ One instruction, 4 constraints
"Run the linter after every edit batch, fix all errors, verify tests pass,
and report completion with evidence."

# ✅ Split into individual budget items
"Run the linter after every edit batch."              → Constraint 1
"Fix all lint errors in files you edited."             → Constraint 2
"Run tests and verify they pass."                      → Constraint 3
"Report completion with evidence, never 'should work.'" → Constraint 4
```
Each split constraint occupies a budget slot. Before splitting, ask: do all four need to be in always-on context?

### Practical Thresholds
| Model Tier | Max Always-On Constraints | Expected Concurrent Compliance |
|-----------|--------------------------|-------------------------------|
| Reasoning-optimized (o3, Gemini 2.5 Pro) | 15 | ~8-10 (threshold decay at 150+) |
| Frontier (GPT-4o, Claude 3.7) | 10 | ~3-5 |
| Open-source (Llama 4, Qwen) | 5 | ~1-3 |
| Small/fast (GPT-4.1-nano, Haiku) | 3 | ~1-2 |

---

## Pattern 10: Fade-Out Prevention via Event-Driven Re-Injection

### The Problem
Critical constraints must hold across long sessions (50K+ tokens, 15+ tool calls), but the U-shaped attention curve means earlier constraints fade by mid-session. The model complies perfectly in 2-turn tests and fails in production 50-turn sessions.

### The Fix
Re-inject critical constraints at decision points. Don't rely on the model remembering them from the system prompt.

### Decision Points for Re-Injection

| Decision Point | Re-Injected Constraint | Mechanism |
|---------------|----------------------|-----------|
| Before delegation | "Does a specialist exist for this task?" | Auto-injected by `task` tool wrapper |
| Before file edit | Layer-specific conventions | Auto-injected by apply-to plugin |
| Before claiming DONE | Completion gate checklist | Loaded on demand via `skill` tool |
| Before architectural decision | "Stop and question the user" | Triggered by "just put it in X" patterns |
| Before tool selection | "Prefer AFT tools over bash" | Auto-injected by tool description |
| Post 15+ tool calls | "Check constraint compliance" | Timer/event-driven reminder |

### Implementation Approaches

**Approach A: Tool Wrappers (Most Reliable)**
```markdown
# The `task` tool wrapper auto-injects delegation rules before every call:
"Before using this tool, verify: does the task match a specialist agent's domain?
If yes, delegate to that specialist. If no, proceed."

# The `edit` tool wrapper auto-injects layer conventions:
"Editing files in {directory}. Layer conventions: {conventions}."
```

**Approach B: Skill-Based Checkpoints (Flexible)**
```markdown
# At known decision points, load a checkpoint skill:
"When 3+ tool calls have been made without delegation, load `delegation-checkpoint`
to verify routing decisions."
```

**Approach C: API-Layer Proxy (External Enforcement)**
```markdown
# Proxy intercepts tool calls and enforces constraints externally:
# - After 15 tool calls, inject constraint reminder
# - Before file writes, verify scope boundaries
# - Before delegation, verify capability matching
```

### When to Use Each Approach

| Scenario | Approach |
|----------|----------|
| Platform supports tool wrapping | A: Most reliable, zero prompt overhead |
| Platform supports on-demand skill loading | B: Flexible, minimal prompt overhead |
| Neither available | C: External proxy, architecture change required |
| None of the above feasible | Reduce always-on constraints (P8) + position critical at token 1 (P7) |

### Evidence
Event-driven re-injection measurably improves constraint compliance (Cobus Greyling, 2026). The 15-tool-call limit (Code on Grass, 2026) is avoidable with checkpoint-based re-injection — constraints re-injected at decision points don't degrade with tool-call count.
