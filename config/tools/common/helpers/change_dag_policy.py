"""Canonical run-command policy for Change DAG ``run`` nodes.

``run.command`` is an argv array executed with ``shell=False``. This module is
the single canonical owner of the executable-plus-subcommand allowlist. Prefix
matching on the executable alone is insufficient: the first executable AND the
immediately following subcommand tokens must match an entry.

The policy is deliberately conservative. Shell metacharacters, shell
interpreters, VCS/publication/lifecycle tooling, and commands whose exact shape
is not on the allowlist are rejected.
"""
from __future__ import annotations

import os

__all__ = [
    "RUN_ALLOWLIST",
    "FORBIDDEN_FIRST_TOKENS",
    "FORBIDDEN_EXACT_TOKENS",
    "FORBIDDEN_SUBCOMMANDS",
    "SHELL_METACHARACTERS",
    "validate_run_command",
    "describe_allowlist",
]

# (executable, following-token prefix). A command is allowed only when its
# executable basename equals the first element and the tokens after the
# executable start with the prefix tuple. Each entry is a bounded
# implementation/verification/build/test command.
RUN_ALLOWLIST: list[tuple[str, tuple[str, ...]]] = [
    # --- Python test / verify modules (preferred over `python3 <script>`) ---
    ("python3", ("-m", "pytest")),        # run the pytest suite
    ("python3", ("-m", "compileall")),    # byte-compile for import errors
    ("python3", ("-m", "mypy")),          # static type check
    ("python3", ("-m", "ruff")),          # lint
    ("python3", ("-m", "flake8")),        # lint
    ("python3", ("-m", "black")),         # format check / apply
    ("python3", ("-m", "isort")),         # import sort check / apply
    # --- Direct Python verification executables ---
    ("pytest", ()),                       # test runner
    ("pyright", ()),                      # type checker
    ("mypy", ()),                         # type checker
    ("ruff", ()),                         # linter
    ("flake8", ()),                       # linter
    ("black", ()),                        # formatter
    ("isort", ()),                        # import sorter
    # --- JavaScript / TypeScript build+test (bounded subcommands) ---
    ("node", ("--test",)),                # node's built-in test runner only
    ("bun", ("test",)),                   # test runner
    ("bun", ("run",)),                    # run a package script (build/test)
    ("bun", ("install",)),                # dependency install (build step)
    ("bun", ("build",)),                  # build
    ("npm", ("test",)),                   # test script
    ("npm", ("run",)),                    # run a package script (build/test)
    ("npm", ("ci",)),                     # clean install (build step)
    ("tsc", ()),                          # TypeScript compiler / --noEmit
    # --- Systems languages ---
    ("cargo", ("test",)),                 # Rust tests
    ("cargo", ("check",)),                # Rust type/build check
    ("cargo", ("build",)),                # Rust build
    ("cargo", ("clippy",)),               # Rust lint
    ("cargo", ("fmt",)),                  # Rust format check
    ("go", ("test",)),                    # Go tests
    ("go", ("build",)),                   # Go build
    ("go", ("vet",)),                     # Go vet
    ("go", ("fmt",)),                     # Go format
    # --- Shell / config verification ---
    ("shellcheck", ()),                   # shell script lint
]

# Interpreters and launchers that can smuggle arbitrary commands or mutate the
# repository/publication lifecycle are never allowed as the first token.
FORBIDDEN_FIRST_TOKENS = {
    "git", "gh", "docker", "make", "sh", "bash", "zsh", "dash",
    "env", "eval", "exec", "xargs", "curl", "wget", "ssh", "scp",
}

# Publication / lifecycle vocabulary rejected only as *whole* tokens. Matching a
# bare substring would wrongly reject legitimate verification arguments such as
# ``tests/test_provider.py`` or ``src/prompts`` because they contain "pr".
FORBIDDEN_EXACT_TOKENS = frozenset(
    {"commit", "push", "publish", "deploy", "release", "tag"}
)

# Executable -> forbidden immediate subcommand. This is defense in depth: these
# executables are already rejected outright by ``FORBIDDEN_FIRST_TOKENS``, but
# the boundary is kept explicit so ``gh pr``/``git commit`` can never be admitted
# were the first-token rule ever relaxed.
FORBIDDEN_SUBCOMMANDS: dict[str, frozenset[str]] = {
    "gh": frozenset({"pr", "release", "repo", "workflow", "run", "api", "auth"}),
    "git": frozenset({"commit", "push", "tag", "release", "remote", "publish"}),
}

# Characters that would enable shell interpretation or control-sequence abuse.
SHELL_METACHARACTERS = frozenset(";|&$><`\n\r\x00")

_SHELL_EXECUTABLES = {"sh", "bash", "zsh", "dash"}

_ALLOWED_EXECUTABLES = {executable for executable, _ in RUN_ALLOWLIST}


def _executable_basename(token: str) -> str:
    """Return the basename of an executable token (handles POSIX and Windows)."""
    return os.path.basename(token.replace("\\", "/"))


def _forbidden_token(tokens: list[str]) -> str | None:
    for token in tokens:
        lowered = token.lower()
        if lowered in FORBIDDEN_EXACT_TOKENS:
            return lowered
    return None


def _forbidden_subcommand(tokens: list[str]) -> str | None:
    executable = _executable_basename(tokens[0])
    forbidden = FORBIDDEN_SUBCOMMANDS.get(executable)
    if forbidden and len(tokens) > 1 and tokens[1].lower() in forbidden:
        return f"{executable} {tokens[1]}"
    return None


def validate_run_command(command: list[str]) -> tuple[bool, str]:
    """Return ``(True, "")`` for an allowed argv command, else ``(False, reason)``."""
    if not isinstance(command, list):
        return False, "command must be a list (argv array), not a string"
    if not command:
        return False, "command must be a non-empty argv array"
    for part in command:
        if not isinstance(part, str):
            return False, "command entries must all be strings"
    if any(part == "" for part in command):
        return False, "command entries must be non-empty strings"

    executable = _executable_basename(command[0])
    if not executable:
        return False, "command executable must not be empty"
    if executable in FORBIDDEN_FIRST_TOKENS:
        return False, f"forbidden executable: {executable}"

    for token in command:
        if any(character in SHELL_METACHARACTERS for character in token):
            return False, f"token contains a shell metacharacter: {token!r}"

    if "-c" in command[1:] and executable in _SHELL_EXECUTABLES:
        return False, "shell '-c' invocation is not allowed"

    fragment = _forbidden_token(command)
    if fragment is not None:
        return False, f"forbidden publication/lifecycle token: {fragment!r}"

    subcommand = _forbidden_subcommand(command)
    if subcommand is not None:
        return False, f"forbidden publication/lifecycle subcommand: {subcommand!r}"

    if executable not in _ALLOWED_EXECUTABLES:
        return False, f"executable is not on the run allowlist: {executable}"

    following = command[1:]
    for allowed_executable, prefix in RUN_ALLOWLIST:
        if allowed_executable != executable:
            continue
        if tuple(following[: len(prefix)]) == prefix:
            return True, ""
    return False, f"subcommand is not on the run allowlist for: {executable}"


def describe_allowlist() -> list[str]:
    """Return human-readable descriptions of every allowlist entry."""
    lines: list[str] = []
    for executable, prefix in RUN_ALLOWLIST:
        if prefix:
            lines.append(f"{executable} {' '.join(prefix)} ...")
        else:
            lines.append(f"{executable} ...")
    return lines
