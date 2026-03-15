"""CLI entry point for greybeard."""

from __future__ import annotations

import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .analyzer import run_review
from .config import (
    CONFIG_FILE,
    KNOWN_BACKENDS,
    GreybeardConfig,
)
from .models import ReviewRequest
from .packs import (
    install_pack_source,
    list_builtin_packs,
    list_installed_packs,
    load_pack,
    remove_pack_source,
)

load_dotenv()

console = Console()

MODES = ["review", "mentor", "coach", "self-check"]
AUDIENCES = ["team", "peers", "leadership", "customer"]


def _print_header(mode: str, pack_name: str, backend: str, model: str) -> None:
    console.print(
        Panel(
            f"[bold]Mode:[/bold] {mode}  |  "
            f"[bold]Pack:[/bold] {pack_name}  |  "
            f"[bold]LLM:[/bold] {backend}/{model}",
            title="[bold purple]🧙 greybeard[/bold purple]",
            border_style="purple",
        )
    )


def _read_stdin_if_available() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _save_output(text: str, path: str) -> None:
    import pathlib

    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    console.print(f"\n[dim]Review saved to {path}[/dim]")


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="greybeard")
def cli() -> None:
    """🧙 greybeard — Staff-level review & decision assistant.

    \b
    Quick start:
      greybeard init                              # configure LLM backend
      git diff main | greybeard analyze           # review a diff
      greybeard self-check --context "my plan"    # review your own thinking
      greybeard packs                             # list content packs
      greybeard mcp                               # start MCP server

    \b
    Install community packs:
      greybeard pack install github:owner/repo
    """


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--mode",
    "-m",
    type=click.Choice(MODES),
    default=None,
    help="Review mode (default from config, usually 'review').",
)
@click.option("--pack", "-p", default=None, help="Content pack name or path (default from config).")
@click.option(
    "--repo",
    "-r",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Path to a repository for context.",
)
@click.option("--context", "-c", default="", help="Additional context notes.")
@click.option("--model", default=None, help="Override LLM model.")
@click.option(
    "--audience",
    "-a",
    type=click.Choice(AUDIENCES),
    default=None,
    help="Audience (for coach mode).",
)
@click.option("--output", "-o", default=None, help="Save review to a markdown file.")
def analyze(mode, pack, repo, context, model, audience, output) -> None:
    """Analyze a decision, diff, or document.

    \b
    Examples:
      git diff main | greybeard analyze
      git diff main | greybeard analyze --mode mentor --pack oncall-future-you
      cat design-doc.md | greybeard analyze --output review.md
      greybeard analyze --repo . --context "mid-sprint auth migration"
    """
    cfg = GreybeardConfig.load()
    mode = mode or cfg.default_mode
    pack_name = pack or cfg.default_pack

    try:
        content_pack = load_pack(pack_name)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    input_text = _read_stdin_if_available()

    if not input_text and not repo and not context:
        console.print(
            "[yellow]No input provided.[/yellow] Pipe in a diff, pass --repo, or use --context."
        )
        console.print("Run [bold]greybeard analyze --help[/bold] for usage.")
        sys.exit(1)

    _print_header(mode, content_pack.name, cfg.llm.backend, model or cfg.llm.resolved_model())

    request = ReviewRequest(
        mode=mode,  # type: ignore[arg-type]
        pack=content_pack,
        input_text=input_text,
        context_notes=context,
        repo_path=repo,
        audience=audience,  # type: ignore[arg-type]
    )

    result = run_review(request, config=cfg, model_override=model, stream=True)
    if output:
        _save_output(result, output)


# ---------------------------------------------------------------------------
# self-check
# ---------------------------------------------------------------------------


@cli.command("self-check")
@click.option(
    "--context", "-c", required=True, help="The decision or proposal you want to self-check."
)
@click.option("--pack", "-p", default=None, help="Content pack name or path.")
@click.option("--model", default=None, help="Override LLM model.")
@click.option("--output", "-o", default=None, help="Save review to a markdown file.")
def self_check(context, pack, model, output) -> None:
    """Review your own decision before sharing it.

    \b
    Example:
      greybeard self-check --context "We're adding a DB table per tenant"
    """
    cfg = GreybeardConfig.load()
    pack_name = pack or cfg.default_pack

    try:
        content_pack = load_pack(pack_name)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    input_text = _read_stdin_if_available()
    resolved = model or cfg.llm.resolved_model()
    _print_header("self-check", content_pack.name, cfg.llm.backend, resolved)

    request = ReviewRequest(
        mode="self-check",
        pack=content_pack,
        input_text=input_text,
        context_notes=context,
    )

    result = run_review(request, config=cfg, model_override=model, stream=True)
    if output:
        _save_output(result, output)


