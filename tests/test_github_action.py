"""Tests for GitHub Actions integration."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from greybeard.github_action import (
    DEFAULT_PACKS,
    DEFAULT_RISK_THRESHOLD,
    PACK_ICONS,
    RISK_PATTERNS,
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

# ---------------------------------------------------------------------------
# detect_blocking_issues
# ---------------------------------------------------------------------------


class TestDetectBlockingIssues:
    """Tests for detect_blocking_issues."""

    def test_high_threshold_matches_production_incident(self):
        result = detect_blocking_issues("This could cause a production incident", "high")
        assert result is True

    def test_high_threshold_no_match(self):
        result = detect_blocking_issues("Minor code style improvement", "high")
        assert result is False

    def test_none_threshold_never_blocks(self):
        result = detect_blocking_issues(
            "production incident data loss security vulnerability", "none"
        )
        assert result is False

    def test_low_threshold_matches_risk(self):
        result = detect_blocking_issues("Please consider this carefully", "low")
        assert result is True

    def test_medium_threshold_matches_scaling(self):
        result = detect_blocking_issues("This introduces a scaling limitation", "medium")
        assert result is True

    def test_unknown_threshold_defaults_to_high(self):
        result = detect_blocking_issues("production incident", "invalid-threshold")
        assert result is True

    def test_case_insensitive(self):
        result = detect_blocking_issues("PRODUCTION INCIDENT risk", "high")
        assert result is True

    def test_default_threshold_used(self):
        # Default risk threshold is 'high'
        result = detect_blocking_issues("production incident", DEFAULT_RISK_THRESHOLD)
        assert result is True


# ---------------------------------------------------------------------------
# get_risk_threshold
# ---------------------------------------------------------------------------


class TestGetRiskThreshold:
    """Tests for get_risk_threshold."""

    def test_returns_default_when_none(self):
        assert get_risk_threshold(None) == DEFAULT_RISK_THRESHOLD

    def test_returns_default_when_empty(self):
        assert get_risk_threshold("") == DEFAULT_RISK_THRESHOLD

    def test_valid_threshold_high(self):
        assert get_risk_threshold("high") == "high"

    def test_valid_threshold_low(self):
        assert get_risk_threshold("low") == "low"

    def test_valid_threshold_none_string(self):
        assert get_risk_threshold("none") == "none"

    def test_case_insensitive(self):
        assert get_risk_threshold("HIGH") == "high"
        assert get_risk_threshold("Low") == "low"

    def test_invalid_returns_default(self):
        assert get_risk_threshold("extreme") == DEFAULT_RISK_THRESHOLD


# ---------------------------------------------------------------------------
# format_pr_comment
# ---------------------------------------------------------------------------


class TestFormatPrComment:
    """Tests for format_pr_comment."""

    def test_basic_format(self):
        comment = format_pr_comment("Review content here", "staff-core", blocking=False)
        assert "Greybeard Review: staff-core" in comment
        assert "Review content here" in comment

    def test_blocking_adds_badge(self):
        comment = format_pr_comment("Danger!", "staff-core", blocking=True)
        assert "BLOCKING ISSUES DETECTED" in comment

    def test_non_blocking_no_badge(self):
        comment = format_pr_comment("All good", "staff-core", blocking=False)
        assert "BLOCKING" not in comment

    def test_pack_icon_known_pack(self):
        comment = format_pr_comment("Content", "staff-core", blocking=False)
        assert PACK_ICONS["staff-core"] in comment

    def test_pack_icon_unknown_pack(self):
        comment = format_pr_comment("Content", "my-custom-pack", blocking=False)
        assert "📋" in comment

    def test_content_truncated_when_too_long(self):
        long_content = "x" * 70000
        comment = format_pr_comment(long_content, "staff-core", blocking=False, max_length=60000)
        assert "_(review truncated)_" in comment

    def test_content_not_truncated_when_short(self):
        short_content = "Short review"
        comment = format_pr_comment(short_content, "staff-core", blocking=False)
        assert "_(review truncated)_" not in comment


# ---------------------------------------------------------------------------
# format_pr_comment_with_metadata
# ---------------------------------------------------------------------------


class TestFormatPrCommentWithMetadata:
    """Tests for format_pr_comment_with_metadata."""

    def test_includes_commit_sha(self):
        comment = format_pr_comment_with_metadata(
            "Content", "staff-core", blocking=False, commit_sha="abc123def456"
        )
        assert "abc123d" in comment

    def test_includes_base_branch(self):
        comment = format_pr_comment_with_metadata(
            "Content", "staff-core", blocking=False, base_branch="main"
        )
        assert "main" in comment

    def test_no_metadata_still_works(self):
        comment = format_pr_comment_with_metadata("Content", "staff-core", blocking=False)
        assert "Greybeard Review: staff-core" in comment
        assert "Greybeard" in comment

    def test_footer_contains_greybeard(self):
        comment = format_pr_comment_with_metadata("Content", "staff-core", blocking=False)
        assert "Review generated by Greybeard" in comment


# ---------------------------------------------------------------------------
# create_check_payload
# ---------------------------------------------------------------------------


class TestCreateCheckPayload:
    """Tests for create_check_payload."""

    def test_basic_payload(self):
        payload = create_check_payload(
            name="greybeard",
            status="completed",
            conclusion="success",
            title="All good",
            summary="No issues found",
        )
        assert payload["name"] == "greybeard"
        assert payload["status"] == "completed"
        assert payload["conclusion"] == "success"
        assert payload["output"]["title"] == "All good"
        assert payload["output"]["summary"] == "No issues found"

    def test_payload_with_text(self):
        payload = create_check_payload(
            name="greybeard",
            status="completed",
            conclusion="failure",
            title="Issues Found",
            summary="Blocking issues",
            text="See details below",
        )
        assert payload["output"]["text"] == "See details below"

    def test_payload_without_text(self):
        payload = create_check_payload(
            name="greybeard",
            status="completed",
            conclusion="success",
            title="OK",
            summary="OK",
        )
        assert "text" not in payload["output"]


# ---------------------------------------------------------------------------
# read_diff_file
# ---------------------------------------------------------------------------


class TestReadDiffFile:
    """Tests for read_diff_file."""

    def test_reads_file_content(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".diff", delete=False) as f:
            f.write("diff --git a/file.py b/file.py\n+new line")
            tmp_path = f.name
        try:
            content = read_diff_file(tmp_path)
            assert "diff --git" in content
            assert "+new line" in content
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# get_diff_size_info
# ---------------------------------------------------------------------------


class TestGetDiffSizeInfo:
    """Tests for get_diff_size_info."""

    def test_small_diff(self):
        diff = "line1\nline2\nline3"
        info = get_diff_size_info(diff)
        assert info.size_category == "Small"
        assert info.line_count == 3

    def test_medium_diff(self):
        diff = "\n".join(f"line {i}" for i in range(150))
        info = get_diff_size_info(diff)
        assert info.size_category == "Medium"

    def test_large_diff(self):
        diff = "\n".join(f"line {i}" for i in range(600))
        info = get_diff_size_info(diff)
        assert info.size_category == "Large"

    def test_very_large_diff(self):
        diff = "\n".join(f"line {i}" for i in range(2100))
        info = get_diff_size_info(diff)
        assert info.size_category == "Very Large"

    def test_char_count(self):
        diff = "hello"
        info = get_diff_size_info(diff)
        assert info.char_count == 5


# ---------------------------------------------------------------------------
# has_binary_files
# ---------------------------------------------------------------------------


class TestHasBinaryFiles:
    """Tests for has_binary_files."""

    def test_detects_binary_files(self):
        diff = "Binary files a/image.png and b/image.png differ"
        assert has_binary_files(diff) is True

    def test_no_binary_files(self):
        diff = "diff --git a/file.py b/file.py\n+new line"
        assert has_binary_files(diff) is False


# ---------------------------------------------------------------------------
# parse_pack_list / get_packs_to_review
# ---------------------------------------------------------------------------


class TestPackParsing:
    """Tests for parse_pack_list and get_packs_to_review."""

    def test_parse_pack_list_single(self):
        packs = parse_pack_list("staff-core")
        assert packs == ["staff-core"]

    def test_parse_pack_list_multiple(self):
        packs = parse_pack_list("staff-core, on-call, security")
        assert packs == ["staff-core", "on-call", "security"]

    def test_parse_pack_list_none_returns_defaults(self):
        packs = parse_pack_list(None)
        assert packs == DEFAULT_PACKS

    def test_parse_pack_list_empty_returns_defaults(self):
        packs = parse_pack_list("")
        assert packs == DEFAULT_PACKS

    def test_get_packs_to_review_with_str(self):
        packs = get_packs_to_review("staff-core")
        assert packs == ["staff-core"]

    def test_get_packs_to_review_none_returns_defaults(self):
        packs = get_packs_to_review(None)
        assert packs == DEFAULT_PACKS


# ---------------------------------------------------------------------------
# validate_pack_names
# ---------------------------------------------------------------------------


class TestValidatePackNames:
    """Tests for validate_pack_names."""

    @patch("greybeard.github_action.load_pack")
    def test_valid_packs(self, mock_load_pack):
        mock_load_pack.return_value = MagicMock()
        assert validate_pack_names(["staff-core", "on-call"]) is True

    @patch("greybeard.github_action.load_pack")
    def test_invalid_pack_returns_false(self, mock_load_pack):
        mock_load_pack.side_effect = FileNotFoundError("Pack not found")
        assert validate_pack_names(["nonexistent-pack"]) is False

    @patch("greybeard.github_action.load_pack")
    def test_invalid_pack_value_error_returns_false(self, mock_load_pack):
        mock_load_pack.side_effect = ValueError("Invalid pack")
        assert validate_pack_names(["bad-pack"]) is False


# ---------------------------------------------------------------------------
# should_block_pr / generate_blocking_summary
# ---------------------------------------------------------------------------


class TestBlockingLogic:
    """Tests for should_block_pr and generate_blocking_summary."""

    def test_should_block_pr_when_issues(self):
        assert should_block_pr("This will cause a production incident", "high") is True

    def test_should_not_block_pr_when_no_issues(self):
        assert should_block_pr("Minor style change", "high") is False

    def test_generate_blocking_summary(self):
        issues = ["Issue A", "Issue B", ""]
        result = generate_blocking_summary(issues)
        assert "- Issue A" in result
        assert "- Issue B" in result
        assert len(result) == 2  # Empty string filtered

    def test_generate_blocking_summary_empty(self):
        result = generate_blocking_summary([])
        assert result == []


# ---------------------------------------------------------------------------
# get_github_env / get_greybeard_config_from_env
# ---------------------------------------------------------------------------


class TestEnvironmentHelpers:
    """Tests for environment variable helpers."""

    def test_get_github_env_defaults(self):
        with patch.dict(os.environ, {}, clear=False):
            env = get_github_env()
        assert "sha" in env
        assert "ref" in env
        assert "base_ref" in env

    def test_get_github_env_with_values(self):
        with patch.dict(
            os.environ,
            {
                "GITHUB_SHA": "abc123",
                "GITHUB_REF": "refs/heads/main",
                "GITHUB_BASE_REF": "main",
                "GITHUB_REPOSITORY": "owner/repo",
                "GITHUB_EVENT_NAME": "pull_request",
            },
        ):
            env = get_github_env()
        assert env["sha"] == "abc123"
        assert env["repo"] == "owner/repo"
        assert env["event_name"] == "pull_request"

    def test_get_greybeard_config_from_env_defaults(self):
        config = get_greybeard_config_from_env()
        assert "llm_backend" in config
        assert "llm_model" in config
        assert "risk_threshold" in config

    def test_get_greybeard_config_from_env_custom(self):
        with patch.dict(
            os.environ,
            {
                "GREYBEARD_LLM_BACKEND": "anthropic",
                "GREYBEARD_LLM_MODEL": "claude-3-5-sonnet-20241022",
                "GREYBEARD_RISK_THRESHOLD": "low",
            },
        ):
            config = get_greybeard_config_from_env()
        assert config["llm_backend"] == "anthropic"
        assert config["llm_model"] == "claude-3-5-sonnet-20241022"
        assert config["risk_threshold"] == "low"


# ---------------------------------------------------------------------------
# validate_github_env
# ---------------------------------------------------------------------------


class TestValidateGithubEnv:
    """Tests for validate_github_env."""

    def test_raises_when_missing_vars(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required GitHub env vars"):
                validate_github_env()

    def test_returns_true_when_vars_present(self):
        with patch.dict(
            os.environ,
            {
                "GITHUB_SHA": "abc123",
                "GITHUB_REPOSITORY": "owner/repo",
            },
        ):
            result = validate_github_env()
        assert result is True


# ---------------------------------------------------------------------------
# validate_llm_credentials
# ---------------------------------------------------------------------------


class TestValidateLlmCredentials:
    """Tests for validate_llm_credentials."""

    def test_ollama_always_valid(self):
        assert validate_llm_credentials("ollama") is True

    def test_lmstudio_always_valid(self):
        assert validate_llm_credentials("lmstudio") is True

    def test_openai_with_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            assert validate_llm_credentials("openai") is True

    def test_openai_without_key(self):
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            assert validate_llm_credentials("openai") is False

    def test_anthropic_with_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            assert validate_llm_credentials("anthropic") is True


# ---------------------------------------------------------------------------
# find_existing_comment / should_update_comment
# ---------------------------------------------------------------------------


class TestCommentHelpers:
    """Tests for comment helper functions."""

    def test_find_existing_comment_found(self):
        comments = [
            {"id": 1, "body": "Some other comment"},
            {"id": 2, "body": "## 🧙 Greybeard Review: staff-core\n\nContent"},
        ]
        result = find_existing_comment(comments, "staff-core")
        assert result is not None
        assert result["id"] == 2

    def test_find_existing_comment_not_found(self):
        comments = [
            {"id": 1, "body": "Some other comment"},
        ]
        result = find_existing_comment(comments, "staff-core")
        assert result is None

    def test_find_existing_comment_empty_list(self):
        result = find_existing_comment([], "staff-core")
        assert result is None

    def test_should_update_comment_when_exists(self):
        existing = {"id": 1, "body": "old content"}
        assert should_update_comment(existing) is True

    def test_should_not_update_when_none(self):
        assert should_update_comment(None) is False


# ---------------------------------------------------------------------------
# ReviewResult dataclass
# ---------------------------------------------------------------------------


class TestReviewResult:
    """Tests for ReviewResult dataclass."""

    def test_basic_review_result(self):
        result = ReviewResult(
            pack="staff-core",
            review_content="All good",
            blocking=False,
        )
        assert result.pack == "staff-core"
        assert result.blocking is False
        assert result.error is None

    def test_review_result_with_error(self):
        result = ReviewResult(
            pack="staff-core",
            review_content="Error",
            blocking=False,
            error="LLM unavailable",
        )
        assert result.error == "LLM unavailable"


# ---------------------------------------------------------------------------
# run_github_action / run_github_action_safe
# ---------------------------------------------------------------------------


class TestRunGitHubAction:
    """Tests for run_github_action and run_github_action_safe."""

    @patch("greybeard.github_action.run_review")
    @patch("greybeard.github_action.load_pack")
    def test_run_github_action_success(self, mock_load_pack, mock_run_review, tmp_path):
        from greybeard.models import ContentPack

        diff_file = tmp_path / "test.diff"
        diff_file.write_text("diff --git a/file.py b/file.py\n+new line")

        mock_load_pack.return_value = ContentPack(
            name="staff-core", perspective="test", tone="constructive"
        )
        mock_run_review.return_value = "## Summary\n\nAll good, no blocking issues."

        result = run_github_action(str(diff_file), "staff-core", "high")
        assert result.pack == "staff-core"
        assert isinstance(result.blocking, bool)

    @patch("greybeard.github_action.run_review")
    @patch("greybeard.github_action.load_pack")
    def test_run_github_action_blocking(self, mock_load_pack, mock_run_review, tmp_path):
        from greybeard.models import ContentPack

        diff_file = tmp_path / "test.diff"
        diff_file.write_text("diff --git a/file.py b/file.py\n+new line")

        mock_load_pack.return_value = ContentPack(
            name="staff-core", perspective="test", tone="constructive"
        )
        mock_run_review.return_value = "This will cause a production incident"

        result = run_github_action(str(diff_file), "staff-core", "high")
        assert result.blocking is True

    def test_run_github_action_safe_with_error(self, tmp_path):
        # Non-existent file - should return error result, not raise
        result = run_github_action_safe("/nonexistent/path.diff", "staff-core")
        assert result.pack == "staff-core"
        assert result.error is not None
        assert result.blocking is False

    @patch("greybeard.github_action.run_review")
    @patch("greybeard.github_action.load_pack")
    def test_process_multiple_packs(self, mock_load_pack, mock_run_review, tmp_path):
        diff_file = tmp_path / "test.diff"
        diff_file.write_text("diff")

        mock_load_pack.return_value = MagicMock()
        mock_run_review.return_value = "All clear"

        results = process_multiple_packs(str(diff_file), packs=["staff-core", "on-call"])
        assert len(results) == 2
        assert results[0].pack == "staff-core"
        assert results[1].pack == "on-call"

    @patch("greybeard.github_action.run_review")
    @patch("greybeard.github_action.load_pack")
    def test_process_multiple_packs_defaults(self, mock_load_pack, mock_run_review, tmp_path):
        diff_file = tmp_path / "test.diff"
        diff_file.write_text("diff")

        mock_load_pack.return_value = MagicMock()
        mock_run_review.return_value = "All clear"

        results = process_multiple_packs(str(diff_file))
        assert len(results) == len(DEFAULT_PACKS)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Tests for module constants."""

    def test_default_packs_is_list(self):
        assert isinstance(DEFAULT_PACKS, list)
        assert len(DEFAULT_PACKS) > 0

    def test_risk_patterns_has_expected_levels(self):
        assert "high" in RISK_PATTERNS
        assert "medium" in RISK_PATTERNS
        assert "low" in RISK_PATTERNS
        assert "none" in RISK_PATTERNS

    def test_pack_icons_dict(self):
        assert "staff-core" in PACK_ICONS
