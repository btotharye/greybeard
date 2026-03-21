"""Tests for dashboard reporter."""

from __future__ import annotations

import tempfile
from pathlib import Path

from greybeard.batch_analyzer import AggregatedFindings, BatchAnalyzer, Finding
from greybeard.reporters.dashboard import DashboardReporter


class TestDashboardReporter:
    """Test DashboardReporter class."""

    def test_reporter_initialization_with_aggregated(self) -> None:
        """Test initializing with AggregatedFindings."""
        aggregated = AggregatedFindings(
            total_reviews=3,
            total_findings=5,
            critical_count=1,
            high_count=2,
            medium_count=2,
            low_count=0,
            info_count=0,
        )
        reporter = DashboardReporter(aggregated)
        assert reporter.aggregated == aggregated

    def test_reporter_initialization_with_analyzer(self) -> None:
        """Test initializing with BatchAnalyzer."""
        analyzer = BatchAnalyzer()
        analyzer.add_review("test.txt", "Critical: SQL injection")
        reporter = DashboardReporter(analyzer)
        assert reporter.aggregated is not None
        assert reporter.aggregated.total_reviews == 1

    def test_render_html_basic(self) -> None:
        """Test rendering basic HTML."""
        aggregated = AggregatedFindings(
            total_reviews=1,
            total_findings=1,
            critical_count=1,
            high_count=0,
            medium_count=0,
            low_count=0,
            info_count=0,
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert "<!DOCTYPE html>" in html
        assert "Batch Review Analysis Dashboard" in html
        assert "1" in html  # critical count

    def test_render_html_includes_summary(self) -> None:
        """Test HTML includes summary cards."""
        aggregated = AggregatedFindings(
            total_reviews=2,
            total_findings=5,
            critical_count=1,
            high_count=2,
            medium_count=2,
            low_count=0,
            info_count=0,
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert "Critical" in html
        assert "High" in html
        assert "Medium" in html
        assert "2" in html  # Total reviews

    def test_render_html_includes_findings(self) -> None:
        """Test HTML includes findings."""
        finding = Finding(
            title="SQL Injection",
            description="Vulnerable to SQL injection",
            risk_level="critical",
            sources=["app.py"],
        )
        aggregated = AggregatedFindings(
            findings=[finding],
            total_reviews=1,
            total_findings=1,
            critical_count=1,
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert "SQL Injection" in html
        assert "critical" in html.lower()
        assert "app.py" in html

    def test_render_html_includes_heatmap(self) -> None:
        """Test HTML includes risk heatmap when data present."""
        aggregated = AggregatedFindings(
            total_reviews=1,
            total_findings=1,
            critical_count=1,
            risk_heatmap={"security": 10, "performance": 5},
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        # Heatmap section should be included
        assert "Risk Heatmap" in html
        assert "heatmapData" in html

    def test_render_html_includes_trends(self) -> None:
        """Test HTML includes detected trends."""
        aggregated = AggregatedFindings(
            total_reviews=3,
            total_findings=5,
            critical_count=1,
            trends=["High consensus on SQL injection", "Critical risk found"],
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert "Detected Trends" in html
        assert "High consensus" in html
        assert "Critical risk" in html

    def test_render_html_escape_special_chars(self) -> None:
        """Test HTML escaping of special characters."""
        finding = Finding(
            title="XSS & CSRF <attack>",
            description="Unescaped & vulnerable",
            risk_level="high",
            sources=["<script>.js"],
        )
        aggregated = AggregatedFindings(
            findings=[finding],
            total_reviews=1,
            total_findings=1,
            high_count=1,
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        # Should be escaped
        assert "&lt;" in html or "&amp;" in html
        assert "<attack>" not in html  # Should not have raw HTML

    def test_render_finding_item(self) -> None:
        """Test rendering individual finding item."""
        reporter = DashboardReporter(AggregatedFindings())
        finding = Finding(
            title="Test Issue",
            description="Test description",
            risk_level="high",
            sources=["file.py"],
            frequency=2,
        )
        html = reporter._render_finding_item(finding)

        assert "Test Issue" in html
        assert "Test description" in html
        assert "high" in html
        assert "file.py" in html
        assert "2x" in html

    def test_render_finding_item_with_frequency(self) -> None:
        """Test rendering finding with frequency display."""
        reporter = DashboardReporter(AggregatedFindings())
        finding = Finding(
            title="Recurring Issue",
            description="Found multiple times",
            risk_level="critical",
            sources=["a.py", "b.py"],
            frequency=3,
        )
        html = reporter._render_finding_item(finding, show_frequency=True)

        assert "3 reviews" in html
        assert "3x" in html

    def test_save_html(self) -> None:
        """Test saving HTML to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregated = AggregatedFindings(
                total_reviews=1,
                total_findings=1,
                critical_count=1,
            )
            reporter = DashboardReporter(aggregated)
            output_path = Path(tmpdir) / "dashboard.html"

            reporter.save_html(output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "<!DOCTYPE html>" in content
            assert "Batch Review Analysis Dashboard" in content

    def test_save_html_creates_directories(self) -> None:
        """Test save_html creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregated = AggregatedFindings(
                total_reviews=1,
                total_findings=1,
                critical_count=1,
            )
            reporter = DashboardReporter(aggregated)
            # Deep nested path
            output_path = Path(tmpdir) / "reports" / "2026" / "Q1" / "dashboard.html"

            reporter.save_html(output_path)

            assert output_path.exists()
            assert output_path.parent.exists()

    def test_escape_html_ampersand(self) -> None:
        """Test escaping ampersand."""
        reporter = DashboardReporter(AggregatedFindings())
        escaped = reporter._escape_html("Fish & Chips")
        assert "&amp;" in escaped

    def test_escape_html_tags(self) -> None:
        """Test escaping HTML tags."""
        reporter = DashboardReporter(AggregatedFindings())
        escaped = reporter._escape_html("<script>alert('xss')</script>")
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "<script>" not in escaped

    def test_escape_html_quotes(self) -> None:
        """Test escaping quotes."""
        reporter = DashboardReporter(AggregatedFindings())
        escaped = reporter._escape_html('He said "hello"')
        assert "&quot;" in escaped or "&#39;" in escaped

    def test_render_html_d3_scripts_included(self) -> None:
        """Test D3.js scripts are included in HTML."""
        aggregated = AggregatedFindings(
            total_reviews=1,
            total_findings=1,
            critical_count=1,
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert "d3.js" in html or "d3.v7" in html
        assert "switchTab" in html
        assert "riskData" in html

    def test_render_html_with_empty_findings(self) -> None:
        """Test rendering with no findings."""
        aggregated = AggregatedFindings(
            total_reviews=1,
            total_findings=0,
            findings=[],
            recurring_findings=[],
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert "<!DOCTYPE html>" in html
        assert "0" in html

    def test_render_html_all_risk_levels(self) -> None:
        """Test rendering with all risk levels."""
        aggregated = AggregatedFindings(
            total_reviews=1,
            total_findings=5,
            critical_count=1,
            high_count=1,
            medium_count=1,
            low_count=1,
            info_count=1,
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert "Critical" in html
        assert "High" in html
        assert "Medium" in html
        assert "Low" in html
        assert "Info" in html

    def test_integration_analyzer_to_dashboard(self) -> None:
        """Test full integration from analyzer to dashboard."""
        analyzer = BatchAnalyzer()
        analyzer.add_review(
            "file1.py",
            "Critical: SQL injection\nHigh: Missing validation",
        )
        analyzer.add_review(
            "file2.py",
            "Critical: SQL injection\nMedium: Error handling",
        )

        reporter = DashboardReporter(analyzer)
        html = reporter.render_html()

        assert "<!DOCTYPE html>" in html
        assert "2" in html  # 2 reviews
        assert "SQL injection" in html.lower() or "sql" in html.lower()

    def test_dashboard_responsive_design(self) -> None:
        """Test HTML includes responsive design classes."""
        aggregated = AggregatedFindings(
            total_reviews=1,
            total_findings=1,
            critical_count=1,
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert "@media" in html  # Media queries present
        assert "max-width" in html
        assert "grid" in html.lower() or "flex" in html.lower()

    def test_dashboard_dark_mode_support(self) -> None:
        """Test HTML includes dark mode support."""
        aggregated = AggregatedFindings(
            total_reviews=1,
            total_findings=1,
            critical_count=1,
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert "prefers-color-scheme" in html

    def test_render_html_tabs_present(self) -> None:
        """Test tabs for all/recurring findings."""
        aggregated = AggregatedFindings(
            total_reviews=1,
            total_findings=2,
            critical_count=2,
            findings=[
                Finding(
                    title="Issue 1",
                    description="Test",
                    risk_level="critical",
                ),
                Finding(
                    title="Issue 2",
                    description="Test",
                    risk_level="critical",
                    frequency=2,
                ),
            ],
            recurring_findings=[
                Finding(
                    title="Issue 2",
                    description="Test",
                    risk_level="critical",
                    frequency=2,
                ),
            ],
        )
        reporter = DashboardReporter(aggregated)
        html = reporter.render_html()

        assert 'id="all-findings"' in html
        assert 'id="recurring-findings"' in html
        assert "switchTab" in html
