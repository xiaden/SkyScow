"""Contract: the container healthcheck survives enabled OpenCode authentication.

Issue #35: the healthcheck probed ``curl -sf http://localhost:4096/``, which
OpenCode answers with 401 as soon as ``OPENCODE_SERVER_PASSWORD`` is set, so a
healthy container was reported unhealthy.

Verified against the OpenCode version this image ships (``OPENCODE_VERSION`` in
the Dockerfile, 1.18.31 at the time of writing): unauthenticated requests return
401 for every route including ``/``; an authenticated ``GET /global/health``
returns ``{"healthy": true, "version": "1.18.31"}``.

These tests extract the real ``HEALTHCHECK`` command from the Dockerfile and run
it with a stub ``curl`` that records its arguments, so the contract is checked
against the shipped command rather than a reimplementation of it.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parents[1]
DOCKERFILE = REPO_ROOT / "Dockerfile"

HEALTH_ENDPOINT = "/global/health"
DEFAULT_USERNAME = "opencode"
HEALTH_URL = f"http://localhost:4096{HEALTH_ENDPOINT}"

_STUB_CURL = """#!/bin/sh
printf '%s\\n' "$@" > "$CURL_ARGS_FILE"
exit "${CURL_EXIT_CODE:-0}"
"""


def _dockerfile_text() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _healthcheck_command() -> str:
    """Return the shell command of the Dockerfile HEALTHCHECK instruction."""
    lines = _dockerfile_text().splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith("HEALTHCHECK")
    )
    collected: list[str] = []
    for line in lines[start:]:
        collected.append(line.rstrip().rstrip("\\").strip())
        if not line.rstrip().endswith("\\"):
            break
    joined = " ".join(part for part in collected if part)
    return joined.split("CMD ", 1)[1]


def _pinned_opencode_version() -> str:
    match = re.search(
        r"^ARG OPENCODE_VERSION=(\S+)$", _dockerfile_text(), flags=re.MULTILINE
    )
    assert match, "Dockerfile must pin ARG OPENCODE_VERSION"
    return match.group(1)


def _run_healthcheck(
    tmp_path: Path, **env_overrides: str
) -> tuple[int, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "curl"
    stub.write_text(_STUB_CURL, encoding="utf-8")
    stub.chmod(0o755)

    args_file = tmp_path / "curl-args"
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "CURL_ARGS_FILE": str(args_file),
    }
    env.update(env_overrides)

    result = subprocess.run(
        ["/bin/sh", "-c", _healthcheck_command()],
        env=env,
        capture_output=True,
        text=True,
    )
    recorded = args_file.read_text(encoding="utf-8").splitlines() if args_file.exists() else []
    return result.returncode, recorded


def _user_argument(args: list[str]) -> str | None:
    for index, arg in enumerate(args):
        if arg in {"--user", "-u"} and index + 1 < len(args):
            return args[index + 1]
    return None


def test_healthcheck_targets_the_health_endpoint():
    args_command = _healthcheck_command()
    assert HEALTH_ENDPOINT in args_command
    assert f"http://localhost:4096/" not in args_command.replace(HEALTH_URL, "")
    assert re.search(r"curl\s+-fsS", args_command), "probe must fail on HTTP errors"


def test_without_password_the_probe_sends_no_credentials(tmp_path):
    code, args = _run_healthcheck(tmp_path)

    assert code == 0
    assert _user_argument(args) is None
    assert HEALTH_URL in args


def test_with_password_the_probe_sends_basic_auth(tmp_path):
    code, args = _run_healthcheck(
        tmp_path, OPENCODE_SERVER_PASSWORD="s3cret"
    )

    assert code == 0
    assert _user_argument(args) == f"{DEFAULT_USERNAME}:s3cret"
    assert HEALTH_URL in args


def test_custom_username_is_respected(tmp_path):
    code, args = _run_healthcheck(
        tmp_path, OPENCODE_SERVER_PASSWORD="s3cret", OPENCODE_SERVER_USERNAME="operator"
    )

    assert code == 0
    assert _user_argument(args) == "operator:s3cret"


def test_absent_username_uses_the_supported_default(tmp_path):
    code, args = _run_healthcheck(tmp_path, OPENCODE_SERVER_PASSWORD="s3cret")

    assert code == 0
    assert _user_argument(args).split(":", 1)[0] == DEFAULT_USERNAME


def test_authentication_is_not_bypassed(tmp_path):
    command = _healthcheck_command()
    lowered = command.lower()

    # No auth-disabling flags, no credential scrubbing, and the probe still fails
    # closed: curl keeps -f/--fail so an authentication error is a health failure.
    assert "--no-auth" not in lowered
    assert "no-auth" not in lowered
    assert "unset" not in lowered
    assert "OPENCODE_SERVER_PASSWORD" in command

    code, _args = _run_healthcheck(tmp_path, CURL_EXIT_CODE="22")
    assert code != 0, "a failing curl must fail the healthcheck"

    dockerfile = _dockerfile_text()
    assert "OPENCODE_SERVER_PASSWORD=" not in dockerfile.replace(
        "${OPENCODE_SERVER_PASSWORD:-}", ""
    )


def test_health_endpoint_matches_the_shipped_opencode_version():
    pinned = _pinned_opencode_version()
    binary = shutil.which("opencode")

    if binary is None:
        pytest.skip("opencode is not installed in this environment")
    reported = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    assert reported == pinned, (
        f"Dockerfile pins {pinned} but the installed opencode reports {reported}; "
        f"re-verify that {HEALTH_ENDPOINT} is still the health route"
    )


def test_live_server_enforces_auth_on_the_health_endpoint():
    """Probe the shipped server when one is reachable (CI has none)."""
    password = os.environ.get("OPENCODE_SERVER_PASSWORD", "")
    if not password or shutil.which("curl") is None:
        pytest.skip("no live password-protected OpenCode server in this environment")

    def probe(user: str | None) -> tuple[int, str]:
        argv = [
            "curl", "-sS", "-m", "5", "-o", "/dev/null", "-w", "%{http_code}",
        ]
        if user is not None:
            argv += ["--user", f"{user}:{password}"]
        argv.append(HEALTH_URL)
        result = subprocess.run(argv, capture_output=True, text=True)
        return result.returncode, result.stdout.strip()

    _anon_code, anonymous = probe(None)
    assert anonymous == "401", "the health endpoint must not be auth-exempt"

    username = os.environ.get("OPENCODE_SERVER_USERNAME", DEFAULT_USERNAME)
    authed_code, authed = probe(username)
    assert authed_code == 0 and authed == "200"

    body = json.loads(
        subprocess.run(
            ["curl", "-sS", "-m", "5", "--user", f"{username}:{password}", HEALTH_URL],
            capture_output=True,
            text=True,
        ).stdout
    )
    assert body["healthy"] is True
    assert body["version"] == _pinned_opencode_version()
