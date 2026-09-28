# Support-Researcher

Dispatch Support-Researcher for deep, multi-file codebase investigation or external documentation research.

## When to Dispatch

Dispatch only when bounded local evidence establishes that unresolved substantive investigation remains, for example:
- Deep multi-file dependency tracing (call chains or dependency graphs across layers)
- Unclear integration ownership
- External library documentation, API references, or version-specific behavior that must be verified
- Complex repository behavior bounded localization cannot resolve
- Another agent lacks information to make routing decisions

**Escalation order:** bounded/local evidence first → load the relevant local skill/governance when applicable → consult targeted historical context when materially useful → dispatch Support-Researcher only when unresolved substantive investigation remains.

**Do NOT dispatch when:**
- A single file read or `aft_search` will answer the question
- The task is a simple "find where X is defined" lookup
- You're doing routine implementation work that doesn't require research
- The code is merely unfamiliar, or was not touched earlier in the session — unfamiliarity and session history are not triggers (see Nyx's Direct-Work Invariant)
- The question can be answered by loading a local governance skill (for example `architecture-decisions` or `system-requirements`), checking existing logs, or consulting process artifacts

## Dispatch Template

```
Investigate [TOPIC] in the codebase.

Questions to answer:
1. [specific question]
2. [specific question]

Return findings with file paths and code locations. Depth: [quick / standard / thorough].
```

## Required Fields

- **`[TOPIC]`**: What to investigate (e.g., "how library scanning works", "tag calibration flow")
- **`[specific question]`**: Concrete questions to answer — aim for 2–5 distinct questions
- **Depth**: How deep to go
  - `quick`: Surface-level, file locations and symbol names only
  - `standard`: Moderate depth, key code paths with relevant snippets
  - `thorough`: Deep dive — all relevant code, edge cases, related patterns

## Expected Output

Support-Researcher returns:
- Findings organized by question
- File paths and line numbers for all code references
- Code snippets where relevant
- Summary of key insights
- A named `scope_signal` (`WITHIN_BRIEF` / `BROADER_SAME_REQUIREMENT` / `NEW_REQUIREMENT`) the caller consumes deterministically

## After Research

- Use findings to make routing and implementation decisions; consume `scope_signal` per the caller's contract (broader same-requirement surface → re-evaluate routing/tier; new requirement → user decision)
- Pass relevant findings to downstream agents in their dispatch prompts
- Log significant discoveries (`log_write`) if they reveal architectural patterns or dead-ends
- Store reusable knowledge as a subsystem skill if the area is stable and frequently referenced

## Validation Checklist

Before dispatching, verify:
- [ ] The topic requires multi-file or multi-layer investigation (not a single-file lookup)
- [ ] Questions are specific and answerable (not "tell me everything about X")
- [ ] Depth level matches the information need (don't use `thorough` for a file-location question)
- [ ] Previous research on this topic doesn't already exist — check logs and process artifacts first (and the local governance skills for governing decisions)
- [ ] The dispatch prompt includes all Required Fields with concrete values
