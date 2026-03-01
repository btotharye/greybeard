# 🧙 greybeard

```
        .  .
       .|  |.
       ||  ||
      .+====+.
      | .''. |
      |/ () \|    "Would I be okay getting paged
     (_`.__.'_)    about this at 3am six months
     //|    |\\    from now?"
    || |    | ||
    `--'    '--`
   ~~~~~~~~~~~~~~~~~
```

> A CLI-first thinking tool that channels the calm, battle-tested wisdom of a Staff / Principal engineer — helping you review decisions, systems, and tradeoffs before you ship them.
>
> The greybeard has been paged at 3am. They've watched confident decisions become production incidents. They've seen "we'll clean it up later" last five years. They're not here to block you — they're here to make sure you've thought it through.

[![CI](https://github.com/btotharye/greybeard/actions/workflows/ci.yml/badge.svg)](https://github.com/btotharye/greybeard/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-readthedocs-blue)](https://greybeard.readthedocs.io)
[![PyPI](https://img.shields.io/pypi/v/greybeard?color=blue)](https://pypi.org/project/greybeard/)
[![Python Version](https://img.shields.io/pypi/pyversions/greybeard)](https://pypi.org/project/greybeard/)
[![License](https://img.shields.io/github/license/btotharye/greybeard)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## Philosophy

This is **not** a linter. It won't yell at your variable names or enforce opinionated formatting.

This is a **thinking partner**. It models how Staff and Principal engineers reason about systems: failure modes, ownership, long-term cost, and the human impact of decisions. It asks the uncomfortable questions so your reviewer doesn't have to.

---

## What It Does

- **Sanity-checks** architecture decisions and design docs
- **Surfaces** operational risks, ownership gaps, and maintenance burden
- **Coaches** you on how to communicate decisions to peers, teams, and leadership
- **Teaches** Staff-level reasoning through mentorship mode
- **Reviews** your own thinking before you share it with others
- **Integrates** into Claude Desktop, Cursor, Zed and any MCP-compatible tool

📚 **[Full Documentation](https://greybeard.readthedocs.io/en/latest/)** — Installation, configuration, guides, and reference

---

## Quick Start

### Install from PyPI

```bash
# Using uv (recommended - faster)
uv pip install greybeard

# Or using pip
pip install greybeard
```

**With optional extras:**

```bash
uv pip install "greybeard[anthropic]"     # Add Claude/Anthropic support
uv pip install "greybeard[all]"           # Everything

# Or with pip
pip install "greybeard[anthropic]"
pip install "greybeard[all]"
```

**Then configure:**

```bash
greybeard init          # interactive setup wizard
greybeard packs         # see available content packs
```

### Development installation

For contributing or local development:

### Development installation

For contributing or local development:

```bash
git clone https://github.com/btotharye/greybeard.git
cd greybeard

# Option 1: Use Makefile (easiest)
make install-dev
make test
make help                      # see all available commands

# Option 2: Use uv directly
uv pip install -e ".[dev]"
uv run pytest

# Option 3: Traditional pip
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development setup.

---

## LLM Backends

greybeard works with whatever LLM you prefer — cloud or local. Configure once with `greybeard init` or `greybeard config set`.

