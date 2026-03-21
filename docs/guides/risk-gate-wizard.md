# Risk Gate Wizard Guide

The **Risk Gate Wizard** is an interactive tool that helps you configure intelligent pre-commit gates. Instead of checking all files equally, risk gates apply greybeard analysis only to the files that matter most—based on risk level, file patterns, and business criticality.

## Overview

**Risk gates** are pre-commit checks that analyze code based on file patterns and severity levels:

- 🚫 **Critical**: Deploy paths, infrastructure, auth logic — always review
- ⚠️ **High**: API contracts, migrations, configuration — fail on high-risk concerns
- 📋 **Medium**: Business logic, features — helpful review
- 📝 **Documentation**: Keep docs in sync with code

The wizard walks you through:

1. Selecting a risk gate template (or creating custom)
2. Defining file patterns to match
3. Choosing analysis packs to run
4. Setting severity thresholds
5. Configuring branch bypasses (for emergencies)
6. Validating your repo structure

**Output**: `.greybeard-precommit.yaml` — ready to use with pre-commit hooks.

---

## Quick Start

### Run the Wizard

```bash
greybeard risk-gate-wizard
```

This launches an interactive wizard in your terminal. Answer the prompts to configure your gates.

### What You'll Do

1. **Select gate(s)** to configure:
   - Critical (infra, deploy, auth)
   - High (API, migrations, config)
   - Medium (business logic)
   - Documentation
   - Custom

2. **Define file patterns** (glob patterns):
   - `infra/*` — infrastructure code
   - `src/**/*.py` — Python source
   - `docs/*.md` — documentation

3. **Choose analysis packs**:
   - `staff-core` — Staff engineer lens
   - `security-reviewer` — Security perspective
   - `documentation-reviewer` — Docs consistency

4. **Set severity thresholds** (fail on concerns):
   - `critical` — Fail on any critical issue
   - `high` — Fail on high or higher
   - `medium` — Fail on medium or higher

5. **Configure emergency bypass**:
   - Define branch patterns for hotfixes (e.g., `hotfix/*`)
   - These skip gates temporarily for emergencies

6. **Review & save**:
   - Wizard generates `.greybeard-precommit.yaml`
   - Git hooks installed automatically

### Example: 5-Minute Setup

```bash
$ greybeard risk-gate-wizard

📋 Risk Gate Wizard
───────────────────────────────────────────────────────

🔧 Available gates: critical, high, medium, documentation

Which gate(s) to configure? (critical, high, or both?)
> critical

✅ Critical gate selected

📝 File patterns for critical files (glob)
  (e.g., infra/*, deploy/*, auth/*)

Enter pattern (blank to stop):
  1: infra/*
  2: deploy/*
  3: auth/*
  4: schema/*.sql
  5: 

✅ Patterns added: infra/*, deploy/*, auth/*, schema/*.sql

📦 Available packs: staff-core, security-reviewer, platform-ops

Select pack(s) to run for critical files:
  [ ] staff-core ............................ Staff engineer analysis
  [x] security-reviewer ..................... Security review (RECOMMENDED)
  [ ] platform-ops .......................... Platform engineer lens
  [ ] custom ................................ Custom pack

⚠️ Threshold: fail_on_concerns: critical

Branch bypass pattern (for hotfixes):
  > hotfix/*

✅ Configuration:
  Pattern: infra/*, deploy/*, auth/*, schema/*.sql
  Packs: security-reviewer
  Fail on: critical concerns
  Bypass: hotfix/*

Generate config? (y/n)
> y

✅ Created .greybeard-precommit.yaml
✅ Git hooks configured
✅ Ready for pre-commit checks!
```

### Test It

```bash
# Test on a critical file
echo "SELECT * FROM users" > infra/schema.sql
git add infra/schema.sql

# Run pre-commit
pre-commit run

# Output:
# greybeard-risk-gates.........................FAILED
# - critical: Missing error handling for schema migration
```

---

