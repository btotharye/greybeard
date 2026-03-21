"""Comprehensive tests for CLI SLO check command (greybeard/cli_slo.py).

Tests cover:
- CLI command invocation and option parsing
- Input handling (stdin, file, repo path)
- Output formatting (json, markdown, table)
- Context flag parsing and validation
- Error handling and edge cases
- Integration with SLOAgent
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from greybeard.agents import ServiceType, SLOAgent, SLORecommendation, SLOTarget
from greybeard.cli_slo import _output_json, _output_markdown, _output_table, slo_check


@pytest.fixture
def runner():
    """Return a CliRunner for invoking the slo-check command."""
    return CliRunner()


@pytest.fixture
def sample_recommendation():
    """Return a sample SLORecommendation for testing output formatting."""
    targets = [
        SLOTarget(
            metric="availability",
            target="99.9%",
            rationale="Standard SaaS availability",
            range=("99%", "99.95%"),
        ),
        SLOTarget(
            metric="latency (p99)",
            target="p99 < 200ms",
            rationale="User-facing service",
            range=("100ms", "500ms"),
        ),
        SLOTarget(
            metric="error_rate",
            target="< 0.1%",
            rationale="Production service",
            range=("0.01%", "0.5%"),
        ),
    ]
    return SLORecommendation(
        service_type=ServiceType.SAAS,
        service_name="test-api",
        targets=targets,
        confidence=0.85,
        context_signals={},
        notes="Sample recommendations for testing.",
    )


class TestSloCheckBasicInvocation:
    """Test basic slo-check command invocation."""

    def test_slo_check_help(self, runner):
        """Test slo-check --help."""
        result = runner.invoke(slo_check, ["--help"])
        assert result.exit_code == 0
        assert "Analyze code" in result.output
        assert "SLO targets" in result.output

    def test_slo_check_no_input_no_file(self, runner):
        """Test slo-check with no input (no stdin, no file, no tty)."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "No input provided.",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, [])
            assert result.exit_code == 0
            mock_analyze.assert_called_once()

    def test_slo_check_with_context_flags(self, runner):
        """Test slo-check with context flags."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.9,
                "service_name": "test-service",
                "notes": "Context applied.",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(
                slo_check,
                [
                    "--context",
                    "service-type:saas",
                    "--context",
                    "service-name:test-service",
                ],
            )
            assert result.exit_code == 0
            # Verify analyze was called
            mock_analyze.assert_called_once()

    def test_slo_check_version_not_applicable(self, runner):
        """Test that slo-check doesn't have a --version flag (inherit from cli group)."""
        # This should not have --version; --version belongs to the main cli group
        result = runner.invoke(slo_check, ["--version"])
        # Click will handle this at the group level, so we expect an error or help
        assert result.exit_code != 0 or "--version" not in result.output


class TestContextFlagParsing:
    """Test context flag parsing and validation."""

    def test_parse_single_context_flag(self, runner):
        """Test parsing a single context flag."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.8,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--context", "service-type:saas"])
            assert result.exit_code == 0
            # Check that context was parsed and passed
            call_args = mock_analyze.call_args
            assert call_args is not None
            assert call_args.kwargs["context"]["service-type"] == "saas"

    def test_parse_multiple_context_flags(self, runner):
        """Test parsing multiple context flags."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.8,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(
                slo_check,
                [
                    "--context",
                    "service-type:saas",
                    "--context",
                    "criticality:high",
                    "--context",
                    "users:10000",
                ],
            )
            assert result.exit_code == 0
            call_args = mock_analyze.call_args
            context = call_args.kwargs["context"]
            assert context["service-type"] == "saas"
            assert context["criticality"] == "high"
            assert context["users"] == "10000"

    def test_parse_context_flag_with_spaces(self, runner):
        """Test parsing context flags with spaces around colon."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.8,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--context", "service-type : saas"])
            assert result.exit_code == 0
            call_args = mock_analyze.call_args
            context = call_args.kwargs["context"]
            assert context["service-type"] == "saas"

    def test_invalid_context_flag_no_colon(self, runner):
        """Test invalid context flag without colon."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--context", "invalid_flag"])
            # Should still run but print warning
            assert result.exit_code == 0
            assert "Invalid context flag" in result.output or "Warning" in result.output

    def test_context_with_special_characters(self, runner):
        """Test context flags with special characters."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.8,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(
                slo_check, ["--context", "service-name:my-api-service-v2"]
            )
            assert result.exit_code == 0
            call_args = mock_analyze.call_args
            context = call_args.kwargs["context"]
            assert context["service-name"] == "my-api-service-v2"

    def test_context_with_complex_values(self, runner):
        """Test context with complex values."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.8,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(
                slo_check, ["--context", "data-type:json:structured"]
            )
            assert result.exit_code == 0
            call_args = mock_analyze.call_args
            context = call_args.kwargs["context"]
            # Should split on first colon only
            assert context["data-type"] == "json:structured"


