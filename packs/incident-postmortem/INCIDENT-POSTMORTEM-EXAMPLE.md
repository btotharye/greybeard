# Incident Postmortem Pack: Real-World Example

## Scenario: Database Replication Lag Causes Stale Data

### The Proposal (Postmortem to Review)

**Incident:** Users saw their recently-created comments not appear for 2-3 minutes

**Timeline:**

- 14:32: User submits comment, sees success response
- 14:33: User refreshes feed, comment missing
- 14:35: Comment appears

**Root Cause (as written):** "Database replication lag was higher than expected due to network congestion"

**Action Items:**

- [ ] Monitor replication lag more closely - TBD owner, TBD date
- [ ] Consider read replicas in same region - TBD owner, TBD date
- [ ] Engineer to investigate network - unassigned, "when there's time"

---

### What Incident Postmortem Would Flag

**1. "Replication Lag" Isn't a Root Cause, It's a Symptom**

Question: "Why was replication lag _possible_ at all?"

You're reading from replicas. Why did we architect it so that **reading from replication lag was possible**?

Better root cause:

- "We don't have read-after-write consistency for user-generated content"
- "Application doesn't handle replication lag — it assumes recent writes are immediately readable"
- "Database architecture allows multiple seconds of lag without our awareness"

**2. Blameless Review**

Current language: "...due to network congestion" (→ implies an operator or network team did something wrong)

Better framing: "The application assumes [assumption], but the system doesn't guarantee [guarantee]. Network variance exposed this gap."

**3. Action Item Quality**

Current: "Monitor replication lag more closely - TBD owner, TBD date"

Problems: No owner, no date, no success criteria, vague action

Better: "By [date], add alerting on replica lag > 500ms. Owner: [person]. Success criteria: [alert fires, is actionable within 5 minutes]"

**4. What Would Have Caught This?**

"Why don't we have monitoring that detects when replication lag exceeds acceptable thresholds?"

This should have been a detection question in the postmortem, not something discovered after an incident.

**5. The System Questions**

Instead of "engineer will investigate network," ask:

- "Do we know what the normal range for replication lag is?"
- "When replication lag exceeds X ms, what should the application do? (Fall back to primary? Show cached data? Show a 'data might be stale' message?)"
- "Why does the application not use read-after-write consistency for user operations?"

---

### Better Action Items

✅ **By [date], implement read-after-write consistency for comment operations** - Owner: [person]

- Read comments from primary database for 30 seconds after user creates, then fall back to replica
- Success: Users see their own comments immediately, latency <50ms

✅ **By [date], add monitoring and alerting for replica lag > 500ms** - Owner: [person]

- Alert to on-call engineer, is actionable (runbook describes mitigation steps)

✅ **By [date], document the architectural assumption and its limits** - Owner: [person]

- Decision log: "We use read replicas. Acceptable lag is X ms. Our app handles lag by [strategy]."

---

_This example demonstrates how Incident Postmortem separates symptoms from root causes, drives specific preventative action, and avoids theater in favor of systemic change._
