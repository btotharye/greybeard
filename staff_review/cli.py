"""CLI entry point for staff-review."""

from __future__ import annotations

import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from .analyzer import DEFAULT_MODEL, run_review
from .models import ReviewRequest
from .packs import list_builtin_packs, load_pack

load_dotenv()

console = Console()

MODES = ["review", "mentor", "coach", "self-check"]
AUDIENCES = ["team", "peers", "leadership", "customer"]


def _print_header(mode: str, pack_name: str) -> None:
    console.print(
        Panel(
            f"[bold]Mode:[/bold] {mode}  |  [bold]Pack:[/bold] {pack_name}",
            title="[bold purple]Staff Review[/bold purple]",
            border_style="purple",
        )
    )


def _read_stdin_if_available() -> str:
    """Read stdin if it's not a TTY (i.e. something was piped in)."""
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


@click.group()
@click.version_option(package_name="staff-review")
def cli() -> None:
    """Staff Review & Decision Assistant.

    A CLI thinking tool that acts like a calm, experienced Staff / Principal engineer.
    Helps you review decisions, sanity-check systems, and communicate tradeoffs.

    \b
    Examples:
      git diff main | staff-review analyze --mode review
      staff-review self-check --context "We're migrating auth mid-sprint"
      staff-review coach --audience team --pack oncall-future-you
      staff-review packs
    """


@cli.command()
@click.option(
    "--mode", "-m",
    type=click.Choice(MODES),
    default="review",
    show_default=True,
    help="Review mode.",
)
@click.option(
    "--pack", "-p",
    default="staff-core",
    show_default=True,
    help="Content pack name (built-in) or path to a .yaml file.",
)
@click.option(
    "--repo", "-r",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Path to a repository for context (README, git log, structure).",
)
@click.option(
    "--context", "-c",
    default="",
    help="Additional context notes (e.g. 'this is part of a migration').",
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="OpenAI model to use.",
)
@click.option(
    "--audience", "-a",
    type=click.Choice(AUDIENCES),
    default=None,
    help="Audience for coach mode.",
)
def analyze(
    mode: str,
    pack: str,
    repo: str | None,
    context: str,
    model: str,
    audience: str | None,
) -> None:
    """Analyze a decision, diff, or document.

    Reads from stdin if input is piped, or uses --repo for repository context.

    \b
    Examples:
      git diff main | staff-review analyze --mode review --pack staff-core
      staff-review analyze --repo . --mode mentor --pack oncall-future-you
      cat design-doc.md | staff-review analyze --mode self-check
    """
    try:
        content_pack = load_pack(pack)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    input_text = _read_stdin_if_available()

    if not input_text and not repo and not context:
        console.print(
            "[yellow]No input provided.[/yellow] "
            "Pipe in a git diff, pass --repo, or use --context."
        )
        console.print("Run [bold]staff-review analyze --help[/bold] for usage.")
        sys.exit(1)

    _print_header(mode, content_pack.name)

    request = ReviewRequest(
        mode=mode,  # type: ignore[arg-type]
        pack=content_pack,
        input_text=input_text,
        context_notes=context,
        repo_path=repo,
        audience=audience,  # type: ignore[arg-type]
    )

    run_review(request, model=model, stream=True)


@cli.command("self-check")
@click.option(
    "--context", "-c",
    required=True,
    help="The decision or proposal you want to self-check.",
)
@click.option(
    "--pack", "-p",
    default="staff-core",
    show_default=True,
    help="Content pack name or path.",
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="OpenAI model to use.",
)
def self_check(context: str, pack: str, model: str) -> None:
    """Review your own decision before sharing it.

    \b
    Example:
      staff-review self-check --context "We're adding a new DB table for every tenant"
    """
    try:
        content_pack = load_pack(pack)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    input_text = _read_stdin_if_available()

    _print_header("self-check", content_pack.name)

    request = ReviewRequest(
        mode="self-check",
        pack=content_pack,
        input_text=input_text,
        context_notes=context,
    )

    run_review(request, model=model, stream=True)


@cli.command()
@click.option(
    "--audience", "-a",
    type=click.Choice(AUDIENCES),
    required=True,
    help="Who you're communicating with.",
)
@click.option(
    "--context", "-c",
    default="",
    help="The concern or decision you need to communicate.",
)
@click.option(
    "--pack", "-p",
    default="mentor-mode",
    show_default=True,
    help="Content pack name or path.",
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="OpenAI model to use.",
)
def coach(audience: str, context: str, pack: str, model: str) -> None:
    """Get help communicating a concern or decision constructively.

    \b
    Examples:
      staff-review coach --audience team --context "I think we're shipping too fast"
      cat my-concern.md | staff-review coach --audience leadership
    """
    try:
        content_pack = load_pack(pack)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    input_text = _read_stdin_if_available()

    if not input_text and not context:
        console.print(
            "[yellow]No context provided.[/yellow] "
            "Use --context or pipe in a description of the concern."
        )
        sys.exit(1)

    _print_header("coach", content_pack.name)

    request = ReviewRequest(
        mode="coach",
        pack=content_pack,
        input_text=input_text,
        context_notes=context,
        audience=audience,  # type: ignore[arg-type]
    )

    run_review(request, model=model, stream=True)


@cli.command()
def packs() -> None:
    """List all available content packs."""
    available = list_builtin_packs()
    console.print("\n[bold]Built-in content packs:[/bold]\n")
    for name in available:
        try:
            pack = load_pack(name)
            console.print(f"  [bold purple]{name}[/bold purple]")
            console.print(f"    Perspective: {pack.perspective}")
            console.print(f"    Tone: {pack.tone}")
            if pack.description:
                console.print(f"    {pack.description}")
            console.print()
        except FileNotFoundError:
            console.print(f"  [dim]{name}[/dim] (not found)")
    console.print("[dim]Pass a .yaml file path to --pack for custom packs.[/dim]\n")
