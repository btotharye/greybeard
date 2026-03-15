"""Global configuration management for greybeard.

Config lives at ~/.greybeard/config.yaml.
All fields are optional — sensible defaults work out of the box.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_DIR = Path.home() / ".greybeard"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
PACK_CACHE_DIR = CONFIG_DIR / "packs"

# Backend names we know about
KNOWN_BACKENDS = ["openai", "anthropic", "ollama", "lmstudio"]

# Default models per backend
DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
    "ollama": "llama3.2",
    "lmstudio": "local-model",
}

# Default base URLs for local/alternate backends
DEFAULT_BASE_URLS: dict[str, str] = {
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}

# Default API key env vars per backend
DEFAULT_API_KEY_ENVS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": "",  # no key needed
    "lmstudio": "",  # no key needed
}


@dataclass
class LLMConfig:
    """LLM backend configuration."""

    backend: str = "openai"
    model: str = ""  # empty = use DEFAULT_MODELS[backend]
    base_url: str = ""  # empty = use DEFAULT_BASE_URLS[backend] if known
    api_key_env: str = ""  # empty = use DEFAULT_API_KEY_ENVS[backend]

    def resolved_model(self) -> str:
        return self.model or DEFAULT_MODELS.get(self.backend, "gpt-4o")

    def resolved_base_url(self) -> str | None:
        if self.base_url:
            return self.base_url
        return DEFAULT_BASE_URLS.get(self.backend)

    def resolved_api_key(self) -> str | None:
        env_var = self.api_key_env or DEFAULT_API_KEY_ENVS.get(self.backend, "OPENAI_API_KEY")
        if not env_var:
            return "no-key-needed"
        return os.getenv(env_var)

    def resolved_api_key_env(self) -> str:
        return self.api_key_env or DEFAULT_API_KEY_ENVS.get(self.backend, "OPENAI_API_KEY")


@dataclass
class GreybeardConfig:
    """Top-level greybeard configuration."""

    default_pack: str = "staff-core"
    default_mode: str = "review"
    llm: LLMConfig = field(default_factory=LLMConfig)
    pack_sources: list[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> GreybeardConfig:
        """Load config from ~/.greybeard/config.yaml, or return defaults."""
        if not CONFIG_FILE.exists():
            return cls()

        with CONFIG_FILE.open() as f:
            data = yaml.safe_load(f) or {}

        llm_data = data.get("llm", {})
        llm = LLMConfig(
            backend=llm_data.get("backend", "openai"),
            model=llm_data.get("model", ""),
            base_url=llm_data.get("base_url", ""),
            api_key_env=llm_data.get("api_key_env", ""),
        )

        return cls(
            default_pack=data.get("default_pack", "staff-core"),
            default_mode=data.get("default_mode", "review"),
            llm=llm,
            pack_sources=data.get("pack_sources", []),
        )

    def save(self) -> None:
        """Write config to ~/.greybeard/config.yaml."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data: dict = {
            "default_pack": self.default_pack,
            "default_mode": self.default_mode,
            "llm": {
                "backend": self.llm.backend,
                "model": self.llm.model,
                "base_url": self.llm.base_url,
                "api_key_env": self.llm.api_key_env,
            },
            "pack_sources": self.pack_sources,
        }
        # Strip empty strings to keep the file clean
        data["llm"] = {k: v for k, v in data["llm"].items() if v}
        with CONFIG_FILE.open("w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def to_display_dict(self) -> dict:
        """Render config for display."""
        return {
            "default_pack": self.default_pack,
            "default_mode": self.default_mode,
            "llm.backend": self.llm.backend,
            "llm.model": self.llm.resolved_model(),
            "llm.base_url": self.llm.resolved_base_url() or "(default)",
            "llm.api_key_env": self.llm.resolved_api_key_env() or "(none)",
            "pack_sources": self.pack_sources or [],
        }
