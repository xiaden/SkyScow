# QA-DocsGenerator

Dispatch QA-DocsGenerator to generate documentation for gaps identified by QA-DocsAnalyzer.

## When to Dispatch

**Dispatch when:**
- QA-DocsAnalyzer reports MINOR_DISPATCH or MAJOR_DISPATCH with specific gaps
- You have a concrete list of missing documentation to generate

**Do NOT dispatch when:**
- You need documentation analysis — use `qa-docs-analyzer` instead
- No gaps have been identified — generation needs specific targets
- The docs are trivial (one-line docstrings on obvious functions) — write them yourself

## Dispatch Template

```
Generate documentation for the following gaps:

Context files to read:
- [files that need documentation]
- [reference docs for style/format guidance]

gaps:
  - file: "[path to source file]"
    missing:
      - "[function/class/module that needs docs]"
    type: "[docstring | API doc | user doc | README]"
    reason: "[why it needs docs]"
  # ... repeat per gap

Follow project documentation conventions. Write docs, verify accuracy. Leaf agent — no children.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `gaps` | List of gaps from QA-DocsAnalyzer | See template |
| `file` | Path to source file needing docs | `src/api/routes/users.ts` |
| `missing` | Functions/classes/modules needing docs | `DELETE /users/:id`, `UserService.deleteUser()` |
| `type` | Documentation type | `docstring`, `API doc`, `user doc`, `README` |
| `reason` | Why docs are needed | "Public API endpoint — no documentation for DELETE behavior" |

## Expected Output

- Generated docstrings in source files
- Updated documentation files (`docs/`, `README.md`, etc.)
- Coverage improvement summary
- Any docs that couldn't be generated with reason

This agent is **leaf** — it does not spawn children. It writes docstrings, updates user docs, fixes API docs, and reports completion.

## After Generation

- Verify generated docs are accurate (docstrings match function signatures)
- Check for stale references (links to renamed/moved files)
- Report documentation coverage improvement
