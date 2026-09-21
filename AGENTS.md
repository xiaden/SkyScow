# AGENTS.md — SkyScow

## Workspace purpose

SkyScow is an agentic software-engineering harness built around OpenCode. This repository owns the container image, shipped OpenCode configuration, runtime entrypoints, process supervision, Sleev integration, and release automation; projects mounted at `/workspace` supply their own application code and dependencies.

## Repository map

| Area | Purpose |
|---|---|
| `Dockerfile` | Pinned base image, tools, architecture branches, integrity checks, shipped configuration, and installed runtime entrypoints. |
| `scripts/` | Startup, UID/GID setup, manifest-based configuration reconciliation, Sleev synchronization, and focused validators. |
| `config/agents/`, `config/commands/`, `config/skills/`, `config/instructions/` | Shipped agent contracts, commands, procedural skills, and workspace instructions. |
| `config/plugins/`, `config/tools/` | OpenCode plugins and Python-backed MCP/AFT tools; `config/tools/tests/` contains the Python tool test suite. |
| `config/opencode.json`, `config/agent-context-budgets.yaml` | Shipped OpenCode plugin registration and context-budget policy. |
| `s6-overlay/s6-rc.d/` | Service definitions for the final image; `opencode` and `sleev` are the active long-running services. |
| `docker-compose.yaml`, `docker-compose.full.yaml` | Quick-start and full runtime configuration, including mounts, secrets, sandbox profile, and shared memory. |
| `tests/` | Focused Bun/TypeScript tests for the native request-context plugin. |
| `.github/workflows/` | Pull-request validation and GHCR image publication workflows. `.github/release.yml` controls release-note categories. |
| `docs/`, `README.md`, `.github/CONTRIBUTING.md`, `.github/SECURITY.md` | User, contribution, troubleshooting, and security documentation. |
| `artifacts/` | Runtime engineering artifacts: request context, designs, plans, and logs. These are process records, not implementation state. |

There are currently no subordinate `AGENTS.md` files; this root file is the repository-wide contract.

## Start here by task

| Task | Start with | Also inspect |
|---|---|---|
| Image, startup, or runtime behavior | `Dockerfile`, `scripts/entrypoint.sh` | `scripts/bootstrap.sh`, `scripts/sleev-gateway-sync.sh`, `s6-overlay/s6-rc.d/`, compose files |
| OpenCode agents, commands, skills, or permissions | Relevant directory under `config/` | `config/opencode.json`, `config/instructions/skill-first.md`, `config/skills/agent-tool-permissions/` |
| Plugins or OpenCode tool bridge | `config/plugins/` or `config/tools/` | `.opencode/package.json`, `tests/`, `config/tools/tests/`, `config/skills/opencode-plugins/` |
| Artifact, DD, plan, ADR, or logging behavior | `artifacts/` and the matching tool under `config/tools/` | `config/skills/artifact-logging/`, `config/skills/making-design-documents/`, `config/skills/making-and-using-task-plans/` |
| Chromium or container security | `config/chromium-seccomp.json`, `scripts/validate_chromium_seccomp.py` | `Dockerfile`, compose `security_opt`, `README.md` |
| CI, release, or image publication | `.github/workflows/validation.yml` or `docker-publish.yml` | `renovate.json`, `.github/release.yml`, Dockerfile, applicable `gg-*` skills |
| Documentation | `README.md` and `docs/` | `.github/CONTRIBUTING.md`, `.github/SECURITY.md`, source and scripts being documented |

## Working rules

- Treat the current source, tests, workflow definitions, and configuration as authoritative. Search results, logs, generated context, and persisted artifacts are pointers and must be checked against source before relying on them.
- Keep dependency and tool versions exact in `Dockerfile`; Renovate manages the declared Dockerfile, GitHub Actions, npm, and Python pins. Do not float versions manually.
- Configuration shipped in the image is reconciled through the bootstrap manifest. Change the source under `config/`; do not edit generated persistent state under `/home/opencode/.config/opencode` as if it were repository source.
- Preserve executable permissions on shell entrypoints and s6 `run`/`finish` files. Preserve both `amd64` and `arm64` branches and their integrity checks in binary-download blocks.
- Use the repository’s existing artifact/tool conventions for DDs, plans, logs, and request context. Do not create a DD or plan for routine edits; load the relevant skill when the task enters that artifact workflow.
- Internal replacements are migrations, not dual implementations: update active callers and remove superseded internal paths. External compatibility is allowed only under the canonical boundary rules in `config/instructions/compatability.md` and the `code-migration` skill.

## Architecture boundaries

