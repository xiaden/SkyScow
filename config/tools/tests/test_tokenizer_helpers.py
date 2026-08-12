"""Tests for the shared tokenizer helper boundary."""

from __future__ import annotations

import hashlib

import pytest

from common.helpers import tokenizer_helpers as th


class TestWeightedTokens:
    def test_single_section_single_file(self):
        # weight = 1 + 0.03*0 + 0.015*0 = 1.0
        assert th.weighted_tokens(100, 1, 1) == 100

    def test_multiple_sections(self):
        # weight = 1 + 0.03*2 + 0.015*0 = 1.06 -> ceil(106) for 100 tokens
        assert th.weighted_tokens(100, 3, 1) == 106

    def test_multiple_files(self):
        # weight = 1 + 0.03*3 + 0.015*3 = 1.135 -> ceil(113.5) for 100 tokens
        assert th.weighted_tokens(100, 4, 4) == 114

    def test_ceiling_behavior(self):
        # 10 * 1.03 = 10.3 -> ceil = 11
        assert th.weighted_tokens(10, 2, 1) == 11
        # 10 * 1.0 = 10 -> no rounding up
        assert th.weighted_tokens(10, 1, 1) == 10


class TestAssembleSections:
    def test_joins_with_blank_line(self):
        assert th.assemble_sections(["a", "b"]) == "a\n\nb"

    def test_single_section(self):
        assert th.assemble_sections(["only"]) == "only"


class TestReadSubsection:
    def test_reads_inclusive_range(self, tmp_path):
        path = tmp_path / "f.txt"
        path.write_text("one\ntwo\nthree\nfour\n")
        assert th.read_subsection(path, 2, 3) == "two\nthree"

    def test_strips_only_final_newline(self, tmp_path):
        path = tmp_path / "f.txt"
        path.write_text("a\n\nb\n")
        assert th.read_subsection(path, 1, 3) == "a\n\nb"

    def test_end_line_exceeds_length(self, tmp_path):
        path = tmp_path / "f.txt"
        path.write_text("one\n")
        with pytest.raises(ValueError, match="exceeds file length"):
            th.read_subsection(path, 1, 5)

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("")
        with pytest.raises(ValueError, match="File is empty"):
            th.read_subsection(path, 1, 1)


class TestSha256AndVerifiedPath:
    def test_sha256_matches_hashing(self, tmp_path):
        path = tmp_path / "blob.bin"
        path.write_bytes(b"hello world")
        assert th.sha256(path) == hashlib.sha256(b"hello world").hexdigest()

    def test_verified_path_accepts_matching_digest(self, tmp_path, monkeypatch):
        path = tmp_path / "tok.json"
        path.write_text("{}")
        monkeypatch.setattr(th, "sha256", lambda p: th.DEEPSEEK_TOKENIZER_SHA256)
        assert th.verified_path(path) == path

    def test_verified_path_rejects_mismatch(self, tmp_path, monkeypatch):
        path = tmp_path / "tok.json"
        path.write_text("{}")
        monkeypatch.setattr(th, "sha256", lambda p: "0" * 64)
        assert th.verified_path(path) is None

    def test_verified_path_missing(self, tmp_path):
        assert th.verified_path(tmp_path / "nope.json") is None

    def test_verified_path_rejects_directory(self, tmp_path):
        assert th.verified_path(tmp_path) is None


class TestResolutionOrder:
    def test_prefers_verified_system_artifact(self, monkeypatch):
        system = th.DEEPSEEK_TOKENIZER_PATH
        calls = []
        monkeypatch.setattr(th, "verified_path", lambda p: (calls.append(p) or system if p == th.DEEPSEEK_TOKENIZER_PATH else None))
        monkeypatch.setattr(th, "download_tokenizer", lambda: (_ for _ in ()).throw(AssertionError("must not download")))
        assert th.resolve_tokenizer_path() == system
        assert calls == [system]

    def test_falls_back_to_download_when_system_unverified(self, monkeypatch, tmp_path):
        downloaded = tmp_path / "downloaded.json"
        downloaded.write_text("{}")
        monkeypatch.setattr(th, "verified_path", lambda p: None)
        monkeypatch.setattr(th, "download_tokenizer", lambda: downloaded)
        assert th.resolve_tokenizer_path() == downloaded

    def test_download_reuses_verified_cache(self, monkeypatch, tmp_path):
        cache = tmp_path / "cache.json"
        cache.write_text("{}")
        monkeypatch.setattr(th, "DEEPSEEK_TOKENIZER_CACHE_PATH", cache)
        monkeypatch.setattr(
            th, "verified_path", lambda p: cache if p == cache else None
        )
        monkeypatch.setattr(
            th,
            "urllib",
            type("U", (), {"request": type("R", (), {"urlopen": lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not download"))})}),
        )
        assert th.download_tokenizer() == cache

    def test_download_verifies_before_replace(self, monkeypatch, tmp_path):
        cache = tmp_path / "cache.json"
        monkeypatch.setattr(th, "DEEPSEEK_TOKENIZER_CACHE_PATH", cache)
        # cache not verified, so a download happens; downloaded bytes fail hash
        monkeypatch.setattr(th, "verified_path", lambda p: None)
        monkeypatch.setattr(th, "sha256", lambda p: "0" * 64)

        class Response:
            def __init__(self):
                self._sent = False

            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                return False

            def read(self, size=None):
                # One chunk, then EOF — mirrors a real HTTP body stream.
                if not self._sent:
                    self._sent = True
                    return b"bad bytes"
                return b""

        monkeypatch.setattr(th.urllib.request, "urlopen", lambda *a, **k: Response())
        with pytest.raises(ValueError, match="SHA-256"):
            th.download_tokenizer()
        assert not cache.exists()


class TestLoadTokenizers:
    def test_loads_real_tokenizers(self):
        try:
            o200k, deepseek = th.load_tokenizers()
        except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
            pytest.skip(f"tokenizer unavailable: {exc}")
        assert o200k.name == "o200k_base"
        token_ids = deepseek.encode(
            "hello world", add_special_tokens=False
        ).ids
        assert isinstance(token_ids, list) and len(token_ids) > 0
