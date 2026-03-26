"""Groq fallback provider for greybeard.

Routes simple tasks to Groq (free tier / low cost) before falling back
to the configured primary backend (Anthropic/OpenAI).

Task complexity heuristics:
  - "simple": short Q&A, formatting, summaries, <500 tokens expected output
  - "complex": code review, architecture decisions, multi-file analysis
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    pass

console = Console()

# Groq models sorted by preference (fast + cheap first)
GROQ_DEFAULT_MODEL = "llama-3.1-8b-instant"
GROQ_FALLBACK_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Keywords that signal complex tasks (=> route to primary)
COMPLEX_SIGNALS = [
    "architecture",
    "security",
    "self-check",
    "risk",
    "compliance",
    "slo",
    "adr",
    "design doc",
    "tradeoffs",
    "trade-offs",
]

# Max input chars we'll still consider "simple" (~2000 tokens)
SIMPLE_INPUT_MAX_CHARS = 8_000


def is_simple_task(
    mode: str,
    user_message: str,
    force_complex: bool = False,
) -> bool:
    """Heuristic: should this task go to Groq (True) or stay on primary (False)?"""
    if force_complex:
        return False

    # self-check mode always needs the primary model
    if mode == "self-check":
        return False

    # Long input => complex
    if len(user_message) > SIMPLE_INPUT_MAX_CHARS:
        return False

    # Complexity signal in mode name
    msg_lower = user_message.lower()
    for signal in COMPLEX_SIGNALS:
        if signal in msg_lower:
            return False

    # Mentor / coach on short input = simple enough for Groq
    return True


def run_groq(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    stream: bool = True,
    api_key: str | None = None,
) -> tuple[str, int, int]:
    """Call Groq API. Returns (response_text, input_tokens, output_tokens).

    Uses the OpenAI-compatible endpoint that Groq exposes.
    Raises RuntimeError on failure so the caller can fall back.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed; cannot use Groq fallback")

    groq_key = api_key or os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise RuntimeError("GROQ_API_KEY not set; cannot use Groq fallback")

    chosen_model = model or GROQ_DEFAULT_MODEL
    client = OpenAI(api_key=groq_key, base_url=GROQ_BASE_URL)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        if stream:
            full_text = ""
            console.print()
            resp = client.chat.completions.create(
                model=chosen_model,
                messages=messages,  # type: ignore[arg-type]
                stream=True,
            )
            for chunk in resp:  # type: ignore[union-attr]
                delta = chunk.choices[0].delta.content or ""  # type: ignore[union-attr]
                print(delta, end="", flush=True)
                full_text += delta
            console.print("\n")
            # Groq doesn't return token counts in streaming mode; estimate
            input_tokens = len(system_prompt.split()) + len(user_message.split())
            output_tokens = len(full_text.split())
            return full_text, input_tokens, output_tokens
        else:
            resp = client.chat.completions.create(
                model=chosen_model,
                messages=messages,  # type: ignore[arg-type]
                stream=False,
            )
            text = resp.choices[0].message.content or ""
            usage = resp.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            return text, input_tokens, output_tokens

    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Groq API error: {exc}") from exc


class GroqConfig:
    """Groq settings, resolved from env + config dict."""

    def __init__(self, cfg: dict | None = None) -> None:
        cfg = cfg or {}
        self.enabled: bool = cfg.get("enabled", True)
        self.use_for_simple_tasks: bool = cfg.get("use_for_simple_tasks", True)
        self.model: str = cfg.get("model", GROQ_DEFAULT_MODEL)
        self.api_key: str = cfg.get("api_key", "") or os.getenv("GROQ_API_KEY", "")

    @property
    def available(self) -> bool:
        return self.enabled and bool(self.api_key)
