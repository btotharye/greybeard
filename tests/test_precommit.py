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
    run_diff_review,
    run_risk_check,
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

    @patch("greybeard.precommit.subprocess.run")
    def test_get_staged_files(self, mock_run):
        """Test getting staged files."""
        mock_run.return_value = MagicMock(stdout="file1.py\nfile2.py\n", stderr="", returncode=0)
        files = get_staged_files()
        assert files == ["file1.py", "file2.py"]

    @patch("greybeard.precommit.subprocess.run")
    def test_get_staged_files_empty(self, mock_run):
        """Test getting staged files when empty."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        files = get_staged_files()
        assert files == []

    @patch("greybeard.precommit.subprocess.run")
    def test_get_staged_diff(self, mock_run):
        """Test getting staged diff."""
        diff_text = "diff --git a/file.py b/file.py\n+new line"
        mock_run.return_value = MagicMock(stdout=diff_text, stderr="", returncode=0)
        diff = get_staged_diff()
        assert diff == diff_text

    @patch("greybeard.precommit.subprocess.run")
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


# ---------------------------------------------------------------------------
# PreCommitConfig.load() from file
# ---------------------------------------------------------------------------


class TestPreCommitConfigLoad:
    """Tests for PreCommitConfig.load() that reads from an actual YAML file."""

    def test_load_from_file(self):
        """Test loading config from a YAML file in the working directory."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".greybeard-precommit.yaml"
            data = {
                "enabled": False,
                "default_pack": "on-call",
                "additional_packs": ["security-reviewer"],
                "fail_on_concerns": "high",
                "skip_unstaged": False,
                "max_context_lines": 100,
                "verbose": True,
                "allow_empty_commits": True,
                "excluded_paths": ["*.lock"],
                "risk_gates": [
                    {
                        "name": "infra",
                        "patterns": ["infra/*"],
                        "fail_on_concerns": "critical",
                        "required_packs": ["platform-eng"],
                        "skip_if_branch": ["hotfix/*"],
                    }
                ],
            }
            with config_path.open("w") as f:
                yaml.dump(data, f)

            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = PreCommitConfig.load()
            finally:
                os.chdir(original_dir)

        assert config.enabled is False
        assert config.default_pack == "on-call"
        assert config.additional_packs == ["security-reviewer"]
        assert config.fail_on_concerns == "high"
        assert config.skip_unstaged is False
        assert config.max_context_lines == 100
        assert config.verbose is True
        assert config.allow_empty_commits is True
        assert config.excluded_paths == ["*.lock"]
        assert len(config.risk_gates) == 1
        assert config.risk_gates[0].name == "infra"
        assert config.risk_gates[0].skip_if_branch == ["hotfix/*"]

    def test_load_defaults_when_no_file(self):
        """Test that load() returns defaults when no config file exists."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = PreCommitConfig.load()
            finally:
                os.chdir(original_dir)

        assert config.enabled is True
        assert config.default_pack == "staff-core"


# ---------------------------------------------------------------------------
# get_staged_diff with file_path
# ---------------------------------------------------------------------------


class TestStagedDiffWithFilePath:
    """Test get_staged_diff with a specific file path."""

    @patch("subprocess.run")
    def test_get_staged_diff_specific_file(self, mock_run):
        """Test getting staged diff for a specific file."""
        diff_text = "diff --git a/foo.py b/foo.py\n+added line"
        mock_run.return_value = MagicMock(stdout=diff_text, stderr="")
        diff = get_staged_diff(file_path="foo.py")
        assert diff == diff_text
        call_args = mock_run.call_args[0][0]
        assert "foo.py" in call_args


# ---------------------------------------------------------------------------
# get_applicable_gate with skipped gate
# ---------------------------------------------------------------------------


class TestApplicableGateSkipped:
    """Test get_applicable_gate when a gate is skipped due to branch."""

    def test_skips_gate_on_hotfix_branch(self):
        """Gate should be skipped on hotfix branch."""
        gates = [
            RiskGate(
                name="infra",
                patterns=["infra/*"],
                fail_on_concerns="critical",
                skip_if_branch=["hotfix/*"],
            )
        ]
        gate = get_applicable_gate("infra/deployment.yaml", gates, "hotfix/emergency-fix")
        assert gate is None

    def test_second_gate_returned_when_first_skipped(self):
        """Second gate is returned when first is skipped."""
        gates = [
            RiskGate(
                name="infra-skip",
                patterns=["infra/*"],
                skip_if_branch=["hotfix/*"],
            ),
            RiskGate(
                name="infra-always",
                patterns=["infra/*"],
            ),
        ]
        gate = get_applicable_gate("infra/deployment.yaml", gates, "hotfix/fix")
        assert gate is not None
        assert gate.name == "infra-always"


# ---------------------------------------------------------------------------
# run_diff_review
# ---------------------------------------------------------------------------


class TestRunDiffReview:
    """Tests for run_diff_review function."""

    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_no_staged_files_returns_pass(self, mock_files, mock_diff):
        """Empty staged files returns a passing review."""
        mock_files.return_value = []
        mock_diff.return_value = ""
        config = PreCommitConfig()
        result = run_diff_review(config)
        assert result.passed is True
        assert "No staged" in result.message

    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_empty_diff_returns_pass(self, mock_files, mock_diff):
        """Empty diff returns a passing review."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "   "
        config = PreCommitConfig()
        result = run_diff_review(config)
        assert result.passed is True
        assert "No changes" in result.message

    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_pack_not_found_skips_gracefully(self, mock_files, mock_diff):
        """Missing pack skips review gracefully."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "diff --git a/src/main.py b/src/main.py\n+new line"
        config = PreCommitConfig(default_pack="nonexistent-pack")
        with patch("greybeard.packs.load_pack", side_effect=Exception("not found")):
            result = run_diff_review(config)
        assert result.passed is True
        assert "skipped" in result.message.lower()

    @patch("greybeard.analyzer.run_review")
    @patch("greybeard.packs.load_pack")
    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_successful_review_pass(self, mock_files, mock_diff, mock_load_pack, mock_run_review):
        """Successful review with no concerns returns pass."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "diff content"
        mock_load_pack.return_value = MagicMock()
        mock_run_review.return_value = "## Summary\n\nAll good, no issues."
        config = PreCommitConfig()
        result = run_diff_review(config)
        assert result.passed is True

    @patch("greybeard.analyzer.run_review")
    @patch("greybeard.packs.load_pack")
    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_review_with_concerns_fails(
        self, mock_files, mock_diff, mock_load_pack, mock_run_review
    ):
        """Review with critical concerns returns fail."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "diff content"
        mock_load_pack.return_value = MagicMock()
        mock_run_review.return_value = "[CRITICAL] This will break production"
        config = PreCommitConfig(fail_on_concerns="critical")
        result = run_diff_review(config)
        assert result.passed is False

    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_review_error_skips_gracefully(self, mock_files, mock_diff):
        """LLM error skips review gracefully without blocking commit."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "diff content"
        config = PreCommitConfig()
        with patch("greybeard.packs.load_pack", return_value=MagicMock()):
            with patch("greybeard.analyzer.run_review", side_effect=Exception("LLM error")):
                result = run_diff_review(config)
        assert result.passed is True
        assert "error" in result.message.lower()

    @patch("greybeard.analyzer.run_review")
    @patch("greybeard.packs.load_pack")
    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_verbose_mode(self, mock_files, mock_diff, mock_load_pack, mock_run_review):
        """Verbose mode triggers additional prints."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "diff content"
        mock_load_pack.return_value = MagicMock()
        mock_run_review.return_value = "All good"
        result = run_diff_review(PreCommitConfig(), verbose=True)
        assert result is not None

    @patch("greybeard.analyzer.run_review")
    @patch("greybeard.packs.load_pack")
    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_excluded_files_filtered_verbose(
        self, mock_files, mock_diff, mock_load_pack, mock_run_review
    ):
        """Excluded files are filtered from review (verbose mode shows count)."""
        mock_files.return_value = ["src/main.py", "poetry.lock"]
        mock_diff.return_value = "diff content"
        mock_load_pack.return_value = MagicMock()
        mock_run_review.return_value = "All good"
        config = PreCommitConfig(excluded_paths=["*.lock"], verbose=True)
        result = run_diff_review(config)
        assert result is not None

    @patch("greybeard.analyzer.run_review")
    @patch("greybeard.packs.load_pack")
    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_diff_truncation(self, mock_files, mock_diff, mock_load_pack, mock_run_review):
        """Large diffs are truncated to max_context_lines."""
        mock_files.return_value = ["src/main.py"]
        large_diff = "\n".join(f"line {i}" for i in range(1000))
        mock_diff.return_value = large_diff
        mock_load_pack.return_value = MagicMock()
        mock_run_review.return_value = "All good"
        config = PreCommitConfig(max_context_lines=10)
        result = run_diff_review(config, verbose=True)
        assert result is not None

    @patch("greybeard.analyzer.run_review")
    @patch("greybeard.packs.load_pack")
    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_long_review_truncated(self, mock_files, mock_diff, mock_load_pack, mock_run_review):
        """Review result longer than 200 chars is truncated in message."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "diff content"
        mock_load_pack.return_value = MagicMock()
        mock_run_review.return_value = "x" * 300
        result = run_diff_review(PreCommitConfig())
        assert result.message.endswith("...")

    @patch("greybeard.analyzer.run_review")
    @patch("greybeard.packs.load_pack")
    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_pack_override(self, mock_files, mock_diff, mock_load_pack, mock_run_review):
        """Pack argument overrides default pack."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "diff content"
        mock_load_pack.return_value = MagicMock()
        mock_run_review.return_value = "All good"
        run_diff_review(PreCommitConfig(default_pack="staff-core"), pack="on-call")
        mock_load_pack.assert_called_once_with("on-call")

    @patch("greybeard.packs.load_pack")
    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_verbose_pack_not_found(self, mock_files, mock_diff, mock_load_pack):
        """Verbose mode when pack is not found."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "diff content"
        mock_load_pack.side_effect = Exception("pack missing")
        config = PreCommitConfig(verbose=True)
        result = run_diff_review(config, verbose=True)
        assert result.passed is True

    @patch("greybeard.analyzer.run_review")
    @patch("greybeard.packs.load_pack")
    @patch("greybeard.precommit.get_staged_diff")
    @patch("greybeard.precommit.get_staged_files")
    def test_verbose_review_error(self, mock_files, mock_diff, mock_load_pack, mock_run_review):
        """Verbose mode on review error."""
        mock_files.return_value = ["src/main.py"]
        mock_diff.return_value = "diff content"
        mock_load_pack.return_value = MagicMock()
        mock_run_review.side_effect = Exception("LLM down")
        config = PreCommitConfig(verbose=True)
        result = run_diff_review(config, verbose=True)
        assert result.passed is True


