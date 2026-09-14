---
name: code-migration
description: Move responsibility to a canonical owner and remove the old path. Use for logic migrations, duplicate consolidation, or pattern deprecation; not for new code or ordinary refactoring.
---

# Code Migration

**Core principle:** When you move responsibility from A to B, delete A.

Half-migrations are technical debt. If `files_helper.py` and `path_comp.py` both construct paths, every developer must learn *which one to use*. That ambiguity is the bug.

---

## When to Use

**Trigger conditions:**

- Moving logic from one module/layer to its canonical owner
- Consolidating duplicate implementations of the same responsibility
- Deprecating a pattern in favor of a canonical alternative
- Enforcing import bans after a migration is complete
- Encountering a half-migration that leaves old code coexisting with new

**Do NOT use this skill when:**

- Creating new code from scratch (no migration to perform)
- General refactoring that doesn't move responsibility between owners
- Writing the initial version of a module (nothing to delete)
- Renaming functions or variables without changing where they live
- Test coverage is insufficient to verify correctness after deletion
- The codebase is unstable (fix stability first, then migrate)

---

## Migration Checklist

When moving logic from one location to another:

- [ ] **Move the code** to its canonical location
- [ ] **Update all call sites** (use grep, not hope)
- [ ] **Update skills** that reference the old location
- [ ] **Add ruff rules** to ban imports from the old location
- [ ] **Delete the old code** (not deprecate — delete)
- [ ] **Run validate_skills.py** to catch stale references
- [ ] **Run tests** to confirm nothing broke

If you can't check all boxes, the migration isn't done.

---

## Canonical Owners

Every responsibility has exactly ONE canonical owner:

 | Responsibility | Canonical Owner | NOT |
 | --------------- | ----------------- | ----- |
 | Library path construction | `path_comp.py` | `files_helper.py` |
 | Wall-clock timestamps | `time_helper.now_ms()` | `time.time()` |
 | Monotonic intervals | `time_helper.internal_ms()` | `time.monotonic()` |
 | Essentia calls | `ml_backend_essentia_comp.py` | anywhere else |
 | Logging setup | `logging_helper.get_logger()` | `logging.getLogger()` |
 | Config access | Injected `AppConfig` | `os.environ`, `config.yaml` |

**If two places can do the same thing, one of them is wrong.**

---

## Anti-Patterns

### Deprecation Warnings

If it's deprecated, delete it. Pre-alpha means no backwards compatibility.

### Keeping It Around "Just In Case"

Delete it. Git remembers.

### TODO: Remove After Migration

Remove it now. The migration isn't done until it's gone.

### Wrapper For Compatibility

Update the callers directly. Shims become permanent.

