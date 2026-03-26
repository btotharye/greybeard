"""Pluggable storage interfaces for history and packs.

Allows greybeard to work with different backends (filesystem, databases, APIs)
without changing the core analyzer logic.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# History Storage Interface
# ---------------------------------------------------------------------------


class HistoryStorage(ABC):
    """Abstract interface for decision history storage."""

    @abstractmethod
    def save_entry(self, entry: dict[str, Any]) -> None:
        """Save a single history entry.

        Args:
            entry: Dict with keys: timestamp, decision_name, pack, mode, summary,
                   key_risks, key_questions.
        """
        pass

    @abstractmethod
    def load_entries(
        self,
        days: int = 30,
        pack: str | None = None,
    ) -> list[dict[str, Any]]:
        """Load history entries, optionally filtered.

        Args:
            days: Include entries from last N days (0 = all time).
            pack: If set, only entries for this pack.

        Returns:
            List of entry dicts, newest first.
        """
        pass


class FileHistoryStorage(HistoryStorage):
    """Default file-based history storage (JSONL at ~/.greybeard/history.jsonl)."""

    def __init__(self, history_file: Path | None = None):
        """Initialize file-based history storage.

        Args:
            history_file: Path to .jsonl file. Defaults to ~/.greybeard/history.jsonl.
        """
        self.history_file = history_file or (Path.home() / ".greybeard" / "history.jsonl")

    def save_entry(self, entry: dict[str, Any]) -> None:
        """Append entry to JSONL file."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with self.history_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def load_entries(
        self,
        days: int = 30,
        pack: str | None = None,
    ) -> list[dict[str, Any]]:
        """Load entries from JSONL file with optional filtering."""
        if not self.history_file.exists():
            return []

        from datetime import UTC, timedelta

        cutoff = (
            datetime.now(tz=UTC) - timedelta(days=days)
            if days > 0
            else datetime.min.replace(tzinfo=UTC)
        )

        entries: list[dict[str, Any]] = []
        with self.history_file.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Timestamp filter
                try:
                    ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                except (KeyError, ValueError):
                    continue
                if ts < cutoff:
                    continue

                # Pack filter
                if pack and entry.get("pack") != pack:
                    continue

                entries.append(entry)

        return list(reversed(entries))  # newest first


# ---------------------------------------------------------------------------
# Packs Storage Interface
# ---------------------------------------------------------------------------


class PacksStorage(ABC):
    """Abstract interface for content packs storage."""

    @abstractmethod
    def save_pack(self, name: str, source_slug: str, yaml_content: str) -> Path:
        """Save a pack YAML content.

        Args:
            name: Pack name.
            source_slug: Source identifier (e.g., 'github__owner__repo').
            yaml_content: Full YAML text.

        Returns:
            Path where the pack was saved.
        """
        pass

    @abstractmethod
    def load_pack(self, name: str, source_slug: str | None = None) -> str | None:
        """Load a pack YAML content.

        Args:
            name: Pack name.
            source_slug: If set, only search this source. Otherwise search all.

        Returns:
            YAML content string, or None if not found.
        """
        pass

    @abstractmethod
    def list_installed(self) -> list[dict[str, str]]:
        """List all installed packs with metadata.

        Returns:
            List of dicts with keys: name, source, path.
        """
        pass

    @abstractmethod
    def remove_source(self, source_slug: str) -> int:
        """Remove all packs from a source.

        Returns:
            Count of packs removed.
        """
        pass


class FilePacksStorage(PacksStorage):
    """Default file-based packs storage (filesystem cache at ~/.greybeard/packs/)."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize file-based packs storage.

        Args:
            cache_dir: Root cache directory. Defaults to ~/.greybeard/packs/.
        """
        self.cache_dir = cache_dir or (Path.home() / ".greybeard" / "packs")

    def save_pack(self, name: str, source_slug: str, yaml_content: str) -> Path:
        """Save a pack YAML to filesystem."""
        source_dir = self.cache_dir / source_slug
        source_dir.mkdir(parents=True, exist_ok=True)
        pack_file = source_dir / f"{name}.yaml"
        pack_file.write_text(yaml_content)
        return pack_file

    def load_pack(self, name: str, source_slug: str | None = None) -> str | None:
        """Load a pack YAML from filesystem."""
        if source_slug:
            pack_file = self.cache_dir / source_slug / f"{name}.yaml"
            if pack_file.exists():
                return pack_file.read_text()
            return None

        # Search all sources
        if not self.cache_dir.exists():
            return None

        for source_dir in self.cache_dir.iterdir():
            if not source_dir.is_dir():
                continue
            pack_file = source_dir / f"{name}.yaml"
            if pack_file.exists():
                return pack_file.read_text()

        return None

    def list_installed(self) -> list[dict[str, str]]:
        """List all installed packs from filesystem."""
        if not self.cache_dir.exists():
            return []

        results = []
        for source_dir in sorted(self.cache_dir.iterdir()):
            if not source_dir.is_dir():
                continue
            for pack_file in sorted(source_dir.glob("*.yaml")):
                results.append(
                    {
                        "name": pack_file.stem,
                        "source": source_dir.name,
                        "path": str(pack_file),
                    }
                )
        return results

    def remove_source(self, source_slug: str) -> int:
        """Remove all packs from a source."""
        target = self.cache_dir / source_slug
        if not target.exists():
            # Try to find by partial match
            matches = [d for d in self.cache_dir.iterdir() if source_slug in d.name]
            if not matches:
                raise FileNotFoundError(f"No cached source matching: {source_slug}")
            target = matches[0]

        count = len(list(target.glob("*.yaml")))
        import shutil

        shutil.rmtree(target)
        return count
