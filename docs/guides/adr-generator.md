# ADR Generator Guide

Architecture Decision Records (ADRs) are a structured way to document important decisions in your project. The greybeard ADR Generator converts review findings into properly formatted ADRs that you can version control and reference.

## What is an ADR?

An ADR captures:
- **Status**: Proposed, Accepted, Deprecated, or Superseded
- **Context**: The problem or constraints you face
- **Decision**: What you're actually doing
- **Consequences**: The trade-offs and impacts
- **Alternatives**: What else you considered

## Quick Start

### Save a review as an ADR

```bash
greybeard analyze < design-doc.md | greybeard adr-save --title "Use PostgreSQL for Persistence"
```

This creates a numbered ADR file in `docs/adr/` with proper formatting.

### List all ADRs in a project

```bash
greybeard adr-list
```

Shows all ADRs with their status and dates.

## Usage

### Basic Workflow

1. **Run a review:**
   ```bash
   git diff main | greybeard analyze --mode review --pack staff-core
   ```

2. **Save the output as an ADR:**
   ```bash
   git diff main | greybeard analyze --mode review --pack staff-core | \
     greybeard adr-save --title "Migrate to gRPC"
   ```

3. **Verify it was created:**
   ```bash
   greybeard adr-list
   ```

### Command Reference

#### `greybeard adr-save`

Converts a greybeard review into a structured ADR.

**Options:**

- `--title`, `-t` (required): ADR title
  - Example: `"Use PostgreSQL for Persistence"`
  
- `--status`, `-s`: ADR status (default: `Proposed`)
  - Choices: `Proposed`, `Accepted`, `Deprecated`, `Superseded`
  - Use `Accepted` after team sign-off
  
- `--authors`, `-a`: Author names (can be used multiple times)
  - Example: `--authors alice --authors bob`
  
- `--repo`, `-r`: Path to git repository (default: current directory)
  - Use when running from outside the project
  
- `--commit`: Auto-commit the ADR to git
  - Creates a commit with message: `docs(adr): {title} [{status}]`

**Examples:**

```bash
# Basic save
greybeard analyze < design.md | greybeard adr-save --title "Use Redis"

# With authors and auto-commit
greybeard analyze < design.md | \
  greybeard adr-save \
    --title "Adopt Microservices" \
    --authors alice \
    --authors bob \
    --commit

# After team approval
greybeard analyze < design.md | \
  greybeard adr-save \
    --title "Add TypeScript" \
    --status Accepted \
    --commit
```

#### `greybeard adr-list`

Lists all ADRs in a repository.

**Options:**

- `--repo`, `-r`: Path to git repository (default: current directory)

**Output:**

Shows a table with:
- **Number**: ADR sequence number (0001, 0002, etc.)
- **Title**: Decision title
- **Status**: Current status (color-coded)
- **Date**: When the ADR was created

**Examples:**

```bash
# List ADRs in current project
greybeard adr-list

# List ADRs in another project
greybeard adr-list --repo /path/to/project
```

## ADR Structure

### Generated Format

ADRs are stored as markdown files in `docs/adr/` with sequential numbering:

```
docs/adr/
├── 0001-use-postgresql.md
├── 0002-adopt-microservices.md
└── 0003-add-redis-caching.md
```

### File Contents

Each ADR follows this structure:

```markdown
# ADR: Use PostgreSQL

**Status:** Proposed
**Date:** 2026-03-21
**Authors:** alice, bob

## Context

The system currently uses SQLite, which is a bottleneck under high load.
We need a production-grade relational database.

## Decision

Adopt PostgreSQL with connection pooling via pgBouncer.

## Consequences

**Positive:**
- Scales to 10k+ concurrent connections
- Full ACID compliance
- Mature ecosystem

**Negative:**
- Requires operational expertise
- Additional infrastructure cost (~$500/mo)
- Migration effort (2-3 weeks)

## Alternatives Considered

- MySQL: Less mature JSON support
- MongoDB: Wrong model for our domain
- RDS Aurora: Vendor lock-in

## Related Decisions

- 0001-choose-postgresql-for-main-db
```

## Workflow: From Review to Decision

### Step 1: Conduct a Review

```bash
git diff main | greybeard analyze \
  --mode review \
  --pack staff-core \
  --context "Q1 architecture planning"
```

This produces a markdown review with findings.

### Step 2: Extract Key Insights

The review suggests a particular approach. The ADR generator extracts:
- **Context** from problem/constraint sections
- **Decision** from recommendation sections
- **Consequences** from impact/trade-off sections
- **Alternatives** from considered-options sections

### Step 3: Save as ADR

```bash
# Pipe directly
greybeard analyze < design.md | greybeard adr-save --title "Migrate Auth to OAuth2"

# Or save review first, then convert
greybeard analyze < design.md > review.md
cat review.md | greybeard adr-save --title "Migrate Auth to OAuth2"
```

### Step 4: Track Over Time

As decisions evolve:

```bash
# New alternative emerges, supersede the old ADR
greybeard analyze < updated-analysis.md | \
  greybeard adr-save \
    --title "Migrate Auth to OAuth2 (v2)" \
    --status Superseded
```

## Integration with Git

### Auto-Commit ADRs

