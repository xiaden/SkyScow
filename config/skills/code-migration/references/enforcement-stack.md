# Enforcement Stack

Migrations are enforced at every layer:

## 1. Ruff Rules (Syntax-Level)

Ban dangerous imports before code runs:

```toml
# ruff.toml
[lint.flake8-tidy-imports.banned-api]
"time.time".msg = "Use src.helpers.time_helper.now_ms() for timestamps"
"builtins.print".msg = "Use logging via get_logger()"
```

## 2. Import-Linter (Architecture-Level)

Prevent layer violations:

```
helpers cannot import from services
workflows cannot import from interfaces
only ml_backend_essentia_comp.py may import essentia
```

## 3. Skills (Documentation-Level)

Every skill documents what IS canonical, not what WAS.

## 4. validate_skills.py (Tooling-Level)

Catches stale references in skills:

```bash
python scripts/validate_skills.py --check-refs
```
