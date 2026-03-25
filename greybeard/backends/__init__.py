"""Greybeard backend implementations.

Backends provide LLM access for different providers.
Currently supported:
  - openai (via OpenAI-compatible API)
  - anthropic (via Anthropic SDK)
  - ollama (local, OpenAI-compatible)
  - lmstudio (local, OpenAI-compatible)
  - copilot (GitHub Copilot API, routes to claude/gpt-4)
"""

from .base import Backend, BackendResponse
from .copilot import CopilotBackend

__all__ = ["Backend", "BackendResponse", "CopilotBackend"]
