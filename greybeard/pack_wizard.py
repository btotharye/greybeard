"""Interactive wizard for creating new greybeard content packs.

Scaffolds the full pack folder structure:
  <pack-name>/
    <pack-name>.yaml       — pack definition (perspective, tone, heuristics, etc.)
    <PACK-NAME>-EXAMPLE.md — example scenario showing the pack in action
    README.md              — quick-start guide
"""

from __future__ import annotations

import re
from pathlib import Path

import click
import yaml  # type: ignore[import-untyped]
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _slugify(text: str) -> str:
    """Convert arbitrary text to a valid kebab-case pack slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _validate_pack_name(name: str) -> str | None:
    """Return an error string if the name is invalid, else None."""
    if not name:
        return "Pack name cannot be empty."
    slug = _slugify(name)
    if not _SLUG_RE.match(slug):
        return f"Pack name must be kebab-case (e.g. 'security-review'). Got: {slug!r}"
    return None


def _prompt_list(
    prompt: str,
    hint: str = "",
    min_items: int = 1,
    example: str = "",
) -> list[str]:
    """Prompt for a list of items, one per line, blank to stop."""
    items: list[str] = []
    console.print(f"\n[bold]{prompt}[/bold]")
    if hint:
        console.print(f"[dim]{hint}[/dim]")
    if example:
        console.print(f"[dim]e.g. {example}[/dim]")
    console.print("[dim](Enter each item on its own line. Blank line when done.)[/dim]")

    while True:
        idx = len(items) + 1
        value = click.prompt(f"  {idx}", default="", show_default=False).strip()
        if not value:
            if len(items) < min_items:
                console.print(f"[yellow]Please enter at least {min_items} item(s).[/yellow]")
                continue
            break
        items.append(value)

    return items


def _build_yaml(data: dict) -> str:
    """Render pack data as nicely formatted YAML."""
    # We control field order manually for readability
    ordered_keys = [
        "name",
        "description",
        "perspective",
        "tone",
        "focus_areas",
        "heuristics",
        "example_questions",
        "communication_style",
    ]
    lines: list[str] = []
    for key in ordered_keys:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, str) and "\n" in value:
            # Block scalar
            lines.append(f"{key}: |")
            for line in value.splitlines():
                lines.append(f"  {line}" if line else "")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                # Escape single quotes in YAML single-quoted style
                escaped = str(item).replace("'", "''")
                lines.append(f"  - '{escaped}'")
        else:
            lines.append(yaml.dump({key: value}, default_flow_style=False).rstrip())
    return "\n".join(lines) + "\n"


def _build_example_md(
    pack_name: str,
    pack_title: str,
    description: str,
    focus_areas: list[str],
    heuristics: list[str],
) -> str:
    """Generate a placeholder EXAMPLE.md for the pack."""
    focus_list = "\n".join(f"- **{fa.split('(')[0].strip()}**" for fa in focus_areas[:4])
    heuristic_sample = "\n".join(f"- {h}" for h in heuristics[:3])

    return f"""\
# {pack_title} Pack: Real-World Example

## Scenario: *(replace with a realistic scenario for your domain)*

### The Proposal

"*(Describe a typical decision or artifact this pack should review.)*"

**Context:**
- Team size: ?
- Timeline: ?
- Key stakeholders: ?

---

### What {pack_title} Would Ask

*(Walk through 2-3 concrete concerns this reviewer would surface.)*

**Focus area example**

"{heuristics[0] if heuristics else "What is the blast radius if this goes wrong?"}"

→ *(Explain what this reviewer would probe and why.)*

---

### Key Focus Areas This Pack Covers

{focus_list}

### Sample Heuristics in Action

{heuristic_sample}

---

### Action Items

❌ **Don't:** *(Anti-pattern to avoid)*
✅ **Do:** *(Better approach)*
✅ **Do:** *(Another concrete recommendation)*

---

