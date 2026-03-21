"""CLI entry point for greybeard."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .analyzer import run_review
from .cli_slo import slo_check
from .config import (
    CONFIG_FILE,
    KNOWN_BACKENDS,
    GreybeardConfig,
)
from .formatters import FORMAT_EXTENSIONS, SUPPORTED_FORMATS, ReviewMetadata, convert
from .history import (
    HISTORY_FILE,
    PATTERN_THRESHOLD,
    analyze_trends,
    load_history,
    save_decision,
)
from .interactive import run_interactive_repl
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


def _resolve_output_path(output: str | None, fmt: str) -> str | None:
    """If an output path is given without an extension, append the format extension."""
    if output is None:
        return None
    import pathlib

    p = pathlib.Path(output)
    if not p.suffix:
        return str(p.with_suffix(FORMAT_EXTENSIONS.get(fmt, ".txt")))
    return output


def _apply_format_and_save(
    result: str,
    fmt: str,
    output: str | None,
    meta: ReviewMetadata,
) -> None:
    """Convert the markdown result to the target format and optionally save it."""
    if fmt == "markdown":
        if output:
            _save_output(result, output)
        return

    # PDF format requires special handling
    if fmt == "pdf":
        if not output:
            console.print(
                "[red]Error:[/red] PDF export requires --output path (e.g., --output report.pdf)"
            )
            sys.exit(1)
        from greybeard.formatters import convert_to_pdf

        pdf_path = convert_to_pdf(result, meta, _resolve_output_path(output, fmt) or output)
        console.print(f"\n[dim]PDF report saved to {pdf_path}[/dim]")
        return

    converted = convert(result, fmt, meta)  # type: ignore[arg-type]

    if output:
        _save_output(converted, output)
    else:
        # Print converted output to stdout (non-markdown formats don't stream)
        console.print()
        print(converted)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="greybeard")
def cli() -> None:
    r"""🧙 greybeard — Staff-level review & decision assistant.

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
@click.option("--output", "-o", default=None, help="Save review to a file.")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(SUPPORTED_FORMATS),
    default="markdown",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--save-decision",
    "save_decision_name",
    default=None,
    metavar="NAME",
    help="Save this review to decision history (e.g. 'auth-migration-q1').",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Start interactive REPL after initial analysis.",
)
def analyze(
    mode, pack, repo, context, model, audience, output, fmt, save_decision_name, interactive
) -> None:
    r"""Analyze a decision, diff, or document.

    \b
    Examples:
      git diff main | greybeard analyze
      git diff main | greybeard analyze --interactive
      git diff main | greybeard analyze --mode mentor --pack oncall-future-you
      cat design-doc.md | greybeard analyze --output review.md
      cat design-doc.md | greybeard analyze --format json --output review.json
      cat design-doc.md | greybeard analyze --format html --output review.html
      cat design-doc.md | greybeard analyze --format jira
      greybeard analyze --repo . --context "mid-sprint auth migration"
      git diff main | greybeard analyze --save-decision "auth-migration-q1"
      git diff main | greybeard analyze --interactive --mode mentor
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

    resolved_model = model or cfg.llm.resolved_model()
    _print_header(mode, content_pack.name, cfg.llm.backend, resolved_model)

    # Interactive mode: start REPL session instead of single analysis
    if interactive:
        run_interactive_repl(
            mode=mode,
            pack=content_pack,
            config=cfg,
            model_override=model,
            initial_input=input_text,
            initial_context=context,
        )
        return

    request = ReviewRequest(
        mode=mode,  # type: ignore[arg-type]
        pack=content_pack,
        input_text=input_text,
        context_notes=context,
        repo_path=repo,
        audience=audience,  # type: ignore[arg-type]
    )

    # Non-markdown formats don't benefit from streaming (we need the full text to convert)
    should_stream = fmt == "markdown"
    result = run_review(request, config=cfg, model_override=model, stream=should_stream)

    meta = ReviewMetadata(
        mode=mode,
        pack_name=content_pack.name,
        backend=cfg.llm.backend,
        model=resolved_model,
    )
    output = _resolve_output_path(output, fmt)
    _apply_format_and_save(result, fmt, output, meta)

    if save_decision_name:
        path = save_decision(save_decision_name, result, content_pack.name, mode)
        console.print(f"\n[dim]Decision saved to history: {path}[/dim]")


# ---------------------------------------------------------------------------
# self-check
# ---------------------------------------------------------------------------


@cli.command("self-check")
@click.option(
    "--context", "-c", required=True, help="The decision or proposal you want to self-check."
)
@click.option("--pack", "-p", default=None, help="Content pack name or path.")
@click.option("--model", default=None, help="Override LLM model.")
@click.option("--output", "-o", default=None, help="Save review to a file.")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(SUPPORTED_FORMATS),
    default="markdown",
    show_default=True,
    help="Output format.",
)
def self_check(context, pack, model, output, fmt) -> None:
    r"""Review your own decision before sharing it.

    \b
    Examples:
      greybeard self-check --context "We're adding a DB table per tenant"
      greybeard self-check --context "migration plan" --format json --output check.json
    """
    cfg = GreybeardConfig.load()
    pack_name = pack or cfg.default_pack

    try:
        content_pack = load_pack(pack_name)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    input_text = _read_stdin_if_available()
    resolved_model = model or cfg.llm.resolved_model()
    _print_header("self-check", content_pack.name, cfg.llm.backend, resolved_model)

    request = ReviewRequest(
        mode="self-check",
        pack=content_pack,
        input_text=input_text,
        context_notes=context,
    )

    should_stream = fmt == "markdown"
    result = run_review(request, config=cfg, model_override=model, stream=should_stream)

    meta = ReviewMetadata(
        mode="self-check",
        pack_name=content_pack.name,
        backend=cfg.llm.backend,
        model=resolved_model,
    )
    output = _resolve_output_path(output, fmt)
    _apply_format_and_save(result, fmt, output, meta)


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
@click.option("--output", "-o", default=None, help="Save to a file.")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(SUPPORTED_FORMATS),
    default="markdown",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Start interactive REPL after initial analysis.",
)
def coach(audience, context, pack, model, output, fmt, interactive) -> None:
    r"""Get help communicating a concern or decision constructively.

    \b
    Examples:
      greybeard coach --audience team --context "I think we're shipping too fast"
      cat concern.md | greybeard coach --audience leadership
      greybeard coach --audience peers --context "concerns" --format jira
      greybeard coach --audience team --context "shipping too fast" --interactive
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

    resolved_model = model or cfg.llm.resolved_model()
    _print_header("coach", content_pack.name, cfg.llm.backend, resolved_model)

    # Interactive mode
    if interactive:
        run_interactive_repl(
            mode="coach",
            pack=content_pack,
            config=cfg,
            model_override=model,
            initial_input=input_text,
            initial_context=context,
        )
        return

    request = ReviewRequest(
        mode="coach",
        pack=content_pack,
        input_text=input_text,
        context_notes=context,
        audience=audience,  # type: ignore[arg-type]
    )

    should_stream = fmt == "markdown"
    result = run_review(request, config=cfg, model_override=model, stream=should_stream)

    meta = ReviewMetadata(
        mode="coach",
        pack_name=content_pack.name,
        backend=cfg.llm.backend,
        model=resolved_model,
    )
    output = _resolve_output_path(output, fmt)
    _apply_format_and_save(result, fmt, output, meta)


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
    r"""Install packs from a remote source.

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


@pack.command("new")
@click.option(
    "--output-dir",
    "-o",
    default=None,
    type=click.Path(file_okay=False),
    help="Directory to create the pack folder in (default: current directory).",
)
def pack_new(output_dir: str | None) -> None:
    r"""Interactively scaffold a new content pack.

    \b
    Runs a step-by-step wizard that collects:
      - Pack name, description, and reviewer persona
      - Focus areas and key heuristics
      - Example questions and communication style

    \b
    Generates a complete pack folder:
      <pack-name>/
        <pack-name>.yaml          — pack definition
        <PACK-NAME>-EXAMPLE.md    — example scenario
        README.md                 — quick-start guide

    \b
    Examples:
      greybeard pack new
      greybeard pack new --output-dir ~/.greybeard/my-packs
    """
    from .pack_wizard import run_pack_wizard

    run_pack_wizard(output_dir=output_dir)


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
    r"""Set a config value.

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
# trends
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--last",
    "days",
    default=30,
    show_default=True,
    metavar="DAYS",
    help="Analyse decisions from the last N days (0 = all time).",
)
@click.option("--pack", "-p", default=None, help="Filter by pack name.")
@click.option(
    "--llm",
    "use_llm",
    is_flag=True,
    default=False,
    help="Use the configured LLM to synthesize a narrative summary.",
)
@click.option("--model", default=None, help="Override LLM model (requires --llm).")
def trends(days: int, pack: str | None, use_llm: bool, model: str | None) -> None:
    r"""Show decision trends and recurring risk patterns.

    \b
    Examples:
      greybeard trends
      greybeard trends --last 7
      greybeard trends --pack staff-core
      greybeard trends --llm
    """
    history = load_history(days=days, pack=pack)

    if not history:
        filter_desc = []
        if days:
            filter_desc.append(f"last {days} days")
        if pack:
            filter_desc.append(f"pack={pack}")
        filters = f" ({', '.join(filter_desc)})" if filter_desc else ""
        console.print(f"[yellow]No decision history found{filters}.[/yellow]")
        console.print(
            "Use [bold]greybeard analyze --save-decision <name>[/bold] to start tracking decisions."
        )
        return

    result = analyze_trends(history)

    # ── Header ───────────────────────────────────────────────────────────────
    header_parts = [f"[bold]Decisions analysed:[/bold] {result['total_decisions']}"]
    dr = result["date_range"]
    if dr["from"] and dr["to"]:
        header_parts.append(f"[bold]Period:[/bold] {dr['from'][:10]} → {dr['to'][:10]}")
    if days:
        header_parts.append(f"[bold]Window:[/bold] last {days} days")
    if pack:
        header_parts.append(f"[bold]Pack filter:[/bold] {pack}")

    console.print(
        Panel(
            "  ".join(header_parts),
            title="[bold purple]🧙 greybeard trends[/bold purple]",
            border_style="purple",
        )
    )

    # ── Risk frequency table ──────────────────────────────────────────────────
    risk_freq = result["risk_frequency"]
    if risk_freq:
        table = Table(
            title="Risk Frequency",
            show_header=True,
            header_style="bold",
            title_style="bold purple",
        )
        table.add_column("Risk", style="white")
        table.add_column("Count", justify="right", style="cyan")
        table.add_column("", style="")  # flag column

        for risk, count in risk_freq[:20]:
            flag = "[bold red]⚠ recurring[/bold red]" if count >= PATTERN_THRESHOLD else ""
            table.add_row(risk, str(count), flag)

        console.print(table)
    else:
        console.print("[dim]No risks extracted yet — run more analyses.[/dim]")

    # ── Pack usage ────────────────────────────────────────────────────────────
    if result["most_used_packs"]:
        pack_table = Table(show_header=True, header_style="bold", title="Pack Usage")
        pack_table.add_column("Pack")
        pack_table.add_column("Uses", justify="right", style="cyan")
        for p, count in result["most_used_packs"]:
            pack_table.add_row(p, str(count))
        console.print(pack_table)

    # ── Flagged patterns + suggestions ───────────────────────────────────────
    flagged = result["flagged_risks"]
    if flagged:
        console.print(
            f"\n[bold red]⚠  {len(flagged)} recurring risk(s) detected "
            f"(threshold: {PATTERN_THRESHOLD}+ times):[/bold red]\n"
        )
        for risk in flagged:
            advice = result["suggestions"].get(risk, "")
            count = next(c for r, c in risk_freq if r == risk)
            console.print(f"  [bold yellow]• {risk}[/bold yellow] [dim]({count}x)[/dim]")
            if advice:
                console.print(f"    [dim]→ {advice}[/dim]")
        console.print()

    # ── Optional LLM narrative ────────────────────────────────────────────────
    if use_llm and flagged:
        cfg = GreybeardConfig.load()
        _synthesize_with_llm(result, history, cfg, model)
    elif use_llm and not flagged:
        console.print(
            "[dim]No recurring patterns yet — LLM synthesis skipped. "
            "Accumulate more decisions first.[/dim]"
        )


