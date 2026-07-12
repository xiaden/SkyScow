# Research Papers: Agent Instruction Design

## Contents
- [Prompt Composition & System Prompt Architecture](#prompt-composition--system-prompt-architecture)
- [Delegation & Multi-Agent Routing](#delegation--multi-agent-routing)
- [Coding Agent Scaffold Architecture](#coding-agent-scaffold-architecture)
- [Prompt Engineering for SE Tasks](#prompt-engineering-for-se-tasks)
- [Prompt-Architecture Coupling](#prompt-architecture-coupling)
- [Context Engineering](#context-engineering)
- [Instruction Compliance & Failure Modes](#instruction-compliance--failure-modes)
- [Instruction Fade-Out & Context Position Effects](#instruction-fade-out--context-position-effects)
- [Harness Engineering & Agent Infrastructure](#harness-engineering--agent-infrastructure)

---

## Prompt Composition & System Prompt Architecture

### REprompt: Requirements Engineering-Guided Prompt Optimization
**arXiv:2601.16507, 2026**

> Treats system prompts as software requirements and runs them through a requirements engineering pipeline.

**Key findings:**
- Decomposes system prompts into 5 components: Role Definition, Knowledge, Available Tools, Context Information, Work Modes
- Uses 4 agents (Interviewee, Interviewer, CoTer, Critic) to elicit, analyze, specify, and validate prompts
- Validated on MetaGPT agent system prompts — achieved 4.7/5 consistency, 4.5/5 communication (LLM-as-judge)
- Human evaluation: 5.75/7 overall user satisfaction, 5.42/7 usability
- Optimized prompts outperformed baselines on both gaming (scores up to 6.53/7) and tools subsets

**Relevance to agent design:** The 5-component decomposition is a template for auditing agent files. If any component is missing or intermixed, the agent's behavior will be inconsistent.

### Claude Code Architecture: Prompt Composition
**"Dive into Claude Code," arXiv:2604.14228, 2026**

> Source-code-level analysis of Claude Code's system prompt assembly pipeline.

**Key findings:**
- System prompt assembled at runtime from modular sections, each with a condition predicate and priority integer
- Five functional tiers: Core Identity → Tool Definitions → Safety & Rules → Provider-Specific Guidance → Dynamic Context
- "Behavioral instructions are factored into independent sections, each stored as a separate markdown file"
- Condition predicates determine loading: sections load only when contextually relevant
- Priority integers control reading order within each tier

**Relevance to agent design:** The conditional loading pipeline is the antidote to monolithic agent files. Sections that aren't relevant to the current task should never enter context.

### OpenDev: Scaffolding and Harness Design
**"Building AI Coding Agents for the Terminal," arXiv:2603.05344, 2026**

> Architectural analysis of an open-source terminal coding agent with emphasis on context engineering.

**Key findings:**
- Three guiding principles: separation of concerns, progressive degradation, transparency over magic
- Dynamic system prompt construction via PromptComposer: condition evaluation → priority sort → concatenation
- Event-driven system reminders counteract instruction fade-out in long-running sessions
- Planner subagent with read-only tools and specialized prompt — write operations excluded from tool schema entirely
- "Getting the prompt right at startup is the central initialization problem"

**Relevance to agent design:** Validates that prompt assembly should be dynamic and conditional. Also confirms that planning should be delegated to a specialist, not done by the main agent.

---

## Delegation & Multi-Agent Routing

### Intelligent AI Delegation Framework
**arXiv:2602.11865, 2026**

> Formal framework for delegation involving transfer of authority, responsibility, and accountability.

**Key findings:**
- Defines intelligent delegation as: task allocation + transfer of authority + assignment of responsibility + role/boundary specification + capability matching + trust calibration
- Five requirements: dynamic assessment, adaptive execution, structural transparency, scalable market coordination, systemic resilience
- Distinguishes atomic execution (strict specifications, narrow scope) from open-ended delegation (authority to decompose and pursue sub-goals)
- "Delegation is more than just task decomposition into manageable sub-units of action"

**Relevance to agent design:** A bullet point saying "delegate specialized work" fails all five requirements. Agent files need a delegation decision matrix covering capability matching, boundary specification, and autonomy calibration.

### Know-The-Ropes (KtR): Heuristic Multi-Agent System Design
**arXiv:2505.16979, 2025**

> Algorithmic approach to multi-agent system design that decomposes tasks into typed, controller-mediated subtasks.

**Key findings:**
- Poorly designed MAS can be worse than single-agent: 3-agent system on Knapsack started at 3% accuracy (below single-agent) before bottleneck was patched
- Typed I/O contracts enforced by a lightweight controller prevent cross-talk and context bloat
- After patching: 95% accuracy on size-5 instances with GPT-4o-mini
- On Task-Assignment benchmark: 6-agent o3-mini system hit 100% up to size 10, ≥84% on sizes 13-15 (vs ≤11% single-agent)
- "Robustness must flow from exploiting domain structure, not from ever-larger prompt templates"

**Relevance to agent design:** Delegation without proper contracts can make things worse. Agent files need explicit I/O contracts between delegator and delegatee.

### RTADev: Intention-Aligned Multi-Agent Framework
**"RTADev: Intention Aligned Multi-Agent Framework for Software Development," ACL 2025 Findings**

> Multi-agent framework with real-time alignment mechanism to prevent consensus drift.

**Key findings:**
- 5 role-playing agents (Product Manager, Architect, Project Manager, Programmer, Test Engineer)
- Real-Time Alignment (RTA) mechanism: each deliverable passes alignment checking before entering the Shared Certified Repository
- Ad-hoc group review when alignment fails — only dissenting agents participate
- "All agents work based on common understandings of the target software"

**Relevance to agent design:** Alignment drift between agents (and between agent and its own instructions) is a recognized failure mode. Agent instructions need explicit alignment checkpoints.

### MasRouter: Learning to Route LLMs for Multi-Agent Systems
**"MasRouter: Learning to Route LLMs for Multi-Agent System," ACL 2025**

> First LLM routing solution for multi-agent systems that selects collaboration mode, roles, and model assignments.

**Key findings:**
- MAS routing involves: collaboration mode determination, dynamic agent count, role allocation, agent LLM routing
- 1.8-8.2% improvement over SOTA on MBPP, up to 52.07% overhead reduction on HumanEval
- "Routing in MAS involves more tasks than just LLM recommendations"

**Relevance to agent design:** Even within a single agent's delegation logic, routing should be explicit — which subagent, with what collaboration mode, using which model.

---

## Coding Agent Scaffold Architecture

### Inside the Scaffold: A Source-Code Taxonomy of Coding Agent Architectures
**arXiv:2604.03515, 2026**

> Analysis of 13 open-source coding agent scaffolds across 12 dimensions in 3 layers.

**Key findings:**
- 11 of 13 agents compose multiple loop primitives (ReAct, generate-test-repair, plan-execute, multi-attempt retry) rather than relying on a single control structure
- Delegation/sub-agent spawning is a first-class tool in production agents — not an afterthought
- Control strategies form a spectrum: fixed pipelines (Agentless) to full MCTS (Moatless Tools)
- Multi-model routing: some agents assign different models to different roles (planning vs. execution)
- "Agents occupy positions along continuous spectra rather than discrete architectural categories"

**Relevance to agent design:** Delegation as a core loop primitive (not an exception path) is the norm in production coding agents. Agent files should reflect this.

### Runtime-Structured Task Decomposition
**arXiv:2605.15425, 2026**

> Architectural pattern where task partitioning decisions are governed by executable control flow, not static prompt text.

**Key findings:**
- Static decomposition can increase retry cost vs. monolithic: 80.5% increase in Kubernetes RCA workload
- Runtime branching reduces retry cost by 51.7% over monolithic, 73.2% over static
- "Decomposition structure alone does not reliably reduce retry cost"
- Validation-gated state transitions prevent malformed outputs from reaching downstream subtasks

**Relevance to agent design:** Agent instructions that prescribe a fixed workflow (always plan first, then execute) can be worse than a flexible routing approach. Runtime decisions based on task characteristics outperform static decomposition.

---

## Prompt Engineering for SE Tasks

### Which Prompting Technique Should I Use?
**arXiv:2506.05614, 2025**

> Systematic evaluation of 14 prompting techniques across 10 SE tasks using 4 LLMs.

**Key findings:**
- Structured Guidance (32.05%) and In-Context Examples (21.80%) are the most prevalent factors among best-performing techniques
- Worst-performing techniques underperformed a simplistic baseline — more complexity ≠ better results
- "Complex prompting techniques would not necessarily improve performance"
- Token efficiency varies dramatically: ES-KNN is top-performing but least token-efficient; RP is most token-efficient

**Relevance to agent design:** Adding more instructions to an agent file can make it perform worse. Structured guidance aligned to the task is what matters.

### Guidelines to Prompt LLMs for Code Generation
**arXiv:2601.13118, 2026**

> Empirically derived 10 guidelines for code generation prompts, validated with 50 practitioners.

**Key findings:**
- 10 guidelines: I/O format specification, pre/post-conditions, I/O examples, dependencies, algorithmic details, exceptions/error handling, complex conditions, ambiguity resolution, code structure, testability
- Practitioners already use I/O formatting and pre/post-conditions but underuse ambiguity resolution and I/O examples
- "Minor specifications in a prompt may make the difference between a test-passing and a test-failing implementation"

**Relevance to agent design:** The specific, concrete details matter. "Delegate specialized work" is too vague — the agent needs to know what "specialized" means for each task category.

### Think Less, Code Better: When Chain-of-Thought Hurts
**"Think Less, Code Better: Probing When Chain-of-Thought Hurts and How to Route Around It," ACL 2026**

> Controlled study showing CoT's effect on code generation depends on model, training regime, and scale.

**Key findings:**
- Instruction tuning reverses CoT's effect on small models: CoT improves base (+13.4pp) but degrades instruct variant (-15.2pp) on Qwen2.5-Coder-1.5B
- Effect is scale-bounded: disappears at 7B, slightly positive at 14B
- Mechanism: CoT inflates instruct model's output length by 112 tokens, pushes 7.6× more generations into truncation
- All models detect CoT structure in layers 1-4 (>90% probe accuracy) but interpret it differently

**Relevance to agent design:** Instructions that prompt reasoning (like troubleshooting procedures) can actively harm performance on smaller/faster models. Consider whether the agent model actually benefits from detailed procedural instructions.

---

## Prompt-Architecture Coupling

### Architecture Without Architects: How AI Coding Agents Shape Software Architecture
**arXiv:2604.04990, 2026**

> Identifies 6 prompt-architecture coupling patterns where natural-language prompts determine infrastructure.

**Key findings:**
- Six coupling patterns across three categories: output format constraints (contingent), tool-call orchestration and ReAct reasoning (fundamental), retrieval augmentation and guarded autonomy (contingent/fundamental)
- Case study: same task produced 141 LoC (Variant A) vs 827 LoC (Variant C) depending solely on prompt design
- "Prompt specifications are architectural artifacts and belong in architectural review"
- "The agent file is the architecture" — changing prompt structure changes tool dependencies, agent loops, and state management

**Relevance to agent design:** Every instruction in an agent file that triggers a tool call, a decision branch, or a state change is an architectural decision. Agent files should be reviewed as architecture, not configuration.

---

## Context Engineering

### Reporting LLM Prompting in Automated SE: A Guideline
**arXiv:2601.01954, 2026**

> Analysis of ~300 SE papers on how prompt design, testing, and optimization are reported.

**Key findings:**
- 75% of papers fully or partially describe prompts; 70% provide prompts word-by-word
- Only 59% justify prompt construction (why they created the prompt that way)
- Only 23% report prompting as a threat to validity
- "Prompting as a potential threat to validity is still not widely recognized"

**Relevance to agent design:** Agent files should include the rationale for structural choices — why responsibilities are ordered this way, why delegation rules are structured as they are. Without rationale, future editors can't assess whether changes are safe.

### Context Engineering as a First-Class Concern
**"Context Engineering: A Methodology for Structured Human-AI Collaboration," arXiv:2604.04258, Apr 2026**

> File-based authority outperforms verbal instructions.

**Key findings:**
- File-based authority outperforms verbal instructions by a ~60pp quality gap
- Write standards in files, don't embed them in prompts
- Triple-placement of format instructions (system prompt + before task + compressed at end) prevents format drift
- Explicit delimiters between instruction, context, and data regions reduce ambiguity

**Relevance to agent design:** Agent files are the "file-based authority." The structure of the file itself — section boundaries, conditional loading predicates, priority ordering — is more impactful than the specific wording of individual instructions.
---

## Instruction Compliance & Failure Modes

### The Instruction Complexity Cliff
**Tian Pan, Independent Research, April 2026**

> Systematic evaluation of how model compliance degrades as instruction count increases.

**Key findings:**
- Tested frontier models from 10 to 500 instructions; three distinct degradation patterns observed:
  - **Threshold decay:** Reasoning-optimized models (o3, Gemini 2.5 Pro) near-perfect until ~150-250 instructions, then sharp drop
  - **Linear decay:** Some architectures show steady, predictable accuracy reduction
  - **Exponential decay:** Certain architectures collapse rapidly after 50-100 instructions
- At 500 instructions: Gemini 2.5 Pro 68.9%, Claude 3.7 52.7%, GPT-4o 15.4%, Llama 4 Scout 6.7%
- Even at modest densities: GPT-4 averaged 3.3 concurrently satisfied constraints; GPT-3.5: 2.9; open-source: 1.4-2.4
- LLMs are like operating systems with hard RAM limits — they literally cannot keep arbitrary numbers of requirements in working memory

**Relevance to agent design:** Every "must," "always," "never," "ensure," and "verify" in an agent file is a constraint competing for compliance. The always-on section should stay under ~10 constraints. Multi-constraint instructions ("respond in a friendly tone, format as a numbered list, keep under 200 words, always ask a follow-up question") should be split.

### Conflicting Instructions: Silent Failure Mode
**Tian Pan, Independent Research, May 2026**

> Analysis of how incremental PR changes to system prompts produce contradictions that models resolve silently.

**Key findings:**
- Agent system prompts accumulate instructions through many PRs over months; each addition is individually sensible but collectively contradictory
- LLMs exhibit recency bias when resolving contradictory instructions — the instruction that appears latest in the prompt wins
- The model never raises an error or warning; it resolves contradictions through whatever heuristic its training provides
- The heuristic that enables navigation of contradictions is the same heuristic that prevents recognition of them as contradictory

**Relevance to agent design:** Agent files need explicit contradiction audits before shipping. Block-pair analysis: extract all imperatives, group by scope domain, check each pair for direct conflicts.

### Arbiter: Formal Interference Detection in Agent System Prompts
**arXiv:2603.08993, 2026**

> Applied formal interference detection to production coding agent system prompts.

**Key findings:**
- Analyzed Claude Code, Codex CLI, and Gemini CLI system prompts
- Found 152 issues via undirected scouring, 21 hand-labeled interference patterns
- Three failure classes: growth-level bugs (monolithic prompts), simplicity trade-offs (flat prompts), design-level bugs at composition seams (modular prompts)
- "The agent that resolves the conflict cannot be the agent that detects it" — LLMs cannot detect contradictions in their own instructions
- Formal theory parallels interference in programming language semantics; applied software engineering concepts to prompt engineering

**Relevance to agent design:** Contradiction detection requires external tooling, not self-audit. Agent files that have been through multiple PRs should be checked with systematic block-pair analysis — never rely on asking the agent "are there contradictions in your instructions?"

### Claude Code Instruction Violation Incidents
**Claude Code Issues #45239, #28158, 2025-2026**

> Production incidents where Claude Code agents systematically ignored CLAUDE.md instructions.

**Key findings:**
- Issue #45239: 117 documented CLAUDE.md violations in a single day; agent acknowledged reading the rules and then ignored them
- Root cause: the harness injects CLAUDE.md with a qualifier like "this context may or may not be relevant to your tasks" — this undermines the authority of the instructions
- The "wrapper-authority problem": instructions injected via wrappers are treated by the model as optional advice, not binding constraints
- Agents can quote the rules back verbatim while simultaneously violating them — the acknowledgment is not evidence of compliance

**Relevance to agent design:** Any instruction injection mechanism must carry native authority. Wrapper qualifiers like "may or may not be relevant" or "consider the following" are actively harmful. Injected instructions should use the same authority framing as native system prompt content.

### 15-Tool-Call Constraint Break Limit
**"Code on Grass" blog, April 2026**

> Field observation of constraint degradation over extended tool-call sequences.

**Key findings:**
- Claude agents reliably break constraints after approximately 15 tool calls in a single session
- The mechanism: as context accumulates tool outputs and conversation turns, earlier instructions drift into the mid-context dead zone
- Proposed fix: API-layer proxy that re-injects critical constraints at decision points; constraint enforcement moved from prompt to infrastructure
- Event-driven system reminders measurably improve constraint compliance in long-running sessions (quantified in Cobus Greyling analysis)

**Relevance to agent design:** Critical constraints that must hold across 15+ tool calls should not rely solely on prompt position. Implement event-driven re-injection (at decision points) or API-layer enforcement as a supplement.

### Cobus Greyling: Instruction Fade-Out Analysis
**Cobus Greyling, "Agentic AI" blog, 2026**

> Detailed analysis of instruction fade-out and mitigation strategies.

**Key findings:**
- Event-driven system reminders at decision points measurably fix fade-out
- Quantified JSON compliance improvement when critical constraints are re-injected at checkpoints
- Three intervention points: before delegation, before tool selection, and before output generation
- Fade-out is not random — it follows the U-shaped attention curve and is predictable

**Relevance to agent design:** If a constraint must hold at specific decision points (e.g., "always delegate design to RnD-Manager"), re-inject it at those decision points rather than relying on the agent remembering it across 50K+ tokens of conversation.

### When Refusals Fail: Safety in Long Contexts
**arXiv:2512.02445, 2025**

> Safety mechanism instability in long-context LLM interactions.

**Key findings:**
- Refusal behaviors change dramatically over context length: GPT-4.1-nano refusal rate jumps from 5% at short context to 40% at 200K tokens
- Grok 4 Fast drops from 80% refusal to 10% at 200K tokens
- Long-context prefix attacks can circumvent safeguards as context length increases
- Safety mechanisms designed for short interactions fail in long-running agent sessions

**Relevance to agent design:** Safety-critical constraints should be at position 1 (top of prompt) where the U-shaped attention curve provides maximum retention. Never rely on safety instructions that drift into the mid-context dead zone.

### Intelligence Degradation at Scale
**arXiv:2601.15300, 2026**

> Measured LLM reasoning quality as context approaches capacity limits.

**Key findings:**
- Critical degradation threshold at 40-50% of max context length
- F1 score dropped 45.5% when approaching the threshold
- RAG quality degrades at 30% of max context — earlier than raw reasoning
- Degradation is not model-specific; all tested models exhibit the effect

**Relevance to agent design:** Agent sessions that approach 40% of the model's context window will exhibit measurable intelligence degradation. Always-on agent instructions should be as compact as possible to delay this threshold.

### Lost in Decomposition
**"Lost in the Middle of Decomposition: Rethinking Chain-of-Thought Decomposition," ACL 2026 Findings**

> Extends "Lost in the Middle" to structured reasoning chains.

**Key findings:**
- Decomposition into subtasks can hurt performance on tasks requiring cross-subtask context dependency modeling
- Static decomposition fragments contextual relationships that the model would otherwise preserve
- "Lost in the Middle" applies not just to documents in retrieval but to reasoning steps in chain-of-thought
- The sequence position of each reasoning step affects how much attention it receives from subsequent steps

**Relevance to agent design:** Agent files that decompose complex behaviors into many procedural steps may lose cross-step dependencies. This reinforces P5 (Simpler Can Be Better) and the constraint-count budget (P8).

---

## Instruction Fade-Out & Context Position Effects

### Bento Labs: Instruction Fade-Out Field Study
**Bento Labs Engineering Blog, 2026**

> Field study of instruction compliance degradation in production coding agents.

**Key findings:**
- By token 50,000, agents reliably stop attending to system prompt instructions
- The U-shaped attention curve creates a "dead zone" in the middle of context — instructions at positions ~5K-50K tokens from the prompt start receive minimal attention
- System prompts that are long (>5K tokens) begin in the dead zone from session start
- Instructions that work perfectly in 2-turn tests fail in production 50-turn sessions

**Relevance to agent design:** Agent files must be structured with the U-shaped attention curve in mind. Long agent files are self-defeating — the instructions that make them long are the same instructions the model will ignore.

### CodeDelegator: Preventing Context Pollution via Role Separation
**arXiv:2601.14914, 2026**

> Delegation-based architecture that prevents debugging traces from polluting the main agent's context.

**Key findings:**
- Role separation: ephemeral Coder sub-agents handle implementation; each gets a fresh context
- EPSS (Ephemeral Plugin Scoped Session) isolates debugging traces from planner context
- Debugging traces (tool output, error messages, retry attempts) are the fastest-growing context consumers
- Without role separation, debugging traces crowd out the planner's instructions, accelerating fade-out

**Relevance to agent design:** Delegation prevents context pollution, not just workload distribution. The main agent's context stays clean — only task summaries and completion evidence return.

### RTADev: Context-Aware Delegation
**RTADev, ACL 2025 Findings (additional context analysis)**

> Sub-finding: relationship between delegation cadence and context preservation.

**Key findings:**
- Agents with a Shared Certified Repository preserved cross-subtask dependencies better than agents without
- The SCR acts as a compressed knowledge store — delegates don't need the full conversation history, just the relevant domain context
- Delegation with explicit artifact handoff reduced context consumption by ~40% vs. inline execution

**Relevance to agent design:** Delegation with structured handoff artifacts (plans, design docs, review reports) is a context preservation strategy. The delegatee receives curated context, not the full conversation history.

---

## Second-Round Delegation & Routing Papers

### Uno-Orchestra: Selective Delegation
**arXiv:2605.05007, 2026**

> Orchestrator that selectively delegates tasks to specialized models based on capability matching.

**Key findings:**
- 77% pass@1, 16% above baseline at approximately 10x lower cost
- Selective delegation: not all tasks benefit from specialist routing; the orchestrator learns when to delegate vs. execute
- Cost-efficiency from model tiering: cheap models for routine work, expensive specialists only when needed

**Relevance to agent design:** The delegation matrix should include a "don't delegate" path — some tasks are faster and cheaper to execute directly. Delegation is not always the right answer.

### EvoRoute: Experience-Driven Routing
**"EvoRoute: Pareto-Optimal Multi-Agent Architectures via Evolutionary Optimization," ACL 2026**

> Evolutionary optimization of multi-agent routing decisions informed by the Agent System Trilemma.

**Key findings:**
- Agent System Trilemma: accuracy, cost, and latency cannot all be optimized simultaneously
- Experience-driven routing: 80% cost reduction while maintaining accuracy by learning which tasks benefit from delegation
- The optimal routing strategy changes over time as the system accumulates task history

**Relevance to agent design:** Agent routing rules should be experience-updatable. A static delegation matrix is a starting point, not an endpoint.

### CADMAS-CTX: Contextual Capability Calibration
**arXiv:2604.17950, 2026**

> System that calibrates delegation decisions based on current context state.

**Key findings:**
- Contextual capability calibration improved SWE-bench Lite from 22.3% to 31.4%
- Routing decisions change based on context length, task complexity, and available tools — not just task category
- The same task routed differently at 10K vs. 50K context tokens

**Relevance to agent design:** Delegation decisions should factor in context state. An agent at 80% context capacity should delegate more aggressively than one at 20%.

### Software Delegation Contracts
**arXiv:2606.17099, 2026**

> Evaluation of structured delegation contracts for LLM-based software agents.

**Key findings:**
- Contracts improve reviewability of delegated work but not correctness
- +0.83 on evidence sufficiency metric (reviewer confidence that work was done correctly)
- +13% tokens consumed (contract overhead)
- Contracts help humans verify AI work, not AI improve its own work

**Relevance to agent design:** Delegation contracts (see P3) are worth the token cost — they improve human reviewability even if they don't directly improve agent correctness.---

## Harness Engineering & Agent Infrastructure (from `research_papers` arXiv)

### TTHE: Test-Time Harness Evolution
**arXiv:2607.08124, July 2026**

> The agent's harness — not just its prompt — determines behavior. Harness optimization as a search problem.

**Key findings:**
- "The behavior of an LLM agent is determined not only by the underlying model, but also by its harness: the executable program that constructs context, invokes tools, verifies intermediate results, and recovers from failures"
- Existing approaches optimize harnesses before deployment; this paper proposes test-time optimization
- Harness components: context construction, tool invocation, intermediate verification, failure recovery
- The harness is architecture — changing it changes agent behavior as much as changing the prompt

**Relevance to agent design:** Prompt-design principles (P1-P8) apply equally to harness design. The harness that constructs the context, loads tools, and manages session state is the infrastructure side of P4 (Prompt ≈ Architecture). Harness decisions (when to load skills, when to inject instructions, when to truncate context) are prompt-architecture coupling points.

### From Prompts to Contracts: Harness Engineering for Auditable Enterprise LLM Agents
**arXiv:2607.08028, July 2026**

> Enterprise LLM applications mature from prompt-driven prototypes to contract-driven production systems.

**Key findings:**
- "Enterprise LLM applications often begin as prototypes whose behavior is carried by prompts and retrieval context"
- Productization adds: source boundaries, entity routing, answer contracts, reproducible traces
- Harness-engineering approach treats prompts as contracts with structured enforcement
- Transition point: when the agent must be auditable, prompts must become contracts

**Relevance to agent design:** Directly validates P3 (Delegation as Structured Contract). The progression from ad-hoc prompt instructions to structured, auditable contracts mirrors the progression from "delegate specialized work" (bullet point) to a delegation matrix with capability matching, boundary specification, and completion criteria. Contracts are the production form of delegation instructions.

### Agent Delivery Engineering Predictive Reliability Framework (ADE-PRF)
**arXiv:2607.07689, July 2026**

> Proactive degradation detection for long-horizon multi-agent systems, not just reactive monitoring.

**Key findings:**
- "Long-horizon LLM multi-agent systems face reliability risks invisible to infrastructure monitoring"
- Proposes proactive health trajectory prediction vs. passive degradation detection
- 20 heterogeneous signals across 5 dimensions for predicting agent reliability
- Degradation patterns that are invisible to per-request monitoring become visible through trajectory analysis

**Relevance to agent design:** Validates P6 (Position Over Content) and P8 (Complexity Cliff) — degradation over long sessions is a measurable phenomenon that requires proactive monitoring. The finding that reliability risks are "invisible to infrastructure monitoring" (you can't just watch CPU/memory) aligns with our fade-out analysis: instruction compliance degrades silently.

### Reason Less, Verify More: Deterministic Gates Recover Silent Policy-Violation Failure Mode
**arXiv:2607.07405, July 2026**

> Tool-using agents violate policies while appearing to complete tasks successfully.

**Key findings:**
- "Tool-using LLM agents can violate the very policies they are deployed to enforce while appearing to complete the task successfully"
- Policy-permissive environments: a tool executes any well-formed call even when the corresponding state transition is forbidden by domain policy
- Result: "a silent failure mode" — the agent reports success while violating constraints
- Fix: deterministic verification gates that check state transitions outside the LLM's reasoning loop

**Relevance to agent design:** This is the enforcement-side counterpart to P7 (Contradiction Detection). Even if the prompt doesn't contain contradictions, the agent may violate policies through tool calls that the prompt can't gate. Deterministic external verification is the architectural answer — "the agent that follows the policy cannot be the agent that enforces it."

### ScopeJudge: Cost-Aware Pre-Execution Gating for Security Agents
**arXiv:2607.07774, July 2026**

> Pre-execution scope gating prevents out-of-scope tool calls before they happen.

**Key findings:**
- "A single out-of-scope tool call can breach a client's engagement boundary, disrupt production, or void a bug-bounty finding"
- The scope boundary is declared in the user's request and must be inferred from intent — not a fixed safety policy
- Pre-execution gating (before the tool call) is more reliable than post-hoc review
- Cost-aware: the gating mechanism itself has a computational budget

**Relevance to agent design:** Extends the delegation contract concept (P3). Scope boundaries should be enforced before delegation, not after. A delegation matrix that specifies "who handles what" should also specify enforcement: does the agent gate itself (prompt-based) or does the infrastructure gate (pre-execution)?

### DevMemory: Structured Memory for AI Coding Agents
**arXiv, October 2026**

> Persistent, trust-scored, cross-scope knowledge retention for coding agents.

**Key findings:**
- "AI coding agents operate without persistent memory; useful outputs produced in one session are unavailable in the next"
- Trust-scored knowledge retention: outputs from sessions are graded for correctness before being stored
- Cross-scope retrieval: information from one project transfers to others when relevant
- Addresses the "fresh context" problem — each session starts from zero

**Relevance to agent design:** This is the infrastructure-side solution to P2 (Conditional Prompt Loading). Instead of loading all possible instructions into every session (or loading nothing between sessions), a persistent memory system loads only what the current task needs, scored by trust and relevance. This is the architectural implementation of "conditional loading."
