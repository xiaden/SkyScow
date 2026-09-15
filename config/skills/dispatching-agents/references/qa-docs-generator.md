# QA-DocsGenerator

Dispatch QA-DocsGenerator to generate documentation for gaps identified by QA-DocsAnalyzer.

## When to Dispatch

**Dispatch when:**
- QA-DocsAnalyzer reports MINOR_DISPATCH or MAJOR_DISPATCH with specific surviving candidates
- You have a concrete list of missing documentation to generate

**Do NOT dispatch when:**
- You need documentation analysis — use `qa-docs-analyzer` instead
- No candidate gaps have been identified — generation needs specific targets

## Dispatch Template

```
Generate documentation for the following gaps.

Context files to read:
- [files that need documentation]
- [reference docs for style/format guidance]

task_family: "[existing task family]"
round: [positive QA round number]

gaps:
  - file: "[path to source file]"
    subject: {kind: symbol, symbol: "[function/class/module that needs docs]"}
    missing:
      - "[function/class/module that needs docs]"
    type: "[docstring | API doc | user doc | README]"
    reason: "[why it needs docs]"
  # ... repeat per gap

Follow project documentation conventions. Verify claims against authoritative code, config, and
manifests — never trust fluent prose. Every invocation ends in exactly one verified terminal decision
(REPAIRED, UNNECESSARY, BLOCKED, or ESCALATED) written durably via qa_record_write BEFORE you return.
UNNECESSARY may never waive a required public/operator documentation requirement. Leaf agent — no
children.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `gaps` | Surviving candidate list from QA-DocsAnalyzer | See template |
| `subject` | Stable identity for the gap | `{kind: symbol, symbol: "src/api/routes/users.deleteUser"}` |
| `file` | Path to source file needing docs | `src/api/routes/users.ts` |
| `missing` | Functions/classes/modules needing docs | `DELETE /users/:id`, `UserService.deleteUser()` |
| `type` | Documentation type | `docstring`, `API doc`, `user doc`, `README` |
| `reason` | Why docs are needed | "Public API endpoint — no documentation for DELETE behavior" |
| `task_family` | Existing task family for the durable record | `TASK-api-A-endpoints` |
| `round` | Positive QA round number | `1` |

## Terminal Contract

Every invocation ends in **exactly one** verified terminal decision, written via `qa_record_write`
**before return**:

- `REPAIRED` — docstrings/docs were changed. Requires non-empty actual verification and at least one
  changed file or symbol.
- `UNNECESSARY` — repository-derived evidence shows the symbol genuinely needs no documentation.
  Requires non-empty repository-derived evidence. **Never** waive a required public/operator
  documentation requirement.
- `BLOCKED` — the gap cannot be completed now (too complex to document meaningfully, missing
  authoritative source, no filler would be honest).
- `ESCALATED` — a systemic documentation or contract problem outside the generator's remit was found.

The record requires `writer`/`agent` = `qa-docs-generator`, the task family and positive round, a stable
`subject` (kind plus at least one identifying key), `decision`, `evidence`, `verification`,
`changed_files`/`changed_symbols` (empty only for a no-change outcome; `REPAIRED` needs at least one),
and `source_kind: "analyzer-finding"` plus `source_ref`. A failed or missing write is a failed
invocation.

## Expected Output

- Generated docstrings in source files and/or updated documentation files (`docs/`, `README.md`, etc.)
- The terminal decision and the durable record path (`artifacts/logs/qa-rounds/{family}/round-{N}/qa-docs-generator.jsonl`)
- Accuracy verification against authoritative code/config/manifests
- Any docs that couldn't be generated with reason

This agent is **leaf** — it does not spawn children. It writes docstrings, updates user docs, fixes API
docs, records its terminal decision, and reports completion.

## After Generation

- Verify generated docs are accurate (docstrings match function signatures)
- Check for stale references (links to renamed/moved files)
- Confirm the durable record was written before the report
- Report the documentation coverage improvement
