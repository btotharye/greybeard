"""Tests for InterviewCapability."""

from __future__ import annotations

from unittest.mock import patch

from greybeard.common.interview import InterviewCapability


class TestInterviewCapability:
    """Test suite for InterviewCapability."""

    def test_initialization(self):
        """Test InterviewCapability initializes correctly."""
        interview = InterviewCapability()
        assert interview.conversation_history == []
        assert interview.context == {}

    def test_start_interview(self):
        """Test starting a new interview."""
        interview = InterviewCapability()

        with patch("rich.console.Console.print"):
            interview.start_interview(
                opening_question="What is your goal?",
                topic="career",
            )

        assert interview.context["topic"] == "career"
        assert len(interview.conversation_history) == 0

    def test_ask_question(self):
        """Test asking a question."""
        interview = InterviewCapability()

        with patch("rich.prompt.Prompt.ask", return_value="My answer"):
            response = interview.ask_question("What is X?")

        assert response == "My answer"
        assert len(interview.conversation_history) == 1
        assert interview.conversation_history[0]["role"] == "user"
        assert interview.conversation_history[0]["content"] == "My answer"

    def test_ask_multiple_questions(self):
        """Test asking multiple questions."""
        interview = InterviewCapability()

        with patch("rich.prompt.Prompt.ask") as mock_ask:
            mock_ask.side_effect = ["Answer 1", "Answer 2", "Answer 3"]

            interview.ask_question("Q1?")
            interview.ask_question("Q2?")
            interview.ask_question("Q3?")

        assert len(interview.conversation_history) == 3

    def test_ask_followup(self):
        """Test generating AI followup."""
        interview = InterviewCapability()

        def mock_llm_call(system, messages):
            return "Generated followup response"

        interview.conversation_history = [{"role": "user", "content": "Initial response"}]

        response = interview.ask_followup(
            previous_response="User's response",
            system_prompt="System prompt",
            llm_call=mock_llm_call,
        )

        assert response == "Generated followup response"
        assert len(interview.conversation_history) == 3
        # user, assistant, user (from previous), assistant (followup)

    def test_get_history(self):
        """Test retrieving conversation history."""
        interview = InterviewCapability()

        interview.conversation_history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        history = interview.get_history()

        assert len(history) == 2
        # Verify it's a copy, not reference
        history.append({"role": "user", "content": "Q2"})
        assert len(interview.conversation_history) == 2

    def test_get_context(self):
        """Test retrieving interview context."""
        interview = InterviewCapability()
        interview.context = {
            "topic": "promotion",
            "level": "senior",
        }

        context = interview.get_context()

        assert context["topic"] == "promotion"
        assert context["level"] == "senior"
        # Verify it's a copy
        context["new_key"] = "value"
        assert "new_key" not in interview.context

    def test_add_context(self):
        """Test adding context values."""
        interview = InterviewCapability()

        interview.add_context("key1", "value1")
        interview.add_context("key2", 123)

        assert interview.context["key1"] == "value1"
        assert interview.context["key2"] == 123

    def test_summarize_interview(self):
        """Test summarizing interview."""
        interview = InterviewCapability()
        interview.context = {"topic": "career decision"}
        interview.conversation_history = [
            {"role": "user", "content": "I want to change jobs"},
            {"role": "assistant", "content": "That's a big decision"},
            {"role": "user", "content": "Yes, very big"},
        ]

        summary = interview.summarize_interview()

        assert "career decision" in summary
        assert "Interview Summary" in summary
        assert "👤 You" in summary or "User" in summary
        assert "assistant" in summary.lower()

    def test_summarize_empty_interview(self):
        """Test summarizing empty interview."""
        interview = InterviewCapability()

        summary = interview.summarize_interview()

        assert "Interview Summary" in summary

    def test_clear(self):
        """Test clearing interview data."""
        interview = InterviewCapability()

        interview.context = {"topic": "test"}
        interview.conversation_history = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        interview.clear()

        assert interview.context == {}
        assert interview.conversation_history == []

    def test_conversation_flow(self):
        """Test realistic conversation flow."""
        interview = InterviewCapability()

        with patch("rich.console.Console.print"):
            interview.start_interview(
                opening_question="Tell me about your goal",
                topic="career",
            )

        with patch("rich.prompt.Prompt.ask") as mock_ask:
            mock_ask.side_effect = ["Goal is X", "Because of Y"]

            interview.ask_question("Why?")
            interview.ask_question("How will you achieve it?")

        assert interview.context["topic"] == "career"
        assert len(interview.conversation_history) == 2
        assert interview.conversation_history[0]["content"] == "Goal is X"
        assert interview.conversation_history[1]["content"] == "Because of Y"

    def test_llm_integration(self):
        """Test LLM integration in followups."""
        interview = InterviewCapability()

        def mock_llm(system, messages):
            return f"Response to: {messages[-1]['content']}"

        interview.conversation_history = [{"role": "user", "content": "Initial thought"}]

        response = interview.ask_followup(
            previous_response="User thinking more",
            system_prompt="Help analyze",
            llm_call=mock_llm,
        )

        assert "Response to:" in response
        assert "User thinking more" in response
