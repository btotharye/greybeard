"""Tests for ADR CLI commands."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from greybeard.cli import adr_list, adr_save
from greybeard.reporters.adr import ADRRepository


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_repo() -> Path:
    """Create a temporary git repository for CLI tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import subprocess

        repo_path = Path(tmpdir)
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
        (repo_path / "README.md").write_text("# Test\n")
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        yield repo_path


class TestAdrSaveCommand:
    """Test the adr-save CLI command."""

    def test_adr_save_requires_title(self, cli_runner: CliRunner) -> None:
        """Test that adr-save requires --title option."""
        review_text = "## Context\nThis is a test.\n## Decision\nDo it."
        result = cli_runner.invoke(adr_save, input=review_text)
        assert result.exit_code != 0
        assert "title" in result.output.lower() or "missing" in result.output.lower()

    def test_adr_save_requires_input(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test that adr-save requires stdin input."""
        result = cli_runner.invoke(
            adr_save,
            ["--title", "Test Decision", "--repo", str(temp_repo)],
        )
        assert result.exit_code != 0
        assert "no review text" in result.output.lower() or "pipe in" in result.output.lower()

    def test_adr_save_basic(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test basic adr-save operation."""
        review_text = "## Context\nSQLite is slow.\n## Decision\nUse PostgreSQL."
        result = cli_runner.invoke(
            adr_save,
            ["--title", "Use PostgreSQL", "--repo", str(temp_repo)],
            input=review_text,
        )
        assert result.exit_code == 0
        assert "ADR saved" in result.output or "✓" in result.output

        # Verify file was created
        adr_dir = temp_repo / "docs" / "adr"
        assert adr_dir.exists()
        adr_files = list(adr_dir.glob("*.md"))
        assert len(adr_files) > 0

    def test_adr_save_with_authors(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test adr-save with author names."""
        review_text = "## Context\nTest.\n## Decision\nDecide."
        result = cli_runner.invoke(
            adr_save,
            [
                "--title",
                "Test ADR",
                "--authors",
                "alice",
                "--authors",
                "bob",
                "--repo",
                str(temp_repo),
            ],
            input=review_text,
        )
        assert result.exit_code == 0

        # Verify authors are in the file
        adr_files = list((temp_repo / "docs" / "adr").glob("*.md"))
        assert len(adr_files) > 0
        content = adr_files[0].read_text()
        assert "alice" in content
        assert "bob" in content

    def test_adr_save_with_status(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test adr-save with custom status."""
        review_text = "## Context\nTest.\n## Decision\nDecide."
        result = cli_runner.invoke(
            adr_save,
            [
                "--title",
                "Test ADR",
                "--status",
                "Accepted",
                "--repo",
                str(temp_repo),
            ],
            input=review_text,
        )
        assert result.exit_code == 0

        # Verify status is in the file
        adr_files = list((temp_repo / "docs" / "adr").glob("*.md"))
        content = adr_files[0].read_text()
        assert "Accepted" in content

    def test_adr_save_with_commit(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test adr-save with --commit flag."""
        review_text = "## Context\nTest.\n## Decision\nDecide."
        result = cli_runner.invoke(
            adr_save,
            [
                "--title",
                "Test ADR",
                "--commit",
                "--repo",
                str(temp_repo),
            ],
            input=review_text,
        )
        assert result.exit_code == 0
        output = result.output.lower()
        assert "commit" in output or "git" in output or "✓" in result.output

    def test_adr_save_invalid_status(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test adr-save with invalid status."""
        review_text = "## Context\nTest.\n## Decision\nDecide."
        result = cli_runner.invoke(
            adr_save,
            [
                "--title",
                "Test ADR",
                "--status",
                "InvalidStatus",
                "--repo",
                str(temp_repo),
            ],
            input=review_text,
        )
        assert result.exit_code != 0


class TestAdrListCommand:
    """Test the adr-list CLI command."""

    def test_adr_list_empty(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test adr-list with no ADRs."""
        result = cli_runner.invoke(adr_list, ["--repo", str(temp_repo)])
        assert result.exit_code == 0
        assert "no adrs" in result.output.lower() or "not found" in result.output.lower()

    def test_adr_list_with_adrs(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test adr-list with existing ADRs."""
        # Create some ADRs
        from greybeard.reporters.adr import ADREntry

        repo = ADRRepository(temp_repo)
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

        result = cli_runner.invoke(adr_list, ["--repo", str(temp_repo)])
        assert result.exit_code == 0
        assert "Decision 1" in result.output
        assert "Decision 2" in result.output
        assert "Decision 3" in result.output
        assert "Proposed" in result.output

    def test_adr_list_shows_status(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test that adr-list shows ADR status."""
        from greybeard.reporters.adr import ADREntry

        repo = ADRRepository(temp_repo)
        adr = ADREntry(
            title="Test Decision",
            status="Accepted",
            context="",
            decision="",
            consequences="",
            alternatives="",
        )
        repo.save_adr(adr)

        result = cli_runner.invoke(adr_list, ["--repo", str(temp_repo)])
        assert result.exit_code == 0
        assert "Accepted" in result.output

    def test_adr_list_with_explicit_repo(self, cli_runner: CliRunner) -> None:
        """Test adr-list with explicit repo path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import subprocess

            # Setup git repo
            repo_path = Path(tmpdir)
            subprocess.run(
                ["git", "init"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create an ADR
            from greybeard.reporters.adr import ADREntry

            repo = ADRRepository(repo_path)
            adr = ADREntry(
                title="Test",
                status="Proposed",
                context="",
                decision="",
                consequences="",
                alternatives="",
            )
            repo.save_adr(adr)

            # Run command with explicit repo path
            result = cli_runner.invoke(adr_list, ["--repo", str(repo_path)])
            assert result.exit_code == 0
            assert "Test" in result.output


class TestADRWorkflow:
    """Integration tests for the full ADR workflow."""

    def test_full_adr_workflow(self, cli_runner: CliRunner, temp_repo: Path) -> None:
        """Test complete workflow: create, list, verify."""
        # Create first ADR
        review_text_1 = """
## Context
Database is a bottleneck.

## Decision
Implement caching layer.

## Consequences
Better performance.
"""
        result = cli_runner.invoke(
            adr_save,
            [
                "--title",
                "Add Redis Cache",
                "--authors",
                "alice",
                "--repo",
                str(temp_repo),
            ],
            input=review_text_1,
        )
        assert result.exit_code == 0

        # Create second ADR
        review_text_2 = """
## Context
Microservices architecture needed.

## Decision
Split monolith.
"""
        result = cli_runner.invoke(
            adr_save,
            [
                "--title",
                "Adopt Microservices",
                "--status",
                "Proposed",
                "--repo",
                str(temp_repo),
            ],
            input=review_text_2,
        )
        assert result.exit_code == 0

        # List all ADRs
        result = cli_runner.invoke(adr_list, ["--repo", str(temp_repo)])
        assert result.exit_code == 0
        assert "Redis Cache" in result.output
        assert "Microservices" in result.output
        assert "0001" in result.output  # First ADR number
        assert "0002" in result.output  # Second ADR number
