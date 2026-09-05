# Draft and publish immutable releases

Tag, attach assets, and publish releases without mutating a published tag.

## Preferred flow
1. Create the tag from the protected branch at the version commit.
2. Draft the release associated with that tag.
3. Attach any build artifacts (checksums, binaries, SBOM) as release assets.
4. Review, then publish. Publishing is the point of no return — treat the tag and assets as immutable after that.

## Immutability
- Once published, do not rewrite or delete the tag; consumers may have pinned or downloaded it.
- Prefer draft -> attach assets -> publish so nothing is publicly mutable during setup.
- If a tag must move, coordinate the change explicitly; a moved tag is a supply-chain risk for anyone who pinned it.

## Release hygiene
- Include release notes describing behavior changes and breaking changes.
- Attach checksums and verification material so consumers can verify what they download.
- Reference the source commit and any closing issues for traceability.

https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases | checked 2026-08-28 | re-check on GitHub releases or immutable-release change
