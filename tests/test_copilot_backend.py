"""Tests for the GitHub Copilot LLM backend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from greybeard.backends.copilot import CopilotBackend, get_copilot_backend
from greybeard.config import GreybeardConfig, LLMConfig


class TestCopilotBackend:
    """Test CopilotBackend class initialization and properties."""

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        backend = CopilotBackend(github_token="test-token-123")
        assert backend.token == "test-token-123"
        assert backend.api_key == "test-token-123"

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization from environment variable."""
        monkeypatch.setenv("GITHUB_TOKEN", "env-token-456")
        backend = CopilotBackend()
        assert backend.token == "env-token-456"
        assert backend.api_key == "env-token-456"

    def test_init_missing_token_raises(self, monkeypatch):
        """Test that missing token raises ValueError."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(ValueError, match="GitHub token required"):
            CopilotBackend()

    def test_base_url_property(self):
        """Test base_url property."""
        assert CopilotBackend.base_url == "https://api.githubcopilot.com/v1"

    def test_api_key_env_property(self):
        """Test api_key_env property."""
        assert CopilotBackend.api_key_env == "GITHUB_TOKEN"

    def test_get_base_url_static_method(self):
        """Test static get_base_url method."""
        url = CopilotBackend.get_base_url()
        assert url == "https://api.githubcopilot.com/v1"

    def test_get_api_key_env_var_static_method(self):
        """Test static get_api_key_env_var method."""
        env_var = CopilotBackend.get_api_key_env_var()
        assert env_var == "GITHUB_TOKEN"


class TestGetCopilotBackendFactory:
    """Test get_copilot_backend factory function."""

    def test_factory_with_env_var(self, monkeypatch):
        """Test factory function with environment variable."""
        monkeypatch.setenv("GITHUB_TOKEN", "factory-token-789")
        config = LLMConfig(backend="copilot")
        backend = get_copilot_backend(config)

        assert isinstance(backend, CopilotBackend)
        assert backend.api_key == "factory-token-789"

    def test_factory_with_custom_env_var(self, monkeypatch):
        """Test factory with custom environment variable."""
        monkeypatch.setenv("CUSTOM_GITHUB_TOKEN", "custom-token-999")
        config = LLMConfig(backend="copilot", api_key_env="CUSTOM_GITHUB_TOKEN")
        backend = get_copilot_backend(config)

        assert backend.api_key == "custom-token-999"

    def test_factory_missing_token_raises(self, monkeypatch):
        """Test factory raises when token is missing."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        config = LLMConfig(backend="copilot")

        with pytest.raises(ValueError, match="GitHub token required"):
            get_copilot_backend(config)


class TestCopilotConfigIntegration:
    """Test Copilot backend integration with GreybeardConfig."""

    def test_copilot_in_known_backends(self):
        """Test that copilot is in KNOWN_BACKENDS."""
        from greybeard.config import KNOWN_BACKENDS

        assert "copilot" in KNOWN_BACKENDS

    def test_copilot_default_model(self):
        """Test default model for copilot backend."""
        from greybeard.config import DEFAULT_MODELS

        assert "copilot" in DEFAULT_MODELS
        assert DEFAULT_MODELS["copilot"] == "gpt-4-turbo"

    def test_copilot_api_key_env(self):
        """Test API key environment variable for copilot."""
        from greybeard.config import DEFAULT_API_KEY_ENVS

        assert "copilot" in DEFAULT_API_KEY_ENVS
        assert DEFAULT_API_KEY_ENVS["copilot"] == "GITHUB_TOKEN"

    def test_copilot_config_resolved_model(self):
        """Test resolved model for copilot config."""
        config = LLMConfig(backend="copilot")
        assert config.resolved_model() == "gpt-4-turbo"

    def test_copilot_config_base_url(self):
        """Test base URL resolution for copilot."""
        config = LLMConfig(backend="copilot")
        resolved_url = config.resolved_base_url()
        assert resolved_url is None  # copilot not in DEFAULT_BASE_URLS

    def test_copilot_config_api_key(self, monkeypatch):
        """Test API key resolution for copilot config."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
        config = LLMConfig(backend="copilot")
        assert config.resolved_api_key() == "test-github-token"

    def test_copilot_config_api_key_env_var(self):
        """Test API key environment variable name resolution."""
        config = LLMConfig(backend="copilot")
        assert config.resolved_api_key_env() == "GITHUB_TOKEN"

    def test_greybeard_config_load_with_copilot(self, tmp_path, monkeypatch):
        """Test loading GreybeardConfig with copilot backend."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token-xyz")
        config_dict = {
            "llm": {
                "backend": "copilot",
                "model": "gpt-4-turbo",
            }
        }
        cfg = GreybeardConfig.from_dict(config_dict)

        assert cfg.llm.backend == "copilot"
        assert cfg.llm.resolved_model() == "gpt-4-turbo"
        assert cfg.llm.resolved_api_key() == "test-token-xyz"


