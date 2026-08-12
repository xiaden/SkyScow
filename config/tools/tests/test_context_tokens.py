"""Regression tests: context_tokens retains its counting contract.

Proves the o200k / DS_V4_F_0731 counts, the weighting formula, verified
system-artifact preference, and cache/download fallback survive the refactor
to shared tokenizer helpers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.helpers import tokenizer_helpers as th
from common.tools import context_tokens


@pytest.fixture(scope="module")
def counts():
    """Deterministic reference counts from the real tokenizers."""
    try:
        o200k, deepseek = th.load_tokenizers()
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        pytest.skip(f"tokenizer unavailable: {exc}")
    source = (
        "def hello():\n"
        "    return 'world'\n"
        "\n"
        "\n"
        "def main():\n"
        "    print(hello())"  # no trailing newline -> tool slice matches exactly
    )
    return {
        "o200k": len(o200k.encode(source, disallowed_special=())),
        "DS_V4_F_0731": len(deepseek.encode(source, add_special_tokens=False).ids),
        "source": source,
    }


class TestCountsRetained:
    def test_reference_source_counts(self, counts):
        assert counts["o200k"] > 0 and counts["DS_V4_F_0731"] > 0

    def test_full_tool_returns_both_models(self, counts, tmp_path):
        path = tmp_path / "app.py"
        path.write_text(counts["source"])
        result = context_tokens.context_tokens(
            files=[{"path": str(path), "start_line": 1, "end_line": 6}],
            workspace_root=tmp_path,
        )
        assert set(result) == {"o200k", "DS_V4_F_0731"}
        assert result["o200k"]["source_tokens"] == counts["o200k"]
        assert result["DS_V4_F_0731"]["source_tokens"] == counts["DS_V4_F_0731"]
        # Single section, single file -> weight is exactly 1.0.
        assert result["o200k"]["weighted_tokens"] == counts["o200k"]
        assert result["DS_V4_F_0731"]["weighted_tokens"] == counts["DS_V4_F_0731"]

    def test_multi_range_weighting(self, counts, tmp_path):
        path = tmp_path / "app.py"
        path.write_text("line one\nline two\nline three\nline four\n")
        result = context_tokens.context_tokens(
            files=[
                {"path": str(path), "start_line": 1, "end_line": 2},
                {"path": str(path), "start_line": 3, "end_line": 4},
            ],
            workspace_root=tmp_path,
        )
        # Two sections, one file -> weight = 1.03.
        for model in ("o200k", "DS_V4_F_0731"):
            entry = result[model]
            assert entry["weighted_tokens"] == th.weighted_tokens(
                entry["source_tokens"], 2, 1
            )
            assert entry["weighted_tokens"] >= entry["source_tokens"]


class TestErrorContract:
    def test_empty_files_rejected(self, tmp_path):
        result = context_tokens.context_tokens(files=[], workspace_root=tmp_path)
        assert result["error"] == "invalid_files"

    def test_non_object_entry(self, tmp_path):
        result = context_tokens.context_tokens(
            files=["nope"], workspace_root=tmp_path
        )
        assert result["error"] == "invalid_file"

    def test_traversal_rejected(self, tmp_path):
        result = context_tokens.context_tokens(
            files=[{"path": "../evil.txt", "start_line": 1, "end_line": 1}],
            workspace_root=tmp_path,
        )
        assert result["error"] == "invalid_file"
        assert "outside workspace" in result["message"] or "File not found" in result["message"]

    def test_end_before_start(self, tmp_path):
        path = tmp_path / "a.txt"
        path.write_text("x\n")
        result = context_tokens.context_tokens(
            files=[{"path": str(path), "start_line": 5, "end_line": 2}],
            workspace_root=tmp_path,
        )
        assert result["error"] == "invalid_line_range"

    def test_range_exceeding_file(self, tmp_path):
        path = tmp_path / "a.txt"
        path.write_text("x\n")
        result = context_tokens.context_tokens(
            files=[{"path": str(path), "start_line": 1, "end_line": 99}],
            workspace_root=tmp_path,
        )
        assert result["error"] == "read_error"


class TestHelperReuse:
    """Both tools must consume the shared tokenizer-helper boundary."""

    def test_context_tokens_uses_shared_helpers(self):
        from common.tools import context_tokens as ct

        assert ct.assemble_sections is th.assemble_sections
        assert ct.weighted_tokens is th.weighted_tokens
        assert ct.load_tokenizers is th.load_tokenizers

    def test_context_budget_uses_shared_helpers(self):
        from common.tools import context_budget as cb

        assert cb.assemble_sections is th.assemble_sections
        assert cb.weighted_tokens is th.weighted_tokens
        assert cb.load_tokenizers is th.load_tokenizers
        assert cb.read_subsection is th.read_subsection

    def test_no_private_cross_tool_imports(self):
        """context_budget must not import private helpers from context_tokens."""
        from common.tools import context_budget as cb

        import inspect

        source = inspect.getsource(cb)
        assert "from ..tools.context_tokens import" not in source
        assert "context_tokens._" not in source


class TestVerifiedArtifactPreference:
    def test_system_artifact_is_verified(self):
        """The shipped system artifact must satisfy the pinned digest."""
        verified = th.verified_path(th.DEEPSEEK_TOKENIZER_PATH)
        assert verified is not None, "system tokenizer artifact is not verified"

    def test_resolve_prefers_verified_system_path(self, monkeypatch):
        """Regression: resolution prefers the verified system artifact."""
        monkeypatch.setattr(
            th, "verified_path", lambda p: p if p == th.DEEPSEEK_TOKENIZER_PATH else None
        )
        calls = []

        def _download():
            calls.append("download")
            return Path("/nonexistent/downloaded.json")

        monkeypatch.setattr(th, "download_tokenizer", _download)
        assert th.resolve_tokenizer_path() == th.DEEPSEEK_TOKENIZER_PATH
        assert calls == []

    def test_download_fallback_reused_from_verified_cache(self, monkeypatch, tmp_path):
        """Regression: a verified cache path is reused without re-downloading."""
        cache = tmp_path / "cache" / "tokenizer.json"
        cache.parent.mkdir(parents=True)
        cache.write_text("{}")
        monkeypatch.setattr(th, "DEEPSEEK_TOKENIZER_CACHE_PATH", cache)
        monkeypatch.setattr(
            th, "verified_path", lambda p: cache if p == cache else None
        )
        # If download is attempted, urlopen raises instead of fetching.
        def _explode(*args, **kwargs):
            raise AssertionError("verified cache must be reused without download")

        monkeypatch.setattr(th.urllib.request, "urlopen", _explode)
        assert th.download_tokenizer() == cache
