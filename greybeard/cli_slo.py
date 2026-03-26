"""SLO check command for CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agents import SLOAgent
from .agents.slo_agent import SLORecommendation

console = Console()


@click.command()
@click.option(
    "--context",
    "-c",
    multiple=True,
    help="Context flags: service-type:saas, criticality:high, users:1000, etc.",
)
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False),
    help="Path to repository for deeper analysis.",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "markdown", "table"]),
    default="table",
    help="Output format.",
)
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, file_okay=True),
    help="File or diff to analyze (instead of stdin).",
)
def slo_check(context: tuple[str], repo: str | None, output: str, file: str | None) -> None:
    """Analyze code and recommend SLO targets.

    Examines code patterns, architecture, and deployment context to recommend
    appropriate SLO targets (latency, error rate, availability).

    \b
    Examples:
      greybeard slo-check --context "service-type:saas"
      greybeard slo-check --repo /path/to/api --context "criticality:high"
      git diff main | greybeard slo-check --output json
      cat service.py | greybeard slo-check --context "service-type:batch"
    """
    # Parse context flags
    ctx_dict = {}
    for flag in context:
        if ":" in flag:
            key, val = flag.split(":", 1)
            ctx_dict[key.strip()] = val.strip()
        else:
            console.print(f"[yellow]Warning:[/yellow] Invalid context flag: {flag}")

    # Read code input
    code_input = ""
    if file:
        code_input = Path(file).read_text()
    else:
        if not sys.stdin.isatty():
            code_input = sys.stdin.read()

    # Run analysis
    agent = SLOAgent()
    recommendation = agent.analyze(
        code_snippet=code_input,
        repo_path=repo,
        service_type=ctx_dict.get("service-type"),
        context=ctx_dict,
    )

    # Output
    if output == "json":
        _output_json(recommendation)
    elif output == "markdown":
        _output_markdown(recommendation)
    else:
        _output_table(recommendation)


def _output_json(rec: SLORecommendation) -> None:
    """Output as JSON."""
    data = rec.to_dict()
    console.print(json.dumps(data, indent=2))


def _output_markdown(rec: SLORecommendation) -> None:
    """Output as Markdown."""
    rec_dict = rec.to_dict()

    lines = [
        f"# SLO Recommendations: {rec_dict['service_type'].upper()}",
        "",
    ]

    if rec_dict.get("service_name"):
        lines.append(f"**Service:** {rec_dict['service_name']}")
        lines.append("")

    lines.append(f"**Confidence:** {rec_dict['confidence']:.0%}")
    lines.append("")

    if rec_dict.get("targets"):
        lines.append("## SLO Targets")
        lines.append("")
        for target in rec_dict["targets"]:
            lines.append(f"### {target['metric'].upper()}")
            lines.append(f"- **Target:** {target['target']}")
            if target["range"][0]:
                lines.append(f"- **Range:** {target['range'][0]} - {target['range'][1]}")
            lines.append(f"- **Rationale:** {target['rationale']}")
            lines.append("")

    if rec_dict.get("notes"):
        lines.append("## Notes & Recommendations")
        lines.append("")
        lines.append(rec_dict["notes"])
        lines.append("")

    console.print("\n".join(lines))


def _output_table(rec: SLORecommendation) -> None:
    """Output as a nice table."""
    rec_dict = rec.to_dict()

    console.print(
        Panel(
            f"[bold]{rec_dict['service_type'].upper()}[/bold] Service",
            title="[bold cyan]SLO Recommendations[/bold cyan]",
            border_style="cyan",
        )
    )

    if rec_dict.get("service_name"):
        console.print(f"[bold]Service:[/bold] {rec_dict['service_name']}")

    console.print(f"[bold]Confidence:[/bold] {rec_dict['confidence']:.0%}")
    console.print("")

    # Targets table
    if rec_dict.get("targets"):
        table = Table(title="SLO Targets", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Target", style="green")
        table.add_column("Range", style="dim")
        table.add_column("Rationale", style="white")

        for target in rec_dict["targets"]:
            range_str = (
                f"{target['range'][0]} → {target['range'][1]}" if target["range"][0] else "—"
            )
            rationale = target["rationale"]
            if len(rationale) > 60:
                rationale = rationale[:60] + "..."
            table.add_row(
                target["metric"],
                target["target"],
                range_str,
                rationale,
            )

        console.print(table)

    # Notes
    if rec_dict.get("notes"):
        console.print("")
        console.print("[bold]Notes & Recommendations:[/bold]")
        for line in rec_dict["notes"].split("\n"):
            console.print(f"  {line}")
