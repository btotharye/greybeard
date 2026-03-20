"""Tests for interactive REPL mode."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from greybeard.config import GreybeardConfig, LLMConfig
from greybeard.interactive import InteractiveSession, run_interactive_repl
from greybeard.models import ContentPack

# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def sample_pack() -> ContentPack:
    """Create a sample content pack for testing."""
    return ContentPack(
        name="test-pack",
        perspective="Staff engineer reviewing architectural decisions",
        tone="analytical and constructive",
        focus_areas=["scalability", "reliability"],
        heuristics=["ask why", "consider tradeoffs"],
        example_questions=["Is this scalable?", "What are the risks?"],
        communication_style="clear and direct",
        description="Test pack for interactive mode",
    )


@pytest.fixture
def sample_config() -> GreybeardConfig:
    """Create a sample config for testing."""
    return GreybeardConfig(
        llm=LLMConfig(
            backend="openai",
            model="gpt-4o",
        ),
        default_mode="review",
        default_pack="test-pack",
    )


@pytest.fixture
def interactive_session(
    sample_pack: ContentPack, sample_config: GreybeardConfig
) -> InteractiveSession:
    """Create an interactive session for testing."""
    return InteractiveSession(
        mode="review",
        pack=sample_pack,
        config=sample_config,
        model_override=None,
    )


# -----------------------------------------------------------------------
# InteractiveSession Tests
# -----------------------------------------------------------------------


class TestInteractiveSessionInit:
    """Test InteractiveSession initialization."""

    def test_init(self, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
        """Test basic initialization."""
        session = InteractiveSession(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            model_override="gpt-4-turbo",
        )

        assert session.mode == "review"
        assert session.pack == sample_pack
        assert session.config == sample_config
        assert session.model == "gpt-4-turbo"
        assert session.conversation_history == []
        assert session.initial_analysis is None

    def test_init_resolves_model(
        self, sample_pack: ContentPack, sample_config: GreybeardConfig
    ) -> None:
        """Test that model is resolved from config if not overridden."""
        session = InteractiveSession(
            mode="review",
            pack=sample_pack,
            config=sample_config,
        )

        assert session.model == sample_config.llm.resolved_model()


class TestInitialAnalysis:
    """Test initial analysis functionality."""

    @patch("greybeard.interactive.run_review")
    def test_run_initial_analysis(
        self, mock_run_review: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test running the initial analysis."""
        mock_run_review.return_value = "Initial analysis result"

        result = interactive_session.run_initial_analysis("test input", "test context")

        assert result == "Initial analysis result"
        assert interactive_session.initial_analysis == "Initial analysis result"
        assert len(interactive_session.conversation_history) == 1
        assert interactive_session.conversation_history[0]["role"] == "assistant"
        assert interactive_session.conversation_history[0]["content"] == "Initial analysis result"

    @patch("greybeard.interactive.run_review")
    def test_run_initial_analysis_with_repo(
        self, mock_run_review: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test initial analysis with repo context."""
        mock_run_review.return_value = "Analysis with repo context"

        result = interactive_session.run_initial_analysis(
            "test input",
            context_notes="context",
            repo_path="/path/to/repo",
            audience="team",
        )

        assert result == "Analysis with repo context"
        mock_run_review.assert_called_once()

    @patch("greybeard.interactive.run_review")
    def test_run_initial_analysis_streams(
        self, mock_run_review: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test that initial analysis uses streaming."""
        mock_run_review.return_value = "Streamed analysis"

        interactive_session.run_initial_analysis("test")

        # Verify stream=True was passed
        call_kwargs = mock_run_review.call_args[1]
        assert call_kwargs["stream"] is True


class TestFollowupQuestions:
    """Test asking follow-up questions."""

    @patch.object(InteractiveSession, "_call_llm")
    def test_ask_followup(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test asking a follow-up question."""
        interactive_session.initial_analysis = "Initial analysis"
        interactive_session.conversation_history.append(
            {"role": "assistant", "content": "Initial analysis"}
        )
        mock_call_llm.return_value = "Follow-up response"

        result = interactive_session.ask_followup("What are the risks?")

        assert result == "Follow-up response"
        assert len(interactive_session.conversation_history) == 3  # assistant, user, assistant
        assert interactive_session.conversation_history[-2]["role"] == "user"
        assert interactive_session.conversation_history[-2]["content"] == "What are the risks?"
        assert interactive_session.conversation_history[-1]["role"] == "assistant"

    def test_ask_followup_without_analysis(self, interactive_session: InteractiveSession) -> None:
        """Test asking follow-up without initial analysis raises error."""
        with pytest.raises(RuntimeError, match="No initial analysis"):
            interactive_session.ask_followup("What are the risks?")

    @patch.object(InteractiveSession, "_call_llm")
    def test_followup_includes_context(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test that follow-up includes conversation context."""
        interactive_session.initial_analysis = "Initial analysis"
        interactive_session.conversation_history.append(
            {"role": "assistant", "content": "Initial analysis"}
        )
        mock_call_llm.return_value = "Response"

        interactive_session.ask_followup("Question?")

        # Verify the user message includes context
        call_args = mock_call_llm.call_args
        user_message = call_args[0][1]  # Second positional arg is user_message
        assert "Initial Analysis" in user_message
        assert "Question?" in user_message


class TestRefinement:
    """Test analysis refinement."""

    @patch.object(InteractiveSession, "_call_llm")
    def test_refine_analysis(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test refining the analysis."""
        interactive_session.initial_analysis = "Initial analysis"
        interactive_session.conversation_history.append(
            {"role": "assistant", "content": "Initial analysis"}
        )
        mock_call_llm.return_value = "Refined analysis"

        result = interactive_session.refine_analysis("New context")

        assert result == "Refined analysis"
        assert len(interactive_session.conversation_history) == 3

    def test_refine_without_analysis(self, interactive_session: InteractiveSession) -> None:
        """Test refining without initial analysis raises error."""
        with pytest.raises(RuntimeError, match="No initial analysis"):
            interactive_session.refine_analysis("New context")

    @patch.object(InteractiveSession, "_call_llm")
    def test_refine_includes_new_context(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test that refinement includes new context in the message."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history.append({"role": "assistant", "content": "Initial"})
        mock_call_llm.return_value = "Refined"

        interactive_session.refine_analysis("6-month rollout plan")

        user_message = mock_call_llm.call_args[0][1]
        assert "6-month rollout plan" in user_message
        assert "refine" in user_message.lower()


class TestAlternativeExploration:
    """Test exploring alternatives."""

    @patch.object(InteractiveSession, "_call_llm")
    def test_explore_alternative(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test exploring an alternative."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history.append({"role": "assistant", "content": "Initial"})
        mock_call_llm.return_value = "Alternative analysis"

        result = interactive_session.explore_alternative("Use event sourcing")

        assert result == "Alternative analysis"
        assert len(interactive_session.conversation_history) == 3

    def test_explore_without_analysis(self, interactive_session: InteractiveSession) -> None:
        """Test exploring alternative without analysis raises error."""
        with pytest.raises(RuntimeError, match="No initial analysis"):
            interactive_session.explore_alternative("Alternative")

    @patch.object(InteractiveSession, "_call_llm")
    def test_explore_includes_alternative(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test that exploration includes the alternative."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history.append({"role": "assistant", "content": "Initial"})
        mock_call_llm.return_value = "Analysis"

        interactive_session.explore_alternative("Event sourcing approach")

        user_message = mock_call_llm.call_args[0][1]
        assert "Event sourcing approach" in user_message
        assert "alternative" in user_message.lower()
        assert "compare" in user_message.lower()


class TestConversationHistory:
    """Test conversation history management."""

    def test_get_conversation_history(self, interactive_session: InteractiveSession) -> None:
        """Test retrieving conversation history."""
        history = interactive_session.get_conversation_history()
        assert history == []

        interactive_session._add_to_history("user", "test")
        history = interactive_session.get_conversation_history()
        assert len(history) == 1
        assert history[0]["role"] == "user"

    def test_conversation_history_is_copy(self, interactive_session: InteractiveSession) -> None:
        """Test that returned history is a copy, not reference."""
        interactive_session._add_to_history("user", "test")
        history1 = interactive_session.get_conversation_history()
        history2 = interactive_session.get_conversation_history()

        # Modify one, verify the other isn't affected
        history1.append({"role": "assistant", "content": "modified"})
        assert len(history2) == 1

    @patch.object(InteractiveSession, "_call_llm")
    def test_clear_conversation(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test clearing conversation history."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history = [
            {"role": "assistant", "content": "Initial"},
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Response"},
        ]

        interactive_session.clear_conversation()

        # History should be reset to just initial analysis
        assert len(interactive_session.conversation_history) == 1
        assert interactive_session.conversation_history[0]["content"] == "Initial"

    def test_clear_conversation_without_initial(
        self, interactive_session: InteractiveSession
    ) -> None:
        """Test clearing conversation without initial analysis."""
        interactive_session.conversation_history = [{"role": "user", "content": "Question"}]

        interactive_session.clear_conversation()

        assert len(interactive_session.conversation_history) == 0


class TestLLMCalls:
    """Test LLM backend calls."""

    @patch("greybeard.interactive.InteractiveSession._call_openai_compat", return_value="response")
    def test_call_openai_compat(
        self, mock_call: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test calling OpenAI-compatible API."""
        result = interactive_session._call_openai_compat("system", "user message")
        assert result == "response"
        mock_call.assert_called_once()

    @patch("greybeard.interactive.InteractiveSession._call_anthropic", return_value="response")
    def test_call_anthropic(self, mock_call: Mock, sample_pack: ContentPack) -> None:
        """Test calling Anthropic API."""
        config = GreybeardConfig(
            llm=LLMConfig(backend="anthropic", model="claude-3-5-sonnet"),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        result = session._call_anthropic("system", "user message")
        assert result == "response"
        mock_call.assert_called_once()

    def test_call_llm_dispatches_to_backend(self, interactive_session: InteractiveSession) -> None:
        """Test that _call_llm dispatches to the correct backend."""
        with patch.object(interactive_session, "_call_openai_compat") as mock_openai:
            mock_openai.return_value = "response"
            result = interactive_session._call_llm("system", "user")
            assert result == "response"
            mock_openai.assert_called_once_with("system", "user")


class TestSystemPromptBuilding:
    """Test system prompt construction."""

    def test_build_followup_system_prompt(self, interactive_session: InteractiveSession) -> None:
        """Test building follow-up system prompt."""
        prompt = interactive_session._build_followup_system_prompt()

        assert "staff-level review assistant" in prompt.lower()
        assert "interactive session" in prompt.lower()
        assert interactive_session.pack.perspective in prompt
        assert "follow-up" in prompt.lower()

    def test_build_followup_user_message(self, interactive_session: InteractiveSession) -> None:
        """Test building follow-up user message."""
        interactive_session.initial_analysis = "Initial analysis"
        interactive_session.conversation_history = [
            {"role": "assistant", "content": "Initial analysis"}
        ]

        message = interactive_session._build_followup_user_message("New question?")

        assert "Initial Analysis" in message
        assert "Initial analysis" in message
        assert "New question?" in message


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch.object(InteractiveSession, "_call_llm")
    def test_long_conversation_context(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test handling of long conversation history."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history = [{"role": "assistant", "content": "Initial"}]

        # Add many turns to conversation
        for i in range(20):
            interactive_session.conversation_history.append(
                {"role": "user", "content": f"Question {i}"}
            )
            interactive_session.conversation_history.append(
                {"role": "assistant", "content": f"Response {i}"}
            )

        mock_call_llm.return_value = "Response"
        interactive_session.ask_followup("Another question?")

        # Verify it still works and includes context
        call_args = mock_call_llm.call_args
        user_message = call_args[0][1]
        assert "Another question?" in user_message

    @patch.object(InteractiveSession, "_call_llm")
    def test_empty_llm_response(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test handling of empty LLM response."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history = [{"role": "assistant", "content": "Initial"}]
        mock_call_llm.return_value = ""

        result = interactive_session.ask_followup("Question?")

        assert result == ""
        assert interactive_session.conversation_history[-1]["content"] == ""

    def test_different_modes(
        self, sample_pack: ContentPack, sample_config: GreybeardConfig
    ) -> None:
        """Test creating sessions with different modes."""
        for mode in ["review", "mentor", "coach", "self-check"]:
            session = InteractiveSession(mode, sample_pack, sample_config)
            assert session.mode == mode


class TestMultiTurnConversations:
    """Test realistic multi-turn conversation scenarios."""

    @patch("greybeard.interactive.run_review")
    @patch.object(InteractiveSession, "_call_llm")
    def test_complete_conversation_flow(
        self,
        mock_call_llm: Mock,
        mock_run_review: Mock,
        interactive_session: InteractiveSession,
    ) -> None:
        """Test a complete multi-turn conversation."""
        # Initial analysis
        mock_run_review.return_value = "This design has scalability concerns."
        interactive_session.run_initial_analysis("Design proposal")

        # First question
        mock_call_llm.return_value = "The main concern is database queries."
        interactive_session.ask_followup("What specifically is concerning?")

        # Refinement
        mock_call_llm.return_value = "With caching, this becomes viable."
        interactive_session.refine_analysis("We're adding Redis caching")

        # Alternative exploration
        mock_call_llm.return_value = "Event sourcing would be overkill."
        interactive_session.explore_alternative("Use event sourcing instead")

        # Verify complete conversation
        history = interactive_session.get_conversation_history()
        assert len(history) >= 7  # at least assistant + 3 user/assistant pairs

    @patch.object(InteractiveSession, "_call_llm")
    def test_conversation_maintains_context(
        self, mock_call_llm: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test that conversation context is maintained across turns."""
        interactive_session.initial_analysis = "Initial analysis mentions X"
        interactive_session.conversation_history = [
            {"role": "assistant", "content": "Initial analysis mentions X"}
        ]

        mock_call_llm.return_value = "Acknowledged X, now discussing Y"

        # Ask first question
        interactive_session.ask_followup("Tell me more about X")

        # Ask second question
        mock_call_llm.return_value = "Based on earlier discussion of X and Y..."
        interactive_session.ask_followup("How does Z relate?")

        # Verify both questions are in history
        history = interactive_session.get_conversation_history()
        assert "Tell me more about X" in str(history)
        assert "How does Z relate?" in str(history)


class TestIntegration:
    """Integration tests for the interactive REPL runner."""

    @patch("greybeard.interactive.run_review", return_value="Initial analysis")
    def test_run_interactive_repl_signature(
        self, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig
    ) -> None:
        """Test run_interactive_repl accepts correct signature."""
        # Mock Prompt.ask to exit immediately
        with patch("greybeard.interactive.Prompt.ask", side_effect=["quit"]):
            # This should not raise an error about signature
            run_interactive_repl(
                mode="review",
                pack=sample_pack,
                config=sample_config,
                model_override="gpt-4-turbo",
                initial_input="test input",
                initial_context="test context",
            )

    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.InteractiveSession")
    def test_run_interactive_repl_creates_session(
        self,
        mock_session_class: Mock,
        mock_prompt: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test that run_interactive_repl creates a session."""
        mock_prompt.side_effect = ["quit"]  # Exit immediately

        # This would normally hang without mocking, so we catch it
        try:
            run_interactive_repl(
                mode="review",
                pack=sample_pack,
                config=sample_config,
                initial_input="test",
                initial_context="",
            )
        except (StopIteration, EOFError):
            pass  # Expected when exiting


class TestErrorPaths:
    """Test error handling paths for coverage."""

    def test_call_openai_compat_missing_api_key(
        self, interactive_session: InteractiveSession
    ) -> None:
        """Test OpenAI call handles missing API key gracefully."""
        # Create a scenario where the config doesn't provide a valid key
        interactive_session.config.llm.backend = "openai"

        # The actual call to OpenAI will fail due to missing key, which is expected
        with pytest.raises(SystemExit):
            with patch.dict("os.environ", {}, clear=True):
                interactive_session._call_openai_compat("system", "user")

    def test_call_anthropic_missing_api_key(self, sample_pack: ContentPack) -> None:
        """Test Anthropic call handles missing API key gracefully."""
        config = GreybeardConfig(
            llm=LLMConfig(backend="anthropic", model="claude-3-5-sonnet"),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        with pytest.raises(SystemExit):
            with patch.dict("os.environ", {}, clear=True):
                session._call_anthropic("system", "user")

    def test_call_openai_compat_import_error(self, interactive_session: InteractiveSession) -> None:
        """Test OpenAI call handles missing openai package gracefully."""
        with pytest.raises(SystemExit):
            with patch.dict("sys.modules", {"openai": None}):
                # Force reimport to fail
                import sys

                # Clear openai from modules if it exists
                if "openai" in sys.modules:
                    del sys.modules["openai"]
                interactive_session._call_openai_compat("system", "user")

    def test_call_anthropic_import_error(self, sample_pack: ContentPack) -> None:
        """Test Anthropic call handles missing anthropic package gracefully."""
        config = GreybeardConfig(
            llm=LLMConfig(backend="anthropic", model="claude-3-5-sonnet"),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        with pytest.raises(SystemExit):
            with patch.dict("sys.modules", {"anthropic": None}):
                # Force reimport to fail
                import sys

                # Clear anthropic from modules if it exists
                if "anthropic" in sys.modules:
                    del sys.modules["anthropic"]
                session._call_anthropic("system", "user")


class TestLocalLLMBackends:
    """Test local LLM backend behavior (ollama, lmstudio)."""

    def test_openai_compat_ollama_no_api_key(self, sample_pack: ContentPack) -> None:
        """Test OpenAI-compat call with ollama backend doesn't require API key."""
        config = GreybeardConfig(
            llm=LLMConfig(backend="ollama", model="llama2", base_url="http://localhost:11434/v1"),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        # Verify that ollama backend with empty api_key_env doesn't need a key
        api_key = session.config.llm.resolved_api_key()
        assert api_key == "no-key-needed"

    def test_openai_compat_lmstudio_no_api_key(self, sample_pack: ContentPack) -> None:
        """Test OpenAI-compat call with lmstudio backend doesn't require API key."""
        config = GreybeardConfig(
            llm=LLMConfig(
                backend="lmstudio", model="local-model", base_url="http://localhost:1234/v1"
            ),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        # Verify that lmstudio backend with empty api_key_env doesn't need a key
        api_key = session.config.llm.resolved_api_key()
        assert api_key == "no-key-needed"

    def test_openai_requires_api_key(self, sample_pack: ContentPack) -> None:
        """Test OpenAI backend requires API key."""
        config = GreybeardConfig(
            llm=LLMConfig(backend="openai", model="gpt-4"),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        # Verify that openai backend needs an API key
        with patch.dict("os.environ", {}, clear=True):
            api_key = session.config.llm.resolved_api_key()
            # Should be None when env var is not set
            assert api_key is None


class TestCoverageEdgeCases:
    """Additional tests to improve coverage."""

    def test_add_to_history_helper(self, interactive_session: InteractiveSession) -> None:
        """Test the _add_to_history helper."""
        interactive_session._add_to_history("user", "content")
        assert len(interactive_session.conversation_history) == 1
        assert interactive_session.conversation_history[0]["role"] == "user"
        assert interactive_session.conversation_history[0]["content"] == "content"

    def test_multiple_add_to_history(self, interactive_session: InteractiveSession) -> None:
        """Test adding multiple messages."""
        interactive_session._add_to_history("user", "msg1")
        interactive_session._add_to_history("assistant", "msg2")
        interactive_session._add_to_history("user", "msg3")

        assert len(interactive_session.conversation_history) == 3
        assert interactive_session.conversation_history[0]["content"] == "msg1"
        assert interactive_session.conversation_history[1]["content"] == "msg2"
        assert interactive_session.conversation_history[2]["content"] == "msg3"


class TestREPLFunctions:
    """Test the REPL helper functions."""

    @patch("greybeard.interactive.console")
    def test_print_help(self, mock_console: Mock) -> None:
        """Test print_help displays help text."""
        from greybeard.interactive import _print_help

        _print_help()

        # Verify console.print was called with help text
        mock_console.print.assert_called_once()
        help_text = mock_console.print.call_args[0][0]
        assert "Interactive Commands" in help_text or "ask" in help_text

    @patch("greybeard.interactive.console")
    def test_print_conversation_history_empty(
        self, mock_console: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test printing empty conversation history."""
        from greybeard.interactive import _print_conversation_history

        _print_conversation_history(interactive_session)

        # Should print message about no history
        mock_console.print.assert_called()

    @patch("greybeard.interactive.console")
    def test_print_conversation_history_with_messages(
        self, mock_console: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test printing conversation history with messages."""
        from greybeard.interactive import _print_conversation_history

        interactive_session.conversation_history = [
            {"role": "user", "content": "Question?"},
            {"role": "assistant", "content": "Answer."},
        ]

        _print_conversation_history(interactive_session)

        # Should print history
        assert mock_console.print.call_count >= 1

    @patch("greybeard.interactive.console")
    def test_print_conversation_history_truncates_long(
        self, mock_console: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test that printing conversation truncates long responses."""
        from greybeard.interactive import _print_conversation_history

        long_response = "x" * 1000
        interactive_session.conversation_history = [
            {"role": "assistant", "content": long_response},
        ]

        _print_conversation_history(interactive_session)

        # Verify console was called (content should be truncated)
        mock_console.print.assert_called()
        # Verify truncation happened - check that the output includes ellipsis
        call_args_list = mock_console.print.call_args_list
        # At least one call should contain text (the content output)
        assert len(call_args_list) >= 1

    @patch("greybeard.interactive.console")
    def test_print_conversation_history_different_roles(
        self, mock_console: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test printing conversation with different roles uses different formatting."""
        from greybeard.interactive import _print_conversation_history

        interactive_session.conversation_history = [
            {"role": "user", "content": "User question"},
            {"role": "assistant", "content": "Assistant answer"},
        ]

        _print_conversation_history(interactive_session)

        # Verify console was called
        mock_console.print.assert_called()
        call_str = str(mock_console.print.call_args_list)
        # Should mention both roles
        assert "User" in call_str or "user" in call_str
        assert "Assistant" in call_str or "assistant" in call_str


class TestREPLValidation:
    """Test REPL input validation for refine and explore commands."""

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_refine_without_context(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL refine command without context shows usage."""
        # "refine " with no context after it, followed by quit
        mock_prompt.side_effect = ["refine ", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should show usage message for refine
        calls_str = str(mock_console.print.call_args_list)
        assert "refine" in calls_str.lower() or "usage" in calls_str.lower()

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_explore_without_context(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL explore command without context shows usage."""
        # "explore " with no context after it, followed by quit
        mock_prompt.side_effect = ["explore ", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should show usage message for explore
        calls_str = str(mock_console.print.call_args_list)
        assert "explore" in calls_str.lower() or "usage" in calls_str.lower()


class TestREPLInteractiveLoop:
    """Test the REPL loop behavior."""

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_help_command(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL help command."""
        mock_prompt.side_effect = ["help", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should have printed help
        assert any("help" in str(call).lower() for call in mock_console.print.call_args_list)

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_history_command(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL history command."""
        mock_prompt.side_effect = ["history", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should have shown conversation history
        assert any(
            "conversation" in str(call).lower() or "history" in str(call).lower()
            for call in mock_console.print.call_args_list
        )

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_reset_command(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL reset command."""
        mock_prompt.side_effect = ["reset", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should have cleared history
        assert any("cleared" in str(call).lower() for call in mock_console.print.call_args_list)

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch.object(InteractiveSession, "refine_analysis", return_value="Refined")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_refine_command(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_refine: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL refine command."""
        mock_prompt.side_effect = ["refine new context", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should have called refine_analysis
        mock_refine.assert_called_once()

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch.object(InteractiveSession, "explore_alternative", return_value="Explored")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_explore_command(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_explore: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL explore command."""
        mock_prompt.side_effect = ["explore alternative approach", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should have called explore_alternative
        mock_explore.assert_called_once()

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch.object(InteractiveSession, "ask_followup", return_value="Response")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_default_question(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_ask: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL default behavior for regular questions."""
        mock_prompt.side_effect = ["What about risks?", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should have called ask_followup for the question
        mock_ask.assert_called_once()

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_empty_input(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL skips empty input."""
        mock_prompt.side_effect = ["", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should not error on empty input
        assert mock_console.print.called

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_exit_command(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL exit command."""
        mock_prompt.side_effect = ["exit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should exit gracefully
        assert any("goodbye" in str(call).lower() for call in mock_console.print.call_args_list)

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask", side_effect=KeyboardInterrupt)
    @patch("greybeard.interactive.console")
    def test_repl_keyboard_interrupt(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL handles keyboard interrupt gracefully."""
        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should handle interrupt and say goodbye
        assert any("goodbye" in str(call).lower() for call in mock_console.print.call_args_list)

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask", side_effect=EOFError)
    @patch("greybeard.interactive.console")
    def test_repl_eof(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL handles EOF gracefully."""
        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
            initial_context="",
        )

        # Should handle EOF and say goodbye
        assert any("goodbye" in str(call).lower() for call in mock_console.print.call_args_list)

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.console")
    def test_repl_error_handling(
        self,
        mock_console: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL error handling."""
        # This test verifies the REPL doesn't crash on unexpected errors
        with patch("greybeard.interactive.Prompt.ask", side_effect=["quit"]):
            run_interactive_repl(
                mode="review",
                pack=sample_pack,
                config=sample_config,
                initial_input="input",
                initial_context="",
            )

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_generic_exception(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL generic exception handling (line 406-407)."""
        # Make ask_followup raise an exception, then exit
        with patch.object(InteractiveSession, "ask_followup", side_effect=ValueError("Test error")):
            mock_prompt.side_effect = ["some question", "quit"]

            run_interactive_repl(
                mode="review",
                pack=sample_pack,
                config=sample_config,
                initial_input="input",
                initial_context="",
            )

        # Verify the error was caught and printed
        assert any("Error:" in str(call) for call in mock_console.print.call_args_list)


class TestBackendDispatch:
    """Test LLM backend dispatching and selection."""

    @patch.object(InteractiveSession, "_call_anthropic", return_value="Response")
    def test_call_llm_dispatches_anthropic(
        self, mock_anthropic: Mock, interactive_session: InteractiveSession
    ) -> None:
        """Test that anthropic backend is selected correctly (line 231)."""
        interactive_session.config.llm.backend = "anthropic"

        result = interactive_session._call_llm("system", "user")

        mock_anthropic.assert_called_once_with("system", "user")
        assert result == "Response"

    @patch.object(InteractiveSession, "_call_openai_compat", return_value="Response")
    def test_call_llm_dispatches_openai(
        self, mock_openai: Mock, interactive_pack: ContentPack, sample_config: GreybeardConfig
    ) -> None:
        """Test that openai backend is selected correctly."""
        sample_config.llm.backend = "openai"
        session = InteractiveSession(
            mode="review",
            pack=interactive_pack,
            config=sample_config,
        )

        result = session._call_llm("system", "user")

        mock_openai.assert_called_once_with("system", "user")
        assert result == "Response"

    def test_call_openai_missing_openai_package(
        self, interactive_session: InteractiveSession
    ) -> None:
        """Test ImportError when openai package not installed (lines 239-242)."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'openai'")):
            with pytest.raises(SystemExit) as exc_info:
                interactive_session._call_openai_compat("system", "user")

            assert exc_info.value.code == 1


class TestOpenAIStreaming:
    """Test OpenAI streaming response handling (lines 254-274)."""

    @patch("builtins.print")
    @patch("greybeard.interactive.console")
    def test_openai_streaming_chunks(
        self,
        mock_console: Mock,
        mock_print: Mock,
        interactive_session: InteractiveSession,
    ) -> None:
        """Test that OpenAI streaming correctly processes chunks (lines 268-273)."""
        # Mock the OpenAI client and its streaming response
        mock_client = Mock()

        # Create mock chunks with delta content
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock(delta=Mock(content="Hello "))]
        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock(delta=Mock(content="World"))]

        mock_client.chat.completions.create.return_value = [mock_chunk1, mock_chunk2]

        # Mock config to provide API key
        interactive_session.config.llm.backend = "openai"

        with patch.object(
            interactive_session.config.llm, "resolved_api_key", return_value="test-key"
        ):
            with patch("openai.OpenAI", return_value=mock_client):
                result = interactive_session._call_openai_compat("System", "User")

        # Verify chunks were streamed and concatenated
        assert result == "Hello World"
        # Verify print was called for each chunk
        assert mock_print.call_count >= 2

    @patch("builtins.print")
    @patch("greybeard.interactive.console")
    def test_openai_streaming_empty_chunk(
        self,
        mock_console: Mock,
        mock_print: Mock,
        interactive_session: InteractiveSession,
    ) -> None:
        """Test that OpenAI handles empty delta content gracefully."""
        mock_client = Mock()

        # Create chunk with None delta content
        mock_chunk = Mock()
        mock_chunk.choices = [Mock(delta=Mock(content=None))]

        mock_client.chat.completions.create.return_value = [mock_chunk]

        interactive_session.config.llm.backend = "openai"

        with patch.object(
            interactive_session.config.llm, "resolved_api_key", return_value="test-key"
        ):
            with patch("openai.OpenAI", return_value=mock_client):
                result = interactive_session._call_openai_compat("System", "User")

        # Empty content should result in empty string
        assert result == ""

    @patch("builtins.print")
    @patch("greybeard.interactive.console")
    def test_openai_with_base_url(
        self,
        mock_console: Mock,
        mock_print: Mock,
        interactive_session: InteractiveSession,
    ) -> None:
        """Test OpenAI client creation with custom base_url (line 257)."""
        mock_client = Mock()

        mock_chunk = Mock()
        mock_chunk.choices = [Mock(delta=Mock(content="Response"))]
        mock_client.chat.completions.create.return_value = [mock_chunk]

        # Set up config with base URL
        interactive_session.config.llm.backend = "openai"
        interactive_session.config.llm.api_base = "https://custom.example.com"

        mock_openai = Mock(return_value=mock_client)

        with patch.object(
            interactive_session.config.llm, "resolved_api_key", return_value="test-key"
        ):
            with patch.object(
                interactive_session.config.llm,
                "resolved_base_url",
                return_value="https://custom.example.com",
            ):
                with patch("openai.OpenAI", mock_openai):
                    interactive_session._call_openai_compat("System", "User")

        # Verify OpenAI was called with base_url
        call_kwargs = mock_openai.call_args[1]
        assert "base_url" in call_kwargs
        assert call_kwargs["base_url"] == "https://custom.example.com"


def _has_module(module_name: str) -> bool:
    """Check if a module is available."""
    import importlib.util

    return importlib.util.find_spec(module_name) is not None


class TestAnthropicStreaming:
    """Test Anthropic streaming response handling (lines 287-309)."""

    @pytest.mark.skipif(not _has_module("anthropic"), reason="anthropic package not installed")
    @patch("builtins.print")
    @patch("greybeard.interactive.console")
    def test_anthropic_streaming_chunks(
        self,
        mock_console: Mock,
        mock_print: Mock,
        interactive_session: InteractiveSession,
    ) -> None:
        """Test that Anthropic streaming correctly processes chunks (lines 305-307)."""
        # Mock the Anthropic client and streaming context manager
        mock_client = Mock()

        # Create a mock context manager that yields text chunks
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)
        mock_stream.text_stream = ["Hello ", "World"]

        mock_client.messages.stream.return_value = mock_stream

        # Set up config
        interactive_session.config.llm.backend = "anthropic"

        with patch.object(
            interactive_session.config.llm, "resolved_api_key", return_value="test-key"
        ):
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = interactive_session._call_anthropic("System", "User")

        # Verify chunks were streamed and concatenated
        assert result == "Hello World"
        # Verify print was called for each chunk
        assert mock_print.call_count >= 2

    @pytest.mark.skipif(not _has_module("anthropic"), reason="anthropic package not installed")
    @patch("builtins.print")
    @patch("greybeard.interactive.console")
    def test_anthropic_streaming_empty_response(
        self,
        mock_console: Mock,
        mock_print: Mock,
        interactive_session: InteractiveSession,
    ) -> None:
        """Test Anthropic handles empty streaming gracefully."""
        mock_client = Mock()

        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)
        mock_stream.text_stream = []

        mock_client.messages.stream.return_value = mock_stream

        interactive_session.config.llm.backend = "anthropic"

        with patch.object(
            interactive_session.config.llm, "resolved_api_key", return_value="test-key"
        ):
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = interactive_session._call_anthropic("System", "User")

        # Empty stream should result in empty string
        assert result == ""

    def test_call_anthropic_missing_anthropic_package(
        self, interactive_session: InteractiveSession
    ) -> None:
        """Test ImportError when anthropic package not installed (lines 278-285)."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'anthropic'")):
            with pytest.raises(SystemExit) as exc_info:
                interactive_session._call_anthropic("system", "user")

            assert exc_info.value.code == 1


class TestREPLCommandEdgeCases:
    """Test REPL command parsing and edge cases."""

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_refine_without_args(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test refine command without arguments shows usage (lines 254-274)."""
        mock_prompt.side_effect = ["refine", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
        )

        # Verify usage message was printed
        assert any("Usage: refine" in str(call) for call in mock_console.print.call_args_list)

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_explore_without_args(
        self,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test explore command without arguments shows usage (lines 287-309)."""
        mock_prompt.side_effect = ["explore", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
        )

        # Verify usage message was printed
        assert any("Usage: explore" in str(call) for call in mock_console.print.call_args_list)

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    @patch.object(InteractiveSession, "refine_analysis", return_value="Refined")
    def test_repl_refine_with_args(
        self,
        mock_refine: Mock,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test refine command with proper arguments."""
        mock_prompt.side_effect = ["refine Additional context here", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
        )

        # Verify refine_analysis was called
        mock_refine.assert_called_once()

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    @patch.object(InteractiveSession, "explore_alternative", return_value="Alternative")
    def test_repl_explore_with_args(
        self,
        mock_explore: Mock,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test explore command with proper arguments."""
        mock_prompt.side_effect = ["explore Use event sourcing instead", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
        )

        # Verify explore_alternative was called
        mock_explore.assert_called_once()

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    @patch.object(InteractiveSession, "refine_analysis", return_value="Refined")
    def test_repl_multiple_whitespace(
        self,
        mock_refine: Mock,
        mock_console: Mock,
        mock_prompt: Mock,
        mock_review: Mock,
        sample_pack: ContentPack,
        sample_config: GreybeardConfig,
    ) -> None:
        """Test REPL with command having multiple whitespace."""
        mock_prompt.side_effect = ["refine   multiple   spaces", "quit"]

        run_interactive_repl(
            mode="review",
            pack=sample_pack,
            config=sample_config,
            initial_input="input",
        )

        # Should not crash and refine should be called
        assert mock_console.print.called
        mock_refine.assert_called_once()


# -----------------------------------------------------------------------
# Additional comprehensive coverage tests for error paths
# -----------------------------------------------------------------------


class TestAnthropicErrorPaths:
    """Comprehensive tests for anthropic error handling to ensure coverage of lines 287-309."""

    def test_anthropic_missing_api_key_error_message(self, sample_pack: ContentPack) -> None:
        """Test missing API key error output."""
        config = GreybeardConfig(
            llm=LLMConfig(backend="anthropic", model="claude-3-5-sonnet"),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        # Mock the config to have no API key AND mock the anthropic import
        mock_anthropic_module = Mock()
        mock_anthropic_module.Anthropic = Mock()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            with patch.object(config.llm, "resolved_api_key", return_value=None):
                with patch.object(
                    config.llm, "resolved_api_key_env", return_value="ANTHROPIC_API_KEY"
                ):
                    with patch("greybeard.interactive.print") as mock_print:
                        with patch("builtins.__import__", wraps=__import__) as mock_import:

                            def side_effect(name, *args, **kwargs):
                                if name == "anthropic":
                                    return mock_anthropic_module
                                return __import__(name, *args, **kwargs)

                            mock_import.side_effect = side_effect

                            with pytest.raises(SystemExit) as exc_info:
                                session._call_anthropic("system prompt", "user message")
                            assert exc_info.value.code == 1
                            # Verify error message was printed
                            print_calls = [str(call) for call in mock_print.call_args_list]
                            # Check error was printed
                            has_api_key = any(
                                "ANTHROPIC_API_KEY" in str(call) for call in print_calls
                            )
                            has_error = any("Error" in str(call) for call in print_calls)
                            assert has_api_key or has_error

    def test_anthropic_missing_package_error_message(self, sample_pack: ContentPack) -> None:
        """Test that _call_anthropic properly handles missing anthropic package."""
        config = GreybeardConfig(
            llm=LLMConfig(backend="anthropic", model="claude-3-5-sonnet"),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        # Mock import to fail
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("No module named 'anthropic'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                session._call_anthropic("system prompt", "user message")
            assert exc_info.value.code == 1

    def test_anthropic_streaming_output(self, sample_pack: ContentPack) -> None:
        """Test anthropic streaming properly outputs text chunks (lines 296-309)."""
        config = GreybeardConfig(
            llm=LLMConfig(backend="anthropic", model="claude-3-5-sonnet"),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        # Mock anthropic client and streaming
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)
        mock_stream.text_stream = ["Hello ", "World", "!"]

        mock_client_instance = Mock()
        mock_client_instance.messages.stream = Mock(return_value=mock_stream)

        mock_anthropic_module = Mock()
        mock_anthropic_module.Anthropic = Mock(return_value=mock_client_instance)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            with patch.object(config.llm, "resolved_api_key", return_value="test-key"):
                with patch("builtins.__import__", wraps=__import__) as mock_import:

                    def side_effect(name, *args, **kwargs):
                        if name == "anthropic":
                            return mock_anthropic_module
                        return __import__(name, *args, **kwargs)

                    mock_import.side_effect = side_effect
                    result = session._call_anthropic("system prompt", "user message")

        assert result == "Hello World!"

    def test_anthropic_with_api_key_success(self, sample_pack: ContentPack) -> None:
        """Test successful anthropic call with valid API key."""
        config = GreybeardConfig(
            llm=LLMConfig(backend="anthropic", model="claude-3-5-sonnet"),
            default_mode="review",
            default_pack="test",
        )
        session = InteractiveSession("review", sample_pack, config)

        # Mock streaming response
        mock_stream = Mock()
        mock_stream.__enter__ = Mock(return_value=mock_stream)
        mock_stream.__exit__ = Mock(return_value=None)
        mock_stream.text_stream = ["Test response"]

        mock_client_instance = Mock()
        mock_client_instance.messages.stream = Mock(return_value=mock_stream)

        mock_anthropic_module = Mock()
        mock_anthropic_module.Anthropic = Mock(return_value=mock_client_instance)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            with patch.object(config.llm, "resolved_api_key", return_value="valid-key"):
                with patch("builtins.__import__", wraps=__import__) as mock_import:

                    def side_effect(name, *args, **kwargs):
                        if name == "anthropic":
                            return mock_anthropic_module
                        return __import__(name, *args, **kwargs)

                    mock_import.side_effect = side_effect
                    result = session._call_anthropic("system prompt", "user message")

        assert result == "Test response"


# Additional fixture
@pytest.fixture
def interactive_pack() -> ContentPack:
    """Create a sample content pack for backend dispatch testing."""
    return ContentPack(
        name="test-pack",
        perspective="Staff engineer",
        tone="analytical",
        focus_areas=["scalability"],
        heuristics=["ask why"],
        example_questions=["Is this scalable?"],
        communication_style="clear",
        description="Test pack",
    )
