"""Interactive REPL mode for iterative multi-turn conversations with greybeard."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .analyzer import run_review
from .config import GreybeardConfig
from .models import ContentPack, ReviewRequest

console = Console()


class InteractiveSession:
    """Manages an interactive REPL-style review conversation.

    After the initial analysis, the user can:
    - Ask follow-up questions about specific aspects
    - Refine their findings with additional context
    - Iterate on risks and recommendations
    - Explore alternative approaches

    Conversation history is maintained for context continuity.
    """

    def __init__(
        self,
        mode: str,
        pack: ContentPack,
        config: GreybeardConfig,
        model_override: str | None = None,
    ) -> None:
        """Initialize an interactive session.

        Args:
            mode: Review mode (review, mentor, coach, self-check)
            pack: Content pack to use
            config: GreybeardConfig instance
            model_override: Optional LLM model override
        """
        self.mode = mode
        self.pack = pack
        self.config = config
        self.model = model_override or config.llm.resolved_model()
        self.conversation_history: list[dict[str, str]] = []
        self.initial_analysis: str | None = None

    def run_initial_analysis(
        self,
        input_text: str,
        context_notes: str = "",
        repo_path: str | None = None,
        audience: str | None = None,
    ) -> str:
        """Run the initial analysis and store it for reference.

        Args:
            input_text: The code/document to analyze
            context_notes: Additional context
            repo_path: Optional path to a repository
            audience: Optional audience (for coach mode)

        Returns:
            The initial analysis result
        """
        request = ReviewRequest(
            mode=self.mode,  # type: ignore[arg-type]
            pack=self.pack,
            input_text=input_text,
            context_notes=context_notes,
            repo_path=repo_path,
            audience=audience,  # type: ignore[arg-type]
        )

        # Always stream for interactive mode (nice UX)
        result = run_review(request, config=self.config, model_override=self.model, stream=True)
        self.initial_analysis = result
        self._add_to_history("assistant", result)

        return result

    def ask_followup(self, question: str) -> str:
        """Ask a follow-up question about the analysis.

        The question is asked in the context of:
        - The initial analysis
        - Previous questions and answers in this session

        Args:
            question: The follow-up question

        Returns:
            The LLM's response
        """
        if not self.initial_analysis:
            raise RuntimeError("No initial analysis. Call run_initial_analysis() first.")

        self._add_to_history("user", question)

        # Build context for the follow-up
        system_prompt = self._build_followup_system_prompt()
        user_message = self._build_followup_user_message(question)

        result = self._call_llm(system_prompt, user_message)
        self._add_to_history("assistant", result)

        return result

    def refine_analysis(self, additional_context: str) -> str:
        """Refine the analysis with additional context or clarification.

        This re-analyzes the original input with new context factored in.

        Args:
            additional_context: New context to incorporate

        Returns:
            The refined analysis
        """
        if not self.initial_analysis:
            raise RuntimeError("No initial analysis. Call run_initial_analysis() first.")

        self._add_to_history("user", f"Additional context: {additional_context}")

        system_prompt = self._build_followup_system_prompt()
        user_message = (
            f"With this additional context in mind:\n{additional_context}\n\n"
            f"Please refine your analysis, highlighting what changes and why."
        )

        result = self._call_llm(system_prompt, user_message)
        self._add_to_history("assistant", result)

        return result

    def explore_alternative(self, alternative: str) -> str:
        """Explore an alternative approach or decision.

        Args:
            alternative: Description of the alternative to explore

        Returns:
            Analysis of the alternative
        """
        if not self.initial_analysis:
            raise RuntimeError("No initial analysis. Call run_initial_analysis() first.")

        self._add_to_history("user", f"Alternative to explore: {alternative}")

        system_prompt = self._build_followup_system_prompt()
        user_message = (
            f"Now consider this alternative:\n{alternative}\n\n"
            f"How does this compare to your original analysis? "
            f"What are the trade-offs and implications?"
        )

        result = self._call_llm(system_prompt, user_message)
        self._add_to_history("assistant", result)

        return result

    def get_conversation_history(self) -> list[dict[str, str]]:
        """Get the full conversation history.

        Returns:
            List of conversation turns with role and content
        """
        return self.conversation_history.copy()

    def clear_conversation(self) -> None:
        """Clear conversation history (but keep initial analysis)."""
        self.conversation_history.clear()
        if self.initial_analysis:
            self._add_to_history("assistant", self.initial_analysis)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _add_to_history(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def _build_followup_system_prompt(self) -> str:
        """Build system prompt for follow-up questions."""
        lines = [
            "You are a staff-level review assistant engaged in an interactive session.",
            "You have provided an initial analysis. The user is now asking follow-up questions,",
            "seeking refinements, or exploring alternatives.",
            "",
            self.pack.to_system_prompt_fragment(),
            "",
            "Reference your initial analysis when answering follow-ups.",
            "Be concise but thorough. Build on previous context.",
        ]
        return "\n".join(lines)

    def _build_followup_user_message(self, question: str) -> str:
        """Build user message for follow-up, including conversation context."""
        lines: list[str] = [
            "## Initial Analysis\n",
            self.initial_analysis or "(No initial analysis available)",
            "\n## Conversation So Far\n",
        ]

        # Keep last 10 messages for context (avoid token bloat)
        recent = self.conversation_history[-10:]
        for msg in recent:
            role = "You" if msg["role"] == "assistant" else "User"
            lines.append(f"\n**{role}:**\n{msg['content']}")

        lines.append(f"\n## New Question\n{question}")

        return "\n".join(lines)

    def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """Call the LLM with the given prompts.

        Args:
            system_prompt: System prompt
            user_message: User message

        Returns:
            The LLM's response
        """
        if self.config.llm.backend == "anthropic":
            return self._call_anthropic(system_prompt, user_message)
        else:
            return self._call_openai_compat(system_prompt, user_message)

    def _call_openai_compat(self, system_prompt: str, user_message: str) -> str:
        """Call an OpenAI-compatible API."""
        try:
            from openai import OpenAI
        except ImportError:
            msg = "Error: openai package not installed. Run: uv pip install openai"
            print(msg, file=sys.stderr)
            sys.exit(1)

        api_key = self.config.llm.resolved_api_key()
        if not api_key and self.config.llm.backend not in ("ollama", "lmstudio"):
            env_var = self.config.llm.resolved_api_key_env()
            print(
                f"Error: {env_var} is not set.\nExport it or add it to a .env file.",
                file=sys.stderr,
            )
            sys.exit(1)

        kwargs: dict = {"api_key": api_key or "no-key-needed"}
        base_url = self.config.llm.resolved_base_url()
        if base_url:
            kwargs["base_url"] = base_url

        client = OpenAI(**kwargs)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # Stream response
        full_text = ""
        console.print()
        stream = client.chat.completions.create(model=self.model, messages=messages, stream=True)  # type: ignore[union-attr,arg-type,attr-defined]
        for chunk in stream:  # type: ignore[misc]
            delta = chunk.choices[0].delta.content or ""
            print(delta, end="", flush=True)
            full_text += delta
        console.print("\n")
        return full_text

    def _call_anthropic(self, system_prompt: str, user_message: str) -> str:
        """Call Anthropic API."""
        try:
            import anthropic
        except ImportError:
            print(
                "Error: anthropic package not installed.\nRun: uv pip install anthropic",
                file=sys.stderr,
            )
            sys.exit(1)

        api_key = self.config.llm.resolved_api_key()
        if not api_key:
            print(
                f"Error: {self.config.llm.resolved_api_key_env()} is not set.\n"
                f"Export it or run: greybeard init",
                file=sys.stderr,
            )
            sys.exit(1)

        client = anthropic.Anthropic(api_key=api_key)

        full_text = ""
        with client.messages.stream(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as s:
            for text in s.text_stream:
                print(text, end="", flush=True)
                full_text += text
        print()
        return full_text


def run_interactive_repl(
    mode: str,
    pack: ContentPack,
    config: GreybeardConfig,
    model_override: str | None = None,
    initial_input: str = "",
    initial_context: str = "",
) -> None:
    """Run an interactive REPL session for exploring and refining analyses.

    This is the main entry point for interactive mode. It:
    1. Runs the initial analysis
    2. Starts a REPL loop for follow-ups, refinements, and alternatives
    3. Handles user input and LLM responses interactively

    Args:
        mode: Review mode (review, mentor, coach, self-check)
        pack: Content pack to use
        config: GreybeardConfig instance
        model_override: Optional LLM model override
        initial_input: Initial input text (code, design doc, etc.)
        initial_context: Additional context for initial analysis
    """
    session = InteractiveSession(mode, pack, config, model_override)

    # Run initial analysis
    console.print("\n[bold cyan]Running initial analysis...[/bold cyan]\n")
    session.run_initial_analysis(initial_input, initial_context)

    # Interactive REPL loop
    console.print(
        Panel(
            "Interactive mode enabled. You can now:\n"
            "  • Ask follow-up questions about the analysis\n"
            "  • Refine the analysis with additional context\n"
            "  • Explore alternative approaches\n\n"
            "Type 'help' for commands or 'quit' to exit.",
            title="[bold green]Interactive Review Session[/bold green]",
            border_style="green",
        )
    )

    while True:
        try:
            command = Prompt.ask("\n[bold]>[/bold]").strip()

            if not command:
                continue

            if command.lower() == "quit" or command.lower() == "exit":
                console.print("[dim]Goodbye![/dim]")
                break

            if command.lower() == "help":
                _print_help()
                continue

            if command.lower() == "history":
                _print_conversation_history(session)
                continue

            if command.lower() == "reset":
                session.clear_conversation()
                console.print("[dim]Conversation history cleared.[/dim]")
                continue

            if command.lower().startswith("refine"):
                additional_context = command[6:].strip()
                if not additional_context:
                    console.print("[yellow]Usage: refine <additional context>[/yellow]")
                    continue
                console.print("\n[cyan]Refining analysis...[/cyan]\n")
                session.refine_analysis(additional_context)
                continue

            if command.lower().startswith("explore"):
                alternative = command[7:].strip()
                if not alternative:
                    console.print("[yellow]Usage: explore <alternative to explore>[/yellow]")
                    continue
                console.print("\n[cyan]Exploring alternative...[/cyan]\n")
                session.explore_alternative(alternative)
                continue

            # Default: treat as a follow-up question
            console.print("\n[cyan]Answering follow-up...[/cyan]\n")
            session.ask_followup(command)

        except KeyboardInterrupt:
            console.print("\n[dim]Session interrupted. Goodbye![/dim]")
            break
        except EOFError:
            console.print("\n[dim]End of input. Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def _print_help() -> None:
    """Print interactive mode help."""
    help_text = """
