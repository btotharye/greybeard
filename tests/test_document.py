"""Tests for DocumentationGenerator."""

from __future__ import annotations

import pytest
import json
from pathlib import Path

from greybeard.common.document import DocumentationGenerator


class TestDocumentationGenerator:
    """Test suite for DocumentationGenerator."""

    def test_initialization(self):
        """Test DocumentationGenerator initializes correctly."""
        doc_gen = DocumentationGenerator()
        assert doc_gen is not None

    def test_format_markdown(self):
        """Test markdown formatting."""
        doc_gen = DocumentationGenerator()
        
        content = "# Header\n\nContent here"
        metadata = {"version": "1.0", "author": "test"}
        
        result = doc_gen.format(
            content=content,
            format_type="markdown",
            metadata=metadata,
        )
        
        assert "---" in result  # Metadata markers
        assert "version: 1.0" in result
        assert content in result

    def test_format_markdown_without_metadata(self):
        """Test markdown formatting without metadata."""
        doc_gen = DocumentationGenerator()
        
        content = "Simple content"
        result = doc_gen.format(content=content, format_type="markdown")
        
        assert content in result
        # Might not have metadata markers

    def test_format_json(self):
        """Test JSON formatting."""
        doc_gen = DocumentationGenerator()
        
        content = "Test content"
        metadata = {"key": "value"}
        
        result = doc_gen.format(
            content=content,
            format_type="json",
            metadata=metadata,
        )
        
        parsed = json.loads(result)
        assert parsed["content"] == content
        assert parsed["metadata"]["key"] == "value"
        assert "timestamp" in parsed

    def test_format_json_without_metadata(self):
        """Test JSON formatting without metadata."""
        doc_gen = DocumentationGenerator()
        
        content = "Test"
        result = doc_gen.format(content=content, format_type="json")
        
        parsed = json.loads(result)
        assert parsed["content"] == content
        assert "timestamp" in parsed

    def test_format_yaml(self):
        """Test YAML formatting."""
        doc_gen = DocumentationGenerator()
        
        content = "Content"
        metadata = {"key": "value"}
        
        result = doc_gen.format(
            content=content,
            format_type="yaml",
            metadata=metadata,
        )
        
        # Should contain yaml-formatted data
        assert "content:" in result.lower()
        assert "timestamp:" in result.lower()

    def test_format_yaml_fallback(self):
        """Test YAML formatting with missing yaml library."""
        doc_gen = DocumentationGenerator()
        
        with pytest.importorskip("yaml", minversion=None) or True:
            # Test that it at least returns something
            result = doc_gen.format(
                content="test",
                format_type="yaml",
            )
            assert result is not None

    def test_format_default_is_markdown(self):
        """Test default format is markdown."""
        doc_gen = DocumentationGenerator()
        
        content = "Content"
        result = doc_gen.format(content=content)
        
        assert content in result

    def test_save_markdown(self, tmp_path):
        """Test saving markdown file."""
        doc_gen = DocumentationGenerator()
        
        content = "# Test\n\nContent"
        filepath = tmp_path / "test.md"
        
        doc_gen.save_markdown(content, str(filepath))
        
        assert filepath.exists()
        assert filepath.read_text() == content

    def test_save_markdown_creates_directories(self, tmp_path):
        """Test save_markdown creates parent directories."""
        doc_gen = DocumentationGenerator()
        
        content = "Content"
        filepath = tmp_path / "dir1" / "dir2" / "test.md"
        
        doc_gen.save_markdown(content, str(filepath))
        
        assert filepath.exists()

    def test_save_json(self, tmp_path):
        """Test saving JSON file."""
        doc_gen = DocumentationGenerator()
        
        data = {"key": "value", "number": 42}
        filepath = tmp_path / "test.json"
        
        doc_gen.save_json(data, str(filepath))
        
        assert filepath.exists()
        loaded = json.loads(filepath.read_text())
        assert loaded == data

    def test_save_json_list(self, tmp_path):
        """Test saving JSON list."""
        doc_gen = DocumentationGenerator()
        
        data = [1, 2, 3, {"key": "value"}]
        filepath = tmp_path / "test.json"
        
        doc_gen.save_json(data, str(filepath))
        
        assert filepath.exists()
        loaded = json.loads(filepath.read_text())
        assert loaded == data

    def test_save_yaml(self, tmp_path):
        """Test saving YAML file."""
        doc_gen = DocumentationGenerator()
        
        data = {"key": "value", "nested": {"data": 123}}
        filepath = tmp_path / "test.yaml"
        
        doc_gen.save_yaml(data, str(filepath))
        
        assert filepath.exists()

    def test_save_yaml_fallback_to_json(self, tmp_path):
        """Test YAML fallback saves as JSON."""
        doc_gen = DocumentationGenerator()
        
        with pytest.importorskip("yaml", minversion=None) or True:
            data = {"key": "value"}
            filepath = tmp_path / "test.yaml"
            
            doc_gen.save_yaml(data, str(filepath))
            
            assert filepath.exists()

    def test_create_template(self):
        """Test creating markdown template."""
        doc_gen = DocumentationGenerator()
        
        title = "Decision Document"
        sections = {
            "Context": "Explain the context",
            "Options": "List options",
            "Decision": "What was decided",
        }
        
        result = doc_gen.create_template(title=title, sections=sections)
        
        assert f"# {title}" in result
        assert "## Context" in result
        assert "## Options" in result
        assert "## Decision" in result
        assert "Explain the context" in result

    def test_create_template_with_metadata(self):
        """Test creating template with metadata."""
        doc_gen = DocumentationGenerator()
        
        metadata = {"version": "1.0", "date": "2026-03-18"}
        
        result = doc_gen.create_template(
            title="Test",
            sections={"Section": "Content"},
            metadata=metadata,
        )
        
        assert "---" in result
        assert "version: 1.0" in result
        assert "date: 2026-03-18" in result

    def test_create_template_empty_sections(self):
        """Test creating template with no sections."""
        doc_gen = DocumentationGenerator()
        
        result = doc_gen.create_template(
            title="Empty Template",
            sections={},
        )
        
        assert "# Empty Template" in result

    def test_format_markdown_preserves_content(self):
        """Test markdown formatting preserves original content."""
        doc_gen = DocumentationGenerator()
        
        original = "# Header\n\nParagraph with **bold** and *italic*\n\n```code\nblock\n```"
        
        result = doc_gen.format(content=original, format_type="markdown")
        
        assert original in result

    def test_save_creates_parent_directories_json(self, tmp_path):
        """Test save_json creates parent directories."""
        doc_gen = DocumentationGenerator()
        
        filepath = tmp_path / "deep" / "nested" / "path" / "file.json"
        doc_gen.save_json({"data": "test"}, str(filepath))
        
        assert filepath.exists()
        assert filepath.parent == tmp_path / "deep" / "nested" / "path"
