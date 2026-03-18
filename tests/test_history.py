"""Tests for greybeard decision history and trend analysis."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from staff_review.cli import cli
from staff_review.history import (
    PATTERN_THRESHOLD,
    _clean_phrase,
    _extract_key_questions,
    _extract_key_risks,
    analyze_trends,
    load_history,
    save_decision,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_history(tmp_path, monkeypatch):
    """Redirect HISTORY_FILE and HISTORY_DIR to a temporary directory."""
    history_dir = tmp_path / ".greybeard"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_file = history_dir / "history.jsonl"
    monkeypatch.setattr("staff_review.history.HISTORY_DIR", history_dir)
    monkeypatch.setattr("staff_review.history.HISTORY_FILE", history_file)
    # Also patch the cli module's imports (they imported directly)
    monkeypatch.setattr("staff_review.cli.HISTORY_FILE", history_file)
    return history_file


def _make_entry(
    decision_name: str = "test-decision",
    pack: str = "staff-core",
    mode: str = "review",
    days_ago: int = 0,
    key_risks: list[str] | None = None,
    key_questions: list[str] | None = None,
) -> dict:
    """Build a synthetic history entry."""
    ts = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return {
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decision_name": decision_name,
        "pack": pack,
        "mode": mode,
        "summary": "A sample review summary.",
        "key_risks": key_risks or ["knowledge concentration", "missing tests"],
        "key_questions": key_questions or ["Have you considered rollback?"],
    }


# ── Unit: extraction helpers ──────────────────────────────────────────────────


class TestExtractKeyRisks:
    REVIEW_WITH_RISKS = """
## Risks

- Knowledge concentration in a single team member
- No rollback plan exists for this migration
- Missing test coverage on the auth layer

## Questions

- Have you thought about failure modes?
"""

    REVIEW_BULLETED_NO_HEADING = """
Some intro text.

- This carries a risk of data loss if the migration fails mid-way.
- The service has no monitoring in place.
"""

    def test_extracts_risks_from_risk_section(self):
        risks = _extract_key_risks(self.REVIEW_WITH_RISKS)
        assert any("knowledge" in r for r in risks)
        assert any("rollback" in r for r in risks)

    def test_extracts_risks_without_heading(self):
        risks = _extract_key_risks(self.REVIEW_BULLETED_NO_HEADING)
        assert any("data loss" in r or "risk" in r for r in risks)

    def test_returns_at_most_10(self):
        many_risks = "\n".join(f"- risk item number {i} with some signal word" for i in range(20))
        risks = _extract_key_risks(many_risks)
        assert len(risks) <= 10

    def test_empty_text(self):
        assert _extract_key_risks("") == []

    def test_no_duplicates(self):
        text = "## Risks\n- knowledge concentration\n- knowledge concentration\n"
        risks = _extract_key_risks(text)
        assert risks.count("knowledge concentration") <= 1


class TestExtractKeyQuestions:
    def test_extracts_questions(self):
        text = "Some preamble.\n- Have you considered rollback?\n- What happens if this fails?\n"
        questions = _extract_key_questions(text)
        assert len(questions) == 2
        assert any("rollback" in q for q in questions)

    def test_returns_at_most_8(self):
        text = "\n".join(f"- Question number {i}?" for i in range(15))
        questions = _extract_key_questions(text)
        assert len(questions) <= 8

    def test_ignores_short_questions(self):
        questions = _extract_key_questions("- OK?\n- Have you thought about failure modes?\n")
        assert all(len(q) > 5 for q in questions)

    def test_empty_text(self):
        assert _extract_key_questions("") == []


class TestCleanPhrase:
    def test_strips_markdown(self):
        assert "**" not in _clean_phrase("**bold risk** here")

    def test_strips_links(self):
        result = _clean_phrase("[click here](https://example.com) is a risk")
        assert "https" not in result
        assert "click here" in result

    def test_truncates_long_phrases(self):
        long_text = "a" * 200
        assert len(_clean_phrase(long_text)) <= 120

    def test_first_sentence_only(self):
        result = _clean_phrase("first risk. second risk. third.")
        assert "second" not in result


# ── Unit: save_decision ───────────────────────────────────────────────────────


class TestSaveDecision:
    REVIEW_TEXT = """
## Risks

- Knowledge concentration risk in payment team
- No rollback strategy documented

## Conclusion

