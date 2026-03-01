# Quick Start

## 1. Configure your LLM

Run the interactive setup wizard:

```bash
greybeard init
```

This walks you through choosing a backend (OpenAI, Claude, Ollama, or LM Studio) and saves your preferences to `~/.greybeard/config.yaml`.

!!! tip "Local LLMs"
If you want to run completely free and offline, choose `ollama` or `lmstudio`.
See [LLM Backends](../guides/backends.md) for setup instructions.

## 2. Review a git diff

The most common use case — pipe a diff and get a Staff-level review:

```bash
git diff main | greybeard analyze
```

Change the perspective with a different mode or pack:

```bash
# More explanation of the reasoning (teaching mode)
git diff main | greybeard analyze --mode mentor

# From the 3am on-call perspective
git diff main | greybeard analyze --pack oncall-future-you
```

## 3. Self-check a decision

Before opening a PR or sharing a proposal, run it through greybeard:

```bash
greybeard self-check --context "We're migrating auth to a new provider mid-sprint"
```

You can also pipe in a draft document:

```bash
cat my-proposal.md | greybeard self-check --context "Proposal for replacing our job queue"
```

## 4. Get coaching on communication

When you have a concern but aren't sure how to raise it:

```bash
greybeard coach --audience leadership --context "I think we're shipping too fast and cutting QA"
```

## 5. Save the output

Use `--output` to save the review to a markdown file:

```bash
git diff main | greybeard analyze --output reviews/$(date +%Y-%m-%d)-review.md
```

## What's next

- [Configuration](configuration.md) — set your defaults
- [LLM Backends](../guides/backends.md) — all supported backends
- [Content Packs](../guides/packs.md) — install community packs or write your own
- [MCP Integration](../guides/mcp.md) — use greybeard inside Claude Desktop, Cursor, Zed
