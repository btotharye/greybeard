# On-Call Future You: Real-World Example

## Scenario: Deploying a Data Pipeline Without Alerts

### The Proposal

We're building a batch data pipeline that runs every hour:

**What happens:**

- Extracts data from 3 sources
- Transforms and normalizes
- Loads into data warehouse
- Takes 45 minutes to run

**Deployment plan:**

- "It runs in batch, so failures aren't user-facing"
- "We have logs"
- "We'll monitor it"

---

### What On-Call Future You Would Flag

**Silence is Failure**

The biggest risk: "This runs, then nothing. No error, no alert, just wrong data for 2 hours."

- How does the on-call engineer know the pipeline failed?
- What dashboard tells them: "This should have completed by 1:15am but it's 5am"?
- Is there an alert when the pipeline is still running 2 hours later?

**Recovery Story**

- If the pipeline fails at 3am, what's the runbook?
- Can you re-run a partial load, or do you restart from scratch?
- How long does it take to go from "pager fires" to "we've re-run the corrected data"?
- Does the data warehouse have a rollback story, or is the bad data already propagated to reports?

**Operational Readiness**

Before deploying this pipeline:

1. You need an alert when it doesn't complete on time
2. You need a runbook for common failure modes (stalled extraction, transformation error, load lock)
3. You need monitoring on data freshness, not just job success
4. You need a way to validate the data after loading (row count sanity check, minimum/maximum checks)

---

### What Gets Built as a Result

✅ Alert when pipeline doesn't complete within SLA
✅ Monitoring on each stage: extract, transform, load
✅ Data validation dashboard showing data freshness
✅ Automated rollback for obvious data quality issues
✅ Runbook with the exact sequence to re-run a failed pipeline

---

_This example demonstrates how On-Call Future You forces you to think about what happens when things fail silently — and build the observability to catch it before data quality degrades._
