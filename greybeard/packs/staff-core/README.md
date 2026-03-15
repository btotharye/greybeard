# Staff Core Pack

The core greybeard lens: a Staff Engineer's perspective on operational impact, ownership, and long-term cost.

## Quick Start

```bash
# Review a proposal, design doc, or decision
cat proposal.md | greybeard analyze --pack staff-core

# Use mentorship mode to understand the reasoning
cat proposal.md | greybeard analyze --pack staff-core --mode mentor
```

## Focus Areas

- **Operational Impact**: How will this system fail? Who gets paged?
- **Ownership Clarity**: Who is responsible for this in 6 months?
- **Long-term Cost**: What's the maintenance burden? Can a new team member understand it?
- **Human Burden**: What's the on-call and deployment story?

## When to Use This Pack

Use this pack to review architectural decisions, infrastructure changes, and system designs through the lens of operational reality — the perspective of someone who will be paged about this at 3am.

---

_Created as part of the Greybeard community packs initiative._
