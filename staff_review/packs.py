"""Remote and local pack registry management.

Pack sources can be:
  - Built-in: just a name like "staff-core"
  - Local file: path/to/pack.yaml
  - GitHub repo: github:owner/repo  (loads all .yaml files from packs/ dir)
  - GitHub file: github:owner/repo/path/to/pack.yaml
  - Raw URL: https://example.com/my-pack.yaml

Installed packs are cached in ~/.greybeard/packs/<source-slug>/<pack-name>.yaml
"""

from __future__ import annotations

import hashlib
import re
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from .models import ContentPack

if TYPE_CHECKING:
    pass

PACK_CACHE_DIR = Path.home() / ".greybeard" / "packs"

# GitHub API base
GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_pack(name_or_path: str) -> ContentPack:
    """
    Load a content pack by:
      - Built-in name (e.g. "staff-core")
      - Local file path (e.g. "my-pack.yaml")
      - Cache slug (e.g. "owner__repo__pack-name")
      - github: prefix (loads from GitHub, caches locally)
      - https:// URL (downloads, caches locally)

    Raises FileNotFoundError if the pack cannot be found.
    """
    name_or_path = name_or_path.strip()

    # Remote sources — download and cache
    if name_or_path.startswith("github:"):
        return _load_github_pack(name_or_path[7:])
    if name_or_path.startswith("https://") or name_or_path.startswith("http://"):
        return _load_url_pack(name_or_path)

    # Local file path
    path = Path(name_or_path)
    if path.suffix in (".yaml", ".yml") or "/" in name_or_path or "\\" in name_or_path:
        if not path.is_file():
            raise FileNotFoundError(f"Content pack file not found: {name_or_path}")
        return _load_from_file(path)

    # Check ~/.greybeard/packs/<anything>/<name>.yaml (cached remote packs)
    cached = _find_in_cache(name_or_path)
    if cached:
        return _load_from_file(cached)

    # Built-in packs: try both old format (name.yaml) and new format (name/name.yaml)
    builtin = _builtin_packs_dir()

    # Old format: packs/name.yaml
    for ext in (".yaml", ".yml"):
        candidate = builtin / f"{name_or_path}{ext}"
        if candidate.is_file():
            return _load_from_file(candidate)

    # New format: packs/name/name.yaml
    for ext in (".yaml", ".yml"):
        candidate = builtin / name_or_path / f"{name_or_path}{ext}"
        if candidate.is_file():
            return _load_from_file(candidate)

    available = ", ".join(list_builtin_packs())
    raise FileNotFoundError(
        f"Pack '{name_or_path}' not found.\n"
        f"Built-in packs: {available}\n"
        f"Install remote packs with: greybeard pack install github:owner/repo"
    )


def list_builtin_packs() -> list[str]:
    """Return names of all available built-in packs.

    Supports both old and new pack structures:
    - Old: packs/pack-name.yaml
    - New: packs/pack-folder/pack-name.yaml
    """
    d = _builtin_packs_dir()
    found = set()

    # Old format: packs/*.yaml
    for ext in (".yaml", ".yml"):
        found.update(p.stem for p in sorted(d.glob(f"*{ext}")))

    # New format: packs/folder/*.yaml
    for subfolder in sorted(d.iterdir()):
        if not subfolder.is_dir():
            continue
        for ext in (".yaml", ".yml"):
            found.update(p.stem for p in sorted(subfolder.glob(f"*{ext}")))

    return sorted(list(found)) or BUILTIN_PACK_NAMES


def list_installed_packs() -> list[dict]:
    """List all packs in ~/.greybeard/packs/ with source info."""
    if not PACK_CACHE_DIR.exists():
        return []
    results = []
    for source_dir in sorted(PACK_CACHE_DIR.iterdir()):
        if not source_dir.is_dir():
            continue
        for pack_file in sorted(source_dir.glob("*.yaml")):
            try:
                pack = _load_from_file(pack_file)
                results.append(
                    {
                        "name": pack.name,
                        "source": source_dir.name,
                        "path": str(pack_file),
                        "description": pack.description,
                    }
                )
            except Exception:
                pass
    return results


