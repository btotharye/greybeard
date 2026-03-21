"""Comprehensive tests for GitHub Actions integration."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from greybeard.github_action import (
    DEFAULT_PACKS,
    DEFAULT_RISK_THRESHOLD,
    PACK_ICONS,
    RISK_PATTERNS,
    DiffSizeInfo,
    ReviewResult,
    create_check_payload,
    detect_blocking_issues,
    find_existing_comment,
    format_pr_comment,
    format_pr_comment_with_metadata,
    generate_blocking_summary,
    get_diff_size_info,
    get_github_env,
    get_greybeard_config_from_env,
    get_packs_to_review,
    get_risk_threshold,
    has_binary_files,
    parse_pack_list,
    process_multiple_packs,
    read_diff_file,
    run_github_action,
    run_github_action_safe,
    should_block_pr,
    should_update_comment,
    validate_github_env,
    validate_llm_credentials,
    validate_pack_names,
)


class TestRiskDetection:
    """Test risk detection and blocking logic."""

    def test_detect_blocking_issues_high_threshold_critical(self):
        """Test high threshold detects critical issues."""
        content = "production incident detected"
        assert detect_blocking_issues(content, "high") is True

    def test_detect_blocking_issues_high_threshold_no_match(self):
        """Test high threshold doesn't match low severity."""
        content = "minor code style issue"
        assert detect_blocking_issues(content, "high") is False

    def test_detect_blocking_issues_medium_threshold(self):
        """Test medium threshold detects medium and above."""
        assert detect_blocking_issues("scaling limitation found", "medium") is True
        assert detect_blocking_issues("concern noted", "medium") is False

    def test_detect_blocking_issues_low_threshold(self):
        """Test low threshold detects anything with 'risk'."""
        assert detect_blocking_issues("careful implementation required", "low") is True
        assert detect_blocking_issues("no issues", "low") is False

    def test_detect_blocking_issues_none_threshold(self):
        """Test 'none' threshold never blocks."""
        assert detect_blocking_issues("critical error!", "none") is False
        assert detect_blocking_issues("production incident", "none") is False

    def test_detect_blocking_issues_case_insensitive(self):
        """Test detection is case-insensitive."""
        assert detect_blocking_issues("PRODUCTION INCIDENT", "high") is True
        assert detect_blocking_issues("Production Incident", "high") is True

    def test_get_risk_threshold_valid(self):
        """Test getting valid risk threshold."""
        assert get_risk_threshold("high") == "high"
        assert get_risk_threshold("medium") == "medium"
        assert get_risk_threshold("low") == "low"
        assert get_risk_threshold("none") == "none"

    def test_get_risk_threshold_invalid_defaults(self):
        """Test invalid threshold defaults to high."""
        assert get_risk_threshold("invalid") == DEFAULT_RISK_THRESHOLD
        assert get_risk_threshold("") == DEFAULT_RISK_THRESHOLD
        assert get_risk_threshold(None) == DEFAULT_RISK_THRESHOLD

    def test_get_risk_threshold_case_insensitive(self):
        """Test threshold is case-insensitive."""
        assert get_risk_threshold("HIGH") == "high"
        assert get_risk_threshold("Medium") == "medium"

    def test_should_block_pr(self):
        """Test PR blocking logic."""
        assert should_block_pr("data loss possible", "high") is True
        assert should_block_pr("minor issue", "high") is False


class TestPRCommentFormatting:
    """Test PR comment formatting."""

    def test_format_pr_comment_basic(self):
        """Test basic PR comment formatting."""
        content = "Review found issues"
        comment = format_pr_comment(content, "staff-core", False)

        assert "## 🧙 Greybeard Review: staff-core" in comment
        assert "Review found issues" in comment
        assert "BLOCKING" not in comment

    def test_format_pr_comment_with_blocking(self):
        """Test formatting with blocking badge."""
        content = "Critical issues"
        comment = format_pr_comment(content, "staff-core", True)

        assert "⚠️ **BLOCKING ISSUES DETECTED**" in comment
        assert "Critical issues" in comment

    def test_format_pr_comment_icon_selection(self):
        """Test icon selection for different packs."""
        content = "test"

        comment1 = format_pr_comment(content, "staff-core", False)
        assert "🧙" in comment1

        comment2 = format_pr_comment(content, "on-call", False)
        assert "📟" in comment2

        comment3 = format_pr_comment(content, "security", False)
        assert "🔒" in comment3

        comment4 = format_pr_comment(content, "unknown", False)
        assert "📋" in comment4

    def test_format_pr_comment_truncation(self):
        """Test content truncation."""
        long_content = "x" * 70000
        comment = format_pr_comment(long_content, "staff-core", False)

        assert len(comment) < len(long_content)
        assert "... _(review truncated)_" in comment

    def test_format_pr_comment_no_truncation(self):
        """Test no truncation for short content."""
        content = "Short review"
        comment = format_pr_comment(content, "staff-core", False)

        assert content in comment
        assert "truncated" not in comment

    def test_format_pr_comment_with_metadata(self):
        """Test formatting with metadata."""
        content = "Review content"
        comment = format_pr_comment_with_metadata(
            content, "staff-core", False, "abc1234", "main"
        )

        assert "Review content" in comment
        assert "[abc1234]" in comment
        assert "→ main" in comment
        assert "Review generated by" in comment

    def test_format_pr_comment_with_metadata_partial(self):
        """Test metadata with only commit SHA."""
        content = "Review"
        comment = format_pr_comment_with_metadata(
            content, "staff-core", False, commit_sha="abc1234"
        )

        assert "[abc1234]" in comment
        assert "→" not in comment

    def test_format_pr_comment_with_metadata_blocking(self):
        """Test blocking metadata formatting."""
        content = "Critical"
        comment = format_pr_comment_with_metadata(
            content, "staff-core", True, "abc1234", "main"
        )

        assert "BLOCKING" in comment
        assert "[abc1234]" in comment


