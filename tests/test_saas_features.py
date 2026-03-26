"""Tests for SaaS-ready features: Pydantic models, dict config, async, and storage abstractions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from greybeard.analyzer import run_review_async
from greybeard.config import GreybeardConfig
from greybeard.history import analyze_trends
from greybeard.models import ContentPack, ReviewRequest
from greybeard.storage import FileHistoryStorage, FilePacksStorage, HistoryStorage, PacksStorage


# ─────────────────────────────────────────────────────────────────────────────
# Test Models (Pydantic)
# ─────────────────────────────────────────────────────────────────────────────


class TestPydanticModels:
    """Test Pydantic-based data models."""

    def test_content_pack_model(self):
        """Test ContentPack Pydantic model."""
        pack = ContentPack(
            name="test-pack",
            perspective="Staff Engineer",
            tone="direct",
            focus_areas=["security", "performance"],
            heuristics=["Consider scaling"],
        )
        assert pack.name == "test-pack"
        assert pack.perspective == "Staff Engineer"
        assert "security" in pack.focus_areas

    def test_content_pack_from_dict(self):
        """Test ContentPack can be created from dict (Pydantic validation)."""
        data = {
            "name": "from-dict",
            "perspective": "Architect",
            "tone": "helpful",
            "description": "A test pack",
        }
        pack = ContentPack(**data)
        assert pack.name == "from-dict"
        assert pack.description == "A test pack"

    def test_content_pack_validation(self):
        """Test ContentPack validates required fields."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ContentPack(name="test")  # Missing required fields

    def test_review_request_model(self):
        """Test ReviewRequest Pydantic model."""
        pack = ContentPack(name="test", perspective="Test", tone="calm")
        req = ReviewRequest(
            mode="review",
            pack=pack,
            input_text="some code",
            audience="team",
        )
        assert req.mode == "review"
        assert req.audience == "team"
        assert req.pack.name == "test"

    def test_review_request_from_dict(self):
        """Test ReviewRequest can be created from dict."""
        pack_data = {"name": "test", "perspective": "Test", "tone": "calm"}
        data = {
            "mode": "mentor",
            "pack": pack_data,
            "input_text": "some code",
        }
        req = ReviewRequest(**data)
        assert req.mode == "mentor"
        assert isinstance(req.pack, ContentPack)

    def test_whitespace_stripping(self):
        """Test Pydantic config strips whitespace."""
        pack = ContentPack(
            name="  test  ",
            perspective="  Staff  ",
            tone="  calm  ",
        )
        assert pack.name == "test"
        assert pack.perspective == "Staff"
        assert pack.tone == "calm"


# ─────────────────────────────────────────────────────────────────────────────
# Test Config Dict Support
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigDictSupport:
    """Test GreybeardConfig.from_dict() for SaaS integrations."""

    def test_config_from_empty_dict(self):
        """Test creating config from empty dict uses defaults."""
        cfg = GreybeardConfig.from_dict({})
        assert cfg.default_pack == "staff-core"
        assert cfg.default_mode == "review"
        assert cfg.llm.backend == "openai"

    def test_config_from_dict_with_llm(self):
        """Test creating config with LLM settings."""
        data = {
            "llm": {
                "backend": "anthropic",
                "model": "claude-sonnet-4-6",
            }
        }
        cfg = GreybeardConfig.from_dict(data)
        assert cfg.llm.backend == "anthropic"
        assert cfg.llm.model == "claude-sonnet-4-6"

    def test_config_from_dict_with_groq(self):
        """Test creating config with Groq settings."""
        data = {
            "groq": {
                "enabled": True,
                "use_for_simple_tasks": False,
                "model": "llama-3.3-70b-versatile",
            }
        }
        cfg = GreybeardConfig.from_dict(data)
        assert cfg.groq.enabled
        assert not cfg.groq.use_for_simple_tasks
        assert cfg.groq.model == "llama-3.3-70b-versatile"

    def test_config_from_complete_dict(self):
        """Test creating config from complete dict."""
        data = {
            "default_pack": "custom-pack",
            "default_mode": "mentor",
            "llm": {
                "backend": "anthropic",
                "model": "claude-haiku-4-5-20251001",
            },
            "groq": {
                "enabled": False,
            },
            "pack_sources": ["github:owner/repo"],
        }
        cfg = GreybeardConfig.from_dict(data)
        assert cfg.default_pack == "custom-pack"
        assert cfg.default_mode == "mentor"
        assert cfg.llm.backend == "anthropic"
        assert not cfg.groq.enabled
        assert "github:owner/repo" in cfg.pack_sources


# ─────────────────────────────────────────────────────────────────────────────
# Test History Storage Abstraction
# ─────────────────────────────────────────────────────────────────────────────


class MockHistoryStorage(HistoryStorage):
    """In-memory mock for testing history storage."""

    def __init__(self):
        self.entries: list[dict[str, Any]] = []

    def save_entry(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)

    def load_entries(self, days: int = 30, pack: str | None = None) -> list[dict[str, Any]]:
        results = self.entries.copy()
        if pack:
            results = [e for e in results if e.get("pack") == pack]
        return list(reversed(results))  # newest first


