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

import asyncio
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from .config import GreybeardConfig, LLMConfig
from .groq_fallback import is_simple_task, run_groq
from .models import ReviewRequest
from .modes import build_system_prompt

# Token logging (best-effort — never crash the CLI if it fails)
try:
    import os as _os
    import sys as _sys

    _modules_path = _os.environ.get("OPENCLAW_MODULES_PATH") or str(
        Path.home() / ".openclaw" / "workspace" / "modules"
    )
    if _modules_path not in _sys.path:
        _sys.path.insert(0, _modules_path)
    from token_logger import log_usage as _log_usage
except Exception:

    def _log_usage(**kwargs) -> None:  # type: ignore[misc]
        pass


console = Console()

MAX_INPUT_CHARS = 120_000  # ~30k tokens, warn above this


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def run_review(
    request: ReviewRequest,
    config: GreybeardConfig | dict | None = None,
    model_override: str | None = None,
    stream: bool = True,
    use_groq: bool | None = None,
) -> str:
    """Run the review and return the full response text.

    Args:
        request: The ReviewRequest with mode, pack, and content.
        config: GreybeardConfig object, dict, or None (loads from file).
                When dict is passed, it's converted to GreybeardConfig.
        model_override: Override the configured model.
        stream: Whether to stream the response (default True).
        use_groq: Force Groq (True), skip (False), or auto-detect (None).

    Returns:
        The full review response text.

    If use_groq is None (default), auto-detect based on task complexity + config.
    If use_groq is True, force Groq. If False, skip Groq entirely.
    """
    if config is None:
        config = GreybeardConfig.load()
    elif isinstance(config, dict):
        config = GreybeardConfig.from_dict(config)

    llm = config.llm
    model = model_override or llm.resolved_model()
    system_prompt = build_system_prompt(request.mode, request.pack, request.audience)
    user_message = _build_user_message(request)

    groq_cfg = config.groq
    # Determine whether to attempt Groq
    should_try_groq = False
    if use_groq is True:
        should_try_groq = groq_cfg.available
    elif use_groq is None:
        should_try_groq = (
            groq_cfg.available
            and groq_cfg.use_for_simple_tasks
            and is_simple_task(request.mode, user_message)
        )

    if should_try_groq:
        try:
            console.print("[dim]Routing to Groq (simple task)…[/dim]")
            result, input_tok, output_tok = run_groq(
                system_prompt=system_prompt,
                user_message=user_message,
                model=groq_cfg.model,
                stream=stream,
                api_key=groq_cfg.resolved_api_key(),
            )
            _log_usage(
                agent="greybeard",
                command="analyze",
                pack=request.pack.name if request.pack else "",
                mode=request.mode,
                input_tokens=input_tok,
                output_tokens=output_tok,
                model=groq_cfg.model,
                provider="groq",
            )
            console.print("[dim]via Groq ✓[/dim]")
            return result
        except RuntimeError as e:
            console.print(f"[yellow]Groq unavailable ({e}), falling back to {llm.backend}[/yellow]")

    # Primary backend
    if llm.backend == "anthropic":
        result, input_tok, output_tok = _run_anthropic(
            llm, model, system_prompt, user_message, stream=stream
        )
    elif llm.backend == "copilot":
        result, input_tok, output_tok = _run_copilot(
            llm, model, system_prompt, user_message, stream=stream
        )
    else:
        result, input_tok, output_tok = _run_openai_compat(
            llm, model, system_prompt, user_message, stream=stream
        )

    _log_usage(
        agent="greybeard",
        command="analyze",
        pack=request.pack.name if request.pack else "",
        mode=request.mode,
        input_tokens=input_tok,
        output_tokens=output_tok,
        model=model,
        provider=llm.backend,
    )
    provider_label = "via Anthropic" if llm.backend == "anthropic" else f"via {llm.backend}"
    console.print(f"[dim]{provider_label} ✓[/dim]")
    return result