This looks fragile.
"""

    def test_creates_history_file(self, tmp_history):
        save_decision("test-dec", self.REVIEW_TEXT, "staff-core", "review")
        assert tmp_history.exists()

    def test_appends_valid_json(self, tmp_history):
        save_decision("dec-1", self.REVIEW_TEXT, "staff-core", "review")
        save_decision("dec-2", self.REVIEW_TEXT, "oncall-future-you", "mentor")
        lines = tmp_history.read_text().strip().splitlines()
        assert len(lines) == 2
        for line in lines:
            entry = json.loads(line)
            assert "timestamp" in entry
            assert "decision_name" in entry
            assert "pack" in entry
            assert "mode" in entry
            assert "summary" in entry
            assert isinstance(entry["key_risks"], list)
            assert isinstance(entry["key_questions"], list)

    def test_stores_correct_fields(self, tmp_history):
        save_decision("my-decision", self.REVIEW_TEXT, "staff-core", "review")
        entry = json.loads(tmp_history.read_text().strip())
        assert entry["decision_name"] == "my-decision"
        assert entry["pack"] == "staff-core"
        assert entry["mode"] == "review"
        assert len(entry["summary"]) <= 500

    def test_summary_truncated_to_500(self, tmp_history):
        long_review = "x" * 2000
        save_decision("dec", long_review, "pack", "review")
        entry = json.loads(tmp_history.read_text().strip())
        assert len(entry["summary"]) <= 500

    def test_returns_history_file_path(self, tmp_history):
        result = save_decision("dec", self.REVIEW_TEXT, "pack", "review")
        assert result == tmp_history

    def test_creates_parent_dirs(self, tmp_history):
        # The dir didn't exist before save_decision
        assert not tmp_history.parent.exists() or not tmp_history.exists()
        save_decision("dec", "review text", "pack", "review")
        assert tmp_history.parent.exists()


# ── Unit: load_history ────────────────────────────────────────────────────────


class TestLoadHistory:
    def test_returns_empty_when_no_file(self, tmp_history):
        assert load_history() == []

    def test_filters_by_days(self, tmp_history):
        old_entry = _make_entry("old", days_ago=40)
        new_entry = _make_entry("new", days_ago=5)
        with tmp_history.open("w") as f:
            f.write(json.dumps(old_entry) + "\n")
            f.write(json.dumps(new_entry) + "\n")

        entries = load_history(days=30)
        assert len(entries) == 1
        assert entries[0]["decision_name"] == "new"

    def test_all_time_when_days_zero(self, tmp_history):
        old_entry = _make_entry("old", days_ago=400)
        new_entry = _make_entry("new", days_ago=5)
        with tmp_history.open("w") as f:
            f.write(json.dumps(old_entry) + "\n")
            f.write(json.dumps(new_entry) + "\n")

        entries = load_history(days=0)
        assert len(entries) == 2

    def test_filters_by_pack(self, tmp_history):
        e1 = _make_entry("dec-1", pack="staff-core")
        e2 = _make_entry("dec-2", pack="oncall-future-you")
        with tmp_history.open("w") as f:
            f.write(json.dumps(e1) + "\n")
            f.write(json.dumps(e2) + "\n")

        entries = load_history(pack="staff-core")
        assert len(entries) == 1
        assert entries[0]["pack"] == "staff-core"

    def test_newest_first(self, tmp_history):
        e1 = _make_entry("first", days_ago=10)
        e2 = _make_entry("second", days_ago=2)
        with tmp_history.open("w") as f:
            f.write(json.dumps(e1) + "\n")
            f.write(json.dumps(e2) + "\n")

        entries = load_history(days=30)
        assert entries[0]["decision_name"] == "second"
        assert entries[1]["decision_name"] == "first"

    def test_skips_malformed_lines(self, tmp_history):
        good = _make_entry("good")
        with tmp_history.open("w") as f:
            f.write("not-valid-json\n")
            f.write(json.dumps(good) + "\n")

        entries = load_history()
        assert len(entries) == 1
        assert entries[0]["decision_name"] == "good"

    def test_skips_blank_lines(self, tmp_history):
        good = _make_entry("good")
        with tmp_history.open("w") as f:
            f.write("\n")
            f.write(json.dumps(good) + "\n")
            f.write("\n")

        entries = load_history()
        assert len(entries) == 1


# ── Unit: analyze_trends ──────────────────────────────────────────────────────


class TestAnalyzeTrends:
    def test_empty_history(self):
        result = analyze_trends([])
        assert result["total_decisions"] == 0
        assert result["risk_frequency"] == []
        assert result["flagged_risks"] == []

    def test_counts_risk_frequency(self):
        history = [
            _make_entry(key_risks=["knowledge concentration", "missing tests"]),
            _make_entry(key_risks=["knowledge concentration"]),
            _make_entry(key_risks=["knowledge concentration", "no rollback"]),
        ]
        result = analyze_trends(history)
        freq = dict(result["risk_frequency"])
        assert freq["knowledge concentration"] == 3

    def test_flags_risks_at_threshold(self):
        # Exactly at threshold
        history = [_make_entry(key_risks=["knowledge concentration"]) for _ in range(PATTERN_THRESHOLD)]
        result = analyze_trends(history)
        assert "knowledge concentration" in result["flagged_risks"]

    def test_does_not_flag_below_threshold(self):
        history = [_make_entry(key_risks=["rare risk"]) for _ in range(PATTERN_THRESHOLD - 1)]
        result = analyze_trends(history)
        assert "rare risk" not in result["flagged_risks"]

    def test_suggestions_for_flagged_risks(self):
        history = [_make_entry(key_risks=["knowledge concentration"]) for _ in range(PATTERN_THRESHOLD)]
        result = analyze_trends(history)
        assert "knowledge concentration" in result["suggestions"]
        assert len(result["suggestions"]["knowledge concentration"]) > 0

    def test_generic_suggestion_for_unknown_risk(self):
        history = [_make_entry(key_risks=["totally unique risk xyz"]) for _ in range(PATTERN_THRESHOLD)]
        result = analyze_trends(history)
        assert "totally unique risk xyz" in result["suggestions"]
        advice = result["suggestions"]["totally unique risk xyz"]
        assert "totally unique risk xyz" in advice

    def test_pack_frequency(self):
        history = [
            _make_entry(pack="staff-core"),
            _make_entry(pack="staff-core"),
            _make_entry(pack="oncall-future-you"),
        ]
        result = analyze_trends(history)
        pack_counts = dict(result["most_used_packs"])
        assert pack_counts["staff-core"] == 2
        assert pack_counts["oncall-future-you"] == 1

    def test_date_range(self):
        history = [
            _make_entry(days_ago=10),
            _make_entry(days_ago=5),
            _make_entry(days_ago=1),
        ]
        result = analyze_trends(history)
        assert result["date_range"]["from"] is not None
        assert result["date_range"]["to"] is not None

    def test_normalises_risk_case(self):
        history = [
            _make_entry(key_risks=["Knowledge Concentration"]),
            _make_entry(key_risks=["knowledge concentration"]),
            _make_entry(key_risks=["KNOWLEDGE CONCENTRATION"]),
        ]
        result = analyze_trends(history)
        freq = dict(result["risk_frequency"])
        assert freq.get("knowledge concentration", 0) == 3

    def test_total_decisions(self):
        history = [_make_entry() for _ in range(7)]
        result = analyze_trends(history)
        assert result["total_decisions"] == 7


# ── Integration: CLI commands ─────────────────────────────────────────────────


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config():
    with patch("staff_review.cli.GreybeardConfig") as mock:
        config = MagicMock()
        config.llm.backend = "openai"
        config.llm.model = "gpt-4o"
        config.llm.resolved_model.return_value = "gpt-4o"
        config.default_mode = "review"
        config.default_pack = "staff-core"
        mock.load.return_value = config
        yield config


class TestAnalyzeWithSaveDecision:
    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    @patch("staff_review.cli.save_decision")
    def test_save_decision_called_when_flag_set(
        self, mock_save, mock_stdin, mock_review, runner, mock_config, tmp_history
    ):
        mock_stdin.return_value = "some diff content"
        mock_review.return_value = "Review output with some risks"
        mock_save.return_value = tmp_history

        result = runner.invoke(cli, ["analyze", "--save-decision", "auth-migration"])
        assert result.exit_code == 0
        mock_save.assert_called_once()
        call_args = mock_save.call_args
        assert call_args[0][0] == "auth-migration"

    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    def test_save_decision_not_called_without_flag(
        self, mock_stdin, mock_review, runner, mock_config
    ):
        mock_stdin.return_value = "some diff content"
        mock_review.return_value = "Review output"

        with patch("staff_review.cli.save_decision") as mock_save:
            result = runner.invoke(cli, ["analyze"])
            assert result.exit_code == 0
            mock_save.assert_not_called()

    @patch("staff_review.cli.run_review")
    @patch("staff_review.cli._read_stdin_if_available")
    def test_save_decision_prints_confirmation(
        self, mock_stdin, mock_review, runner, mock_config, tmp_history
    ):
        mock_stdin.return_value = "some diff content"
        mock_review.return_value = "Review output"

        with patch("staff_review.cli.save_decision", return_value=tmp_history):
            result = runner.invoke(cli, ["analyze", "--save-decision", "my-dec"])
            assert "history" in result.output.lower()


class TestTrendsCommand:
    def test_trends_no_history(self, runner, tmp_history):
        with patch("staff_review.cli.load_history", return_value=[]):
            result = runner.invoke(cli, ["trends"])
            assert result.exit_code == 0
            assert "No decision history" in result.output

    def test_trends_with_history(self, runner, tmp_history):
        history = [
            _make_entry("dec-1", key_risks=["knowledge concentration"]),
            _make_entry("dec-2", key_risks=["knowledge concentration"]),
            _make_entry("dec-3", key_risks=["knowledge concentration", "missing tests"]),
        ]
        with patch("staff_review.cli.load_history", return_value=history):
            result = runner.invoke(cli, ["trends"])
            assert result.exit_code == 0
            assert "knowledge concentration" in result.output
            assert "recurring" in result.output.lower()

    def test_trends_last_flag(self, runner, tmp_history):
        with patch("staff_review.cli.load_history", return_value=[]) as mock_load:
            runner.invoke(cli, ["trends", "--last", "7"])
            mock_load.assert_called_once_with(days=7, pack=None)

    def test_trends_pack_filter(self, runner, tmp_history):
        with patch("staff_review.cli.load_history", return_value=[]) as mock_load:
            runner.invoke(cli, ["trends", "--pack", "staff-core"])
            mock_load.assert_called_once_with(days=30, pack="staff-core")

    def test_trends_shows_flagged_pattern(self, runner, tmp_history):
        history = [
            _make_entry(key_risks=["knowledge concentration"]) for _ in range(PATTERN_THRESHOLD)
        ]
        with patch("staff_review.cli.load_history", return_value=history):
            result = runner.invoke(cli, ["trends"])
            assert result.exit_code == 0
            # Should flag the recurring risk
            assert "recurring" in result.output.lower() or "⚠" in result.output

    def test_trends_help(self, runner):
        result = runner.invoke(cli, ["trends", "--help"])
        assert result.exit_code == 0
        assert "last" in result.output


class TestHistoryCommand:
    def test_history_no_entries(self, runner, tmp_history):
        with patch("staff_review.cli.load_history", return_value=[]):
            result = runner.invoke(cli, ["history"])
            assert result.exit_code == 0
            assert "No history" in result.output

    def test_history_shows_entries(self, runner, tmp_history):
        history = [_make_entry("auth-migration")]
        with patch("staff_review.cli.load_history", return_value=history):
            result = runner.invoke(cli, ["history"])
            assert result.exit_code == 0
            assert "auth-migration" in result.output

    def test_history_help(self, runner):
        result = runner.invoke(cli, ["history", "--help"])
        assert result.exit_code == 0
        assert "last" in result.output


# ── Round-trip integration ────────────────────────────────────────────────────


class TestRoundTrip:
    """End-to-end: save decisions then load and analyze trends."""

    REVIEW = """
## Risks

- Knowledge concentration — only one engineer knows this system
- No rollback plan for the database migration
- Missing integration test coverage

## Questions

- Have you considered a staged rollout?
- What's the rollback procedure if the migration corrupts data?
"""

    def test_save_load_analyze_round_trip(self, tmp_history):
        # Save 4 decisions with overlapping risks
        for i in range(4):
            save_decision(f"decision-{i}", self.REVIEW, "staff-core", "review")

        entries = load_history(days=30)
        assert len(entries) == 4

        result = analyze_trends(entries)
        assert result["total_decisions"] == 4
        assert result["risk_frequency"]
        # "knowledge concentration" should appear in flagged risks
        flagged = result["flagged_risks"]
        assert any("knowledge" in r for r in flagged)

    def test_save_then_filter_by_pack(self, tmp_history):
        save_decision("dec-a", self.REVIEW, "staff-core", "review")
        save_decision("dec-b", self.REVIEW, "oncall-future-you", "review")

        staff_entries = load_history(pack="staff-core")
        assert len(staff_entries) == 1
        assert staff_entries[0]["pack"] == "staff-core"
