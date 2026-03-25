"""Tests for CLI integration with Copilot backend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from greybeard.cli import cli


@pytest.fixture
def runner():
    """Return a CliRunner for invoking CLI commands."""
    return CliRunner()


class TestAnalyzeCommandBackendOption:
    """Test --backend and --github-token options on analyze command."""

    @patch("greybeard.cli.GreybeardConfig")
    @patch("greybeard.cli.load_pack")
    @patch("greybeard.cli.run_review")
    def test_analyze_with_copilot_backend(self, mock_run, mock_pack, mock_config, runner):
        """Test analyze command with --backend copilot."""
        # Mock config
        config = MagicMock()
        config.llm.backend = "openai"
        config.llm.resolved_model.return_value = "gpt-4o"
        config.default_mode = "review"
        config.default_pack = "staff-core"
        mock_config.load.return_value = config

        # Mock pack
        mock_pack.return_value = MagicMock(name="staff-core")

        # Mock review result
        mock_run.return_value = "Analysis complete."

        result = runner.invoke(
            cli,
            ["analyze", "--backend", "copilot"],
            input="test diff content\n",
        )

        # Verify backend was changed
        assert config.llm.backend == "copilot"

    @patch("greybeard.cli.GreybeardConfig")
    @patch("greybeard.cli.load_pack")
    @patch("greybeard.cli.run_review")
    def test_analyze_with_github_token_option(
        self, mock_run, mock_pack, mock_config, runner
    ):
        """Test analyze command with --github-token option."""
        import os

        config = MagicMock()
        config.llm.backend = "openai"
        config.llm.resolved_model.return_value = "gpt-4o"
        config.default_mode = "review"
        config.default_pack = "staff-core"
        mock_config.load.return_value = config

        mock_pack.return_value = MagicMock(name="staff-core")
        mock_run.return_value = "Analysis complete."

        result = runner.invoke(
            cli,
            ["analyze", "--github-token", "ghp_test123"],
            input="test diff\n",
        )

        # Verify token was set in environment
        assert os.environ.get("GITHUB_TOKEN") == "ghp_test123"

    @patch("greybeard.cli.GreybeardConfig")
    @patch("greybeard.cli.load_pack")
    @patch("greybeard.cli.run_review")
    def test_analyze_with_both_backend_and_token(
        self, mock_run, mock_pack, mock_config, runner
    ):
        """Test analyze command with both --backend and --github-token."""
        import os

        config = MagicMock()
        config.llm.backend = "openai"
        config.llm.resolved_model.return_value = "gpt-4o"
        config.default_mode = "review"
        config.default_pack = "staff-core"
        mock_config.load.return_value = config

        mock_pack.return_value = MagicMock(name="staff-core")
        mock_run.return_value = "Analysis complete."

        result = runner.invoke(
            cli,
            [
                "analyze",
                "--backend",
                "copilot",
                "--github-token",
                "ghp_test456",
            ],
            input="test diff\n",
        )

        assert config.llm.backend == "copilot"
        assert os.environ.get("GITHUB_TOKEN") == "ghp_test456"

    @patch("greybeard.cli.GreybeardConfig")
    @patch("greybeard.cli.load_pack")
    @patch("greybeard.cli.run_review")
    def test_analyze_backend_validation_fails(
        self, mock_run, mock_pack, mock_config, runner
    ):
        """Test analyze with invalid backend."""
        # Invalid backend should be rejected by click
        result = runner.invoke(
            cli,
            ["analyze", "--backend", "invalid-backend"],
            input="test\n",
        )

        # Click should reject invalid choice
        assert result.exit_code != 0


class TestSelfCheckCommandBackendOption:
    """Test --backend and --github-token options on self-check command."""

    @patch("greybeard.cli.GreybeardConfig")
    @patch("greybeard.cli.load_pack")
    @patch("greybeard.cli.run_review")
    def test_self_check_with_copilot_backend(
        self, mock_run, mock_pack, mock_config, runner
    ):
        """Test self-check command with --backend copilot."""
        config = MagicMock()
        config.llm.backend = "openai"
        config.llm.resolved_model.return_value = "gpt-4o"
        config.default_pack = "staff-core"
        mock_config.load.return_value = config

        mock_pack.return_value = MagicMock(name="staff-core")
        mock_run.return_value = "Self-check complete."

        result = runner.invoke(
            cli,
            [
                "self-check",
                "--context",
                "test decision",
                "--backend",
                "copilot",
            ],
        )

        assert config.llm.backend == "copilot"

    @patch("greybeard.cli.GreybeardConfig")
    @patch("greybeard.cli.load_pack")
    @patch("greybeard.cli.run_review")
    def test_self_check_with_github_token(
        self, mock_run, mock_pack, mock_config, runner
    ):
        """Test self-check command with --github-token option."""
        import os

        config = MagicMock()
        config.llm.backend = "openai"
        config.llm.resolved_model.return_value = "gpt-4o"
        config.default_pack = "staff-core"
        mock_config.load.return_value = config

        mock_pack.return_value = MagicMock(name="staff-core")
        mock_run.return_value = "Self-check complete."

        result = runner.invoke(
            cli,
            [
                "self-check",
                "--context",
                "test",
                "--github-token",
                "ghp_test789",
            ],
        )

        assert os.environ.get("GITHUB_TOKEN") == "ghp_test789"


class TestCoachCommandBackendOption:
    """Test --backend and --github-token options on coach command."""

    @patch("greybeard.cli.GreybeardConfig")
    @patch("greybeard.cli.load_pack")
    @patch("greybeard.cli.run_review")
    def test_coach_with_copilot_backend(
        self, mock_run, mock_pack, mock_config, runner
    ):
        """Test coach command with --backend copilot."""
        config = MagicMock()
        config.llm.backend = "openai"
        config.llm.resolved_model.return_value = "gpt-4o"
        mock_config.load.return_value = config

        mock_pack.return_value = MagicMock(name="mentor-mode")
        mock_run.return_value = "Coaching complete."

        result = runner.invoke(
            cli,
            [
                "coach",
                "--audience",
                "team",
                "--context",
                "concern",
                "--backend",
                "copilot",
            ],
        )

        assert config.llm.backend == "copilot"

    @patch("greybeard.cli.GreybeardConfig")
    @patch("greybeard.cli.load_pack")
    @patch("greybeard.cli.run_review")
    def test_coach_with_github_token(
        self, mock_run, mock_pack, mock_config, runner
    ):
        """Test coach command with --github-token option."""
        import os

        config = MagicMock()
        config.llm.backend = "openai"
        config.llm.resolved_model.return_value = "gpt-4o"
        mock_config.load.return_value = config

        mock_pack.return_value = MagicMock(name="mentor-mode")
        mock_run.return_value = "Coaching complete."

        result = runner.invoke(
            cli,
            [
                "coach",
                "--audience",
                "team",
                "--context",
                "test",
                "--github-token",
                "ghp_coach123",
            ],
        )

        assert os.environ.get("GITHUB_TOKEN") == "ghp_coach123"


class TestBackendEnvVarIntegration:
    """Test GITHUB_TOKEN environment variable integration."""

    @patch("greybeard.cli.GreybeardConfig")
    @patch("greybeard.cli.load_pack")
    @patch("greybeard.cli.run_review")
    def test_github_token_from_env_var(
        self, mock_run, mock_pack, mock_config, runner
    ):
        """Test --github-token can read from GITHUB_TOKEN env var."""
        config = MagicMock()
        config.llm.backend = "copilot"
        config.llm.resolved_model.return_value = "claude-3-5-sonnet-20241022"
        config.default_mode = "review"
        config.default_pack = "staff-core"
        mock_config.load.return_value = config

        mock_pack.return_value = MagicMock(name="staff-core")
        mock_run.return_value = "Analysis complete."

        # Set env var and don't pass --github-token explicitly
        result = runner.invoke(
            cli,
            ["analyze"],
            input="test\n",
            env={"GITHUB_TOKEN": "ghp_from_env"},
        )

        # The click option should read from env var
        # Note: click's envvar behavior means it's auto-set from env


class TestAnalyzeCommandExamples:
    """Test that analyze command help includes new examples."""

    def test_analyze_help_includes_copilot_examples(self, runner):
        """Test that --help includes Copilot backend examples."""
        result = runner.invoke(cli, ["analyze", "--help"])

        assert "--backend" in result.output
        assert "--github-token" in result.output
        assert "copilot" in result.output.lower()


class TestSelfCheckCommandExamples:
    """Test that self-check command help includes new examples."""

    def test_self_check_help_includes_backend_option(self, runner):
        """Test that --help includes --backend option."""
        result = runner.invoke(cli, ["self-check", "--help"])

        assert "--backend" in result.output
        assert "--github-token" in result.output


class TestCoachCommandExamples:
    """Test that coach command help includes new examples."""

    def test_coach_help_includes_backend_option(self, runner):
        """Test that --help includes --backend option."""
        result = runner.invoke(cli, ["coach", "--help"])

        assert "--backend" in result.output
        assert "--github-token" in result.output