## Understanding Risk Gates

### Gate Templates

The wizard provides four predefined templates:

#### Critical Gate
**For**: Deploy paths, infrastructure, auth logic, database schema  
**File patterns**: `infra/*`, `deploy/*`, `auth/*`, `schema/*.sql`  
**Fail on**: `critical` concerns  
**Default packs**: `staff-core`, `security-reviewer`

```yaml
critical_gate:
  patterns:
    - infra/*
    - deploy/*
    - auth/*
    - schema/*.sql
  packs:
    - staff-core
    - security-reviewer
  fail_on_concerns: critical
```

**Use when**: Your infrastructure code is critical and needs Staff-level review before merge.

#### High Gate
**For**: API contracts, migrations, configuration files  
**File patterns**: `api/v*/`, `migrations/*`, `config/*`, `*.proto`  
**Fail on**: `high` concerns  
**Default packs**: `staff-core`

```yaml
high_gate:
  patterns:
    - api/v*/
    - migrations/*
    - config/*
    - "*.proto"
  packs:
    - staff-core
  fail_on_concerns: high
```

**Use when**: You want to catch API breaking changes and risky configuration updates.

#### Medium Gate
**For**: Standard business logic, feature code  
**File patterns**: `src/**/*.py`, `src/**/*.ts`, `src/**/*.tsx`  
**Fail on**: `medium` concerns  
**Default packs**: `staff-core`

```yaml
medium_gate:
  patterns:
    - src/**/*.py
    - src/**/*.ts
    - src/**/*.tsx
  packs:
    - staff-core
  fail_on_concerns: medium
```

**Use when**: You want helpful review on all feature code without blocking every change.

#### Documentation Gate
**For**: ADRs, README, design docs  
**File patterns**: `docs/*.md`, `ADR*.md`, `*.md`  
**Fail on**: `low` concerns  
**Default packs**: `documentation-reviewer`

```yaml
documentation_gate:
  patterns:
    - docs/*.md
    - ADR*.md
    - "*.md"
  packs:
    - documentation-reviewer
  fail_on_concerns: low
```

**Use when**: You want to keep documentation in sync with code.

### Custom Gates

Need something different? Create custom gates during wizard or edit the config:

```yaml
# .greybeard-precommit.yaml
risk_gates:
  data_pipeline:
    description: "Data pipeline and ETL code"
    patterns:
      - pipelines/*
      - src/etl/*
      - queries/*.sql
    packs:
      - staff-core
      - data-engineer
    fail_on_concerns: high
    
  frontend:
    description: "Frontend and UI code"
    patterns:
      - frontend/src/**/*.{ts,tsx}
      - "!frontend/src/**/*.test.{ts,tsx}"
    packs:
      - staff-core
      - frontend-reviewer
    fail_on_concerns: medium
```

---

## File Patterns (Glob)

File patterns use standard glob syntax to match files:

### Common Patterns

| Pattern | Matches |
|---------|---------|
| `infra/*` | Files in infra/ directory |
| `src/**/*.py` | All .py files in src/ and subdirectories |
| `*.yaml` | All YAML files in root |
| `deploy/*` | Files in deploy/ directory |
| `src/api/v*/*.py` | API versioning pattern |
| `migrations/*` | Migration files |
| `!src/**/*.test.py` | Exclude test files |
| `config/*.{yaml,yml}` | YAML config files |

### Pattern Tips

**Multiple file types:**
```yaml
patterns:
  - src/**/*.{ts,tsx,js,jsx}  # All JS/TS files
  - "!src/**/*.test.{ts,tsx}" # Except tests
```

**Version patterns:**
```yaml
patterns:
  - api/v[0-9]/*  # api/v1/*, api/v2/*, etc.
```

**Exclude patterns:**
```yaml
patterns:
  - src/**/*.py
  - "!src/generated/*"  # Except generated code
  - "!src/**/*_pb2.py"  # Except protobuf
```

