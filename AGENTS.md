# AGENTS.md — HolyCode

## What this repo is

A Docker image definition that packages [OpenCode](https://opencode.ai) (AI coding agent) into a container with 50+ dev tools, headless Chromium, and provider-agnostic model support. There is **no application source code** — no build step, no test suite, no package.json scripts. The repo produces a Docker image consumed via `docker compose`.

## Architecture

```
entrypoint.sh  →  UID/GID remap  →  bootstrap.sh (first boot only)  →  s6-overlay /init
                                                                        ├── xvfb (:99)
                                                                        ├── opencode web (:4096)
                                                                        └── sleev gateway
```

- **s6-overlay v3** is the process supervisor (PID 1). Services live in `s6-overlay/s6-rc.d/`.
- **entrypoint.sh** remaps the `opencode` user to host UID/GID via `PUID`/`PGID`, pre-creates XDG directories, checks CIFS/SMB SQLite WAL compatibility, and hands off to s6.
- **bootstrap.sh** runs on first boot only (sentinel: `~/.config/opencode/.holycode-bootstrapped`). It copies shipped config, plugins, and commands into the bind-mounted home directory.

## Key files and directories

| Path | Role |
|---|---|
| `Dockerfile` | Single source of truth for all installed packages and versions |
| `scripts/entrypoint.sh` | Container entrypoint — UID/GID, dirs, CIFS check, bootstrap gate |
| `scripts/bootstrap.sh` | First-boot config copy + git identity setup |
| `scripts/sleev-wrapper.sh` | Translates sleev CLI (expects systemd) to s6 supervision |
| `config/opencode.json` | Shipped OpenCode config (enables AFT plugin) |
| `config/agents/` | 30 OpenCode agent definitions |
| `config/commands/` | Shipped OpenCode commands (`/onboard`, `/rw`, ECC suite) |
| `config/skills/` | 20+ skill definitions |
| `config/plugin/background-agents.ts` | Async delegation plugin |
| `config/plugins/` | Additional plugins (ECC hooks, tools) |
| `config/tools/` | Tool implementations (helpers, schemas) |
| `s6-overlay/s6-rc.d/` | Service definitions for opencode, xvfb, sleev |
| `renovate.json` | Automated dep bumps (Dockerfile ARGs, npm, pip, GitHub Actions) |

## Developer commands

```bash
# Build the image locally
docker build -t holycode:local .

# Run with the quick-start compose file
cp .env.example .env   # fill in at least one API key
docker compose up -d   # web UI at http://localhost:4096

# Exec into the running container
docker exec -it holycode bash

# Re-trigger first-boot bootstrap (updates shipped configs)
docker exec holycode rm /home/opencode/.config/opencode/.holycode-bootstrapped
docker compose restart
```

## Config update flow

Shipped config lives at `/usr/local/share/holycode/` inside the image. On first boot, `bootstrap.sh` copies it to `~/.config/opencode/` **only if the target doesn't already exist**. This means:
- Updating the image does NOT overwrite user-customized config.
- To force a re-copy of shipped config, delete the sentinel file and restart.
- New agents, skills, or commands added to `config/` will only reach existing users on a fresh data volume or after sentinel deletion.

## Conventions and gotchas

- **No app source**: don't look for `src/`, `package.json` scripts, `tsconfig.json`, or try `npm test`. There is no application — only Docker infrastructure and OpenCode configuration.
- **Renovate manages versions**: `renovate.json` auto-bumps Dockerfile ARGs, npm packages, and pip packages. Don't manually bump versions without understanding the renovate rules — it may conflict.
- **`bat` is `batcat`**: Debian names the binary `batcat`. The Dockerfile symlinks `bat` → `batcat`.
- **sleev wrapper**: The real `sleev` CLI assumes systemd. `sleev-wrapper.sh` catches the expected failure and signals s6 to start the gateway binary instead.
- **SQLite WAL on CIFS/SMB**: The entrypoint tests WAL locking. If the data mount is on a NAS, CIFS mount options `nobrl,mfsymlinks` are required.
- **Two compose files**: `docker-compose.yaml` is the quick-start. `docker-compose.full.yaml` is the reference with every option documented and commented out. They serve different purposes — don't conflate them.
- **Cache mount must be local disk**: `./local-cache/opencode` should always be on local storage, not NAS. If the whole project is on network storage, use an absolute local path for the cache volume.
- **No CI/CD in repo**: No `.github/workflows/` exists currently. The only automation is Renovate for dependency bumps.
- **Multi-arch**: The Dockerfile supports `amd64` and `arm64` via `$TARGETARCH`. Binary downloads (s6, lazygit, delta, eza) branch on architecture.
- **Container user**: The `node` user from the base image is renamed to `opencode` (UID 1000). `PUID`/`PGID` remap it at runtime.

## When editing this repo

- **Dockerfile changes**: pin exact versions. Renovate will bump them. Test with `docker build`.
- **Config changes** (`config/agents/`, `config/commands/`, `config/skills/`, `config/plugin/`): these are shipped to new users on first boot. Existing users must delete the sentinel to receive updates. Consider this when changing behavior.
- **s6 service changes**: service files are shell scripts run by s6-overlay. They must be executable (`chmod +x`). The `type` file must contain `longrun`.
- **Script changes**: `entrypoint.sh` and `bootstrap.sh` run as root before s6 handoff. Use `runuser -u opencode` for user-level operations.
