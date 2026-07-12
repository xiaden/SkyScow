---
name: making-editing-agents
description: Design, write, and edit agent instruction files by applying research-backed principles for coding agents. Covers prompt composition architecture (conditional loading, priority ordering, component decomposition), delegation-as-first-class routing, responsibility framing, and context management. Use when creating a new agent, editing an existing agent instruction file, debugging agent misbehavior (wrong tool choices, failure to delegate, instruction fade-out, "me-first" execution bias), or evaluating whether an agent's instructions are architecturally sound. Do NOT use for writing skills (use making-editing-skills), commands (use command-creation-guide), or auto-injected layer instructions (use creating-auto-injected-instructions).
---

# Making & Editing Agents

**Purpose:** Produce agent instruction files that produce correct agent behavior — routing before executing, delegating to specialists, and staying coherent over long sessions.

This skill distills findings from 20+ recent papers (plus production incident reports and field studies) on coding agent architecture, prompt engineering, multi-agent delegation, context management, and instruction compliance failure modes into actionable principles for writing agent instructions.

---

## When to Use

**Trigger conditions:**

- Creating a new agent instruction file from scratch
- Editing an existing agent file (any agent, any layer)
- Debugging: the agent won't delegate, tries to do everything itself, or makes wrong tool choices
- Evaluating whether existing agent instructions are architecturally sound
- The agent ignores delegation rules, skips scope exclusions, or drifts from its role

**Do NOT use for:**

- Writing skills (SKILL.md files) → use `making-editing-skills`
- Writing commands (opencode.json entries) → use `command-creation-guide`
- Auto-injected layer-specific instructions → use `creating-auto-injected-instructions`
- Capturing codebase research → use `capture-subsystem`

---

## The Eight Principles

These principles are derived from empirical research on coding agent behavior. They form a diagnostic framework — when an agent misbehaves, trace the symptom to the principle being violated.

### Principle 1: Decomposition Before Execution

> An agent's first decision should be *whether to route*, not *how to execute*.

**The problem:** Agent files that list "execute implementation tasks" before "delegate specialized work" prime the model to default to direct action. Multi-agent systems research shows that poorly designed delegation can be *worse* than single-agent execution — a 3-agent system on Knapsack problems started at 3% accuracy (below single-agent baseline) until the bottleneck was patched (KtR, arXiv:2505.16979).

**The fix:** Reorder responsibilities so routing comes first. Frame the agent as a *router that executes only when no specialist is available*, not a *worker with delegation as a fallback*.

| Before (me-first) | After (router-first) |
|---|---|
| 1. Execute implementation tasks | 1. Identify the right agent for the task |
| 2. Delegate specialized work | 2. Delegate when a specialist matches |
| 3. Own all lint errors | 3. Execute only what falls within scope |

### Principle 2: Conditional Prompt Loading

> Not every instruction is relevant to every session. Load sections only when contextually relevant.

**The problem:** Monolithic agent files load delegation rules, plan syntax, error ownership, troubleshooting procedures, and layer-specific conventions into every session regardless of the task. The "Which Prompting Technique Should I Use?" survey (arXiv:2506.05614) found that complex prompting techniques routinely *underperform* simplistic baselines — more instruction does not mean better behavior.

**The fix:** Decompose the agent file into independent sections loaded by condition predicates. Claude Code's architecture (analyzed in arXiv:2604.14228) organizes sections into five priority-ordered tiers: Core Identity → Tool Definitions → Safety & Rules → Provider-Specific Guidance → Dynamic Context. Each section has a condition predicate; irrelevant sections never enter context.

