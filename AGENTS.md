# AGENTS.md — HolyCode

## Repository shape

HolyCode is a Docker image definition for OpenCode, not an application repository. There is no project `src/`, `package.json` script suite, typecheck, or test suite. The image provides general runtimes/tools; the project mounted at `/workspace` supplies its own dependencies and tests.

## Runtime architecture

```
docker compose up → entrypoint.sh → UID/GID + directories → bootstrap.sh
                  → sleev-gateway-sync.sh → s6-overlay /init
                                                        ├── opencode web :4096
                                                        └── sleev gateway
```

- `scripts/entrypoint.sh` runs as root on every start: remaps `opencode` with `PUID`/`PGID`, creates XDG directories, checks SQLite WAL compatibility, reconciles config, synchronizes Sleev, then execs `/init`.
- s6-overlay v3 is PID 1. Active services are `s6-overlay/s6-rc.d/opencode` and `s6-overlay/s6-rc.d/sleev`; the repository’s `xvfb` source is removed by the Dockerfile, so Chromium runs native headless.
- `scripts/sleev-gateway-sync.sh` selects one versioned CLI/gateway release under `/home/opencode/.local/share/sleev/`, verifies downloaded artifacts by official manifest, size, SHA-256, and reported version, then atomically updates `current` symlinks. `SLEEV_VERSION` must be stable semver; failed sync aborts startup.
- `scripts/sleev-wrapper.sh` is only a tolerant CLI shim. It does not supervise or restart the gateway; s6 owns gateway supervision.

## High-value files

- `Dockerfile` — source of truth for pinned image/tool versions, architecture branches, security gates, shipped config manifest, and installed entrypoints.
- `scripts/entrypoint.sh`, `scripts/bootstrap.sh` — root startup and config reconciliation; use `runuser -u opencode` for user-level operations.
- `scripts/sleev-gateway-sync.sh`, `scripts/sleev-wrapper.sh` — Sleev release selection and CLI compatibility shim.
- `config/opencode.json`, `config/agents/`, `config/commands/`, `config/skills/`, `config/plugins/`, `config/tools/` — shipped OpenCode configuration. Note the directory is `plugins/` (plural).
- `s6-overlay/s6-rc.d/` — service definitions. `run`/`finish` files are shell scripts and must remain executable; each active service’s `type` is `longrun`.
- `.github/workflows/pr-validation.yml` — PR build plus `opencode --version` smoke test. `.github/workflows/docker-publish.yml` — multi-arch GHCR release on `v*` tags or manual dispatch.
- `scripts/validate_chromium_seccomp.py` and `config/chromium-seccomp.json` — pinned Chromium sandbox profile validation.

## Commands and verification

```bash
# Required focused security check
python3 scripts/validate_chromium_seccomp.py

# Match PR validation locally
docker build -t holycode-pr-test .
docker run --rm holycode-pr-test opencode --version

# Run locally
cp .env.example .env       # set at least one provider key
docker compose up -d       # web UI: http://localhost:4096
docker exec -it holycode bash
```

There is no repo-wide lint/test command; validate Dockerfile changes with the image build and smoke test, and review `git diff --check`. Do not run `npm test` or invent project-level checks for this repository.

## Persistent config reconciliation

The image ships `/usr/local/share/holycode/bootstrap-manifest.tsv`; `bootstrap.sh` reconciles it with `/home/opencode/.config/opencode/` on every start. Unchanged shipped files may update or be removed, but edited files, user deletions, and symlinks are preserved. Existing files without provenance are recorded as legacy `0.0.0` and preserved. Preview or review changes with:

```bash
docker exec holycode /usr/local/bin/bootstrap.sh --check
docker exec -it holycode /usr/local/bin/bootstrap.sh --interactive
```

Config changes are manifest-shipped to existing users; do not use the old sentinel-file workflow.

## Operational constraints

- Compose must attach `config/chromium-seccomp.json` via `security_opt`; Chromium’s setuid sandbox is required. Do not “fix” browser failures with `--no-sandbox` or `seccomp=unconfined`. Keep `shm_size: 2g`.
- If `/home/opencode` data is on CIFS/SMB, mount with `nobrl,mfsymlinks` for SQLite WAL and plugin symlinks. Keep `/home/opencode/.cache/opencode` on local disk, even when the data/workspace mounts are on a NAS.
- `PUID`/`PGID` control ownership of bind-mounted files. `GIT_USER_NAME` and `GIT_USER_EMAIL` are applied by bootstrap on each reconciliation unless `HOLYCODE_SKIP_GIT_CONFIG=1`.
- Keep exact versions in `Dockerfile`; Renovate manages Dockerfile dependency pins, including its regex-managed npm/Python entries and GitHub Actions. Do not manually “float” versions.
- Dockerfile builds target `amd64` and `arm64`. Binary download blocks must preserve both architecture branches and their integrity checks.