| Backend     | How           | What you need                                                        |
| ----------- | ------------- | -------------------------------------------------------------------- |
| `openai`    | OpenAI API    | `OPENAI_API_KEY`                                                     |
| `anthropic` | Anthropic API | `ANTHROPIC_API_KEY` + `greybeard[anthropic]` extra (see Quick Start) |
| `ollama`    | Local (free)  | [Ollama](https://ollama.ai) running: `ollama serve`                  |
| `lmstudio`  | Local (free)  | [LM Studio](https://lmstudio.ai) server running                      |

```bash
# Configure interactively
greybeard init

# Or set directly
greybeard config set llm.backend ollama
greybeard config set llm.model llama3.2

greybeard config set llm.backend openai
greybeard config set llm.model gpt-4o-mini

greybeard config show
```

Config lives at `~/.greybeard/config.yaml`.

See [LLM Backends Guide](https://greybeard.readthedocs.io/en/latest/guides/backends/) for detailed setup instructions.

---

## Modes

| Mode         | Description                                               |
| ------------ | --------------------------------------------------------- |
| `review`     | Concise Staff-level review of a decision or diff          |
| `mentor`     | Explain the reasoning and thought process behind concerns |
| `coach`      | Help phrase constructive feedback for a specific audience |
| `self-check` | Review your own decision before sharing it                |

---

## Usage

```bash
# Review a git diff (default mode + default pack from config)
git diff main | greybeard analyze

# Review with a specific mode and pack
git diff main | greybeard analyze --mode mentor --pack oncall-future-you

# Review a design doc and save the output
cat design-doc.md | greybeard analyze --output review-2024-03-01.md

# Self-check a decision before sharing
greybeard self-check --context "We're migrating auth to a new provider mid-sprint"

# Get help communicating a concern
greybeard coach --audience leadership --context "I think we're moving too fast"

# Review with repo context (README, git log, structure)
greybeard analyze --repo . --context "mid-sprint auth migration"

# List available packs
greybeard packs

# Start MCP server (for Claude Desktop, Cursor, Zed, etc.)
greybeard mcp
```

---

## Content Packs

Content packs define the perspective, tone, and heuristics used during review. They're plain YAML — human-editable, version-controllable, shareable.

### Built-in Packs

| Pack                  | Perspective           | Focus                                        |
| --------------------- | --------------------- | -------------------------------------------- |
| `staff-core`          | Staff Engineer        | Ops, ownership, long-term cost               |
| `oncall-future-you`   | On-call engineer, 3am | Failure modes, pager noise, recovery         |
| `mentor-mode`         | Experienced mentor    | Teaching, reasoning, growth                  |
| `solutions-architect` | Solutions Architect   | Entity modeling, boundaries, fit-for-purpose |
| `idp-readiness`       | Platform Engineering  | IDP maturity, automation vs process          |

### Community Packs (from GitHub)

```bash
# Install all packs from a GitHub repo's packs/ directory
greybeard pack install github:someone/their-greybeard-packs

# Install a single pack file
greybeard pack install github:owner/repo/packs/my-pack.yaml

# Install from a raw URL
greybeard pack install https://example.com/my-pack.yaml

# See what's installed
greybeard pack list

# Remove a source
greybeard pack remove owner__repo
```

Installed packs are cached at `~/.greybeard/packs/` and available by name just like built-ins.

### Custom Packs

Create a `.yaml` file and pass it directly:

```bash
cat design-doc.md | greybeard analyze --pack my-team.yaml
```

See [`examples/custom-pack.md`](examples/custom-pack.md) for the pack schema.

### Publishing a Pack

Create a public GitHub repo with a `packs/` directory containing `.yaml` files. Anyone can install it with:

```bash
greybeard pack install github:your-handle/your-pack-repo
```

---

## MCP Integration

greybeard runs as a local [MCP](https://modelcontextprotocol.io) server, exposing its review tools to any compatible client.

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "greybeard": {
      "command": "greybeard",
      "args": ["mcp"]
    }
  }
}
```

Then restart Claude Desktop. You'll see greybeard tools available in the tool picker.

### Cursor / Zed / Other MCP Clients

Any client that supports the MCP stdio transport works. Point it at `greybeard mcp`.

### Available MCP Tools

| Tool                  | Description                                    |
| --------------------- | ---------------------------------------------- |
| `review_decision`     | Staff-level review of a decision or document   |
| `self_check`          | Review your own proposal before sharing        |
| `coach_communication` | Get suggested language for a specific audience |
| `list_packs`          | List available content packs                   |

---

## Primary Review Lenses

The greybeard always reasons through four lenses:

1. **Operational impact** — failure modes, observability, deploy & rollback safety
2. **Long-term ownership** — who owns this in 6–12 months, tribal knowledge risk, accountability
3. **On-call & human cost** — pager noise, manual recovery, 3am failure scenarios
4. **"Who pays for this later?"** — complexity tax, maintenance burden, coordination overhead

---

## Output Format

All output is structured Markdown:

```markdown
## Summary

...

## Key Risks

...

## Tradeoffs

...

## Questions to Answer Before Proceeding

...

## Suggested Communication Language

...

---

_Assumptions made: ..._
```

Save to a file with `--output review.md`.

---

## Design Decisions

- **Multi-backend**: OpenAI, Anthropic, Ollama, LM Studio. Configured via `~/.greybeard/config.yaml`. All local backends require no API key.
- **CLI-first**: No web UI, no server. Designed to be piped into and out of.
- **Stateless**: No conversation history by default. Add `--context` for prior context.
- **Pack format**: YAML for human editability. Packs are loaded at runtime and validated loosely.
- **Remote packs cached locally**: `~/.greybeard/packs/<source>/` — installed once, used like built-ins.
- **MCP stdio transport**: The simplest, most compatible MCP integration. No HTTP server needed.
- **Minimal deps**: `click`, `openai`, `pyyaml`, `rich`, `python-dotenv`. Anthropic is optional.

---

## Contributing

We welcome contributions! 🎉

**Quick Start:**

- **Content Packs**: Add a `.yaml` file to `packs/` - the easiest and highest-value contribution
- **Bug Reports**: [Open an issue](https://github.com/btotharye/greybeard/issues/new?template=bug_report.yml)
- **Feature Requests**: [Suggest a feature](https://github.com/btotharye/greybeard/issues/new?template=feature_request.yml)
- **Code**: See the [Contributing Guide](CONTRIBUTING.md) for setup instructions

**Community:**

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)
- [Documentation](https://greybeard.readthedocs.io/en/latest/contributing/)

If you build a public pack repo on GitHub, feel free to open an issue linking to it — we'll add it to a community registry.