def install_pack_source(source: str, force: bool = False) -> list[ContentPack]:
    """
    Install all packs from a source into the cache.
    Returns list of installed ContentPack objects.
    """
    source = source.strip()
    if source.startswith("github:"):
        return _install_github_source(source[7:], force=force)
    if source.startswith("https://") or source.startswith("http://"):
        pack = _load_url_pack(source, cache=True, force=force)
        return [pack]
    raise ValueError(
        f"Unknown source format: {source!r}\n"
        "Supported formats:\n"
        "  github:owner/repo\n"
        "  github:owner/repo/path/to/pack.yaml\n"
        "  https://example.com/pack.yaml"
    )


def remove_pack_source(source_slug: str) -> int:
    """Remove all packs from a cached source. Returns count removed."""
    target = PACK_CACHE_DIR / source_slug
    if not target.exists():
        # Try to find by partial match
        matches = [d for d in PACK_CACHE_DIR.iterdir() if source_slug in d.name]
        if not matches:
            raise FileNotFoundError(f"No cached source matching: {source_slug}")
        target = matches[0]

    count = len(list(target.glob("*.yaml")))
    import shutil

    shutil.rmtree(target)
    return count


# ---------------------------------------------------------------------------
# GitHub loading
# ---------------------------------------------------------------------------


def _install_github_source(spec: str, force: bool = False) -> list[ContentPack]:
    """
    Install from a GitHub source spec:
      owner/repo           → all .yaml files in packs/ directory
      owner/repo/path/file.yaml → single file
    """
    parts = spec.split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub source: {spec!r}. Expected owner/repo")

    owner, repo = parts[0], parts[1]
    subpath = "/".join(parts[2:]) if len(parts) > 2 else ""

    if subpath.endswith(".yaml") or subpath.endswith(".yml"):
        # Single file install
        pack = _load_github_pack(spec, cache=True, force=force)
        return [pack]

    # Directory install — look for packs/ subdirectory by default
    pack_subdir = subpath if subpath else "packs"
    slug = _source_slug(f"github:{owner}/{repo}")
    cache_dir = PACK_CACHE_DIR / slug
    cache_dir.mkdir(parents=True, exist_ok=True)

    # List files via GitHub API
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{pack_subdir}"
    try:
        contents = _fetch_json(url)
    except Exception as e:
        raise FileNotFoundError(
            f"Could not list {pack_subdir}/ in {owner}/{repo}: {e}\n"
            "Make sure the repo is public and the packs/ directory exists."
        ) from e

    installed = []
    for item in contents:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if not (name.endswith(".yaml") or name.endswith(".yml")):
            continue
        raw_url = item.get("download_url", "")
        if not raw_url:
            continue
        pack = _load_url_pack(raw_url, cache=True, force=force, cache_dir=cache_dir)
        installed.append(pack)

    if not installed:
        raise FileNotFoundError(
            f"No .yaml files found in {owner}/{repo}/{pack_subdir}/\n"
            "Make sure the repo has a packs/ directory with .yaml pack files."
        )
    return installed


def _load_github_pack(spec: str, cache: bool = True, force: bool = False) -> ContentPack:
    """
    Load a single pack from GitHub.
      owner/repo/path/to/pack.yaml  → raw content
    """
    parts = spec.split("/")
    if len(parts) < 3:
        raise FileNotFoundError(
            f"Invalid GitHub pack spec: {spec!r}.\n"
            "Expected: github:owner/repo/path/to/pack.yaml\n"
            "Or for a whole repo: greybeard pack install github:owner/repo"
        )
    owner, repo = parts[0], parts[1]
    file_path = "/".join(parts[2:])
    branch = "main"
    url = f"{GITHUB_RAW}/{owner}/{repo}/{branch}/{file_path}"

    slug = _source_slug(f"github:{owner}/{repo}")
    cache_dir = PACK_CACHE_DIR / slug if cache else None
    return _load_url_pack(url, cache=cache, force=force, cache_dir=cache_dir)


