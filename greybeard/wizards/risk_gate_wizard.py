"""Interactive wizard for creating and configuring risk gates in .greybeard-precommit.yaml.

This wizard walks users through:
  1. Selecting a risk gate to configure (critical, high, medium, low, custom)
  2. Defining glob patterns for file matching
  3. Selecting packs to run for matched files
  4. Setting severity thresholds (fail_on_concerns)
  5. Defining branch skip patterns (for emergency bypasses)
  6. Validating repo structure (checking for .git, pyproject.toml, etc.)

Output: .greybeard-precommit.yaml with risk_gates configured, ready for pre-commit.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import click
import yaml  # type: ignore[import-untyped]
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

console = Console()

# Severity levels in order of severity (most to least)
SEVERITY_LEVELS = ["critical", "high", "medium", "low", "none"]

# Predefined risk gate templates
RISK_GATE_TEMPLATES = {
    "critical": {
        "description": "Catch critical issues — deploy paths, infra changes, auth logic",
        "patterns": ["infra/*", "deploy/*", "auth/*", "schema/*.sql"],
        "fail_on_concerns": "critical",
        "default_packs": ["staff-core", "security-reviewer"],
    },
    "high": {
        "description": "High-risk changes — API contracts, database migrations, config",
        "patterns": ["api/v*/", "migrations/*", "config/*", "*.proto"],
        "fail_on_concerns": "high",
        "default_packs": ["staff-core"],
    },
    "medium": {
        "description": "Standard code review — business logic, features",
        "patterns": ["src/**/*.py", "src/**/*.ts", "src/**/*.tsx"],
        "fail_on_concerns": "medium",
        "default_packs": ["staff-core"],
    },
    "documentation": {
        "description": "Documentation and ADRs — keep docs in sync with code",
        "patterns": ["docs/*.md", "ADR*.md", "*.md"],
        "fail_on_concerns": "low",
        "default_packs": ["documentation-reviewer"],
    },
}

# Common path patterns to suggest
COMMON_PATTERNS = [
    "infra/*",
    "deploy/*",
    "auth/*",
    "migrations/*",
    "schema/*",
    "config/*",
    "src/**/*.py",
    "src/**/*.ts",
    "src/**/*.tsx",
    "api/*",
    "docs/*.md",
    "ADR*.md",
    "*.yaml",
    "*.yml",
    "Dockerfile",
    ".github/workflows/*",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_glob_pattern(pattern: str) -> str | None:
    """Validate a glob pattern. Return error string if invalid, else None."""
    if not pattern or not pattern.strip():
        return "Pattern cannot be empty."
    pattern = pattern.strip()
    # Basic validation: check for invalid characters
    if any(c in pattern for c in ["\0", "\n", "\r"]):
        return "Pattern contains invalid characters."
    return None


def _list_available_packs() -> list[str]:
    """Get list of available packs from the packs directory."""
    packs_dir = Path(__file__).parent.parent / "packs"
    if not packs_dir.exists():
        return []
    # Get all pack directories (directories with a .yaml file inside)
    packs = []
    for pack_dir in packs_dir.iterdir():
        if pack_dir.is_dir():
            yaml_file = pack_dir / f"{pack_dir.name}.yaml"
            if yaml_file.exists():
                packs.append(pack_dir.name)
    return sorted(packs)


def _validate_repo_structure() -> dict[str, bool]:
    """Validate repo structure and return findings."""
    findings: dict[str, bool] = {
        "has_git": (Path.cwd() / ".git").exists(),
        "has_pyproject": (Path.cwd() / "pyproject.toml").exists(),
        "has_precommit": (Path.cwd() / ".pre-commit-config.yaml").exists(),
        "has_github_workflows": (Path.cwd() / ".github" / "workflows").exists(),
    }
    return findings


def _prompt_list(
    prompt: str,
    hint: str = "",
    min_items: int = 0,
    max_items: int | None = None,
    suggestion_list: list[str] | None = None,
) -> list[str]:
    """Prompt for a list of items, one per line, blank to stop.

    Args:
        prompt: Main prompt text
        hint: Additional hint text
        min_items: Minimum items required
        max_items: Maximum items allowed (None = unlimited)
        suggestion_list: List of suggestions to display
    """
    items: list[str] = []
    console.print(f"\n[bold]{prompt}[/bold]")
    if hint:
        console.print(f"[dim]{hint}[/dim]")
    if suggestion_list:
        console.print(f"[dim]Suggestions: {', '.join(suggestion_list[:5])}")
        if len(suggestion_list) > 5:
            console.print(f"[dim]... and {len(suggestion_list) - 5} more[/dim]")
    console.print("[dim](Enter each item on its own line. Blank line when done.)[/dim]")

    while True:
        idx = len(items) + 1
        prompt_text = f"  {idx}"
        if max_items:
            prompt_text += f" (max {max_items})"
        value = click.prompt(prompt_text, default="", show_default=False).strip()
        if not value:
            if len(items) < min_items:
                console.print(f"[yellow]Please enter at least {min_items} item(s).[/yellow]")
                continue
            break
        err = _validate_glob_pattern(value)
        if err:
            console.print(f"[red]{err}[/red]")
            continue
        items.append(value)
        if max_items and len(items) >= max_items:
            console.print(f"[yellow]Reached maximum of {max_items} items.[/yellow]")
            break

    return items


def _select_packs(available_packs: list[str]) -> list[str]:
    """Interactive pack selection."""
    if not available_packs:
        console.print("[yellow]No packs available in this repo.[/yellow]")
        return []

    console.print("\n[bold]Select packs for this risk gate[/bold]")
    console.print("[dim]Packs will be run in order. Multiple packs merge findings.[/dim]")

    # Show table of available packs
    table = Table(title="Available Packs")
    table.add_column("ID", style="cyan")
    table.add_column("Pack Name", style="magenta")
    for idx, pack_name in enumerate(available_packs, 1):
        table.add_row(str(idx), pack_name)
    console.print(table)

    selected: list[str] = []
    console.print("\n[dim](Enter pack IDs or names, one per line. Blank line when done.)[/dim]")

    while True:
        idx = len(selected) + 1
        value = click.prompt(f"  Pack {idx}", default="", show_default=False).strip()
        if not value:
            if len(selected) == 0:
                if click.confirm("No packs selected. Use default 'staff-core'?", default=True):
                    selected.append("staff-core")
            break

        # Try to resolve pack ID or name
        pack: str | None = None
        if value.isdigit():
            pack_idx = int(value) - 1
            if 0 <= pack_idx < len(available_packs):
                pack = available_packs[pack_idx]
        elif value in available_packs:
            pack = value

        if pack:
            if pack not in selected:
                selected.append(pack)
            else:
                console.print(f"[yellow]{pack} already selected.[/yellow]")
        else:
            console.print(f"[red]Pack not found: {value}[/red]")

    return selected


def _select_severity_threshold() -> str:
    """Prompt to select severity threshold (fail_on_concerns)."""
    console.print("\n[bold]Severity threshold (when to fail commit)[/bold]")
    console.print("[dim]Risk gates fail the commit if findings are at or above this level.[/dim]")

    table = Table(title="Severity Levels")
    table.add_column("ID", style="cyan")
    table.add_column("Level", style="magenta")
    table.add_column("Description", style="green")

    descriptions = {
        "critical": "Only critical issues block commit",
        "high": "High or critical issues block commit",
        "medium": "Medium or higher issues block commit",
        "low": "Low or higher issues block commit",
        "none": "Never block commit (warning only)",
    }

    for idx, level in enumerate(SEVERITY_LEVELS, 1):
        table.add_row(str(idx), level, descriptions[level])
    console.print(table)

    while True:
        selection = click.prompt("\nSelect level", default="1", show_default=True).strip()
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(SEVERITY_LEVELS):
                return SEVERITY_LEVELS[idx]
        elif selection in SEVERITY_LEVELS:
            return cast(str, selection)
        console.print("[red]Invalid selection.[/red]")


def _select_template() -> str | None:
    """Interactive template selection."""
    console.print("\n[bold]Quick Start Templates[/bold]")
    console.print("[dim]Start with a template or create a custom risk gate.[/dim]")

    table = Table(title="Risk Gate Templates")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Description", style="green")

    template_names = list(RISK_GATE_TEMPLATES.keys())
    for idx, name in enumerate(template_names, 1):
        tmpl = RISK_GATE_TEMPLATES[name]
        table.add_row(str(idx), name, cast(str, tmpl["description"]))

    console.print(table)

    table2 = Table()
    table2.add_column("ID", style="cyan")
    table2.add_column("Name", style="magenta")
    table2.add_row(str(len(template_names) + 1), "custom")

    console.print(table2)

    while True:
        selection = (
            click.prompt("\nSelect template or (c)ustom", default="1", show_default=True)
            .strip()
            .lower()
        )
        if selection in ["c", "custom"]:
            return None
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(template_names):
                return template_names[idx]
        console.print("[red]Invalid selection.[/red]")


# ---------------------------------------------------------------------------
# Main wizard
# ---------------------------------------------------------------------------


def run_risk_gate_wizard(output_file: str | None = None) -> Path:
    """Run the interactive risk gate wizard.

    Returns the Path to the created/updated config file.
    """
    output_file = output_file or ".greybeard-precommit.yaml"
    output_path = Path(output_file)

    console.print(
        Panel(
            "[bold]Risk Gate Configuration Wizard[/bold]\n\n"
            "Build .greybeard-precommit.yaml with risk gates for pre-commit reviews.\n"
            "Risk gates control which packs run and when to block commits.",
            title="[bold purple]🧙 greybeard risk-gate-wizard[/bold purple]",
            border_style="purple",
        )
    )

    # Load existing config or create new one
    from ..precommit import PreCommitConfig

    config = PreCommitConfig()
    if output_path.exists():
        console.print(f"\n[dim]Found existing config at {output_file}[/dim]")
        if click.confirm("Load existing config?", default=True):
            try:
                config = PreCommitConfig.load()
                console.print(
                    f"[green]✓[/green] Loaded {len(config.risk_gates)} existing risk gates"
                )
            except yaml.YAMLError as e:
                console.print(f"[red]Error loading config: {e}[/red]")
                if not click.confirm("Continue anyway?", default=False):
                    raise click.Abort()

    # Check repo structure
    console.print(Rule("[bold]Repo Structure Check[/bold]", style="blue"))
    findings = _validate_repo_structure()
    if findings["has_git"]:
        console.print("[green]✓[/green] Git repository detected")
    if findings["has_precommit"]:
        console.print("[green]✓[/green] .pre-commit-config.yaml found")
    if findings["has_pyproject"]:
        console.print("[green]✓[/green] pyproject.toml found")

    # Get available packs
    available_packs = _list_available_packs()
    if not available_packs:
        console.print(
            "[yellow]⚠️  No packs found in ./greybeard/packs[/yellow]\n"
            "[dim]Install packs or create your own before defining risk gates.[/dim]"
        )
    else:
        console.print(f"[green]✓[/green] Found {len(available_packs)} available packs")

    # Configure base settings
    console.print(Rule("[bold]Base Configuration[/bold]", style="purple"))

    config.enabled = click.confirm("\nEnable pre-commit hook integration?", default=config.enabled)

    if not config.enabled:
        console.print("[yellow]Pre-commit integration is disabled. Risk gates won't run.[/yellow]")

    config.default_pack = click.prompt(
        "\nDefault pack for reviews",
        default=config.default_pack,
        show_default=True,
    )

    config.skip_unstaged = click.confirm(
        "\nSkip unstaged changes (only review staged)?",
        default=config.skip_unstaged,
    )

    # Configure excluded paths
    excluded = _prompt_list(
        "\nExcluded paths (glob patterns)",
        hint="Files matching these patterns won't be reviewed.",
        suggestion_list=[".venv/*", "node_modules/*", "*.lock", ".mypy_cache/*"],
    )
    config.excluded_paths = excluded

    # Configure risk gates
    console.print(Rule("[bold]Risk Gates Configuration[/bold]", style="purple"))
    console.print(
        "\n[dim]Risk gates define which files require which packs and when to fail commits.[/dim]"
    )

    while True:
        if config.risk_gates:
            console.print(f"\n[bold]Current risk gates ({len(config.risk_gates)}):[/bold]")
            for gate in config.risk_gates:
                console.print(
                    f"  • [cyan]{gate.name}[/cyan]: "
                    f"{len(gate.patterns)} patterns, "
                    f"fail_on={gate.fail_on_concerns}, "
                    f"{len(gate.required_packs)} packs"
                )

        if not click.confirm("\nAdd/edit a risk gate?", default=True):
            break

        # Select template or go custom
        template = _select_template()

        gate_name = None
        gate_patterns = []
        gate_packs = []
        gate_severity = "critical"

        if template:
            tmpl = RISK_GATE_TEMPLATES[template]
            gate_name = template
            gate_patterns = tmpl["patterns"].copy()
            gate_packs = tmpl["default_packs"].copy()
            gate_severity = tmpl["fail_on_concerns"]

            console.print(f"\n[green]✓[/green] Using [bold]{template}[/bold] template")
            console.print(f"  Patterns: {', '.join(gate_patterns)}")
            console.print(f"  Packs: {', '.join(gate_packs)}")
            console.print(f"  Fail on: {gate_severity}")

            if click.confirm("\nCustomize this template?", default=False):
                template = None

        if not template:
            # Custom configuration
            gate_num = len(config.risk_gates) + 1
            gate_name = click.prompt("\nRisk gate name", default=f"gate-{gate_num}")

            gate_patterns = _prompt_list(
                "\nFile patterns (glob)",
                hint="Which files should this gate check?",
                min_items=1,
                suggestion_list=COMMON_PATTERNS,
            )

            gate_packs = _select_packs(available_packs)

            gate_severity = _select_severity_threshold()

        # Optional: branch skip patterns
        skip_branches = _prompt_list(
            "\nBranch patterns to skip (optional)",
            hint="Skip this gate on branches matching these patterns (e.g. hotfix/*, emergency/*)",
            suggestion_list=["hotfix/*", "emergency/*", "wip/*"],
        )

        # Create/update risk gate
        new_gate = type(
            "RiskGate",
            (),
            {
                "name": gate_name,
                "patterns": gate_patterns,
                "fail_on_concerns": gate_severity,
                "required_packs": gate_packs,
                "skip_if_branch": skip_branches,
            },
        )()

        # Check for duplicates
        existing_idx = None
        for idx, gate in enumerate(config.risk_gates):
            if gate.name == gate_name:
                existing_idx = idx
                break

        if existing_idx is not None:
            if click.confirm(f"\nOverwrite existing '{gate_name}' gate?", default=True):
                config.risk_gates[existing_idx] = new_gate
                console.print(f"[green]✓[/green] Updated [bold]{gate_name}[/bold]")
            else:
                console.print("[yellow]Skipped.[/yellow]")
        else:
            config.risk_gates.append(new_gate)
            console.print(f"[green]✓[/green] Added [bold]{gate_name}[/bold]")

    # Review and save
    console.print(Rule("[bold]Summary[/bold]", style="green"))
    console.print(f"\n  [bold]Config file:[/bold] {output_file}")
    console.print(f"  [bold]Risk gates:[/bold] {len(config.risk_gates)}")
    for gate in config.risk_gates:
        console.print(
            f"    • [cyan]{gate.name}[/cyan]: {len(gate.patterns)} patterns, "
            f"fail_on={gate.fail_on_concerns}"
        )
    console.print(f"  [bold]Excluded paths:[/bold] {len(config.excluded_paths)}")
    console.print(f"  [bold]Default pack:[/bold] {config.default_pack}")

    if not click.confirm("\nSave configuration?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        raise click.Abort()

    # Convert config to dict for YAML serialization
    config_dict = {
        "enabled": config.enabled,
        "default_pack": config.default_pack,
        "additional_packs": config.additional_packs,
        "fail_on_concerns": config.fail_on_concerns,
        "skip_unstaged": config.skip_unstaged,
        "max_context_lines": config.max_context_lines,
        "verbose": config.verbose,
        "allow_empty_commits": config.allow_empty_commits,
        "excluded_paths": config.excluded_paths,
        "risk_gates": [
            {
                "name": gate.name,
                "patterns": gate.patterns,
                "fail_on_concerns": gate.fail_on_concerns,
                "required_packs": gate.required_packs,
                "skip_if_branch": gate.skip_if_branch,
            }
            for gate in config.risk_gates
        ],
    }

    # Write config file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    console.print(
        Panel(
            f"[bold green]✓ Configuration saved![/bold green]\n\n"
            f"  [bold]{output_file}[/bold]\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Review the config: [bold]cat {output_file}[/bold]\n"
            f"  2. Show current settings: [bold]greybeard-precommit config show[/bold]\n"
            f"  3. Install pre-commit hook: [bold].pre-commit-config.yaml[/bold]\n"
            f"  4. Test: [bold]git add . && git commit --dry-run[/bold]",
            title="[bold purple]🧙 Configuration Complete[/bold purple]",
            border_style="green",
        )
    )

    return output_path
