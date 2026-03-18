# Creating Greybeard Agents

This guide shows you how to build new agents on top of the Greybeard framework.

## Quick Start

### 1. Create Your Agent File

```bash
# Create a new agent in greybeard/agents/your_agent_name/
mkdir -p greybeard/agents/your_agent_name
touch greybeard/agents/your_agent_name/__init__.py
touch greybeard/agents/your_agent_name/agent.py
```

### 2. Implement Your Agent

```python
# greybeard/agents/your_agent_name/agent.py

from greybeard.common import BaseAgent

class YourAgent(BaseAgent):
    """Brief description of what your agent does."""
    
    def __init__(self):
        super().__init__(
            name="your-agent-name",
            description="What this agent helps with",
        )
    
    def run(self, user_input: str) -> dict:
        """Execute the agent.
        
        Args:
            user_input: Initial user question or input
            
        Returns:
            Dictionary with results
        """
        # Your implementation here
        return {
            "result": "something",
            "analysis": "details",
        }
```

### 3. Write Tests

```python
# tests/test_your_agent.py

import pytest
from greybeard.agents.your_agent_name.agent import YourAgent

def test_agent_initialization():
    agent = YourAgent()
    assert agent.name == "your-agent-name"

def test_agent_run():
    agent = YourAgent()
    result = agent.run("test input")
    assert "result" in result
```

## Available Capabilities

All agents inherit these capabilities from `BaseAgent`:

### LLM Capability

Call the configured language model:

```python
def run(self, user_input: str) -> dict:
    response = self.llm.call(
        system="You are an expert...",
        messages=[
            {"role": "user", "content": user_input}
        ],
        temperature=0.7,
    )
    return {"response": response}
```

**Methods:**
- `call(system, messages, temperature, model_override)` - Synchronous call
- `stream_call(...)` - Streaming call
- `get_config()` - Get current configuration
- `reload_config()` - Reload from disk

### Research Capability

Gather context and information:

```python
def run(self, user_input: str) -> dict:
    # Analyze directory structure
    structure = self.research.analyze_structure("/path/to/dir")
    
    # Get file context
    content = self.research.gather_file_context("/path/to/file.txt")
    
    # Get git repository info
    git_info = self.research.get_git_context(".")
    
    # Load JSON data
    data = self.research.load_json_data("/path/to/data.json")
    
    # Research a topic
    summary = self.research.research_topic("kubernetes")
    
    return {"structure": structure, "git": git_info}
```

**Methods:**
- `research_topic(topic, sources)` - Research a topic
- `gather_file_context(filepath)` - Read file content
- `analyze_structure(dirpath)` - Analyze directory structure
- `get_git_context(repo_path)` - Get git repository info
- `load_json_data(filepath)` - Load and parse JSON

### Interview Capability

Conduct multi-turn conversations:

```python
def run(self, user_input: str) -> dict:
    # Start interview session
    self.interview.start_interview(
        opening_question="Tell me about your decision",
        topic="career decision"
    )
    
    # Ask question
    response = self.interview.ask_question("Why are you considering this?")
    
    # Get accumulated context
    context = self.interview.get_context()
    
    # Get conversation history
    history = self.interview.get_history()
    
    # Summarize
    summary = self.interview.summarize_interview()
    
    return {"summary": summary, "history": history}
```

**Methods:**
- `start_interview(opening_question, topic)` - Begin interview
- `ask_question(question)` - Ask user a question
- `ask_followup(response, system, llm_call)` - Generate AI followup
- `get_history()` - Get conversation history
- `get_context()` - Get accumulated context
- `add_context(key, value)` - Add context value
- `summarize_interview()` - Get conversation summary
- `clear()` - Clear history and context

### Documentation Capability

Format and save outputs:

```python
def run(self, user_input: str) -> dict:
    # Format output
    markdown = self.documentation.format(
        content="# Header\n\nContent",
        format_type="markdown",
        metadata={"version": "1.0"}
    )
    
    # Create template
    template = self.documentation.create_template(
        title="Decision Document",
        sections={
            "Context": "Explain context",
            "Decision": "What you decided",
        },
        metadata={"date": "2026-03-18"}
    )
    
    # Save files
    self.documentation.save_markdown(markdown, "/path/to/output.md")
    self.documentation.save_json({"data": "value"}, "/path/to/output.json")
    
    return {"output": markdown}
```

**Methods:**
- `format(content, format_type, metadata)` - Format content (markdown/json/yaml)
- `create_template(title, sections, metadata)` - Create template
- `save_markdown(content, filepath)` - Save markdown file
- `save_json(data, filepath)` - Save JSON file
- `save_yaml(data, filepath)` - Save YAML file

## Multi-Turn Conversation

For agents that need interactive conversations:

```python
def run(self, user_input: str) -> dict:
    # Run multi-turn conversation
    result = self.multi_turn_conversation(
        initial_question=user_input,
        max_turns=10,
        expected_completion_fn=self._is_conversation_complete,
    )
    
    return {"result": result, "history": self.conversation_history}

def _is_conversation_complete(self, response: str) -> bool:
    """Check if conversation is complete."""
    # Return True when conversation should end
    return "final answer" in response.lower()
```

**Parameters:**
- `initial_question` (str) - The opening question
- `max_turns` (int) - Maximum conversation turns (default 10)
- `expected_completion_fn` (callable) - Function to check if done

## State Management

Agents maintain state across runs:

