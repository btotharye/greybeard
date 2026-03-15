# Security Reviewer Pack

AppSec engineer perspective — evidence-based risk assessment focused on preventing boring, real-world mistakes.

## Quick Start

```bash
# Review code or design for security concerns
cat code-review.md | greybeard analyze --pack security-reviewer

# Understand the attack class and impact
cat code-review.md | greybeard analyze --pack security-reviewer --mode mentor
```

## Focus Areas

- **Authentication & Authorization**: Are the auth boundaries clear?
- **Injection Risks**: Where does user input touch dangerous operations?
- **Secrets Management**: Could credentials leak in logs or errors?
- **Blast Radius**: What's the impact if this is compromised?

## When to Use This Pack

Use this pack for code reviews, design reviews, and threat modeling — especially for auth, data handling, and external integrations.

---

_Created as part of the Greybeard community packs initiative._
