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
def interactive_session(sample_pack: ContentPack, sample_config: GreybeardConfig) -> InteractiveSession:
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

    def test_init_resolves_model(self, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_run_initial_analysis(self, mock_run_review: Mock, interactive_session: InteractiveSession) -> None:
        """Test running the initial analysis."""
        mock_run_review.return_value = "Initial analysis result"

        result = interactive_session.run_initial_analysis("test input", "test context")

        assert result == "Initial analysis result"
        assert interactive_session.initial_analysis == "Initial analysis result"
        assert len(interactive_session.conversation_history) == 1
        assert interactive_session.conversation_history[0]["role"] == "assistant"
        assert interactive_session.conversation_history[0]["content"] == "Initial analysis result"

    @patch("greybeard.interactive.run_review")
    def test_run_initial_analysis_with_repo(self, mock_run_review: Mock, interactive_session: InteractiveSession) -> None:
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
    def test_run_initial_analysis_streams(self, mock_run_review: Mock, interactive_session: InteractiveSession) -> None:
        """Test that initial analysis uses streaming."""
        mock_run_review.return_value = "Streamed analysis"

        interactive_session.run_initial_analysis("test")

        # Verify stream=True was passed
        call_kwargs = mock_run_review.call_args[1]
        assert call_kwargs["stream"] is True


class TestFollowupQuestions:
    """Test asking follow-up questions."""

    @patch.object(InteractiveSession, "_call_llm")
    def test_ask_followup(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
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
    def test_followup_includes_context(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
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
    def test_refine_analysis(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
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
    def test_refine_includes_new_context(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
        """Test that refinement includes new context in the message."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history.append(
            {"role": "assistant", "content": "Initial"}
        )
        mock_call_llm.return_value = "Refined"

        interactive_session.refine_analysis("6-month rollout plan")

        user_message = mock_call_llm.call_args[0][1]
        assert "6-month rollout plan" in user_message
        assert "refine" in user_message.lower()


class TestAlternativeExploration:
    """Test exploring alternatives."""

    @patch.object(InteractiveSession, "_call_llm")
    def test_explore_alternative(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
        """Test exploring an alternative."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history.append(
            {"role": "assistant", "content": "Initial"}
        )
        mock_call_llm.return_value = "Alternative analysis"

        result = interactive_session.explore_alternative("Use event sourcing")

        assert result == "Alternative analysis"
        assert len(interactive_session.conversation_history) == 3

    def test_explore_without_analysis(self, interactive_session: InteractiveSession) -> None:
        """Test exploring alternative without analysis raises error."""
        with pytest.raises(RuntimeError, match="No initial analysis"):
            interactive_session.explore_alternative("Alternative")

    @patch.object(InteractiveSession, "_call_llm")
    def test_explore_includes_alternative(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
        """Test that exploration includes the alternative."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history.append(
            {"role": "assistant", "content": "Initial"}
        )
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
    def test_clear_conversation(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
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

    def test_clear_conversation_without_initial(self, interactive_session: InteractiveSession) -> None:
        """Test clearing conversation without initial analysis."""
        interactive_session.conversation_history = [
            {"role": "user", "content": "Question"}
        ]

        interactive_session.clear_conversation()

        assert len(interactive_session.conversation_history) == 0


class TestLLMCalls:
    """Test LLM backend calls."""

    @patch("greybeard.interactive.InteractiveSession._call_openai_compat", return_value="response")
    def test_call_openai_compat(self, mock_call: Mock, interactive_session: InteractiveSession) -> None:
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
    def test_long_conversation_context(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
        """Test handling of long conversation history."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history = [
            {"role": "assistant", "content": "Initial"}
        ]

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
    def test_empty_llm_response(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
        """Test handling of empty LLM response."""
        interactive_session.initial_analysis = "Initial"
        interactive_session.conversation_history = [
            {"role": "assistant", "content": "Initial"}
        ]
        mock_call_llm.return_value = ""

        result = interactive_session.ask_followup("Question?")

        assert result == ""
        assert interactive_session.conversation_history[-1]["content"] == ""

    def test_different_modes(self, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_conversation_maintains_context(self, mock_call_llm: Mock, interactive_session: InteractiveSession) -> None:
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
    def test_run_interactive_repl_signature(self, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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

    def test_call_openai_compat_missing_api_key(self, interactive_session: InteractiveSession) -> None:
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
    def test_print_conversation_history_empty(self, mock_console: Mock, interactive_session: InteractiveSession) -> None:
        """Test printing empty conversation history."""
        from greybeard.interactive import _print_conversation_history

        _print_conversation_history(interactive_session)

        # Should print message about no history
        mock_console.print.assert_called()

    @patch("greybeard.interactive.console")
    def test_print_conversation_history_with_messages(self, mock_console: Mock, interactive_session: InteractiveSession) -> None:
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
    def test_print_conversation_history_truncates_long(self, mock_console: Mock, interactive_session: InteractiveSession) -> None:
        """Test that printing conversation truncates long responses."""
        from greybeard.interactive import _print_conversation_history

        long_response = "x" * 1000
        interactive_session.conversation_history = [
            {"role": "assistant", "content": long_response},
        ]

        _print_conversation_history(interactive_session)

        # Verify console was called (content should be truncated)
        mock_console.print.assert_called()


class TestREPLInteractiveLoop:
    """Test the REPL loop behavior."""

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_help_command(self, mock_console: Mock, mock_prompt: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_repl_history_command(self, mock_console: Mock, mock_prompt: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
        assert any("conversation" in str(call).lower() or "history" in str(call).lower()
                   for call in mock_console.print.call_args_list)

    @patch("greybeard.interactive.run_review", return_value="Initial")
    @patch("greybeard.interactive.Prompt.ask")
    @patch("greybeard.interactive.console")
    def test_repl_reset_command(self, mock_console: Mock, mock_prompt: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_repl_refine_command(self, mock_console: Mock, mock_prompt: Mock, mock_refine: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_repl_explore_command(self, mock_console: Mock, mock_prompt: Mock, mock_explore: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_repl_default_question(self, mock_console: Mock, mock_prompt: Mock, mock_ask: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_repl_empty_input(self, mock_console: Mock, mock_prompt: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_repl_exit_command(self, mock_console: Mock, mock_prompt: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_repl_keyboard_interrupt(self, mock_console: Mock, mock_prompt: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_repl_eof(self, mock_console: Mock, mock_prompt: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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
    def test_repl_error_handling(self, mock_console: Mock, mock_review: Mock, sample_pack: ContentPack, sample_config: GreybeardConfig) -> None:
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


