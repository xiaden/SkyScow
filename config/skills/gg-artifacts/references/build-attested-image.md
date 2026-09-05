# Build and push a versioned, attested image

Build an immutable, versioned container image on a GitHub-hosted runner, publish it
directly to a registry, and attach provenance, SBOM, and GitHub attestations.

## Sections
- Step 0: visibility and plan branch
- Versioned, immutable image naming
- GitHub-hosted runner
- Scoped workflow permissions
- Direct registry push and the `load: true` limitation
- Provenance / SLSA version selection
- SBOM
- GitHub artifact attestation
- Secret mounts instead of build args
- Fact stamps

## Step 0: visibility and plan branch
Determine repository visibility and account plan before building, because they change
provenance defaults and attestation support. Follow the shared visibility/plan table
(`credentials-and-visibility.md` in this skill's `references/` directory): public
repositories automatically get `mode=max` provenance; private repositories default to
`mode=min`; artifact attestations for private/internal repositories require GitHub
Enterprise Cloud and are not supported on GitHub Enterprise Server.

## Versioned, immutable image naming
- Tag images with a stable, semver-like version (`v1.2.3` or `1.2.3`) and treat tags as
  immutable: never retag or overwrite a released version.
- Consume and verify images by digest, not a mutable tag (`latest`), so a specific
  artifact is unambiguous.
- Derive version tags from metadata with `docker/metadata-action`, or set them
  explicitly with the `tags:` input.

## GitHub-hosted runner
- Run builds on a GitHub-hosted runner (`runs-on: ubuntu-latest`); local Docker is not
  required for the GitHub Actions build/push path.
- Set up Buildx with `docker/setup-buildx-action`, then authenticate with
  `docker/login-action`.

## Scoped workflow permissions
- Request only the permissions the build needs:
  - `contents: read` and `packages: write` to build and publish to GHCR.
  - Add `id-token: write`, `attestations: write`, and `artifact-metadata: write` when
    generating GitHub artifact attestations.
- Do not grant broader `GITHUB_TOKEN` scopes than the build requires.

## Direct registry push and the `load: true` limitation
- Attestations are only preserved on a direct registry push (`push: true`).
- The Docker exporter and `load: true` strip attestations; the runner's local image
  store cannot carry them.
- For a local smoke test, build once with `load: true`; then rebuild with `push: true`
  for the published, attested artifact.

## Provenance / SLSA version selection
- Public repositories automatically receive `mode=max` provenance; private repositories
  receive `mode=min`. Set `provenance: mode=max` explicitly when max-level detail is
  required.
- Pin the provenance schema version (`version=v0.2` or `version=v1`) and match it
  during verification; do not rely on defaults.
- `mode=max` embeds build parameters and the full Dockerfile, so it can expose build
  arguments — keep secrets out of build args (see below).

## SBOM
- SBOM attestations are not automatic. Set `sbom: true` on `docker/build-push-action`,
  or attach an SBOM attestation with `actions/attest` using its `sbom-path` input.

## GitHub artifact attestation
- `actions/attest` is the canonical GitHub artifact-attestation action for container
  images: pass `subject-name` (fully-qualified image name, no tag) and `subject-digest`
  (the digest output of the build step) with `push-to-registry: true`.
- `actions/attest-build-provenance` is a wrapper around it.
- Verify the same predicate type you used at build time.

## Secret mounts instead of build args
- Never pass secrets as build args: `mode=max` provenance records their values.
- Pass secrets through secret mounts (`--secret` / the `secrets:` input), which are
  never included in provenance attestations.

## Fact stamps
https://github.com/docker/build-push-action | checked 2026-08-28 | re-check on docker/build-push-action major change
https://github.com/docker/setup-buildx-action | checked 2026-08-28 | re-check on setup-buildx-action major change
https://github.com/docker/login-action | checked 2026-08-28 | re-check on login-action major change
https://github.com/docker/metadata-action | checked 2026-08-28 | re-check on metadata-action major change
https://docs.docker.com/build/ci/github-actions/attestations/ | checked 2026-08-28 | re-check on Docker attestation or action-major change
https://docs.docker.com/build/metadata/attestations/slsa-provenance/ | checked 2026-08-28 | re-check on SLSA provenance schema change
https://slsa.dev/spec/v1.1/provenance | checked 2026-08-28 | re-check on SLSA provenance spec change
https://github.com/actions/attest | checked 2026-08-28 | re-check on actions/attest major change
https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations | checked 2026-08-28 | re-check on artifact-attestation plan or behavior change
