"""Tests for GitHub Copilot API backend."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from greybeard.backends.copilot import CopilotBackend


class TestCopilotBackendInit:
    """Test CopilotBackend initialization."""

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        backend = CopilotBackend(github_token="ghp_test123")
        assert backend.github_token == "ghp_test123"

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization reads from GITHUB_TOKEN env var."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env456")
        backend = CopilotBackend()
        assert backend.github_token == "ghp_env456"

    def test_init_with_default_model(self):
        """Test initialization with default model."""
        backend = CopilotBackend(github_token="ghp_test123")
        assert backend.default_model == "claude-3-5-sonnet-20241022"

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        backend = CopilotBackend(
            github_token="ghp_test123", default_model="claude-opus"
        )
        assert backend.default_model == "claude-3-opus-20250219"

    def test_init_no_token(self):
        """Test initialization without token."""
        backend = CopilotBackend()
        assert backend.github_token == ""


class TestCopilotBackendValidate:
    """Test credential validation."""

    def test_validate_credentials_success(self):
        """Test successful validation."""
        backend = CopilotBackend(github_token="ghp_test123")
        assert backend.validate_credentials() is True

    def test_validate_credentials_failure(self):
        """Test validation failure without token."""
        backend = CopilotBackend()
        assert backend.validate_credentials() is False


class TestCopilotBackendModelResolution:
    """Test model name resolution."""

    def test_resolve_claude_friendly_name(self):
        """Test resolving friendly Claude name."""
        backend = CopilotBackend(github_token="ghp_test123")
        resolved = backend._resolve_model("claude")
        assert resolved == "claude-3-5-sonnet-20241022"

    def test_resolve_claude_3_5_sonnet(self):
        """Test resolving claude-3.5-sonnet."""
        backend = CopilotBackend(github_token="ghp_test123")
        resolved = backend._resolve_model("claude-3.5-sonnet")
        assert resolved == "claude-3-5-sonnet-20241022"

    def test_resolve_claude_haiku(self):
        """Test resolving haiku."""
        backend = CopilotBackend(github_token="ghp_test123")
        resolved = backend._resolve_model("claude-3.5-haiku")
        assert resolved == "claude-3-5-haiku-20241022"

    def test_resolve_gpt4(self):
        """Test resolving gpt-4."""
        backend = CopilotBackend(github_token="ghp_test123")
        resolved = backend._resolve_model("gpt-4")
        assert resolved == "gpt-4"

    def test_resolve_gpt4o(self):
        """Test resolving gpt-4o."""
        backend = CopilotBackend(github_token="ghp_test123")
        resolved = backend._resolve_model("gpt-4o")
        assert resolved == "gpt-4o"

    def test_resolve_empty_model(self):
        """Test resolving empty model uses default."""
        backend = CopilotBackend(github_token="ghp_test123")
        resolved = backend._resolve_model("")
        assert resolved == "claude-3-5-sonnet-20241022"

    def test_resolve_full_model_id(self):
        """Test resolving full model ID directly."""
        backend = CopilotBackend(github_token="ghp_test123")
        resolved = backend._resolve_model("claude-3-5-sonnet-20241022")
        assert resolved == "claude-3-5-sonnet-20241022"

    def test_resolve_unknown_model(self):
        """Test unknown model name is passed through."""
        backend = CopilotBackend(github_token="ghp_test123")
        resolved = backend._resolve_model("custom-model-xyz")
        assert resolved == "custom-model-xyz"


class TestCopilotBackendCall:
    """Test non-streaming call."""

    @patch("openai.OpenAI")
    def test_call_success(self, mock_openai_class):
        """Test successful call."""
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock the response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_client.chat.completions.create.return_value = mock_response

        backend = CopilotBackend(github_token="ghp_test123")
        result = backend.call(
            system="Test system prompt",
            user_message="Test user message",
        )

        assert result.content == "Test response"
        assert result.model == "claude-3-5-sonnet-20241022"
        assert result.usage["input_tokens"] == 10
        assert result.usage["output_tokens"] == 5

        # Verify client was created with correct args
        mock_openai_class.assert_called_once_with(
            api_key="ghp_test123", base_url="https://api.githubcopilot.com/v1"
        )

    @patch("openai.OpenAI")
    def test_call_with_model_override(self, mock_openai_class):
        """Test call with model override."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_client.chat.completions.create.return_value = mock_response

        backend = CopilotBackend(github_token="ghp_test123")
        result = backend.call(
            system="Test system prompt",
            user_message="Test user message",
            model="gpt-4o",
        )

        assert result.model == "gpt-4o"

    def test_call_without_token_raises_error(self):
        """Test call without token raises RuntimeError."""
        backend = CopilotBackend()
        with pytest.raises(RuntimeError, match="GitHub token is not configured"):
            backend.call(
                system="Test system",
                user_message="Test message",
            )

    @patch("openai.OpenAI")
    def test_call_with_custom_temperature(self, mock_openai_class):
        """Test call with custom temperature."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = None
        mock_client.chat.completions.create.return_value = mock_response

        backend = CopilotBackend(github_token="ghp_test123")
        backend.call(
            system="Test system",
            user_message="Test message",
            temperature=1.5,
        )

        # Verify temperature was passed
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 1.5


class TestCopilotBackendStreamCall:
    """Test streaming call."""

    @patch("openai.OpenAI")
    def test_stream_call_success(self, mock_openai_class, capsys):
        """Test successful streaming call."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock streaming chunks
        mock_chunk1 = MagicMock()
        mock_chunk1.choices[0].delta.content = "Hello "

        mock_chunk2 = MagicMock()
        mock_chunk2.choices[0].delta.content = "world"

        mock_chunk3 = MagicMock()
        mock_chunk3.choices[0].delta.content = None

        mock_client.chat.completions.create.return_value.__enter__.return_value = [
            mock_chunk1,
            mock_chunk2,
            mock_chunk3,
        ]

        backend = CopilotBackend(github_token="ghp_test123")
        result = backend.stream_call(
            system="Test system",
            user_message="Test message",
        )

        assert result == "Hello world"

        # Verify streaming was enabled
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["stream"] is True

    def test_stream_call_without_token_raises_error(self):
        """Test stream call without token raises RuntimeError."""
        backend = CopilotBackend()
        with pytest.raises(RuntimeError, match="GitHub token is not configured"):
            backend.stream_call(
                system="Test system",
                user_message="Test message",
            )

    @patch("openai.OpenAI")
    def test_stream_call_with_model_override(self, mock_openai_class):
        """Test stream call with model override."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_chunk = MagicMock()
        mock_chunk.choices[0].delta.content = "Test"

        mock_client.chat.completions.create.return_value.__enter__.return_value = [
            mock_chunk
        ]

        backend = CopilotBackend(github_token="ghp_test123")
        backend.stream_call(
            system="Test system",
            user_message="Test message",
            model="claude-opus",
        )

        # Verify model was resolved and used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-opus-20250219"


class TestCopilotBackendInfo:
    """Test backend information methods."""

    def test_get_available_models(self):
        """Test listing available models."""
        backend = CopilotBackend(github_token="ghp_test123")
        models = backend.get_available_models()

        assert isinstance(models, list)
        assert "claude-3-5-sonnet-20241022" in models
        assert "gpt-4" in models
        assert len(models) > 0

    def test_get_model_info(self):
        """Test getting model information."""
        backend = CopilotBackend(github_token="ghp_test123")
        info = backend.get_model_info()

        assert info["name"] == "GitHub Copilot"
        assert info["base_url"] == "https://api.githubcopilot.com/v1"
        assert "auth_type" in info
        assert "available_models" in info
        assert "default_model" in info


class TestCopilotBackendIntegration:
    """Integration tests."""

    def test_backend_response_format(self):
        """Test BackendResponse data class."""
        from greybeard.backends.base import BackendResponse

        response = BackendResponse(
            content="Test content",
            model="claude-3-5-sonnet-20241022",
            usage={"input_tokens": 10, "output_tokens": 5},
        )

        assert response.content == "Test content"
        assert response.model == "claude-3-5-sonnet-20241022"
        assert response.usage["input_tokens"] == 10

    def test_backend_is_subclass_of_base(self):
        """Test CopilotBackend is a Backend."""
        from greybeard.backends.base import Backend

        assert issubclass(CopilotBackend, Backend)

    @patch("openai.OpenAI")
    def test_full_workflow_analyze_request(self, mock_openai_class):
        """Test full workflow with a realistic request."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "This is a good approach because...\n- Point 1\n- Point 2"
        )
        mock_response.usage.prompt_tokens = 150
        mock_response.usage.completion_tokens = 75
        mock_client.chat.completions.create.return_value = mock_response

        backend = CopilotBackend(github_token="ghp_test123")

        system_prompt = (
            "You are a staff-level reviewer. Provide constructive feedback."
        )
        user_message = (
            "Here's my approach to sharding the database:\n"
            "1. Add tenant_id to all tables\n"
            "2. Use routing layer..."
        )

        result = backend.call(
            system=system_prompt,
            user_message=user_message,
            temperature=0.7,
        )

        assert "good approach" in result.content.lower()
        assert result.usage["input_tokens"] == 150
        assert result.usage["output_tokens"] == 75
