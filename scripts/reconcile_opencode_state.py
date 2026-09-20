#!/usr/bin/env python3
"""Reset generated OpenCode dependency state after a CLI upgrade.

SkyScow owns the generated package manifests and dependency trees used by
OpenCode. Configuration files and workspace plugin source remain untouched.
The database query intentionally targets the schema shipped by the pinned
OpenCode image; it is not a historical schema compatibility layer.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


SDK_PACKAGE = "@opencode-ai/plugin"
LOCKFILES = ("package-lock.json", "bun.lock", "bun.lockb")
VERSION_RE = re.compile(r"\b(\d+\.\d+\.\d+)\b")
EXPECTED_TABLES = ("project", "project_directory", "workspace")


def log(message: str) -> None:
    print(f"[bootstrap] {message}")


def warn(message: str) -> None:
    print(f"[bootstrap] WARNING: {message}", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--user", default="opencode")
    parser.add_argument("--check", action="store_true", help="report changes without deleting files")
    return parser.parse_args()


def installed_version() -> str | None:
    try:
        result = subprocess.run(
            ["opencode", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        warn(f"unable to determine installed OpenCode version: {exc}")
        return None

    match = VERSION_RE.search(result.stdout)
    if match is None:
        warn(f"unable to parse OpenCode version from: {result.stdout.strip()!r}")
        return None
    return match.group(1)


def database_path(home: Path) -> Path:
    configured = os.environ.get("OPENCODE_DB")
    if configured:
        return Path(configured).expanduser().resolve()
    environment = os.environ.copy()
    environment["HOME"] = str(home)
    environment["XDG_DATA_HOME"] = str(home / ".local" / "share")
    try:
        result = subprocess.run(
            ["opencode", "db", "path"],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        reported_path = result.stdout.strip().splitlines()[-1]
        if reported_path:
            return Path(reported_path).expanduser().resolve()
    except (IndexError, OSError, subprocess.CalledProcessError) as exc:
        warn(f"unable to resolve OpenCode database path from CLI: {exc}")
    return (home / ".local" / "share" / "opencode" / "opencode.db").resolve()


def path_present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def directory_has_entries(path: Path) -> bool:
    try:
        return any(path.iterdir())
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return False


def read_sdk_version(package_path: Path) -> str | None:
    if not package_path.is_file() or package_path.is_symlink():
        return None
    try:
        document = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict):
        return None
    dependencies = document.get("dependencies")
    if not isinstance(dependencies, dict):
        return None
    version = dependencies.get(SDK_PACKAGE)
    return version if isinstance(version, str) else None


def generated_state_needs_reset(base: Path, expected_version: str) -> bool:
    package_path = base / "package.json"
    modules_path = base / "node_modules"
    generated_paths = (package_path, modules_path, base / ".cache") + tuple(
        base / name for name in LOCKFILES
    )
    has_generated_state = any(path_present(path) for path in generated_paths)
    if not has_generated_state:
        return False
    if read_sdk_version(package_path) != expected_version:
        return True
    return not modules_path.is_dir() or modules_path.is_symlink()


def remove_path(path: Path, dry_run: bool) -> None:
    if not path_present(path):
        return
    if dry_run:
        log(f"would remove {path}")
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def clear_directory(path: Path, dry_run: bool) -> None:
    """Remove cache contents while retaining a possible bind-mount directory."""
    if path.is_symlink() or not path.is_dir():
        remove_path(path, dry_run)
        return
    try:
        children = tuple(path.iterdir())
    except OSError as exc:
        warn(f"unable to inspect cache {path}: {exc}")
        return
    for child in children:
        remove_path(child, dry_run)


def reset_generated_state(base: Path, dry_run: bool) -> None:
    remove_path(base / "package.json", dry_run)
    for lockfile in LOCKFILES:
        remove_path(base / lockfile, dry_run)
    remove_path(base / "node_modules", dry_run)
    remove_path(base / ".cache", dry_run)


def writable_by_user(path: Path, user: str) -> bool:
    try:
        result = subprocess.run(
            ["runuser", "-u", user, "--", "test", "-w", str(path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return result.returncode == 0


def workspace_config_path(directory: Path) -> Path | None:
    if not directory.is_absolute() or directory == Path("/"):
        return None
    try:
        if directory.is_symlink() or not directory.is_dir():
            return None
        config_dir = directory / ".opencode"
        if config_dir.is_symlink() or not config_dir.is_dir():
            return None
    except OSError:
        return None
    return config_dir


def collect_paths(connection: sqlite3.Connection) -> set[Path]:
    table_rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    tables = {row[0] for row in table_rows}
    missing = [table for table in EXPECTED_TABLES if table not in tables]
    if missing:
        raise LookupError(f"expected table(s) not found: {', '.join(missing)}")

    paths: set[Path] = set()
    for (value,) in connection.execute("SELECT worktree FROM project"):
        if isinstance(value, str) and value:
            paths.add(Path(value))

    for (value,) in connection.execute("SELECT sandboxes FROM project"):
        if not isinstance(value, str) or not value:
            continue
        try:
            sandboxes = json.loads(value)
        except json.JSONDecodeError:
            warn("ignored malformed project.sandboxes value")
            continue
        if isinstance(sandboxes, list):
            paths.update(Path(item) for item in sandboxes if isinstance(item, str) and item)
        elif isinstance(sandboxes, dict):
            paths.update(
                Path(item) for item in sandboxes.values() if isinstance(item, str) and item
            )

    for query in (
        "SELECT directory FROM project_directory",
        "SELECT directory FROM workspace",
    ):
        for (value,) in connection.execute(query):
            if isinstance(value, str) and value:
                paths.add(Path(value))
    return paths


def known_workspace_paths(database: Path) -> set[Path] | None:
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=1)
    except (OSError, sqlite3.Error) as exc:
        warn(f"unable to open OpenCode database {database}: {exc}")
        return None
    try:
        return collect_paths(connection)
    except (LookupError, sqlite3.Error) as exc:
        warn(
            f"OpenCode database schema is not ready ({exc}); "
            "workspace dependency state may remain stale until the next restart"
        )
        return None
    finally:
        connection.close()


def reconcile_workspace(directory: Path, expected_version: str, user: str, dry_run: bool) -> bool:
    config_dir = workspace_config_path(directory)
    if config_dir is None:
        return False
    if not generated_state_needs_reset(config_dir, expected_version):
        return False
    if not writable_by_user(config_dir, user):
        warn(f"skipping stale workspace state in non-writable {config_dir}")
        return False
    log(f"resetting stale workspace dependency state in {config_dir}")
    reset_generated_state(config_dir, dry_run)
    return True


def main() -> int:
    args = parse_args()
    version = installed_version()
    if version is None:
        return 0

    config_dir = args.home / ".config" / "opencode"
    cache_dir = args.home / ".cache" / "opencode"
    cache_reset = False
    if generated_state_needs_reset(config_dir, version):
        log(f"resetting stale global OpenCode dependency state for {version}")
        reset_generated_state(config_dir, args.check)
        cache_reset = True
    elif directory_has_entries(cache_dir) and read_sdk_version(config_dir / "package.json") is None:
        log("resetting untracked global OpenCode plugin cache")
        cache_reset = True

    database = database_path(args.home)
    if not database.exists():
        log("OpenCode database not found; skipping workspace dependency state")
        if cache_reset:
            log("clearing global OpenCode plugin cache")
            clear_directory(cache_dir, args.check)
        return 0

    paths = known_workspace_paths(database)
    if paths is None:
        if cache_reset:
            log("clearing global OpenCode plugin cache")
            clear_directory(cache_dir, args.check)
        return 0

    for directory in sorted(paths, key=lambda path: str(path)):
        if reconcile_workspace(directory, version, args.user, args.check):
            cache_reset = True

    if cache_reset:
        log("clearing global OpenCode plugin cache")
        clear_directory(cache_dir, args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
