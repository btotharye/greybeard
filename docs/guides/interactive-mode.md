# Interactive Mode Guide

Interactive mode transforms greybeard from a one-shot analysis tool into a **thinking partner** for iterative decision-making. After running an initial analysis, you can ask follow-up questions, refine your understanding, and explore alternatives—all within a single session.

## What is Interactive Mode?

Interactive mode is a REPL (Read-Eval-Print Loop) where:

1. You provide initial input (code diff, design doc, architecture proposal)
2. Greybeard runs its initial analysis using your chosen mode and content pack
3. You're dropped into a conversation prompt `>` where you can:
   - **Ask follow-up questions** about the analysis
   - **Refine the analysis** with additional context or clarification
   - **Explore alternatives** to see how different approaches compare
   - **Review conversation history** to stay on track
   - **Exit and save** whenever you're ready

The entire conversation is stateful—greybeard remembers your initial analysis and previous questions, building context as you go.

## When to Use Interactive Mode

### Perfect For:

- **Architecture reviews** — Ask probing questions about scalability, failure modes, ownership
- **Pre-proposal refinement** — Iterate on your thinking before sharing with your team
- **Decision-making with context** — Start with initial input, then layer in real-world constraints
- **Teaching/learning** — Use mentor mode to explore how experienced engineers reason
- **Sensitive discussions** — Self-check a concern in private before bringing it to leadership

### Less Ideal For:

- **Quick one-off reviews** — Skip interactive mode if you just want a quick opinion
- **Automated CI/CD** — Interactive mode requires human input; use standard analyze for pipelines
- **Mass analysis** — Processing many diffs at once is better without REPL

## Getting Started

### Basic Usage

```bash
# Review a design doc with interactive mode
cat design-doc.md | greybeard analyze --interactive

# Review a code diff with a specific pack
git diff main | greybeard analyze --interactive --pack oncall-future-you

# Use mentor mode for teaching/learning
git diff main | greybeard analyze --interactive --mode mentor

# Coach mode for phrasing feedback
greybeard coach --audience leadership --interactive
```

### Session Workflow

```
$ cat my-design.md | greybeard analyze --interactive --mode review

Running initial analysis...

[cyan]## Summary[/cyan]
Your proposed Redis caching layer would reduce database load by ~60% in the 
happy path, but introduces new operational complexity...

[green]## Key Risks[/green]
- Cache invalidation consistency across distributed team
- Debugging production cache misses becomes harder
- New on-call burden for Redis cluster monitoring...

[Interactive Review Session]
You can now:
  • Ask follow-up questions about the analysis
  • Refine the analysis with additional context
  • Explore alternative approaches

Type 'help' for commands or 'quit' to exit.

> What happens if Redis goes down during peak load?

[cyan]Answering follow-up...[/cyan]

Redis failure would cascade to the database. With current query patterns,
you'd see ~2-3s of latency spikes while cache warmed up...

> refine We're planning a 6-month rollout, starting with read-heavy endpoints

[cyan]Refining analysis...[/cyan]

With a phased rollout, the risks change significantly. Starting with read-only
operations limits blast radius...

> explore What if we used in-process memory caching instead of Redis?

[cyan]Exploring alternative...[/cyan]

In-process caching would reduce operational complexity but would break
down across your 5-instance deployment...

> history

[bold]Conversation History[/bold]

[ASSISTANT]
Your proposed Redis caching layer...

[USER]
What happens if Redis goes down during peak load?

[ASSISTANT]
Redis failure would cascade...

> quit

Goodbye!
```

## Interactive Commands

You can type any of these commands at the `>` prompt:

### Ask Follow-up Questions

Just type any question directly:

```
> What are the biggest operational risks here?
> How would this change if we had 100 engineers instead of 10?
> Does this work for our current infrastructure?
```

You can also use the explicit `ask` prefix (optional):

```
> ask What's the failure scenario I should worry about most?
```

### Refine Analysis

When you have additional context or want to adjust assumptions:

```
> refine We're moving to serverless architecture, which changes database access patterns

> refine The team has deep Kubernetes experience but no Go expertise

> refine We're using AWS, not Terraform, so infrastructure-as-code isn't available
```

### Explore Alternatives