class TestCheckPayload:
    """Test GitHub Check creation."""

    def test_create_check_payload_minimal(self):
        """Test creating minimal check payload."""
        payload = create_check_payload(
            name="test-check",
            status="completed",
            conclusion="success",
            title="Test Title",
            summary="Test Summary",
        )

        assert payload["name"] == "test-check"
        assert payload["status"] == "completed"
        assert payload["conclusion"] == "success"
        assert payload["output"]["title"] == "Test Title"
        assert payload["output"]["summary"] == "Test Summary"
        assert "text" not in payload["output"]

    def test_create_check_payload_with_text(self):
        """Test creating check payload with text."""
        payload = create_check_payload(
            name="review-check",
            status="completed",
            conclusion="failure",
            title="Review Failed",
            summary="Issues found",
            text="Detailed text here",
        )

        assert payload["output"]["text"] == "Detailed text here"

    def test_create_check_payload_in_progress(self):
        """Test check payload for in-progress status."""
        payload = create_check_payload(
            name="test",
            status="in_progress",
            conclusion="neutral",
            title="Running",
            summary="Processing",
        )

        assert payload["status"] == "in_progress"
        assert payload["conclusion"] == "neutral"


class TestDiffHandling:
    """Test diff file handling and analysis."""

    def test_read_diff_file(self):
        """Test reading diff file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".diff", delete=False) as f:
            f.write("diff --git a/file.py b/file.py\n+new content")
            f.flush()

            diff = read_diff_file(f.name)
            assert "diff --git" in diff
            assert "+new content" in diff

            Path(f.name).unlink()

    def test_get_diff_size_info_small(self):
        """Test diff size categorization - small."""
        diff = "line\n" * 50
        info = get_diff_size_info(diff)

        assert info.size_category == "Small"
        assert info.line_count == 50
        assert info.char_count == len(diff)

    def test_get_diff_size_info_medium(self):
        """Test diff size categorization - medium."""
        diff = "line\n" * 300
        info = get_diff_size_info(diff)

        assert info.size_category == "Medium"
        assert info.line_count == 300

    def test_get_diff_size_info_large(self):
        """Test diff size categorization - large."""
        diff = "line\n" * 1000
        info = get_diff_size_info(diff)

        assert info.size_category == "Large"

    def test_get_diff_size_info_very_large(self):
        """Test diff size categorization - very large."""
        diff = "line\n" * 2500
        info = get_diff_size_info(diff)

        assert info.size_category == "Very Large"

    def test_has_binary_files_true(self):
        """Test detection of binary files."""
        diff = "Binary files a/image.png and b/image.png differ"
        assert has_binary_files(diff) is True

    def test_has_binary_files_false(self):
        """Test no binary files."""
        diff = "diff --git a/file.py\n+content"
        assert has_binary_files(diff) is False


class TestPackHandling:
    """Test pack list parsing and validation."""

    def test_parse_pack_list_none(self):
        """Test parsing None returns defaults."""
        packs = parse_pack_list(None)
        assert packs == DEFAULT_PACKS

    def test_parse_pack_list_single(self):
        """Test parsing single pack."""
        packs = parse_pack_list("staff-core")
        assert packs == ["staff-core"]

    def test_parse_pack_list_multiple(self):
        """Test parsing multiple packs."""
        packs = parse_pack_list("staff-core, on-call, security")
        assert packs == ["staff-core", "on-call", "security"]

    def test_parse_pack_list_with_whitespace(self):
        """Test parsing with extra whitespace."""
        packs = parse_pack_list("  staff-core  ,  on-call  ")
        assert packs == ["staff-core", "on-call"]

    def test_parse_pack_list_empty_string(self):
        """Test parsing empty string defaults."""
        packs = parse_pack_list("")
        assert packs == DEFAULT_PACKS

    def test_get_packs_to_review_default(self):
        """Test getting default packs."""
        packs = get_packs_to_review(None)
        assert packs == DEFAULT_PACKS

    def test_get_packs_to_review_custom(self):
        """Test getting custom packs."""
        packs = get_packs_to_review("staff-core,security")
        assert packs == ["staff-core", "security"]

    @patch("greybeard.github_action.load_pack")
    def test_validate_pack_names_success(self, mock_load):
        """Test validating existing packs."""
        mock_load.return_value = MagicMock()
        assert validate_pack_names(["staff-core", "security"]) is True
        assert mock_load.call_count == 2

    @patch("greybeard.github_action.load_pack")
    def test_validate_pack_names_failure(self, mock_load):
        """Test validating non-existent packs."""
        mock_load.side_effect = FileNotFoundError("Pack not found")
        assert validate_pack_names(["invalid-pack"]) is False


class TestEnvironmentVariables:
    """Test GitHub environment variable handling."""

    @patch.dict("os.environ", {
        "GITHUB_SHA": "abc123",
        "GITHUB_REF": "refs/pull/42/merge",
        "GITHUB_BASE_REF": "develop",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_EVENT_NAME": "pull_request",
    })
    def test_get_github_env_all_set(self):
        """Test getting all GitHub env variables."""
        env = get_github_env()

        assert env["sha"] == "abc123"
        assert env["ref"] == "refs/pull/42/merge"
        assert env["base_ref"] == "develop"
        assert env["repo"] == "owner/repo"
        assert env["event_name"] == "pull_request"

    @patch.dict("os.environ", {}, clear=True)
    def test_get_github_env_defaults(self):
        """Test GitHub env defaults to unknown."""
        env = get_github_env()

        assert env["sha"] == "unknown"
        assert env["repo"] == "unknown"
        assert env["base_ref"] == "main"

    @patch.dict("os.environ", {"GITHUB_SHA": "abc", "GITHUB_REPOSITORY": "owner/repo"})
    def test_validate_github_env_success(self):
        """Test validating required GitHub env."""
        assert validate_github_env() is True

    @patch.dict("os.environ", {}, clear=True)
    def test_validate_github_env_failure(self):
        """Test missing required GitHub env."""
        with pytest.raises(ValueError, match="Missing required GitHub env vars"):
            validate_github_env()

    @patch.dict("os.environ", {"GREYBEARD_LLM_BACKEND": "openai", "GREYBEARD_LLM_MODEL": "gpt-4"})
    def test_get_greybeard_config_from_env(self):
        """Test getting Greybeard config from env."""
        config = get_greybeard_config_from_env()

        assert config["llm_backend"] == "openai"
        assert config["llm_model"] == "gpt-4"
        assert config["risk_threshold"] == DEFAULT_RISK_THRESHOLD

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    def test_validate_llm_credentials_openai_success(self):
        """Test OpenAI credentials validation - success."""
        assert validate_llm_credentials("openai") is True

    @patch.dict("os.environ", {}, clear=True)
    def test_validate_llm_credentials_openai_failure(self):
        """Test OpenAI credentials validation - failure."""
        assert validate_llm_credentials("openai") is False

    def test_validate_llm_credentials_ollama(self):
        """Test Ollama doesn't require credentials."""
        assert validate_llm_credentials("ollama") is True

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"})
    def test_validate_llm_credentials_anthropic(self):
        """Test Anthropic credentials validation."""
        assert validate_llm_credentials("anthropic") is True


