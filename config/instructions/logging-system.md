# Logging System: How It Works

**The logging system is your memory across sessions.** Every discovery, dead-end, decision, and observation you write persists. Every log you skip is context a future agent (including you) will lack. Silence is the most expensive form of technical debt — it forces repeated exploration, repeated mistakes, and repeated research.

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

## When You Must Write Logs

Every time you encounter something worth remembering:

| You encounter... | Log it as... | Example |
|-----------------|-------------|---------|
| A fragile pattern, inconsistency, or gotcha | `discovery` | "Config loading in X bypasses ConfigService" |
| An approach that failed | `dead-end` | "Tried rename on re-export — doesn't follow re-exports" |
| A choice between approaches | `decision` | "Used component-level caching over service-level" |
| Something you're unsure about | `observation` (tag: `uncertainty`) | "Unclear if migration needs down path — proceeding without" |
| Context uncovered during research | `research` | "Library scan depends on filesystem watcher, not polling" |

**The syntax is minimal:**

```
log_write(agent="agent", category="discovery", message="What you found", tags=["module-name"])
```

**Tags are not optional.** Every log needs at least one tag (module name, plan title, or topic) so future agents can find it. Untagged logs are unfindable logs — they might as well not exist.

---

## What Happens When You Don't Log

- The next agent re-discovers the same gotcha from scratch
- The same dead-end approach gets tried again
- The same architectural tradeoff gets debated without knowing the prior decision
- Each session starts from zero, burning tokens and time on solved problems

**Not logging is not neutral. It's actively harming every session that follows.**

---

## For Full Procedures

This file covers the behavioral rule — when and why to log. For detailed procedures (ADR workflow, cross-agent log access rules, plan-tag requirements, log archiving), load the `artifact-logging` skill.

But do not wait to load the skill before logging. The rule is: **encounter → log.** If you know the category and you have a message, write it now. Load the skill later if you need the advanced features.