Compare your proposal against alternatives:

```
> explore What if we rebuilt this in Go instead of Python?

> explore How would this look with event sourcing?

> explore What's the minimal viable version of this?
```

### View Conversation History

See the full conversation thread:

```
> history
```

Shows all user questions and greybeard responses in chronological order. Useful when you've been chatting for a while and want context.

### Reset Conversation

Clear the conversation history (but keep the initial analysis):

```
> reset
```

This is useful if you've wandered off-topic and want to start fresh with follow-ups.

### Show Help

See command reference:

```
> help
```

### Exit Session

Leave the REPL:

```
> quit
> exit
```

Or press `Ctrl+C` or `Ctrl+D`.

## Practical Examples

### Example 1: Architecture Review with Risks

**Scenario:** You've designed a microservices migration and want greybeard to probe for risks before you present to leadership.

```bash
$ cat migration-plan.md | greybeard analyze --interactive --pack oncall-future-you --mode mentor

# Initial analysis identifies risks around:
# - distributed transaction handling
# - observability across services
# - team coordination overhead

> refine Our team has strong observability practices; we use Datadog everywhere

# Greybeard acknowledges and adjusts risk scoring for observability

> explore What if we kept the monolith for user auth and only migrated read-heavy services?

# Explores reduced scope, lower coordination overhead, but different risks (coupling)

> ask What's the biggest surprise we'll hit in production six months from now?

# Greybeard considers team maturity, the specific trade-offs you've made

> quit
```

**Why interactive mode shines:** Each refinement and alternative builds on context from prior turns. By the end, you have a much more nuanced understanding of what could go wrong—and you're more confident in your proposal.

### Example 2: Pre-Leadership Discussion Self-Check

**Scenario:** You're concerned about shipping a feature before integration testing is done. You want to articulate your concern clearly.

```bash
$ greybeard coach --audience leadership --interactive \
    --context "We're shipping user auth changes without full integration tests"

# Initial coaching provides language for framing concern constructively

> refine We have unit tests at 90% coverage and manual testing of critical flows

# Refines the concern—it's not "no testing," it's "gaps in specific test types"

> explore What if we shipped with a kill switch and could roll back in <5 minutes?

# Explores how risk tolerance changes with operational safety

> ask How do I explain this to non-technical stakeholders?

# Greybeard suggests framing around "unknown unknowns" and risk tolerance

> quit
```

**Why interactive mode shines:** You end the session with a clear, nuanced message tailored to your audience—not just a generic critique.

### Example 3: Learning/Teaching with Mentor Mode

**Scenario:** A junior engineer wrote some code. You want to understand how a staff engineer would reason about it, and use that to teach.

```bash
$ cat junior-design.md | greybeard analyze --interactive --mode mentor --pack staff-core

# Mentor mode explains the reasoning: what looks good, what to consider, why

> ask Why does ownership matter so much in this decision?

# Greybeard explains the long-term maintenance and escalation implications

> ask How would you approach testing this at scale?

# Mentorship on test strategy for systems that grow

> ask What would change if we had to support 10x more users?

# Explores scalability thinking without being prescriptive

> quit
```

**Why interactive mode shines:** It's a dialogue, not a monologue. You can ask "why" repeatedly until you truly understand the thinking, not just the conclusion.

## Tips & Tricks

### Keep Context in Mind

Greybeard maintains conversation history automatically. However, if your session gets long (>15-20 messages), older context gets trimmed to avoid token bloat. If you need to reference something earlier:

```
> history       # See what we've discussed
```

### Combine with Repo Context

For better analysis, include your actual codebase:

```bash
git diff main | greybeard analyze --interactive --repo . --context "microservices migration"
```

The `--repo` flag gives greybeard access to your README, git history, and structure—making follow-ups more grounded.

### Use Explicit Modes for Different Purposes

- **`review`** (default) — Fast, direct staff-level assessment
- **`mentor`** — Teaching/learning; greybeard explains reasoning
- **`coach`** — Phrasing feedback for specific audiences
- **`self-check`** — Personal reflection before sharing

```bash
# Review for speed
git diff | greybeard analyze --interactive --mode review

# Learn why
git diff | greybeard analyze --interactive --mode mentor

# Prepare for tough conversation
git diff | greybeard analyze --interactive --mode coach --audience leadership
```

