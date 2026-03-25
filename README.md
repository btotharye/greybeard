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

## Features

### Core Reviews

- **Architecture Decisions** — Sanity-check design docs and proposals
- **Code Diffs** — Review changes through a Staff-engineer lens
- **Tradeoff Analysis** — Surface operational risks, ownership gaps, maintenance burden
- **Mentorship** — Learn how experienced engineers think through problems
- **Communication Coaching** — Phrase feedback for specific audiences

### Modes

| Mode           | Purpose                                                   |
| -------------- | --------------------------------------------------------- |
| **review**     | Fast, direct Staff-level assessment (default)             |
| **mentor**     | Explain reasoning and thought process behind concerns     |
| **coach**      | Help phrase constructive feedback for a specific audience |
| **self-check** | Review your own thinking before sharing with others       |

### Interactive Mode

After running an analysis, ask follow-up questions, refine with additional context, and explore alternatives—all in a single conversation.

```bash
git diff main | greybeard analyze --interactive

> What happens if this fails in production?
> refine We're doing a 6-month rollout
> explore What if we used event sourcing instead?
```

See the [Interactive Mode Guide](docs/guides/interactive-mode.md) for workflows, tips, and examples.

### Content Packs

10+ built-in perspectives (staff engineer, on-call, security, platform engineering, startup pragmatist, etc.). Write custom YAML packs for your team's values.

### IDE & Tool Integration

Runs as an MCP server compatible with Claude Desktop, Cursor, Zed, and any MCP-compatible tool. Bring greybeard into your IDE.

### Multi-Backend LLM Support

Works with OpenAI, Anthropic, Ollama, or LM Studio. Configure once, use anywhere.

---

## Quick Start

### 1. Install

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
```

### 2. Configure

```bash
greybeard init          # Interactive setup wizard
greybeard config show   # See what's configured
```

This creates `~/.greybeard/config.yaml` with your LLM backend choice.

### 3. Run Your First Review

```bash
# Review a code diff
git diff main | greybeard analyze

# Review with a specific mode and pack
git diff main | greybeard analyze --mode mentor --pack oncall-future-you

# Run a self-check on a design decision
greybeard self-check --context "We're migrating auth mid-sprint"

# Get coaching on how to phrase feedback
greybeard coach --audience leadership --context "I think we're moving too fast"
```

### 4. Try Interactive Mode

```bash
# Start an interactive REPL after initial analysis
cat design-doc.md | greybeard analyze --interactive

# Then ask follow-up questions, refine with context, explore alternatives
> What's the biggest operational risk?
> refine We have strong on-call practices with Datadog everywhere
> explore What if we kept the monolith for auth?
```

📚 **Full Documentation** — [docs](docs/) and [readthedocs](https://greybeard.readthedocs.io)

---

## Usage Examples

### Review a Git Diff

The simplest way to get feedback:

```bash
# Use default mode (review) and default pack from config
git diff main | greybeard analyze

# Or specify both
git diff main | greybeard analyze --mode mentor --pack staff-core

# Save output to a file
git diff main | greybeard analyze --output review.md
```

### Interactive Iteration

Ask follow-up questions and refine your thinking:

```bash
cat my-design.md | greybeard analyze --interactive --pack oncall-future-you

Running initial analysis...

[Initial analysis output]

Interactive Review Session. Type 'help' for commands or 'quit' to exit.

> What about failure recovery?
[greybeard responds with recovery implications]

> refine We're rolling out gradually over 6 months
[greybeard adjusts analysis based on timeline]

> explore What if we used event sourcing?
[greybeard compares to original approach]

> quit
```

### Self-Check Before Sharing

Review your own decision privately before presenting:

```bash
greybeard self-check --context "We're caching heavily with Redis"

# Returns thoughtful review of your assumptions and risks
```

### Coach Mode for Leadership Conversations

Get help phrasing a concern constructively:

```bash
greybeard coach --audience leadership --interactive \
  --context "I'm worried we're shipping without enough integration testing"

# Initial response frames the concern clearly
# Then ask follow-ups to refine your message
> What if we added a kill switch?
> How do I explain this to non-technical stakeholders?
```

### Include Repo Context

For better analysis, give greybeard your project structure:

```bash
git diff main | greybeard analyze --repo . --context "microservices migration"

