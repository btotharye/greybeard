"""Tests for the analyzer module (no live API calls)."""

from __future__ import annotations

from staff_review.analyzer import _build_user_message, _collect_repo_context
from staff_review.models import ContentPack, ReviewRequest


def _make_pack() -> ContentPack:
    return ContentPack(name="test", perspective="Tester", tone="calm")


def _make_request(**kwargs) -> ReviewRequest:
    defaults = {
        "mode": "review",
        "pack": _make_pack(),
    }
    defaults.update(kwargs)
    return ReviewRequest(**defaults)  # type: ignore[arg-type]


class TestBuildUserMessage:
    def test_includes_input_text(self):
        req = _make_request(input_text="diff --git a/foo.py b/foo.py\n+some change")
        msg = _build_user_message(req)
        assert "diff --git" in msg

    def test_includes_context_notes(self):
        req = _make_request(context_notes="This is part of a DB migration")
        msg = _build_user_message(req)
        assert "DB migration" in msg

    def test_no_input_returns_fallback(self):
        req = _make_request()
        msg = _build_user_message(req)
        assert "No input" in msg or "no input" in msg.lower()

    def test_both_context_and_input_included(self):
        req = _make_request(
            input_text="some diff",
            context_notes="some context",
        )
        msg = _build_user_message(req)
        assert "some diff" in msg
        assert "some context" in msg

    def test_large_input_does_not_raise(self, capsys):
        large_input = "x" * 200_000
        req = _make_request(input_text=large_input)
        msg = _build_user_message(req)
        assert large_input in msg
        captured = capsys.readouterr()
        assert "Warning" in captured.err


class TestCollectRepoContext:
    def test_includes_readme(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\n\nThis is a test project.")
        context = _collect_repo_context(str(tmp_path))
        assert "My Project" in context
        assert "test project" in context

    def test_includes_directory_structure(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main")
        (tmp_path / "tests").mkdir()
        context = _collect_repo_context(str(tmp_path))
        assert "src" in context
        assert "tests" in context

    def test_skips_node_modules(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "some-lib").mkdir()
        (tmp_path / "src").mkdir()
        context = _collect_repo_context(str(tmp_path))
        assert "node_modules" not in context
        assert "src" in context

    def test_handles_no_readme(self, tmp_path):
        (tmp_path / "src").mkdir()
        context = _collect_repo_context(str(tmp_path))
        assert "README" not in context
        assert "src" in context

    def test_handles_nonexistent_path(self):
        # Should not raise, may return empty string
        context = _collect_repo_context("/nonexistent/path/that/does/not/exist")
        assert isinstance(context, str)