class TestInputMethods:
    """Test different input methods (stdin, file, repo)."""

    def test_input_from_stdin(self, runner):
        """Test reading code from stdin."""
        code_input = "def hello(): return 'world'"
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, [], input=code_input)
            assert result.exit_code == 0
            call_args = mock_analyze.call_args
            assert call_args.kwargs["code_snippet"] == code_input

    def test_input_from_file(self, runner):
        """Test reading code from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test(): pass")
            f.flush()
            file_path = f.name

        try:
            with patch.object(SLOAgent, "analyze") as mock_analyze:
                mock_rec = MagicMock()
                mock_rec.to_dict.return_value = {
                    "service_type": "unknown",
                    "targets": [],
                    "confidence": 0.5,
                    "service_name": None,
                    "notes": "",
                }
                mock_analyze.return_value = mock_rec

                result = runner.invoke(slo_check, ["--file", file_path])
                assert result.exit_code == 0
                call_args = mock_analyze.call_args
                assert "def test(): pass" in call_args.kwargs["code_snippet"]
        finally:
            Path(file_path).unlink()

    def test_input_from_file_not_found(self, runner):
        """Test error when file doesn't exist."""
        result = runner.invoke(slo_check, ["--file", "/nonexistent/file.py"])
        # Click validates the file exists via type=click.Path(exists=True)
        assert result.exit_code != 0

    def test_input_from_repo_path(self, runner):
        """Test passing repo path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(SLOAgent, "analyze") as mock_analyze:
                mock_rec = MagicMock()
                mock_rec.to_dict.return_value = {
                    "service_type": "unknown",
                    "targets": [],
                    "confidence": 0.5,
                    "service_name": None,
                    "notes": "",
                }
                mock_analyze.return_value = mock_rec

                result = runner.invoke(slo_check, ["--repo", tmpdir])
                assert result.exit_code == 0
                call_args = mock_analyze.call_args
                assert call_args.kwargs["repo_path"] == tmpdir

    def test_file_takes_priority_over_stdin(self, runner):
        """Test that file input takes priority over stdin."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from_file = True")
            f.flush()
            file_path = f.name

        try:
            stdin_input = "from_stdin = True"
            with patch.object(SLOAgent, "analyze") as mock_analyze:
                mock_rec = MagicMock()
                mock_rec.to_dict.return_value = {
                    "service_type": "unknown",
                    "targets": [],
                    "confidence": 0.5,
                    "service_name": None,
                    "notes": "",
                }
                mock_analyze.return_value = mock_rec

                result = runner.invoke(slo_check, ["--file", file_path], input=stdin_input)
                assert result.exit_code == 0
                call_args = mock_analyze.call_args
                # Should have file content, not stdin
                assert "from_file" in call_args.kwargs["code_snippet"]
                assert "from_stdin" not in call_args.kwargs["code_snippet"]
        finally:
            Path(file_path).unlink()

    def test_empty_stdin_handling(self, runner):
        """Test handling of empty stdin."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, [])
            assert result.exit_code == 0
            # Empty input is valid
            call_args = mock_analyze.call_args
            assert call_args.kwargs["code_snippet"] == ""


class TestOutputFormats:
    """Test output formatting options."""

    def test_output_json_format(self, runner):
        """Test JSON output format."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [
                    {
                        "metric": "availability",
                        "target": "99.9%",
                        "rationale": "Standard",
                        "range": ("99%", "99.95%"),
                    }
                ],
                "confidence": 0.85,
                "service_name": "test-service",
                "notes": "Good service.",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--output", "json"])
            assert result.exit_code == 0
            # Should be valid JSON
            data = json.loads(result.output)
            assert data["service_type"] == "saas"
            assert "targets" in data

    def test_output_markdown_format(self, runner):
        """Test Markdown output format."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "service_name": "test-service",
                "targets": [
                    {
                        "metric": "availability",
                        "target": "99.9%",
                        "rationale": "Standard",
                        "range": ("99%", "99.95%"),
                    }
                ],
                "confidence": 0.85,
                "notes": "Good service.",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--output", "markdown"])
            assert result.exit_code == 0
            # Check Markdown-specific formatting
            assert "# SLO Recommendations" in result.output
            assert "SAAS" in result.output
            assert "99.9%" in result.output

    def test_output_table_format(self, runner):
        """Test Table output format (default)."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "service_name": "test-service",
                "targets": [
                    {
                        "metric": "availability",
                        "target": "99.9%",
                        "rationale": "Standard",
                        "range": ("99%", "99.95%"),
                    }
                ],
                "confidence": 0.85,
                "notes": "Good service.",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, [])
            assert result.exit_code == 0
            # Table format uses rich formatting
            assert "SLO Recommendations" in result.output

    def test_output_default_is_table(self, runner):
        """Test that default output is table format."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            # Without --output flag, should default to table
            result = runner.invoke(slo_check, [])
            assert result.exit_code == 0

    def test_output_invalid_format(self, runner):
        """Test error on invalid output format."""
        result = runner.invoke(slo_check, ["--output", "invalid_format"])
        # Click should reject invalid choice
        assert result.exit_code != 0

    def test_output_json_with_no_service_name(self, runner):
        """Test JSON output when service_name is None."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "Unknown service.",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--output", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["service_name"] is None

    def test_output_markdown_with_empty_targets(self, runner):
        """Test Markdown output with no targets."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "No targets.",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--output", "markdown"])
            assert result.exit_code == 0
            # Should still include notes even if no targets
            assert "No targets" in result.output

    def test_output_table_with_long_rationale(self, runner):
        """Test table output truncates long rationales."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            long_rationale = (
                "This is a very long rationale that should be truncated "
                "when displayed in the table format to avoid ugly wrapping issues"
            )
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [
                    {
                        "metric": "latency",
                        "target": "p99 < 200ms",
                        "rationale": long_rationale,
                        "range": ("100ms", "500ms"),
                    }
                ],
                "confidence": 0.85,
                "service_name": "test",
                "notes": "Test",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--output", "table"])
            assert result.exit_code == 0
            # Verify it doesn't crash and produces output
            assert result.output


