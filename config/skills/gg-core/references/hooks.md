# Configure and troubleshoot local hooks

Run scripts automatically at local Git events to enforce or check your own workflow.

## What hooks do
Git runs hook scripts (executables in `.git/hooks/`) at lifecycle points such as:
- `pre-commit` — before a commit is created (style, lint, quick checks).
- `commit-msg` — validate the commit message before it is recorded.
- `pre-push` — before refs are pushed to a remote.
- `post-checkout`, `post-merge`, `prepare-commit-msg` — other lifecycle events.

## Enable a hook
1. `.git/hooks/` contains `.sample` files (for example `pre-commit.sample`).
2. Create an executable script at the hook name: `touch .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`.
3. The script exits non-zero to abort the operation.

## Share hooks across a repository
Point all clones at a shared location: `git config core.hooksPath .githooks`, then keep executable hook scripts under `.githooks/` in the repository. A non-zero exit from a committed hook still blocks the operation for every contributor.

## Troubleshooting
- Hook does not run: confirm the file is executable and named exactly (no `.sample`) at the path Git uses (`git rev-parse --git-path hooks`).
- Hook aborts unexpectedly: run it manually with the same arguments to see its output and exit code.
- Path confusion: if `core.hooksPath` is set, Git ignores `.git/hooks`; confirm which location is active with `git config --get core.hooksPath`.

## Boundary
Hooks are a local developer convenience, not a security boundary. They are bypassable and never replace server-side review or branch protection.