```python
def run(self, user_input: str) -> dict:
    # Access conversation history
    history = self.conversation_history
    # [{"role": "user", "content": "..."}, ...]
    
    # Access accumulated context
    context = self.context
    # {"key": "value", ...}
    
    # Modify context
    self.context["analysis_result"] = "something"
    
    # Save conversation
    self.save_conversation("/path/to/conversation.json")
    
    return {"result": "done"}
```

## Real-World Example: Architecture Decision Agent

```python
from greybeard.common import BaseAgent

class ADRAgent(BaseAgent):
    """Help teams write Architecture Decision Records."""
    
    def __init__(self):
        super().__init__(
            name="architecture",
            description="Document architectural decisions properly",
        )
    
    def run(self, decision_question: str) -> dict:
        # Interview about decision
        self.interview.start_interview(
            opening_question=f"Help me document: {decision_question}",
            topic="architecture decision"
        )
        
        # Gather context
        alternatives = self.research.research_topic(decision_question)
        
        # Multi-turn conversation for ADR generation
        adr_draft = self.multi_turn_conversation(
            initial_question=decision_question,
            expected_completion_fn=self._is_adr_complete
        )
        
        # Format as markdown ADR
        adr_markdown = self.documentation.create_template(
            title=f"ADR: {decision_question}",
            sections={
                "Context": "Why are we making this decision now?",
                "Decision": "What are we going to do?",
                "Consequences": "What are the good and bad outcomes?",
                "Alternatives": "What else did we consider?",
            },
            metadata={"status": "Proposed", "date": str(datetime.now())}
        )
        
        return {
            "adr": adr_markdown,
            "alternatives": alternatives,
            "conversation": self.conversation_history,
        }
    
    def _is_adr_complete(self, response: str) -> bool:
        """Check if ADR draft is complete."""
        return all(
            section in response.lower()
            for section in ["context", "decision", "consequences"]
        )
```

## Testing Your Agent

```python
import pytest
from unittest.mock import Mock, patch
from your_agent import YourAgent

class TestYourAgent:
    
    def test_initialization(self):
        agent = YourAgent()
        assert agent.name == "your-agent-name"
    
    def test_run_basic(self):
        agent = YourAgent()
        result = agent.run("test input")
        assert isinstance(result, dict)
    
    def test_with_mocked_llm(self):
        agent = YourAgent()
        agent.llm.call = Mock(return_value="Mocked response")
        
        result = agent.run("test")
        
        assert "Mocked response" in result.get("result", "")
    
    def test_conversation_flow(self):
        agent = YourAgent()
        
        with patch('rich.prompt.Prompt.ask') as mock_ask:
            mock_ask.side_effect = ["Answer 1", "Answer 2"]
            
            agent.interview.start_interview("Opening?", "test")
            agent.interview.ask_question("Q1?")
            agent.interview.ask_question("Q2?")
        
        assert len(agent.interview.get_history()) == 2
```

## Publishing Your Agent

To share your agent:

1. **Create a PR** with your agent implementation
2. **Include tests** (aim for 80%+ coverage)
3. **Add documentation** explaining what it does
4. **Update CONTRIBUTING.md** if you're adding a new agent

Example PR title:
```
feat: add [agent-name] agent

Adds [AgentName] agent for [purpose].

Includes:
- Agent implementation
- Comprehensive tests
- Documentation with examples
- Integration examples
```

## Best Practices

1. **Keep agents focused** - Each agent solves one problem well
2. **Use all capabilities** - Leverage research, interview, docs
3. **Test thoroughly** - Aim for 80%+ coverage
4. **Document well** - Include docstrings and examples
5. **Handle errors gracefully** - Use try/except, provide feedback
6. **Accumulate context** - Use `self.context` to build knowledge
7. **Track history** - `self.conversation_history` is your audit trail

## Common Patterns

### Pattern 1: Interview → Analysis → Output

```python
def run(self, user_input):
    # Interview user
    self.interview.start_interview(user_input, "analysis")
    context = self.interview.ask_question("Tell me more")
    
    # Analyze with LLM
    analysis = self.llm.call(
        system="Analyze this:",
        messages=[{"role": "user", "content": context}]
    )
    
    # Format and return
    output = self.documentation.format(analysis, "markdown")
    return {"analysis": output}
```

### Pattern 2: Research → Synthesis → Documentation

```python
def run(self, user_input):
    # Research the topic
    git_info = self.research.get_git_context(".")
    structure = self.research.analyze_structure(".")
    
    # Synthesize with LLM
    synthesis = self.llm.call(
        system="Summarize this infrastructure",
        messages=[{
            "role": "user",
            "content": f"Git: {git_info}\nStructure: {structure}"
        }]
    )
    
    # Document
    doc = self.documentation.create_template(
        title="Infrastructure Summary",
        sections={"Analysis": synthesis}
    )
    
    return {"documentation": doc}
```

### Pattern 3: Multi-Turn Conversation

```python
def run(self, user_input):
    # Interactive conversation
    result = self.multi_turn_conversation(
        initial_question=user_input,
        expected_completion_fn=self._done,
    )
    
    # Save results
    self.documentation.save_markdown(result, "output.md")
    
    return {
        "result": result,
        "turns": len(self.conversation_history)
    }

def _done(self, response):
    return "done" in response.lower()
```

## Questions?

Refer to:
- `greybeard/common/agent.py` - BaseAgent implementation
- `examples/` - Real agent examples
- `tests/` - Test patterns and fixtures
