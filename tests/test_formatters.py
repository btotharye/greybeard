"""Tests for the output format converters."""

from __future__ import annotations

import json

import pytest

from greybeard.formatters import (
    FORMAT_EXTENSIONS,
    SUPPORTED_FORMATS,
    ReviewMetadata,
    _md_inline_to_jira,
    _md_to_html_body,
    _parse_bullets,
    _parse_sections,
    _to_html,
    _to_jira,
    _to_json,
    convert,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MARKDOWN = """\
## Summary

This is a mid-sprint database migration with high operational risk.

## Key Risks

- No rollback plan documented
- Migration touches 3 high-traffic tables
- No dry-run results shared

## Tradeoffs

Speed vs safety. Shipping now saves a sprint, but risk of 3am incident is real.

## Questions to Answer Before Proceeding

1. What does rollback look like if the migration fails at step 3?
2. Have you run EXPLAIN on the ALTER TABLE statements?

## Suggested Communication Language

Consider framing this as: ("We have a path forward, but want to share the "
    "risk profile before proceeding.")

---
*Assumed: production traffic is non-trivial.*
"""


@pytest.fixture
def meta() -> ReviewMetadata:
    """Fixture: ReviewMetadata for testing."""
    return ReviewMetadata(
        mode="review",
        pack_name="staff-core",
        backend="openai",
        model="gpt-4o",
        generated_at="2026-03-17T10:00:00Z",
    )


# ---------------------------------------------------------------------------
# SUPPORTED_FORMATS / FORMAT_EXTENSIONS
# ---------------------------------------------------------------------------


class TestFormatConstants:
    """Test Format Constants."""

    def test_supported_formats_list(self):
        """Test supported formats list."""
        assert set(SUPPORTED_FORMATS) == {"markdown", "json", "html", "jira"}

    def test_format_extensions_coverage(self):
        """Test format extensions coverage."""
        for fmt in SUPPORTED_FORMATS:
            assert fmt in FORMAT_EXTENSIONS
            assert FORMAT_EXTENSIONS[fmt].startswith(".")


# ---------------------------------------------------------------------------
# convert() dispatch
# ---------------------------------------------------------------------------


class TestConvertDispatch:
    """Test Convert Dispatch."""

    def test_markdown_passthrough(self, meta):
        """Test markdown passthrough."""
        result = convert("# Hello\n\nworld", "markdown", meta)
        assert result == "# Hello\n\nworld"

    def test_json_dispatch(self, meta):
        """Test json dispatch."""
        result = convert(SAMPLE_MARKDOWN, "json", meta)
        data = json.loads(result)
        assert data["format_version"] == "1.0"

    def test_html_dispatch(self, meta):
        """Test html dispatch."""
        result = convert(SAMPLE_MARKDOWN, "html", meta)
        assert "<!DOCTYPE html>" in result

    def test_jira_dispatch(self, meta):
        """Test jira dispatch."""
        result = convert(SAMPLE_MARKDOWN, "jira", meta)
        assert "h1." in result or "h2." in result

    def test_invalid_format_raises(self, meta):
        """Test invalid format raises."""
        with pytest.raises(ValueError, match="Unsupported format"):
            convert("text", "xml", meta)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _parse_sections
# ---------------------------------------------------------------------------


class TestParseSections:
    """Test Parse Sections."""

    def test_extracts_summary(self):
        """Test extracts summary."""
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "summary" in sections
        assert "mid-sprint" in sections["summary"]

    def test_extracts_key_risks(self):
        """Test extracts key risks."""
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "key_risks" in sections
        assert "rollback" in sections["key_risks"]

    def test_extracts_tradeoffs(self):
        """Test extracts tradeoffs."""
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "tradeoffs" in sections
        assert "Speed" in sections["tradeoffs"]

    def test_extracts_questions(self):
        """Test extracts questions."""
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "questions" in sections
        assert "rollback" in sections["questions"]

    def test_extracts_communication_language(self):
        """Test extracts communication language."""
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "communication_language" in sections
        assert "framing" in sections["communication_language"]

    def test_empty_markdown_returns_empty_dict(self):
        """Test empty markdown returns empty dict."""
        sections = _parse_sections("")
        assert sections == {}

    def test_missing_section_not_in_dict(self):
        """Test missing section not in dict."""
        md = "## Summary\n\nJust a summary.\n"
        sections = _parse_sections(md)
        assert "summary" in sections
        assert "key_risks" not in sections


# ---------------------------------------------------------------------------
# _parse_bullets
# ---------------------------------------------------------------------------


class TestParseBullets:
    """Test Parse Bullets."""

    def test_dash_bullets(self):
        """Test dash bullets."""
        text = "- Item one\n- Item two\n- Item three"
        result = _parse_bullets(text)
        assert result == ["Item one", "Item two", "Item three"]

    def test_star_bullets(self):
        """Test star bullets."""
        text = "* Alpha\n* Beta"
        result = _parse_bullets(text)
        assert result == ["Alpha", "Beta"]

    def test_numbered_list(self):
        """Test numbered list."""
        text = "1. First\n2. Second\n3. Third"
        result = _parse_bullets(text)
        assert result == ["First", "Second", "Third"]

    def test_non_list_returns_text_wrapped(self):
        """Test non list returns text wrapped."""
        text = "Some prose paragraph."
        result = _parse_bullets(text)
        assert result == ["Some prose paragraph."]

    def test_empty_text_returns_empty(self):
        """Test empty text returns empty."""
        assert _parse_bullets("") == []


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


class TestJsonOutput:
    """Test Json Output."""

    def test_valid_json(self, meta):
        """Test valid json."""
        result = _to_json(SAMPLE_MARKDOWN, meta)
        data = json.loads(result)  # must not raise
        assert isinstance(data, dict)

    def test_metadata_fields(self, meta):
        """Test metadata fields."""
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        assert data["mode"] == "review"
        assert data["pack"] == "staff-core"
        assert data["backend"] == "openai"
        assert data["model"] == "gpt-4o"
        assert data["generated_at"] == "2026-03-17T10:00:00Z"
        assert data["format_version"] == "1.0"

    def test_sections_present(self, meta):
        """Test sections present."""
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        sections = data["sections"]
        assert "summary" in sections
        assert "key_risks" in sections
        assert "tradeoffs" in sections
        assert "questions" in sections
        assert "communication_language" in sections

    def test_key_risks_is_list(self, meta):
        """Test key risks is list."""
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        assert isinstance(data["sections"]["key_risks"], list)
        assert len(data["sections"]["key_risks"]) >= 1

    def test_questions_is_list(self, meta):
        """Test questions is list."""
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        assert isinstance(data["sections"]["questions"], list)

    def test_raw_markdown_preserved(self, meta):
        """Test raw markdown preserved."""
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        assert data["raw_markdown"] == SAMPLE_MARKDOWN

    def test_empty_markdown(self, meta):
        """Test empty markdown."""
        data = json.loads(_to_json("", meta))
        assert data["sections"]["summary"] == ""
        assert data["raw_markdown"] == ""


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------


class TestHtmlOutput:
    """Test Html Output."""

    def test_doctype(self, meta):
        """Test doctype."""
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert result.startswith("<!DOCTYPE html>")

    def test_title_contains_mode_and_pack(self, meta):
        """Test title contains mode and pack."""
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "review" in result
        assert "staff-core" in result

    def test_metadata_in_header(self, meta):
        """Test metadata in header."""
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "gpt-4o" in result
        assert "2026-03-17T10:00:00Z" in result

    def test_headings_converted(self, meta):
        """Test headings converted."""
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "<h2>" in result

    def test_bullet_list_converted(self, meta):
        """Test bullet list converted."""
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "<ul>" in result
        assert "<li>" in result

    def test_hr_converted(self, meta):
        """Test hr converted."""
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "<hr" in result

    def test_valid_html_structure(self, meta):
        """Test valid html structure."""
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "<html" in result
        assert "</html>" in result
        assert "<body>" in result
        assert "</body>" in result


class TestMdToHtmlBody:
    """Test Md To Html Body."""

    def test_h1(self):
        """Test h1."""
        assert "<h1>Hello</h1>" in _md_to_html_body("# Hello")

    def test_h2(self):
        """Test h2."""
        assert "<h2>Section</h2>" in _md_to_html_body("## Section")

    def test_bold(self):
        """Test bold."""
        result = _md_to_html_body("**bold text**")
        assert "<strong>bold text</strong>" in result

    def test_italic(self):
        """Test italic."""
        result = _md_to_html_body("*italic text*")
        assert "<em>italic text</em>" in result

    def test_inline_code(self):
        """Test inline code."""
        result = _md_to_html_body("`some code`")
        assert "<code>some code</code>" in result

    def test_fenced_code_block(self):
        """Test fenced code block."""
        result = _md_to_html_body("```python\nprint('hello')\n```")
        assert "<pre>" in result
        assert "<code" in result
        assert "print" in result

    def test_unordered_list(self):
        """Test unordered list."""
        result = _md_to_html_body("- item one\n- item two")
        assert "<ul>" in result
        assert "<li>item one</li>" in result

    def test_ordered_list(self):
        """Test ordered list."""
        result = _md_to_html_body("1. first\n2. second")
        assert "<ol>" in result
        assert "<li>first</li>" in result

    def test_horizontal_rule(self):
        """Test horizontal rule."""
        assert "<hr" in _md_to_html_body("---")

    def test_blockquote(self):
        """Test blockquote."""
        result = _md_to_html_body("> a quote")
        assert "<blockquote>" in result

    def test_html_entities_escaped(self):
        """Test html entities escaped."""
        result = _md_to_html_body("x < y & z > w")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result

    def test_link(self):
        """Test link."""
        result = _md_to_html_body("[click here](https://example.com)")
        assert '<a href="https://example.com">click here</a>' in result

    def test_nested_unordered_list(self):
        """Test that indented bullet points render as nested lists."""
        md = "- Item 1\n  - Sub-item 1a\n  - Sub-item 1b\n- Item 2"
        result = _md_to_html_body(md)
        # Should have nested <ul> elements
        assert "<ul>" in result and "</ul>" in result
        assert "<li>Item 1</li>" in result
        assert "<li>Sub-item 1a</li>" in result
        assert "<li>Sub-item 1b</li>" in result
        assert "<li>Item 2</li>" in result
        # Verify proper nesting (nested lists should appear)
        assert "<ul>\n<li>Sub-item 1a</li>" in result

    def test_nested_ordered_list(self):
        """Test that indented numbered items render as nested lists."""
        md = "1. First\n   1. Sub-first\n   2. Sub-second\n2. Second"
        result = _md_to_html_body(md)
        # Should have nested <ol> elements
        assert "<ol>" in result and "</ol>" in result
        assert "<li>First</li>" in result
        assert "<li>Sub-first</li>" in result
        assert "<li>Sub-second</li>" in result
        assert "<li>Second</li>" in result
        # Verify proper nesting
        assert "<ol>\n<li>Sub-first</li>" in result

    def test_mixed_nested_lists(self):
        """Test bullet point with indented sub-points (real-world use case)."""
        md = (
            "- **Operational Impact**:\n"
            "  - First concern\n"
            "  - Second concern\n"
            "- **Ownership**:\n"
            "  - Who owns this?"
        )
        result = _md_to_html_body(md)
        # Check that nested structure is present
        assert "<strong>Operational Impact</strong>" in result
        assert "<strong>Ownership</strong>" in result
        # Verify nesting
        assert "<li>First concern</li>" in result
        assert "<li>Second concern</li>" in result
        assert "<li>Who owns this?" in result or "<li>Who owns this</li>" in result


# ---------------------------------------------------------------------------
# Jira output
# ---------------------------------------------------------------------------


class TestJiraOutput:
    """Test Jira Output."""

    def test_header_banner(self, meta):
        """Test header banner."""
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "h1. 🧙 greybeard review" in result

    def test_metadata_table(self, meta):
        """Test metadata table."""
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "||Mode||" in result
        assert "|review|" in result

    def test_h2_converted(self, meta):
        """Test h2 converted."""
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "h2. Summary" in result

    def test_bullet_list_converted(self, meta):
        """Test bullet list converted."""
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "* No rollback plan documented" in result

    def test_numbered_list_converted(self, meta):
        """Test numbered list converted."""
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "# What does rollback look like" in result

    def test_hr_converted(self, meta):
        """Test hr converted."""
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "----" in result

    def test_code_block_converted(self):
        """Test code block converted."""
        md = "```python\nprint('hi')\n```"
        meta = ReviewMetadata(
            mode="review",
            pack_name="staff-core",
            backend="openai",
            model="gpt-4o",
        )
        result = _to_jira(md, meta)
        assert "{code:python}" in result
        assert "{code}" in result


class TestMdInlineToJira:
    """Test Md Inline To Jira."""

    def test_bold(self):
        """Test bold."""
        assert _md_inline_to_jira("**bold**") == "*bold*"

    def test_italic(self):
        """Test italic."""
        assert _md_inline_to_jira("*italic*") == "_italic_"

    def test_inline_code(self):
        """Test inline code."""
        assert _md_inline_to_jira("`code`") == "{{code}}"

    def test_link(self):
        """Test link."""
        assert _md_inline_to_jira("[label](https://example.com)") == "[label|https://example.com]"

    def test_bold_italic(self):
        """Test bold italic."""
        result = _md_inline_to_jira("***both***")
        assert "*_both_*" in result

    def test_plain_text_unchanged(self):
        """Test plain text unchanged."""
        assert _md_inline_to_jira("plain text") == "plain text"


# ---------------------------------------------------------------------------
# CLI integration: _resolve_output_path
# ---------------------------------------------------------------------------


class TestResolveOutputPath:
    """Test Resolve Output Path."""

    def test_none_returns_none(self):
        """Test none returns none."""
        from greybeard.cli import _resolve_output_path

        assert _resolve_output_path(None, "json") is None

    def test_no_extension_appended(self):
        """Test no extension appended."""
        from greybeard.cli import _resolve_output_path

        assert _resolve_output_path("review", "json") == "review.json"
        assert _resolve_output_path("review", "html") == "review.html"
        assert _resolve_output_path("review", "jira") == "review.txt"
        assert _resolve_output_path("review", "markdown") == "review.md"

    def test_existing_extension_preserved(self):
        """Test existing extension preserved."""
        from greybeard.cli import _resolve_output_path

        assert _resolve_output_path("review.json", "json") == "review.json"
        assert _resolve_output_path("output.html", "html") == "output.html"


# ---------------------------------------------------------------------------
# CLI flag smoke tests
# ---------------------------------------------------------------------------


class TestCliFormatFlag:
    """Test Cli Format Flag."""

    def test_analyze_format_choices(self):
        """Verify --format is accepted by analyze command."""
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from greybeard.cli import cli

        runner = CliRunner()
        with (
            patch("greybeard.cli.GreybeardConfig") as mock_cfg_cls,
            patch("greybeard.cli.run_review") as mock_review,
            patch("greybeard.cli._read_stdin_if_available") as mock_stdin,
        ):
            cfg = MagicMock()
            cfg.llm.backend = "openai"
            cfg.llm.resolved_model.return_value = "gpt-4o"
            cfg.default_mode = "review"
            cfg.default_pack = "staff-core"
            mock_cfg_cls.load.return_value = cfg
            mock_stdin.return_value = "some diff content"
            mock_review.return_value = SAMPLE_MARKDOWN

            for fmt in SUPPORTED_FORMATS:
                result = runner.invoke(cli, ["analyze", "--format", fmt])
                assert result.exit_code == 0, f"format={fmt} failed: {result.output}"

    def test_analyze_invalid_format_rejected(self):
        """Verify an invalid format value is rejected by Click."""
        from click.testing import CliRunner

        from greybeard.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--format", "xml"])
        assert result.exit_code != 0
        assert "xml" in result.output or "invalid" in result.output.lower()

    def test_json_format_not_streaming(self):
        """Non-markdown formats should pass stream=False to run_review."""
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from greybeard.cli import cli

        runner = CliRunner()
        with (
            patch("greybeard.cli.GreybeardConfig") as mock_cfg_cls,
            patch("greybeard.cli.run_review") as mock_review,
            patch("greybeard.cli._read_stdin_if_available") as mock_stdin,
        ):
            cfg = MagicMock()
            cfg.llm.backend = "openai"
            cfg.llm.resolved_model.return_value = "gpt-4o"
            cfg.default_mode = "review"
            cfg.default_pack = "staff-core"
            mock_cfg_cls.load.return_value = cfg
            mock_stdin.return_value = "some content"
            mock_review.return_value = SAMPLE_MARKDOWN

            runner.invoke(cli, ["analyze", "--format", "json"])
            _, kwargs = mock_review.call_args
            assert kwargs.get("stream") is False or mock_review.call_args[1].get("stream") is False
