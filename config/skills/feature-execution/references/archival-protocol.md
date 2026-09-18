````markdown
# Feature Archival Protocol

How to close out a completed feature execution: archive completed plan files and, when a DD bundle is in use, move the completed bundle to its completed design bin. DD completion is represented by the DD's `**Status:** Completed` metadata; no completion manifest is generated or required.

---

## Completion Record

No completion manifest is generated or required. Use the DD's `**Status:** Completed` metadata, the bundle contents, and completed plan files as the audit trail. The DD status remains authoritative even when moving the bundle is pending or unsuccessful, so a bundle may temporarily remain under `artifacts/designs/pending/{feature}/` for a retry.

---

## Internal DD Tool Usage

DD operations are performed by internal agents through the registered OpenCode plugin tools `dd_create`, `dd_read`, and `dd_archive`. `dd_create` writes `artifacts/designs/pending/{slug}/DD.md`; `dd_read` prefers the pending bundle before the completed bundle; and `dd_archive` validates linked plans, sets the DD status to `Completed`, and moves the bundle when possible. Direct `python3 -m common.tools.<module>` invocation is only the focused test boundary. These tools do not provide generic artifact writes, arbitrary artifact filesystem access, or a user-facing CLI.

## Move Protocol

Move plan files from active directories to `artifacts/plans/completed/` using the plan archival tool. When a DD bundle is being archived, use the internal agentic `dd_archive` tool; do not use generic file moves for DD operations.

### Artifacts to Move

| Source | Destination | Notes |
| --- | --- | --- |
| `artifacts/plans/pending/TASK-{feature}-*.md` | `artifacts/plans/completed/TASK-{feature}-*.md` | All plan files — includes fix plans |
| `artifacts/designs/pending/{feature}/` | `artifacts/designs/completed/{feature}/` | Entire DD bundle: DD.md, README.md, CONTRACTS.md, part scopes, and root ADVERSARIAL.md; no COMPLETION.md |

### Move Order

1. **Plans first** — move all `TASK-{feature}-*.md` files, leaving them under `artifacts/plans/completed/`
2. **DD bundle** — use the internal agentic `dd_archive` tool to move the entire `artifacts/designs/pending/{feature}/` directory to `artifacts/designs/completed/{feature}/` (including root DD.md, README.md, CONTRACTS.md, part scopes, and ADVERSARIAL.md). No `COMPLETION.md` is generated or required.

The complete bundle is moved as one unit after `DD.md` has `**Status:** Completed`. If the move cannot complete, retain the completed DD in its pending bundle location and retry; the status itself is authoritative.

### Verification

After moving, confirm clean state:

```
# These should return no results:
artifacts/plans/pending/TASK-{feature}-*.md          → none remain
artifacts/designs/pending/{feature}/                   → directory gone
artifacts/designs/pending/{feature}/DD.md              → file gone

# These should exist:
artifacts/plans/completed/TASK-{feature}-*.md              → all plans present
artifacts/designs/completed/{feature}/DD.md                → design doc exists with `**Status:** Completed`
artifacts/designs/completed/{feature}/CONTRACTS.md         → ledger preserved
artifacts/designs/completed/{feature}/README.md            → decomposition preserved  
artifacts/designs/completed/{feature}/DD.md                → design doc preserved
```

---

## Standalone Plan Archival

Not all plans are part of multi-part features. Single plans (`artifacts/plans/pending/TASK-{name}.md` without letter suffixes) also need archival.

**For standalone plans:**
1. No completion manifest is generated or required — the plan's own checkboxes and annotations are the audit trail
2. Move: `artifacts/plans/pending/TASK-{name}.md` → `artifacts/plans/completed/TASK-{name}.md`
3. No parts directory or design doc to move

---

## Auditability Guide

When revisiting a completed feature, read artifacts in this order:

1. **`artifacts/designs/completed/{feature}/DD.md`** — Original intent and authoritative completion status
3. **`artifacts/designs/completed/{feature}/README.md`** — How it was decomposed
4. **`artifacts/designs/completed/{feature}/CONTRACTS.md`** — What was actually built (signatures, schemas)
5. **Individual `artifacts/plans/completed/TASK-*.md` plans** — Step-by-step implementation details with annotations
````
