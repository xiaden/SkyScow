# Configure branch protection

Protect important branches with required reviews, checks, and push rules.

## What to protect
- The default branch.
- Release branches and any branch from which artifacts are cut.

## Common rules
- Require pull request reviews before merging.
- Require status checks to pass (CI) before merging.
- Require up-to-date branches before merging (stale branches blocked).
- Require linear history, signed commits, or dismiss stale reviews where policy demands.
- Restrict who can push directly, forcing changes through reviewed PRs.
- Set branch protection as a server-side rule; it is not bypassable the way local hooks are.

## Apply
Branch protection is configured in the repository settings (Settings > Branches > Add rule) or via the REST/GraphQL API. Prefer settings for human-managed rules.

https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches | checked 2026-08-28 | re-check on branch-protection policy or API change

## Boundary
Protection complements, but does not replace, the verification-before-push discipline of the owning skills (`gg-core`/`gg-repos`/`gg-actions`). Align protection rules with that baseline; do not treat protection as the sole control.
