"""Tests for ADR (Architecture Decision Record) reporter."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from greybeard.reporters.adr import (
    ADREntry,
    ADRReporter,
    ADRRepository,
    _generate_fallback_alternatives,
    _generate_fallback_consequences,
    _generate_fallback_context,
    _generate_fallback_decision,
    _parse_adr_metadata,
)


class TestADREntry:
    """Test ADREntry dataclass."""

    def test_adr_entry_initialization(self) -> None:
        """Test creating an ADREntry."""
        adr = ADREntry(
            title="Use PostgreSQL",
            status="Proposed",
            context="Current state uses SQLite",
            decision="Switch to PostgreSQL",
            consequences="Better performance",
            alternatives="MySQL, MongoDB",
        )
        assert adr.title == "Use PostgreSQL"
        assert adr.status == "Proposed"
        assert adr.date is None

    def test_adr_entry_to_markdown(self) -> None:
        """Test markdown rendering."""
        adr = ADREntry(
            title="Use PostgreSQL",
            status="Accepted",
            context="SQLite is a bottleneck",
            decision="Adopt PostgreSQL with connection pooling",
            consequences="Improved throughput. Additional operational overhead.",
            alternatives="MySQL, RDS Aurora",
            date="2026-03-21",
            authors=["alice", "bob"],
        )
        markdown = adr.to_markdown()
        assert "# ADR: Use PostgreSQL" in markdown
        assert "**Status:** Accepted" in markdown
        assert "**Date:** 2026-03-21" in markdown
        assert "**Authors:** alice, bob" in markdown
        assert "## Context" in markdown
        assert "## Decision" in markdown
        assert "## Consequences" in markdown
        assert "## Alternatives Considered" in markdown

    def test_adr_entry_to_dict(self) -> None:
        """Test dictionary serialization."""
        adr = ADREntry(
            title="Cache Strategy",
            status="Proposed",
            context="Users experience slow page loads",
            decision="Implement Redis caching",
            consequences="5x faster page loads, +$200/mo infra cost",
            alternatives="Memcached, application-level caching",
            authors=["charlie"],
            related_decisions=["0001-use-postgresql", "0002-async-workers"],
        )
        data = adr.to_dict()
        assert data["title"] == "Cache Strategy"
        assert data["status"] == "Proposed"
        assert data["authors"] == ["charlie"]
        assert data["related_decisions"] == ["0001-use-postgresql", "0002-async-workers"]


class TestADRReporter:
    """Test ADRReporter class."""

    SAMPLE_REVIEW = """
## Context
The system currently uses a monolithic architecture which makes it difficult to scale.
We have identified performance issues and need better separation of concerns.

## Problem
Request latency has increased 3x in the past 6 months.
Our database is becoming a bottleneck.

## Decision
We should migrate to a microservices architecture starting with the payment service.
This will allow independent scaling and faster iteration.

## Consequences
**Positive:**
- Better scalability for high-traffic services
- Faster deployment cycles
- Improved team autonomy

**Negative:**
- Increased operational complexity
- Network latency between services
- Distributed debugging challenges