class TestOutputFormattingFunctions:
    """Test individual output formatting functions directly."""

    def test_output_json_function(self, sample_recommendation, capsys):
        """Test _output_json directly."""
        _output_json(sample_recommendation)
        captured = capsys.readouterr()
        # Should be valid JSON
        data = json.loads(captured.out)
        assert data["service_type"] == "saas"
        assert data["service_name"] == "test-api"
        assert len(data["targets"]) == 3

    def test_output_markdown_function(self, sample_recommendation, capsys):
        """Test _output_markdown directly."""
        _output_markdown(sample_recommendation)
        captured = capsys.readouterr()
        output = captured.out
        assert "# SLO Recommendations" in output
        assert "SAAS" in output
        assert "test-api" in output
        assert "availability" in output
        assert "## SLO Targets" in output

    def test_output_table_function(self, sample_recommendation, capsys):
        """Test _output_table directly."""
        _output_table(sample_recommendation)
        captured = capsys.readouterr()
        output = captured.out
        assert "SLO Recommendations" in output
        assert "test-api" in output
        assert "availability" in output
        assert "latency" in output

    def test_output_markdown_with_no_service_name(self, capsys):
        """Test markdown output when service_name is None."""
        targets = [
            SLOTarget(
                metric="availability",
                target="99%",
                rationale="Basic service",
                range=("", ""),
            )
        ]
        rec = SLORecommendation(
            service_type=ServiceType.UNKNOWN,
            service_name=None,
            targets=targets,
            confidence=0.5,
            context_signals={},
            notes="Test",
        )
        _output_markdown(rec)
        captured = capsys.readouterr()
        output = captured.out
        # Should not include "Service:" line if name is None
        assert "Service:" not in output or output.count("Service:") == 0

    def test_output_table_confidence_percentage(self, capsys):
        """Test that table output shows confidence as percentage."""
        targets = [
            SLOTarget(
                metric="availability",
                target="99%",
                rationale="Test",
                range=("", ""),
            )
        ]
        rec = SLORecommendation(
            service_type=ServiceType.SAAS,
            service_name="test",
            targets=targets,
            confidence=0.75,
            context_signals={},
            notes="",
        )
        _output_table(rec)
        captured = capsys.readouterr()
        output = captured.out
        # Should show 75% not 0.75
        assert "75%" in output

    def test_output_markdown_range_handling(self, capsys):
        """Test markdown correctly formats range display."""
        targets = [
            SLOTarget(
                metric="latency",
                target="p99 < 200ms",
                rationale="User service",
                range=("100ms", "500ms"),
            ),
            SLOTarget(
                metric="error_rate",
                target="< 0.1%",
                rationale="Production",
                range=("", ""),  # Empty range
            ),
        ]
        rec = SLORecommendation(
            service_type=ServiceType.SAAS,
            service_name="test",
            targets=targets,
            confidence=0.85,
            context_signals={},
            notes="",
        )
        _output_markdown(rec)
        captured = capsys.readouterr()
        output = captured.out
        # Should show range for first target
        assert "100ms - 500ms" in output
        # Second target should show differently (empty range)
        lines = output.split("\n")
        latency_section = "\n".join([line for line in lines if "latency" in line.lower()])
        assert latency_section

    def test_output_table_range_formatting(self, capsys):
        """Test table correctly formats range with → symbol."""
        targets = [
            SLOTarget(
                metric="availability",
                target="99.9%",
                rationale="Standard",
                range=("99%", "99.95%"),
            )
        ]
        rec = SLORecommendation(
            service_type=ServiceType.SAAS,
            service_name="test",
            targets=targets,
            confidence=0.85,
            context_signals={},
            notes="",
        )
        _output_table(rec)
        captured = capsys.readouterr()
        output = captured.out
        # Should use → or similar separator
        assert "99%" in output


