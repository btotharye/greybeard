# GitHub Repository Configuration

This file documents the recommended GitHub repository settings for greybeard.

## Repository Settings

### General

**Description:**

> CLI-first Staff/Principal engineer review assistant powered by LLMs. Works with OpenAI, Anthropic, Ollama, and more.

**Topics (keywords):**

```
code-review
llm
ai
staff-engineer
architecture
cli
openai
anthropic
ollama
python
mcp
model-context-protocol
code-quality
```

**Features:**

- ✅ Issues
- ✅ Projects
- ✅ Discussions
- ✅ Wiki (optional)
- ✅ Sponsorships (if configured in FUNDING.yml)

**Social Preview Image:**
Consider creating a 1280x640 image with:

- greybeard ASCII art
- Project name
- Tagline: "Staff-level code review from the command line"

### Branch Protection (for `main`)

**Required:**

- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
  - `test (3.11)`
  - `test (3.12)`
  - `test (3.13)`
  - `lint`
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

**Optional:**

- Require linear history
- Include administrators (for solo maintainer, may want to disable)

### Security

**Advisories:**

- ✅ Enable private vulnerability reporting

**Dependabot:**

- ✅ Alerts enabled (configured via `.github/dependabot.yml`)
- ✅ Security updates enabled

**Code Scanning:**

- Consider enabling CodeQL for Python

### Automation

**GitHub Actions:**
See `.github/workflows/` for:

- `ci.yml` - Tests and linting on PRs
- `docs.yml` - Documentation builds
- `publish.yml` - PyPI publishing on releases
- `stale.yml` - Closes stale issues/PRs

### Community Standards

All files present:

- ✅ LICENSE
- ✅ README.md
- ✅ CODE_OF_CONDUCT.md
- ✅ CONTRIBUTING.md
- ✅ SECURITY.md
- ✅ Issue templates
- ✅ PR template
- ✅ Funding (optional)

## Environment Secrets

For PyPI publishing (after first manual upload), configure in repository settings:

**Environments → `pypi`:**

- No secrets needed (uses trusted publishing)

**Environments → `testpypi`:**

- No secrets needed (uses trusted publishing)

## Discussions Categories

Recommended categories:

- 💡 Ideas - Feature requests and suggestions
- 🙋 Q&A - Questions and answers
- 📣 Announcements - Project updates
- 🎨 Show and Tell - Share your content packs
- 💬 General - Everything else

## Labels

The issue templates will create these labels automatically:

- `bug`
- `enhancement`
- `triage`
- `content-pack`
- `community`
- `dependencies`
- `python`
- `github-actions`
- `stale`

Additional recommended labels:

- `good first issue`
- `help wanted`
- `documentation`
- `question`
- `wontfix`
- `duplicate`

## Applying These Settings

Most settings must be configured through the GitHub web UI:

1. Go to `https://github.com/btotharye/greybeard/settings`
2. Update **Description** and **Topics** under General
3. Configure **Branch protection rules** under Branches
4. Enable **Discussions** under General → Features
5. Review **Security** settings under Security & analysis
6. Create **Environments** (`pypi`, `testpypi`) under Environments

Note: The YAML files in `.github/` handle automation (workflows, issue templates, dependabot).