# ---------------------------------------------------------------------------
# coach
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--audience",
    "-a",
    type=click.Choice(AUDIENCES),
    required=True,
    help="Who you're communicating with.",
)
@click.option("--context", "-c", default="", help="The concern or decision to communicate.")
@click.option(
    "--pack", "-p", default="mentor-mode", show_default=True, help="Content pack name or path."
)
@click.option("--model", default=None, help="Override LLM model.")
@click.option("--output", "-o", default=None, help="Save to a markdown file.")
def coach(audience, context, pack, model, output) -> None:
    """Get help communicating a concern or decision constructively.

    \b
    Examples:
      greybeard coach --audience team --context "I think we're shipping too fast"
      cat concern.md | greybeard coach --audience leadership
    """
    cfg = GreybeardConfig.load()
    try:
        content_pack = load_pack(pack)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    input_text = _read_stdin_if_available()

    if not input_text and not context:
        console.print("[yellow]No context provided.[/yellow] Use --context or pipe in text.")
        sys.exit(1)

    _print_header("coach", content_pack.name, cfg.llm.backend, model or cfg.llm.resolved_model())

    request = ReviewRequest(
        mode="coach",
        pack=content_pack,
        input_text=input_text,
        context_notes=context,
        audience=audience,  # type: ignore[arg-type]
    )

    result = run_review(request, config=cfg, model_override=model, stream=True)
    if output:
        _save_output(result, output)


# ---------------------------------------------------------------------------
# packs (list)
# ---------------------------------------------------------------------------


@cli.command()
def packs() -> None:
    """List all available content packs (built-in and installed)."""
    console.print("\n[bold]Built-in content packs:[/bold]\n")
    for name in list_builtin_packs():
        try:
            pack = load_pack(name)
            console.print(f"  [bold purple]{name}[/bold purple]")
            console.print(f"    Perspective: {pack.perspective[:80]}")
            console.print(f"    Tone: {pack.tone}")
            if pack.description:
                console.print(f"    {pack.description}")
            console.print()
        except FileNotFoundError:
            console.print(f"  [dim]{name}[/dim] (not found)")

    installed = list_installed_packs()
    if installed:
        console.print("[bold]Installed packs (remote):[/bold]\n")
        for p in installed:
            console.print(f"  [bold green]{p['name']}[/bold green] [dim]({p['source']})[/dim]")
            if p["description"]:
                console.print(f"    {p['description']}")
            console.print()

    console.print("[dim]Install more: greybeard pack install github:owner/repo[/dim]\n")


# ---------------------------------------------------------------------------
# pack (management subgroup)
# ---------------------------------------------------------------------------


@cli.group()
def pack() -> None:
    """Manage content packs (install, remove, list)."""


@pack.command("install")
@click.argument("source")
@click.option("--force", is_flag=True, help="Re-download even if already cached.")
def pack_install(source: str, force: bool) -> None:
    """Install packs from a remote source.

    \b
    Examples:
      greybeard pack install github:owner/repo
      greybeard pack install github:owner/repo/packs/my-pack.yaml
      greybeard pack install https://example.com/my-pack.yaml
    """
    console.print(f"[bold]Installing packs from:[/bold] {source}\n")
    try:
        installed = install_pack_source(source, force=force)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    for p in installed:
        console.print(f"  ✓ [green]{p.name}[/green] — {p.description or p.perspective[:60]}")

    console.print(
        f"\n[bold green]{len(installed)} pack(s) installed.[/bold green] "
        "Use [bold]greybeard packs[/bold] to see all available packs."
    )


