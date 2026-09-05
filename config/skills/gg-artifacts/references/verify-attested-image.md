# Verify digest, provenance, signer, and SBOM

Verify an image's integrity and provenance before consuming or releasing it: registry
authentication, image digest, provenance predicate, trusted signer, and SBOM.

## Sections
- Validate the GitHub CLI first
- Verify registry authentication
- Verify the image digest
- Verify provenance with `gh attestation verify`
- Verify the SBOM
- Fact stamps

## Validate the GitHub CLI first
The installed `gh` may be an unverified shim; whether it is, is a repo-local environment fact —
see `ggt-conventions`. Validate its version and behavior before trusting output; do not
improvise a fallback client. The signer
matcher had a bypass that was fixed in the CLI security releases; use exact-match
verification, never a loose pattern, on a patched, behavior-validated CLI.

## Verify registry authentication
Authenticate to the registry before verification (`docker login ghcr.io`, or an
equivalent credential) so the image and its attestations can be resolved.

## Verify the image digest
- Resolve the image by digest so the exact artifact is unambiguous.
- Confirm the digest matches the digest recorded at publish time (the build step's
  `digest` output). `docker buildx imagetools inspect` inspects the image manifest.

## Verify provenance with `gh attestation verify`
- `gh attestation verify oci://ghcr.io/owner/name:tag -R owner/name` verifies the
  signature, certificate identity, and provenance predicate.
- Enforce identity precisely: use `--repo` (or `--owner`) and, ideally,
  `--signer-workflow`/`--signer-repo`/`--signer-digest` and `--cert-identity` so the
  signer must match exactly. Use `--digest-alg` matching the artifact.
- Match the predicate type you pinned at build time. The command defaults to
  `https://slsa.dev/provenance/v1`; if the build used `version=v0.2`, pass
  `--predicate-type https://slsa.dev/provenance/v0.2`.
- Use `--format json` for machine-readable verification and additional policy checks.
- `--bundle-from-oci` fetches attestations from the registry when they were pushed there.

## Verify the SBOM
SBOM attestations use a non-default predicate. Verify with the matching
`--predicate-type`, for example `https://spdx.dev/Document/v2.3` for an SPDX SBOM, and
inspect with `--format json`.

## Fact stamps
https://cli.github.com/manual/gh_attestation_verify | checked 2026-08-28 | re-check on gh attestation or SLSA predicate change
https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations | checked 2026-08-28 | re-check on artifact-attestation plan or behavior change
https://docs.docker.com/build/metadata/attestations/slsa-provenance/ | checked 2026-08-28 | re-check on SLSA provenance schema change
https://slsa.dev/spec/v1.1/provenance | checked 2026-08-28 | re-check on SLSA provenance spec change
