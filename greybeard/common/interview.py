"""Multi-turn conversation and interview utilities.

Provides conversation loop logic, context building, and question generation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rich.console import Console
from rich.prompt import Prompt

console = Console()


class InterviewCapability:
    """Multi-turn interview and conversation management."""

    def __init__(self):
        """Initialize interview capability."""
        self.conversation_history: list[dict[str, str]] = []
        self.context: dict[str, Any] = {}

    def start_interview(
        self,
        opening_question: str,
        topic: str = "decision",
    ) -> None:
        """Start a new interview session.

        Args:
            opening_question: The initial question to ask
            topic: Topic of the interview (for context)
        """
        self.conversation_history = []
        self.context = {"topic": topic}
        console.print(f"\n[bold cyan]Interviewing about {topic}[/bold cyan]")
        console.print(f"[dim]{opening_question}[/dim]")

    def ask_question(self, question: str) -> str:
        """Ask a question and record the response.

        Args:
            question: Question to ask

        Returns:
            User's response
        """
        response = Prompt.ask(question)

        self.conversation_history.append({"role": "user", "content": response})

        return response

    def ask_followup(
        self,
        previous_response: str,
        system_prompt: str,
        llm_call: Callable[..., str],
    ) -> str:
        """Generate and ask an AI-powered followup question.

        Args:
            previous_response: User's previous response
            system_prompt: System prompt for question generation
            llm_call: Function to call LLM

        Returns:
            LLM-generated followup response
        """
        # Add user response to history
        self.conversation_history.append({"role": "user", "content": previous_response})

        # Generate followup from LLM
        response = llm_call(
            system=system_prompt,
            messages=self.conversation_history,
        )

        # Record in history
        self.conversation_history.append({"role": "assistant", "content": response})

        return response

    def get_history(self) -> list[dict[str, str]]:
        """Get conversation history.

        Returns:
            List of conversation messages
        """
        return self.conversation_history.copy()

    def get_context(self) -> dict[str, Any]:
        """Get accumulated interview context.

        Returns:
            Context dictionary
        """
        return self.context.copy()

    def add_context(self, key: str, value: Any) -> None:
        """Add a context value.

        Args:
            key: Context key
            value: Context value
        """
        self.context[key] = value

    def summarize_interview(self) -> str:
        """Summarize the interview in natural language.

        Returns:
            Summary of interview
        """
        summary_lines = [
            f"[bold]Interview Summary: {self.context.get('topic', 'decision')}[/bold]",
            "",
        ]

        for msg in self.conversation_history:
            role = "👤 You" if msg["role"] == "user" else "🤖 Assistant"
            summary_lines.append(f"{role}: {msg['content'][:100]}...")

        return "\n".join(summary_lines)

    def clear(self) -> None:
        """Clear interview history and context."""
        self.conversation_history = []
        self.context = {}
