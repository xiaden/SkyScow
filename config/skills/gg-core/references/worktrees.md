# Work with multiple branches at once

Use linked worktrees to check out multiple branches simultaneously in separate directories.

## Why
A single working tree can only have one branch active at a time. Worktrees let you:
- keep the default branch clean while a feature branch is active elsewhere
- review or test another branch without stashing or switching
- run parallel lines of work without context switching

## Create a worktree
`git worktree add <path> <branch>` checks out `<branch>` (creating it if you pass `-b`) into a new directory at `<path>`.

Example:
`git worktree add ../hotfix -b hotfix/issue-123`

## List and manage
- `git worktree list` — show all linked worktrees and their branches.
- `git worktree remove <path>` — remove a linked worktree (use `--force` after discarding changes).
- `git worktree prune` — clean stale administrative entries after deleting a worktree directory by hand.

## Notes
- A given branch is active in exactly one worktree at a time.
- Each worktree has its own working tree, index, and HEAD, but shares the repository object store.
- Always remove or prune worktrees before deleting their directories to avoid stale metadata.
