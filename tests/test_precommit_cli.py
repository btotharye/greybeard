"""Tests for the precommit CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from greybeard.precommit import PreCommitConfig, PreCommitReview, RiskGate
from greybeard.precommit_cli import cli


@pytest.fixture
def runner():
    """Provide a Click test runner."""
    return CliRunner()


@pytest.fixture
def passed_review():
    """Provide a passing review."""
    return PreCommitReview(passed=True, message="Review passed — no issues found", concerns=[])


@pytest.fixture
def failed_review():
    """Provide a failing review."""
    return PreCommitReview(
        passed=False,
        message="Critical issue detected",
        concerns=["[CRITICAL] Dangerous change"],
        failed_gates=["infra"],
    )


# ---------------------------------------------------------------------------
# diff command
# ---------------------------------------------------------------------------


class TestDiffCommand:
    """Tests for the `diff` subcommand."""

    @patch("greybeard.precommit_cli.run_diff_review")
    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_diff_passes(self, mock_load, mock_run_review, runner, passed_review):
        mock_load.return_value = PreCommitConfig(enabled=True)
        mock_run_review.return_value = passed_review

        result = runner.invoke(cli, ["diff"])
        assert result.exit_code == 0

    @patch("greybeard.precommit_cli.run_diff_review")
    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_diff_fails_when_review_fails(self, mock_load, mock_run_review, runner, failed_review):
        mock_load.return_value = PreCommitConfig(enabled=True)
        mock_run_review.return_value = failed_review

        result = runner.invoke(cli, ["diff"])
        assert result.exit_code == 1

    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_diff_disabled_in_config(self, mock_load, runner):
        mock_load.return_value = PreCommitConfig(enabled=False)

        result = runner.invoke(cli, ["diff"])
        assert result.exit_code == 0
        assert "disabled" in result.output

    @patch("greybeard.precommit_cli.run_diff_review")
    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_diff_with_pack_option(self, mock_load, mock_run_review, runner, passed_review):
        mock_load.return_value = PreCommitConfig(enabled=True)
        mock_run_review.return_value = passed_review

        result = runner.invoke(cli, ["diff", "--pack", "on-call"])
        assert result.exit_code == 0
        mock_run_review.assert_called_once()
        _, kwargs = mock_run_review.call_args
        assert kwargs.get("pack") == "on-call" or mock_run_review.call_args[0][1] == "on-call"

    @patch("greybeard.precommit_cli.run_diff_review")
    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_diff_verbose_flag(self, mock_load, mock_run_review, runner, passed_review):
        mock_load.return_value = PreCommitConfig(enabled=True)
        mock_run_review.return_value = passed_review

        result = runner.invoke(cli, ["diff", "--verbose"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# check command
# ---------------------------------------------------------------------------


class TestCheckCommand:
    """Tests for the `check` subcommand."""

    @patch("greybeard.precommit_cli.run_risk_check")
    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_check_passes(self, mock_load, mock_run_check, runner, passed_review):
        mock_load.return_value = PreCommitConfig(enabled=True)
        mock_run_check.return_value = passed_review

        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 0

    @patch("greybeard.precommit_cli.run_risk_check")
    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_check_fails_when_gates_fail(self, mock_load, mock_run_check, runner, failed_review):
        mock_load.return_value = PreCommitConfig(enabled=True)
        mock_run_check.return_value = failed_review

        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 1

    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_check_disabled_in_config(self, mock_load, runner):
        mock_load.return_value = PreCommitConfig(enabled=False)

        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 0
        assert "disabled" in result.output

    @patch("greybeard.precommit_cli.run_risk_check")
    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_check_verbose_flag(self, mock_load, mock_run_check, runner, passed_review):
        mock_load.return_value = PreCommitConfig(enabled=True)
        mock_run_check.return_value = passed_review

        result = runner.invoke(cli, ["check", "--verbose"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# config init command
# ---------------------------------------------------------------------------


class TestConfigInitCommand:
    """Tests for the `config init` subcommand."""

    def test_config_init_creates_file(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["config", "init", "--path", "test-config.yaml"])
            assert result.exit_code == 0
            assert "Config initialized" in result.output
            assert Path("test-config.yaml").exists()

    def test_config_init_default_path(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["config", "init"])
            assert result.exit_code == 0
            assert Path(".greybeard-precommit.yaml").exists()


# ---------------------------------------------------------------------------
# config show command
# ---------------------------------------------------------------------------


class TestConfigShowCommand:
    """Tests for the `config show` subcommand."""

    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_config_show_displays_settings(self, mock_load, runner):
        mock_load.return_value = PreCommitConfig(
            enabled=True,
            default_pack="staff-core",
            fail_on_concerns="critical",
        )
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0

    @patch("greybeard.precommit_cli.PreCommitConfig.load")
    def test_config_show_with_risk_gates(self, mock_load, runner):
        mock_load.return_value = PreCommitConfig(
            enabled=True,
            risk_gates=[
                RiskGate(
                    name="infra",
                    patterns=["infra/*"],
                    fail_on_concerns="critical",
                )
            ],
        )
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# config edit command
# ---------------------------------------------------------------------------


class TestConfigEditCommand:
    """Tests for the `config edit` subcommand."""

    def test_config_edit_opens_editor(self, runner):
        with runner.isolated_filesystem():
            with patch("subprocess.run") as mock_subproc:
                mock_subproc.return_value = MagicMock(returncode=0)
                result = runner.invoke(cli, ["config", "edit", "--editor", "vim"])
                assert result.exit_code == 0
                assert "Config saved" in result.output

    def test_config_edit_creates_config_if_missing(self, runner):
        with runner.isolated_filesystem():
            assert not Path(".greybeard-precommit.yaml").exists()
            with patch("subprocess.run") as mock_subproc:
                mock_subproc.return_value = MagicMock(returncode=0)
                runner.invoke(cli, ["config", "edit", "--editor", "echo"])
                assert Path(".greybeard-precommit.yaml").exists()

    def test_config_edit_editor_not_found(self, runner):
        with runner.isolated_filesystem():
            with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
                result = runner.invoke(cli, ["config", "edit", "--editor", "nonexistent-editor"])
                assert result.exit_code == 1
                assert "not found" in result.output.lower() or "Editor not found" in result.output

    def test_config_edit_editor_error(self, runner):
        with runner.isolated_filesystem():
            import subprocess

            with patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "vim"),
            ):
                result = runner.invoke(cli, ["config", "edit", "--editor", "vim"])
                assert result.exit_code == 1

    @patch("greybeard.precommit_cli.os.environ", {"EDITOR": "nano"})
    def test_config_edit_uses_env_editor(self, runner):
        with runner.isolated_filesystem():
            with patch("subprocess.run") as mock_subproc:
                mock_subproc.return_value = MagicMock(returncode=0)
                result = runner.invoke(cli, ["config", "edit"])
                assert result.exit_code == 0
                call_args = mock_subproc.call_args
                assert "nano" in call_args[0][0]


# ---------------------------------------------------------------------------
# CLI group help
# ---------------------------------------------------------------------------


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_cli_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "greybeard" in result.output.lower()

    def test_diff_help(self, runner):
        result = runner.invoke(cli, ["diff", "--help"])
        assert result.exit_code == 0

    def test_check_help(self, runner):
        result = runner.invoke(cli, ["check", "--help"])
        assert result.exit_code == 0

    def test_config_help(self, runner):
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
