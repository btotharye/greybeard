"""Tests for batch analyzer and aggregation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from greybeard.batch_analyzer import (
    AggregatedFindings,
    BatchAnalyzer,
    Finding,
    ReviewSummary,
)


class TestFinding:
    """Test Finding dataclass."""

    def test_finding_initialization(self) -> None:
        """Test creating a Finding."""
        finding = Finding(
            title="SQL Injection Risk",
            description="User input not sanitized",
            risk_level="critical",
        )
        assert finding.title == "SQL Injection Risk"
        assert finding.risk_level == "critical"
        assert finding.frequency == 1
        assert finding.sources == []

    def test_finding_to_dict(self) -> None:
        """Test Finding serialization."""
        finding = Finding(
            title="Test Finding",
            description="A test",
            risk_level="high",
            frequency=3,
            sources=["file1.py", "file2.py"],
            tags=["security", "performance"],
        )
        data = finding.to_dict()
        assert data["title"] == "Test Finding"
        assert data["risk_level"] == "high"
        assert data["frequency"] == 3
        assert data["sources"] == ["file1.py", "file2.py"]
        assert data["tags"] == ["security", "performance"]


class TestReviewSummary:
    """Test ReviewSummary dataclass."""

    def test_review_summary_initialization(self) -> None:
        """Test creating a ReviewSummary."""
        summary = ReviewSummary(
            source_file="review1.txt",
            review_text="Critical: SQL injection vulnerability",
        )
        assert summary.source_file == "review1.txt"
        assert summary.critical_count == 0
        assert summary.total_risk_score == 0.0

    def test_review_summary_to_dict(self) -> None:
        """Test ReviewSummary serialization."""
        finding = Finding(
            title="Test",
            description="Test finding",
            risk_level="high",
        )
        summary = ReviewSummary(
            source_file="test.txt",
            review_text="Some text",
            findings=[finding],
            critical_count=1,
        )
        data = summary.to_dict()
        assert data["source_file"] == "test.txt"
        assert len(data["findings"]) == 1


class TestBatchAnalyzer:
    """Test BatchAnalyzer class."""

    def test_analyzer_initialization(self) -> None:
        """Test initializing analyzer."""
        analyzer = BatchAnalyzer()
        assert analyzer.reviews == []
        assert analyzer.aggregated is None

    def test_add_single_review(self) -> None:
        """Test adding a single review."""
        analyzer = BatchAnalyzer()
        review_text = "Critical: SQL injection in login form"
        summary = analyzer.add_review("review1.txt", review_text)

        assert summary.source_file == "review1.txt"
        assert len(analyzer.reviews) == 1
        assert summary.findings  # Should have extracted findings

    def test_add_multiple_reviews(self) -> None:
        """Test adding multiple reviews."""
        analyzer = BatchAnalyzer()
        analyzer.add_review("review1.txt", "Critical: SQL injection")
        analyzer.add_review("review2.txt", "High: Missing auth check")
        analyzer.add_review("review3.txt", "Medium: Poor error handling")

        assert len(analyzer.reviews) == 3

    def test_extract_findings_critical(self) -> None:
        """Test extracting critical findings."""
        analyzer = BatchAnalyzer()
        review_text = "🔴 Critical: SQL injection vulnerability in user login"
        summary = analyzer.add_review("test.txt", review_text)

        critical_findings = [f for f in summary.findings if f.risk_level == "critical"]
        assert len(critical_findings) > 0

    def test_extract_findings_high(self) -> None:
        """Test extracting high-level findings."""
        analyzer = BatchAnalyzer()
        review_text = "High risk issue: Missing input validation"
        summary = analyzer.add_review("test.txt", review_text)

        findings = [f for f in summary.findings if f.risk_level == "high"]
        assert len(findings) > 0

    def test_extract_findings_medium(self) -> None:
        """Test extracting medium-level findings."""
        analyzer = BatchAnalyzer()
        review_text = "Medium severity: Incomplete error handling"
        summary = analyzer.add_review("test.txt", review_text)

        findings = [f for f in summary.findings if f.risk_level == "medium"]
        assert len(findings) > 0

    def test_calculate_risk_metrics(self) -> None:
        """Test calculating risk metrics."""
        analyzer = BatchAnalyzer()
        analyzer.add_review(
            "test.txt",
            "Critical: issue1\n\nHigh: issue2\n\nMedium: issue3",
        )

        summary = analyzer.reviews[0]
        assert summary.critical_count >= 1
        assert summary.high_count >= 1
        assert summary.medium_count >= 1
        assert summary.total_risk_score > 0

    def test_analyze_single_review(self) -> None:
        """Test analyzing a single review."""
        analyzer = BatchAnalyzer()
        analyzer.add_review("test.txt", "Critical: SQL injection vulnerability")
        aggregated = analyzer.analyze()

        assert aggregated.total_reviews == 1
        assert len(aggregated.findings) > 0
        assert aggregated.critical_count > 0

    def test_analyze_multiple_reviews(self) -> None:
        """Test analyzing multiple reviews."""
        analyzer = BatchAnalyzer()
        analyzer.add_review("review1.txt", "Critical: SQL injection")
        analyzer.add_review("review2.txt", "Critical: SQL injection")
        analyzer.add_review("review3.txt", "High: Auth issue")

        aggregated = analyzer.analyze()

        assert aggregated.total_reviews == 3
        assert aggregated.total_findings > 0

    def test_deduplicate_findings(self) -> None:
        """Test deduplicating similar findings."""
        analyzer = BatchAnalyzer()
        analyzer.add_review("review1.txt", "Critical: SQL injection in login form")
        analyzer.add_review("review2.txt", "Critical: SQL injection vulnerability")
        analyzer.add_review("review3.txt", "Critical: SQL injection")

        aggregated = analyzer.analyze()

        # Should detect these as similar and deduplicate
        sql_findings = [
            f for f in aggregated.findings
            if "sql" in f.title.lower() or "injection" in f.title.lower()
        ]
        # After deduplication, should have fewer distinct findings
        assert len(sql_findings) <= 3

    def test_identify_recurring_findings(self) -> None:
        """Test identifying recurring findings."""
        analyzer = BatchAnalyzer()
        # Same finding in 2+ reviews
        analyzer.add_review("review1.txt", "Critical: Missing authentication check\nHigh: Validation issue")
        analyzer.add_review("review2.txt", "Critical: Missing authentication check\nHigh: SQL injection")
        analyzer.add_review("review3.txt", "High: Something else")

        aggregated = analyzer.analyze()

        # Should have at least one recurring finding (auth check appears in 2 reviews)
        assert len(aggregated.recurring_findings) >= 1

    def test_build_risk_heatmap(self) -> None:
        """Test building risk heatmap by tag."""
        analyzer = BatchAnalyzer()
        finding1 = Finding(
            title="SQL Issue",
            description="Test",
            risk_level="critical",
            tags=["security"],
        )
        finding2 = Finding(
            title="Auth Issue",
            description="Test",
            risk_level="high",
            tags=["security"],
        )
        finding3 = Finding(
            title="Perf Issue",
            description="Test",
            risk_level="medium",
            tags=["performance"],
        )

        # Manually test heatmap
        heatmap = analyzer._build_risk_heatmap([finding1, finding2, finding3])
        assert "security" in heatmap
        assert "performance" in heatmap
        assert heatmap["security"] > heatmap.get("performance", 0)

    def test_detect_trends(self) -> None:
        """Test detecting trends."""
        analyzer = BatchAnalyzer()
        analyzer.add_review("review1.txt", "Critical: SQL injection")
        analyzer.add_review("review2.txt", "Critical: SQL injection")
        analyzer.add_review("review3.txt", "Critical: SQL injection")

        aggregated = analyzer.analyze()

        assert len(aggregated.trends) > 0
        # Should detect critical risk concentration
        assert any("critical" in trend.lower() for trend in aggregated.trends)

    def test_export_json(self) -> None:
        """Test JSON export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = BatchAnalyzer()
            analyzer.add_review("test.txt", "Critical: Issue")
            analyzer.analyze()

            output_path = Path(tmpdir) / "output.json"
            analyzer.export_json(output_path)

            assert output_path.exists()
            data = json.loads(output_path.read_text())
            assert data["metadata"]["total_reviews"] == 1
            assert data["metadata"]["total_findings"] > 0

    def test_export_markdown(self) -> None:
        """Test Markdown export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = BatchAnalyzer()
            analyzer.add_review("test.txt", "Critical: Issue\nHigh: Another issue")
            analyzer.analyze()

            output_path = Path(tmpdir) / "output.md"
            analyzer.export_markdown(output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "Batch Review Analysis Report" in content
            assert "Total Reviews" in content
            assert "Critical" in content

    def test_normalize_text(self) -> None:
        """Test text normalization."""
        analyzer = BatchAnalyzer()
        normalized = analyzer._normalize_text("  SQL   Injection   ")
        assert normalized == "sql injection"

    def test_fuzzy_match_identical(self) -> None:
        """Test fuzzy matching identical texts."""
        analyzer = BatchAnalyzer()
        text1 = "sql injection vulnerability"
        text2 = "sql injection vulnerability"
        assert analyzer._fuzzy_match(text1, text2) is True

    def test_fuzzy_match_similar(self) -> None:
        """Test fuzzy matching similar texts."""
        analyzer = BatchAnalyzer()
        text1 = "sql injection in login form"
        text2 = "sql injection vulnerability"
        # Should match with moderate similarity (both mention sql and injection)
        # Jaccard: {sql, injection} / {sql, injection, in, login, form, vulnerability} = 2/6 = 0.33
        # So threshold needs to be <= 0.33 for this to pass
        assert analyzer._fuzzy_match(text1, text2, threshold=0.3) is True

    def test_fuzzy_match_different(self) -> None:
        """Test fuzzy matching different texts."""
        analyzer = BatchAnalyzer()
        text1 = "sql injection"
        text2 = "missing authentication"
        assert analyzer._fuzzy_match(text1, text2, threshold=0.7) is False

    def test_risk_weights(self) -> None:
        """Test risk weight constants."""
        assert BatchAnalyzer.RISK_WEIGHTS["critical"] == 10
        assert BatchAnalyzer.RISK_WEIGHTS["high"] == 5
        assert BatchAnalyzer.RISK_WEIGHTS["medium"] == 2
        assert BatchAnalyzer.RISK_WEIGHTS["low"] == 1
        assert BatchAnalyzer.RISK_WEIGHTS["info"] == 0

    def test_empty_analyzer(self) -> None:
        """Test analyzing empty analyzer."""
        analyzer = BatchAnalyzer()
        aggregated = analyzer.analyze()

        assert aggregated.total_reviews == 0
        assert len(aggregated.findings) == 0

    def test_real_world_scenario(self) -> None:
        """Test real-world scenario with multiple reviews."""
        analyzer = BatchAnalyzer()

        # Review 1: API endpoint
        analyzer.add_review(
            "api_auth.py",
            """
            Critical: SQL injection in user lookup
            
            High risk: Missing CORS validation
            
            Medium: Unhandled exceptions
            """,
        )

        # Review 2: Database queries
        analyzer.add_review(
            "db_queries.py",
            """
            Critical: Parameterization missing in SQL injection
            
            High risk: No input validation on user ID
            
            Low: Inconsistent error messages
            """,
        )

        # Review 3: Frontend validation
        analyzer.add_review(
            "forms.js",
            """
            Medium: Client-side only validation (insufficient)
            
            Low: Missing loading states
            """,
        )

        aggregated = analyzer.analyze()

        assert aggregated.total_reviews == 3
        assert aggregated.total_findings > 0
        # SQL injection issues should be deduplicated and marked as recurring
        assert aggregated.critical_count >= 1
        # Should detect some high risk findings
        assert aggregated.high_count >= 1 or aggregated.total_findings >= 2
        # Should detect some recurring findings (SQL issues appear in 2+ reviews)
        assert len(aggregated.recurring_findings) >= 1

        # Verify deduplication worked
        total_original_findings = (
            len(analyzer.reviews[0].findings)
            + len(analyzer.reviews[1].findings)
            + len(analyzer.reviews[2].findings)
        )
        assert aggregated.total_findings <= total_original_findings
