# Publish documentation to GitHub Pages

Build static documentation, upload it as a Pages artifact, and deploy it to GitHub
Pages, from either the repository's Pages source or a GitHub Actions workflow.

## Sections
- Publishing sources
- Canonical build -> upload -> deploy sequence
- Required workflow permissions
- The github-pages environment
- Public by default, and plan branches
- Project versus user/org sites
- Delayed publication
- Fact stamps

## Publishing sources
Two publishing sources are supported:
- **Repository Pages source:** deploy from a branch (or a `/docs` folder on a
  branch) of the source repository. No build control; best for simple sites. The
  source branch can be any branch; the source folder is the repo root `/` or a
  `/docs` folder. Choose this when no custom build step is needed.
- **Actions workflow:** a GitHub Actions workflow builds the site and deploys it.
  Choose this when you need build control or a non-Jekyll static-site generator.
  GitHub publishes starter workflow templates for common frameworks.

## Canonical build -> upload -> deploy sequence
For an Actions-source site the deployment always follows this order:
1. **Build** the static files (check out the repository, run the site generator).
2. **Upload** the static files as a Pages artifact with
   `actions/upload-pages-artifact` (current major v5, verified 2026-08-28). Point
   its `path` input at the built output folder; it packages the files into an
   artifact named `github-pages` by default.
3. **Deploy** the artifact with `actions/deploy-pages` (current major v5, verified
   2026-08-28). It publishes the artifact to Pages and reports the deployed page
   URL.

`actions/configure-pages` (current major v6, verified 2026-08-28) enables Pages
and extracts site metadata for static-site-generator starter workflows; it is
optional for a hand-written workflow.

## Required workflow permissions
Request only the permissions the publication needs:
- `contents: read` for the checkout in the build job.
- `pages: write` so the deploy job can create a Pages deployment.
- `id-token: write` so the deploy job can request an OIDC token used to verify the
  deployment originates from the appropriate branch/source.
Do not grant broader `GITHUB_TOKEN` scopes than publication requires.

## The github-pages environment
Run the deploy job against the `github-pages` deployment environment
(`environment: name: github-pages`). The environment is created automatically on
first use. Recommend a deployment protection rule so only the default branch can
deploy; when a protection rule is set, it takes precedence over the source-branch
rule. Pages uses the OIDC token to validate the branch/ref claim before deploying.

## Public by default, and plan branches
Follow the shared visibility table (credentials-and-visibility.md in this skill's
references directory) for the full branches. In short: Pages sites are publicly
available by default even when the source repository is private or internal;
GitHub Free requires a public repository; private publication is Enterprise
Cloud-gated; and user/org sites cannot be treated as private project documentation.

## Project versus user/org sites
- **User and organization sites** live in a repository named `<owner>.github.io`
  and serve at `https://<owner>.github.io`; one per account.
- **Project sites** live in the project's repository and serve at
  `https://<owner>.github.io/<repositoryname>`; one per repository.
Treat user/org sites as public, never as a private project documentation area.

## Delayed publication
Publication is not immediate. Deployments and DNS/HTTPS changes take time to take
effect (DNS changes can take up to 24 hours to propagate). Treat publication as a
delayed operation and verify the deployed site rather than assuming instant
availability.

## Fact stamps
https://github.com/actions/configure-pages | checked 2026-08-28 | re-check on configure-pages major change
https://github.com/actions/upload-pages-artifact | checked 2026-08-28 | re-check on upload-pages-artifact major change
https://github.com/actions/deploy-pages | checked 2026-08-28 | re-check on deploy-pages major change
https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site | checked 2026-08-28 | re-check on Pages publishing-source change
https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages | checked 2026-08-28 | re-check on Pages site-type or limit change
https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments | checked 2026-08-28 | re-check on environment-protection change
