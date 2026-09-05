# Commit and create isolated branches

Create focused, reviewable commits on an isolated line of history.

## Make a focused commit
1. `git status` to see what changed.
2. `git diff` to review the exact changes before staging.
3. Stage deliberately: `git add <path>` (or `git add -p` for hunks). Stage only what belongs to one logical change.
4. Commit with a clear subject and body: `git commit -m "subject" -m "why, not just what"`.
5. Verify: `git log --oneline -1` and `git show --stat HEAD`.

Prefer small, single-purpose commits over large mixed ones. Keep the subject short and imperative ("Add", "Fix", "Refactor"), and explain the rationale in the body.

## Create an isolated branch
- `git switch -c <feature>` to start a new branch from the current HEAD.
- Give branches a descriptive name that states the intent.
- Work on the feature branch; keep the default branch stable.
- `git switch -` to return to the branch you were on before.

## Inspect what you are about to change
- `git status` — staged / unstaged / untracked.
- `git diff` — unstaged changes.
- `git diff --cached` — staged changes.
- `git log --oneline --decorate -10` — recent history with branch and HEAD markers.

## Clean up a merged or abandoned local branch
- `git switch -` back to the default branch first.
- `git branch -d <branch>` deletes a fully merged branch; `git branch -D <branch>` forces deletion of an unmerged branch.
- Verify with `git branch` that only intended branches remain.

Local branch/commit state is owned here. Pushing that branch to a remote and opening a PR is `gg-repos`; the workflow lifecycle (branch + push a workflow change, run, collect, iterate) is `gg-actions`.
