"""Core review engine — assembles context and calls the LLM."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from openai import OpenAI

from .models import ReviewRequest
from .modes import build_system_prompt

DEFAULT_MODEL = "gpt-4o"
MAX_INPUT_TOKENS_APPROX = 30_000  # rough char limit before truncation warning


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "Error: OPENAI_API_KEY is not set.\n"
            "Export it or add it to a .env file in the current directory.",
            file=sys.stderr,
        )
        sys.exit(1)
    return OpenAI(api_key=api_key)


def _collect_repo_context(repo_path: str) -> str:
    """
    Collect lightweight context from a repo: README, recent git log,
    and a directory tree (depth 2). Skips binary and vendor dirs.
    """
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

    # Directory tree (depth 2, skip common noise)
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
            parts.append("## Directory Structure\n\n```\n" + "\n".join(tree_lines) + "\n```")
    except PermissionError:
        pass

    return "\n\n".join(parts)


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

    # Warn if input is very large
    if len(combined) > MAX_INPUT_TOKENS_APPROX * 4:
        print(
            f"Warning: input is large (~{len(combined)//4} tokens estimated). "
            "Consider trimming or using --repo with a focused diff.",
            file=sys.stderr,
        )

    return combined


def run_review(
    request: ReviewRequest,
    model: str = DEFAULT_MODEL,
    stream: bool = True,
) -> str:
    """Run the review and return the full response text."""
    client = _get_client()
    system_prompt = build_system_prompt(request.mode, request.pack, request.audience)
    user_message = _build_user_message(request)

    if stream:
        return _stream_response(client, model, system_prompt, user_message)
    else:
        return _single_response(client, model, system_prompt, user_message)


def _stream_response(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_message: str,
) -> str:
    """Stream the response to stdout and return the full text."""
    full_text = ""
    with client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        stream=True,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            print(delta, end="", flush=True)
            full_text += delta
    print()  # final newline
    return full_text


def _single_response(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_message: str,
) -> str:
    """Non-streaming response (used in tests)."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        stream=False,
    )
    return response.choices[0].message.content or ""