@pack.command("remove")
@click.argument("source_slug")
def pack_remove(source_slug: str) -> None:
    """Remove installed packs from a source.

    SOURCE_SLUG is the directory name under ~/.greybeard/packs/
    (visible in `greybeard packs` output).
    """
    try:
        count = remove_pack_source(source_slug)
        console.print(f"[green]Removed {count} pack(s) from {source_slug}[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@pack.command("list")
def pack_list() -> None:
    """List all installed (remote) packs."""
    installed = list_installed_packs()
    if not installed:
        console.print("[dim]No remote packs installed.[/dim]")
        console.print("Install with: [bold]greybeard pack install github:owner/repo[/bold]")
        return

    table = Table(title="Installed Packs", show_header=True, header_style="bold purple")
    table.add_column("Name", style="green")
    table.add_column("Source", style="dim")
    table.add_column("Description")
    for p in installed:
        table.add_row(p["name"], p["source"], p["description"] or "—")
    console.print(table)


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


@cli.group()
def config() -> None:
    """View and manage greybeard configuration."""


@config.command("show")
def config_show() -> None:
    """Show current configuration."""
    cfg = GreybeardConfig.load()
    d = cfg.to_display_dict()

    table = Table(title="greybeard config", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value", style="green")
    for k, v in d.items():
        if isinstance(v, list):
            table.add_row(k, ", ".join(v) if v else "[dim](none)[/dim]")
        else:
            table.add_row(k, str(v))
    console.print(table)
    console.print(f"\n[dim]Config file: {CONFIG_FILE}[/dim]")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a config value.

    \b
    Keys:
      llm.backend      openai | anthropic | ollama | lmstudio
      llm.model        e.g. gpt-4o, claude-3-5-sonnet-20241022, llama3.2
      llm.base_url     e.g. http://localhost:11434/v1
      llm.api_key_env  e.g. OPENAI_API_KEY
      default_pack     e.g. staff-core
      default_mode     review | mentor | coach | self-check
    """
    cfg = GreybeardConfig.load()
    if key == "llm.backend":
        if value not in KNOWN_BACKENDS:
            console.print(f"[red]Unknown backend:[/red] {value}")
            console.print(f"Known backends: {', '.join(KNOWN_BACKENDS)}")
            sys.exit(1)
        cfg.llm.backend = value
    elif key == "llm.model":
        cfg.llm.model = value
    elif key == "llm.base_url":
        cfg.llm.base_url = value
    elif key == "llm.api_key_env":
        cfg.llm.api_key_env = value
    elif key == "default_pack":
        cfg.default_pack = value
    elif key == "default_mode":
        if value not in MODES:
            console.print(f"[red]Unknown mode:[/red] {value}. Choose from: {', '.join(MODES)}")
            sys.exit(1)
        cfg.default_mode = value
    else:
        console.print(
            f"[red]Unknown key:[/red] {key}. Run [bold]greybeard config set --help[/bold]"
        )
        sys.exit(1)

    cfg.save()
    console.print(f"[green]✓[/green] {key} = {value}")


# ---------------------------------------------------------------------------
# init (interactive setup wizard)
# ---------------------------------------------------------------------------


@cli.command()
def init() -> None:
    """Interactive setup wizard.

    Configures your LLM backend and saves to ~/.greybeard/config.yaml.
    """
    console.print(
        Panel(
            "[bold]Welcome to greybeard.[/bold]\n\nLet's configure your LLM backend.",
            title="[bold purple]🧙 greybeard init[/bold purple]",
            border_style="purple",
        )
    )

    cfg = GreybeardConfig.load()

    console.print("\n[bold]Available LLM backends:[/bold]")
    backend_info = {
        "openai": "OpenAI API (gpt-4o, gpt-4o-mini, etc.) — needs OPENAI_API_KEY",
        "anthropic": "Anthropic API (claude-3-5-sonnet, etc.) — needs ANTHROPIC_API_KEY",
        "ollama": "Ollama (local, free) — run `ollama serve` first",
        "lmstudio": "LM Studio (local, free) — run LM Studio server first",
    }
    for i, (name, desc) in enumerate(backend_info.items(), 1):
        marker = "[green]●[/green]" if name == cfg.llm.backend else " "
        console.print(f"  {marker} {i}. [bold]{name}[/bold] — {desc}")

    console.print()
    backend_choice = click.prompt(
        "Choose backend (1-4)",
        default=str(list(backend_info.keys()).index(cfg.llm.backend) + 1),
    )
    try:
        backend = list(backend_info.keys())[int(backend_choice) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid choice.[/red]")
        sys.exit(1)

    cfg.llm.backend = backend

    from .config import DEFAULT_API_KEY_ENVS, DEFAULT_MODELS

    default_model = DEFAULT_MODELS.get(backend, "")
    model = click.prompt("Model", default=cfg.llm.model or default_model)
    cfg.llm.model = model if model != default_model else ""

    if backend in ("ollama", "lmstudio"):
        from .config import DEFAULT_BASE_URLS

        default_url = DEFAULT_BASE_URLS.get(backend, "")
        base_url = click.prompt("Base URL", default=cfg.llm.base_url or default_url)
        cfg.llm.base_url = base_url if base_url != default_url else ""
    else:
        env_var = DEFAULT_API_KEY_ENVS.get(backend, "")
        if env_var:
            console.print(
                f"\n[dim]Make sure {env_var} is set in your environment or .env file.[/dim]"
            )

    default_pack = click.prompt(
        "\nDefault content pack",
        default=cfg.default_pack,
        type=click.Choice(list_builtin_packs()),
    )
    cfg.default_pack = default_pack

    cfg.save()

    console.print(
        f"\n[bold green]✓ Config saved to {CONFIG_FILE}[/bold green]\n"
        f"  Backend: [bold]{cfg.llm.backend}[/bold]\n"
        f"  Model:   [bold]{cfg.llm.resolved_model()}[/bold]\n"
        f"  Pack:    [bold]{cfg.default_pack}[/bold]\n\n"
        "Run [bold]greybeard analyze --help[/bold] to get started."
    )


# ---------------------------------------------------------------------------
# mcp (MCP server)
# ---------------------------------------------------------------------------


@cli.command()
def mcp() -> None:
    """Start a stdio MCP server for use with Claude Desktop, Cursor, Zed, etc.

    \b
    Add to Claude Desktop config:
      {
        "mcpServers": {
          "greybeard": {
            "command": "greybeard",
            "args": ["mcp"]
          }
        }
      }

    \b
    Config file location:
      macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
      Windows: %APPDATA%\\Claude\\claude_desktop_config.json
    """
    from .mcp_server import serve

    serve()
