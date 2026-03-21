"""Tests for pre-commit hook integration."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from greybeard.precommit import (
    PreCommitConfig,
    PreCommitReview,
    RiskGate,
    analyze_review_output,
    extract_diff_context,
    format_review_output,
    get_applicable_gate,
    get_current_branch,
    get_staged_diff,
    get_staged_files,
    should_skip_file,
    should_skip_gate,
)


class TestRiskGate:
    """Test RiskGate dataclass."""

    def test_risk_gate_creation(self):
        """Test creating a risk gate."""
        gate = RiskGate(
            name="test-gate",
            patterns=["infra/*", "terraform/*"],
            fail_on_concerns="critical",
            required_packs=["platform-eng"],
        )
        assert gate.name == "test-gate"
        assert gate.patterns == ["infra/*", "terraform/*"]
        assert gate.fail_on_concerns == "critical"
        assert gate.required_packs == ["platform-eng"]

    def test_risk_gate_defaults(self):
        """Test risk gate defaults."""
        gate = RiskGate(name="simple")
        assert gate.patterns == []
        assert gate.fail_on_concerns == "critical"
        assert gate.required_packs == []
        assert gate.skip_if_branch == []


class TestPreCommitConfig:
    """Test PreCommitConfig loading and saving."""

    def test_default_config(self):
        """Test default config values."""
        config = PreCommitConfig()
        assert config.enabled is True
        assert config.default_pack == "staff-core"
        assert config.additional_packs == []
        assert config.fail_on_concerns == "critical"
        assert config.skip_unstaged is True
        assert config.max_context_lines == 500
        assert config.verbose is False

    def test_config_with_risk_gates(self):
        """Test config with risk gates."""
        config = PreCommitConfig(
            risk_gates=[
                RiskGate(
                    name="infra",
                    patterns=["infra/*"],
                    fail_on_concerns="critical",
                )
            ]
        )
        assert len(config.risk_gates) == 1
        assert config.risk_gates[0].name == "infra"

    def test_config_save_and_load(self):
        """Test saving and loading config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create and save
            original = PreCommitConfig(
                default_pack="platform-eng",
                additional_packs=["security-reviewer"],
                fail_on_concerns="high",
                verbose=True,
            )
            original.save(str(config_path))

            # Verify file exists
            assert config_path.exists()

            # Load and verify
            with config_path.open() as f:
                data = yaml.safe_load(f)

            assert data["default_pack"] == "platform-eng"
            assert data["additional_packs"] == ["security-reviewer"]
            assert data["fail_on_concerns"] == "high"
            assert data["verbose"] is True

    def test_config_with_gates_save_and_load(self):
        """Test saving and loading config with risk gates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            original = PreCommitConfig(
                risk_gates=[
                    RiskGate(
                        name="infra",
                        patterns=["infra/*"],
                        fail_on_concerns="critical",
                        required_packs=["platform-eng"],
                        skip_if_branch=["hotfix/*"],
                    )
                ]
            )
            original.save(str(config_path))

            # Load and verify gates
            with config_path.open() as f:
                data = yaml.safe_load(f)

            assert len(data["risk_gates"]) == 1
            gate = data["risk_gates"][0]
            assert gate["name"] == "infra"
            assert gate["patterns"] == ["infra/*"]
            assert gate["fail_on_concerns"] == "critical"
            assert gate["required_packs"] == ["platform-eng"]
            assert gate["skip_if_branch"] == ["hotfix/*"]


class TestFileMatching:
    """Test file pattern matching."""

    def test_should_skip_file_with_pattern(self):
        """Test skipping files matching patterns."""
        patterns = ["*.lock", ".venv/*", "node_modules/*"]
        assert should_skip_file("test.lock", patterns) is True
        assert should_skip_file(".venv/lib/python3.11/site.py", patterns) is True

    def test_should_skip_file_no_match(self):
        """Test files that don't match skip patterns."""
        patterns = ["*.lock", ".venv/*"]
        assert should_skip_file("src/main.py", patterns) is False
        assert should_skip_file("README.md", patterns) is False

    def test_should_skip_gate(self):
        """Test skipping gates by branch name."""
        gate = RiskGate(
            name="test",
            skip_if_branch=["hotfix/*", "emergency/*"],
        )
        assert should_skip_gate(gate, "hotfix/prod-issue") is True
        assert should_skip_gate(gate, "feat/new-feature") is False

    def test_get_applicable_gate(self):
        """Test finding applicable risk gate for a file."""
        gates = [
            RiskGate(
                name="infra",
                patterns=["infra/*", "terraform/*"],
            ),
            RiskGate(
                name="auth",
                patterns=["auth/*"],
            ),
        ]

        gate = get_applicable_gate("infra/kubernetes/deployment.yaml", gates, "main")
        assert gate is not None
        assert gate.name == "infra"

        gate = get_applicable_gate("auth/oauth.py", gates, "main")
        assert gate is not None
        assert gate.name == "auth"

        gate = get_applicable_gate("src/main.py", gates, "main")
        assert gate is None


