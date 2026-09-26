---
name: artifact-logging
description: Procedures for logging observations, decisions, and discoveries during agent work. Load when you need to write or read logs, create ADRs, or understand logging conventions.
---

# Artifact Logging

**Purpose:** Procedures and conventions for logging observations, decisions, and discoveries during agent work. Covers log writing, log reading, ADR creation, and access rules.

## When to Use

**Trigger conditions:**
- Writing or reading agent log entries (`log_write`, `log_read`)
- Creating or committing Architecture Decision Records (`adr_suggest`, `adr_commit`)
- Understanding log access rules across agent hierarchies
- Following logging conventions during Change DAG execution

**Do NOT use this skill for:**
- Creating design documents (use `dd_create`)
- Writing ASRs (use `asr_create`)
- Managing Change DAGs (use `dag_*` tools)

## When to Log

Log durable knowledge only — entries a future agent (including yourself in later sessions) cannot cheaply recover from the current code, Change DAG/DD, or current external evidence. Logging is for memory, not ceremony: do not log routine progress, obvious observations, successful ordinary commands, trivially rediscoverable facts, or ceremonial status entries.

| Observable fact | Category | Example |
|-----------------|----------|---------|
| An architectural or design decision was made | `decision` | "Used component-level caching over service-level — keeps DI simpler" |
| Work is blocked | `blocker` | "Upstream contract missing — cannot proceed" |
| Important uncertainty remains unresolved | `observation` + tag `uncertainty` | "Unclear if this migration needs a down path — proceeding without" |
| Work deviated from an accepted Change DAG or DD | `observation` + tag `dag-deviation` | Record the drift and its reason |
| A non-obvious codebase fact was discovered | `discovery` | "AQL UPSERT requires all three clauses even when update is empty" |
| An approach was proven to fail | `dead-end` | "Tried using rename on re-exported symbol — doesn't follow re-exports" |
| Important external evidence was found | `research` | "Library scan workflow depends on filesystem watcher, not polling" |
| A risk is left unresolved | `observation` + tag `risk` | Record the unresolved risk and its trigger |

## Log Entry Format

```python
log_write(
    agent="your-agent-name",  # e.g., "change-dag-runner", "qa-reviewer"
    category="observation",   # or "discovery", "decision", "dead-end", "research", "blocker"
    message="Clear description of what happened",
    tags=["dag-slug", "module-name"]  # Required for durable entries: at least one tag
)
```

**Always include:**
- `agent`: Your agent name (e.g., "change-dag-runner", "rnd-dd-author")
- `category`: One of the categories above
- `message`: Clear, specific description
- `tags`: At least one tag for durable entries — a Change DAG slug (e.g., "myfeature-change"), module name, or topic. The `log_write` schema may accept an empty list, but policy requires at least one tag on every durable entry so future agents can find it.

**Often include:**
- Additional `tags` beyond the first — more context improves discoverability (at least one is required; more is often useful)

## Reading Logs

Before starting work, check for relevant context:

```python
# Check for prior observations about this module/area
log_read(agent="your-agent-name", tag="module-name")

# Check for logs from a specific Change DAG
log_read(tag="dag-slug")

# Check for specific categories
log_read(category="discovery")
log_read(category="dead-end")

# Reconstruct execution history (for managers picking up mid-stream)
log_read(since="<timestamp>")  # All logs since a time
log_read(tag="<dag-slug>")   # All logs for a Change DAG
```

## ADR Workflow

When you make a decision that constrains future work:

1. **Log the reasoning first** using `log_write` with category `decision`
2. **Create the ADR** using `adr_suggest` — reference the log entry in `source_log`
3. **User approves** (you must ask)
4. **Commit the ADR** using `adr_commit`

**When to create ADRs:**
- Architectural decisions that constrain future work
- Choosing between approaches with significant tradeoffs
- Changes to public APIs or contracts
- Breaking a previous ADR (supersede it, don't silently ignore)

**When NOT to create ADRs:**
- Implementation details (those go in design docs)
- One-off fixes (those go in logs)
- Trivial choices (just log them)

## Log Access Rules

Agents can read logs from:
- **Own logs**: Your own agent name
- **Up**: Agents that manage you (e.g., a manager can read logs of agents it dispatches)
- **Down**: Agents you manage (e.g., a manager can read its dispatched agents' logs)
- **Audit targets**: Specific agents you're responsible for reviewing

Agents **cannot** read logs from:
- Peer agents (unless explicitly allowed)
- Agents in unrelated departments

## References

- [**`references/logging-patterns.md`**](file:///home/opencode/.config/opencode/skills/artifact-logging/references/logging-patterns.md) — Detailed patterns: Change DAG tag requirements, mid-stream context recovery, discovery logging, dead-end logging


## Process-Artifact Lifecycle

DD adversarial logs live as root-level `ADVERSARIAL.md` files inside each `artifacts/designs/pending/{slug}/` or `artifacts/designs/completed/{slug}/` bundle. Bundle artifacts record their owner, status, and disposition; completed bundles move to `artifacts/designs/completed/{slug}/` or are explicitly deprecated. Large adversarial logs must declare a retention period or an archive/deprecate disposition.

When a Change DAG or DD is superseded, update only its `Status` field according to the ADR/supersession convention, add a back-pointer to the superseding artifact, and remove it from the executable set. Mark stale handoffs superseded when their contract is superseded.
