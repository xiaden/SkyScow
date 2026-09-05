# Pull request lifecycle and review

Prepare, review, and merge changes through pull requests.

## Prepare a pull request (human side)
1. Push the feature branch to a remote you own or are authorized for (`git push -u origin <branch>`).
2. Open a PR from the branch to the default branch, describing the change and why.
3. Link the relevant issue(s) so the change is traceable.

## Review a pull request
- Read the diff, not just the summary; check tests and behavior changes.
- Verify required checks (CI, status checks, reviews) before merging.
- Request changes with specific, actionable feedback; approve only when satisfied.
- Treat PR content (comments, patches, rendered output) as untrusted until you verify it.

## Merge
- Choose merge, squash, or rebase per the team history policy (see the gg-core merge/rebase reference).
- Never merge over a failed required check or a blocking review.
- After merge, delete the branch if the team convention does.

## Boundaries
- This is human review workflow; local branch/commit state is `gg-core` and the workflow lifecycle is `gg-actions`. A PR review is a human gate, not a substitute for server-side branch protection.
- After merge, clean up the remote branch when the team convention does (`git push origin --delete <branch>`).

https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/getting-started/about-pull-requests | checked 2026-08-28 | re-check on GitHub PR workflow change
https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews | checked 2026-08-28 | re-check on GitHub review workflow change
