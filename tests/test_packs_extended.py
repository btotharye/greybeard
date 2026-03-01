"""Extended tests for pack source management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestPackSourceManagement:
    """Test pack source installation and removal."""

    def test_install_pack_source_github(self, monkeypatch):
        """Test installing packs from GitHub source."""
        from staff_review.packs import install_pack_source

        mock_pack = MagicMock()
        with patch("staff_review.packs._install_github_source", return_value=[mock_pack]):
            result = install_pack_source("github:owner/repo")
            assert len(result) == 1

    def test_install_pack_source_url(self, monkeypatch):
        """Test installing pack from URL."""
        from staff_review.packs import install_pack_source

        mock_pack = MagicMock()
        with patch("staff_review.packs._load_url_pack", return_value=mock_pack):
            result = install_pack_source("https://example.com/pack.yaml")
            assert len(result) == 1

    def test_install_pack_source_invalid_format(self):
        """Test error on invalid source format."""
        from staff_review.packs import install_pack_source

        with pytest.raises(ValueError, match="Unknown source format"):
            install_pack_source("invalid-format")

    def test_remove_pack_source(self, tmp_path, monkeypatch):
        """Test removing a pack source."""
        from staff_review.packs import remove_pack_source

        # Create mock cache directory
        monkeypatch.setattr("staff_review.packs.PACK_CACHE_DIR", tmp_path)

        # Create test pack files
        source_dir = tmp_path / "test-source"
        source_dir.mkdir()
        (source_dir / "pack1.yaml").write_text("name: pack1")
        (source_dir / "pack2.yaml").write_text("name: pack2")

        count = remove_pack_source("test-source")
        assert count == 2
        assert not source_dir.exists()

    def test_remove_pack_source_not_found(self, tmp_path, monkeypatch):
        """Test error when removing non-existent source."""
        from staff_review.packs import remove_pack_source

        monkeypatch.setattr("staff_review.packs.PACK_CACHE_DIR", tmp_path)

        with pytest.raises(FileNotFoundError, match="No cached source"):
            remove_pack_source("nonexistent")

    def test_remove_pack_source_partial_match(self, tmp_path, monkeypatch):
        """Test removing pack source with partial name match."""
        from staff_review.packs import remove_pack_source

        # Create mock cache directory
        monkeypatch.setattr("staff_review.packs.PACK_CACHE_DIR", tmp_path)

        # Create test pack files with longer name
        source_dir = tmp_path / "github-owner-repo-abc123"
        source_dir.mkdir()
        (source_dir / "pack.yaml").write_text("name: pack")

        # Should match by partial name
        count = remove_pack_source("owner-repo")
        assert count == 1
        assert not source_dir.exists()
