# Sign and verify commits

Attach a verifiable signature to commits so others can confirm the author.

## Choose a key type
Git accepts GPG and SSH signing keys. Configure which with `git config commit.gpgsign` or sign explicitly per commit.

## Sign a commit
- Configure the signing key and default: `git config user.signingkey <key>` and `git config commit.gpgsign true`.
- Sign a single commit: `git commit -S -m "message"`.
- Enable signing by default for the repository: `git config commit.gpgsign true`.

## Verify signatures
- `git log --show-signature` — verify signatures on recent commits.
- `git verify-commit <commit>` — verify one commit explicitly.
- `git config gpg.program <path>` — point Git at your signing program if it is not on PATH.

## GitHub verification
GitHub shows a Verified badge on commits whose signature it can verify against a key the author has uploaded to their account. See the current GitHub policy and upload procedure:
https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification | checked 2026-08-28 | re-check on GitHub signature-verification policy change

## Safety
- Never expose your private signing key. Anyone with it can forge your identity.
- A signature verifies authorship of the commit, not the safety of its content; review still applies.
