---
name: refactor-clean
description: Detect and remove dead code, unused exports, unused dependencies, and duplicate implementations using knip, depcheck, and ts-prune. Covers risk assessment, safe deletion order, and DELETION_LOG.md audit trail. Use when cleaning up a codebase, removing unused code, auditing dependencies, or consolidating duplicates.
---

# Refactor & Clean

**Purpose:** Systematically identify and remove dead code, unused exports, unused dependencies, and duplicates — with an audit trail and safe rollback at every step.

---

## When to Use

**Trigger conditions:**

- Cleaning up a codebase after a large feature removal or migration
- Auditing unused npm dependencies or TypeScript exports
- Consolidating duplicate implementations across modules
- Preparing a repo for handoff, open-source release, or major refactor
- User mentions knip, depcheck, ts-prune, or dead code detection

**Do NOT use this skill when:**

- Actively developing a feature (cleanup mid-flight causes merge conflicts)
- Right before a production deployment (no time for rollback if a false positive bites)
- Test coverage is below ~60% (can't verify removals safely)
- Working in code you don't understand — research first, clean second
- The codebase has no build/lint pipeline (you can't verify removals)

---

## Workflow

### 1. Analyze Phase

Run detection tools in parallel. Each tool has a different lens — use all three and cross-reference.

| Tool | What it finds | Key flags |
|------|--------------|-----------|
| **knip** | Unused files, exports, dependencies, types | `--include exports,types` to focus; `--strict` to catch re-exports |
| **depcheck** | Unused npm dependencies | `--ignores=<pkg>` for known dev-time-only deps |
| **ts-prune** | Unused TypeScript exports | `-p tsconfig.json` to scope; pipe through `grep -v` to exclude public API |
| **eslint** | Unused disable directives, variables | `--report-unused-disable-directives` |

```bash
npx knip --include exports,dependencies,files
npx depcheck
npx ts-prune -p tsconfig.json | grep -v "index.ts"
npx eslint . --report-unused-disable-directives --quiet
```

**Gotchas:**
- knip reports re-exports as unused even when consumed externally — verify against public API surface
- ts-prune can't see dynamic imports (`import()`) or `require()` calls — grep for those separately
- depcheck flags devDependencies used only in scripts (e.g., `tsx`, `ts-node`) — check `package.json` scripts
- Tools disagree on barrel files (`index.ts`) — these are often false positives

### 2. Risk Assessment

Categorize each finding before removing:

| Risk level | Criteria | Action |
|-----------|----------|--------|
| **SAFE** | Unused export with zero internal/external imports; unused devDependency | Remove immediately |
| **CAREFUL** | Potentially used via dynamic import, reflection, or plugin registration | Grep for string references; check if registered in config |
| **RISKY** | Part of public API, shared utility, or barrel re-export | Do not remove without confirming external consumers |

For each item:
1. `grep -rn "symbolName" src/` — confirm zero live references
2. Check for dynamic imports: `grep -rn "import(.*symbolName" src/`
3. Check git history: `git log --oneline -5 -- path/to/file` — understand why it exists
4. Verify it's not in the public API surface (check `exports` in `package.json`, README docs)

### 3. Remove Phase

Safe deletion order (each step verifiable independently):

1. **Unused imports** — `eslint --fix` or manual removal
2. **Unused private functions** — internal, no external risk
3. **Unused exported functions** — after confirming zero consumers
4. **Unused types/interfaces** — after confirming no type-only imports
5. **Unused files** — last, after all their exports are confirmed dead
6. **Unused dependencies** — `npm uninstall <pkg>` (updates `package.json` + lockfile)

After each removal:
```bash
npm run build && npm test && npm run lint
```

### 4. Consolidate Phase

For duplicate code found during analysis:

1. **Pick the winner** — most feature-complete, best tested, most recently modified
2. **Update all imports** to point at the winner
3. **Delete the duplicate**
4. **Verify** build + tests pass
5. **Log** in DELETION_LOG.md

### 5. Verify Phase

Final gate before committing:

```bash
npm run build      # Builds successfully
npm test           # All tests pass
npm run lint       # No new lint errors
npx knip           # Re-run to confirm findings are resolved
```

---

## Safety Checklist

**Before removing anything:**
- [ ] Detection tools run and findings categorized
- [ ] Grep confirms zero live references
- [ ] Dynamic imports checked
- [ ] Public API surface verified
- [ ] Backup branch created (`git checkout -b cleanup/dead-code-YYYY-MM-DD`)

**After each removal:**
- [ ] Build succeeds
- [ ] Tests pass
- [ ] No new lint errors
- [ ] Committed with clear message (`chore: remove unused <thing>`)
- [ ] DELETION_LOG.md updated

---

## Error Recovery

If something breaks after removal:

1. `git revert HEAD && npm install && npm run build && npm test`
2. Identify the failure — was it a dynamic import, tool false negative, or external consumer?
3. Mark the item as **"DO NOT REMOVE"** in DELETION_LOG.md with the reason
4. Fix forward with updated grep patterns (e.g., add the dynamic import pattern to your search)

---

## References

- **DELETION_LOG.md format and examples:** See [`references/deletion-log.md`](file:///home/opencode/.config/opencode/skills/refactor-clean/references/deletion-log.md)
