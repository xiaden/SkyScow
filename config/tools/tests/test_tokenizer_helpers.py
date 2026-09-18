"""Tests for the shared tokenizer helper boundary."""

from __future__ import annotations

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


class TestResolution:
    def test_returns_existing_shipped_artifact(self, monkeypatch, tmp_path):
        tokenizer = tmp_path / "tokenizer.json"
        tokenizer.write_text("{}")
        monkeypatch.setattr(th, "DEEPSEEK_TOKENIZER_PATH", tokenizer)
        assert th.resolve_tokenizer_path() == tokenizer

    def test_fails_when_shipped_artifact_is_missing(self, monkeypatch, tmp_path):
        tokenizer = tmp_path / "missing-tokenizer.json"
        monkeypatch.setattr(th, "DEEPSEEK_TOKENIZER_PATH", tokenizer)
        with pytest.raises(FileNotFoundError, match="tokenizer is missing"):
            th.resolve_tokenizer_path()


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
