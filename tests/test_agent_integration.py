"""Integration tests for agent framework."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock

from greybeard.common.agent import BaseAgent
from greybeard.common.llm_wrapper import LLMWrapper


class SimpleAgent(BaseAgent):
    """Simple agent for testing."""
    
    def run(self, user_input: str) -> dict:
        """Simple run implementation."""
        return {
            "input": user_input,
            "history_length": len(self.conversation_history),
            "context": self.context.copy(),
        }


class IntegrationTestAgent(BaseAgent):
    """Agent with full capability usage."""
    
    def run(self, user_input: str) -> dict:
        """Run with all capabilities."""
        # Gather context
        self.context["input"] = user_input
        
        # Multi-turn conversation
        result = self.multi_turn_conversation(
            initial_question=user_input,
            expected_completion_fn=self._is_done,
        )
        
        # Format output
        formatted = self.documentation.format(result, "markdown")
        
        return {
            "result": result,
            "formatted": formatted,
            "conversation_turns": len(self.conversation_history),
        }
    
    def _is_done(self, response: str) -> bool:
        """Check if conversation is complete."""
        return len(response) > 0


class TestAgentIntegration:
    """Integration tests for agent framework."""

    def test_agent_full_lifecycle(self):
        """Test full agent lifecycle."""
        agent = SimpleAgent(
            name="test-agent",
            description="integration test",
        )
        
        # Gather context
        agent.gather_context({"source": "test"})
        assert agent.context["source"] == "test"
        
        # Run agent
        result = agent.run("test input")
        
        # Verify results
        assert result["input"] == "test input"
        assert result["context"]["source"] == "test"

    def test_agent_with_multiple_capabilities(self):
        """Test agent using multiple capabilities."""
        agent = IntegrationTestAgent(
            name="multi-capability",
            description="test multiple capabilities",
        )
        
        # Mock LLM
        agent.llm.call = Mock(return_value="Test response from LLM")
        
        result = agent.run("What should I do?")
        
        assert "result" in result
        assert "formatted" in result
        assert result["conversation_turns"] > 0

    def test_agent_conversation_tracking(self):
        """Test agent tracks conversation properly."""
        agent = SimpleAgent(
            name="conversation-tracker",
            description="test",
        )
        
        # Simulate conversation
        agent.conversation_history.append({"role": "user", "content": "Q1"})
        agent.conversation_history.append({"role": "assistant", "content": "A1"})
        agent.conversation_history.append({"role": "user", "content": "Q2"})
        
        result = agent.run("Q3")
        
        # Conversation should be tracked
        assert agent.conversation_history[0]["content"] == "Q1"
        assert agent.conversation_history[1]["content"] == "A1"
        assert agent.conversation_history[2]["content"] == "Q2"

    def test_agent_context_accumulation(self):
        """Test agent accumulates context."""
        agent = SimpleAgent(
            name="context-accumulator",
            description="test",
        )
        
        # Accumulate context over time
        agent.gather_context({"phase": 1})
        agent.context["status"] = "running"
        agent.context["results"] = []
        
        result = agent.run("Update")
        
        assert result["context"]["phase"] == 1
        assert result["context"]["status"] == "running"
        assert isinstance(result["context"]["results"], list)

    def test_agent_output_formatting_integration(self):
        """Test output formatting in agent context."""
        agent = SimpleAgent(
            name="formatter",
            description="test",
        )
        
        content = "# Test Header\n\nTest content"
        
        # Format as markdown
        markdown = agent.format_output(content, format_type="markdown")
        assert "# Test Header" in markdown
        
        # Format as JSON
        json_output = agent.format_output(content, format_type="json")
        import json
        parsed = json.loads(json_output)
        assert parsed["content"] == content

    def test_multiple_agents_independent(self):
        """Test multiple agents operate independently."""
        agent1 = SimpleAgent("agent1", "test")
        agent2 = SimpleAgent("agent2", "test")
        
        agent1.gather_context({"id": 1})
        agent2.gather_context({"id": 2})
        
        assert agent1.context["id"] == 1
        assert agent2.context["id"] == 2

    def test_agent_research_integration(self):
        """Test agent using research capability."""
        agent = SimpleAgent(
            name="researcher",
            description="test",
        )
        
        # Use research
        context = agent.research.analyze_structure(".")
        assert "files" in context or "error" in context

    def test_agent_interview_integration(self):
        """Test agent using interview capability."""
        agent = SimpleAgent(
            name="interviewer",
            description="test",
        )
        
        # Use interview
        with patch('rich.console.Console.print'):
            agent.interview.start_interview(
                "Initial question",
                topic="test topic"
            )
        
        assert agent.interview.context["topic"] == "test topic"

    def test_agent_documentation_integration(self):
        """Test agent using documentation capability."""
        agent = SimpleAgent(
            name="documenter",
            description="test",
        )
        
        template = agent.documentation.create_template(
            title="Test Template",
            sections={"Intro": "intro text"},
            metadata={"version": "1.0"},
        )
        
        assert "# Test Template" in template
        assert "## Intro" in template
        assert "version: 1.0" in template

    def test_agent_error_handling(self):
        """Test agent error handling."""
        agent = SimpleAgent(
            name="error-handler",
            description="test",
        )
        
        # Try to load nonexistent file
        result = agent.research.gather_file_context("/nonexistent/file.txt")
        
        assert "not found" in result.lower() or "error" in result.lower()

    def test_agent_state_isolation(self):
        """Test agent state is isolated."""
        agent1 = SimpleAgent("agent1", "test")
        agent2 = SimpleAgent("agent2", "test")
        
        # Modify agent1
        agent1.conversation_history.append({"role": "user", "content": "Test"})
        agent1.context["data"] = "test"
        
        # agent2 should be unaffected
        assert len(agent2.conversation_history) == 0
        assert "data" not in agent2.context

    def test_agent_capability_access(self):
        """Test agent can access all capabilities."""
        agent = SimpleAgent("test", "test")
        
        # Verify all capabilities exist
        assert hasattr(agent, 'llm')
        assert hasattr(agent, 'research')
        assert hasattr(agent, 'interview')
        assert hasattr(agent, 'documentation')
        
        assert agent.llm is not None
        assert agent.research is not None
        assert agent.interview is not None
        assert agent.documentation is not None

    def test_agent_framework_extensibility(self):
        """Test that agents can extend the framework."""
        
        class CustomAgent(BaseAgent):
            def __init__(self):
                super().__init__("custom", "test")
                self.custom_data = "custom value"
            
            def run(self, user_input: str) -> dict:
                return {"custom": self.custom_data}
        
        agent = CustomAgent()
        result = agent.run("test")
        
        assert result["custom"] == "custom value"