def _synthesize_with_llm(
    trends_result: dict,
    history: list[dict],
    cfg: GreybeardConfig,
    model_override: str | None = None,
) -> None:
    """Ask the configured LLM to synthesize a narrative from the trends data."""
    flagged = trends_result["flagged_risks"]
    risk_lines = "\n".join(
        f"- {r} ({c}x)" for r, c in trends_result["risk_frequency"] if r in flagged
    )
    decision_names = ", ".join(e.get("decision_name", "?") for e in history[:10])

    prompt = (
        f"You are a staff-engineer advisor reviewing a team's decision history.\n\n"
        f"Over the last {trends_result['total_decisions']} decisions "
        f"({decision_names}{', ...' if len(history) > 10 else ''}), "
        f"the following risks recurred most often:\n\n{risk_lines}\n\n"
        "Write a concise (3-5 sentences) synthesis that:\n"
        "1. Names the dominant patterns and why they matter\n"
        "2. Offers one concrete systemic fix\n"
        "3. Ends with an encouraging note about the team's self-awareness\n\n"
        "Do NOT use bullet points. Write in plain prose."
    )

    console.print(
        Panel(
            "[bold]LLM Pattern Synthesis[/bold]",
            border_style="purple",
        )
    )

    from .analyzer import _run_anthropic, _run_openai_compat

    llm = cfg.llm
    resolved_model = model_override or llm.resolved_model()
    system = "You are a concise, insightful staff-engineer coach."

    if llm.backend == "anthropic":
        _run_anthropic(llm, resolved_model, system, prompt, stream=True)
    else:
        _run_openai_compat(llm, resolved_model, system, prompt, stream=True)

    console.print()


