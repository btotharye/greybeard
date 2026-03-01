"""Tests for the CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from staff_review.cli import cli


@pytest.fixture
def runner():
    """Return a CliRunner for invoking CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Return a mock config with standard settings."""
    with patch("staff_review.cli.GreybeardConfig") as mock:
        config = MagicMock()
        config.llm.backend = "openai"
        config.llm.model = "gpt-4o"
        config.default_mode = "review"
        config.default_pack = "staff-core"
        mock.load.return_value = config
        yield config


class TestCliVersion:
    def test_version_flag(self, runner):
        """Test that --version returns version info."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()


class TestCliHelp:
    def test_help_flag(self, runner):
        """Test that --help returns help text."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "greybeard" in result.output.lower()

    def test_analyze_help(self, runner):
        """Test that analyze --help returns command help."""
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "analyze" in result.output.lower()


class TestConfigCommand:
    def test_config_show(self, runner, mock_config):
        """Test config show command."""
        with patch("staff_review.cli.console") as mock_console:
            result = runner.invoke(cli, ["config", "show"])
            assert result.exit_code == 0
            assert mock_console.print.called

    def test_config_set_backend(self, runner, mock_config):
        """Test config set command."""
        result = runner.invoke(cli, ["config", "set", "llm.backend", "anthropic"])
        assert result.exit_code == 0
        # Check that save was called on the mocked config instance
        mock_config.save.assert_called()

    def test_config_set_model(self, runner, mock_config):
        """Test config set for model."""
        result = runner.invoke(cli, ["config", "set", "llm.model", "gpt-4o-mini"])
        assert result.exit_code == 0
        mock_config.save.assert_called()

    def test_config_set_invalid_backend(self, runner, mock_config):
        """Test config set with invalid backend."""
        result = runner.invoke(cli, ["config", "set", "llm.backend", "invalid_backend"])
        assert result.exit_code == 1
        assert "Unknown backend" in result.output

    def test_config_set_invalid_mode(self, runner, mock_config):
        """Test config set with invalid mode."""
        result = runner.invoke(cli, ["config", "set", "default_mode", "invalid_mode"])
        assert result.exit_code == 1
        assert "Unknown mode" in result.output

    def test_config_set_unknown_key(self, runner, mock_config):
        """Test config set with unknown key."""
        result = runner.invoke(cli, ["config", "set", "unknown.key", "value"])
        assert result.exit_code == 1
        assert "Unknown key" in result.output


class TestPacksCommand:
    def test_packs_list(self, runner):
        """Test packs command lists available packs."""
        with patch("staff_review.cli.list_builtin_packs") as mock_list:
            mock_list.return_value = ["staff-core", "oncall-future-you"]
            result = runner.invoke(cli, ["packs"])
            assert result.exit_code == 0
            assert "staff-core" in result.output


class TestAnalyzeCommand:
    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    def test_analyze_from_stdin(self, mock_stdin, mock_review, runner, mock_config):
        """Test analyze command reads from stdin."""
        mock_stdin.return_value = "some diff content"
        mock_review.return_value = "Review output"

        result = runner.invoke(cli, ["analyze"])
        assert result.exit_code == 0
        assert mock_review.called

    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    def test_analyze_with_mode(self, mock_stdin, mock_review, runner, mock_config):
        """Test analyze command with --mode flag."""
        mock_stdin.return_value = "test diff"
        mock_review.return_value = "Review output"

        result = runner.invoke(cli, ["analyze", "--mode", "mentor"])
        assert result.exit_code == 0
        assert mock_review.called

    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    def test_analyze_with_pack(self, mock_stdin, mock_review, runner, mock_config):
        """Test analyze command with --pack flag."""
        mock_stdin.return_value = "test diff"
        mock_review.return_value = "Review output"

        result = runner.invoke(cli, ["analyze", "--pack", "oncall-future-you"])
        assert result.exit_code == 0

    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    def test_analyze_with_output_file(self, mock_stdin, mock_review, runner, mock_config):
        """Test analyze command with --output flag."""
        mock_stdin.return_value = "test diff"
        mock_review.return_value = "Review output"

        output_file = "review.md"
        result = runner.invoke(cli, ["analyze", "--output", output_file])
        assert result.exit_code == 0

    @patch("staff_review.cli.load_pack")
    def test_analyze_pack_not_found_error(self, mock_load_pack, runner, mock_config):
        """Test analyze fails when pack not found."""
        mock_load_pack.side_effect = FileNotFoundError("Pack not found")

        result = runner.invoke(cli, ["analyze", "--pack", "nonexistent"])
        assert result.exit_code == 1
        assert "Error" in result.output

    @patch("staff_review.cli._read_stdin_if_available")
    def test_analyze_no_input_error(self, mock_stdin, runner, mock_config):
        """Test analyze fails when no input provided."""
        mock_stdin.return_value = ""

        result = runner.invoke(cli, ["analyze"])
        assert result.exit_code == 1
        assert "No input provided" in result.output


class TestSelfCheckCommand:
    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    def test_self_check_basic(self, mock_stdin, mock_review, runner, mock_config):
        """Test self-check command."""
        mock_stdin.return_value = "proposal content"
        mock_review.return_value = "Self-check output"

        result = runner.invoke(cli, ["self-check", "--context", "My decision"])
        assert result.exit_code == 0
        assert mock_review.called

    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    def test_self_check_with_context(self, mock_stdin, mock_review, runner, mock_config):
        """Test self-check with --context flag."""
        mock_stdin.return_value = "proposal content"
        mock_review.return_value = "Self-check output"

        result = runner.invoke(
            cli,
            ["self-check", "--context", "migration"],
        )
        assert result.exit_code == 0

    @patch("staff_review.cli.load_pack")
    def test_self_check_pack_not_found_error(self, mock_load_pack, runner, mock_config):
        """Test self-check fails when pack not found."""
        mock_load_pack.side_effect = FileNotFoundError("Pack not found")

        result = runner.invoke(cli, ["self-check", "--context", "test", "--pack", "nonexistent"])
        assert result.exit_code == 1
        assert "Error" in result.output


class TestCoachCommand:
    @patch("staff_review.cli.run_review")
    def test_coach_basic(self, mock_review, runner, mock_config):
        """Test coach command."""
        mock_review.return_value = "Coaching output"

        result = runner.invoke(
            cli,
            ["coach", "--audience", "team", "--context", "shipping too fast"],
        )
        assert result.exit_code == 0
        assert mock_review.called

    @patch("staff_review.cli.run_review")
    def test_coach_with_leadership_audience(self, mock_review, runner, mock_config):
        """Test coach with leadership audience."""
        mock_review.return_value = "Coaching output"

        result = runner.invoke(
            cli,
            ["coach", "--audience", "leadership", "--context", "concerns"],
        )
        assert result.exit_code == 0

    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    def test_coach_no_context_error(self, mock_stdin, mock_review, runner, mock_config):
        """Test coach fails without context."""
        mock_stdin.return_value = ""
        mock_review.return_value = "Output"

        result = runner.invoke(cli, ["coach", "--audience", "team"])
        assert result.exit_code == 1
        assert "No context provided" in result.output

    @patch("staff_review.cli.load_pack")
    def test_coach_pack_not_found_error(self, mock_load_pack, runner, mock_config):
        """Test coach fails when pack not found."""
        mock_load_pack.side_effect = FileNotFoundError("Pack not found")

        result = runner.invoke(
            cli, ["coach", "--audience", "team", "--context", "test", "--pack", "nonexistent"]
        )
        assert result.exit_code == 1
        assert "Error" in result.output


class TestInitCommand:
    @patch("staff_review.cli.click.prompt")
    def test_init_openai_backend(self, mock_prompt, runner, mock_config):
        """Test init command with OpenAI backend."""
        # Mock user inputs
        mock_prompt.side_effect = [
            "1",  # backend choice (openai)
            "gpt-4o",  # model
            "staff-core",  # default pack
        ]

        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert "Config saved" in result.output
        assert mock_config.save.called

    @patch("staff_review.cli.click.prompt")
    def test_init_ollama_backend(self, mock_prompt, runner, mock_config):
        """Test init command with Ollama backend."""
        mock_prompt.side_effect = [
            "3",  # backend choice (ollama)
            "llama3.2",  # model
            "http://localhost:11434/v1",  # base_url
            "staff-core",  # default pack
        ]

        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert "Config saved" in result.output

    @patch("staff_review.cli.click.prompt")
    def test_init_invalid_backend_choice(self, mock_prompt, runner, mock_config):
        """Test init command with invalid backend choice."""
        mock_prompt.side_effect = ["99"]  # Invalid choice

        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 1
        assert "Invalid choice" in result.output


class TestMcpCommand:
    @patch("staff_review.mcp_server.serve")
    def test_mcp_command(self, mock_serve, runner, mock_config):
        """Test mcp command starts server."""
        result = runner.invoke(cli, ["mcp"])
        assert result.exit_code == 0
        assert mock_serve.called