class TestCommentManagement:
    """Test finding and updating existing comments."""

    def test_find_existing_comment_found(self):
        """Test finding existing comment."""
        comments = [
            {"body": "Some other comment"},
            {"body": "## Greybeard Review: staff-core\nReview content"},
            {"body": "Another comment"},
        ]

        found = find_existing_comment(comments, "staff-core")
        assert found is not None
        assert "Greybeard Review: staff-core" in found["body"]

    def test_find_existing_comment_not_found(self):
        """Test comment not found."""
        comments = [{"body": "Regular comment"}]
        found = find_existing_comment(comments, "staff-core")
        assert found is None

    def test_find_existing_comment_empty_list(self):
        """Test empty comment list."""
        found = find_existing_comment([], "staff-core")
        assert found is None

    def test_should_update_comment_true(self):
        """Test should update when comment exists."""
        comment = {"body": "existing"}
        assert should_update_comment(comment) is True

    def test_should_update_comment_false(self):
        """Test should create new when no comment."""
        assert should_update_comment(None) is False


class TestReviewResult:
    """Test ReviewResult dataclass."""

    def test_review_result_success(self):
        """Test successful review result."""
        result = ReviewResult(
            pack="staff-core",
            review_content="All good",
            blocking=False,
        )

        assert result.pack == "staff-core"
        assert result.review_content == "All good"
        assert result.blocking is False
        assert result.error is None

    def test_review_result_with_error(self):
        """Test review result with error."""
        result = ReviewResult(
            pack="staff-core",
            review_content="",
            blocking=False,
            error="API timeout",
        )

        assert result.error == "API timeout"


