# On-Call Future You Pack

The perspective of the on-call engineer who will inherit this at 3am — brutally honest about operational readiness.

## Quick Start

```bash
# Review operational readiness of a system or change
cat design.md | greybeard analyze --pack oncall-future-you

# Use mentorship mode to learn the on-call thinking
cat design.md | greybeard analyze --pack oncall-future-you --mode mentor
```

## Focus Areas

- **Failure Modes**: What are the realistic failure modes? How obvious is the problem when it happens?
- **Runbook Completeness**: Is there a runbook? Is it findable at 3am?
- **Observability**: Can you tell the difference between degraded and down?
- **Recovery**: How long does rollback take? How many manual steps are there?

## When to Use This Pack

Use this pack before shipping changes that will impact reliability — designs, monitoring strategies, incident response procedures, and recovery automation.

---

_Created as part of the Greybeard community packs initiative._
