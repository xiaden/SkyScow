# SkyScow

**One container. Every tool. Any provider.**

Agentic software-engineering harness built around the OpenCode AI coding agent with built-in web UI, 50+ dev tools, headless browser, and process supervision. Provider-agnostic — bring any API key.

[![GitHub Stars](https://img.shields.io/github/stars/xiaden/SkyScow?style=flat-square&logo=github)](https://github.com/xiaden/SkyScow)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://github.com/xiaden/SkyScow/blob/main/LICENSE)

## Quick Start

```yaml
services:
  skyscow:
    image: ghcr.io/xiaden/skyscow:latest
    container_name: skyscow
    restart: unless-stopped
    shm_size: 2g
    ports:
      - "127.0.0.1:4096:4096"   # local-only by default
    volumes:
      - ./data/opencode:/home/opencode
      - ./local-cache/opencode:/home/opencode/.cache/opencode
      - ./workspace:/workspace
    environment:
      - ANTHROPIC_API_KEY=your-key-here
    secrets:
      - github_token

secrets:
  github_token:
    file: ${GITHUB_TOKEN_FILE:-/dev/null}
```

```bash
docker compose up -d
# Open http://localhost:4096 (published on loopback only)
```

> The web UI is bound to the host's loopback interface by default. To expose it to other machines, publish a wider interface **and** set `OPENCODE_SERVER_PASSWORD` — an unauthenticated OpenCode server can execute code with your workspace and provider credentials.
>
> For GitHub CLI access, set `GITHUB_TOKEN_FILE=./secrets/github_token` in `.env`, create that file with a fine-grained token, and keep it out of the image and persistent OpenCode state. Compose mounts it read-only at `/run/secrets/github_token` for runtime use. The file is optional; omit the variable and file when GitHub access is not needed.


## What's Inside

**OpenCode AI Agent** — Built-in web UI on port 4096. Provider-agnostic. Bring any API key.

**Headless Browser** — Chromium + Xvfb + Playwright, pre-configured for screenshots, scraping, and browser automation.

**50+ Dev Tools** — Node.js 22, Python 3, git, ripgrep, fzf, bat, eza, lazygit, delta, gh CLI, pnpm, TypeScript, Prisma, and more.

**AI Coding Tools** — Sleev context compression gateway, AFT code search and analysis, Ralph-RLM self-correcting coding loop, and bun runtime.

**10+ AI Providers** — Anthropic, OpenAI, Gemini, Groq, AWS Bedrock, Azure OpenAI, Vertex AI, GitHub Models, Ollama, and any OpenAI-compatible endpoint.

**s6-overlay v3** — Process supervision with auto-restart and clean shutdown. No zombie processes.

**Persistent State** — One bind mount. Sessions, settings, MCP configs, plugins all survive rebuilds.

**Permissions** — UID/GID remapping via PUID/PGID. No credentials are baked into the image.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic Claude |
| `OPENAI_API_KEY` | OpenAI |
| `GEMINI_API_KEY` | Google Gemini |
| `GROQ_API_KEY` | Groq |
| `GITHUB_TOKEN_FILE` | Optional host path to a fine-grained GitHub token; mounted read-only at `/run/secrets/github_token` when set |
| `PUID` / `PGID` | Container user UID/GID (default: 1000) |
| `OPENCODE_SERVER_PASSWORD` | Protect web UI with basic auth |

## Links

- [GitHub](https://github.com/xiaden/SkyScow)