For anti-pattern code examples, see [`references/anti-patterns.md`](file:///home/opencode/.config/opencode/skills/code-migration/references/anti-patterns.md).

---

## External-Boundary Exception

The no-shim rule has exactly one exception: an **externally owned boundary** — a surface this repository does not control and cannot migrate in the same change. This section is the canonical owner of that exception; `config/instructions/compatability.md` applies it at the compatibility instruction layer.

An externally owned boundary is one of these observable boundary classes:

| Boundary class | Observable fact that identifies it |
| --- | --- |
| Persisted data format | Data written by a released version remains on disk or in a datastore after the change |
| Public API or contract | A published interface (HTTP/RPC endpoint, exported public symbol, config file format) is consumed by callers outside this repository |
| Externally consumed artifact | A published build output, package, or file format is fetched or installed by external consumers |

A compatibility path may exist only at such a boundary, and only when **all** of the following hold:

1. The boundary is explicitly identified and named in the change.
2. The compatibility path is marked, in code and in the change description, as temporary migration infrastructure.
3. A removal condition is defined — the observable event (for example, a deprecation window closing or all external consumers migrated) after which the path is deleted.
4. The exception applies only at the named boundary; every internal surface still migrates all active callers and deletes the superseded implementation in the same change.

Remove the path when its removal condition is met. Do not renew or extend it without a new, observable boundary justification.

---

## Decision Framework

When you find duplicate responsibilities:

```
Q: Is there a clear canonical owner?
├─ No  → Decide which location should own it
└─ Yes → Q: Does the old location still exist?
         ├─ Yes → Delete it. Update callers first if needed.
         └─ No  → Good. Verify skills and rules match reality.
```

When consolidating duplicate implementations:

```
Q: Which implementation should be the canonical one?
├─ Most feature-complete  → covers more use cases
├─ Best-tested             → highest confidence, least risk
├─ Most recently used      → reflects current patterns and API design
└─ None clearly best?      → Merge strengths into one canonical location, then delete the rest
```

When someone proposes keeping both:

```
"Can we keep the old one for compatibility?"
→ No. Pre-alpha. Delete it.

"What if something still uses it?"
→ Find it and update it. That's the migration.

"What if we need it later?"
→ Git remembers. Delete it.
```

---

## Enforcement Stack

Migrations are enforced at every layer: ruff rules (syntax), import-linter (architecture), skills (documentation), and validate_skills.py (tooling).

For full configuration details, see [`references/enforcement-stack.md`](file:///home/opencode/.config/opencode/skills/code-migration/references/enforcement-stack.md).

---

## Migration Workflow

1. **Identify** — find all usages of the old pattern (grep, `discover_import_chains.py`, or generic tools like `knip`, `ts-prune`)
2. **Create** — move logic to its canonical location
3. **Update** — change every call site
4. **Ban** — add a ruff ban to prevent new usages (temporary)
5. **Delete** — remove the old code entirely
6. **Update skills** — run `validate_skills.py --check-refs`
7. **Verify** — run migration checks, lint, and tests

For step-by-step commands, see [`references/migration-workflow.md`](file:///home/opencode/.config/opencode/skills/code-migration/references/migration-workflow.md).

---

## Validation

Before considering a migration complete, run the full validation suite.

Manual checks:

- [ ] No wrapper/shim functions exist
- [ ] Tests pass

For automated validation commands, see [`references/migration-workflow.md#step-7-verify-migration-complete`](file:///home/opencode/.config/opencode/skills/code-migration/references/migration-workflow.md#step-7-verify-migration-complete).

**The migration is done when there's no trace of the old pattern.**

---

## Error Recovery

When a migration breaks something — a test fails, a build errors, a file is mangled:

1. **Stop and revert the edit.** Check your context history. Identify which edit caused the breakage and undo it. Do not keep editing — a bad edit cascading into more edits is how files get mangled.
2. **Diagnose.** Run tests to see what actually broke. Was it a missed caller? A botched replacement? A dynamic import that `grep` missed?
3. **Fix the caller, not the deletion.** The migration direction was correct — update the missed caller to use the canonical location. Do not restore the old code to "unblock."
4. **If the deletion itself was wrong** (rare: wrong file deleted, wrong judgment call): restore surgically. `git checkout HEAD~1 -- path/to/deleted_file.py` restores one file without touching anything else from the plan.
5. **Re-verify.** Run tests. Confirm nothing else is broken. Re-delete if you restored temporarily.

**Git remembers. A targeted undo is safer than `git revert HEAD` — the latter nukes unrelated plan work.**

---

## References

- **This skill's references:**
  - [`references/migration-workflow.md`](file:///home/opencode/.config/opencode/skills/code-migration/references/migration-workflow.md) — Step-by-step commands for each phase
  - [`references/enforcement-stack.md`](file:///home/opencode/.config/opencode/skills/code-migration/references/enforcement-stack.md) — Ruff, import-linter, skills, and tooling layers
  - [`references/anti-patterns.md`](file:///home/opencode/.config/opencode/skills/code-migration/references/anti-patterns.md) — Code examples of anti-patterns to avoid
- **Related skills:** `code-migration` enforces the "one canonical owner" rule that other skills document
