# Git Conventions

## When This Applies

- When creating any commit
- When opening or reviewing a pull request
- When planning a feature implementation (the workflow starts before code)
- When writing commit messages, PR descriptions, or changelogs

## Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

<optional body — explain WHY, not WHAT>
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

**Violation examples:**
- `fix bug` — no type, no scope, no information
- `WIP` — not a commit message; squash or rebase before pushing
- `feat: add stuff` — vague description; what was added and where?

**Correct examples:**
- `fix(auth): handle expired token refresh without re-login`
- `feat(api): add rate limiting to /users endpoint`
- `refactor(db): extract query builder into separate module`

## Pull Request Workflow

When creating a PR:

1. **Analyze the full diff** — use `git diff [base-branch]...HEAD`, not just the latest commit
2. **Write a comprehensive description:**
   - What changed and why (not just what the commits say)
   - Testing performed (which tests, what coverage)
   - Screenshots or output for visual changes
3. **Include a test plan** with TODOs for any remaining work
4. **Push with `-u`** if it's a new branch

**Violation examples:**
- PR with no description — reviewer has to read every commit to understand intent
- PR that mixes unrelated changes (feature + refactor + dependency bump) — split into separate PRs
- PR without a test plan — how does the reviewer know what to verify?

## Feature Implementation Workflow

Follow this sequence for every feature:

1. **Plan** — Write an implementation plan before coding. Identify dependencies, risks, and phases.  
   *Use the `/plan` command or `planner` agent for complex features.*
2. **TDD** — Write tests first (RED), implement to pass (GREEN), refactor (IMPROVE). Verify tiered coverage.  
   *Use the `/tdd` command or `tdd-guide` agent to enforce the TDD cycle.*
3. **Self-review** — Review your own code before requesting review. Address CRITICAL and HIGH issues; fix MEDIUM when possible.  
   *Use the `/code-review` command or `code-reviewer` agent. See [Review Severity Levels](#review-severity-levels) below.*
4. **Commit & push** — Write detailed conventional commit messages. One logical change per commit.  
   *Before committing, run the `/security` command to verify C01-C08 gates and the `/verify` pipeline.*

**Violation examples:**
- Starting to code without a plan — leads to rework and scope creep
- Skipping self-review — pushes obvious issues to the reviewer
- One giant commit with the entire feature — impossible to review; split by logical change

## Review Severity Levels

When self-reviewing code (or reviewing a PR), classify every issue by severity. The review must not approve code with any unresolved CRITICAL or HIGH issues:

| Severity | Category | Check For | Action |
|----------|----------|-----------|--------|
| **CRITICAL** | Security | Hardcoded secrets, SQL injection, XSS, missing input validation, insecure dependencies, path traversal, auth/authz flaws | Block commit — must fix before proceeding |
| **HIGH** | Code Quality | Functions >50 lines, files >800 lines, nesting >4 levels, missing error handling, `console.log` statements, TODO/FIXME without tracking | Block merge — fix before requesting review |
| **MEDIUM** | Best Practices | Mutation patterns (use immutable instead), unnecessary complexity, missing tests for new code, accessibility issues, performance concerns | Fix when possible — flag in PR description |
| **LOW** | Style | Inconsistent naming, missing type annotations, formatting inconsistencies | Optional — fix if touching the code anyway |

**Review report format** (one line per issue):
```
**[SEVERITY]** file.ts:123
Issue: [Description]
Fix: [How to fix]
```

**Decision rules:**
- CRITICAL or HIGH → block commit, require fixes
- MEDIUM → recommend fixes before merge
- LOW → optional improvements

**Violation examples:**
- Approving code with a CRITICAL security issue — never acceptable
- Using `// eslint-disable` to silence a HIGH severity code quality issue
- Skipping a review because "the changes are small" — every diff gets reviewed

## Enforcement

- **Commit lint:** Use `commitlint` or equivalent to enforce conventional commit format in pre-commit hook
- **CI gate:** Reject PRs with non-conventional commit messages; reject PRs without descriptions
- **Branch protection:** Require at least one approval; require CI to pass before merge
- **PR template:** Enforce a PR template that requires: description, testing performed, test plan
- **Pre-commit verification:** Run the [verification loop](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/verification.md) before every commit
- **Security scan:** Run `/security` or `security-reviewer` agent before merging; block on CRITICAL findings