*This example demonstrates how the {pack_title} pack surfaces domain-specific
risks and drives better decisions.*
"""


def _build_readme(
    pack_name: str,
    pack_title: str,
    description: str,
    focus_areas: list[str],
) -> str:
    """Generate a README.md for the pack."""
    focus_bullets = "\n".join(
        f"- **{fa.split('(')[0].strip()}**: *(what to look for)*" for fa in focus_areas
    )
    return f"""\
# {pack_title} Pack

{description}

## Quick Start

```bash
# Review a decision or document
cat your-doc.md | greybeard analyze --pack {pack_name}

# Self-check before sharing
greybeard self-check --pack {pack_name} --context "my proposal"

# Mentor mode — explain the reasoning
cat design-doc.md | greybeard analyze --pack {pack_name} --mode mentor
```

## Focus Areas

{focus_bullets}

## When to Use This Pack

Use this pack when reviewing *(describe the kinds of decisions and documents
this pack is best for)*.

## Customizing

Edit `{pack_name}.yaml` to:
- Adjust the `perspective` to change the reviewer's voice
- Add `heuristics` for your team's specific rules of thumb
- Add `example_questions` to guide AI output

---

*Created with `greybeard pack new`. See [greybeard docs](https://greybeard.readthedocs.io)
for more.*
"""


# ---------------------------------------------------------------------------
# Main wizard
# ---------------------------------------------------------------------------


def run_pack_wizard(output_dir: str | None = None) -> Path:
    """Run the interactive pack creation wizard.

    Returns the Path to the created pack directory.
    """
    console.print(
        Panel(
            "[bold]Pack Authoring Wizard[/bold]\n\n"
            "Answer a few questions to scaffold a complete greybeard content pack.\n"
            "You can edit the generated files afterward to refine your pack.",
            title="[bold purple]🧙 greybeard pack new[/bold purple]",
            border_style="purple",
        )
    )

    # ------------------------------------------------------------------
    # Step 1: Pack identity
    # ------------------------------------------------------------------
    console.print(Rule("[bold]Step 1 of 4[/bold] — Pack Identity", style="purple"))

    # Name
    while True:
        raw_name = click.prompt("\nPack name", default="my-pack")
        slug = _slugify(raw_name)
        err = _validate_pack_name(slug)
        if err:
            console.print(f"[red]{err}[/red]")
        else:
            pack_name = slug
            if slug != raw_name.lower().strip():
                console.print(f"[dim]→ normalized to: [bold]{pack_name}[/bold][/dim]")
            break

    pack_title = " ".join(word.capitalize() for word in pack_name.split("-"))

    description = click.prompt(
        "\nOne-line description (what problem does this pack solve?)",
        default=f"Domain-specific review lens for {pack_title} decisions.",
    ).strip()

    # ------------------------------------------------------------------
    # Step 2: Reviewer persona
    # ------------------------------------------------------------------
    console.print(Rule("[bold]Step 2 of 4[/bold] — Reviewer Persona", style="purple"))
    console.print(
        "\n[dim]Define the perspective this pack adopts. Think of it as a character:\n"
        "who is this reviewer, what have they seen, and what do they care about?[/dim]"
    )

    perspective = click.prompt(
        "\nPerspective (who is this reviewer?)",
        default=(
            f"A senior {pack_title} practitioner with deep domain expertise and "
            "battle-tested experience making and reviewing these kinds of decisions."
        ),
    ).strip()

    tone = click.prompt(
        "\nTone (how do they communicate?)",
        default="direct and constructive — raises hard questions without blocking progress",
    ).strip()

    # ------------------------------------------------------------------
    # Step 3: Focus areas and heuristics
    # ------------------------------------------------------------------
    console.print(Rule("[bold]Step 3 of 4[/bold] — Focus Areas & Heuristics", style="purple"))

    focus_areas = _prompt_list(
        "Focus areas",
        hint="What domains or concerns should this reviewer always check?",
        min_items=2,
        example="data integrity, rollback safety, blast radius",
    )

    heuristics = _prompt_list(
        "Key heuristics (mental checklist questions)",
        hint="Specific questions the reviewer asks themselves. Phrase as questions.",
        min_items=2,
        example='"What happens when this fails at 3am?", "Who owns this in 6 months?"',
    )

    example_questions = _prompt_list(
        "Example questions to surface in a review",
        hint="Specific, pointed questions the reviewer would ask the author.",
        min_items=2,
        example='"Has this rollback plan been tested?", "What does the alert look like?"',
    )

    # ------------------------------------------------------------------
    # Step 4: Communication style
    # ------------------------------------------------------------------
    console.print(Rule("[bold]Step 4 of 4[/bold] — Communication Style", style="purple"))
    console.print(
        "\n[dim]How should findings be framed? What tone and structure should "
        "the output follow?[/dim]"
    )

    communication_style = click.prompt(
        "\nCommunication style guidance",
        default=(
            "Frame concerns as questions and tradeoffs, not vetoes. "
            "Acknowledge what works before raising risks. "
            "Be specific about who is affected and what the blast radius is."
        ),
    ).strip()

    # ------------------------------------------------------------------
    # Confirm and generate
    # ------------------------------------------------------------------
    console.print(Rule("[bold]Summary[/bold]", style="green"))
    console.print(f"\n  [bold]Pack:[/bold]        {pack_name}")
    console.print(f"  [bold]Description:[/bold] {description}")
    console.print(f"  [bold]Focus areas:[/bold] {len(focus_areas)} defined")
    console.print(f"  [bold]Heuristics:[/bold]  {len(heuristics)} defined")
    console.print(f"  [bold]Questions:[/bold]   {len(example_questions)} defined")

    # Determine output directory
    base = Path(output_dir) if output_dir else Path.cwd()

    pack_dir = base / pack_name
    yaml_path = pack_dir / f"{pack_name}.yaml"
    example_path = pack_dir / f"{pack_name.upper().replace('-', '-')}-EXAMPLE.md"
    readme_path = pack_dir / "README.md"

    console.print(f"\n  [bold]Output:[/bold]      {pack_dir}/")
    console.print(f"    [dim]{yaml_path.name}[/dim]")
    console.print(f"    [dim]{example_path.name}[/dim]")
    console.print(f"    [dim]{readme_path.name}[/dim]")

    if not click.confirm("\nGenerate pack?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        raise click.Abort()

    # ------------------------------------------------------------------
    # Write files
    # ------------------------------------------------------------------
    pack_dir.mkdir(parents=True, exist_ok=True)

    pack_data = {
        "name": pack_name,
        "description": description,
        "perspective": perspective,
        "tone": tone,
        "focus_areas": focus_areas,
        "heuristics": heuristics,
        "example_questions": example_questions,
        "communication_style": communication_style,
    }

    yaml_path.write_text(_build_yaml(pack_data))
    example_path.write_text(
        _build_example_md(pack_name, pack_title, description, focus_areas, heuristics)
    )
    readme_path.write_text(_build_readme(pack_name, pack_title, description, focus_areas))

    # ------------------------------------------------------------------
    # Success
    # ------------------------------------------------------------------
    console.print(
        Panel(
            f"[bold green]✓ Pack scaffolded![/bold green]\n\n"
            f"  [bold]{pack_dir}/[/bold]\n"
            f"    {yaml_path.name}\n"
            f"    {example_path.name}\n"
            f"    README.md\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Edit [bold]{yaml_path}[/bold] to refine your pack\n"
            f"  2. Fill in [bold]{example_path.name}[/bold] with a real scenario\n"
            f"  3. Test it: [bold]cat doc.md | greybeard analyze --pack {pack_dir}[/bold]\n"
            f"  4. Share: [bold]greybeard pack install github:you/your-packs-repo[/bold]",
            title="[bold purple]🧙 Pack Created[/bold purple]",
            border_style="green",
        )
    )

    return pack_dir
