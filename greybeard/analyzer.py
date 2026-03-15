"""Core review engine — assembles context and calls the LLM.

Supports multiple backends via the greybeard config:
  - openai      (default, gpt-4o)
  - anthropic   (claude-3-5-sonnet)
  - ollama      (local, llama3.2 or any model)
  - lmstudio    (local OpenAI-compatible server)


All backends except anthropic are accessed via the OpenAI-compatible API.
Anthropic uses its own SDK.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from rich.console import Console

from .config import GreybeardConfig, LLMConfig
from .models import ReviewRequest
from .modes import build_system_prompt

console = Console()

MAX_INPUT_CHARS = 120_000  # ~30k tokens, warn above this


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_review(
    request: ReviewRequest,
    config: GreybeardConfig | None = None,
    model_override: str | None = None,
    stream: bool = True,
) -> str:
    """Run the review and return the full response text."""
    if config is None:
        config = GreybeardConfig.load()

    llm = config.llm
    model = model_override or llm.resolved_model()
    system_prompt = build_system_prompt(request.mode, request.pack, request.audience)
    user_message = _build_user_message(request)

    if llm.backend == "anthropic":
        return _run_anthropic(llm, model, system_prompt, user_message, stream=stream)
    else:
        return _run_openai_compat(llm, model, system_prompt, user_message, stream=stream)


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------


def _run_openai_compat(
    llm: LLMConfig,
    model: str,
    system_prompt: str,
    user_message: str,
    stream: bool = True,
) -> str:
    """Run via any OpenAI-compatible API (openai, ollama, lmstudio)."""
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: openai package not installed. Run: uv pip install openai", file=sys.stderr)
        sys.exit(1)

    api_key = llm.resolved_api_key()
    if not api_key and llm.backend not in ("ollama", "lmstudio"):
        env_var = llm.resolved_api_key_env()
        print(
            f"Error: {env_var} is not set.\n"
            f"Export it or add it to a .env file, or run: greybeard init",
            file=sys.stderr,
        )
        sys.exit(1)

    kwargs: dict = {"api_key": api_key or "no-key-needed"}
    base_url = llm.resolved_base_url()
    if base_url:
        kwargs["base_url"] = base_url

    client = OpenAI(**kwargs)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    if stream:
        return _stream_openai(client, model, messages)
    else:
        resp = client.chat.completions.create(model=model, messages=messages, stream=False)
        return resp.choices[0].message.content or ""


def _run_anthropic(
    llm: LLMConfig,
    model: str,
    system_prompt: str,
    user_message: str,
    stream: bool = True,
) -> str:
    """Run via Anthropic API."""
    try:
        import anthropic
    except ImportError:
        print(
            "Error: anthropic package not installed.\nRun: uv pip install anthropic",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = llm.resolved_api_key()
    if not api_key:
        print(
            f"Error: {llm.resolved_api_key_env()} is not set.\nExport it or run: greybeard init",
            file=sys.stderr,
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    if stream:
        full_text = ""
        with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as s:
            for text in s.text_stream:
                print(text, end="", flush=True)
                full_text += text
        print()
        return full_text
    else:
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return resp.content[0].text


def _stream_openai(client, model: str, messages: list) -> str:
    """Stream an OpenAI-compatible response."""
    full_text = ""
    console.print()  # Add spacing before output
    with client.chat.completions.create(model=model, messages=messages, stream=True) as s:
        for chunk in s:
            delta = chunk.choices[0].delta.content or ""
            print(delta, end="", flush=True)
            full_text += delta
    console.print("\n")  # Clean newline at end
    return full_text


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------


def _build_user_message(request: ReviewRequest) -> str:
    """Assemble everything the model needs to see into one user message."""
    parts: list[str] = []

    if request.context_notes:
        parts.append(f"## Context\n\n{request.context_notes}")

    if request.repo_path:
        repo_context = _collect_repo_context(request.repo_path)
        if repo_context:
            parts.append(f"## Repository Context\n\n{repo_context}")

    if request.input_text:
        label = "Input" if len(request.input_text) < 200 else "Input (diff / document)"
        parts.append(f"## {label}\n\n```\n{request.input_text}\n```")

    if not parts:
        parts.append(
            "No input was provided. Please describe what you'd like reviewed, "
            "or pipe in a git diff or design document."
        )

    combined = "\n\n".join(parts)

    if len(combined) > MAX_INPUT_CHARS:
        print(
            f"Warning: input is large (~{len(combined) // 4} tokens estimated). "
            "Consider trimming or using --repo with a focused diff.",
            file=sys.stderr,
        )

    return combined


def _collect_repo_context(repo_path: str) -> str:
    """Collect lightweight context from a repo: README, recent git log, dir tree."""
    path = Path(repo_path).resolve()
    if not path.exists():
        return ""

    parts: list[str] = []

    # README
    for name in ("README.md", "README.rst", "README.txt", "README"):
        readme = path / name
        if readme.is_file():
            content = readme.read_text(errors="replace")[:3000]
            parts.append(f"## README\n\n{content}")
            break

    # Recent git log
    try:
        log = subprocess.check_output(
            ["git", "log", "--oneline", "-20"],
            cwd=path,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        parts.append(f"## Recent Git History\n\n```\n{log.strip()}\n```")
    except subprocess.CalledProcessError:
        pass

    # Directory tree (depth 2, skip noise)
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
    tree_lines = []
    try:
        for item in sorted(path.iterdir()):
            if item.name.startswith(".") or item.name in skip_dirs:
                continue
            if item.is_dir():
                tree_lines.append(f"  {item.name}/")
                for sub in sorted(item.iterdir()):
                    if sub.name.startswith(".") or sub.name in skip_dirs:
                        continue
                    tree_lines.append(f"    {sub.name}{'/' if sub.is_dir() else ''}")
            else:
                tree_lines.append(f"  {item.name}")
        if tree_lines:
            tree_str = "\n".join(tree_lines)
            parts.append(f"## Directory Structure\n\n```\n{tree_str}\n```")
    except PermissionError:
        pass

    return "\n\n".join(parts)