### Save Your Session

Interactive mode prints to stdout. You can capture it:

```bash
# Redirect to a file
cat design.md | greybeard analyze --interactive --pack staff-core > session-notes.md

# Or use script (captures full output including formatting)
script session.txt
cat design.md | greybeard analyze --interactive
exit
```

### Iterate on Multiple Alternatives

If you're deciding between approaches:

```bash
> explore Approach A: Use message queue for async work

> explore Approach B: Use cron jobs with retries

> explore Approach C: Use serverless functions (Lambda)

# Each gives you a detailed comparison within the same session
```

### Combine with MCP for IDE Integration

If you're using Claude Desktop, Cursor, or Zed with greybeard's MCP server:

```
You: "I drafted an architecture decision. Can you review it with interactive mode?"

Claude: [opens interactive session]
You: "What about failure recovery?"
Claude: [asks greybeard, streams response]
```

## Architecture & Under the Hood

Interactive mode works through the `InteractiveSession` class (`greybeard/interactive.py`):

1. **Initial Analysis** — Runs through normal `run_review()`, stores result
2. **Conversation History** — Maintains list of (role, content) pairs
3. **Follow-up Questions** — Reconstructs context (initial analysis + recent history) and calls LLM with enriched prompt
4. **Refinements** — Similar to follow-ups, but explicitly marked as "refine" context
5. **Alternatives** — Asks LLM to compare new approach against original analysis

All LLM calls stream to the terminal for instant feedback. The session is stateless (no database)—all context lives in memory during your session.

### System Prompts

Follow-up questions use a refined system prompt that includes:

- Your pack's perspective and heuristics (same as initial analysis)
- Reference to your initial analysis
- Recent conversation history (last 10 messages, to avoid token bloat)
- Clear instruction to build on prior context

This keeps answers coherent and grounded.

## Troubleshooting

### "No initial analysis. Call run_initial_analysis() first."

You're trying to ask a follow-up before running the initial analysis. This shouldn't happen in normal CLI usage—just make sure you're using `--interactive` flag.

### LLM Errors in Follow-ups

If you get API errors during a follow-up:

- Check your API key is still valid (`export ANTHROPIC_API_KEY=...`)
- If using local (Ollama/LM Studio), make sure the server is still running
- Re-run `greybeard config show` to verify configuration

### Session Feels Slow

Interactive mode streams responses, so you see output as it arrives. If streams feel slow:

- Check your network (especially for cloud APIs)
- Verify your LLM backend isn't overloaded
- Switch to a faster model: `greybeard config set llm.model gpt-4o-mini` (OpenAI) or `llama2` (Ollama)

### Can't Remember What We Discussed?

Use the `history` command to see full conversation. Or:

```bash
# Save to file before quitting
> history > session-summary.txt
```

## Advanced: Using Interactive Mode Programmatically

If you're building tools on top of greybeard, you can use `InteractiveSession` directly:

```python
from greybeard.config import GreybeardConfig
from greybeard.interactive import InteractiveSession
from greybeard.models import ContentPack

config = GreybeardConfig.from_file("~/.greybeard/config.yaml")
pack = ContentPack.from_yaml("path/to/pack.yaml")

session = InteractiveSession(
    mode="review",
    pack=pack,
    config=config,
    model_override="gpt-4o"
)

# Run initial analysis
session.run_initial_analysis("your code diff or design doc here")

# Ask follow-ups programmatically
response = session.ask_followup("What are the biggest risks?")
print(response)

# Explore alternatives
alt_response = session.explore_alternative("What if we used X instead?")
print(alt_response)

# Access full conversation
history = session.get_conversation_history()
for turn in history:
    print(f"{turn['role']}: {turn['content']}")
```

See `greybeard/interactive.py` for the full API.

---

## See Also

- [CLI Reference](../reference/cli.md) — All `greybeard` commands
- [Content Packs Guide](packs.md) — Choosing and building packs
- [Modes & Philosophy](modes.md) — Understanding review, mentor, coach, self-check
- [MCP Integration](mcp.md) — Using interactive mode in Claude Desktop, Cursor, Zed