# Greybeard has access to README, git history, structure
# Responses are more grounded in your actual setup
```

### Review with a Custom Pack

Create a `.yaml` file for your team's values and review with it:

```bash
cat design-doc.md | greybeard analyze --pack ./my-team-pack.yaml
```

See [Custom Packs](#custom-packs) below and [Pack Schema](docs/reference/pack-schema.md) for format.

---

## Content Packs

Content packs define the perspective, tone, and heuristics used during review. They're plain YAML—human-editable, version-controllable, shareable.

### Built-in Packs

| Pack                  | Perspective           | Focus                                             |
| --------------------- | --------------------- | ------------------------------------------------- |
| `staff-core`          | Staff Engineer        | Ops, ownership, long-term cost                    |
| `oncall-future-you`   | On-call engineer, 3am | Failure modes, pager noise, recovery              |
| `mentor-mode`         | Experienced mentor    | Teaching, reasoning, growth                       |
| `solutions-architect` | Solutions Architect   | Entity modeling, boundaries, fit-for-purpose      |
| `platform-eng`        | Platform Engineer     | DX, abstractions, tool maturity, scaling          |
| `security-reviewer`   | AppSec Engineer       | Auth, injection, secrets, overprivileged access   |
| `startup-pragmatist`  | Pragmatic Engineer    | Complexity vs stage, reversibility, scope         |
| `incident-postmortem` | SRE / On-call         | Blameless analysis, root cause, action items      |
| `idp-readiness`       | Platform Engineering  | IDP maturity, automation vs process               |
| `data-migrations`     | Migration Expert      | Lock safety, zero-downtime, rollback, performance |

### Testing Packs

Each built-in pack includes an example file to test with:

```bash
# Test a pack against its example
cat packs/staff-core/STAFF-CORE-EXAMPLE.md | greybeard analyze --pack staff-core

# Try different modes
cat packs/mentor-mode/MENTOR-MODE-EXAMPLE.md | greybeard analyze --pack mentor-mode --mode mentor

