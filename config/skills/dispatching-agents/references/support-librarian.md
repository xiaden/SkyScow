# Support-Librarian

Dispatch Support-Librarian when materially relevant **process history** (logs, dead ends, prior discoveries, prior design-doc history, unresolved historical questions, and other retained process artifacts) may constrain R&D or decomposition routing; record an evidence-based skip when it does not. Governing decisions and requirements come from the workspace-local `architecture-decisions` and `system-requirements` skills, not from Support-Librarian.

## When to Dispatch

**Use when:**
 - Before dispatching RnD-Manager or Change-DAG-Author when prior process artifacts materially constrain the route
 - Entering an unfamiliar module or subsystem where prior work history is relevant
 - You need to avoid repeating a recorded dead end or contradicting prior process history

**Do NOT dispatch when:**
- The task is trivial and context is obvious from current code
- You've already gathered context for this area in the current session
- The work is purely mechanical (typo fixes, formatting, simple renames)
- No retained process artifacts exist for the area

## Dispatch Template

```
Gather process-artifact context before we begin work on [TOPIC].

Search for:
- Logs from prior work on related modules: [module names]
- Dead ends or failed approaches recorded in this area
- Prior design-doc history that constrains this area

Return a structured briefing: prior observations, dead-ends to avoid, and historical constraints.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[TOPIC]` | The feature or area you're about to work on | "Tag autocomplete", "Library scan performance" |
| `[module names]` | Code modules that might have relevant agent logs | "src/components/tagging/", "src/workflows/scan/" |

## Expected Output

Support-Librarian returns a structured briefing with:
- **Prior observations** — discoveries and patterns noted by past agents
- **Dead-ends to avoid** — approaches that were tried and failed
- **Design-doc history constraints** — existing prior designs that bound the current work

It does **not** return governing ADRs/ASRs. For those, load the workspace-local
`architecture-decisions` / `system-requirements` skill and read a specific record by
identity with `adr_read` / `asr_read`.

## After Receiving Briefing

1. **Pass the briefing downstream.** Include it in dispatch prompts to RnD-Manager, Change-DAG-Author, or other agents.
2. **Respect dead-ends.** Don't retry approaches that were documented as failures.
3. **Get governance elsewhere.** When a governing decision or requirement is relevant, load the appropriate local governance skill; cite a specific ADR/ASR by identity when you need its full text.

## How Support-Librarian Searches

Support-Librarian is a read-only agent that navigates retained process artifacts using:

| Artifact type | Tool | What it finds |
|--------------|------|---------------|
| Agent logs | `log_read(agent, category, tag)` | Observations, discoveries, dead-ends |
| Design docs | `dd_read(name)` | Full design documents and prior design history |
| Retained process artifacts | `aft_search` / `read` | Prior discoveries and unresolved historical questions |

It returns a **curated summary**, not raw dumps. The caller receives the process history that matters, not a list of matching file paths.

## Example Dispatch → Briefing

### Dispatch

```
Gather process-artifact context before we begin work on Tag Autocomplete.

Search for:
- Logs from prior work on related modules: src/components/tagging, src/services/search
- Dead ends or failed approaches recorded in this area
- Prior design-doc history that constrains this area

Return a structured briefing: prior observations, dead-ends to avoid, and historical constraints.
```

### Expected Briefing Shape

```
## Process-Artifact Context Briefing: Tag Autocomplete

### Prior Observations
- agent/2025-06-12: "Trie rebuild blocks main thread on large tag sets (>5000). Consider web worker."

### Dead-Ends to Avoid
- LRU caching on autocomplete results (invalidation complexity)
- DB LIKE queries for autocomplete (latency, prior design ruled this out)

### Design-Doc History Constraints
- DD "Tag System v2": Autocomplete must return results in <50ms. Trie must stay.
```

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Dispatch with no module names filled in | Fill every bracketed field with concrete values |
| Topic too broad ("the whole project") | Narrow to one feature or module |
| Module names are file paths without log history | Use actual directories where agents have worked |
| Asking Librarian to find governing ADRs/ASRs | Load the `architecture-decisions` / `system-requirements` skill and read the record by identity |
| Skipping the dispatch entirely | Dispatch anyway — missing context is still a useful finding |


### Required Lifecycle Checks

The briefing must include DD status/location and ledger-vs-verbatim-request conformance, superseded artifacts/back-pointers, and ownership-closure gaps. A handoff annotation is not caller ownership. Flag improperly pending accepted DDs and executable superseded Change DAGs before downstream dispatch.
