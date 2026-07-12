---
description: Generate skills from git history analysis. Analyzes commits to extract patterns, conventions, and best practices.
argument-hint: "[scope or topic for skill generation]"
---

# Skill Create

Generate skills from git history analysis: $ARGUMENTS

## Process

1. **Analyze commits** — recent history, file-type patterns, most-changed files
   ```bash
   git log --oneline -100
   git log --name-only --pretty=format: | sort | uniq -c | sort -rn
   git log --pretty=format: --name-only | sort | uniq -c | sort -rn | head -20
   ```

2. **Extract patterns** — commit message conventions, code structure patterns, error handling approaches, review feedback themes

3. **Generate SKILL.md** — structured skill documentation following making-editing-skills conventions

## Output

Creates `skills/[name]/SKILL.md` with patterns, best practices, common mistakes, and examples extracted from project history.
