# Platform Engineering Pack

A thinking framework for platform engineering decisions.

## What It Does

Evaluates decisions through the lens of a platform engineer:

- Abstraction layer design
- Developer experience impact
- Tool maturity vs complexity
- Team scaling and knowledge transfer
- Self-service vs gating tradeoffs
- Adoption metrics and feedback loops

## When to Use It

- Deciding whether to build an abstraction or platform feature
- Evaluating new tools or infrastructure changes
- Reviewing architectural decisions that affect multiple teams
- Training new platform engineers on "how we think"

## Quick Start

```bash
# Review a proposal or decision doc
cat proposal.md | greybeard analyze --pack platform-eng.yaml

# Use mentorship mode to understand the reasoning
cat proposal.md | greybeard analyze --pack platform-eng.yaml --mode mentor
```
