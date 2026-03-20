"""Base agent class for all Greybeard agents.

All agents inherit from BaseAgent and implement the run() method.
Provides shared capabilities like multi-turn conversation, research, and documentation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from rich.console import Console

from .document import DocumentationGenerator
from .interview import InterviewCapability
from .llm_wrapper import LLMWrapper
from .research import ResearchCapability

console = Console()


class BaseAgent(ABC):
    """Base class for all Greybeard agents.

    Provides:
    - Multi-turn conversation capabilities
    - Research and context gathering
    - Structured output generation
    - Conversation history management
    """

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str | None = None,
    ):
        """Initialize base agent.

        Args:
            name: Agent name (e.g., "reviews", "architecture")
            description: Agent description
            system_prompt: Custom system prompt (optional)
        """
        self.name = name
        self.description = description
        self.system_prompt = system_prompt or self._default_system_prompt()

        # Capabilities
        self.llm = LLMWrapper()
        self.research = ResearchCapability()
        self.interview = InterviewCapability()
        self.documentation = DocumentationGenerator()

        # State
        self.conversation_history: list[dict[str, str]] = []
        self.context: dict[str, Any] = {}

    def _default_system_prompt(self) -> str:
        """Default system prompt if none is provided."""
        return f"""You are a helpful AI assistant for {self.name}.

Your role: {self.description}

Be thoughtful, thorough, and ask clarifying questions when needed.
Format your responses in clear, structured markdown."""

    @abstractmethod
    def run(self, user_input: str) -> dict[str, Any]:
        """Execute the agent.

        This method must be implemented by subclasses.

        Args:
            user_input: The user's input or question

        Returns:
            Dictionary with agent results
        """
        pass

    def multi_turn_conversation(
        self,
        initial_question: str,
        max_turns: int = 10,
        expected_completion_fn: Callable[[str], bool] | None = None,
    ) -> str:
        """Run a multi-turn conversation.

        Args:
            initial_question: The initial question to ask
            max_turns: Maximum number of conversation turns
            expected_completion_fn: Optional function to check if conversation is complete

        Returns:
            Final conversation result
        """
        self.conversation_history = [{"role": "user", "content": initial_question}]

        console.print(f"\n[bold cyan]{self.name}[/bold cyan]: Processing...")

        for turn in range(max_turns):
            # Get LLM response
            response = self.llm.call(
                system=self.system_prompt,
                messages=self.conversation_history,
                temperature=0.7,
            )

            assistant_message = response.strip()
            self.conversation_history.append({"role": "assistant", "content": assistant_message})

            # Check if conversation is complete
            if expected_completion_fn and expected_completion_fn(assistant_message):
                return assistant_message

            # For final turns, break to avoid infinite loop
            if turn == max_turns - 1:
                return assistant_message

            # Get next user input
            user_input = input("\n[bold]You:[/bold] ").strip()
            if not user_input:
                return assistant_message

            self.conversation_history.append({"role": "user", "content": user_input})

        return assistant_message

    def gather_context(self, context_sources: dict[str, str]) -> dict[str, Any]:
        """Gather context from multiple sources.

        Args:
            context_sources: Dictionary of context source names and values

        Returns:
            Analyzed context
        """
        self.context = context_sources
        return self.context

    def format_output(
        self,
        content: str,
        format_type: str = "markdown",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Format agent output.

        Args:
            content: The content to format
            format_type: Output format (markdown, json, yaml)
            metadata: Optional metadata to include

        Returns:
            Formatted output
        """
        return self.documentation.format(
            content=content,
            format_type=format_type,
            metadata=metadata or {},
        )

    def save_conversation(self, filepath: str) -> None:
        """Save conversation history to file.

        Args:
            filepath: Path to save conversation
        """
        self.documentation.save_json(
            {
                "agent": self.name,
                "conversation": self.conversation_history,
                "context": self.context,
            },
            filepath,
        )
