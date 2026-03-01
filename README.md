# Staff Review & Decision Assistant

> A CLI-first thinking tool that acts like a calm, experienced Staff / Principal engineer — helping you review decisions, systems, and tradeoffs before you ship them.

---

## Philosophy

This is **not** a linter. It won't yell at your variable names or enforce opinionated formatting.

This is a **thinking partner**. It models how Staff and Principal engineers reason about systems: failure modes, ownership, long-term cost, and the human impact of decisions. It asks the uncomfortable questions so your reviewer doesn't have to.

> "Would I be okay getting paged about this at 3am six months from now?"

---

## What It Does

- **Sanity-checks** architecture decisions and design docs
- **Surfaces** operational risks, ownership gaps, and maintenance burden
- **Coaches** you on how to communicate decisions to peers, teams, and leadership
- **Teaches** Staff-level reasoning through mentorship mode
- **Reviews** your own thinking before you share it with others

---

## Modes

| Mode | Description |
|------|-------------|
| `review` | Concise Staff-level review comments on a decision or diff |
| `mentor` | Explain the reasoning and thought process behind concerns |
| `coach` | Help phrase constructive comments or push back without blocking |
| `self-check` | Review your own decision before sharing it |

---

## Content Packs

Content packs define the perspective, tone, and heuristics used during review. They're plain YAML — easy to edit, extend, and eventually open-source.

### Built-in Packs

| Pack | Perspective | Focus |
|------|-------------|-------|
| `staff-core` | Staff Engineer | Ops, ownership, long-term cost |
| `oncall-future-you` | On-call engineer, 3am | Failure modes, pager noise, recovery |
| `mentor-mode` | Experienced mentor | Teaching, reasoning, growth |
| `solutions-architect` | Solutions Architect | Entity modeling, boundaries, fit-for-purpose |
| `idp-readiness` | Platform Engineering | IDP maturity, automation vs process |

### Custom Packs

Create a YAML file following the pack schema and pass it with `--pack path/to/my-pack.yaml`.

---

## Installation

```bash
pip install -e ".[dev]"
```

Requires an OpenAI API key:

```bash
export OPENAI_API_KEY=sk-...
# or create a .env file
```

---

## Usage

```bash
# Review a git diff through the staff-core lens
git diff main | staff-review analyze --mode review --pack staff-core

# Mentor mode with a repo context
staff-review analyze --repo . --mode mentor --pack oncall-future-you

# Self-check a decision you're about to share
staff-review self-check --context "We're migrating auth to a new provider mid-sprint"

# Get coaching on how to communicate a concern
staff-review coach --audience team --pack mentor-mode

# Pipe in a design doc
cat design-doc.md | staff-review analyze --mode review
```

---

## Primary Review Lenses

The assistant always reasons through four lenses:

1. **Operational impact** — failure modes, observability, deploy & rollback safety
2. **Long-term ownership** — who owns this in 6–12 months, tribal knowledge risk, unclear accountability
3. **On-call & human cost** — pager noise potential, manual recovery steps, 3am failure scenarios
4. **"Who pays for this later?"** — complexity tax, cognitive load, maintenance burden, coordination overhead

---

## Output Format

All output is structured Markdown:

```
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
*Facts vs Assumptions: [clearly separated]*
```

---

## Design Decisions & Assumptions

- **OpenAI backend**: GPT-4o is the default model. The system prompt is the primary control surface — content packs inject into it. You can swap the model with `--model`.
- **CLI-first**: No web UI, no server. Designed to be piped into and out of.
- **Stateless**: No conversation history by default. Add `--context` to provide prior context.
- **Pack format**: YAML was chosen over JSON for human editability. Packs are loaded at runtime and validated loosely — invalid fields are ignored, not errored.
- **Minimal deps**: click, openai, pyyaml, rich. That's it.

---

## Contributing

Content packs are the easiest contribution. Add a YAML file to `packs/`, follow the schema in an existing pack, and open a PR.
