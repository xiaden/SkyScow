# Logging System: How It Works

**The logging system is your memory across sessions for durable knowledge that is not recoverable from the artifacts themselves.** Log architectural/design decisions, blockers, important uncertainty, deviations from an accepted plan/DD, non-obvious discoveries, proven dead ends, important external evidence, and unresolved risks. Do not log routine progress, obvious observations, successful ordinary commands, trivially rediscoverable facts, or ceremonial entries.

---

## The Core Rule

**Read before you act. Write after you discover.**

You have two tools: `log_read` and `log_write`. Use them in that order.

---

## When You Must Read Logs

Before starting any non-trivial work, check what's already known:

| Situation | What to read |
|-----------|-------------|
| Entering an unfamiliar module | `log_read(agent="agent", tag="module-name")` |
| Starting a complex task | `log_read(agent="agent")` — prior sessions' findings |
| Something seems wrong or inconsistent | `log_read(category="discovery")` + `log_read(category="dead-end")` |
| About to make an architectural choice | `log_read(category="decision")` — prior choices on this topic |

**This takes 5 seconds and can save hours.** Skip it at your own risk — and the risk of every agent that comes after you.

---

## When You Must Write Logs (Durable Entries Only)

Write a log entry only when it records durable knowledge that a future agent cannot cheaply recover from the current code, the plan/DD, or current external evidence. Each trigger below is an observable fact — an artifact exists, a decision was made, a plan/DD deviation occurred — never a judgment call about whether something "feels" worth remembering.

| Observable fact | Category | Example |
|-----------------|----------|---------|
| An architectural or design decision was made | `decision` | "Used component-level caching over service-level" |
| Work is blocked | `blocker` | "Upstream contract missing — cannot proceed" |
| Important uncertainty remains unresolved | `observation` (tag: `uncertainty`) | "Unclear if migration needs down path — proceeding without" |
| Work deviated from an accepted plan or DD | `observation` (tag: `plan-deviation`) | "Skipped step 4; contract already satisfied" |
| A non-obvious codebase fact was discovered | `discovery` | "Config loading in X bypasses ConfigService" |
| An approach was proven to fail | `dead-end` | "Tried rename on re-export — doesn't follow re-exports" |
| Important external evidence was found | `research` | "Library scan depends on filesystem watcher, not polling" |
| A risk is left unresolved | `observation` (tag: `risk`) | "No regression test exists for the retry path" |

**Do not log** routine progress, obvious observations, successful ordinary commands, facts trivially rediscoverable from the current code/plan/artifacts, or ceremonial status entries. Noise dilutes the durable record and costs future agents more than it saves.

**The syntax is minimal:**

```
log_write(agent="agent", category="discovery", message="What you found", tags=["module-name"])
```

**Tags are not optional for durable entries.** Every log needs at least one tag (module name, plan title, or topic) so future agents can find it. Untagged logs are unfindable logs — they might as well not exist.

---

## Durable Logs Are Not Authority

Logs are durable memory, not a source of truth over what you can observe now. A stale log must never override current evidence. **Current code, explicit requirements, accepted ADR/DD, tests, and current external evidence all outrank a stale log entry.** Verify against the current artifact before treating a logged claim as correct; if a log contradicts current evidence, trust the evidence and record the drift.

---

## What Happens When Durable Knowledge Is Not Logged

- The next agent re-discovers the same gotcha from scratch
- The same dead-end approach gets tried again
- The same architectural tradeoff gets debated without knowing the prior decision
- A plan/DD deviation or unresolved risk is silently lost

**Failing to log a durable entry is not neutral: it forces every following session to recover knowledge that was already known.** This applies to durable entries, not to routine progress.

---

## For Full Procedures

This file covers the behavioral rule — when and why to log. For detailed procedures (ADR workflow, cross-agent log access rules, plan-tag requirements, log archiving), load the `artifact-logging` skill at the point where you need those procedures.
