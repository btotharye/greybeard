"""Tests for configuration management."""

from __future__ import annotations

import yaml

from greybeard.config import (
    DEFAULT_MODELS,
    GreybeardConfig,
    LLMConfig,
)


class TestLLMConfig:
    def test_default_values(self):
        llm = LLMConfig()
        assert llm.backend == "openai"
        assert llm.model == ""
        assert llm.base_url == ""

    def test_resolved_model_uses_default_when_empty(self):
        llm = LLMConfig(backend="openai", model="")
        assert llm.resolved_model() == DEFAULT_MODELS["openai"]

    def test_resolved_model_uses_explicit_model(self):
        llm = LLMConfig(backend="openai", model="gpt-4o-mini")
        assert llm.resolved_model() == "gpt-4o-mini"

    def test_resolved_base_url_for_ollama(self):
        llm = LLMConfig(backend="ollama")
        assert "localhost" in llm.resolved_base_url()

    def test_resolved_base_url_custom(self):
        llm = LLMConfig(backend="ollama", base_url="http://myhost:11434/v1")
        assert llm.resolved_base_url() == "http://myhost:11434/v1"

    def test_resolved_base_url_none_for_openai(self):
        llm = LLMConfig(backend="openai")
        assert llm.resolved_base_url() is None

    def test_resolved_api_key_reads_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        llm = LLMConfig(backend="openai")
        assert llm.resolved_api_key() == "sk-test-123"

    def test_resolved_api_key_no_key_for_ollama(self):
        llm = LLMConfig(backend="ollama")
        assert llm.resolved_api_key() == "no-key-needed"


class TestGreybeardConfig:
    def test_default_values(self):
        cfg = GreybeardConfig()
        assert cfg.default_pack == "staff-core"
        assert cfg.default_mode == "review"
        assert cfg.llm.backend == "openai"

    def test_load_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        # Patch CONFIG_FILE to a non-existent path
        monkeypatch.setattr("greybeard.config.CONFIG_FILE", tmp_path / "nonexistent.yaml")
        cfg = GreybeardConfig.load()
        assert cfg.default_pack == "staff-core"
        assert cfg.llm.backend == "openai"

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("greybeard.config.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("greybeard.config.CONFIG_FILE", tmp_path / "config.yaml")

        cfg = GreybeardConfig()
        cfg.default_pack = "oncall-future-you"
        cfg.llm.backend = "anthropic"
        cfg.llm.model = "claude-3-5-sonnet-20241022"
        cfg.save()

        loaded = GreybeardConfig.load()
        assert loaded.default_pack == "oncall-future-you"
        assert loaded.llm.backend == "anthropic"
        assert loaded.llm.model == "claude-3-5-sonnet-20241022"

    def test_save_strips_empty_llm_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr("greybeard.config.CONFIG_DIR", tmp_path)
        config_file = tmp_path / "config.yaml"
        monkeypatch.setattr("greybeard.config.CONFIG_FILE", config_file)

        cfg = GreybeardConfig()
        cfg.llm.backend = "openai"
        cfg.llm.model = ""
        cfg.save()

        raw = yaml.safe_load(config_file.read_text())
        assert "model" not in raw.get("llm", {})

    def test_load_from_yaml(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "default_pack": "mentor-mode",
                    "default_mode": "mentor",
                    "llm": {
                        "backend": "ollama",
                        "model": "llama3.2",
                        "base_url": "http://localhost:11434/v1",
                    },
                }
            )
        )
        monkeypatch.setattr("greybeard.config.CONFIG_FILE", config_file)

        cfg = GreybeardConfig.load()
        assert cfg.default_pack == "mentor-mode"
        assert cfg.llm.backend == "ollama"
        assert cfg.llm.model == "llama3.2"
        assert "localhost" in cfg.llm.base_url

    def test_to_display_dict(self):
        cfg = GreybeardConfig()
        d = cfg.to_display_dict()
        assert "default_pack" in d
        assert "llm.backend" in d
        assert "llm.model" in d