class TestCopilotRunReview:
    """Test _run_copilot function in analyzer.py."""

    def test_run_copilot_non_streaming(self, monkeypatch):
        """Test _run_copilot in non-streaming mode."""
        from greybeard.analyzer import _run_copilot

        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        # Mock OpenAI client
        with patch("openai.OpenAI") as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            # Mock response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "## Review Result\n\nLooks good!"
            mock_response.usage.prompt_tokens = 150
            mock_response.usage.completion_tokens = 75
            mock_client.chat.completions.create.return_value = mock_response

            llm = LLMConfig(backend="copilot")
            text, input_tokens, output_tokens = _run_copilot(
                llm,
                "gpt-4-turbo",
                "system prompt",
                "user message",
                stream=False,
            )

            assert text == "## Review Result\n\nLooks good!"
            assert input_tokens == 150
            assert output_tokens == 75

            # Verify the client was initialized correctly
            mock_openai_class.assert_called_once()
            call_kwargs = mock_openai_class.call_args[1]
            assert call_kwargs["api_key"] == "test-token"
            assert call_kwargs["base_url"] == "https://api.githubcopilot.com/v1"

    def test_run_copilot_streaming(self, monkeypatch, capsys):
        """Test _run_copilot in streaming mode."""
        from greybeard.analyzer import _run_copilot

        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        with patch("openai.OpenAI") as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            # Mock streaming response
            mock_chunk1 = MagicMock()
            mock_chunk1.choices = [MagicMock()]
            mock_chunk1.choices[0].delta.content = "Hello"

            mock_chunk2 = MagicMock()
            mock_chunk2.choices = [MagicMock()]
            mock_chunk2.choices[0].delta.content = " world"

            mock_stream = iter([mock_chunk1, mock_chunk2])
            mock_client.chat.completions.create.return_value = mock_stream

            llm = LLMConfig(backend="copilot")
            text, input_tokens, output_tokens = _run_copilot(
                llm,
                "gpt-4-turbo",
                "system prompt here",
                "user message here",
                stream=True,
            )

            assert text == "Hello world"
            assert input_tokens > 0
            assert output_tokens > 0

    def test_run_copilot_missing_api_key(self, monkeypatch):
        """Test _run_copilot raises SystemExit when token is missing."""
        from greybeard.analyzer import _run_copilot

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        llm = LLMConfig(backend="copilot")

        with pytest.raises(SystemExit):
            _run_copilot(llm, "gpt-4-turbo", "system", "user", stream=False)

    def test_run_copilot_uses_correct_base_url(self, monkeypatch):
        """Test that _run_copilot uses the correct GitHub Copilot API base URL."""
        from greybeard.analyzer import _run_copilot

        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        with patch("openai.OpenAI") as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "response"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            mock_client.chat.completions.create.return_value = mock_response

            llm = LLMConfig(backend="copilot")
            _run_copilot(llm, "gpt-4-turbo", "system", "user", stream=False)

            # Verify base_url is set correctly
            call_kwargs = mock_openai_class.call_args[1]
            assert call_kwargs["base_url"] == "https://api.githubcopilot.com/v1"


