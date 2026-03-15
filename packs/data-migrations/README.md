# Data Migrations Pack

The engineer who has learned database migration safety the hard way — reviews for zero-downtime patterns and blast radius.

## Quick Start

```bash
# Review a migration strategy or schema change
cat migration.md | greybeard analyze --pack data-migrations

# Learn zero-downtime migration patterns
cat migration.md | greybeard analyze --pack data-migrations --mode mentor
```

## Focus Areas

- **Lock Safety**: What locks does this acquire? For how long?
- **Zero-Downtime Patterns**: Can this run without a maintenance window?
- **Rollback Strategy**: Is rollback actually possible and tested?
- **Performance**: Will this cause lock contention or slow queries?

## When to Use This Pack

Use this pack when planning or reviewing schema changes and data migrations — especially for databases used in production with non-trivial data volumes.

---

_Created as part of the Greybeard community packs initiative._