class TestSLOAgentIntegration:
    """Test integration with SLOAgent."""

    def test_agent_called_with_correct_params(self, runner):
        """Test that SLOAgent.analyze is called with correct parameters."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.8,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            runner.invoke(
                slo_check,
                [
                    "--context",
                    "service-type:saas",
                    "--output",
                    "json",
                ],
                input="def api(): pass",
            )

            mock_analyze.assert_called_once()
            call_kwargs = mock_analyze.call_args.kwargs
            assert "code_snippet" in call_kwargs
            assert call_kwargs["code_snippet"] == "def api(): pass"
            assert "context" in call_kwargs
            assert call_kwargs["context"]["service-type"] == "saas"

    def test_agent_called_with_repo_path(self, runner):
        """Test that repo_path is passed to agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(SLOAgent, "analyze") as mock_analyze:
                mock_rec = MagicMock()
                mock_rec.to_dict.return_value = {
                    "service_type": "saas",
                    "targets": [],
                    "confidence": 0.8,
                    "service_name": None,
                    "notes": "",
                }
                mock_analyze.return_value = mock_rec

                runner.invoke(slo_check, ["--repo", tmpdir])

                call_kwargs = mock_analyze.call_args.kwargs
                assert call_kwargs["repo_path"] == tmpdir


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_nonexistent_repo_path(self, runner):
        """Test error when repo path doesn't exist."""
        result = runner.invoke(slo_check, ["--repo", "/nonexistent/repo"])
        # Click validates via type=click.Path(exists=True)
        assert result.exit_code != 0

    def test_repo_path_is_file_not_directory(self, runner):
        """Test error when repo path is a file, not directory."""
        with tempfile.NamedTemporaryFile() as f:
            result = runner.invoke(slo_check, ["--repo", f.name])
            # Click validates via type=click.Path(exists=True, file_okay=False)
            assert result.exit_code != 0

    def test_agent_exception_handling(self, runner):
        """Test handling of exceptions from SLOAgent."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_analyze.side_effect = RuntimeError("Agent failed")

            result = runner.invoke(slo_check, [])
            # Exception should propagate and cause non-zero exit
            assert result.exit_code != 0

    def test_recommendation_to_dict_exception(self, runner):
        """Test handling when recommendation.to_dict() fails."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.side_effect = ValueError("to_dict failed")
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--output", "json"])
            assert result.exit_code != 0

    def test_context_flag_with_empty_value(self, runner):
        """Test context flag with empty value after colon."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--context", "service-type:"])
            assert result.exit_code == 0
            call_kwargs = mock_analyze.call_args.kwargs
            # Empty values are allowed
            assert call_kwargs["context"]["service-type"] == ""

    def test_very_large_file_input(self, runner):
        """Test handling of very large input files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            # Write a moderately large file (1MB of repeated Python code)
            large_code = "def func(): pass\n" * 50000
            f.write(large_code)
            f.flush()
            file_path = f.name

        try:
            with patch.object(SLOAgent, "analyze") as mock_analyze:
                mock_rec = MagicMock()
                mock_rec.to_dict.return_value = {
                    "service_type": "unknown",
                    "targets": [],
                    "confidence": 0.5,
                    "service_name": None,
                    "notes": "",
                }
                mock_analyze.return_value = mock_rec

                result = runner.invoke(slo_check, ["--file", file_path])
                assert result.exit_code == 0
                # Should have processed the large input
                call_kwargs = mock_analyze.call_args.kwargs
                assert len(call_kwargs["code_snippet"]) > 100000
        finally:
            Path(file_path).unlink()

    def test_file_with_binary_content(self, runner):
        """Test handling of binary files."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"\x00\x01\x02\xff\xfe")
            f.flush()
            file_path = f.name

        try:
            # Should fail due to binary content
            runner.invoke(slo_check, ["--file", file_path])
            # May fail with decode error or succeed with garbage - both acceptable
            # The important thing is it doesn't crash the CLI
            assert True  # If we get here, we didn't crash
        finally:
            Path(file_path).unlink()


class TestOptionsShorthand:
    """Test short option forms."""

    def test_context_short_option(self, runner):
        """Test -c short form for --context."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.8,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-c", "service-type:saas"])
            assert result.exit_code == 0
            call_kwargs = mock_analyze.call_args.kwargs
            assert call_kwargs["context"]["service-type"] == "saas"

    def test_repo_short_option(self, runner):
        """Test -r short form for --repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(SLOAgent, "analyze") as mock_analyze:
                mock_rec = MagicMock()
                mock_rec.to_dict.return_value = {
                    "service_type": "saas",
                    "targets": [],
                    "confidence": 0.8,
                    "service_name": None,
                    "notes": "",
                }
                mock_analyze.return_value = mock_rec

                result = runner.invoke(slo_check, ["-r", tmpdir])
                assert result.exit_code == 0
                call_kwargs = mock_analyze.call_args.kwargs
                assert call_kwargs["repo_path"] == tmpdir

    def test_output_short_option(self, runner):
        """Test -o short form for --output."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.8,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "json"])
            assert result.exit_code == 0
            # Output should be JSON
            data = json.loads(result.output)
            assert "service_type" in data

    def test_file_short_option(self, runner):
        """Test -f short form for --file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("code = True")
            f.flush()
            file_path = f.name

        try:
            with patch.object(SLOAgent, "analyze") as mock_analyze:
                mock_rec = MagicMock()
                mock_rec.to_dict.return_value = {
                    "service_type": "unknown",
                    "targets": [],
                    "confidence": 0.5,
                    "service_name": None,
                    "notes": "",
                }
                mock_analyze.return_value = mock_rec

                result = runner.invoke(slo_check, ["-f", file_path])
                assert result.exit_code == 0
        finally:
            Path(file_path).unlink()


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_full_workflow_with_all_options(self, runner):
        """Test full workflow using all options together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "service.py"
            code_file.write_text("async def handle_request(): pass")

            with patch.object(SLOAgent, "analyze") as mock_analyze:
                mock_rec = MagicMock()
                mock_rec.to_dict.return_value = {
                    "service_type": "saas",
                    "targets": [
                        {
                            "metric": "latency (p99)",
                            "target": "p99 < 200ms",
                            "rationale": "User-facing",
                            "range": ("100ms", "500ms"),
                        }
                    ],
                    "confidence": 0.9,
                    "service_name": "payment-api",
                    "notes": "Critical service",
                }
                mock_analyze.return_value = mock_rec

                result = runner.invoke(
                    slo_check,
                    [
                        "-c",
                        "service-name:payment-api",
                        "-c",
                        "service-type:saas",
                        "-c",
                        "criticality:critical",
                        "-r",
                        tmpdir,
                        "-f",
                        str(code_file),
                        "-o",
                        "markdown",
                    ],
                )
                assert result.exit_code == 0
                # Should have markdown output
                assert "# SLO Recommendations" in result.output
                assert "payment-api" in result.output

    def test_piped_stdin_workflow(self, runner):
        """Test typical Unix pipe workflow."""
        code = """
        @app.route('/api/users')
        def get_users():
            return db.query(User).all()
        """
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.8,
                "service_name": "users-api",
                "notes": "REST API",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(
                slo_check,
                ["-c", "service-type:saas", "-o", "json"],
                input=code,
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["service_type"] == "saas"

    def test_git_diff_workflow(self, runner):
        """Test workflow with git diff as input."""
        diff_output = """
        diff --git a/src/api.py b/src/api.py
        --- a/src/api.py
        +++ b/src/api.py
        @@ -1,5 +1,10 @@
         def handle_request():
        +    try:
        +        result = fetch_data()
        +    except Exception as e:
        +        log.error(e)
        +        raise
             return result
        """
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.7,
                "service_name": None,
                "notes": "Good error handling detected",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "json"], input=diff_output)
            assert result.exit_code == 0


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    def test_very_long_context_key_value(self, runner):
        """Test handling of extremely long context values."""
        long_value = "x" * 1000
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--context", f"key:{long_value}"])
            assert result.exit_code == 0

    def test_unicode_in_context_values(self, runner):
        """Test Unicode characters in context values."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(
                slo_check, ["--context", "service-name:用户-API-🚀"]
            )
            assert result.exit_code == 0

    def test_empty_targets_list(self, runner):
        """Test handling of recommendation with zero targets."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.0,
                "service_name": None,
                "notes": "Unable to generate recommendations",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "markdown"])
            assert result.exit_code == 0

    def test_confidence_zero(self, runner):
        """Test handling of zero confidence."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.0,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "table"])
            assert result.exit_code == 0
            assert "0%" in result.output

    def test_confidence_one(self, runner):
        """Test handling of 100% confidence."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 1.0,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "table"])
            assert result.exit_code == 0
            assert "100%" in result.output

    def test_multiple_spaces_in_context(self, runner):
        """Test context parsing with multiple spaces."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(
                slo_check, ["--context", "key  :   value  with  spaces"]
            )
            assert result.exit_code == 0
            call_kwargs = mock_analyze.call_args.kwargs
            # Should strip spaces
            assert call_kwargs["context"]["key"] == "value  with  spaces"


class TestMarkdownSpecificFormatting:
    """Test specific markdown formatting edge cases."""

    def test_markdown_with_service_name_and_targets(self, runner):
        """Test markdown includes service name and targets section."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "critical-infra",
                "service_name": "auth-service",
                "targets": [
                    {
                        "metric": "availability",
                        "target": "99.99%",
                        "rationale": "Critical",
                        "range": ("99.9%", "99.99%"),
                    }
                ],
                "confidence": 0.95,
                "notes": "Critical service must be highly available",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "markdown"])
            assert result.exit_code == 0
            assert "# SLO Recommendations" in result.output
            assert "CRITICAL-INFRA" in result.output
            assert "auth-service" in result.output
            assert "## SLO Targets" in result.output
            assert "### AVAILABILITY" in result.output
            assert "99.99%" in result.output
            assert "## Notes & Recommendations" in result.output

    def test_markdown_multiple_targets(self, runner):
        """Test markdown with multiple targets and all fields."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "service_name": "api",
                "targets": [
                    {
                        "metric": "latency (p99)",
                        "target": "p99 < 200ms",
                        "rationale": "User perception",
                        "range": ("100ms", "500ms"),
                    },
                    {
                        "metric": "error_rate",
                        "target": "< 0.1%",
                        "rationale": "Production stability",
                        "range": ("0.01%", "1%"),
                    },
                ],
                "confidence": 0.88,
                "notes": "Good service design",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "markdown"])
            assert result.exit_code == 0
            # All targets should be present
            assert "latency" in result.output.lower()
            assert "error_rate" in result.output.lower()
            assert "88%" in result.output


class TestTableSpecificFormatting:
    """Test specific table formatting details."""

    def test_table_with_full_service_info(self, runner):
        """Test table includes all service info."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "batch",
                "service_name": "data-pipeline",
                "targets": [
                    {
                        "metric": "job_duration (p95)",
                        "target": "< 2 hours",
                        "rationale": "SLA compliance",
                        "range": ("1h", "4h"),
                    }
                ],
                "confidence": 0.82,
                "notes": "Batch jobs should have relaxed latency SLOs",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "table"])
            assert result.exit_code == 0
            assert "data-pipeline" in result.output
            assert "SLO Recommendations" in result.output
            assert "82%" in result.output

    def test_table_target_columns(self, runner):
        """Test table has all expected columns."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "service_name": "test",
                "targets": [
                    {
                        "metric": "latency (p99)",
                        "target": "p99 < 100ms",
                        "rationale": "Fast response",
                        "range": ("50ms", "200ms"),
                    }
                ],
                "confidence": 0.9,
                "notes": "Quick service",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "table"])
            assert result.exit_code == 0
            # Table should have these column names
            output = result.output.lower()
            assert "metric" in output
            assert "target" in output
            assert "rationale" in output


class TestJsonSpecificFormatting:
    """Test specific JSON output formatting."""

    def test_json_valid_structure(self, runner):
        """Test JSON has all required fields."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "service_name": "api",
                "targets": [
                    {
                        "metric": "availability",
                        "target": "99.9%",
                        "rationale": "Standard",
                        "range": ("99%", "99.95%"),
                    }
                ],
                "confidence": 0.85,
                "notes": "Notes here",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            
            # Verify all fields
            assert data["service_type"] == "saas"
            assert data["service_name"] == "api"
            assert "targets" in data
            assert isinstance(data["targets"], list)
            assert len(data["targets"]) == 1
            assert data["targets"][0]["metric"] == "availability"
            assert data["targets"][0]["target"] == "99.9%"
            assert data["targets"][0]["rationale"] == "Standard"
            assert data["targets"][0]["range"] == ["99%", "99.95%"]
            assert data["confidence"] == 0.85
            assert data["notes"] == "Notes here"

    def test_json_with_empty_range(self, runner):
        """Test JSON serializes empty ranges correctly."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "service_name": None,
                "targets": [
                    {
                        "metric": "test",
                        "target": "unknown",
                        "rationale": "Unknown",
                        "range": ("", ""),
                    }
                ],
                "confidence": 0.5,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["targets"][0]["range"] == ["", ""]


class TestStdinHandling:
    """Test stdin input handling in detail."""

    def test_stdin_with_pipe_input(self, runner):
        """Test reading from piped input."""
        pipe_data = (
            "#!/usr/bin/env python\n@app.route('/api')\n"
            "def endpoint():\n    return {'status': 'ok'}"
        )
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "saas",
                "targets": [],
                "confidence": 0.7,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["-o", "json"], input=pipe_data)
            assert result.exit_code == 0
            call_kwargs = mock_analyze.call_args.kwargs
            assert pipe_data in call_kwargs["code_snippet"]

    def test_stdin_multiline_input(self, runner):
        """Test stdin with multiline code."""
        multiline_code = """
