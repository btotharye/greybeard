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
    def test_supported_formats_list(self):
        assert set(SUPPORTED_FORMATS) == {"markdown", "json", "html", "jira"}

    def test_format_extensions_coverage(self):
        for fmt in SUPPORTED_FORMATS:
            assert fmt in FORMAT_EXTENSIONS
            assert FORMAT_EXTENSIONS[fmt].startswith(".")


# ---------------------------------------------------------------------------
# convert() dispatch
# ---------------------------------------------------------------------------


class TestConvertDispatch:
    def test_markdown_passthrough(self, meta):
        result = convert("# Hello\n\nworld", "markdown", meta)
        assert result == "# Hello\n\nworld"

    def test_json_dispatch(self, meta):
        result = convert(SAMPLE_MARKDOWN, "json", meta)
        data = json.loads(result)
        assert data["format_version"] == "1.0"

    def test_html_dispatch(self, meta):
        result = convert(SAMPLE_MARKDOWN, "html", meta)
        assert "<!DOCTYPE html>" in result

    def test_jira_dispatch(self, meta):
        result = convert(SAMPLE_MARKDOWN, "jira", meta)
        assert "h1." in result or "h2." in result

    def test_invalid_format_raises(self, meta):
        with pytest.raises(ValueError, match="Unsupported format"):
            convert("text", "xml", meta)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _parse_sections
# ---------------------------------------------------------------------------


class TestParseSections:
    def test_extracts_summary(self):
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "summary" in sections
        assert "mid-sprint" in sections["summary"]

    def test_extracts_key_risks(self):
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "key_risks" in sections
        assert "rollback" in sections["key_risks"]

    def test_extracts_tradeoffs(self):
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "tradeoffs" in sections
        assert "Speed" in sections["tradeoffs"]

    def test_extracts_questions(self):
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "questions" in sections
        assert "rollback" in sections["questions"]

    def test_extracts_communication_language(self):
        sections = _parse_sections(SAMPLE_MARKDOWN)
        assert "communication_language" in sections
        assert "framing" in sections["communication_language"]

    def test_empty_markdown_returns_empty_dict(self):
        sections = _parse_sections("")
        assert sections == {}

    def test_missing_section_not_in_dict(self):
        md = "## Summary\n\nJust a summary.\n"
        sections = _parse_sections(md)
        assert "summary" in sections
        assert "key_risks" not in sections


# ---------------------------------------------------------------------------
# _parse_bullets
# ---------------------------------------------------------------------------


class TestParseBullets:
    def test_dash_bullets(self):
        text = "- Item one\n- Item two\n- Item three"
        result = _parse_bullets(text)
        assert result == ["Item one", "Item two", "Item three"]

    def test_star_bullets(self):
        text = "* Alpha\n* Beta"
        result = _parse_bullets(text)
        assert result == ["Alpha", "Beta"]

    def test_numbered_list(self):
        text = "1. First\n2. Second\n3. Third"
        result = _parse_bullets(text)
        assert result == ["First", "Second", "Third"]

    def test_non_list_returns_text_wrapped(self):
        text = "Some prose paragraph."
        result = _parse_bullets(text)
        assert result == ["Some prose paragraph."]

    def test_empty_text_returns_empty(self):
        assert _parse_bullets("") == []


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


class TestJsonOutput:
    def test_valid_json(self, meta):
        result = _to_json(SAMPLE_MARKDOWN, meta)
        data = json.loads(result)  # must not raise
        assert isinstance(data, dict)

    def test_metadata_fields(self, meta):
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        assert data["mode"] == "review"
        assert data["pack"] == "staff-core"
        assert data["backend"] == "openai"
        assert data["model"] == "gpt-4o"
        assert data["generated_at"] == "2026-03-17T10:00:00Z"
        assert data["format_version"] == "1.0"

    def test_sections_present(self, meta):
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        sections = data["sections"]
        assert "summary" in sections
        assert "key_risks" in sections
        assert "tradeoffs" in sections
        assert "questions" in sections
        assert "communication_language" in sections

    def test_key_risks_is_list(self, meta):
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        assert isinstance(data["sections"]["key_risks"], list)
        assert len(data["sections"]["key_risks"]) >= 1

    def test_questions_is_list(self, meta):
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        assert isinstance(data["sections"]["questions"], list)

    def test_raw_markdown_preserved(self, meta):
        data = json.loads(_to_json(SAMPLE_MARKDOWN, meta))
        assert data["raw_markdown"] == SAMPLE_MARKDOWN

    def test_empty_markdown(self, meta):
        data = json.loads(_to_json("", meta))
        assert data["sections"]["summary"] == ""
        assert data["raw_markdown"] == ""


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------