async def run_review_async(
    request: ReviewRequest,
    config: GreybeardConfig | dict | None = None,
    model_override: str | None = None,
    stream: bool = False,
    use_groq: bool | None = None,
) -> str:
    """Async wrapper for run_review (non-blocking for SaaS integrations).

    Args:
        request: The ReviewRequest with mode, pack, and content.
        config: GreybeardConfig object, dict, or None (loads from file).
        model_override: Override the configured model.
        stream: Whether to stream the response (default False for async).
        use_groq: Force Groq (True), skip (False), or auto-detect (None).

    Returns:
        The full review response text.

    This wraps run_review in an executor to avoid blocking the event loop.
    Ideal for web services, FastAPI endpoints, and serverless functions.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: run_review(
            request=request,
            config=config,
            model_override=model_override,
            stream=stream,
            use_groq=use_groq,
        ),
    )


# ---------------------------------------------------------------------------
# Backend implementations — return (text, input_tokens, output_tokens)
# ---------------------------------------------------------------------------


def _run_openai_compat(
    llm: LLMConfig,
    model: str,
    system_prompt: str,
    user_message: str,
    stream: bool = True,
) -> tuple[str, int, int]:
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
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    if stream:
        text = _stream_openai(client, model, messages)
        # Estimate tokens for streaming (no usage object)
        input_tokens = len(system_prompt.split()) + len(user_message.split())
        output_tokens = len(text.split())
        return text, input_tokens, output_tokens
    else:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            stream=False,
        )
        text = resp.choices[0].message.content or ""  # type: ignore[union-attr]
        usage = resp.usage
        return (
            text,
            (usage.prompt_tokens if usage else 0),
            (usage.completion_tokens if usage else 0),
        )


def _run_anthropic(
    llm: LLMConfig,
    model: str,
    system_prompt: str,
    user_message: str,
    stream: bool = True,
) -> tuple[str, int, int]:
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
            # get_final_message() has usage counts
            final = s.get_final_message()
            input_tokens = final.usage.input_tokens if final.usage else 0
            output_tokens = final.usage.output_tokens if final.usage else 0
        print()
        return full_text, input_tokens, output_tokens
    else:
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return (
            str(resp.content[0].text),
            resp.usage.input_tokens,
            resp.usage.output_tokens,
        )


def _run_copilot(
    llm: LLMConfig,
    model: str,
    system_prompt: str,
    user_message: str,
    stream: bool = True,
) -> tuple[str, int, int]:
    """Run via GitHub Copilot API (OpenAI-compatible endpoint)."""
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: openai package not installed. Run: uv pip install openai", file=sys.stderr)
        sys.exit(1)

    api_key = llm.resolved_api_key()
    if not api_key:
        env_var = llm.resolved_api_key_env()
        print(
            f"Error: {env_var} is not set.\n"
            f"Export it or add it to a .env file, or run: greybeard init",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = "https://api.githubcopilot.com/v1"
    client = OpenAI(api_key=api_key, base_url=base_url)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    if stream:
        text = _stream_openai(client, model, messages)
        input_tokens = len(system_prompt.split()) + len(user_message.split())
        output_tokens = len(text.split())
        return text, input_tokens, output_tokens
    else:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            stream=False,
        )
        text = resp.choices[0].message.content or ""  # type: ignore[union-attr]
        usage = resp.usage
        return (
            text,
            (usage.prompt_tokens if usage else 0),
            (usage.completion_tokens if usage else 0),
        )


def _stream_openai(client: object, model: str, messages: list[dict[str, str]]) -> str:
    """Stream an OpenAI-compatible response."""
    full_text = ""
    console.print()  # Add spacing before output
    stream = client.chat.completions.create(model=model, messages=messages, stream=True)  # type: ignore[union-attr,arg-type,attr-defined]
    for chunk in stream:  # type: ignore[misc]
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
