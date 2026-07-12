---
description: Verify AFT code search, set up SLEEV gateway, and install Ralph-RLM project wiring
agent: build
---
Walk through HolyCode's three bundled AI tools, verifying or setting up each one. Stop and ask for user input when interactive steps are needed.

## 1. AFT (Code Search)

AFT (@cortexkit/aft-opencode) is already installed as an OpenCode plugin and globally available. Verify it works:

- Run `aft_inspect` to confirm the AFT daemon is running and producing diagnostics.
- Run `aft_search` with a simple query (e.g. "README") to confirm semantic code search works.
- If either fails, check that ONNX runtime is installed: `dpkg -l libonnxruntime1.21`.

Report status. If AFT is working, move on. If not, surface the error and ask the user before troubleshooting further.

## 2. SLEEV (Context Compression Gateway)

SLEEV is installed globally but may not have its gateway binary yet.

- Run `sleev status`. If the gateway is installed and running, report that and move on.
- If not installed, tell the user SLEEV needs a one-time sign-in. Run `sleev` to launch the setup TUI. Let the user complete sign-in interactively.
- After sign-in, run `sleev status` again to confirm the gateway is installed.
- The s6 service in /etc/s6-overlay/s6-rc.d/sleev/ will auto-start the gateway on next container boot. To start it now, run `s6-svc -u /etc/s6-overlay/s6-rc.d/sleev`.

## 3. Ralph-RLM (Self-Correcting Coding Loop)

Ralph-RLM (@doeixd/opencode-ralph-rlm) is installed globally but needs per-project wiring.

- Confirm the current working directory is the user's project (typically /workspace or a subdirectory). If unclear, ask.
- Run `opencode-ralph-rlm setup` in that directory. This creates .opencode/ plugin files and a provider entry for ralph-rlm/supervisor.
- If setup already ran (it skips existing managed files), report that and move on.
- Explain to the user that the provider auto-starts when they open OpenCode. To start it manually: `opencode-ralph-rlm serve`.
- Mention that they can verify with: `opencode-ralph-rlm doctor`.

## 4. Summary

Report what was checked and what state each tool is in. If anything needs manual follow-up, call it out clearly.
