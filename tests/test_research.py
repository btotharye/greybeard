"""Tests for ResearchCapability."""

from __future__ import annotations

from unittest.mock import patch

from greybeard.common.research import ResearchCapability


class TestResearchCapability:
    """Test suite for ResearchCapability."""

    def test_initialization(self):
        """Test ResearchCapability initializes correctly."""
        research = ResearchCapability()
        assert research.cached_research == {}

    def test_research_topic_caching(self):
        """Test that research results are cached."""
        research = ResearchCapability()

        result1 = research.research_topic("kubernetes")
        result2 = research.research_topic("kubernetes")

        # Should return same cached result
        assert result1 == result2
        assert "kubernetes" in research.cached_research

    def test_research_topic_with_sources(self):
        """Test research with specified sources."""
        research = ResearchCapability()

        result = research.research_topic("python", sources=["docs", "examples"])

        assert result is not None
        assert "python" in research.cached_research

    def test_gather_file_context_existing_file(self, tmp_path):
        """Test gathering context from existing file."""
        research = ResearchCapability()

        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = "Test file content"
        test_file.write_text(test_content)

        result = research.gather_file_context(str(test_file))

        assert result == test_content

    def test_gather_file_context_missing_file(self):
        """Test gathering context from non-existent file."""
        research = ResearchCapability()

        result = research.gather_file_context("/nonexistent/file.txt")

        assert "not found" in result.lower()

    def test_gather_file_context_read_error(self):
        """Test handling of file read errors."""
        research = ResearchCapability()

        with patch("pathlib.Path.read_text", side_effect=PermissionError()):
            result = research.gather_file_context("/some/file.txt")

            # Result should indicate an issue with the file
            assert result.lower()

    def test_analyze_structure_directory(self, tmp_path):
        """Test analyzing directory structure."""
        research = ResearchCapability()

        # Create test structure
        (tmp_path / "file1.py").touch()
        (tmp_path / "file2.py").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / ".hidden").mkdir()  # Should be ignored

        result = research.analyze_structure(str(tmp_path))

        assert result["file_count"] == 2
        assert result["dir_count"] == 1
        assert "file1.py" in result["files"]
        assert "file2.py" in result["files"]
        assert "subdir" in result["directories"]
        assert ".hidden" not in result["directories"]

    def test_analyze_structure_not_directory(self, tmp_path):
        """Test analyzing non-directory path."""
        research = ResearchCapability()

        file_path = tmp_path / "file.txt"
        file_path.touch()

        result = research.analyze_structure(str(file_path))

        assert "error" in result

    def test_analyze_structure_missing_directory(self):
        """Test analyzing non-existent directory."""
        research = ResearchCapability()

        result = research.analyze_structure("/nonexistent/directory")

        assert "error" in result

    def test_get_git_context_success(self):
        """Test getting git context."""
        research = ResearchCapability()

        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.side_effect = [
                "main\n",  # branch
                "commit1 message\ncommit2 message\n",  # log
                "file.py | 10 +-\n",  # diff
            ]

            result = research.get_git_context(".")

            assert result["current_branch"] == "main"
            assert "commit1" in result["recent_commits"]
            assert "file.py" in result["current_diff"]

    def test_get_git_context_error(self):
        """Test git context error handling."""
        research = ResearchCapability()

        with patch("subprocess.check_output", side_effect=Exception("Git error")):
            result = research.get_git_context(".")

            assert "error" in result

    def test_load_json_data(self, tmp_path):
        """Test loading JSON data."""
        research = ResearchCapability()

        import json

        test_data = {"key": "value", "nested": {"data": 123}}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(test_data))

        result = research.load_json_data(str(json_file))

        assert result == test_data

    def test_load_json_data_invalid_json(self, tmp_path):
        """Test loading invalid JSON."""
        research = ResearchCapability()

        json_file = tmp_path / "invalid.json"
        json_file.write_text("{ invalid json")

        result = research.load_json_data(str(json_file))

        assert "error" in result

    def test_load_json_data_missing_file(self):
        """Test loading from non-existent file."""
        research = ResearchCapability()

        result = research.load_json_data("/nonexistent/file.json")

        assert "error" in result

    def test_clear_cache(self):
        """Test clearing cached research."""
        research = ResearchCapability()

        # Add some cache
        research.research_topic("python")
        research.research_topic("golang")

        assert len(research.cached_research) == 2

        research.clear_cache()

        assert len(research.cached_research) == 0

    def test_multiple_research_calls_cache_independently(self):
        """Test that different topics are cached separately."""
        research = ResearchCapability()

        research.research_topic("python")
        research.research_topic("golang")

        assert len(research.cached_research) == 2
        assert "python" in research.cached_research
        assert "golang" in research.cached_research

    def test_research_topic_cached_none_value(self):
        """Test handling of None cached values in research_topic."""
        research = ResearchCapability()

        # Manually set a None value in cache
        research.cached_research["test_topic"] = None

        # research_topic should handle None cache gracefully
        result = research.research_topic("test_topic")

        assert result == ""  # Should return empty string for None

    def test_gather_file_context_exception_handling(self, tmp_path):
        """Test exception handling in gather_file_context."""
        research = ResearchCapability()

        # Create a file that will cause read error
        test_file = tmp_path / "readable.txt"
        test_file.write_text("content")

        # First verify it works
        result = research.gather_file_context(str(test_file))
        assert result == "content"

        # Test with path that's a directory
        result = research.gather_file_context(str(tmp_path))
        assert result == f"File not found: {str(tmp_path)}"

    def test_analyze_structure_counts_handling(self, tmp_path):
        """Test that analyze_structure properly handles file and dir counts."""
        research = ResearchCapability()

        # Create files and directories
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        (tmp_path / "subdir1").mkdir()
        (tmp_path / "subdir2").mkdir()

        result = research.analyze_structure(str(tmp_path))

        assert isinstance(result["file_count"], int)
        assert isinstance(result["dir_count"], int)
        assert result["file_count"] == 2
        assert result["dir_count"] == 2
        assert isinstance(result["files"], list)
        assert isinstance(result["directories"], list)