class TestHtmlOutput:
    def test_doctype(self, meta):
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert result.startswith("<!DOCTYPE html>")

    def test_title_contains_mode_and_pack(self, meta):
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "review" in result
        assert "staff-core" in result

    def test_metadata_in_header(self, meta):
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "gpt-4o" in result
        assert "2026-03-17T10:00:00Z" in result

    def test_headings_converted(self, meta):
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "<h2>" in result

    def test_bullet_list_converted(self, meta):
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "<ul>" in result
        assert "<li>" in result

    def test_hr_converted(self, meta):
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "<hr" in result

    def test_valid_html_structure(self, meta):
        result = _to_html(SAMPLE_MARKDOWN, meta)
        assert "<html" in result
        assert "</html>" in result
        assert "<body>" in result
        assert "</body>" in result


class TestMdToHtmlBody:
    def test_h1(self):
        assert "<h1>Hello</h1>" in _md_to_html_body("# Hello")

    def test_h2(self):
        assert "<h2>Section</h2>" in _md_to_html_body("## Section")

    def test_bold(self):
        result = _md_to_html_body("**bold text**")
        assert "<strong>bold text</strong>" in result

    def test_italic(self):
        result = _md_to_html_body("*italic text*")
        assert "<em>italic text</em>" in result

    def test_inline_code(self):
        result = _md_to_html_body("`some code`")
        assert "<code>some code</code>" in result

    def test_fenced_code_block(self):
        result = _md_to_html_body("```python\nprint('hello')\n```")
        assert "<pre>" in result
        assert "<code" in result
        assert "print" in result

    def test_unordered_list(self):
        result = _md_to_html_body("- item one\n- item two")
        assert "<ul>" in result
        assert "<li>item one</li>" in result

    def test_ordered_list(self):
        result = _md_to_html_body("1. first\n2. second")
        assert "<ol>" in result
        assert "<li>first</li>" in result

    def test_horizontal_rule(self):
        assert "<hr" in _md_to_html_body("---")

    def test_blockquote(self):
        result = _md_to_html_body("> a quote")
        assert "<blockquote>" in result

    def test_html_entities_escaped(self):
        result = _md_to_html_body("x < y & z > w")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result

    def test_link(self):
        result = _md_to_html_body("[click here](https://example.com)")
        assert '<a href="https://example.com">click here</a>' in result


# ---------------------------------------------------------------------------
# Jira output
# ---------------------------------------------------------------------------


class TestJiraOutput:
    def test_header_banner(self, meta):
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "h1. 🧙 greybeard review" in result

    def test_metadata_table(self, meta):
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "||Mode||" in result
        assert "|review|" in result

    def test_h2_converted(self, meta):
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "h2. Summary" in result

    def test_bullet_list_converted(self, meta):
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "* No rollback plan documented" in result

    def test_numbered_list_converted(self, meta):
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "# What does rollback look like" in result

    def test_hr_converted(self, meta):
        result = _to_jira(SAMPLE_MARKDOWN, meta)
        assert "----" in result

    def test_code_block_converted(self):
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
    def test_bold(self):
        assert _md_inline_to_jira("**bold**") == "*bold*"

    def test_italic(self):
        assert _md_inline_to_jira("*italic*") == "_italic_"

    def test_inline_code(self):
        assert _md_inline_to_jira("`code`") == "{{code}}"

    def test_link(self):
        assert _md_inline_to_jira("[label](https://example.com)") == "[label|https://example.com]"

    def test_bold_italic(self):
        result = _md_inline_to_jira("***both***")
        assert "*_both_*" in result

    def test_plain_text_unchanged(self):
        assert _md_inline_to_jira("plain text") == "plain text"


# ---------------------------------------------------------------------------
# CLI integration: _resolve_output_path
# ---------------------------------------------------------------------------


class TestResolveOutputPath:
    def test_none_returns_none(self):
        from greybeard.cli import _resolve_output_path

        assert _resolve_output_path(None, "json") is None

    def test_no_extension_appended(self):
        from greybeard.cli import _resolve_output_path

        assert _resolve_output_path("review", "json") == "review.json"
        assert _resolve_output_path("review", "html") == "review.html"
        assert _resolve_output_path("review", "jira") == "review.txt"
        assert _resolve_output_path("review", "markdown") == "review.md"

    def test_existing_extension_preserved(self):
        from greybeard.cli import _resolve_output_path

        assert _resolve_output_path("review.json", "json") == "review.json"
        assert _resolve_output_path("output.html", "html") == "output.html"


# ---------------------------------------------------------------------------
# CLI flag smoke tests
# ---------------------------------------------------------------------------


class TestCliFormatFlag:
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
