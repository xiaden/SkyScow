"""Shared fixtures for the config/tools test suite.

The tools package root is ``config/tools`` (mirrored to
``~/.config/opencode/tools`` in the installed image); modules import as
``common.tools.*`` / ``common.helpers.*``. This conftest makes that import
style work from the repository layout.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]  # config/tools
FIXTURES = Path(__file__).resolve().parent / "fixtures"

if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Isolate HOME so tests never pick up a real user policy file."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("HOLYCODE_CONTEXT_BUDGET_POLICY", raising=False)
    monkeypatch.delenv("HOLYCODE_DEEPSEEK_TOKENIZER_PATH", raising=False)
    monkeypatch.delenv("HOLYCODE_DEEPSEEK_TOKENIZER_CACHE", raising=False)
    (tmp_path / "home").mkdir(exist_ok=True)


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


def build_workspace(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a workspace tree from relative-path -> content mappings."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return workspace


def copy_fixture(workspace: Path, fixture_name: str, dest_rel: str | None = None) -> Path:
    """Copy a fixture file into a workspace tree."""
    source = FIXTURES / fixture_name
    destination = workspace / (dest_rel or fixture_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return destination


@pytest.fixture
def workspace(tmp_path):
    """Empty workspace with the standard subdirectory layout."""
    return build_workspace(tmp_path, {})
