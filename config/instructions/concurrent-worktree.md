# Concurrent Worktree Safety

Agents must assume that other agents or users may be working in the same Git worktree concurrently. Concurrent changes to unrelated files, and changes to the same file between reads, are possible and must be preserved unless the user explicitly directs otherwise.

## Preserve concurrent work

- Re-read a file immediately before editing it when concurrent work may have changed it; base the edit on its current contents.
- Preserve changes that you did not create. Do not overwrite, revert, hide, or discard them as a conflict-resolution shortcut.
- Keep edits within the requested scope. Do not use repository-wide staging or cleanup commands to simplify concurrent work.
- If concurrent changes make the requested change ambiguous or unsafe, stop and ask the user rather than choosing which work to keep.

## Destructive Git operations require confirmation

Before running any Git operation that can discard, overwrite, hide, or rewrite working-tree changes, index state, commits, refs, or remote history, stop and ask the user for confirmation. State the exact command, the paths or refs it affects, what existing work could be lost or changed, and any safer alternative.

This confirmation requirement includes, but is not limited to:

- `git reset` (especially `--hard` or `--mixed`)
- `git checkout` or `git switch` when they replace or abandon local work
- `git restore`
- `git clean`
- destructive `git stash` operations such as `drop` or `clear`
- deleting branches or refs, including `git branch -D`
- rebases, history rewrites, and merges that may alter or replace existing work
- force-pushes, including `--force-with-lease`
- scripts or compound commands that invoke any of the above indirectly

Do not use these operations to resolve concurrent edits without the user's approval. Prefer non-destructive inspection (`git status`, `git diff`, and relevant history/ref inspection), targeted edits, or a disposable worktree when isolation is needed.