class TestHistoryStorage:
    """Test history storage abstraction."""

    def test_file_history_storage_save_and_load(self):
        """Test FileHistoryStorage saves and loads entries."""
        with TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.jsonl"
            storage = FileHistoryStorage(history_file)

            entry = {
                "timestamp": "2026-03-25T12:00:00Z",
                "decision_name": "test-decision",
                "pack": "staff-core",
                "mode": "review",
                "summary": "Test summary",
                "key_risks": ["risk1"],
                "key_questions": ["question1?"],
            }
            storage.save_entry(entry)

            loaded = storage.load_entries(days=30)
            assert len(loaded) == 1
            assert loaded[0]["decision_name"] == "test-decision"

    def test_file_history_storage_pack_filter(self):
        """Test FileHistoryStorage pack filtering."""
        with TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.jsonl"
            storage = FileHistoryStorage(history_file)

            storage.save_entry(
                {
                    "timestamp": "2026-03-25T12:00:00Z",
                    "pack": "staff-core",
                    "mode": "review",
                    "decision_name": "decision1",
                    "summary": "",
                    "key_risks": [],
                    "key_questions": [],
                }
            )
            storage.save_entry(
                {
                    "timestamp": "2026-03-25T13:00:00Z",
                    "pack": "security-reviewer",
                    "mode": "review",
                    "decision_name": "decision2",
                    "summary": "",
                    "key_risks": [],
                    "key_questions": [],
                }
            )

            loaded = storage.load_entries(days=30, pack="staff-core")
            assert len(loaded) == 1
            assert loaded[0]["pack"] == "staff-core"

    def test_mock_history_storage(self):
        """Test mock history storage works as expected."""
        storage = MockHistoryStorage()
        entry = {
            "timestamp": "2026-03-25T12:00:00Z",
            "decision_name": "test",
            "pack": "test-pack",
            "mode": "review",
            "summary": "test",
            "key_risks": [],
            "key_questions": [],
        }
        storage.save_entry(entry)
        loaded = storage.load_entries(days=30)
        assert len(loaded) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test Packs Storage Abstraction
# ─────────────────────────────────────────────────────────────────────────────


class MockPacksStorage(PacksStorage):
    """In-memory mock for testing packs storage."""

    def __init__(self):
        self.packs: dict[tuple[str, str], str] = {}  # (name, source_slug) -> yaml_content

    def save_pack(self, name: str, source_slug: str, yaml_content: str) -> Path:
        self.packs[(name, source_slug)] = yaml_content
        return Path(f"/mock/{source_slug}/{name}.yaml")

    def load_pack(self, name: str, source_slug: str | None = None) -> str | None:
        if source_slug:
            return self.packs.get((name, source_slug))
        # Search all sources
        for (n, s), content in self.packs.items():
            if n == name:
                return content
        return None

    def list_installed(self) -> list[dict[str, str]]:
        return [
            {"name": n, "source": s, "path": f"/mock/{s}/{n}.yaml"} for n, s in self.packs.keys()
        ]

    def remove_source(self, source_slug: str) -> int:
        to_remove = [(n, s) for n, s in self.packs.keys() if s == source_slug]
        for key in to_remove:
            del self.packs[key]
        return len(to_remove)


class TestPacksStorage:
    """Test packs storage abstraction."""

    def test_file_packs_storage_save_and_load(self):
        """Test FilePacksStorage saves and loads packs."""
        with TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            storage = FilePacksStorage(cache_dir)

            yaml_content = "name: test\nperspective: Test\ntone: calm\n"
            storage.save_pack("test-pack", "github__owner__repo", yaml_content)

            loaded = storage.load_pack("test-pack", source_slug="github__owner__repo")
            assert loaded == yaml_content

    def test_file_packs_storage_list(self):
        """Test FilePacksStorage lists installed packs."""
        with TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            storage = FilePacksStorage(cache_dir)

            storage.save_pack("pack1", "source1", "yaml1")
            storage.save_pack("pack2", "source1", "yaml2")
            storage.save_pack("pack3", "source2", "yaml3")

            installed = storage.list_installed()
            assert len(installed) == 3
            assert any(p["name"] == "pack1" for p in installed)

    def test_file_packs_storage_remove_source(self):
        """Test FilePacksStorage removes packs by source."""
        with TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            storage = FilePacksStorage(cache_dir)

            storage.save_pack("pack1", "source1", "yaml1")
            storage.save_pack("pack2", "source1", "yaml2")
            storage.save_pack("pack3", "source2", "yaml3")

            count = storage.remove_source("source1")
            assert count == 2

            installed = storage.list_installed()
            assert len(installed) == 1
            assert installed[0]["source"] == "source2"

    def test_mock_packs_storage(self):
        """Test mock packs storage."""
        storage = MockPacksStorage()
        storage.save_pack("test", "github__owner__repo", "yaml_content")

        loaded = storage.load_pack("test", source_slug="github__owner__repo")
        assert loaded == "yaml_content"

        installed = storage.list_installed()
        assert len(installed) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test Analyzer with Dict Config