class TestDiffProcessing:
    """Test diff context extraction and truncation."""

    def test_extract_diff_context_no_truncation(self):
        """Test diff extraction when under limit."""
        diff = "line1\nline2\nline3\nline4\nline5"
        result = extract_diff_context(diff, max_lines=10)
        assert result == diff

    def test_extract_diff_context_with_truncation(self):
        """Test diff extraction when over limit."""
        lines = [f"line {i}" for i in range(100)]
        diff = "\n".join(lines)
        result = extract_diff_context(diff, max_lines=50)

        assert "[... truncated ...]" in result
        assert len(result.split("\n")) <= 51


class TestReviewAnalysis:
    """Test review output analysis."""

    def test_analyze_review_output_none_threshold(self):
        """Test that 'none' threshold never fails."""
        review = "[CRITICAL] This will explode in production"
        passed, concerns = analyze_review_output(review, "none")
        assert passed is True
        assert concerns == []

    def test_analyze_review_output_critical_threshold(self):
        """Test critical threshold."""
        review = "[CRITICAL] System will fail\n[HIGH] Performance issue"
        passed, concerns = analyze_review_output(review, "critical")
        assert passed is False

    def test_analyze_review_output_high_threshold(self):
        """Test high threshold."""
        review = "[HIGH] This is a problem"
        passed, concerns = analyze_review_output(review, "high")
        assert passed is False


class TestPreCommitReview:
    """Test PreCommitReview dataclass."""

    def test_review_passed(self):
        """Test creating a passed review."""
        review = PreCommitReview(
            passed=True,
            message="All good!",
            concerns=[],
        )
        assert review.passed is True
        assert review.message == "All good!"

    def test_review_failed(self):
        """Test creating a failed review."""
        review = PreCommitReview(
            passed=False,
            message="Critical issues found",
            concerns=["Issue 1", "Issue 2"],
            failed_gates=["infra-gate"],
        )
        assert review.passed is False
        assert len(review.concerns) == 2

    def test_review_to_json(self):
        """Test serializing review to JSON."""
        import json

        review = PreCommitReview(
            passed=True,
            message="Test",
            concerns=["a", "b"],
        )
        json_str = review.to_json()
        data = json.loads(json_str)
        assert data["passed"] is True


class TestFormatting:
    """Test review output formatting."""

    def test_format_review_passed(self):
        """Test formatting a passed review."""
        review = PreCommitReview(
            passed=True,
            message="Review passed",
        )
        output = format_review_output(review)
        assert "✓" in output

    def test_format_review_failed(self):
        """Test formatting a failed review."""
        review = PreCommitReview(
            passed=False,
            message="Review failed",
            concerns=["Issue 1"],
        )
        output = format_review_output(review)
        assert "✗" in output


class TestGitIntegration:
    """Test git command wrappers."""

    @patch("subprocess.run")
    def test_get_staged_files(self, mock_run):
        """Test getting staged files."""
        mock_run.return_value = MagicMock(stdout="file1.py\nfile2.py\n", stderr="", returncode=0)
        files = get_staged_files()
        assert files == ["file1.py", "file2.py"]

    @patch("subprocess.run")
    def test_get_staged_files_empty(self, mock_run):
        """Test getting staged files when empty."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        files = get_staged_files()
        assert files == []

    @patch("subprocess.run")
    def test_get_staged_diff(self, mock_run):
        """Test getting staged diff."""
        diff_text = "diff --git a/file.py b/file.py\n+new line"
        mock_run.return_value = MagicMock(stdout=diff_text, stderr="", returncode=0)
        diff = get_staged_diff()
        assert diff == diff_text

    @patch("subprocess.run")
    def test_get_current_branch(self, mock_run):
        """Test getting current branch."""
        mock_run.return_value = MagicMock(stdout="feat/new-feature\n", stderr="", returncode=0)
        branch = get_current_branch()
        assert branch == "feat/new-feature"


class TestIntegration:
    """Integration tests."""

    def test_end_to_end_config_flow(self):
        """Test full configuration workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".greybeard-precommit.yaml"

            config = PreCommitConfig(
                default_pack="platform-eng",
                additional_packs=["security-reviewer"],
                fail_on_concerns="high",
                risk_gates=[
                    RiskGate(
                        name="infra",
                        patterns=["infra/*"],
                        fail_on_concerns="critical",
                    )
                ],
                excluded_paths=["*.lock", ".venv/*"],
            )

            config.save(str(config_path))

            with config_path.open() as f:
                data = yaml.safe_load(f)

            assert data["default_pack"] == "platform-eng"
            assert data["additional_packs"] == ["security-reviewer"]
            assert len(data["risk_gates"]) == 1
