# Support-Librarian

Dispatch Support-Librarian to gather artifact context (ADRs, logs, design docs) before R&D or Planning work.

## When to Dispatch

**Use when:**
- Before dispatching RnD-Manager or RnD-DDAuthor (design work needs prior decisions)
- Before dispatching Exec-Planner (implementation needs architectural context)
- Entering an unfamiliar module or subsystem
- You need to avoid contradicting prior architectural decisions

**Do NOT dispatch when:**
- The task is trivial and context is obvious from current code
- You've already gathered context for this area in the current session
- The work is purely mechanical (typo fixes, formatting, simple renames)
- The project has no artifact infrastructure (no ADRs/logs directories exist)

## Dispatch Template

```
Gather artifact context before we begin work on [TOPIC].

Search for:
- ADRs relevant to: [list key architectural areas]
- Logs from prior work on related modules: [module names]
- Design docs that constrain this area

Return a structured briefing: relevant decisions, prior observations, dead-ends to avoid.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[TOPIC]` | The feature or area you're about to work on | "Tag autocomplete", "Library scan performance" |
| `[list key architectural areas]` | Specific domains relevant to the work | "tagging system", "scan workflow", "ML inference pipeline" |
| `[module names]` | Code modules that might have relevant agent logs | "src/components/tagging/", "src/workflows/scan/" |

## Expected Output

Support-Librarian returns a structured briefing with:
- **Relevant ADRs** — key decisions and their rationale
- **Prior observations** — discoveries and patterns noted by past agents
- **Dead-ends to avoid** — approaches that were tried and failed
- **Design doc constraints** — existing designs that bound the solution space

## After Receiving Briefing

1. **Pass the briefing downstream.** Include it in dispatch prompts to RnD-Manager, Exec-Planner, or other agents.
2. **Reference specific ADRs.** When making architectural choices, cite the ADR by name.
3. **Respect dead-ends.** Don't retry approaches that were documented as failures.

## How Support-Librarian Searches

Support-Librarian is a read-only agent that navigates the artifact corpus using:

| Artifact type | Tool | What it finds |
|--------------|------|---------------|
| ADRs | `adr_search(query, tag, status)` | Architectural decisions with rationale |
| Agent logs | `log_read(agent, category, tag)` | Observations, discoveries, dead-ends |
| Design docs | `dd_read(name)` | Full design documents |
| ASRs | `asr_search(query, status)` | Architecture specification requirements |

It returns a **curated summary**, not raw dumps. The caller receives the decisions that matter, not a list of matching file paths.

## Example Dispatch → Briefing

### Dispatch

```
Gather artifact context before we begin work on Tag Autocomplete.

Search for:
- ADRs relevant to: tagging system, autocomplete patterns, search infrastructure
- Logs from prior work on related modules: src/components/tagging, src/services/search
- Design docs that constrain this area

Return a structured briefing: relevant decisions, prior observations, dead-ends to avoid.
```

### Expected Briefing Shape

```
## Artifact Context Briefing: Tag Autocomplete

### Relevant ADRs
- **ADR-0012:** Tag storage as flat array in SQLite — chosen for query simplicity over normalization.
- **ADR-0018:** Autocomplete via prefix trie — in-memory trie over DB LIKE for latency.

### Prior Observations
- agent/2025-06-12: "Trie rebuild blocks main thread on large tag sets (>5000). Consider web worker."

### Dead-Ends to Avoid
- LRU caching on autocomplete results (invalidation complexity)
- DB LIKE queries for autocomplete (latency, trie ADR overrides this)

### Design Doc Constraints
- DD "Tag System v2": Autocomplete must return results in <50ms. Trie must stay.
```

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Dispatch with no architectural areas filled in | Fill every bracketed field with concrete values |
| Topic too broad ("the whole project") | Narrow to one feature or module |
| Module names are file paths without log history | Use actual directories where agents have worked |
| Skipping the dispatch entirely | Dispatch anyway — missing context is still a useful finding |