# See all examples
ls packs/*-EXAMPLE.md
```

### Custom Packs

Create a `.yaml` file with your own perspective:

```yaml
name: my-team-pack
perspective: "Platform engineer at a Series B startup"
tone: "pragmatic, balancing shipping speed with sustainability"
focus_areas:
  - "team capacity vs scope"
  - "infrastructure complexity"
  - "operational readiness"
heuristics:
  - "ask: can we do this in 2 weeks?"
  - "what's the blast radius if this breaks?"
  - "does the team have context?"
communication_style: "clear, direct, assume good intent"
description: "Reviews for our team's operating philosophy"
```

Then use it:

```bash
cat design-doc.md | greybeard analyze --pack ./my-team-pack.yaml
```

### Install External Packs

Share and install packs from GitHub repos:

```bash
# Install all packs from a public repo
greybeard pack install github:someone/their-packs

# Install a single pack
greybeard pack install github:owner/repo/packs/my-pack.yaml

# List installed packs
greybeard pack list

# Remove a source
greybeard pack remove owner__repo
```

Installed packs are cached in `~/.greybeard/packs/` and work exactly like built-ins.

### Publishing a Pack

Create a public GitHub repo with a `packs/` folder containing `.yaml` files. Anyone can install it:

```bash
greybeard pack install github:your-handle/your-pack-repo
```

See [Packs Guide](docs/guides/packs.md) for detailed pack creation and best practices.

---

## LLM Backends

greybeard works with any LLM backend. Configure once with `greybeard init`:

| Backend     | How           | What You Need                                      |
| ----------- | ------------- | -------------------------------------------------- |
| `openai`    | OpenAI API    | `OPENAI_API_KEY`                                   |
| `anthropic` | Anthropic API | `ANTHROPIC_API_KEY` + `greybeard[anthropic]` extra |
| `ollama`    | Local (free)  | [Ollama](https://ollama.ai) running locally        |
| `lmstudio`  | Local (free)  | [LM Studio](https://lmstudio.ai) server running    |

### Configure Your Backend

```bash
# Interactive setup
greybeard init

# Or set directly
greybeard config set llm.backend anthropic
greybeard config set llm.model claude-sonnet-4-6

greybeard config show   # Verify
```

Config lives at `~/.greybeard/config.yaml`.

See [Backends Guide](docs/guides/backends.md) for detailed setup for each backend.

---

## IDE & Tool Integration (MCP)

Run greybeard as an MCP server in Claude Desktop, Cursor, Zed, or other MCP-compatible tools.

### Claude Desktop

1. Install greybeard:

```bash
uv pip install greybeard
```

2. Get the greybeard path:

```bash
which greybeard
```

3. Edit Claude config:
   - **macOS:** `~/Library/Application\ Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add:

```json
{
  "mcpServers": {
    "greybeard": {
      "command": "/path/to/greybeard",
      "args": ["mcp"]
    }
  }
}
```

4. Restart Claude Desktop. Now you can:

```
You: I drafted an architecture decision. Can you review it?

Claude: I'll review this with greybeard.
[calls greybeard review tool]
[returns analysis with risks, tradeoffs, questions]
```

### Other Tools

Cursor, Zed, and any MCP-compatible tool work the same way. Point them at `greybeard mcp` (or use the full path from `which greybeard`).

See [MCP Integration Guide](docs/guides/mcp.md) for detailed setup and workflow examples.

---

## GitHub Actions Integration

Automatically review pull requests with greybeard using GitHub Actions. Get Staff-engineer-level feedback on demand — triggered by a label so you control when (and what) it costs.

### Quick Start

1. Add the workflow file to your repo:

```bash
mkdir -p .github/workflows
curl -L https://raw.githubusercontent.com/btotharye/greybeard/main/.github/workflows/greybeard-review.yml \
  -o .github/workflows/greybeard-review.yml
```

2. Set up GitHub Secrets:
   - **`ANTHROPIC_API_KEY`** — your Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))
   - **`GITHUB_TOKEN`** — auto-provided by GitHub Actions, no setup needed

3. Create the `greybeard-review` label in your repo:
   - Go to your repo → **Issues** → **Labels** → **New label**
   - Name: `greybeard-review`, color: `#6f42c1` (purple) 🟣

4. To trigger a review: add the `greybeard-review` label to any PR.

> **Manual trigger:** You can also run it on demand from **Actions → Greybeard Code Review → Run workflow**.

### How It Works

The workflow runs three parallel review perspectives when triggered:

| Pack                | Focus                                                  | Icon |
| ------------------- | ------------------------------------------------------ | ---- |
| `staff-core`        | Overall engineering quality, architecture, readability | 🧙   |
| `oncall-future-you` | Operational risk, runbooks, alerting, rollback         | 📟   |
| `security-reviewer` | Security vulnerabilities, auth, data exposure          | 🔒   |

Each pack posts its own PR comment. Comments are updated (not duplicated) on re-runs.

### Workflow Features

- ✅ **Label-triggered** — only runs when you explicitly ask for it (saves cost)
- ✅ **Manual dispatch** — run from the Actions tab any time
- ✅ **Three parallel perspectives** — staff, oncall, security in one run
- ✅ **PR comments** with findings — updated on re-run, not duplicated
- ✅ **GitHub Check status** for branch protection rules
- ✅ **Diff truncation** — automatically stays within LLM token limits
- ✅ **Blocking issue detection** — marks the check as failed if critical patterns found

### Cost Management

The workflow uses **Claude Haiku** by default — the fastest and cheapest Anthropic model (~$0.05–0.20 per full 3-pack review vs ~$1+ for Sonnet).

**Label-based triggering is the main cost control** — reviews only run when you add the label. No surprise charges from every commit push.

| Model                                  | Cost (input/output per MTok) | Best for                                 |
| -------------------------------------- | ---------------------------- | ---------------------------------------- |
| `claude-haiku-4-5-20251001` ✅ default | $1 / $5                      | Most PRs — fast, cheap, solid            |
| `claude-sonnet-4-6`                    | $3 / $15                     | High-stakes PRs needing deeper analysis  |
| `claude-opus-4-6`                      | $5 / $25                     | Architecture reviews, complex migrations |

To use a more powerful model for a specific repo, update the workflow step:

```yaml
- name: Configure Anthropic backend
  run: |
    greybeard config set llm.backend anthropic
    greybeard config set llm.model claude-sonnet-4-6   # or claude-opus-4-6
```

### Required Permissions

The workflow requires these permissions (already set in the bundled workflow file):

```yaml
permissions:
  contents: read
  pull-requests: write # post PR comments
  checks: write # set check status for branch protection
```

### Configuration

Optional GitHub Variables (set in repo Settings → Variables):

| Variable                   | Default | Description                                      |
| -------------------------- | ------- | ------------------------------------------------ |
| `GREYBEARD_RISK_THRESHOLD` | `high`  | Block threshold: `none`, `low`, `medium`, `high` |

### Troubleshooting

**Q: The workflow isn't triggering when I add the label**

- Confirm the label name is exactly `greybeard-review` (case-sensitive)
- Check that the workflow file is on your default branch (label events only trigger from there)

**Q: `404 - model not found` error**

- The Anthropic model name is wrong. Check [Anthropic's model docs](https://docs.anthropic.com/en/docs/about-claude/models/overview) for current names.

**Q: Review comments aren't appearing**

- Verify `ANTHROPIC_API_KEY` is set in repo Secrets
- Check the Actions log for API errors

**Q: Want to run for every PR automatically?**

- Change the trigger in the workflow to `types: [opened, synchronize, reopened, ready_for_review]`
- Be aware this will charge your API key on every push to an open PR

See [GitHub Actions Integration Guide](docs/guides/github-actions.md) for more examples and troubleshooting.

---

## Pre-commit Hook Integration

Run greybeard checks before committing—fail on risk gates, require approvals on sensitive changes.

### Quick Start

1. Install pre-commit:

```bash
pip install pre-commit
```

2. Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/btotharye/greybeard
    rev: main
    hooks:
      - id: greybeard
        stages: [commit]
```

3. Install hooks:

```bash
pre-commit install
```

### Risk Gates

Fail commits on sensitive paths:

```yaml
# .greybeard-precommit.yaml
enabled: true
default_pack: staff-core
fail_on_concerns: critical

risk_gates:
  - name: "infra-changes"
    patterns: ["infra/*", "terraform/*"]
    fail_on_concerns: critical
    required_packs: ["platform-eng"]
    skip_if_branch: ["hotfix/*"] # Skip on urgent branches

  - name: "auth-changes"
    patterns: ["auth/*", "security/*"]
    fail_on_concerns: high
    required_packs: ["security-reviewer"]
```

Then commit normally—greybeard will check before the commit goes through.

See [Pre-commit Integration Guide](docs/guides/precommit.md) for full configuration and examples.

---

## Advanced Topics

### Building Custom Agents

Use the greybeard agent framework to build specialized decision-making tools:

```python
from greybeard.common import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="my-agent", description="...")

    def run(self, user_input: str) -> dict:
        # Use research, interview, documentation capabilities
        context = self.research.gather_file_context("file.txt")
        response = self.llm.call(...)
        return {"result": response}
```

**Available Capabilities:**

- `research` — Gather context from files, directories, git history
- `interview` — Multi-turn conversations with users
- `llm` — Unified interface to all LLM backends
- `documentation` — Format output as Markdown, JSON, YAML

See [Creating Agents Guide](docs/guides/creating_agents.md) and the [template](examples/custom_agent_template.py).

**Planned Specialized Agents:**

- **Architecture Agent** (v1.1) — Document architectural decisions (ADRs)
- **SLO Agent** (v1.2) — Analyze systems and recommend SLOs
- **Tech Debt Agent** (v1.3) — Scan code and prioritize technical debt

### Output Formatting

All output is structured Markdown:

```markdown
## Summary

Your decision summary...

## Key Risks

- Risk 1
- Risk 2

## Tradeoffs

...

## Questions to Answer Before Proceeding

...

## Suggested Communication Language

...

_Assumptions made: ..._
```

Save with `--output filename.md`. See [Output Guide](docs/guides/output.md).

---

## Development & Contributing

### Quick Dev Setup

```bash
git clone https://github.com/btotharye/greybeard.git
cd greybeard

# Using Makefile (easiest)
make install-dev
make test
make help                      # see all commands

# Or using uv directly
uv pip install -e ".[dev]"
uv run pytest
```

### Ways to Contribute

**Content Packs** (easiest, high value)

- Create a perspective your team or community needs
- See [Packs Guide](docs/guides/packs.md)

**Custom Agents**

- Build specialized tools on top of the framework
- See [Creating Agents Guide](docs/guides/creating_agents.md)

**Bug Reports & Features**

- [Report a bug](https://github.com/btotharye/greybeard/issues/new?template=bug_report.yml)
- [Suggest a feature](https://github.com/btotharye/greybeard/issues/new?template=feature_request.yml)

**Code Contributions**

- See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, testing, style
- Follow [Code of Conduct](CODE_OF_CONDUCT.md)

**Community Packs**

- Build a pack repo and share it
- Open an issue linking to it—we'll feature it

---

## Design Philosophy

- **Multi-backend** — OpenAI, Anthropic, Ollama, LM Studio. Choose your tool.
- **CLI-first** — No web UI. Pipe in, pipe out. Unix philosophy.
- **Stateless** — No conversation history by default. Add `--context` for prior context, or use `--interactive` for stateful REPL.
- **Pack format** — YAML for human editability and version control.
- **MCP stdio** — Simplest, most compatible tool integration.
- **Minimal dependencies** — `click`, `pyyaml`, `rich`, `python-dotenv`, optional `openai` / `anthropic`.

---

## Documentation

- **[Getting Started](docs/getting-started/)** — Installation, setup, first steps
- **[Guides](docs/guides/)** — Interactive mode, packs, agents, backends, MCP, output
- **[Reference](docs/reference/)** — CLI, config, pack schema
- **[Contributing](CONTRIBUTING.md)** — How to contribute
- **[Full Docs](https://greybeard.readthedocs.io)** — Hosted documentation

---

## License

[MIT License](LICENSE) — Use freely, modify, and distribute.

---

## Questions?

- 📚 Check the [docs](https://greybeard.readthedocs.io)
- 💬 [GitHub Discussions](https://github.com/btotharye/greybeard/discussions)
- 🐛 [Open an issue](https://github.com/btotharye/greybeard/issues)

---

_"The greybeard isn't here to block you. They're here to make sure you've thought it through."_