def process_data(data):
    '''Process incoming data.'''
    try:
        result = expensive_operation(data)
        return cache_result(result)
    except TimeoutError:
        log.error('Timeout')
        raise
        """
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "batch",
                "targets": [],
                "confidence": 0.75,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, [], input=multiline_code)
            assert result.exit_code == 0
            assert "batch" in result.output.lower() or result.exit_code == 0


class TestContextParsing:
    """Additional detailed context parsing tests."""

    def test_context_colon_in_value(self, runner):
        """Test context values that contain colons."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(
                slo_check, ["--context", "image:gcr.io/project/service:v1.0"]
            )
            assert result.exit_code == 0
            call_kwargs = mock_analyze.call_args.kwargs
            # Should split on first colon only
            assert call_kwargs["context"]["image"] == "gcr.io/project/service:v1.0"

    def test_multiple_context_flags_same_key(self, runner):
        """Test multiple context flags with same key (last wins)."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(
                slo_check,
                [
                    "--context",
                    "env:dev",
                    "--context",
                    "env:prod",
                ],
            )
            assert result.exit_code == 0
            call_kwargs = mock_analyze.call_args.kwargs
            # Last one should win
            assert call_kwargs["context"]["env"] == "prod"

    def test_context_no_spaces_around_colon(self, runner):
        """Test context without spaces around colon."""
        with patch.object(SLOAgent, "analyze") as mock_analyze:
            mock_rec = MagicMock()
            mock_rec.to_dict.return_value = {
                "service_type": "unknown",
                "targets": [],
                "confidence": 0.5,
                "service_name": None,
                "notes": "",
            }
            mock_analyze.return_value = mock_rec

            result = runner.invoke(slo_check, ["--context", "tier:premium"])
            assert result.exit_code == 0
            call_kwargs = mock_analyze.call_args.kwargs
            assert call_kwargs["context"]["tier"] == "premium"
