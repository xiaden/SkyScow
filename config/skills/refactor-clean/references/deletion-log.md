# DELETION_LOG.md Format

An audit trail for every dead-code removal session. Commit this file alongside the cleanup so future developers understand what was removed and why.

## Table of Contents

- [Template](#template)
- [Example Entry](#example-entry)
- [When to Log](#when-to-log)
- [DO NOT REMOVE Marker](#do-not-remove-marker)

---

## Template

```markdown
## [YYYY-MM-DD] Refactor Session: <short description>

### Unused Dependencies Removed
| Package | Version | Last used | Size impact |
|---------|---------|-----------|-------------|
| package-name | x.y.z | never / last used in <file> | ~XX KB |

### Unused Files Deleted
| File path | Reason | Replaced by |
|-----------|--------|-------------|
| src/old-component.tsx | Unused since migration | src/new-component.tsx |

### Unused Exports Removed
| File | Symbols removed | Consumers confirmed |
|------|----------------|-------------------|
| src/utils/helpers.ts | `foo()`, `bar()` | grep: 0 references |

### Consolidated Duplicates
| Kept | Removed | Reason for choice |
|------|---------|-------------------|
| src/utils/format-date.ts | src/lib/date-format.ts | More tests, newer |

### Impact Summary
- Files deleted: N
- Dependencies removed: N
- Exports removed: N
- Lines removed: N
- Bundle size reduction: ~N KB (if measurable)

### Testing
- [ ] All unit tests passing
- [ ] Build succeeds
- [ ] Lint clean
- [ ] Manual smoke test completed (if applicable)
```

---

## Example Entry

```markdown
## [2025-03-15] Refactor Session: Post-migration cleanup

### Unused Dependencies Removed
| Package | Version | Last used | Size impact |
|---------|---------|-----------|-------------|
| moment | 2.30.1 | never (migrated to date-fns) | ~68 KB gzipped |
| lodash | 4.17.21 | never (using native methods) | ~24 KB gzipped |

### Unused Files Deleted
| File path | Reason | Replaced by |
|-----------|--------|-------------|
| src/legacy/auth-v1.ts | Superseded by auth-v2 migration | src/auth/auth.ts |
| src/components/OldDashboard.tsx | Feature removed in Q4 | N/A |

### Unused Exports Removed
| File | Symbols removed | Consumers confirmed |
|------|----------------|-------------------|
| src/utils/helpers.ts | `formatLegacyDate()`, `parseOldConfig()` | grep: 0 references |
| src/api/client.ts | `fetchV1Users()` | grep: 0 references |

### Consolidated Duplicates
| Kept | Removed | Reason for choice |
|------|---------|-------------------|
| src/utils/format-date.ts | src/lib/date-format.ts | 12 tests vs 3 tests, more recent |

### Impact Summary
- Files deleted: 2
- Dependencies removed: 2
- Exports removed: 4
- Lines removed: 347
- Bundle size reduction: ~92 KB gzipped

### Testing
- [x] All unit tests passing
- [x] Build succeeds
- [x] Lint clean
- [ ] Manual smoke test completed (not applicable — no UI changes)
```

---

## When to Log

Log every removal session, even small ones. The log serves three purposes:

1. **Rollback guide** — if something breaks weeks later, you know what was removed
2. **Knowledge transfer** — new team members see what was dead and why
3. **Pattern detection** — recurring false positives reveal tool limitations

Skip logging only for trivial single-item removals (e.g., one unused import in a WIP commit).

---

## DO NOT REMOVE Marker

When a removal causes a failure, mark it immediately:

```markdown
### DO NOT REMOVE
| Symbol/File | Reason | Date discovered |
|-------------|--------|-----------------|
| `fetchV1Users()` | Called via dynamic import in plugin-loader.ts | 2025-03-16 |
```

This prevents future cleanup sessions from re-attempting the same removal.