[bold]Interactive Commands[/bold]

[bold cyan]ask <question>[/bold cyan]
  Ask a follow-up question about the analysis.
  Example: ask What are the biggest risks here?

[bold cyan]refine <context>[/bold cyan]
  Refine the analysis with additional context.
  Example: refine We're planning a 6-month rollout

[bold cyan]explore <alternative>[/bold cyan]
  Explore an alternative approach.
  Example: explore What if we used event sourcing instead?

[bold cyan]history[/bold cyan]
  Show conversation history.

[bold cyan]reset[/bold cyan]
  Clear conversation history.

[bold cyan]help[/bold cyan]
  Show this help text.

[bold cyan]quit[/bold cyan] or [bold cyan]exit[/bold cyan]
  Exit the session.

[dim]Or just type any question directly![/dim]
    """
    console.print(help_text)


def _print_conversation_history(session: InteractiveSession) -> None:
    """Print formatted conversation history."""
    history = session.get_conversation_history()
    if not history:
        console.print("[dim]No conversation history yet.[/dim]")
        return

    console.print("\n[bold]Conversation History[/bold]\n")
    for i, msg in enumerate(history, 1):
        role = msg["role"].upper()
        content = msg["content"]

        # Truncate long responses for readability
        if len(content) > 500:
            content = content[:497] + "..."

        if msg["role"] == "user":
            console.print(f"[bold cyan]{role}[/bold cyan]\n{content}\n")
        else:
            console.print(f"[bold green]{role}[/bold green]\n{content}\n")
