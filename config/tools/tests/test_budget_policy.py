"""Tests for policy loading and safe model-to-tokenizer selection."""

from __future__ import annotations

import pytest

from common.helpers import budget_policy as bp
from common.helpers.budget_policy import (
    DEFAULT_MODEL,
    DEFAULT_POLICY,
    frontmatter_model,
    load_policy,
    select_tokenizer_model,
)
from tests.conftest import build_workspace, copy_fixture


class TestLoadPolicy:
    def test_defaults_when_absent(self, workspace):
        policy, diagnostics = load_policy(workspace)
        assert policy == DEFAULT_POLICY
        assert diagnostics["source"] == "defaults"
        assert diagnostics["warnings"]

    def test_workspace_shipped_file_wins(self, workspace, fixtures):
        copy_fixture(workspace, "policy/valid.yaml", "config/agent-context-budgets.yaml")
        policy, diagnostics = load_policy(workspace)
        assert policy["worker_phase_limit"] == 48000
        assert policy["manager_operational_limit"] == 96000
        assert policy["physical_limit"] == 128000
        assert policy["correction_multiplier"] == 3
        assert policy["model"] == "DS_V4_F_0731"
        assert diagnostics["source"] == "workspace"
        assert diagnostics["warnings"] == []

    def test_partial_file_merges_defaults(self, workspace, fixtures):
        copy_fixture(workspace, "policy/partial.yaml", "config/agent-context-budgets.yaml")
        policy, _ = load_policy(workspace)
        assert policy["worker_phase_limit"] == 5000
        assert policy["manager_operational_limit"] == DEFAULT_POLICY["manager_operational_limit"]
        assert policy["correction_multiplier"] == DEFAULT_POLICY["correction_multiplier"]

    def test_malformed_yaml_falls_back_to_defaults(self, workspace, fixtures):
        copy_fixture(workspace, "policy/malformed.yaml", "config/agent-context-budgets.yaml")
        policy, diagnostics = load_policy(workspace)
        assert policy == DEFAULT_POLICY
        assert diagnostics["source"] == "defaults"
        assert any("malformed" in w for w in diagnostics["warnings"])

    def test_non_mapping_yaml_falls_back(self, workspace, fixtures):
        copy_fixture(workspace, "policy/non_mapping.yaml", "config/agent-context-budgets.yaml")
        policy, diagnostics = load_policy(workspace)
        assert policy == DEFAULT_POLICY
        assert any("mapping" in w for w in diagnostics["warnings"])

    def test_invalid_values_are_rejected_individually(self, workspace):
        workspace = build_workspace(
            workspace.parent,
            {
                "config/agent-context-budgets.yaml": (
                    "worker_phase_limit: 0\n"
                    "physical_limit: -5\n"
                    "correction_multiplier: true\n"
                    "qa_return_tokens: 12000\n"
                    "model: DS_V4_F_0731\n"
                )
            },
        )
        policy, diagnostics = load_policy(workspace)
        assert policy["worker_phase_limit"] == DEFAULT_POLICY["worker_phase_limit"]
        assert policy["physical_limit"] == DEFAULT_POLICY["physical_limit"]
        assert policy["correction_multiplier"] == DEFAULT_POLICY["correction_multiplier"]
        assert policy["qa_return_tokens"] == 12000
        assert len(diagnostics["warnings"]) == 3

    def test_env_override_wins(self, workspace, fixtures, monkeypatch):
        override = copy_fixture(workspace, "policy/tiny.yaml", "config/override.yaml")
        monkeypatch.setenv("HOLYCODE_CONTEXT_BUDGET_POLICY", str(override))
        copy_fixture(workspace, "policy/valid.yaml", "config/agent-context-budgets.yaml")
        policy, diagnostics = load_policy(workspace)
        assert policy["worker_phase_limit"] == 10
        assert diagnostics["source"] == "env"

    def test_explicit_policy_path(self, workspace, fixtures):
        path = copy_fixture(workspace, "policy/tiny.yaml", "tiny.yaml")
        policy, diagnostics = load_policy(policy_path=path)
        assert policy["worker_phase_limit"] == 10
        assert diagnostics["source"] == str(path.resolve())

    def test_explicit_missing_path_raises(self, workspace):
        with pytest.raises(ValueError, match="not found"):
            load_policy(workspace, policy_path=workspace / "missing.yaml")

    def test_never_raises_for_malformed(self, workspace, fixtures):
        copy_fixture(workspace, "policy/malformed.yaml", "config/agent-context-budgets.yaml")
        policy, diagnostics = load_policy(workspace)
        assert policy == DEFAULT_POLICY


class TestFrontmatterModel:
    def test_known_model(self):
        content = "---\nmodel: omniroute/opencode-go/deepseek-v4-flash\n---\n# Body\n"
        assert frontmatter_model(content) == "omniroute/opencode-go/deepseek-v4-flash"

    def test_unknown_model_string_is_trusted_shape(self):
        content = "---\nmodel: some/unknown-model-9000\n---\n"
        assert frontmatter_model(content) == "some/unknown-model-9000"

    def test_missing_model_key(self):
        assert frontmatter_model("---\nname: Agent\n---\n") is None

    def test_no_frontmatter(self):
        assert frontmatter_model("# Just a heading\n") is None

    def test_unterminated_frontmatter(self):
        assert frontmatter_model("---\nmodel: x\n") is None

    def test_malformed_value_is_untrusted(self):
        # Quoted value with spaces -> not a safe identifier -> ignored.
        assert frontmatter_model('---\nmodel: "quoted value with spaces"\n---\n') is None

    def test_model_after_frontmatter_is_ignored(self):
        content = "---\nname: A\n---\n\nmodel: omniroute/opencode-go/deepseek-v4-flash\n"
        assert frontmatter_model(content) is None


class TestSelectTokenizerModel:
    def test_known_model_selects_its_tokenizer(self):
        assert (
            select_tokenizer_model(["omniroute/opencode-go/deepseek-v4-flash"])
            == "DS_V4_F_0731"
        )

    def test_missing_models_fall_back(self):
        assert select_tokenizer_model([]) == DEFAULT_MODEL
        assert select_tokenizer_model([None, None]) == DEFAULT_MODEL

    def test_unknown_models_fall_back(self):
        assert (
            select_tokenizer_model(["some/unknown-model-9000", "another/thing"])
            == DEFAULT_MODEL
        )

    def test_mixed_known_models_fall_back(self):
        # Two distinct allowlisted models cannot agree -> deterministic fallback.
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(bp, "MODEL_TOKENIZER_MAP", {"a": "DS_V4_F_0731", "b": "o200k"})
        try:
            assert select_tokenizer_model(["a", "b"]) == DEFAULT_MODEL
        finally:
            monkeypatch.undo()

    def test_known_plus_unknown_uses_known(self):
        # Unknown models do not vote; a single known model still selects.
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(bp, "MODEL_TOKENIZER_MAP", {"known": "DS_V4_F_0731"})
        try:
            assert select_tokenizer_model(["known", "unknown/thing"]) == "DS_V4_F_0731"
            assert select_tokenizer_model(["unknown/thing", "known"]) == "DS_V4_F_0731"
        finally:
            monkeypatch.undo()
