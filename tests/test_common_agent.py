"""Tests for BaseAgent class and framework."""

from __future__ import annotations

from unittest.mock import Mock

from greybeard.common.agent import BaseAgent


class ConcreteAgent(BaseAgent):
    """Concrete agent for testing BaseAgent."""

    def run(self, user_input: str) -> dict:
        """Simple implementation for testing."""
        return {
            "input": user_input,
            "history_length": len(self.conversation_history),
        }


class TestBaseAgent:
    """Test suite for BaseAgent."""

    def test_initialization(self):
        """Test agent initialization."""
        agent = ConcreteAgent(
            name="test-agent",
            description="A test agent",
        )

        assert agent.name == "test-agent"
        assert agent.description == "A test agent"
        assert len(agent.conversation_history) == 0
        assert agent.context == {}

    def test_custom_system_prompt(self):
        """Test initialization with custom system prompt."""
        custom_prompt = "Custom system prompt"
        agent = ConcreteAgent(
            name="test",
            description="test",
            system_prompt=custom_prompt,
        )

        assert agent.system_prompt == custom_prompt

    def test_default_system_prompt(self):
        """Test default system prompt generation."""
        agent = ConcreteAgent(
            name="reviewer",
            description="reviews decisions",
        )

        assert "reviewer" in agent.system_prompt.lower()
        assert "reviews decisions" in agent.system_prompt.lower()

    def test_run_method(self):
        """Test run method execution."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        result = agent.run("test input")

        assert result["input"] == "test input"
        assert result["history_length"] == 0

    def test_conversation_history_management(self):
        """Test conversation history tracking."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        # Add messages manually
        agent.conversation_history.append({"role": "user", "content": "Hello"})
        agent.conversation_history.append({"role": "assistant", "content": "Hi there"})

        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0]["role"] == "user"
        assert agent.conversation_history[1]["role"] == "assistant"

    def test_gather_context(self):
        """Test context gathering."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        context_sources = {
            "file": "content.txt",
            "repo": "my-repo",
        }

        result = agent.gather_context(context_sources)

        assert result == context_sources
        assert agent.context == context_sources

    def test_format_output_markdown(self):
        """Test markdown output formatting."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        content = "# Test\n\nContent here"
        metadata = {"timestamp": "2026-03-18", "version": "1.0"}

        result = agent.format_output(
            content=content,
            format_type="markdown",
            metadata=metadata,
        )

        assert "---" in result  # Metadata marker
        assert "timestamp:" in result
        assert content in result

    def test_format_output_json(self):
        """Test JSON output formatting."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        content = "Test content"
        result = agent.format_output(
            content=content,
            format_type="json",
        )

        import json

        parsed = json.loads(result)
        assert parsed["content"] == content
        assert "timestamp" in parsed

    def test_capabilities_initialization(self):
        """Test that agent initializes all capabilities."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        # All capabilities should be initialized
        assert agent.llm is not None
        assert agent.research is not None
        assert agent.interview is not None
        assert agent.documentation is not None

    def test_multi_turn_conversation_single_turn(self):
        """Test multi-turn conversation with immediate completion."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        # Mock the LLM to return immediately
        agent.llm.call = Mock(return_value="Response 1")

        def is_complete(response):
            return "Response" in response  # Always complete

        result = agent.multi_turn_conversation(
            initial_question="Question?",
            expected_completion_fn=is_complete,
        )

        assert result == "Response 1"
        # Multi-turn conversation records both user and assistant messages
        assert len(agent.conversation_history) == 2

    def test_save_conversation(self, tmp_path):
        """Test saving conversation to file."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        agent.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        agent.context = {"topic": "test"}

        filepath = tmp_path / "conversation.json"
        agent.save_conversation(str(filepath))

        assert filepath.exists()

        import json

        with open(filepath) as f:
            data = json.load(f)

        assert data["agent"] == "test"
        assert len(data["conversation"]) == 2
        assert data["context"]["topic"] == "test"

    def test_multi_turn_conversation_max_turns(self):
        """Test multi-turn conversation stops at max turns."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        agent.llm.call = Mock(return_value="Response")

        # Mock input() to return empty on second call (simulating user exit)
        from unittest.mock import patch

        with patch("builtins.input", side_effect=["", ""]):
            result = agent.multi_turn_conversation(
                initial_question="Start?",
                max_turns=2,
            )

        assert result == "Response"

    def test_multi_turn_conversation_no_completion_fn(self):
        """Test multi-turn conversation without completion function."""
        agent = ConcreteAgent(
            name="test",
            description="test",
        )

        agent.llm.call = Mock(return_value="Final response")

        from unittest.mock import patch

        with patch("builtins.input", return_value=""):
            result = agent.multi_turn_conversation(
                initial_question="Question?",
                max_turns=1,
            )

        assert result == "Final response"


class TestAgentInheritance:
    """Test agent inheritance patterns."""

    def test_subclass_can_override_methods(self):
        """Test that subclasses can override methods."""

        class CustomAgent(BaseAgent):
            def run(self, user_input: str) -> dict:
                return {"custom": True}

            def _default_system_prompt(self) -> str:
                return "Custom prompt"

        agent = CustomAgent("test", "test")

        assert agent.system_prompt == "Custom prompt"
        assert agent.run("test")["custom"] is True

    def test_multiple_agents_independent_history(self):
        """Test that different agents have independent history."""
        agent1 = ConcreteAgent("agent1", "test")
        agent2 = ConcreteAgent("agent2", "test")

        agent1.conversation_history.append({"role": "user", "content": "A"})
        agent2.conversation_history.append({"role": "user", "content": "B"})

        assert len(agent1.conversation_history) == 1
        assert len(agent2.conversation_history) == 1
        assert agent1.conversation_history[0]["content"] == "A"
        assert agent2.conversation_history[0]["content"] == "B"
