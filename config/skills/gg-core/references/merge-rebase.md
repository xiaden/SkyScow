# Merge or rebase: choose the integration strategy

Integrate finished work with an explicit history policy.

## When to prefer merge
- Integrating a reviewed, shared branch back into the default branch.
- Preserving the true history and context of when changes were made.
- You must not rewrite commits that others have based work on.
- Team convention is a merge-integrated history.

`git merge <branch>` creates a merge commit joining the two histories.

## When to prefer rebase
- Cleaning up a private or local branch before review or before merging.
- Keeping a feature branch current with the latest default branch.
- Producing a clean, linear history.
- You own the branch and no one else has based work on it.

`git rebase <base>` re-applies your commits on top of a new base.

## Rebasing before review
1. `git rebase <default-branch>` to move your local commits onto the latest.
2. Resolve conflicts file by file, then `git add` and `git rebase --continue`.
3. To abandon the rebase: `git rebase --abort`.

## Golden rules
- **Never rebase a shared or public branch.** Rewriting published history breaks everyone who based work on it.
- Rebase your own unshared work freely; merge shared work.
- When updating a branch you have pushed, prefer `--force-with-lease` over `--force` (see recover-reflog for the safety net).

## Resolving conflicts
- `git status` lists conflicted paths.
- Edit each file to resolve, keeping both sides' intent.
- `git add` the resolved file, then finish with `git merge --continue` or `git rebase --continue`.
- If you get lost, `git merge --abort` or `git rebase --abort` returns to the pre-operation state.
