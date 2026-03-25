"""Base backend abstraction for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BackendResponse:
    """Response from a backend LLM call."""

    content: str
    """The generated text response."""

    model: str
    """The model used for generation."""

    usage: dict | None = None
    """Optional usage stats (tokens, etc)."""


class Backend(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    def call(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.7,
        model: str = "",
    ) -> BackendResponse:
        """Call the LLM synchronously.

        Args:
            system: System prompt
            user_message: User message
            temperature: Temperature for generation
            model: Optional model override

        Returns:
            BackendResponse with generated content
        """

    @abstractmethod
    def stream_call(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.7,
        model: str = "",
    ) -> str:
        """Call the LLM with streaming.

        Args:
            system: System prompt
            user_message: User message
            temperature: Temperature for generation
            model: Optional model override

        Returns:
            Full response text (accumulated from stream)
        """

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate that credentials are configured and valid.

        Returns:
            True if credentials are valid, False otherwise
        """