- `scripts/entrypoint.sh` owns root-level startup sequencing: identity remapping, directory preparation, WAL compatibility probing, configuration reconciliation, and Sleev synchronization before handing control to `/init`.
- `scripts/bootstrap.sh` owns manifest/hash/ownership reconciliation for shipped OpenCode configuration. `scripts/reconcile_opencode_state.py` handles generated dependency-state cleanup; do not replace either with ad-hoc startup mutations.
- s6-overlay owns service supervision and restart behavior. `scripts/sleev-wrapper.sh` is only a tolerant CLI shim; it does not supervise the gateway. The Sleev synchronizer selects and verifies the release before s6 starts.
- OpenCode behavior is divided by shipped configuration type: agents define agent contracts and permissions, commands define command entrypoints, skills define procedures, plugins define runtime hooks/tools, and `config/tools/` contains Python-backed tool implementations. Use the owning layer instead of adding parallel infrastructure.
- Chromium’s setuid sandbox is a runtime security boundary. Compose must attach `config/chromium-seccomp.json`, retain the required shared memory, and never use `--no-sandbox` or `seccomp=unconfined` as a workaround.
- GitHub credentials are runtime-only: Compose mounts the optional token at `/run/secrets/github_token`, and `scripts/with-github-secret` / `scripts/git-credential-secret` mediate access. Do not persist tokens in the image, `.env`, OpenCode state, or repository files.

## Tooling and exploration

Use the repository-aware AFT tools (`aft_search`, `aft_outline`, `aft_zoom`, `aft_callgraph`, and `aft_inspect`) to locate and understand code, then verify important claims in the source. Start with this map and the relevant local skill before broad exploration. For OpenCode configuration, plugin, agent, command, or skill work, use the corresponding `config/skills/` guidance; for Git/GitHub operations, load the applicable `gg-*` skills before acting.

## Validation and tests

There is no repository-wide package script, type-check command, or universal lint command. Do not invent `npm test` or similar gates. Select checks from the changed surface and report unavailable or CI-deferred checks explicitly.

Required or canonical focused checks:

- Any change to `config/chromium-seccomp.json`: `python3 scripts/validate_chromium_seccomp.py`.
- Any change to shipped skill frontmatter: `python3 scripts/validate_skills.py`.
- Python tool/helper changes: `pytest config/tools/tests` (the suite is configured by `config/tools/tests/conftest.py`).
- Native TypeScript request-context plugin changes: `npx --yes bun test tests/capture_request_context.test.ts` when the `.opencode` plugin dependencies are available.
- Shell changes: run `shellcheck` on the changed shell scripts where available.
- Dockerfile, compose, startup, service, or other runtime changes: `docker build -t skyscow-pr-test .` followed by `docker run --rm skyscow-pr-test opencode --version`; exercise container startup/service health when the environment supports it.
- Every change: review `git diff --check` and the final diff for unintended files or scope creep.

The pull-request workflow in `.github/workflows/validation.yml` currently provides the authoritative CI image build and `opencode --version` smoke test. It does not replace focused local checks for Python, TypeScript, shell, or security-profile changes.

## Build, release, and CI

- `Dockerfile` is the build source of truth, including pinned versions, multi-architecture downloads, checksums/sizes, manifest generation, and installed entrypoints.
- `.github/workflows/validation.yml` validates pull requests and pushes to `main` with an image build and binary smoke test.
- `.github/workflows/docker-publish.yml` is authoritative for GHCR publication: it classifies stable/prerelease/manual channels, requires configured successful CI for tag releases, publishes an immutable SHA-tagged image, creates provenance/SBOM attestations, verifies the attestation, and promotes aliases.
- `renovate.json` defines automated dependency-update coverage. Release-note grouping is configured in `.github/release.yml`.

## Artifacts, design, and planning

- `artifacts/requests/` contains captured conversation context used as primary request evidence for downstream DD or plan authoring.
- `artifacts/designs/pending/` and `artifacts/designs/completed/` contain design-document bundles; the DD and any root-level adversarial record are authoritative for design decisions and status.
- `artifacts/plans/` contains implementation plans and their lifecycle state; plan files are authoritative for execution steps, ownership, and completion criteria.
- `artifacts/logs/` contains durable observations, discoveries, decisions, blockers, and QA records. Logs preserve context but do not outrank current source, tests, accepted DDs, or explicit requirements.
- Use the artifact tools and matching skills rather than inventing new formats or writing process artifacts into source directories. The `artifacts/` tree is not a substitute for repository tests or CI evidence.

## Security and safety

Do not weaken the Chromium sandbox, integrity verification, secret mediation, startup-failure behavior, or least-privilege workflow permissions. Never commit credentials or API keys. When exposing the OpenCode web UI beyond loopback, configure its password authentication; the service can execute code with mounted workspace and provider credentials. Report security-sensitive changes and validate them with the focused security/build checks above.

## Deeper guidance

Read `README.md` for user-facing runtime and persistence details, `.github/CONTRIBUTING.md` for contribution expectations, and `.github/SECURITY.md` for vulnerability reporting. Procedural guidance lives in `config/skills/`; especially `artifact-logging`, `ci-lint-test-gates`, `opencode-plugins`, `agent-tool-permissions`, `gg-actions`, `gg-artifacts`, `code-migration`, and `update-docs`. Canonical cross-cutting instructions are under `config/instructions/`, notably `validation-mandate.md`, `compatability.md`, `skill-first.md`, and `logging-system.md`.