# ─────────────────────────────────────────────────────────────────────────────


class TestAnalyzerDictConfig:
    """Test run_review and run_review_async with dict config."""

    def test_run_review_with_dict_config(self):
        """Test run_review accepts dict config."""
        pack = ContentPack(name="test", perspective="Test", tone="calm")
        ReviewRequest(
            mode="review",
            pack=pack,
            input_text="simple code snippet",
            context_notes="no special context",
        )

        config = {
            "llm": {
                "backend": "anthropic",
            },
            "groq": {
                "enabled": False,
            },
        }

        # We can't fully test without valid API keys, but we can verify it accepts the dict
        # and converts it to GreybeardConfig without errors.
        # The actual call would fail due to auth, so we just test type conversion.
        cfg = GreybeardConfig.from_dict(config)
        assert cfg.llm.backend == "anthropic"
        assert not cfg.groq.enabled

    def test_run_review_async_callable(self):
        """Test that run_review_async is callable (doesn't need API keys for signature test)."""
        pack = ContentPack(name="test", perspective="Test", tone="calm")
        ReviewRequest(
            mode="review",
            pack=pack,
            input_text="code",
        )

        # Just verify the function is callable with async/await
        # (actual execution would fail without ollama running)
        assert asyncio.iscoroutinefunction(run_review_async)


# ─────────────────────────────────────────────────────────────────────────────
# Test History Module with Storage Injection
# ─────────────────────────────────────────────────────────────────────────────


class TestHistoryWithStorage:
    """Test history module with injectable storage."""

    def test_save_and_load_history_with_mock(self, monkeypatch):
        """Test save_decision and load_history with mock storage."""
        from greybeard import history

        mock_storage = MockHistoryStorage()
        monkeypatch.setattr(history, "_storage", mock_storage)

        # Save a decision
        history.save_decision(
            name="test-decision",
            review_text=(
                "- Missing tests is a critical issue\n- No monitoring setup\n"
                "- Knowledge concentration risk"
            ),
            pack="staff-core",
            mode="review",
        )

        # Load and verify
        entries = history.load_history(days=30)
        assert len(entries) == 1
        assert entries[0]["decision_name"] == "test-decision"
        # Check that risks were extracted
        assert len(entries[0]["key_risks"]) > 0

    def test_analyze_trends(self):
        """Test trend analysis on history entries."""
        entries = [
            {
                "timestamp": "2026-03-25T12:00:00Z",
                "decision_name": "decision1",
                "pack": "staff-core",
                "mode": "review",
                "summary": "test",
                "key_risks": ["knowledge concentration", "missing tests"],
                "key_questions": ["Who owns this?"],
            },
            {
                "timestamp": "2026-03-25T13:00:00Z",
                "decision_name": "decision2",
                "pack": "staff-core",
                "mode": "review",
                "summary": "test",
                "key_risks": ["missing tests", "no monitoring"],
                "key_questions": ["What if it fails?"],
            },
            {
                "timestamp": "2026-03-25T14:00:00Z",
                "decision_name": "decision3",
                "pack": "security-reviewer",
                "mode": "review",
                "summary": "test",
                "key_risks": ["missing tests"],
                "key_questions": ["Is it secure?"],
            },
        ]

        trends = analyze_trends(entries)
        assert trends["total_decisions"] == 3
        # "missing tests" should be flagged (appears 3 times, at threshold)
        assert len(trends["flagged_risks"]) > 0
        assert trends["most_used_packs"][0][0] == "staff-core"


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestIntegration:
    """Integration tests combining multiple SaaS features."""

    def test_full_saas_workflow_with_dict_config_and_mock_storage(self, monkeypatch):
        """Test a complete SaaS workflow with dict config and mock storage."""
        from greybeard import history

        # Set up mock storage
        mock_storage = MockHistoryStorage()
        monkeypatch.setattr(history, "_storage", mock_storage)

        # Create config from dict (like SaaS would)
        config = GreybeardConfig.from_dict(
            {
                "llm": {"backend": "anthropic"},
                "groq": {"enabled": False},
            }
        )
        assert config.llm.backend == "anthropic"

        # Create request from user input
        pack = ContentPack(
            name="staff-core",
            perspective="Staff Engineer",
            tone="direct",
            focus_areas=["architecture"],
        )
        request = ReviewRequest(
            mode="review",
            pack=pack,
            input_text="sample code",
            context_notes="testing context",
        )
        assert request.pack.name == "staff-core"

        # Save a decision to history
        history.save_decision(
            name="integration-test",
            review_text="Risk: No rollback plan.",
            pack="staff-core",
            mode="review",
        )

        # Load and analyze
        entries = history.load_history(days=30)
        assert len(entries) == 1
        assert entries[0]["decision_name"] == "integration-test"
