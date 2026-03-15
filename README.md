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
[![codecov](https://codecov.io/gh/btotharye/greybeard/branch/main/graph/badge.svg)](https://codecov.io/gh/btotharye/greybeard)
[![Documentation](https://img.shields.io/badge/docs-readthedocs-blue)](https://greybeard.readthedocs.io)
[![PyPI](https://img.shields.io/pypi/v/greybeard?color=blue)](https://pypi.org/project/greybeard/)
[![Python Version](https://img.shields.io/pypi/pyversions/greybeard)](https://pypi.org/project/greybeard/)
[![License](https://img.shields.io/github/license/btotharye/greybeard)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

<p align="center">
  <img src="demo.gif" alt="greybeard demo" width="800">
</p>

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

| Pack                  | Perspective           | Focus                                             |
| --------------------- | --------------------- | ------------------------------------------------- |
| `staff-core`          | Staff Engineer        | Ops, ownership, long-term cost                    |
| `oncall-future-you`   | On-call engineer, 3am | Failure modes, pager noise, recovery              |
| `mentor-mode`         | Experienced mentor    | Teaching, reasoning, growth                       |
| `solutions-architect` | Solutions Architect   | Entity modeling, boundaries, fit-for-purpose      |
| `idp-readiness`       | Platform Engineering  | IDP maturity, automation vs process               |
| `platform-eng`        | Platform Engineer     | DX, abstractions, tool maturity, team scaling     |
| `security-reviewer`   | AppSec Engineer       | Auth, injection, secrets, overprivileged access   |
| `startup-pragmatist`  | Pragmatic Engineer    | Complexity vs stage, reversibility, scope         |
| `incident-postmortem` | SRE / On-call         | Blameless analysis, root cause, action items      |
| `data-migrations`     | Migration Expert      | Lock safety, zero-downtime, rollback, performance |

### Testing Packs

Each built-in pack includes an example markdown file you can test against:

```bash
# Test a pack with its example
cat packs/staff-core/STAFF-CORE-EXAMPLE.md | greybeard analyze --pack staff-core
cat packs/security-reviewer/SECURITY-REVIEWER-EXAMPLE.md | greybeard analyze --pack security-reviewer
cat packs/mentor-mode/MENTOR-MODE-EXAMPLE.md | greybeard analyze --pack mentor-mode --mode mentor

# See what's available
ls packs/*/README.md      # Get quick start for each pack
ls packs/*-EXAMPLE.md     # See all example files
```

Each pack folder contains:

- `<pack-name>.yaml` — The pack definition
- `README.md` — Quick start and focus areas
- `<PACK>-EXAMPLE.md` — A real-world scenario to test with

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

1. Install greybeard (if you haven't already):

```bash
pip install greybeard
# or: uv pip install greybeard
```

2. Find your greybeard command path:

```bash
which greybeard
```

Save this output — you'll need it in the next step.

3. Edit your Claude Desktop config:
   - **macOS:** `~/Library/Application\ Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add the greybeard server with the full path from step 2:

```json
{
  "mcpServers": {
    "greybeard": {
      "command": "/Users/you/.pyenv/shims/greybeard",
      "args": ["mcp"]
    }
  }
}
```

Replace the path with your actual path from `which greybeard`.

4. Save and restart Claude Desktop.

### Using greybeard in Claude

Once connected, just ask Claude naturally to use greybeard's tools:

- _"Review this architecture decision"_ → Claude calls `review_decision`
- _"Self-check my proposal before I send it"_ → Claude calls `self_check`
- _"Help me phrase this feedback for leadership"_ → Claude calls `coach_communication`
- _"What packs are available?"_ → Claude calls `list_packs`

**Example workflows:**

```
You: I drafted a design doc for moving to a new database.
Can you review it with the oncall-future-you pack?

Claude: I'll review this from an on-call perspective.
[calls review_decision with pack=oncall-future-you]
[returns risks, failure modes, and recovery scenarios]
```

```
You: I'm concerned about our caching strategy. Can greybeard
help me phrase this feedback for our VP?

Claude: I'll help you draft constructive language.
[calls coach_communication with audience=leadership]
[returns suggested phrasing]
```

See [MCP Integration Guide](docs/guides/mcp.md) for detailed workflows, tips, and complete tool reference.

### Cursor / Zed / Other MCP Clients

Any client that supports the MCP stdio transport works. Point it at `greybeard mcp` (or use the full path from `which greybeard`).

See [MCP Integration Guide](docs/guides/mcp.md) for client-specific setup.

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

- **Content Packs**: Create a folder in `packs/<pack-name>/` with:
  - `<pack-name>.yaml` — The pack definition
  - `README.md` — Quick start and focus areas
  - `<PACK>-EXAMPLE.md` — A real-world scenario for testing

  Example: See `packs/staff-core/` for the structure.

- **Bug Reports**: [Open an issue](https://github.com/btotharye/greybeard/issues/new?template=bug_report.yml)
- **Feature Requests**: [Suggest a feature](https://github.com/btotharye/greybeard/issues/new?template=feature_request.yml)
- **Code**: See the [Contributing Guide](CONTRIBUTING.md) for setup instructions

**Community:**

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)
- [Documentation](https://greybeard.readthedocs.io/en/latest/contributing/)

If you build a public pack repo on GitHub, feel free to open an issue linking to it — we'll add it to a community registry.
