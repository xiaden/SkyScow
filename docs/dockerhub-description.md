# HolyCode

**One container. Every tool. Any provider.**

OpenCode AI coding agent with built-in web UI, 50+ dev tools, headless browser, and process supervision. Provider-agnostic — bring any API key.

[![Docker Pulls](https://img.shields.io/docker/pulls/coderluii/holycode?style=flat-square&logo=docker)](https://hub.docker.com/r/coderluii/holycode)
[![GitHub Stars](https://img.shields.io/github/stars/coderluii/holycode?style=flat-square&logo=github)](https://github.com/CoderLuii/HolyCode)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://github.com/CoderLuii/HolyCode/blob/main/LICENSE)

## Quick Start

```yaml
services:
  holycode:
    image: coderluii/holycode:latest
    container_name: holycode
    restart: unless-stopped
    shm_size: 2g
    ports:
      - "4096:4096"
    volumes:
      - ./data/opencode:/home/opencode
      - ./local-cache/opencode:/home/opencode/.cache/opencode
      - ./workspace:/workspace
    environment:
      - ANTHROPIC_API_KEY=your-key-here
```

```bash
docker compose up -d
# Open http://localhost:4096
```


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
| `PUID` / `PGID` | Container user UID/GID (default: 1000) |
| `OPENCODE_SERVER_PASSWORD` | Protect web UI with basic auth |

## Links

- [GitHub](https://github.com/coderluii/holycode)
- [HolyCode Page](https://holycode.coderluii.dev)
- [Full Documentation](https://github.com/coderluii/holycode#readme)
- [Podman Guide](https://github.com/CoderLuii/HolyCode/blob/main/docs/podman.md)
