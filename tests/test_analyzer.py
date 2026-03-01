"""Tests for the analyzer module (no live API calls)."""

from __future__ import annotations

from unittest.mock import patch

from staff_review.analyzer import _build_user_message, _collect_repo_context
from staff_review.config import GreybeardConfig
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
        req = _make_request(input_text="some diff", context_notes="some context")
        msg = _build_user_message(req)
        assert "some diff" in msg
        assert "some context" in msg

    def test_large_input_warns(self, capsys):
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
        context = _collect_repo_context("/nonexistent/path/that/does/not/exist")
        assert isinstance(context, str)
        assert context == ""


class TestRunReviewMocked:
    """Tests for run_review that mock out the LLM call."""

    def test_run_review_calls_openai_compat(self):
        from staff_review.analyzer import run_review

        pack = _make_pack()
        req = _make_request(pack=pack, input_text="some diff", context_notes="some context")
        cfg = GreybeardConfig()  # defaults to openai

        with patch("staff_review.analyzer._run_openai_compat") as mock_run:
            mock_run.return_value = "## Summary\n\nMocked review."
            result = run_review(req, config=cfg, stream=False)

        mock_run.assert_called_once()
        assert result == "## Summary\n\nMocked review."

    def test_run_review_uses_anthropic_for_anthropic_backend(self):
        from staff_review.analyzer import run_review

        pack = _make_pack()
        req = _make_request(pack=pack, input_text="some diff")
        cfg = GreybeardConfig()
        cfg.llm.backend = "anthropic"

        with patch("staff_review.analyzer._run_anthropic") as mock_run:
            mock_run.return_value = "## Summary\n\nAnthropic review."
            result = run_review(req, config=cfg, stream=False)

        mock_run.assert_called_once()
        assert result == "## Summary\n\nAnthropic review."

    def test_model_override_passed_through(self):
        from staff_review.analyzer import run_review

        pack = _make_pack()
        req = _make_request(pack=pack, input_text="diff")
        cfg = GreybeardConfig()

        with patch("staff_review.analyzer._run_openai_compat") as mock_run:
            mock_run.return_value = "result"
            run_review(req, config=cfg, model_override="gpt-4o-mini", stream=False)

        call_args = mock_run.call_args
        assert call_args[0][1] == "gpt-4o-mini"  # model is second positional arg


class TestErrorHandling:
    """Test error paths in analyzer."""

    def test_openai_missing_api_key(self, monkeypatch):
        """Test that missing API key for OpenAI provides helpful error."""
        import pytest

        from staff_review.analyzer import _run_openai_compat
        from staff_review.config import LLMConfig

        # Clear any env vars
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        llm = LLMConfig(backend="openai")  # No api_key_env set, uses default

        with pytest.raises(SystemExit):
            _run_openai_compat(llm, "gpt-4o", "system", "user", stream=False)

    def test_anthropic_missing_api_key(self, monkeypatch):
        """Test that missing API key for Anthropic provides helpful error."""
        import pytest

        from staff_review.analyzer import _run_anthropic
        from staff_review.config import LLMConfig

        # Clear any env vars
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        llm = LLMConfig(backend="anthropic")  # No api_key_env set, uses default

        with pytest.raises(SystemExit):
            _run_anthropic(llm, "claude-3-5-sonnet", "system", "user", stream=False)


class TestStreamingFunctionality:
    """Test streaming paths for both OpenAI and Anthropic."""

    def test_openai_streaming(self, capsys):
        """Test OpenAI streaming path."""
        from unittest.mock import MagicMock

        from staff_review.analyzer import _stream_openai

        # Mock client and stream response
        mock_client = MagicMock()
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Hello"

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = " world"

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=[mock_chunk1, mock_chunk2])
        mock_stream.__exit__ = MagicMock(return_value=False)

        mock_client.chat.completions.create.return_value = mock_stream

        result = _stream_openai(mock_client, "gpt-4o", [])

        assert result == "Hello world"
        captured = capsys.readouterr()
        assert "Hello world" in captured.out

    def test_anthropic_streaming(self, capsys, monkeypatch):
        """Test Anthropic streaming path."""
        import sys
        from unittest.mock import MagicMock

        # Create a mock anthropic module
        mock_anthropic_module = MagicMock()
        sys.modules["anthropic"] = mock_anthropic_module

        try:
            from staff_review.analyzer import _run_anthropic
            from staff_review.config import LLMConfig

            # Set env var so resolved_api_key() returns a value
            monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-from-env")

            llm = LLMConfig(backend="anthropic")

            # Mock the Anthropic client
            mock_client = MagicMock()
            mock_anthropic_module.Anthropic.return_value = mock_client

            # Mock streaming response
            mock_stream = MagicMock()
            mock_stream.__enter__ = MagicMock(return_value=mock_stream)
            mock_stream.__exit__ = MagicMock(return_value=False)
            mock_stream.text_stream = ["Hello", " ", "Anthropic"]

            mock_client.messages.stream.return_value = mock_stream

            result = _run_anthropic(llm, "claude-3-5-sonnet", "system", "user", stream=True)

            assert result == "Hello Anthropic"
            captured = capsys.readouterr()
            assert "Hello Anthropic" in captured.out
        finally:
            # Clean up the mock module
            if "anthropic" in sys.modules:
                del sys.modules["anthropic"]

    def test_anthropic_non_streaming(self, monkeypatch):
        """Test Anthropic non-streaming path."""
        import sys
        from unittest.mock import MagicMock

        # Create a mock anthropic module
        mock_anthropic_module = MagicMock()
        sys.modules["anthropic"] = mock_anthropic_module

        try:
            from staff_review.analyzer import _run_anthropic
            from staff_review.config import LLMConfig

            # Set env var so resolved_api_key() returns a value
            monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-from-env")

            llm = LLMConfig(backend="anthropic")

            # Mock the Anthropic client
            mock_client = MagicMock()
            mock_anthropic_module.Anthropic.return_value = mock_client

            # Mock non-streaming response
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = "Non-streamed response"
            mock_client.messages.create.return_value = mock_response

            result = _run_anthropic(llm, "claude-3-5-sonnet", "system", "user", stream=False)

            assert result == "Non-streamed response"
        finally:
            # Clean up the mock module
            if "anthropic" in sys.modules:
                del sys.modules["anthropic"]
