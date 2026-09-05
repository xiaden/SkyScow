# Manage and verify remotes

Add, inspect, and safely use GitHub remotes.

## Inspect
- `git remote -v` — show all remotes and their fetch and push URLs.
- `git remote show <name>` — detailed remote state (HEAD, branches, tracking).

## Add, rename, change
- `git remote add origin <url>` — add a remote named `origin`.
- `git remote rename <old> <new>` — rename a remote.
- `git remote set-url <name> <new-url>` — change a remote URL.

## Choose the URL form
Prefer the HTTPS form for authenticated clones. GitHub does not accept password authentication over HTTPS; use a token (fine-grained PAT or GitHub App) with the credential helpers described in gg-env. Never embed credentials in URLs.

https://docs.github.com/en/get-started/getting-started-with-git/managing-remote-repositories | checked 2026-08-28 | re-check on GitHub remote or authentication change

## Verify identity before acting
- Confirm the origin URL matches the repository you intend to use.
- Treat any remote whose identity you have not verified as untrusted until proven.
- Never invent a remote for a repository that has none; record the absence rather than guessing a URL.

## Push and cleanup
- `git push -u origin <branch>` — push a new branch and set upstream tracking.
- `git push` — push committed changes on a tracked branch.
- `git push origin --delete <branch>` — remove a remote branch after its PR is merged.
- `git fetch --prune` — drop local refs to remote branches that no longer exist.

## Safety
- Never put a token or password in the URL, `.git/config`, or any committed file.
- Prefer `--force-with-lease` when updating a branch you have pushed.
- Review fetch refspecs before pulling from an unfamiliar remote.