# ---------------------------------------------------------------------------
# URL loading
# ---------------------------------------------------------------------------


def _load_url_pack(
    url: str,
    cache: bool = True,
    force: bool = False,
    cache_dir: Path | None = None,
) -> ContentPack:
    """Download a pack YAML from a URL, optionally caching it."""
    if cache_dir is None and cache:
        slug = _source_slug(url)
        cache_dir = PACK_CACHE_DIR / slug

    # Check cache first
    if cache_dir and not force:
        stem = Path(url.split("/")[-1]).stem
        cached_file = cache_dir / f"{stem}.yaml"
        if cached_file.exists():
            return _load_from_file(cached_file)

    # Download
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "greybeard-cli/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
    except Exception as e:
        raise FileNotFoundError(f"Could not download pack from {url}: {e}") from e

    # Parse first to validate
    pack = _parse_yaml_content(content, stem=Path(url.split("/")[-1]).stem)

    # Cache it
    if cache and cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        dest = cache_dir / f"{pack.name}.yaml"
        dest.write_text(content)

    return pack


# ---------------------------------------------------------------------------
# Local file loading
# ---------------------------------------------------------------------------


def _load_from_file(path: Path) -> ContentPack:
    """Parse a YAML file into a ContentPack."""
    with path.open() as f:
        content = f.read()
    return _parse_yaml_content(content, stem=path.stem)


def _parse_yaml_content(content: str, stem: str = "unknown") -> ContentPack:
    """Parse YAML content string into a ContentPack."""
    data = yaml.safe_load(content) or {}
    return ContentPack(
        name=data.get("name", stem),
        perspective=data.get("perspective", "Staff Engineer"),
        tone=data.get("tone", "calm and direct"),
        focus_areas=data.get("focus_areas", []),
        heuristics=data.get("heuristics", []),
        example_questions=data.get("example_questions", []),
        communication_style=data.get("communication_style", ""),
        description=data.get("description", ""),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _builtin_packs_dir() -> Path:
    here = Path(__file__).parent
    candidate = here.parent / "packs"
    if candidate.is_dir():
        return candidate
    return candidate


def _find_in_cache(name: str) -> Path | None:
    """Search ~/.greybeard/packs/*/<name>.yaml"""
    if not PACK_CACHE_DIR.exists():
        return None
    for source_dir in PACK_CACHE_DIR.iterdir():
        if not source_dir.is_dir():
            continue
        for ext in (".yaml", ".yml"):
            candidate = source_dir / f"{name}{ext}"
            if candidate.exists():
                return candidate
    return None


def _source_slug(source: str) -> str:
    """Convert a source URL/spec into a safe directory name."""
    # github:owner/repo -> owner__repo
    slug = re.sub(r"^github:", "", source)
    slug = re.sub(r"^https?://", "", slug)
    slug = re.sub(r"[^a-zA-Z0-9_.-]", "__", slug)
    # Truncate if very long
    if len(slug) > 64:
        slug = slug[:48] + "__" + hashlib.md5(slug.encode()).hexdigest()[:8]
    return slug


def _fetch_json(url: str) -> list | dict:
    """Fetch a URL and parse as JSON."""
    import json

    req = urllib.request.Request(url, headers={"User-Agent": "greybeard-cli/0.1"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Kept for backwards compat
BUILTIN_PACK_NAMES = [
    "staff-core",
    "oncall-future-you",
    "mentor-mode",
    "solutions-architect",
    "idp-readiness",
    "security-reviewer",
    "startup-pragmatist",
    "incident-postmortem",
    "data-migrations",
]
