---
name: gg-artifacts
description: Use ONLY when building, publishing, attesting, or verifying versioned Docker images with provenance, SBOM, and GitHub attestations: versioned immutable image naming, GitHub-hosted runner builds, GHCR digest publication, SLSA provenance version selection, SBOM generation, and exact signer/digest/provenance verification. Load before building or verifying any versioned attested container artifact.
---

# gg-artifacts

**Purpose:** Build, publish, attest, and verify versioned, attested Docker artifacts for release and platform operators, using GitHub-hosted runners and direct registry pushes. Nothing here is a volatile fact — time-sensitive claims (action majors, provenance schema versions, plan gates) live in the dated references, never in this body.

## When to use
- Building and pushing a versioned, immutable container image
- Generating provenance (SLSA) and SBOM attestations for an image
- Publishing images to GHCR and pulling them immutably by digest
- Verifying an image's digest, provenance, signer, and SBOM before consuming or releasing it

**Do NOT use** for general Docker administration, local Docker setup, or non-GitHub registries — out of scope. **Do NOT use** for workflow authoring or security fundamentals — load `gg-actions`. **Do NOT use** for credentials, secrets, or visibility/plan facts beyond the shared table — load `gg-env`.

## First safe step
Start from the visibility/plan branch before building: determine repository visibility and account plan, because public and private repositories get different provenance defaults and attestation support. Consult the shared visibility table before anything else.

## Task index
- Build and push a versioned, attested image (naming, hosted runner, provenance/SBOM, attestation) -> references/build-attested-image.md
- Verify digest, provenance, signer, and SBOM before consuming or releasing -> references/verify-attested-image.md
- Publish and pull GHCR images immutably, with scoped permissions -> references/ghcr.md
- Visibility/plan branching, credential safety, and shared Docker/attestation facts -> references/credentials-and-visibility.md

## Boundary
This skill covers the GitHub-hosted remote-Docker path: building, publishing, attesting, and verifying versioned images on GitHub-hosted runners because local Docker is unavailable (`ggt-conventions` records that repo-local limitation). Non-GitHub registries and general Docker administration are out of scope. The workflow lifecycle (dispatch, run, watch, collect, cancel, iterate) is owned by `gg-actions`; credentials/PAT hygiene is `gg-env`.

## Unmatched task
Consult the official Docker and GitHub documentation: <https://docs.docker.com/build/> and <https://docs.github.com/en/packages>.