# ---------------------------------------------------------------------------
# history (view raw log)
# ---------------------------------------------------------------------------


@cli.command("history")
@click.option(
    "--last",
    "days",
    default=30,
    show_default=True,
    metavar="DAYS",
    help="Show entries from last N days (0 = all).",
)
@click.option("--pack", "-p", default=None, help="Filter by pack name.")
@click.option(
    "--limit", "-n", default=20, show_default=True, help="Maximum number of entries to show."
)
def history_cmd(days: int, pack: str | None, limit: int) -> None:
    r"""Show raw decision history log.

    \b
    Examples:
      greybeard history
      greybeard history --last 7 --limit 5
    """
    entries = load_history(days=days, pack=pack)[:limit]

    if not entries:
        console.print("[yellow]No history entries found.[/yellow]")
        console.print("Use [bold]greybeard analyze --save-decision <name>[/bold] to start logging.")
        return

    table = Table(
        title=f"Decision History (last {days}d)" if days else "Decision History (all time)",
        show_header=True,
        header_style="bold",
        title_style="bold purple",
    )
    table.add_column("Date", style="dim", no_wrap=True)
    table.add_column("Decision Name", style="bold white")
    table.add_column("Pack", style="cyan")
    table.add_column("Mode", style="green")
    table.add_column("Key Risks", style="yellow")

    for entry in entries:
        ts = entry.get("timestamp", "")[:10]
        name = entry.get("decision_name", "—")
        p = entry.get("pack", "—")
        m = entry.get("mode", "—")
        risks = ", ".join(entry.get("key_risks", [])[:3]) or "—"
        table.add_row(ts, name, p, m, risks)

    console.print(table)
    console.print(f"\n[dim]History file: {HISTORY_FILE}[/dim]")


