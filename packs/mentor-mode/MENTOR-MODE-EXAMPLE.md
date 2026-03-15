# Mentor Mode Pack: Real-World Example

## Scenario: Caching Decisions and Cache Invalidation

### The Proposal

A senior engineer proposes adding Redis caching to the user profile endpoint:

**Code change:**

- Check cache for user ID
- If miss, query database
- Store in cache with 1-hour TTL

**The ask:** Code review to make sure it's correct

---

### What Mentor Mode Would Explain

**The Pattern Being Illustrated**

This is a classic "cache invalidation" problem, which has a famous quote: _"There are only two hard things in Computer Science: cache invalidation and naming things."_

The pattern here is:

- **Invalidation by TTL** (what your code does)
- **Invalidation by event** (when data changes, actively invalidate)
- **Invalidation by versioning** (include data version in cache key)

Each has different tradeoffs.

**Why This Matters at Scale**

At 10 requests/second with a database that can handle 1000 requests/second: caching doesn't help much.

At 10,000 requests/second with a database that can handle 1000 requests/second: caching is required, but now:

- If the TTL is 1 hour, stale data affects 3600 seconds of users (real impact)
- If the TTL is 1 minute, you still have 60 seconds of staleness (users see outdated profiles)
- If a profile is invalidated by TTL waiting for expiry, users see stale data even though you just updated their profile

**The Learning Point**

Don't ask: "Is this cache implementation correct?"

Ask: "What's the acceptable staleness window for this data? What happens to our product if a user updates their profile and still sees the old version for 60 seconds?"

**The Real Question for the Author**

"I see you're using a TTL-based invalidation. That works if staleness is acceptable. But have you thought about the case where a user updates their profile and the cache still returns the old data? Is 1 hour the right window, or should this be event-based when we know the profile changes?"

---

_This example demonstrates how Mentor Mode teaches reasoning patterns, not just pointing out what's wrong. It builds judgment._
