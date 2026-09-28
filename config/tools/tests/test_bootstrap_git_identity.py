"""Regression coverage for git identity reconciliation in scripts/bootstrap.sh.

Contract: identity is reconciled from persisted Git state on every start. An
explicit ``GIT_USER_NAME``/``GIT_USER_EMAIL`` is authoritative; otherwise an
existing global value is preserved, and only a missing value is initialized to
the SkyScow default. ``user.name`` and ``user.email`` are independent fields.

These tests run the real ``configure_git_identity`` function extracted from the
script against an isolated ``HOME`` with a stubbed ``runuser``, then assert on
the observable global git config rather than re-implementing the logic.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parents[1]
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap.sh"
FUNCTION = "configure_git_identity"
DEFAULT_NAME = "SkyScow User"
DEFAULT_EMAIL = "noreply@skyscow.local"

# The script is a top-level reconciliation flow, so the function is extracted and
# executed directly. `runuser -u <user> -- <cmd>` is unwrapped to `<cmd>`: the
# test runs as the same user `git config --global` would target anyway.
_HARNESS_PREAMBLE = textwrap.dedent(
    """
    set -euo pipefail
    OC_USER="$(id -un)"
    log() { :; }
    runuser() { shift 3; "$@"; }
    """
)


def _function_source() -> str:
    lines = BOOTSTRAP.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(
        index
        for index, line in enumerate(lines)
        if line.startswith(f"{FUNCTION}()")
    )
    end = next(
        index for index in range(start + 1, len(lines)) if lines[index].startswith("}")
    )
    return "".join(lines[start : end + 1])


def _env(home: Path, **overrides: str) -> dict[str, str]:
    env = {
        "HOME": str(home),
        "PATH": os.environ["PATH"],
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    env.update(overrides)
    return env


def _home(tmp_path: Path) -> Path:
    # ``tmp_path / "home"`` is already taken by the suite's autouse HOME fixture.
    home = tmp_path / "git-home"
    home.mkdir(exist_ok=True)
    return home


def _git(home: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], env=_env(home), capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _set_identity(home: Path, name: str, email: str) -> None:
    _git(home, "config", "--global", "user.name", name)
    _git(home, "config", "--global", "user.email", email)


def _bootstrap(home: Path, **overrides: str) -> None:
    script = _HARNESS_PREAMBLE + _function_source() + f"\n{FUNCTION}\n"
    subprocess.run(
        ["bash", "-c", script],
        env=_env(home, **overrides),
        capture_output=True,
        text=True,
        check=True,
    )


def _identity(home: Path) -> tuple[str, str]:
    return (
        _git(home, "config", "--global", "--get", "user.name"),
        _git(home, "config", "--global", "--get", "user.email"),
    )


def test_fresh_state_initializes_skyscow_defaults(tmp_path):
    home = _home(tmp_path)

    _bootstrap(home)

    assert _identity(home) == (DEFAULT_NAME, DEFAULT_EMAIL)


def test_persisted_identity_is_preserved(tmp_path):
    home = _home(tmp_path)
    _set_identity(home, "Ada Lovelace", "ada@example.com")

    _bootstrap(home)

    assert _identity(home) == ("Ada Lovelace", "ada@example.com")


def test_explicit_overrides_beat_persisted_identity(tmp_path):
    home = _home(tmp_path)
    _set_identity(home, "Ada Lovelace", "ada@example.com")

    _bootstrap(home, GIT_USER_NAME="Grace Hopper", GIT_USER_EMAIL="grace@example.com")

    assert _identity(home) == ("Grace Hopper", "grace@example.com")


def test_partial_override_preserves_persisted_email(tmp_path):
    home = _home(tmp_path)
    _set_identity(home, "Ada Lovelace", "ada@example.com")

    _bootstrap(home, GIT_USER_NAME="Grace Hopper")

    assert _identity(home) == ("Grace Hopper", "ada@example.com")


def test_partial_override_preserves_persisted_name(tmp_path):
    home = _home(tmp_path)
    _set_identity(home, "Ada Lovelace", "ada@example.com")

    _bootstrap(home, GIT_USER_EMAIL="grace@example.com")

    assert _identity(home) == ("Ada Lovelace", "grace@example.com")


def test_repeated_bootstrap_is_idempotent(tmp_path):
    home = _home(tmp_path)
    _set_identity(home, "Ada Lovelace", "ada@example.com")

    _bootstrap(home)
    _bootstrap(home)
    _bootstrap(home, GIT_USER_NAME="Grace Hopper")
    _bootstrap(home, GIT_USER_NAME="Grace Hopper")

    assert _identity(home) == ("Grace Hopper", "ada@example.com")


def test_safe_directory_handling_is_unaffected(tmp_path):
    home = _home(tmp_path)
    _git(home, "config", "--global", "--add", "safe.directory", "/other")

    _bootstrap(home)
    _bootstrap(home)

    entries = _git(home, "config", "--global", "--get-all", "safe.directory").splitlines()
    assert entries.count("/workspace") == 1
    assert "/other" in entries
    assert _identity(home) == (DEFAULT_NAME, DEFAULT_EMAIL)
