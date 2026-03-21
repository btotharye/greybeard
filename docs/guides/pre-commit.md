# Pre-commit Integration

greybeard can run as a pre-commit hook, reviewing staged changes before a commit lands.
This gives fast feedback at the source — before CI, before review, before anything else.

---

## How It Works

```
git commit → pre-commit framework → greybeard-precommit diff/check
                                         ↓
                                  staged diff analyzed
                                         ↓
                              concerns below threshold → commit proceeds
                              concerns at/above threshold → commit blocked
```

Configuration lives in a per-repo `.greybeard-precommit.yaml` file that the hook reads
on every run. The file controls which risk gates apply, which packs run, and whether hooks
are active at all.

---

## Setup

### 1. Add the hook to `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/btotharye/greybeard
    rev: v0.7.0 # pin to a specific release tag — see "Version pinning" below
    hooks:
      - id: greybeard-precommit-diff
        args: [--pack, staff-core]
```

### 2. Create `.greybeard-precommit.yaml` in your repo root

```yaml
enabled: true
default_pack: staff-core
fail_on_concerns: high

risk_gates:
  - name: security-critical
    patterns:
      - "auth/**"
      - "**/*secret*"
      - "**/*token*"
    fail_on_concerns: critical
    required_packs:
      - security-reviewer
    skip_if_branch:
      - "^hotfix/"
      - "^emergency/"
```

**Commit this file.** It is repo configuration, not personal preference. Tracking it in
source control ensures every developer (and CI) uses the same gate definitions.

### 3. Install hooks

```bash
pre-commit install
```

### 4. Verify configuration

```bash
greybeard-precommit config show
```

This prints the active config without running a review — useful to confirm gates loaded
correctly after editing `.greybeard-precommit.yaml`.

---

## Risk Gates

A risk gate is a named policy that applies greybeard checks to a specific subset of files,
at a specific concern threshold, using a specific set of packs.

### Gate fields

| Field              | Required | Description                                                                                                        |
| ------------------ | -------- | ------------------------------------------------------------------------------------------------------------------ |
| `name`             | ✅       | Human-readable name for the gate                                                                                   |
| `patterns`         | ✅       | File glob patterns that trigger this gate                                                                          |
| `fail_on_concerns` | –        | Block commit at this concern level or above (`critical`, `high`, `medium`, `low`). Defaults to repo-level setting. |
| `required_packs`   | –        | Packs that must run for this gate. Defaults to `default_pack`.                                                     |
| `skip_if_branch`   | –        | Regex patterns — skip gate entirely on matching branches.                                                          |

### Example: layered gates by sensitivity

```yaml
enabled: true
default_pack: staff-core
fail_on_concerns: high # default: block on high or critical

risk_gates:
  - name: infra-changes
    patterns:
      - "terraform/**"
      - "k8s/**"
      - "helm/**"
    fail_on_concerns: medium # stricter for infra
    required_packs:
      - oncall-future-you
      - security-reviewer

  - name: auth-and-secrets
    patterns:
      - "auth/**"
      - "**/*secret*"
      - "**/*credential*"
    fail_on_concerns: critical # only block on critical for auth code
    required_packs:
      - security-reviewer

  - name: docs-only
    patterns:
      - "docs/**"
      - "*.md"
    fail_on_concerns: none # never block doc-only commits
```

### Emergency bypass (`skip_if_branch`)

Branches matching the patterns in `skip_if_branch` completely skip the gate. This is
intentional — hotfix and incident branches should not be blocked by greybeard.

```yaml
risk_gates:
  - name: infra-changes
    patterns:
      - "terraform/**"
    skip_if_branch:
      - "^hotfix/"
      - "^incident/"
      - "^emergency/"
```

The patterns are Python regexes matched against the current branch name.

---

## Ownership Model

`.greybeard-precommit.yaml` is **platform/infra team configuration**, not personal tooling.

### Who should own it?

Whoever owns the repo's other developer tooling and CI configuration owns this file:

- Platform team / DX team for shared repos
- The backend team lead for service repos
- The individual developer for personal/side-project repos

If you don't have a clear owner, default to: whoever merges changes to `.pre-commit-config.yaml`.

### Version-control the file

```
.greybeard-precommit.yaml   ← commit this
.greybeard-precommit.local.yaml  ← gitignore this (if you need developer overrides)
```

Add the local override file to `.gitignore` so developers can temporarily adjust their
own settings without affecting the shared config.

### Keep a brief runbook (as code comments or a wiki page)

When gates change, the change should be reviewable. A suggested minimal note:

```yaml
# .greybeard-precommit.yaml
# Owner: platform-team / @your-handle
# Last reviewed: 2026-03
# Purpose: block high-risk commits before they reach CI
#
# To update:
#   1. Edit this file
#   2. Run `greybeard-precommit config show` to verify
#   3. Test with a staged change: git add <file> && greybeard-precommit diff
#   4. PR the change with the platform team as reviewers
enabled: true
```

### Testing gate changes

Before merging a gate change, verify it locally:

```bash
# 1. Show active config
greybeard-precommit config show

# 2. Test against real staged changes
git add path/to/test/file.py
greybeard-precommit diff --pack security-reviewer --verbose

# 3. Test against a specific file without staging
git diff HEAD~1 -- path/to/file.py | greybeard analyze --pack security-reviewer

# 4. Dry-run on all staged changes
greybeard-precommit check --verbose
```

### Rotating or removing a gate

1. Remove or comment out the gate in `.greybeard-precommit.yaml`
2. Run `greybeard-precommit config show` to confirm it's gone
3. Open a PR — reviewers can see the exact gating change in the diff
4. After merge, run `pre-commit run --all-files` to confirm no false positives

---

## Kill Switch

If greybeard is unexpectedly blocking commits (e.g., after a bad release), disable all
hooks immediately without touching `.pre-commit-config.yaml`:

```yaml
# .greybeard-precommit.yaml
enabled: false
```

This is faster than `pre-commit uninstall` and lets you re-enable by changing one line
once the issue is resolved.

For team-wide emergencies, commit `enabled: false`, merge to main, and notify developers
to run `pre-commit autoupdate` or `git pull`.

---

## Version Pinning

Always pin `rev:` to a release tag in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/btotharye/greybeard
    rev: v0.7.0 # ✅ pinned release
    # rev: main   # ❌ never — a bad commit breaks every developer's workflow
```

To update the pin:

```bash
pre-commit autoupdate --repo https://github.com/btotharye/greybeard
```

This updates to the latest release tag. Review the changelog before merging.

---

## Troubleshooting

**`greybeard-precommit: command not found`**

The hook binary isn't on the PATH. Make sure greybeard is installed in the same
environment pre-commit uses:

```bash
pip install "greybeard[anthropic]"
# or
uv tool install "greybeard[anthropic]"
```

**Gate is triggering on the wrong files**

Check your glob patterns with `greybeard-precommit config show`.
Patterns use standard Python `fnmatch`/`glob` syntax — `**` requires Python 3.5+ glob.

**Commit blocked unexpectedly after a greybeard update**

Use the kill switch ([see above](#kill-switch)) and file a bug with the review output
that was incorrectly flagged.

**How do I let one developer bypass gates without changing the shared config?**

Add a local override file (not tracked):

```yaml
# .greybeard-precommit.local.yaml  (gitignored)
enabled: false
```

Then set `GREYBEARD_PRECOMMIT_CONFIG=.greybeard-precommit.local.yaml` in their shell.
