# MCP Integration

greybeard includes a built-in [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server. This lets you use greybeard's review tools directly inside Claude Desktop, Cursor, Zed, and any other MCP-compatible client.

---

## How it works

Running `greybeard mcp` starts a stdio JSON-RPC server that exposes greybeard's tools via the MCP protocol. Your LLM client connects to it locally — no network exposure, no external servers.

---

## Available tools

| Tool                  | Description                                         |
| --------------------- | --------------------------------------------------- |
| `review_decision`     | Staff-level review of a decision, diff, or document |
| `self_check`          | Review your own proposal before sharing it          |
| `coach_communication` | Get suggested language for a specific audience      |
| `list_packs`          | List available content packs                        |

---

## Claude Desktop

### Setup

1. **Verify greybeard is installed:**

```bash
greybeard --version
```

If this fails, [install greybeard first](../getting-started/installation.md).

2. **Find your greybeard installation path:**

This is required for Claude Desktop to find the command. Run:

```bash
which greybeard
```

This will output something like:

- `/usr/local/bin/greybeard` (if installed via Homebrew)
- `/Users/you/.pyenv/shims/greybeard` (if using pyenv)
- `/Users/you/.venv/bin/greybeard` (if in a virtual environment)
- `/opt/homebrew/bin/greybeard` (on Apple Silicon with Homebrew)

**Save this path — you'll need it in the next step.**

3. **Edit Claude Desktop config:**

Open your config file:

- **macOS:** `~/Library/Application\ Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add (or update) the `mcpServers` section with the full path to greybeard:

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

Replace `/Users/you/.pyenv/shims/greybeard` with the path from step 2.

4. **Save and restart Claude Desktop:**

Close Claude Desktop completely, then reopen it. You should see the greybeard icon light up in the MCP status indicator (lower left corner).

### Using greybeard in Claude

Once connected, the greybeard tools become available to Claude. You don't need special syntax — just ask Claude naturally, and it will choose the right tool.

#### Quick examples

```
"Can you review this architecture decision?"
Claude will call review_decision with your text.

"Help me phrase this feedback for leadership"
Claude will call coach_communication with the right audience.

"Self-check my proposal before I send it to the team"
Claude will call self_check.

"What packs are available?"
Claude will call list_packs.
```

#### Real-world workflows

**Scenario 1: Review a design doc before sharing**

```
You: I just drafted a design doc for moving auth to a new provider.
Can you review it with greybeard using the oncall-future-you pack?

[You paste the doc]

Claude: I'll review this using the oncall-future-you perspective.
[calls review_decision with mode=review, pack=oncall-future-you]
```

Claude will return a Staff-level review with:

- Failure modes (what could go wrong at 3am?)
- Recovery scenarios
- Questions to answer before proceeding

**Scenario 2: Get help communicating a concern**

```
You: I'm concerned about our caching strategy but I'm not sure how
to bring it up with the VP. Can greybeard help me phrase this?

Claude: I'll help you draft language for leadership.
[calls coach_communication with audience=leadership]
```

You get suggested language that frames the concern constructively.

**Scenario 3: Self-check your thinking**

```
You: Before I propose removing our feature flags, can I
self-check this decision with the mentor-mode pack?

Claude: I'll review your thinking from a mentoring perspective.
[calls self_check with pack=mentor-mode]
```

You get back the reasoning behind the concerns, not just a list.

**Scenario 4: Review a Git diff**

```
You: Here's a diff we're about to merge.
[paste git diff]

Can greybeard review it with the security-reviewer pack?

Claude: I'll review this from an AppSec perspective.
[calls review_decision with the diff, pack=security-reviewer]
```

#### How Claude presents the tools

When Claude uses a greybeard tool, you'll see:

- The tool name and inputs it's sending
- The review output in structured Markdown
- Follow-up analysis or next steps Claude provides

#### Combining with Claude's reasoning

Claude can also combine greybeard reviews with its own analysis:

```
You: Review this proposal with greybeard, then tell me
which of the risks are most important for our context.

Claude:
1. [calls review_decision, gets risks/tradeoffs]
2. Based on what I know about your team from our conversation,
   here are the top 3 risks...
```

#### Tips for best results

- **Be specific:** Include context about what you're deciding
  - "We're a Series B startup with 50 engineers"
  - "This is our primary revenue service"
  - "We have oncall coverage 9-5 only"

- **Use pack names:** Ask for specific packs when you have a clear perspective in mind
  - Review with `oncall-future-you` for production safety
  - Use `startup-pragmatist` for early-stage decisions
  - Try `security-reviewer` for security-sensitive changes

- **Combine tools:** Get multiple perspectives if it's a big decision
  - "First review with staff-core, then with oncall-future-you"

- **Use the output:** Copy reviews into your decision docs or design docs
  - Greybeard output is always Markdown and copy-paste ready

### Troubleshooting

**Problem:** Claude says "MCP server failed to connect"

- **Check the path:** Run `which greybeard` and verify it matches in your config file
- **Verify greybeard works:** Run `greybeard packs` in a terminal — should list available packs
- **Check the config file:** Make sure the JSON is valid (no missing commas or quotes)
- **Check logs:** Look at `~/Library/Logs/Claude/mcp.log` for error details

**Problem:** Claude connects but tools don't appear

- **Restart Claude:** Close and reopen completely
- **Check stderr:** Run `greybeard mcp` in a terminal — it should print `[greybeard-mcp] greybeard MCP server starting` with no errors

**Problem:** "Module not found" or Python errors

- **Check Python version:** `python --version` should be 3.11+
- **Reinstall:** `pip install --upgrade greybeard`
- **Check venv:** If using a virtual environment, the path in the config should point to its Python

**Problem:** Tools work but reviews are slow or fail

- **Check LLM backend:** Run `greybeard config show` to see which LLM backend is configured
- **Test the backend:** Run `greybeard analyze --pack staff-core` via CLI to test outside MCP
- **For Ollama users:** Make sure `ollama serve` is running

---

## Cursor

In your Cursor `settings.json` (or through the settings UI):

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

Use the full path from `which greybeard`.

---

## Zed

In your Zed `settings.json`:

```json
{
  "assistant": {
    "mcp_servers": {
      "greybeard": {
        "command": "/Users/you/.pyenv/shims/greybeard",
        "args": ["mcp"]
      }
    }
  }
}
```

Use the full path from `which greybeard`.

---

## Other MCP clients

Any client that supports the MCP stdio transport works. Point it at `greybeard mcp`. The server speaks JSON-RPC 2.0 over stdin/stdout.

---

## Tool reference

### `review_decision`

```json
{
  "input": "string (required) — diff, design doc, ADR, etc.",
  "context": "string (optional) — additional context",
  "mode": "review | mentor | self-check (default: review)",
  "pack": "string (default: staff-core)"
}
```

### `self_check`

```json
{
  "context": "string (required) — your decision or proposal",
  "input": "string (optional) — supporting document",
  "pack": "string (default: staff-core)"
}
```

### `coach_communication`

```json
{
  "concern": "string (required) — what you need to communicate",
  "audience": "team | peers | leadership | customer (required)",
  "pack": "string (default: mentor-mode)"
}
```

### `list_packs`

No parameters. Returns a markdown list of all available packs.

---

## LLM backend for MCP

The MCP server uses whatever backend you've configured in `~/.greybeard/config.yaml`. This is separate from the LLM the MCP client itself uses.

For example: Claude Desktop uses Claude for its own reasoning, but when it calls `review_decision`, greybeard uses your configured backend (e.g. Ollama, GPT-4o, etc.) to generate the review.
