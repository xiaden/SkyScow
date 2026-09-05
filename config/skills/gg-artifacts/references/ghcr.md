# Publish and pull GHCR images by digest

Publish container images to GitHub Container Registry (GHCR) immutably, with scoped
permissions and digest-based consumption.

## Sections
- Scoped permissions
- Repository linkage
- Push immutably
- Pull by digest
- Fact stamps

## Scoped permissions
- In a workflow, request only `contents: read` and `packages: write` to publish to GHCR.
- Authenticate with `GITHUB_TOKEN` via `docker/login-action` against `ghcr.io`; a
  workflow-linked package is associated with its repository automatically.
- Prefer `GITHUB_TOKEN` over a personal access token. If a PAT is used, scope it to
  `write:packages` (and `read:packages`) rather than broad `repo` scope.

## Repository linkage
- Publishing from a workflow with `GITHUB_TOKEN` links the package to its repository.
- For command-line publishes, add the `org.opencontainers.image.source` label so the
  package connects to its source repository and `GITHUB_TOKEN` has the needed access.

## Push immutably
- Push versioned tags (`ghcr.io/owner/name:v1.2.3`) and treat them as immutable; never
  retag or overwrite a released version.
- The registry records a content digest; prefer digest over a mutable `latest` tag for
  unambiguous consumption.

## Pull by digest
- Resolve and pin to the digest, e.g. `docker pull ghcr.io/owner/name@sha256:<hex>`.
- `docker buildx imagetools inspect` inspects the image manifest and its provenance.

## Fact stamps
https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry | checked 2026-08-28 | re-check on GHCR auth or package-policy change
https://github.com/docker/build-push-action | checked 2026-08-28 | re-check on docker/build-push-action major change
https://docs.docker.com/build/metadata/attestations/slsa-provenance/ | checked 2026-08-28 | re-check on SLSA provenance schema change