# ---------------------------------------------------------------------------
# run_risk_check
# ---------------------------------------------------------------------------


class TestRunRiskCheck:
    """Tests for run_risk_check function."""

    @patch("greybeard.precommit.get_staged_files")
    def test_no_staged_files_returns_pass(self, mock_files):
        """No staged files returns passing risk check."""
        mock_files.return_value = []
        config = PreCommitConfig()
        result = run_risk_check(config)
        assert result.passed is True
        assert "No staged" in result.message

    @patch("greybeard.precommit.get_staged_files")
    def test_staged_single_empty_string(self, mock_files):
        """Single empty string in staged files returns passing check."""
        mock_files.return_value = [""]
        config = PreCommitConfig()
        result = run_risk_check(config)
        assert result.passed is True

    @patch("greybeard.precommit.get_current_branch")
    @patch("greybeard.precommit.get_staged_files")
    def test_no_matching_gates_returns_pass(self, mock_files, mock_branch):
        """Files with no matching gates all pass."""
        mock_files.return_value = ["src/main.py"]
        mock_branch.return_value = "main"
        config = PreCommitConfig(risk_gates=[RiskGate(name="infra", patterns=["infra/*"])])
        result = run_risk_check(config)
        assert result.passed is True
        assert result.message == "All gates passed"

    @patch("greybeard.precommit.get_current_branch")
    @patch("greybeard.precommit.get_staged_files")
    def test_file_matches_gate(self, mock_files, mock_branch):
        """File matching a gate is processed (placeholder always passes)."""
        mock_files.return_value = ["infra/deployment.yaml"]
        mock_branch.return_value = "main"
        config = PreCommitConfig(
            risk_gates=[RiskGate(name="infra", patterns=["infra/*"], fail_on_concerns="critical")]
        )
        result = run_risk_check(config)
        assert result.passed is True

    @patch("greybeard.precommit.get_current_branch")
    @patch("greybeard.precommit.get_staged_files")
    def test_excluded_file_skipped(self, mock_files, mock_branch):
        """Excluded files are skipped in risk check."""
        mock_files.return_value = ["infra/deployment.yaml", "poetry.lock"]
        mock_branch.return_value = "main"
        config = PreCommitConfig(
            risk_gates=[RiskGate(name="infra", patterns=["infra/*"])],
            excluded_paths=["poetry.lock"],
        )
        result = run_risk_check(config)
        assert result is not None

    @patch("greybeard.precommit.get_current_branch")
    @patch("greybeard.precommit.get_staged_files")
    def test_verbose_mode(self, mock_files, mock_branch):
        """Verbose mode prints gate match info."""
        mock_files.return_value = ["infra/main.tf"]
        mock_branch.return_value = "main"
        config = PreCommitConfig(risk_gates=[RiskGate(name="infra", patterns=["infra/*"])])
        result = run_risk_check(config, verbose=True)
        assert result is not None


# ---------------------------------------------------------------------------
# format_review_output edge cases
# ---------------------------------------------------------------------------


class TestFormatReviewOutputEdgeCases:
    """Tests for edge cases in format_review_output."""

    def test_more_than_five_concerns_shows_truncated(self):
        """More than 5 concerns are truncated with a count."""
        review = PreCommitReview(
            passed=False,
            message="Multiple concerns",
            concerns=[f"Concern {i}" for i in range(8)],
        )
        output = format_review_output(review)
        assert "... and 3 more" in output

    def test_failed_gates_shown_in_output(self):
        """Failed gates are shown in output."""
        review = PreCommitReview(
            passed=False,
            message="Gates failed",
            concerns=[],
            failed_gates=["infra-gate", "security-gate"],
        )
        output = format_review_output(review)
        assert "infra-gate" in output
        assert "security-gate" in output

    def test_verbose_with_metadata_shown(self):
        """Verbose mode with metadata shows debug info."""
        review = PreCommitReview(
            passed=True,
            message="OK",
            concerns=[],
            review_metadata={"pack": "staff-core", "mode": "review"},
        )
        output = format_review_output(review, verbose=True)
        assert "staff-core" in output
