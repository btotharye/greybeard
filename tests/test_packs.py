"""Tests for content pack loading."""

from __future__ import annotations

import pytest
import yaml

from staff_review.models import ContentPack
from staff_review.packs import (
    BUILTIN_PACK_NAMES,
    _source_slug,
    list_builtin_packs,
    list_installed_packs,
    load_pack,
)


class TestLoadBuiltinPacks:
    def test_loads_staff_core(self):
        pack = load_pack("staff-core")
        assert isinstance(pack, ContentPack)
        assert pack.name == "staff-core"
        assert pack.perspective
        assert pack.tone
        assert len(pack.heuristics) > 0
        assert len(pack.example_questions) > 0

    def test_loads_oncall_future_you(self):
        pack = load_pack("oncall-future-you")
        assert pack.name == "oncall-future-you"
        assert "3am" in pack.perspective.lower() or "on-call" in pack.perspective.lower()

    def test_loads_mentor_mode(self):
        pack = load_pack("mentor-mode")
        assert pack.name == "mentor-mode"
        assert pack.tone

    def test_loads_solutions_architect(self):
        pack = load_pack("solutions-architect")
        assert pack.name == "solutions-architect"
        assert len(pack.heuristics) > 0

    def test_loads_idp_readiness(self):
        pack = load_pack("idp-readiness")
        assert pack.name == "idp-readiness"
        assert len(pack.focus_areas) > 0

    @pytest.mark.parametrize("pack_name", BUILTIN_PACK_NAMES)
    def test_all_builtin_packs_load(self, pack_name):
        pack = load_pack(pack_name)
        assert pack.name == pack_name
        assert pack.perspective
        assert pack.tone

    def test_raises_on_unknown_pack(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_pack("nonexistent-pack")


class TestLoadCustomPack:
    def test_loads_from_yaml_file(self, tmp_path):
        pack_file = tmp_path / "my-pack.yaml"
        pack_file.write_text(
            yaml.dump(
                {
                    "name": "my-pack",
                    "perspective": "A test perspective",
                    "tone": "testing tone",
                    "focus_areas": ["area1", "area2"],
                    "heuristics": ["heuristic one", "heuristic two"],
                    "example_questions": ["Question 1?"],
                    "communication_style": "Be clear.",
                    "description": "Test pack",
                }
            )
        )
        pack = load_pack(str(pack_file))
        assert pack.name == "my-pack"
        assert pack.perspective == "A test perspective"
        assert pack.heuristics == ["heuristic one", "heuristic two"]

    def test_loads_with_missing_optional_fields(self, tmp_path):
        pack_file = tmp_path / "minimal.yaml"
        pack_file.write_text(yaml.dump({"name": "minimal", "perspective": "Min", "tone": "calm"}))
        pack = load_pack(str(pack_file))
        assert pack.heuristics == []
        assert pack.communication_style == ""

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_pack("/nonexistent/path/pack.yaml")

    def test_uses_stem_as_name_if_name_not_in_yaml(self, tmp_path):
        pack_file = tmp_path / "auto-named.yaml"
        pack_file.write_text(yaml.dump({"perspective": "Some", "tone": "direct"}))
        pack = load_pack(str(pack_file))
        assert pack.name == "auto-named"


class TestListBuiltinPacks:
    def test_returns_list(self):
        packs = list_builtin_packs()
        assert isinstance(packs, list)
        assert len(packs) > 0

    def test_includes_expected_packs(self):
        packs = list_builtin_packs()
        for expected in BUILTIN_PACK_NAMES:
            assert expected in packs


class TestListInstalledPacks:
    def test_returns_empty_when_no_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr("staff_review.packs.PACK_CACHE_DIR", tmp_path / "empty-packs")
        result = list_installed_packs()
        assert result == []

    def test_finds_cached_packs(self, tmp_path, monkeypatch):
        cache = tmp_path / "packs"
        source_dir = cache / "test__source"
        source_dir.mkdir(parents=True)
        pack_file = source_dir / "my-cached-pack.yaml"
        pack_file.write_text(
            yaml.dump(
                {
                    "name": "my-cached-pack",
                    "perspective": "Cached perspective",
                    "tone": "calm",
                    "description": "A cached test pack",
                }
            )
        )
        monkeypatch.setattr("staff_review.packs.PACK_CACHE_DIR", cache)

        result = list_installed_packs()
        assert len(result) == 1
        assert result[0]["name"] == "my-cached-pack"
        assert result[0]["source"] == "test__source"


class TestSourceSlug:
    def test_github_source(self):
        slug = _source_slug("github:owner/repo")
        assert "owner" in slug
        assert "repo" in slug
        assert "/" not in slug

    def test_url_source(self):
        slug = _source_slug("https://example.com/packs/my-pack.yaml")
        assert "/" not in slug
        assert len(slug) < 80

    def test_long_source_truncated(self):
        long = "github:" + "a" * 100 + "/" + "b" * 100
        slug = _source_slug(long)
        assert len(slug) <= 64


class TestContentPackPromptFragment:
    def test_fragment_includes_perspective(self):
        pack = load_pack("staff-core")
        fragment = pack.to_system_prompt_fragment()
        assert pack.perspective[:20] in fragment

    def test_fragment_includes_heuristics(self):
        pack = load_pack("staff-core")
        fragment = pack.to_system_prompt_fragment()
        assert any(h[:20] in fragment for h in pack.heuristics)

    def test_fragment_includes_tone(self):
        pack = load_pack("staff-core")
        fragment = pack.to_system_prompt_fragment()
        assert pack.tone[:10] in fragment


class TestGitHubPackInstallation:
    """Test GitHub pack installation logic."""

    def test_install_from_github_single_file(self, monkeypatch):
        """Test installing a single pack file from GitHub."""
        from unittest.mock import MagicMock, patch

        from staff_review.packs import _install_github_source

        mock_pack = MagicMock()
        mock_pack.name = "test-pack"

        with patch("staff_review.packs._load_github_pack", return_value=mock_pack):
            result = _install_github_source("owner/repo/path/pack.yaml")
            assert len(result) == 1
            assert result[0] == mock_pack

    def test_install_from_github_directory(self, monkeypatch):
        """Test installing multiple packs from GitHub directory."""
        from unittest.mock import MagicMock, patch

        from staff_review.packs import _install_github_source

        # Mock GitHub API response
        mock_contents = [
            {"name": "pack1.yaml", "download_url": "https://raw.../pack1.yaml"},
            {"name": "pack2.yaml", "download_url": "https://raw.../pack2.yaml"},
            {"name": "README.md", "download_url": "https://raw.../README.md"},  # Should skip
        ]

        mock_pack1 = MagicMock()
        mock_pack1.name = "pack1"
        mock_pack2 = MagicMock()
        mock_pack2.name = "pack2"

        with patch("staff_review.packs._fetch_json", return_value=mock_contents):
            with patch("staff_review.packs._load_url_pack", side_effect=[mock_pack1, mock_pack2]):
                result = _install_github_source("owner/repo")
                assert len(result) == 2
                assert result[0].name == "pack1"
                assert result[1].name == "pack2"

    def test_install_from_github_invalid_spec(self):
        """Test that invalid GitHub spec raises error."""
        import pytest

        from staff_review.packs import _install_github_source

        with pytest.raises(ValueError, match="Invalid GitHub source"):
            _install_github_source("invalid")

    def test_install_from_github_api_error(self, monkeypatch):
        """Test handling of GitHub API errors."""
        from unittest.mock import patch

        import pytest

        from staff_review.packs import _install_github_source

        with patch("staff_review.packs._fetch_json", side_effect=Exception("API error")):
            with pytest.raises(FileNotFoundError, match="Could not list"):
                _install_github_source("owner/repo")

    def test_install_from_github_no_yaml_files(self, monkeypatch):
        """Test error when no yaml files found in directory."""
        from unittest.mock import patch

        import pytest

        from staff_review.packs import _install_github_source

        # Mock GitHub API response with no YAML files
        mock_contents = [
            {"name": "README.md", "download_url": "https://raw.../README.md"},
        ]

        with patch("staff_review.packs._fetch_json", return_value=mock_contents):
            with pytest.raises(FileNotFoundError, match="No .yaml files found"):
                _install_github_source("owner/repo")