**Root-level files:**
```yaml
patterns:
  - "Dockerfile"
  - "docker-compose.*.yaml"
  - ".env.prod"
```

---

## Analysis Packs

Packs define the perspectives applied to matched files. Available packs:

### Core Packs

| Pack | Purpose | When to Use |
|------|---------|------------|
| `staff-core` | Staff-level review (default) | Always—foundational |
| `security-reviewer` | Security perspective | Infra, auth, critical code |
| `documentation-reviewer` | Docs consistency | Documentation, ADRs |
| `platform-ops` | Platform engineering | Infrastructure, deployment |
| `performance-reviewer` | Performance concerns | Hot paths, APIs |

### Domain Packs

| Pack | Purpose | When to Use |
|------|---------|------------|
| `data-engineer` | Data pipeline thinking | ETL, pipelines, SQL |
| `frontend-reviewer` | UI/UX perspective | Frontend code |
| `backend-reviewer` | Backend patterns | API, services |
| `mobile-reviewer` | Mobile-specific | Mobile code |
| `database-reviewer` | Database schema | Migrations, schema changes |

### SLO Packs

| Pack | Purpose | When to Use |
|------|---------|------------|
| `slo-saas` | SaaS reliability | User-facing services |
| `slo-critical-infra` | Critical infrastructure | Auth, gateway, core services |
| `slo-batch` | Batch jobs | Pipelines, ETL |
| `slo-background-jobs` | Background workers | Workers, queues |

### Selecting Packs

**Rule of thumb**: 1-2 packs per gate is best. More packs = slower checks.

**Critical gate** — Use 2 packs:
```yaml
critical_gate:
  packs:
    - staff-core            # Always
    - security-reviewer     # For auth/infra
```

**High gate** — Use 1 pack:
```yaml
high_gate:
  packs:
    - staff-core
```

**Domain-specific** — Use domain + core:
```yaml
data_pipeline_gate:
  packs:
    - staff-core
    - data-engineer
```

---

## Severity Thresholds

The `fail_on_concerns` setting determines which concerns fail the pre-commit check.

### Severity Levels

From most to least severe:

| Level | Meaning | Typical Action |
|-------|---------|----------------|
| `critical` | Major issue that could cause outage | Always block |
| `high` | Significant concern, should be fixed | Block on critical paths |
| `medium` | Should be addressed, but not critical | Helpful feedback |
| `low` | Nice-to-have improvement | FYI |
| `none` | Pass all concerns | Informational only |

### Configuration

```yaml
risk_gates:
  critical_gate:
    fail_on_concerns: critical  # Only fail on critical issues
    
  high_gate:
    fail_on_concerns: high      # Fail on high or critical
    
  medium_gate:
    fail_on_concerns: medium    # Fail on medium+ concerns
    
  documentation_gate:
    fail_on_concerns: low       # Fail on low+ concerns (rarely blocks)
```

### Behavior

When a concern is detected:

- **If <= threshold**: Passes (green) ✅
- **If > threshold**: Fails (red) ❌

Example: `fail_on_concerns: high`

```
Issue Level | Result
────────────┬────────
critical    | FAIL ❌
high        | FAIL ❌
medium      | PASS ✅
low         | PASS ✅
```

---

## Branch Bypass Patterns

Sometimes you need to bypass gates temporarily (e.g., for hotfixes or emergencies).

### Configuring Bypasses

During wizard:
```
🔄 Branch bypass pattern (for hotfixes):
> hotfix/*
```

In config:
```yaml
risk_gates:
  critical_gate:
    patterns: [infra/*, deploy/*]
    packs: [staff-core]
    fail_on_concerns: critical
    skip_on_branch: "hotfix/*"  # Skip on hotfix/* branches
```

### Common Bypass Patterns

```yaml
skip_on_branch:
  - "hotfix/*"        # Any hotfix branch
  - "emergency/*"     # Emergency branches
  - "production-fix"  # Specific branch
  - "release/*"       # Release branches
```