class TestCopilotRouting:
    """Test that Copilot backend is properly routed in run_review."""

    def test_run_review_routes_to_copilot(self, monkeypatch):
        """Test that run_review routes to _run_copilot for copilot backend."""
        from greybeard.analyzer import run_review
        from greybeard.models import ContentPack, ReviewRequest

        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        pack = ContentPack(name="test", perspective="Tester", tone="calm")
        request = ReviewRequest(mode="review", pack=pack, input_text="test diff")

        config = GreybeardConfig()
        config.llm.backend = "copilot"

        with patch("greybeard.analyzer._run_copilot") as mock_copilot:
            mock_copilot.return_value = ("response", 100, 50)
            result = run_review(request, config=config, stream=False)

        mock_copilot.assert_called_once()
        assert result == "response"

    def test_run_review_async_with_copilot(self, monkeypatch):
        """Test async run_review with copilot backend."""
        import asyncio

        from greybeard.analyzer import run_review_async
        from greybeard.models import ContentPack, ReviewRequest

        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        pack = ContentPack(name="test", perspective="Tester", tone="calm")
        request = ReviewRequest(mode="review", pack=pack, input_text="test diff")

        config = GreybeardConfig()
        config.llm.backend = "copilot"

        with patch("greybeard.analyzer._run_copilot") as mock_copilot:
            mock_copilot.return_value = ("async response", 100, 50)

            result = asyncio.run(run_review_async(request, config=config, stream=False))

        mock_copilot.assert_called_once()
        assert result == "async response"


class TestCopilotErrorHandling:
    """Test error handling for Copilot backend."""

    def test_copilot_with_custom_api_key_env(self, monkeypatch):
        """Test Copilot with custom API key environment variable."""
        from greybeard.analyzer import _run_copilot

        monkeypatch.setenv("MY_GH_TOKEN", "custom-token-123")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        with patch("openai.OpenAI") as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "result"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            mock_client.chat.completions.create.return_value = mock_response

            llm = LLMConfig(backend="copilot", api_key_env="MY_GH_TOKEN")
            text, _, _ = _run_copilot(llm, "gpt-4-turbo", "system", "user", stream=False)

            assert text == "result"
            call_kwargs = mock_openai_class.call_args[1]
            assert call_kwargs["api_key"] == "custom-token-123"

    def test_copilot_with_no_usage_info(self, monkeypatch):
        """Test Copilot handles response without usage info gracefully."""
        from greybeard.analyzer import _run_copilot

        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        with patch("openai.OpenAI") as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "result"
            mock_response.usage = None  # No usage info
            mock_client.chat.completions.create.return_value = mock_response

            llm = LLMConfig(backend="copilot")
            text, input_tokens, output_tokens = _run_copilot(
                llm, "gpt-4-turbo", "system", "user", stream=False
            )

            assert text == "result"
            assert input_tokens == 0  # Defaults to 0 when no usage
            assert output_tokens == 0


class TestCopilotModelSelection:
    """Test model selection for Copilot backend."""

    def test_copilot_with_custom_model(self, monkeypatch):
        """Test Copilot with custom model override."""
        from greybeard.analyzer import _run_copilot

        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        with patch("openai.OpenAI") as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "result"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            mock_client.chat.completions.create.return_value = mock_response

            llm = LLMConfig(backend="copilot")
            _run_copilot(llm, "gpt-4o", "system", "user", stream=False)

            # Verify custom model was passed
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]["model"] == "gpt-4o"

    def test_copilot_default_model_from_config(self):
        """Test Copilot uses default model from config."""
        config = LLMConfig(backend="copilot", model="")
        assert config.resolved_model() == "gpt-4-turbo"

    def test_copilot_custom_model_from_config(self):
        """Test Copilot can override default model."""
        config = LLMConfig(backend="copilot", model="gpt-4o")
        assert config.resolved_model() == "gpt-4o"
