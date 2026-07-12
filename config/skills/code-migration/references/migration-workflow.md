# Migration Workflow

Step-by-step commands for a complete migration.

## Step 1: Identify the Migration

```bash
# Find all usages of the old pattern (project-specific)
python scripts/discover_import_chains.py src.helpers.files_helper

# Or grep for specific functions
grep -r "build_path" src/

# Generic alternatives (language-agnostic)
# npm/npx: npx knip, npx ts-prune, npx depcheck
# Python: vulture, dead
```

## Step 2: Create the Canonical Location

Move the logic to its proper layer (components for business logic, helpers for pure utilities).

## Step 3: Update All Call Sites

```bash
# Find all files that import the old module
grep -r "from src.helpers.files_helper import" src/
```

## Step 4: Ban the Old Pattern (If Still Exists)

If old code still exists and has callers, add a temporary ruff ban to prevent new usages:

```toml
# Add to ruff.toml during migration
[lint.flake8-tidy-imports.banned-api]
"src.helpers.files_helper.build_path".msg = "Use path_comp.build_library_path_from_input()"
```

**Remove the ban after deleting the old code.** Bans for deleted patterns are garbage.

## Step 5: Delete the Old Code

```bash
git rm src/helpers/old_module.py
```

## Step 6: Update Skills

```bash
python scripts/validate_skills.py --check-refs
```

## Step 7: Verify Migration Complete

```bash
# Check that all traces are gone
python scripts/check_migration.py src.helpers.old_module

# If migration plan included a ruff ban, verify it exists
python scripts/check_migration.py src.helpers.old_module --expect-ban

# Full QC
python scripts/run_qc.py
pytest
```

The script validates:

- [ ] Old code is **deleted**, not deprecated
- [ ] No imports of the old module remain
- [ ] No skill references to old pattern
- [ ] No `# TODO: remove` comments remain
- [ ] (With `--expect-ban`) Ruff ban exists
