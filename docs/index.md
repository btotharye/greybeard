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

**greybeard** is a CLI-first Staff-level review and decision assistant.

It channels the calm, battle-tested wisdom of a Staff / Principal engineer — helping you review decisions, systems, and tradeoffs before you ship them.

The greybeard has been paged at 3am. They've watched confident decisions become production incidents. They've seen "we'll clean it up later" last five years. They're not here to block you — they're here to make sure you've thought it through.

---

## What it does

- **Sanity-checks** architecture decisions and design docs
- **Surfaces** operational risks, ownership gaps, and maintenance burden
- **Coaches** you on how to communicate concerns to peers, teams, and leadership
- **Teaches** Staff-level reasoning through mentorship mode
- **Reviews** your own thinking before you share it with others
- **Integrates** into Claude Desktop, Cursor, Zed, and any MCP-compatible tool via the built-in MCP server

---

## Quick example

```bash
git diff main | greybeard analyze
```

```markdown
## Summary

This diff adds a background email notification task. Core logic is sound,
but there are operational concerns worth addressing before shipping.

## Key Risks

- **Silent failure mode**: Exceptions are caught and logged but there's no
  alert when the failure rate exceeds a threshold.
- **No retry logic**: Failed sends are permanently lost if SMTP is unavailable.
- **Unclear ownership**: No runbook or on-call assignment.

## Questions to Answer Before Proceeding

1. What is the acceptable failure rate, and how will you know when you exceed it?
2. Who owns this in the runbook?
3. Should failures be retried, and with what backoff?
```

---

## Installation

greybeard is available on [PyPI](https://pypi.org/project/greybeard/):

```bash
# Using uv (fast)
uv pip install greybeard

# Using pip
pip install greybeard
```

Then configure your LLM backend:

```bash
greybeard init
```

---

## Next steps

- [Installation Guide](getting-started/installation.md) — detailed setup, optional extras
- [Quick Start](getting-started/quickstart.md) — examples and common workflows
- [LLM Backends](guides/backends.md) — OpenAI, Claude, Ollama, LM Studio
- [Content Packs](guides/packs.md) — install community packs or write your own
- [MCP Integration](guides/mcp.md) — use greybeard inside Claude Desktop, Cursor, Zed
