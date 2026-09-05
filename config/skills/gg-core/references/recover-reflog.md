# Recover lost history with the reflog

Undo a reset, a lost commit, or a bad merge by recovering the exact previous state.

## Inspect the reflog first
`git reflog` lists every time HEAD moved: commits, checkouts, resets, merges, rebases. It is the first place to look after any mistake.

## Recover a reset or lost commit
1. `git reflog` to find the commit you want (rightmost column is the message or operation).
2. Reset back to it: `git reset --hard <commit>` moves the current branch and working tree there, or `git checkout <commit>` inspects it detached before you decide.
3. Create a branch so you do not lose it again: `git switch -c <recovery-branch> <commit>`.

## Recover after a bad merge or rebase
- `git reflog` shows the pre-merge / pre-rebase HEAD. Reset to it to undo the operation.
- During a rebase, `git rebase --abort` or `git merge --abort` returns to the pre-operation state.

## Deeper recovery
If the commit is not in the reflog (for example dangling after a garbage-collect), search the object store: `git fsck --lost-found` reports unreachable objects; commits appear as `dangling commit` lines you can inspect with `git show`.

## Safety
- `git reset --hard` discards working-tree changes; confirm against `git status` and the reflog first.
- Never run a garbage-collect before you are sure you no longer need recoverable history.
- Recovery is local to your repository; it does not restore anything already lost from a shared remote.