### Use Responsibly ⚠️

Bypass patterns create an exception. Use them for:

- 🆘 Real emergencies (production outage)
- 🔥 Time-critical hotfixes (critical bug)
- 📦 Release branches (final QA)

Don't use for:
- Regular feature work
- Avoiding review
- Speed (gates add ~1-2 seconds)

**Best practice**: Document why the branch needs bypass:

```bash
# Create hotfix branch with bypass pattern
git checkout -b hotfix/critical-bug  # Matches hotfix/*

# Commit message explains urgency
git commit -m "
Hotfix: Critical authentication bug

Bypasses risk gates (hotfix/* pattern)
Reason: Production outage — 5000+ users affected
Reviewed by: @oncall-engineer
"
```

---

## Configuration File

The wizard generates `.greybeard-precommit.yaml`:

```yaml
version: "1.0"
description: "Risk gates for pre-commit checks"

# Git integration
hooks:
  auto_install: true  # Install pre-commit hook automatically

# Risk gate definitions
risk_gates:
  critical:
    description: "Critical infrastructure and deployment code"
    patterns:
      - infra/*
      - deploy/*
      - auth/*
      - schema/*.sql
    packs:
      - staff-core
      - security-reviewer
    fail_on_concerns: critical
    skip_on_branch: "hotfix/*"

  high:
    description: "High-risk changes — API, migrations, config"
    patterns:
      - api/v*/
      - migrations/*
      - config/*
    packs:
      - staff-core
    fail_on_concerns: high
    skip_on_branch: "hotfix/*"

  medium:
    description: "Standard code review"
    patterns:
      - src/**/*.py
      - src/**/*.ts
      - src/**/*.tsx
    packs:
      - staff-core
    fail_on_concerns: medium

# Post-run actions
on_pass:
  - echo "✅ Risk gates passed"

on_fail:
  - echo "❌ Review concerns above"
  - echo "To bypass: git commit --no-verify (use sparingly!)"
```

### Modifying the Config

Edit `.greybeard-precommit.yaml` directly to:

- Add new gates
- Change file patterns
- Add/remove packs
- Adjust severity thresholds
- Update bypass patterns

```bash
# Edit and test
nano .greybeard-precommit.yaml

# Test against a file
greybeard analyze --risk-gates infra/deploy.tf

# Reinstall hooks
pre-commit install
```

---

## Integration with Pre-commit