# ---------------------------------------------------------------------------
# mcp (MCP server)
# ---------------------------------------------------------------------------


@cli.command()
def mcp() -> None:
    r"""Start a stdio MCP server for use with Claude Desktop, Cursor, Zed, etc.

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


# ---------------------------------------------------------------------------
# adr-save (ADR generation from review)
# ---------------------------------------------------------------------------


@cli.command(name="adr-save")
@click.option(
    "--title",
    "-t",
    required=True,
    help="ADR title (e.g., 'Use PostgreSQL for persistence').",
)
@click.option(
    "--status",
    "-s",
    type=click.Choice(["Proposed", "Accepted", "Deprecated", "Superseded"]),
    default="Proposed",
    show_default=True,
    help="ADR status.",
)
@click.option(
    "--authors",
    "-a",
    multiple=True,
    help="ADR author names (can be used multiple times).",
)
@click.option(
    "--repo",
    "-r",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Path to target git repository (default: current directory).",
)
@click.option(
    "--commit",
    is_flag=True,
    help="Auto-commit the ADR file to git.",
)
def adr_save(title, status, authors, repo, commit) -> None:
    """Save a review as an Architecture Decision Record (ADR).

    Reads the previous greybeard review from stdin and converts it to
    a structured ADR with title, status, context, decision, consequences,
    and alternatives.

    \b
    Examples:
      greybeard analyze | greybeard adr-save --title "Use PostgreSQL"
      greybeard analyze | greybeard adr-save --title "Migrate to gRPC" --status Accepted --commit
      greybeard analyze | greybeard adr-save -t "Cache strategy" -a "alice" -a "bob"
    """
    from .reporters.adr import ADRReporter, ADRRepository

    review_text = _read_stdin_if_available()
    if not review_text:
        console.print(
            "[yellow]No review text provided.[/yellow] Pipe in a greybeard review output."
        )
        console.print("Example: greybeard analyze | greybeard adr-save --title '...'")
        sys.exit(1)

    # Generate ADR
    reporter = ADRReporter(review_text, title=title)
    adr = reporter.generate_adr(
        status=status,  # type: ignore[arg-type]
        authors=list(authors) if authors else None,
    )

    # Save to repository
    repo_path = repo or Path.cwd()
    adr_repo = ADRRepository(repo_path)

    try:
        filepath = adr_repo.save_adr(adr, auto_commit=commit)
        console.print(f"[green]✓[/green] ADR saved to [bold]{filepath}[/bold]")
        if commit:
            console.print("[green]✓[/green] ADR committed to git")
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command(name="adr-list")
@click.option(
    "--repo",
    "-r",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Path to git repository (default: current directory).",
)
def adr_list(repo) -> None:
    """List all Architecture Decision Records in a repository.

    Shows title, status, and date for each ADR in docs/adr/.

    \b
    Examples:
      greybeard adr-list
      greybeard adr-list --repo /path/to/project
    """
    from .reporters.adr import ADRRepository

    repo_path = repo or Path.cwd()
    adr_repo = ADRRepository(repo_path)

    adrs = adr_repo.list_adrs()

    if not adrs:
        console.print(f"[dim]No ADRs found in {adr_repo.adr_dir}[/dim]")
        return

    # Create a table
    table = Table(title="Architecture Decision Records")
    table.add_column("Number", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="magenta")
    table.add_column("Date", style="dim")

    for filepath, adr in adrs:
        # Extract number from filename
        filename = filepath.stem
        num = filename.split("-")[0] if "-" in filename else "?"
        status_color = {
            "Proposed": "yellow",
            "Accepted": "green",
            "Deprecated": "red",
            "Superseded": "dim",
        }.get(adr.status, "white")
        status_text = f"[{status_color}]{adr.status}[/{status_color}]"
        table.add_row(num, adr.title, status_text, adr.date or "")

    console.print(table)


# ---------------------------------------------------------------------------
# slo-check
# ---------------------------------------------------------------------------

cli.add_command(slo_check, "slo-check")


# ---------------------------------------------------------------------------
# risk-gate-wizard
# ---------------------------------------------------------------------------


@cli.command(name="risk-gate-wizard")
@click.option(
    "--output",
    "-o",
    default=".greybeard-precommit.yaml",
    help="Output config file (default: .greybeard-precommit.yaml)",
)
def risk_gate_wizard(output: str) -> None:
    """🧙 Interactive wizard for risk gate configuration.
    
    Build .greybeard-precommit.yaml with risk gates for pre-commit reviews.
    Configure which files require which packs and when to block commits.
    """
    from .wizards.risk_gate_wizard import run_risk_gate_wizard

    run_risk_gate_wizard(output_file=output)
