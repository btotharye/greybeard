"""GitHub Copilot API backend for greybeard.

The GitHub Copilot API (api.githubcopilot.com) provides access to Claude and GPT-4
models via GitHub authentication. This backend routes requests through Copilot's
unified API.

Documentation: https://github.com/features/copilot/api
"""

from __future__ import annotations

import os
import sys
from typing import Any

from .base import Backend, BackendResponse

# Client cache for connection pooling (saves ~100ms per request)
_copilot_client_cache: dict[str, Any] = {}


class CopilotBackend(Backend):
    """GitHub Copilot API backend.

    Routes requests to Claude or GPT-4 via api.githubcopilot.com.
    Requires a GitHub token for authentication.
    """

    # Copilot API endpoint
    BASE_URL = "https://api.githubcopilot.com/v1"

    # Map friendly names to Copilot model IDs
    MODEL_MAPPING = {
        # Claude 4.6 models (latest)
        "claude": "claude-sonnet-4-6",
        "claude-opus": "claude-opus-4-6",
        "claude-sonnet": "claude-sonnet-4-6",
        # Claude 3.5 models (legacy)
        "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
        "claude-3.5-haiku": "claude-3-5-haiku-20241022",
        "claude-3-opus": "claude-3-opus-20250219",
        # GPT models
        "gpt-4": "gpt-4",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
    }

    def __init__(self, github_token: str = "", default_model: str = "claude-sonnet"):
        """Initialize Copilot backend.

        Args:
            github_token: GitHub token for authentication. If empty, reads from
                GITHUB_TOKEN env var.
            default_model: Default model to use. Maps to Claude Sonnet 4.6 by default.
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.default_model = self._resolve_model(default_model)

    def _get_client(self) -> Any:
        """Get or create cached Copilot API client.

        Reuses OpenAI client instances to avoid recreating connections.
        Saves ~100ms per request when backend is used multiple times.

        Returns:
            OpenAI client instance
        """
        cache_key = f"{self.github_token}:{self.BASE_URL}"
        if cache_key not in _copilot_client_cache:
            try:
                from openai import OpenAI
            except ImportError:
                msg = "Error: openai package not installed. Run: uv pip install openai"
                print(msg, file=sys.stderr)
                sys.exit(1)

            _copilot_client_cache[cache_key] = OpenAI(
                api_key=self.github_token, base_url=self.BASE_URL
            )

        return _copilot_client_cache[cache_key]

    def call(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.7,
        model: str = "",
    ) -> BackendResponse:
        """Call GitHub Copilot API synchronously.

        Args:
            system: System prompt
            user_message: User message
            temperature: Temperature for generation (0.0-2.0)
            model: Optional model override

        Returns:
            BackendResponse with generated content

        Raises:
            RuntimeError: If GitHub token is not configured
            RuntimeError: If API call fails
        """
        if not self.validate_credentials():
            raise RuntimeError(
                "GitHub token is not configured. Set GITHUB_TOKEN env var "
                "or pass --github-token to the CLI."
            )

        model_id = self._resolve_model(model) if model else self.default_model
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]

        client = self._get_client()

        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
        )

        return BackendResponse(
            content=response.choices[0].message.content or "",
            model=model_id,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else None,
                "output_tokens": response.usage.completion_tokens if response.usage else None,
            },
        )

    def stream_call(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.7,
        model: str = "",
    ) -> str:
        """Call GitHub Copilot API with streaming.

        Args:
            system: System prompt
            user_message: User message
            temperature: Temperature for generation
            model: Optional model override

        Returns:
            Full response text (accumulated from stream)

        Raises:
            RuntimeError: If GitHub token is not configured
            RuntimeError: If API call fails
        """
        if not self.validate_credentials():
            raise RuntimeError(
                "GitHub token is not configured. Set GITHUB_TOKEN env var "
                "or pass --github-token to the CLI."
            )

        model_id = self._resolve_model(model) if model else self.default_model
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]

        client = self._get_client()

        full_response = ""
        with client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            stream=True,
        ) as stream:
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    # Yield to caller (for streaming display)
                    # This will be captured by the CLI
                    print(content, end="", flush=True)

        print()  # Newline after stream
        return full_response

    def validate_credentials(self) -> bool:
        """Validate that GitHub token is configured.

        Returns:
            True if token is set, False otherwise
        """
        return bool(self.github_token)

    def _resolve_model(self, model: str) -> str:
        """Resolve friendly model name to Copilot model ID.

        Args:
            model: Model name (friendly or full ID)

        Returns:
            Full Copilot model ID
        """
        if not model:
            return self.MODEL_MAPPING.get("claude-sonnet", "claude-sonnet-4-6")

        # Check if it's a known friendly name
        if model in self.MODEL_MAPPING:
            return self.MODEL_MAPPING[model]

        # Assume it's a full model ID
        return model

    def get_available_models(self) -> list[str]:
        """List available models.

        Returns:
            List of available model IDs
        """
        return list(self.MODEL_MAPPING.values())

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the backend and available models.

        Returns:
            Dictionary with backend info
        """
        return {
            "name": "GitHub Copilot",
            "base_url": self.BASE_URL,
            "auth_type": "GitHub token (GITHUB_TOKEN env var)",
            "available_models": self.get_available_models(),
            "default_model": self.default_model,
        }