The wizard configures [pre-commit](https://pre-commit.com/) hooks automatically.

### How It Works

1. Wizard creates `.greybeard-precommit.yaml`
2. Adds greybeard hook to `.pre-commit-config.yaml`
3. Installs hook locally
4. On `git commit`, runs gates on staged files

### Manual Setup

If you prefer manual setup:

```bash
# In .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: greybeard-risk-gates
        name: greybeard risk gates
        entry: greybeard analyze --risk-gates
        language: system
        stages: [commit]
        pass_filenames: true
        always_run: false
```

Then install:

```bash
pre-commit install
pre-commit run --all-files  # Test
```

### Testing

```bash
# Run gates on all files
pre-commit run --all-files

# Run on specific files
pre-commit run --files infra/deploy.tf

# Skip gates (use sparingly!)
git commit --no-verify
```

---

## Step-by-Step Walkthroughs

### Walkthrough 1: Basic Setup (5 minutes)

Goal: Set up critical and high gates for a microservice.

**Start:**
```bash
greybeard risk-gate-wizard
```

**Step 1: Select gates**
```
Which gate(s) to configure? (critical, high, or both?)
> critical high
```

**Step 2: Configure critical gate**
```
🔒 Critical Gate

📝 File patterns (glob):
  1: infra/*
  2: deploy/*
  3: auth/*
  4: 

📦 Packs (select all needed):
  [x] staff-core
  [x] security-reviewer

⚠️  Fail on: critical (recommended)

🔄 Branch bypass (for hotfixes):
  > hotfix/*
```

**Step 3: Configure high gate**
```
⚠️  High Gate

📝 File patterns:
  1: api/v*/
  2: migrations/*
  3: config/*
  4: 

📦 Packs:
  [x] staff-core

⚠️  Fail on: high

🔄 Branch bypass:
  > hotfix/*
```

**Step 4: Review**
```
✅ Configuration complete!
  - Critical gate: infra/*, deploy/*, auth/* → staff-core, security-reviewer
  - High gate: api/v*/, migrations/*, config/* → staff-core

Generate? (y/n)
> y

✅ Created .greybeard-precommit.yaml
✅ Git hooks installed
✅ Ready to use!
```

**Done!** Your gates are now active. Test with:

```bash
git add .greybeard-precommit.yaml
git commit -m "Configure risk gates"
```

### Walkthrough 2: Advanced Setup with Multiple Domains (10 minutes)

Goal: Set up gates for a complex app with frontend, backend, data pipeline, and infra.

**Start the wizard:**
```bash
greybeard risk-gate-wizard --advanced
```

**Configure gates:**

1. **Critical Infrastructure**
   - Patterns: `infra/*`, `deploy/*`, `k8s/*`, `helm/*`
   - Packs: `staff-core`, `security-reviewer`, `platform-ops`
   - Fail on: `critical`
   - Bypass: `hotfix/*`, `production-fix`

2. **High-Risk Changes**
   - Patterns: `src/auth/*`, `src/api/*`, `migrations/*`, `config/*`
   - Packs: `staff-core`
   - Fail on: `high`
   - Bypass: `hotfix/*`

3. **Backend Features**
   - Patterns: `src/services/*`, `src/handlers/*`
   - Packs: `staff-core`, `backend-reviewer`
   - Fail on: `medium`
   - Bypass: none

4. **Frontend Code**
   - Patterns: `frontend/src/**/*.{ts,tsx}`
   - Packs: `staff-core`, `frontend-reviewer`
   - Fail on: `medium`
   - Bypass: none

5. **Data Pipeline**
   - Patterns: `pipelines/*`, `src/etl/*`, `queries/*.sql`
   - Packs: `staff-core`, `data-engineer`
   - Fail on: `high`
   - Bypass: none

6. **Documentation**
   - Patterns: `docs/*.md`, `ADR*.md`
   - Packs: `documentation-reviewer`
   - Fail on: `low`
   - Bypass: none

**Result:**
```yaml
risk_gates:
  critical_infra:
    patterns: [infra/*, deploy/*, k8s/*, helm/*]
    packs: [staff-core, security-reviewer, platform-ops]
    fail_on_concerns: critical
    skip_on_branch: ["hotfix/*", "production-fix"]
  
  high_risk:
    patterns: [src/auth/*, src/api/*, migrations/*, config/*]
    packs: [staff-core]
    fail_on_concerns: high
    skip_on_branch: hotfix/*
  
  backend_features:
    patterns: [src/services/*, src/handlers/*]
    packs: [staff-core, backend-reviewer]
    fail_on_concerns: medium
  
  frontend:
    patterns: [frontend/src/**/*.{ts,tsx}]
    packs: [staff-core, frontend-reviewer]
    fail_on_concerns: medium
  
  data_pipeline:
    patterns: [pipelines/*, src/etl/*, queries/*.sql]
    packs: [staff-core, data-engineer]
    fail_on_concerns: high
  
  documentation:
    patterns: [docs/*.md, ADR*.md]
    packs: [documentation-reviewer]
    fail_on_concerns: low
```

### Walkthrough 3: Custom Packs (15 minutes)

Goal: Create a custom pack for your team's specific concerns, then add it to gates.

**Step 1: Create custom pack**

Create `teams/mycompany-slo.yaml`:

```yaml
pack_name: mycompany-slo
description: Company SLO and reliability standards

perspectives:
  - name: service-level-objectives
    context: |
      Our SLO targets:
      - User-facing APIs: 99.9% availability, p99 < 200ms
      - Critical infrastructure: 99.95% availability, p99 < 50ms
      - Batch jobs: 95% availability
      
      When reviewing code:
      1. Does it have retries for external calls?
      2. Are timeouts set appropriately?
      3. Is error handling present?
      4. Are SLO targets documented?

  - name: database-patterns
    context: |
      Database queries should:
      - Have appropriate indexes
      - Include pagination limits
      - Use connection pooling
      - Include timeout handling
      
      Flag missing patterns in code review.
```

**Step 2: Add pack to gate**

Edit `.greybeard-precommit.yaml`:

```yaml
risk_gates:
  critical:
    patterns: [infra/*, deploy/*]
    packs:
      - staff-core
      - security-reviewer
      - mycompany-slo        # Add custom pack
    fail_on_concerns: critical
```

**Step 3: Test**

```bash
# Run gates to test custom pack
pre-commit run --all-files

# Output will include custom pack analysis
```

---

## Examples

### Example 1: Microservice with Critical Infrastructure

```yaml
risk_gates:
  critical:
    description: "Infrastructure and deployment"
    patterns:
      - infra/*
      - deploy/*
      - docker/*
      - k8s/*
    packs:
      - staff-core
      - security-reviewer
      - platform-ops
    fail_on_concerns: critical
    skip_on_branch: hotfix/*

  high:
    description: "API and configuration"
    patterns:
      - src/api/*
      - config/*
      - migrations/*
    packs:
      - staff-core
    fail_on_concerns: high
    skip_on_branch: hotfix/*

  standard:
    description: "Business logic"
    patterns:
      - src/**/*.py
      - "!src/api/*"
    packs:
      - staff-core
    fail_on_concerns: medium
```

### Example 2: Data Platform

```yaml
risk_gates:
  critical:
    patterns:
      - infra/*
      - schema/*
      - scripts/migration*
    packs:
      - staff-core
      - security-reviewer
      - database-reviewer
    fail_on_concerns: critical

  pipelines:
    patterns:
      - dags/*
      - src/etl/*
      - queries/*
    packs:
      - staff-core
      - data-engineer
    fail_on_concerns: high

  features:
    patterns:
      - src/**/*.py
      - "!src/etl/*"
    packs:
      - staff-core
    fail_on_concerns: medium
```

### Example 3: Full-Stack Startup

```yaml
risk_gates:
  infrastructure:
    patterns: [infra/*, deploy/*, devops/*]
    packs: [staff-core, platform-ops]
    fail_on_concerns: critical
    skip_on_branch: hotfix/*

  backend_api:
    patterns: [backend/src/api/*, backend/migrations/*]
    packs: [staff-core, backend-reviewer]
    fail_on_concerns: high
    skip_on_branch: hotfix/*

  backend_services:
    patterns: [backend/src/**/*.py, "!backend/src/api/*"]
    packs: [staff-core]
    fail_on_concerns: medium

  frontend:
    patterns: [frontend/src/**/*.{ts,tsx}]
    packs: [staff-core, frontend-reviewer]
    fail_on_concerns: medium

  database:
    patterns: [migrations/*, schema/]
    packs: [database-reviewer, staff-core]
    fail_on_concerns: high

  docs:
    patterns: [docs/*, README.md, ADR*.md]
    packs: [documentation-reviewer]
    fail_on_concerns: low
```

---

## Troubleshooting

### Gates aren't running on commit

**Problem**: Pre-commit hook installed but not running

**Solutions**:

```bash
# Check hook installation
ls -la .git/hooks/pre-commit

# Re-install
pre-commit install

# Test manually
pre-commit run --all-files
```

### Too many false positives

**Problem**: Gates fail on code that's actually fine

**Solution**: Adjust severity thresholds:

```yaml
# From strict to relaxed
fail_on_concerns: critical  # Least blocking
fail_on_concerns: high
fail_on_concerns: medium
fail_on_concerns: low       # Most blocking
```

### Gates are too slow

**Problem**: Pre-commit checks take > 5 seconds

**Solution**: Reduce packs or split gates:

```yaml
# Before: 3 packs
slow_gate:
  packs: [staff-core, security-reviewer, platform-ops]

# After: 2 gates, faster
critical:
  patterns: [infra/*, deploy/*]
  packs: [staff-core, security-reviewer]

standard:
  patterns: [src/**]
  packs: [staff-core]
```

### Patterns aren't matching files

**Problem**: Gate configured but not running on expected files

**Solution**: Test glob patterns:

```bash
# Check what files match
git ls-files | grep -E 'infra/.*'

# Test pre-commit filters
pre-commit run --all-files --verbose
```

---

## Best Practices

### 1. Start Simple, Expand Gradually

**Phase 1** (Week 1): Critical gate only
```yaml
critical:
  patterns: [infra/*, deploy/*]
  packs: [staff-core, security-reviewer]
  fail_on_concerns: critical
```

**Phase 2** (Week 2-3): Add high gate
```yaml
high:
  patterns: [api/*, migrations/*, config/*]
  packs: [staff-core]
  fail_on_concerns: high
```

**Phase 3** (Week 4+): Add domain-specific gates
```yaml
frontend:
  patterns: [frontend/src/**/*.{ts,tsx}]
  packs: [staff-core, frontend-reviewer]
  fail_on_concerns: medium
```

### 2. Clear Emergency Bypass Rules

Make bypass patterns explicit and document them:

```yaml
skip_on_branch: "hotfix/*"

# Add to wiki/runbook:
# - Use hotfix/* branch ONLY for production emergencies
# - Get approval from on-call lead
# - File incident after fix lands
```

### 3. Iterate Based on Feedback

Track which gates block legit PRs:

```bash
# After 1 week of gates
git log --oneline --grep="bypass"

# If high bypass rate on certain gate → lower threshold
# If gates pass everything → increase severity
```

### 4. Document SLO Targets in Patterns

Use gate descriptions to document why patterns matter:

```yaml
critical:
  description: |
    Infrastructure code. These files impact uptime and security.
    SLO impact: 99.95% availability, < 0.01% error rate
    Change risk: Deployment failures, data loss, security breach
```

### 5. Review Config Monthly

Add to team calendar:

```
Monthly: Review and update .greybeard-precommit.yaml
- Check false positive rate
- Update patterns for new services
- Adjust severity thresholds
- Document new bypass patterns
```

---

## FAQ

**Q: Can gates run in CI instead of locally?**

Yes! Add to your CI config:

```yaml
# GitHub Actions example
- name: Risk gates
  run: greybeard analyze --risk-gates
```

**Q: What if I disagree with a gate?**

Either:
1. Adjust severity threshold: `fail_on_concerns: low` (informational)
2. Remove pattern from gate
3. Use `git commit --no-verify` to bypass (sparingly)
4. File issue to discuss with team

**Q: Can I have different gates for different teams?**

Yes! Create multiple config files:

```bash
# For frontend team
.greybeard-precommit-frontend.yaml

# For backend team
.greybeard-precommit-backend.yaml

# For platform team
.greybeard-precommit-platform.yaml

# In pre-commit hook: run all three
```

**Q: How do I bypass a gate without `--no-verify`?**

Use a branch that matches `skip_on_branch`:

```bash
git checkout -b hotfix/critical-bug
# Commit freely—gate skipped
```

**Q: What's the difference between high and medium?**

- **High**: Business impact if broken (API contracts, data integrity)
- **Medium**: Code quality, but failures are handled gracefully

---

## Next Steps

- Review [Content Packs](packs.md) to understand pack composition
- Check [CLI Reference](../reference/cli.md) for advanced options
- Read [Creating Agents](creating_agents.md) for custom analysis
- See [Interactive Mode](interactive-mode.md) for deeper review
