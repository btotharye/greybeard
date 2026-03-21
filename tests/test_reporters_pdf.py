"""Tests for the PDF reporter."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

from greybeard.formatters import ReviewMetadata
from greybeard.reporters.pdf import PDFReporter, _check_reportlab, to_pdf

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("reportlab") is None,
    reason="reportlab not installed",
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_MARKDOWN = """\
## Summary

This is a mid-sprint database migration with high operational risk.

## Key Risks

- No rollback plan documented
- Migration touches 3 high-traffic tables
- No dry-run results shared

## Tradeoffs

Speed vs safety. Shipping now saves a sprint, but risk of a 3am incident is real.

## Questions to Answer Before Proceeding

1. What does rollback look like if the migration fails at step 3?
2. Have you run EXPLAIN on the ALTER TABLE statements?

## Suggested Communication Language

Consider framing this as: "We have a path forward, but want to share the risk profile."

---
*Assumed: production traffic is non-trivial.*
"""

MINIMAL_MARKDOWN = "## Summary\n\nAll good\n"


@pytest.fixture
def meta() -> ReviewMetadata:
    """Fixture: ReviewMetadata for testing."""
    return ReviewMetadata(
        mode="review",
        pack_name="staff-core",
        backend="openai",
        model="gpt-4o",
        generated_at="2026-03-21T10:00:00Z",
    )


@pytest.fixture
def reporter(meta) -> PDFReporter:
    """Fixture: PDFReporter instance."""
    return PDFReporter(SAMPLE_MARKDOWN, meta)


@pytest.fixture
def tmp_pdf(tmp_path) -> str:
    """Fixture: path for a temporary PDF file."""
    return str(tmp_path / "test-report.pdf")


# ---------------------------------------------------------------------------
# _check_reportlab
# ---------------------------------------------------------------------------


class TestCheckReportlab:
    """Tests for _check_reportlab()."""

    def test_does_not_raise_when_available(self):
        # reportlab is installed, so this should not raise
        _check_reportlab()

    def test_raises_import_error_when_unavailable(self):
        with patch("greybeard.reporters.pdf.HAS_REPORTLAB", False):
            with pytest.raises(ImportError, match="reportlab is required"):
                _check_reportlab()


# ---------------------------------------------------------------------------
# PDFReporter initialization
# ---------------------------------------------------------------------------


class TestPDFReporterInit:
    """Tests for PDFReporter.__init__()."""

    def test_initialization(self, meta):
        reporter = PDFReporter(SAMPLE_MARKDOWN, meta)
        assert reporter.markdown == SAMPLE_MARKDOWN
        assert reporter.meta == meta

    def test_sections_parsed_on_init(self, meta):
        reporter = PDFReporter(SAMPLE_MARKDOWN, meta)
        assert "summary" in reporter.sections
        assert "key_risks" in reporter.sections

    def test_styles_set_up_on_init(self, meta):
        reporter = PDFReporter(SAMPLE_MARKDOWN, meta)
        assert reporter.styles is not None
        assert "CustomHeading1" in reporter.styles.byName
        assert "CustomHeading2" in reporter.styles.byName
        assert "CustomBody" in reporter.styles.byName

    def test_raises_when_reportlab_unavailable(self, meta):
        with patch("greybeard.reporters.pdf.HAS_REPORTLAB", False):
            with pytest.raises(ImportError):
                PDFReporter(SAMPLE_MARKDOWN, meta)


# ---------------------------------------------------------------------------
# PDFReporter._build_title_page
# ---------------------------------------------------------------------------


class TestBuildTitlePage:
    """Tests for PDFReporter._build_title_page()."""

    def test_returns_list(self, reporter):
        story = reporter._build_title_page()
        assert isinstance(story, list)
        assert len(story) > 0

    def test_contains_page_break(self, reporter):
        story = reporter._build_title_page()
        types = [type(elem).__name__ for elem in story]
        assert "PageBreak" in types


# ---------------------------------------------------------------------------
# PDFReporter._build_risk_summary
# ---------------------------------------------------------------------------


class TestBuildRiskSummary:
    """Tests for PDFReporter._build_risk_summary()."""

    def test_returns_list(self, reporter):
        story = reporter._build_risk_summary()
        assert isinstance(story, list)
        assert len(story) > 0

    def test_includes_summary_text(self, reporter):
        story = reporter._build_risk_summary()
        text_parts = [getattr(elem, "text", "") or getattr(elem, "_text", "") for elem in story]
        combined = " ".join(str(p) for p in text_parts)
        assert len(combined) > 0

    def test_risk_summary_no_risks(self, meta):
        """Test risk summary when no key_risks section."""
        reporter = PDFReporter("## Summary\n\nAll good.\n", meta)
        story = reporter._build_risk_summary()
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# PDFReporter._build_findings_section
# ---------------------------------------------------------------------------


class TestBuildFindingsSection:
    """Tests for PDFReporter._build_findings_section()."""

    def test_returns_list(self, reporter):
        story = reporter._build_findings_section()
        assert isinstance(story, list)

    def test_findings_with_questions_no_bullets(self, meta):
        """Questions section as plain text (no bullet items)."""
        markdown = (
            "## Summary\n\nSummary here.\n\n"
            "## Questions to Answer Before Proceeding\n\n"
            "Just a plain question here.\n"
        )
        reporter = PDFReporter(markdown, meta)
        story = reporter._build_findings_section()
        assert isinstance(story, list)

    def test_findings_empty_sections(self, meta):
        """Test with minimal markdown — no tradeoffs/questions/comm."""
        reporter = PDFReporter("## Summary\n\nAll good.\n", meta)
        story = reporter._build_findings_section()
        assert isinstance(story, list)

    def test_findings_with_communication_language(self, meta):
        """Communication language section is rendered when present."""
        markdown = (
            "## Summary\n\nHigh risk change.\n\n"
            "## Suggested Communication Language\n\n"
            "Heads up team, this is a risky deploy — rollback plan is ready."
        )
        reporter = PDFReporter(markdown, meta)
        story = reporter._build_findings_section()
        assert isinstance(story, list)
        # Should contain more elements when comm section is present
        assert len(story) > 2


# ---------------------------------------------------------------------------
# PDFReporter._build_metadata_footer
# ---------------------------------------------------------------------------


class TestBuildMetadataFooter:
    """Tests for PDFReporter._build_metadata_footer()."""

    def test_returns_list(self, reporter):
        story = reporter._build_metadata_footer()
        assert isinstance(story, list)
        assert len(story) > 0

    def test_contains_page_break(self, reporter):
        story = reporter._build_metadata_footer()
        types = [type(elem).__name__ for elem in story]
        assert "PageBreak" in types


# ---------------------------------------------------------------------------
# PDFReporter.generate
# ---------------------------------------------------------------------------


class TestPDFReporterGenerate:
    """Tests for PDFReporter.generate()."""

    def test_generates_pdf_file(self, reporter, tmp_pdf):
        result_path = reporter.generate(tmp_pdf)
        assert result_path == tmp_pdf
        assert Path(tmp_pdf).exists()
        assert Path(tmp_pdf).stat().st_size > 0

    def test_returns_output_path(self, reporter, tmp_pdf):
        result = reporter.generate(tmp_pdf)
        assert result == tmp_pdf

    def test_generates_pdf_with_minimal_markdown(self, meta, tmp_path):
        reporter = PDFReporter(MINIMAL_MARKDOWN, meta)
        output = str(tmp_path / "minimal.pdf")
        result = reporter.generate(output)
        assert Path(result).exists()

    def test_pain_risk_severity_labels(self, meta, tmp_path):
        """Test with various risk keywords to exercise severity classification."""
        markdown = """\
## Summary

Summary here.

## Key Risks

- No plan for rollback
- Unknown impact on traffic
- Consider performance risk
- Critical path affected
- Data loss possible

"""
        reporter = PDFReporter(markdown, meta)
        output = str(tmp_path / "severity.pdf")
        result = reporter.generate(output)
        assert Path(result).exists()


# ---------------------------------------------------------------------------
# to_pdf
# ---------------------------------------------------------------------------


class TestToPdf:
    """Tests for the to_pdf() convenience function."""

    def test_to_pdf_generates_file(self, meta, tmp_pdf):
        result = to_pdf(SAMPLE_MARKDOWN, meta, output_path=tmp_pdf)
        assert result == tmp_pdf
        assert Path(tmp_pdf).exists()

    def test_to_pdf_raises_without_output_path(self, meta):
        with pytest.raises(ValueError, match="output_path is required"):
            to_pdf(SAMPLE_MARKDOWN, meta, output_path=None)