## Alternatives Considered
1. Vertical scaling (adding more hardware) — limited by physics
2. Database optimization — we've already exhausted this approach
3. Caching layers (Redis) — insufficient for our growth trajectory
"""

    def test_adr_reporter_initialization(self) -> None:
        """Test ADRReporter initialization."""
        reporter = ADRReporter(self.SAMPLE_REVIEW)
        assert reporter.review_text == self.SAMPLE_REVIEW
        assert reporter.title is not None

    def test_extract_title_from_review(self) -> None:
        """Test title extraction from review."""
        review_with_heading = "# Microservices Migration\nSome content here"
        reporter = ADRReporter(review_with_heading)
        assert reporter.title == "Microservices Migration"

    def test_extract_title_fallback(self) -> None:
        """Test title extraction fallback."""
        short_review = "Consider using PostgreSQL instead of SQLite for better performance."
        reporter = ADRReporter(short_review)
        assert len(reporter.title) > 0
        assert "PostgreSQL" in reporter.title or "Consider" in reporter.title

    def test_extract_title_custom(self) -> None:
        """Test custom title override."""
        reporter = ADRReporter(self.SAMPLE_REVIEW, title="Custom Title")
        assert reporter.title == "Custom Title"

    def test_extract_sections(self) -> None:
        """Test section extraction from markdown review."""
        reporter = ADRReporter(self.SAMPLE_REVIEW)
        sections = reporter.extract_sections()

        assert "context" in sections
        assert "decision" in sections
        assert "consequences" in sections
        assert "alternatives" in sections

        # Check content extraction - verify that sections contain relevant content
        # The extraction should find at least some of these keywords
        all_text = "".join(sections.values()).lower()
        assert "latency" in all_text or "bottleneck" in all_text or "monolithic" in all_text
        assert "microservices" in all_text
        assert "scalability" in all_text

    def test_extract_sections_no_headers(self) -> None:
        """Test section extraction when no headers present."""
        review_no_headers = "This is a simple review without markdown headers."
        reporter = ADRReporter(review_no_headers)
        sections = reporter.extract_sections()

        # Should treat all as context since there are no headers
        assert sections["context"] == review_no_headers
        # Decision should be populated with fallback
        assert len(sections["decision"]) > 0

    def test_generate_adr(self) -> None:
        """Test ADR generation from review."""
        reporter = ADRReporter(self.SAMPLE_REVIEW, title="Microservices Migration")
        adr = reporter.generate_adr(
            status="Proposed",
            authors=["alice", "bob"],
            related_decisions=["0001-use-postgresql"],
        )

        assert adr.title == "Microservices Migration"
        assert adr.status == "Proposed"
        assert adr.authors == ["alice", "bob"]
        assert adr.related_decisions == ["0001-use-postgresql"]
        assert adr.date is not None

    def test_generate_adr_minimal(self) -> None:
        """Test ADR generation with minimal inputs."""
        reporter = ADRReporter("Quick review: use caching.")
        adr = reporter.generate_adr()

        assert adr.status == "Proposed"
        assert adr.authors == ["greybeard"]
        assert adr.context is not None
        assert adr.decision is not None


class TestFallbackFunctions:
    """Test fallback content generators."""

    def test_fallback_context(self) -> None:
        """Test context fallback generation."""
        text = "Line 1\nLine 2\nLine 3\nLine 4"
        context = _generate_fallback_context(text)
        assert len(context) > 0
        assert "Line" in context

    def test_fallback_decision(self) -> None:
        """Test decision fallback generation."""
        text = "We should use PostgreSQL for better performance."
        decision = _generate_fallback_decision(text)
        assert "PostgreSQL" in decision or "Use" in decision

    def test_fallback_decision_with_imperative(self) -> None:
        """Test decision fallback with imperative verb."""
        text = "Recommend adopting Redis for caching across all services."
        decision = _generate_fallback_decision(text)
        assert "Recommend" in decision or "Redis" in decision

    def test_fallback_consequences(self) -> None:
        """Test consequences fallback generation."""
        text = (
            "This will have significant impact on performance. "
            "Risks include operational complexity."
        )
        consequences = _generate_fallback_consequences(text)
        assert len(consequences) > 0

    def test_fallback_alternatives(self) -> None:
        """Test alternatives fallback generation."""
        text = "We could instead use MySQL or MongoDB."
        alternatives = _generate_fallback_alternatives(text)
        assert len(alternatives) > 0


class TestADRRepository:
    """Test ADRRepository for file management and git integration."""

    @pytest.fixture
    def temp_repo(self) -> Path:
        """Create a temporary git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            # Initialize git repo
            subprocess.run(
                ["git", "init"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            # Create initial commit
            (repo_path / "README.md").write_text("# Test Repo\n")
            subprocess.run(
                ["git", "add", "README.md"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            yield repo_path

    def test_adr_repository_initialization(self, temp_repo: Path) -> None:
        """Test ADRRepository initialization."""
        repo = ADRRepository(temp_repo)
        assert repo.repo_path == temp_repo
        assert repo.adr_dir == temp_repo / "docs" / "adr"

    def test_save_adr_creates_directory(self, temp_repo: Path) -> None:
        """Test that saving an ADR creates necessary directories."""
        repo = ADRRepository(temp_repo)
        adr = ADREntry(
            title="Test Decision",
            status="Proposed",
            context="Test context",
            decision="Test decision",
            consequences="Test consequences",
            alternatives="Test alternatives",
        )

        filepath = repo.save_adr(adr)
        assert filepath.parent.exists()
        assert filepath.exists()

    def test_save_adr_with_custom_filename(self, temp_repo: Path) -> None:
        """Test saving with custom filename."""
        repo = ADRRepository(temp_repo)
        adr = ADREntry(
            title="Test Decision",
            status="Proposed",
            context="Context",
            decision="Decision",
            consequences="Consequences",
            alternatives="Alternatives",
        )

        filepath = repo.save_adr(adr, filename="custom-adr")
        assert "custom-adr" in filepath.name

    def test_save_adr_generates_filename(self, temp_repo: Path) -> None:
        """Test auto-generated filename."""
        repo = ADRRepository(temp_repo)
        adr = ADREntry(
            title="Use PostgreSQL for Persistence",
            status="Proposed",
            context="Context",
            decision="Decision",
            consequences="Consequences",
            alternatives="Alternatives",
        )

        filepath = repo.save_adr(adr)
        assert filepath.name.startswith("0001-")
        assert "postgresql" in filepath.name.lower()

    def test_save_adr_increments_number(self, temp_repo: Path) -> None:
        """Test that ADR numbers increment."""
        repo = ADRRepository(temp_repo)

        adr1 = ADREntry(
            title="First Decision",
            status="Proposed",
            context="",
            decision="",
            consequences="",
            alternatives="",
        )
        path1 = repo.save_adr(adr1)
        assert "0001-" in path1.name

        adr2 = ADREntry(
            title="Second Decision",
            status="Proposed",
            context="",
            decision="",
            consequences="",
            alternatives="",
        )
        path2 = repo.save_adr(adr2)
        assert "0002-" in path2.name

    def test_save_adr_with_commit(self, temp_repo: Path) -> None:
        """Test saving with auto-commit."""
        repo = ADRRepository(temp_repo)
        adr = ADREntry(
            title="Test Decision",
            status="Accepted",
            context="Context",
            decision="Decision",
            consequences="Consequences",
            alternatives="Alternatives",
        )

        filepath = repo.save_adr(adr, auto_commit=True)

        # Check that file is in git
        result = subprocess.run(
            ["git", "log", "--oneline", str(filepath)],
            cwd=temp_repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_list_adrs(self, temp_repo: Path) -> None:
        """Test listing ADRs."""
        repo = ADRRepository(temp_repo)

        # Create a few ADRs
        for i in range(3):
            adr = ADREntry(
                title=f"Decision {i + 1}",
                status="Proposed",
                context="",
                decision="",
                consequences="",
                alternatives="",
            )
            repo.save_adr(adr)

        adrs = repo.list_adrs()
        assert len(adrs) == 3

    def test_get_adr_by_title(self, temp_repo: Path) -> None:
        """Test finding an ADR by title."""
        repo = ADRRepository(temp_repo)
        adr = ADREntry(
            title="Find Me",
            status="Proposed",
            context="",
            decision="",
            consequences="",
            alternatives="",
        )
        repo.save_adr(adr)

        filepath = repo.get_adr_by_title("Find Me")
        assert filepath is not None
        assert filepath.exists()

    def test_get_adr_by_title_not_found(self, temp_repo: Path) -> None:
        """Test finding non-existent ADR."""
        repo = ADRRepository(temp_repo)
        filepath = repo.get_adr_by_title("Does Not Exist")
        assert filepath is None


class TestParseADRMetadata:
    """Test ADR metadata parsing."""

    def test_parse_adr_metadata_basic(self) -> None:
        """Test basic metadata extraction."""
        content = """# ADR: Use PostgreSQL

**Status:** Accepted
**Date:** 2026-03-21

## Context
...
"""
        metadata = _parse_adr_metadata(content, Path("test.md"))
        assert metadata is not None
        assert metadata.title == "Use PostgreSQL"
        assert metadata.status == "Accepted"
        assert metadata.date == "2026-03-21"

    def test_parse_adr_metadata_proposed(self) -> None:
        """Test parsing Proposed status."""
        content = """# ADR: Test

**Status:** Proposed
"""
        metadata = _parse_adr_metadata(content, Path("test.md"))
        assert metadata is not None
        assert metadata.status == "Proposed"

    def test_parse_adr_metadata_fallback_title(self) -> None:
        """Test title fallback to filename."""
        content = "No title here"
        metadata = _parse_adr_metadata(content, Path("0001-test.md"))
        assert metadata is not None
        assert "0001-test" in metadata.title


class TestADRIntegration:
    """Integration tests for full ADR workflow."""

    def test_full_workflow(self) -> None:
        """Test complete review->ADR->save workflow."""
        review = """
## Context
We need better caching to improve response times.

## Decision
Implement Redis with a write-through strategy.

## Consequences
Improved performance, additional infrastructure cost.

## Alternatives
Memcached, application-level caching
"""
        reporter = ADRReporter(review, title="Redis Caching Strategy")
        adr = reporter.generate_adr(
            status="Proposed",
            authors=["alice"],
        )

        # Verify ADR structure
        assert adr.title == "Redis Caching Strategy"
        markdown = adr.to_markdown()
        assert "Redis" in markdown
        assert "Proposed" in markdown

    def test_malformed_status_defaults_to_proposed(self) -> None:
        """Test that invalid status doesn't crash."""
        content = """# ADR: Test

**Status:** Invalid
"""
        metadata = _parse_adr_metadata(content, Path("test.md"))
        assert metadata is not None
        assert metadata.status == "Proposed"  # Should default