class TestReviewExecution:
    """Test review execution functions."""

    @patch("greybeard.github_action.run_review")
    @patch("greybeard.github_action.load_pack")
    @patch("greybeard.github_action.read_diff_file")
    @patch("greybeard.github_action.GreybeardConfig.load")
    def test_run_github_action_success(
        self, mock_config, mock_read, mock_load_pack, mock_review
    ):
        """Test successful review execution."""
        mock_config.return_value = MagicMock()
        mock_read.return_value = "diff content"
        mock_load_pack.return_value = {"name": "staff-core"}
        mock_review.return_value = "Review findings"

        result = run_github_action("diff.patch", "staff-core")

        assert result.pack == "staff-core"
        assert result.review_content == "Review findings"
        assert result.error is None

    @patch("greybeard.github_action.run_review")
    @patch("greybeard.github_action.load_pack")
    @patch("greybeard.github_action.read_diff_file")
    def test_run_github_action_safe_handles_error(
        self, mock_read, mock_load_pack, mock_review
    ):
        """Test safe review handles errors gracefully."""
        mock_read.side_effect = Exception("File not found")

        result = run_github_action_safe("nonexistent.patch", "staff-core")

        assert result.pack == "staff-core"
        assert result.blocking is False
        assert result.error is not None
        assert "Error during review" in result.review_content

    @patch("greybeard.github_action.run_github_action_safe")
    def test_process_multiple_packs(self, mock_run):
        """Test processing multiple packs."""
        mock_run.side_effect = [
            ReviewResult("staff-core", "review 1", False),
            ReviewResult("security", "review 2", False),
        ]

        results = process_multiple_packs("diff.patch", ["staff-core", "security"])

        assert len(results) == 2
        assert results[0].pack == "staff-core"
        assert results[1].pack == "security"

    @patch("greybeard.github_action.run_github_action_safe")
    def test_process_multiple_packs_default(self, mock_run):
        """Test processing uses default packs."""
        mock_run.return_value = ReviewResult("staff-core", "review", False)

        results = process_multiple_packs("diff.patch")

        assert len(results) == len(DEFAULT_PACKS)


class TestBlockingSummary:
    """Test blocking issue summary generation."""

    def test_generate_blocking_summary_single(self):
        """Test generating summary with single issue."""
        summary = generate_blocking_summary(["Data loss risk"])
        assert summary == ["- Data loss risk"]

    def test_generate_blocking_summary_multiple(self):
        """Test generating summary with multiple issues."""
        issues = ["Issue 1", "Issue 2", "Issue 3"]
        summary = generate_blocking_summary(issues)
        assert len(summary) == 3
        assert all("- " in s for s in summary)

    def test_generate_blocking_summary_with_empty_strings(self):
        """Test summary filters empty strings."""
        issues = ["Issue 1", "", "Issue 2"]
        summary = generate_blocking_summary(issues)
        assert len(summary) == 2
        assert "- " in summary[0]


class TestDiffSizeInfo:
    """Test DiffSizeInfo dataclass."""

    def test_diff_size_info_creation(self):
        """Test creating DiffSizeInfo."""
        info = DiffSizeInfo(
            line_count=100,
            char_count=1000,
            size_category="Small",
        )

        assert info.line_count == 100
        assert info.char_count == 1000
        assert info.size_category == "Small"


class TestConstants:
    """Test module constants."""

    def test_risk_patterns_defined(self):
        """Test RISK_PATTERNS contains expected levels."""
        assert "high" in RISK_PATTERNS
        assert "medium" in RISK_PATTERNS
        assert "low" in RISK_PATTERNS
        assert "none" in RISK_PATTERNS

    def test_pack_icons_defined(self):
        """Test PACK_ICONS for known packs."""
        assert PACK_ICONS["staff-core"] == "🧙"
        assert PACK_ICONS["on-call"] == "📟"
        assert PACK_ICONS["security"] == "🔒"

    def test_defaults_defined(self):
        """Test default constants are set."""
        assert DEFAULT_PACKS == ["staff-core", "on-call", "security"]
        assert DEFAULT_RISK_THRESHOLD == "high"
