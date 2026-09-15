# Changelog

All notable changes to SkyScow will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

SkyScow was originally derived from HolyCode by CoderLuii and subsequently developed as an independent project. SkyScow begins a new release lineage: `v0.0.1` is the first SkyScow release, and no release history from the HolyCode lineage is carried forward.

## [0.0.1] - 2026-09-15

### Added

- Initial standalone SkyScow release: an agentic software-engineering harness built around OpenCode.
- Docker image bundling the shipped agent/command/skill configuration, 50+ dev tools, headless Chromium, and s6-overlay v3 process supervision.
- Startup configuration reconciliation (`bootstrap.sh`) with manifest-shipped config updates.
- Sleev CLI and gateway version selection and synchronization at startup.
- Model-aware context budget and tokenizer tooling.
- GHCR publish workflow on `v*` tags and a PR validation build with an `opencode --version` smoke test.
