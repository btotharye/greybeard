"""GitHub Copilot LLM backend implementation.

Routes to api.githubcopilot.com/v1 using OpenAI-compatible API.
Requires GitHub authentication token (PAT or GitHub CLI token).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from greybeard.config import LLMConfig


class CopilotBackend:
    """GitHub Copilot backend for OpenAI-compatible API access.

    GitHub Copilot uses the OpenAI-compatible API endpoint at
    api.githubcopilot.com/v1. Authentication requires a GitHub token
    (personal access token or GitHub CLI token).

    Attributes:
        base_url: The GitHub Copilot API endpoint URL.
        api_key_env: Environment variable name for the GitHub token.
    """

    base_url = "https://api.githubcopilot.com/v1"
    api_key_env = "GITHUB_TOKEN"

    def __init__(self, github_token: str | None = None) -> None:
        """Initialize Copilot backend.

        Args:
            github_token: GitHub token. If not provided, reads from GITHUB_TOKEN env var.

        Raises:
            ValueError: If no token is provided and GITHUB_TOKEN env var is not set.
        """
        token = github_token or os.getenv(self.api_key_env)
        if not token:
            raise ValueError(
                f"GitHub token required. Set {self.api_key_env} env var or pass github_token."
            )
        self.token: str = token

    @property
    def api_key(self) -> str:
        """Get the API key (GitHub token)."""
        return self.token

    @staticmethod
    def get_api_key_env_var() -> str:
        """Get the environment variable name for API key."""
        return CopilotBackend.api_key_env

    @staticmethod
    def get_base_url() -> str:
        """Get the base URL for Copilot API."""
        return CopilotBackend.base_url


def get_copilot_backend(config: LLMConfig) -> CopilotBackend:
    """Factory function to create a Copilot backend from LLMConfig.

    Args:
        config: LLMConfig with optional api_key_env override.

    Returns:
        Initialized CopilotBackend instance.

    Raises:
        ValueError: If no GitHub token is available.
    """
    api_key_env = config.api_key_env or CopilotBackend.api_key_env
    token = os.getenv(api_key_env)
    if not token:
        raise ValueError(
            f"GitHub token required. Set {api_key_env} env var or configure it in greybeard."
        )
    return CopilotBackend(github_token=token)