See [`references/patterns.md`](file:///home/opencode/.config/opencode/skills/making-editing-agents/references/patterns.md) for the full section decomposition template.

### Principle 3: Delegation as Structured Contract

> Delegation is not a bullet point. It requires capability matching, boundary specification, and trust calibration.

**The problem:** A single line — "Delegate specialized work to subagents" — treats delegation as an afterthought. The Intelligent AI Delegation framework (arXiv:2602.11865) defines delegation as a sequence of decisions involving: task allocation, transfer of authority, assignment of responsibility and accountability, explicit role and boundary specification, capability matching, and trust calibration.

**The fix:** Agent files need a delegation decision matrix, not a reminder. Four questions the agent must answer before executing:

| Decision | What the agent file must specify |
|----------|----------------------------------|
| **Who?** | Capability matching — which subagent type for which task category |
| **What?** | Boundary specification — what the delegatee can and cannot do |
| **How much?** | Autonomy calibration — atomic execution vs. open-ended delegation |
| **Verify?** | Completion criteria — what evidence the delegatee must return |

See [`references/patterns.md`](file:///home/opencode/.config/opencode/skills/making-editing-agents/references/patterns.md) for a concrete delegation decision matrix template.

### Principle 4: Prompt ≈ Architecture

> The agent file *is* architecture. Its structure determines tool-call patterns, infrastructure use, and decision flow.

**The problem:** Agent instructions are treated as configuration, not as architectural artifacts. The "Architecture Without Architects" paper (arXiv:2604.04990) identifies six prompt-architecture coupling patterns, three of which are *fundamental* (persist regardless of model capability): tool-call orchestration always requires an agent loop, ReAct reasoning always requires a state machine, and guarded autonomy always requires a permission system. Changing the prompt changes the architecture.

**The fix:** Treat agent file changes as architectural changes. Ask: "Does this instruction change create an implicit tool dependency, a new decision branch, or a new coupling?" If yes, document it.

### Principle 5: Simpler Can Be Better

> Instruction density can be actively harmful. Cut before you add.

**The problem:** Agent files accumulate instructions over time. Each addition has a context cost. The prompt engineering survey found that the worst-performing prompting techniques underperformed a simplistic baseline (arXiv:2506.05614). Instruction-tuned models at small scales can be *harmed* by chain-of-thought prompting — a 15.2pp accuracy drop on HumanEval for Qwen2.5-Coder-1.5B-Instruct (arXiv: "Think Less, Code Better," ACL 2026).

**The fix:** Before adding any instruction, ask: "Does this change behavior, or does it just add words?" If it doesn't change behavior, don't add it. Use conditional loading (Principle 2) to keep always-on instructions to the minimum.

### Principle 6: Position Over Content

> Where an instruction lives in the context window matters more than how it's worded.

**The problem:** LLMs exhibit a U-shaped attention curve — high attention at the start and end of context, a "dead zone" in the middle (Liu et al., "Lost in the Middle," TACL 2024). As agent sessions accumulate tool outputs and conversation turns, the system prompt drifts positionally into the middle. By token 50,000, the model has stopped attending to instructions that are still word-for-word in context.

Quantified: multi-document QA accuracy drops 30%+ when relevant information moves from position 1 to position 10 in a 20-document context. Refusal rates shift unpredictably in long contexts — GPT-4.1-nano jumps from 5% to 40%, Grok 4 Fast drops from 80% to 10% at 200K tokens ("When Refusals Fail," arXiv:2512.02445). Intelligence degradation hits a critical threshold at 40-50% of max context length, with F1 dropping 45.5% (arXiv:2601.15300).

**The fix:** Structure instructions by *persistence requirement*, not by human-readable importance:

| Instruction type | Optimized position | Rationale |
|-----------------|-------------------|-----------|
| High persistence: identity, safety, non-negotiable constraints | **Top (token 1)** | Token 1 never drifts — retains high attention for full trajectory |
| High immediacy: task framing, session setup | **Bottom** | Adjacent to first user message; fading later is acceptable |
| Conditional: layer conventions, plan syntax, troubleshooting | **Loaded on demand** | Never in context unless relevant (Principle 2) |

**Critical implementation detail:** the "wrapper-authority problem." When a harness injects instructions with qualifiers like "this context may or may not be relevant to your tasks," the model treats those instructions as optional — regardless of their content. Multiple production incidents (Claude Code issues #45239, #28158) document agents acknowledging they read CLAUDE.md rules, quoting them back verbatim, and then ignoring them because the injection wrapper undermined their authority. **Instructions injected via wrappers must carry the same authority as native system prompt content.**

### Principle 7: Contradiction Detection Requires External Audit

> An LLM cannot detect contradictions in its own instructions. The agent that resolves the conflict cannot be the agent that finds it.

**The problem:** Agent files accumulate instructions through multiple PRs by different authors across months. Each addition is individually sensible. Collectively, they produce contradictions — "always use TodoWrite" in one section, "NEVER use TodoWrite" in another. The model resolves these silently through whatever heuristic its training provides. No error is raised. No warning is logged.

Arbiter (arXiv:2603.08993) applied formal interference detection to Claude Code, Codex CLI, and Gemini CLI system prompts, finding 152 issues via undirected scouring and 21 hand-labeled interference patterns. Three architectural patterns produce three characteristic failure classes: monolithic prompts → growth-level bugs at subsystem boundaries, flat prompts → simplicity trade-offs, modular prompts → design-level bugs at composition seams. "The heuristic that enables an LLM to navigate contradictory instructions is the same heuristic that prevents it from recognizing those instructions as contradictory."

**The fix:** Before shipping an agent file, audit it for contradictions — not by asking the agent itself, but by systematic block-pair analysis:

1. **Identify all imperatives.** Extract every "must," "always," "never," "do not," "should" statement.
2. **Group by scope.** Which instructions govern the same domain (tools, delegation, verification, user interaction)?
3. **Check for conflicts.** Does any scope group contain contradictory directives?
4. **Check for harness interference.** Does any injection wrapper add a qualifier that undermines instruction authority?

See [`references/patterns.md`](file:///home/opencode/.config/opencode/skills/making-editing-agents/references/patterns.md) for the contradiction audit template.

### Principle 8: The Instruction Complexity Cliff

> Models reliably follow ~3 concurrent constraints. Beyond that, compliance degrades in architecture-specific patterns.

**The problem:** Research testing frontier models from 10 to 500 instructions found three degradation patterns (Tian Pan, April 2026):

| Pattern | Models | Behavior |
|---------|--------|----------|
| **Threshold decay** | Reasoning-optimized (o3, Gemini 2.5 Pro) | Near-perfect until ~150-250 instructions, then sharp drop |
| **Linear decay** | Some architectures | Steady, predictable accuracy reduction |
| **Exponential decay** | Certain architectures | Rapid collapse after 50-100 instructions |

Even at modest densities: GPT-4 averaged 3.3 concurrently satisfied constraints. GPT-3.5: 2.9. Open-source: 1.4-2.4. The practical limit is startlingly low.

At 500 instructions: Gemini 2.5 Pro at 68.9%, Claude 3.7 at 52.7%, GPT-4o at 15.4%, Llama 4 Scout at 6.7%.

**The fix:** Count the constraints in your agent file. Every "must," "always," "never," "ensure," "verify," and procedural rule is a constraint competing for compliance. If the always-on section exceeds ~10 constraints, move conditional ones to on-demand loading (Principle 2). If a single instruction bundles 4+ constraints ("respond in a friendly tone, format as a numbered list, keep under 200 words, always ask a follow-up question") — split it.

---

## Diagnostic Decision Tree

When an agent misbehaves, trace the symptom through this tree to find the violated principle:

```
Agent won't delegate → keeps executing directly?
├─ Yes → Principle 1: Responsibilities order primes execution over routing
│        Check: Is "delegate" listed before or after "execute"?
│
├─ No, it delegates but to the wrong agent?
│   └─ Principle 3: No capability matching matrix in the agent file
│      Check: Does the agent file specify which subagent type matches which task?
│
├─ No, it delegates correctly but loses context across turns?
│   └─ Principle 2: Monolithic instruction file, no conditional loading
│      Check: Are delegation rules, plan syntax, and error ownership always in context?
│
└─ No, it's making architectural decisions without asking?
    └─ Principle 4: Prompt structure creates implicit tool dependencies
       Check: Does the instruction "just put it in X" create a new coupling?

Agent's behavior degrades over long sessions (past ~40K tokens)?
├─ Principle 6: Instructions in the mid-context dead zone — U-shaped attention curve
│   Check: Are critical instructions at the top (token 1) or drifting to middle?
│
├─ Principle 5: Instruction density overwhelming the model
│   Cheque: Count active constraints in always-on sections (target <10)
│
└─ Principle 8: Complexity cliff — model can satisfy only ~3 concurrent constraints
    Check: How many simultaneous "must/always/never" rules are actively competing?

Agent acknowledges instructions but silently ignores them?
├─ Principle 6: Wrapper-authority problem — "this context may be relevant" undermines authority
│   Check: Does any injection wrapper add qualifiers to instruction blocks?
│
└─ Principle 7: Contradictory instructions — model can't detect its own contradictions
    Check: Block-pair audit. Does "always use X" coexist with "NEVER use X"?

Agent follows one rule but violates another without knowing?
└─ Principle 7: Conflicting imperatives from different authors, resolved silently
   Check: Do instructions from different PRs govern the same domain?

Agent breaks constraints after ~15+ tool calls or long sequences?
└─ Principle 8: Constraint decay over long task sequences
   Check: Do critical constraints need event-driven re-injection at decision points?

Agent's safety/refusal behavior changes mid-session?
└─ Principle 6: Refusal mechanisms unstable in long contexts
   Check: Are safety constraints at position 1, or have they drifted?

Agent was working, now it's not — same agent file?
├─ Principle 5: Recent additions may have crossed the complexity threshold
├─ Principle 4: A new instruction created an unexpected coupling
└─ Principle 7: A new imperative contradicts an existing one (silent failure)
```

---

## The REprompt Decomposition Template

The REprompt framework (arXiv:2601.16507) decomposes system prompts into five structured components. Use this as a template when writing or auditing an agent file:

| Component | What it contains | Example from a coding agent |
|-----------|-----------------|---------------------------|
| **Role Definition** | Identity, responsibilities, primary objective | "Default operations agent that determines when to route vs. execute" |
| **Knowledge** | Domain information the agent must use | Project conventions, layer architecture, subagent capabilities |
| **Available Tools** | What the agent can do, with boundaries | Tool list with explicit "use X for Y, never for Z" rules |
| **Context Information** | Work scenario and team composition | Which agents are available, what they specialize in, how to invoke them |
| **Work Modes** | Multiple modes and when each applies | Routing mode (delegation decisions), execution mode (direct implementation), diagnostic mode (troubleshooting) |

Each component should be **independently auditable**. If you can't point to where the delegation rules live, or where the tool boundaries are specified, the decomposition is incomplete.

---

## Validation Checklist

Before declaring an agent file complete, verify every item:

### Structural
- [ ] Responsibilities are ordered: routing/delegation before direct execution
- [ ] The agent's primary identity is clear in one sentence (what it IS, not just what it does NOT do)
- [ ] Section boundaries are explicit — identity vs. rules vs. procedures are not intermixed

### Delegation Quality
- [ ] A delegation decision matrix exists (who handles what, with what autonomy)
- [ ] Each subagent type has a clear trigger condition (when to use it)
- [ ] Delegation includes completion criteria (what evidence the delegatee must return)

### Context Efficiency
- [ ] Always-on instructions are minimal (identity + delegation matrix + core constraints)
- [ ] Task-specific instructions (plan syntax, layer conventions, troubleshooting) are conditionally loaded
- [ ] No instruction exists that duplicates what reference files or skills already provide

### Behavioral
- [ ] The agent's first action for a complex task is "identify the right agent," not "open the file"
- [ ] The agent knows when to stop and question (architectural shortcuts, half-migrations, scope creep)
- [ ] Error ownership is scoped — "fix lint errors" applies to the agent's own domain, not universally

### Anti-Patterns to Catch
- [ ] No "execute" listed before "delegate" in responsibilities
- [ ] No phantom agent references (agents that don't exist in the subagent registry)
- [ ] No unqualified mandates ("always do X" without a "when" condition)
- [ ] No instructions that contradict each other within the same scope domain
- [ ] No injection wrappers that add qualifiers ("may or may not be relevant") — all injected instructions carry native authority
- [ ] Always-on constraint count is under 10 — every "must/always/never/ensure/verify" counts as one
- [ ] Critical instructions (identity, safety, non-negotiable constraints) are at the top of the prompt (token position ≤ 100)
- [ ] No single instruction block bundles 4+ constraints — split multi-constraint rules
- [ ] Event-driven re-injection exists for constraints that must hold across long tool-call sequences (15+ calls)
- [ ] Contradiction audit completed before shipping: all imperative pairs within the same scope domain checked for direct conflicts

---

## References

- **Canonical source:** This skill synthesizes findings from the papers documented in [`references/papers.md`](file:///home/opencode/.config/opencode/skills/making-editing-agents/references/papers.md)
- **Pattern library:** [`references/patterns.md`](file:///home/opencode/.config/opencode/skills/making-editing-agents/references/patterns.md) — before/after agent instruction snippets for each principle
- **Related skills:**
  - `making-editing-skills` — for writing SKILL.md files (different format, different rules)
  - `customize-opencode` — for opencode.json agent registration and configuration
  - `creating-auto-injected-instructions` — for layer-specific instruction files (auto-injected, not agent-level)
  - `dispatching-agents` — for the delegation dispatch templates that agents should use
  - `capture-subsystem` — for documenting codebase architecture (the "Knowledge" component of REprompt)