Use `--commit` to automatically stage and commit:

```bash
greybeard analyze < design.md | \
  greybeard adr-save \
    --title "Cache Strategy" \
    --commit
```

This creates a commit:

```
docs(adr): Cache Strategy [Proposed]
```

### Manual Workflow

If you prefer more control:

```bash
# Save the ADR
greybeard analyze < design.md | \
  greybeard adr-save --title "New Decision"

# Review the generated file
git diff docs/adr/

# Manually commit with custom message
git add docs/adr/0003-new-decision.md
git commit -m "docs: add ADR for new decision with team sign-off"
```

## Tips and Best Practices

### 1. Use Meaningful Titles

Good titles are terse but descriptive:
- ✅ "Use PostgreSQL for Main Database"
- ✅ "Migrate to gRPC for Service Communication"
- ❌ "Architecture"
- ❌ "Should we use a database?"

### 2. Set Status Correctly

- **Proposed**: Initial draft, awaiting team review
- **Accepted**: Team agreed, approved for implementation
- **Deprecated**: No longer recommended but documented for history
- **Superseded**: Replaced by a newer ADR

Example workflow:

```bash
# Initial draft
greybeard analyze < design.md | \
  greybeard adr-save --title "Use Redis" --status Proposed

# After team approval, update the status in the file
# docs/adr/0001-use-redis.md
# Change: **Status:** Proposed → **Status:** Accepted

# Commit the update
git add docs/adr/0001-use-redis.md
git commit -m "docs: accept ADR-0001 (Use Redis)"
```

### 3. Include Authors

Track who was involved in the decision:

```bash
greybeard analyze < design.md | \
  greybeard adr-save \
    --title "Use Kubernetes" \
    --authors alice \
    --authors bob \
    --authors charlie
```

### 4. Link Related ADRs

In the "Related Decisions" section, reference other ADRs:

```markdown
## Related Decisions

- 0001-use-postgresql (Database choice)
- 0002-adopt-connection-pooling (Performance optimization)
```

### 5. Version Control Strategy

Store ADRs in your repository's `docs/adr/` directory:

```bash
git add docs/adr/
git commit -m "docs(adr): add decision record"
git push
```

This makes decisions visible in code review and history.

## Customization

### Custom ADR Directory

If you don't use `docs/adr/`, specify `--repo` with a different path:

```bash
# If your ADRs go in architecture/decisions/
cd /path/to/project
mkdir -p architecture/decisions
# Create a symlink (if needed)
ln -s architecture/decisions docs/adr

greybeard adr-save --title "..."
```

### Batch Conversions

Convert multiple reviews to ADRs:

```bash
for design in designs/*.md; do
  greybeard analyze < "$design" | \
    greybeard adr-save \
      --title "$(basename $design .md)" \
      --authors team
done

greybeard adr-list
```

## Examples

### Example 1: Performance Decision

**Review input:**
```
## Current State
API latency: p99 = 500ms

## Analysis
Bottleneck identified: database queries not cached

## Recommendation
Implement Redis cache with 5-min TTL for read-heavy queries
```

**Command:**
```bash
cat review.txt | greybeard adr-save --title "Implement Redis Caching"
```

**Generated ADR:**
```markdown
# ADR: Implement Redis Caching

**Status:** Proposed
**Date:** 2026-03-21

## Context
API latency is high (p99 = 500ms). Database queries for read-heavy endpoints are the bottleneck.

## Decision
Implement Redis cache with 5-minute TTL for frequently-accessed data.

## Consequences
Positive: 10x faster query results for cached data
Negative: Cache invalidation complexity, additional infrastructure

## Alternatives Considered
- Memcached (simpler but less feature-rich)
- Application-level in-memory caching (not distributed)
```

### Example 2: Technology Choice

**Command:**
```bash
greybeard analyze < arch-review.md | \
  greybeard adr-save \
    --title "Use TypeScript for Frontend" \
    --authors engineering-team \
    --status Accepted \
    --commit
```

**Commit created:**
```
docs(adr): Use TypeScript for Frontend [Accepted]
```

## Troubleshooting

### No input provided error

**Problem:** `greybeard adr-save` complains about no input.

**Solution:** Pipe in a review:
```bash
# Wrong
greybeard adr-save --title "..."

# Right
greybeard analyze < design.md | greybeard adr-save --title "..."
```

### Missing --title

**Problem:** `--title` is required but you forgot it.

**Solution:** Always specify a title:
```bash
greybeard analyze < design.md | \
  greybeard adr-save --title "Your Decision"
```

### ADR file not created

**Problem:** No file appears in `docs/adr/`.

**Solution:** Check that the directory exists:
```bash
mkdir -p docs/adr
greybeard analyze < design.md | greybeard adr-save --title "..."
```

### Git commit failed

**Problem:** Using `--commit` but getting git errors.

**Solution:** Ensure you're in a git repository:
```bash
git init              # If no repo
git config user.name "Your Name"
git config user.email "you@example.com"

greybeard analyze < design.md | \
  greybeard adr-save \
    --title "..." \
    --commit
```

## See Also

- [ADR Format Standard](https://adr.github.io/)
- [greybeard Analyze Guide](./getting-started.md)
- [Decision History](./history.md)
