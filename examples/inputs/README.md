# Example Inputs

Sample files for testing content packs manually. Each file contains a comment at the top with the recommended command to run it.

## Usage

```bash
# security-reviewer — auth endpoint with multiple issues (missing authz, token in logs, no rate limit)
cat examples/inputs/security-example.py | greybeard analyze --pack security-reviewer

# startup-pragmatist — Kafka event bus proposal for a 3-user app
cat examples/inputs/startup-pragmatist-example.md | greybeard analyze --pack startup-pragmatist

# incident-postmortem — postmortem that blames "John", uses human error as root cause, weak action items
cat examples/inputs/postmortem-example.md | greybeard analyze --pack incident-postmortem

# data-migrations — migration that adds NOT NULL column with no default, no concurrent index
cat examples/inputs/migration-example.py | greybeard analyze --pack data-migrations
```

## What to look for

Each example is intentionally flawed in ways specific to its pack:

| File | Intentional issues |
|---|---|
| `security-example.py` | No auth on GET, token in logs, plaintext password comparison, no rate limit, missing authz on DELETE |
| `startup-pragmatist-example.md` | Kafka + event sourcing for 3 users, 1 part-time engineer |
| `postmortem-example.md` | Blames "John" by name, "human error" as root cause, vague action items with no owners |
| `migration-example.py` | NOT NULL with no default (table lock), non-concurrent index, FK without checking index coverage |

A well-tuned pack should surface all of these issues.
