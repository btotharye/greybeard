# Data Migrations Pack: Real-World Example

## Scenario: Adding a Unique Constraint to an Existing Column

### The Proposal

"We want to ensure email addresses are unique. We're adding a unique constraint to the `email` column in the `users` table."

**Database:** PostgreSQL
**Table size:** 50 million rows
**Typical concurrent write load:** 500 writes/second
**Requirement:** Zero-downtime, no maintenance window

---

### What Data Migrations Would Ask

**1. Lock Acquisition and Duration**

"How long does this lock hold the table?"

Naive approach:

```sql
ALTER TABLE users ADD CONSTRAINT users_email_unique UNIQUE (email);
```

This acquires an **exclusive lock** on the table for the entire constraint creation. At 500 writes/second:

- Lock time: ~5-15 minutes (depending on index creation speed and disk I/O)
- Impact: All writes blocked for 5-15 minutes

**That's not zero-downtime.**

**2. The Zero-Downtime Pattern**

Instead, use the **expand-contract** pattern:

**Step 1 (Deploy 1):** Create a non-unique index concurrently (doesn't block writes)

```sql
CREATE UNIQUE INDEX CONCURRENTLY users_email_unique_idx ON users(email)
WHERE email IS NOT NULL;
```

- Time: 10-20 minutes of building (non-blocking, concurrent reads/writes work)
- Lock time: 0 seconds (CONCURRENTLY keyword)

**Step 2 (Deploy 1):** Add the constraint using the index (fast, exclusive lock is brief)

```sql
ALTER TABLE users ADD CONSTRAINT users_email_unique UNIQUE USING INDEX users_email_unique_idx;
```

- Lock time: < 1 second (just adding metadata)

**Step 3:** Validate existing data

```sql
SELECT COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;
```

If this returns rows, you have duplicate emails. You need to:

- Decide which one is "canonical"
- Merge the rows or delete duplicates
- Only then add the constraint

---

### Application Compatibility

**Question:** "Can the application run against both old and new schema?"

- Old schema: No unique constraint
- New schema: Unique constraint exists

If the application ever writes the same email twice (orphaned index, race condition, etc.), this will fail.

**Better approach:**

1. Add the index (application sees it but doesn't enforce it)
2. Update application code to check uniqueness on write
3. Deploy application update
4. Add the database constraint (now redundant but defensive)

This way, the constraint is a safety net, not a breaking change.

---

### Rollback Strategy

**Question:** "Is this rollback actually possible after you've added the constraint?"

Forward: ✅ Adding a constraint is additive
Backward: ❌ If you added the constraint and data is depending on it, removing it is risky

**Better rollback:**

1. If constraint fails to add: Application is unaffected (backward compatible)
2. If you realize you need to modify the constraint: You have to rebuild the index

**Validation Plan**

Before considering this "done," verify:

- [ ] Constraint was created successfully
- [ ] No duplicate emails exist (query above)
- [ ] Application write performance unaffected (check query logs / APM)
- [ ] No deadlocks related to the new constraint (check PostgreSQL logs)

---

### Estimated Time

- Index creation: 15 minutes (non-blocking)
- Constraint addition: 30 seconds (exclusive lock, very quick)
- Deployment: 5 minutes
- **Total: ~20 minutes, mostly waiting for index build (non-blocking)**

Not: "Oh, we'll just add a constraint, what's the risk?"
But: "We need a deployment strategy that doesn't block writes for 10 minutes."

---

_This example demonstrates how Data Migrations forces you to think through lock contention, zero-downtime patterns, and validates that your assumptions actual hold on production data._
