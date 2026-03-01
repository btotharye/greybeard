"""Content pack loader."""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import yaml

from .models import ContentPack

# Built-in pack names (shipped with the package)
BUILTIN_PACKS = [
    "staff-core",
    "oncall-future-you",
    "mentor-mode",
    "solutions-architect",
    "idp-readiness",
]


def _packs_dir() -> Path:
    """Return the path to the built-in packs directory."""
    # Walk up from this file to find the packs/ directory at repo root
    here = Path(__file__).parent
    candidate = here.parent / "packs"
    if candidate.is_dir():
        return candidate
    # Installed package — use importlib.resources
    try:
        ref = importlib.resources.files("packs")  # type: ignore[attr-defined]
        return Path(str(ref))
    except Exception:
        return candidate


def load_pack(name_or_path: str) -> ContentPack:
    """
    Load a content pack by name (built-in) or path (custom YAML file).

    Raises FileNotFoundError if the pack cannot be found.
    """
    path = Path(name_or_path)

    # If it looks like a path (has a slash or .yaml/.yml extension), treat it as a file
    if path.suffix in (".yaml", ".yml") or "/" in name_or_path or "\\" in name_or_path:
        if not path.is_file():
            raise FileNotFoundError(f"Content pack file not found: {name_or_path}")
        return _load_from_file(path)

    # Otherwise look in built-in packs
    packs_dir = _packs_dir()
    for ext in (".yaml", ".yml"):
        candidate = packs_dir / f"{name_or_path}{ext}"
        if candidate.is_file():
            return _load_from_file(candidate)

    available = ", ".join(BUILTIN_PACKS)
    raise FileNotFoundError(
        f"Built-in pack '{name_or_path}' not found. "
        f"Available: {available}. "
        f"Or pass a path to a custom .yaml file."
    )


def _load_from_file(path: Path) -> ContentPack:
    """Parse a YAML file into a ContentPack."""
    with path.open() as f:
        data = yaml.safe_load(f) or {}

    return ContentPack(
        name=data.get("name", path.stem),
        perspective=data.get("perspective", "Staff Engineer"),
        tone=data.get("tone", "calm and direct"),
        focus_areas=data.get("focus_areas", []),
        heuristics=data.get("heuristics", []),
        example_questions=data.get("example_questions", []),
        communication_style=data.get("communication_style", ""),
        description=data.get("description", ""),
    )


def list_builtin_packs() -> list[str]:
    """Return names of all available built-in packs."""
    packs_dir = _packs_dir()
    found = []
    for ext in (".yaml", ".yml"):
        found.extend(p.stem for p in packs_dir.glob(f"*{ext}"))
    return sorted(found) or BUILTIN_PACKS
