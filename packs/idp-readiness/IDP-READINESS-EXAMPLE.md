# IDP Readiness Pack: Real-World Example

## Scenario: Standardizing Database Provisioning

### The Proposal

"Team A has a Terraform module for spinning up RDS instances. Team B built their own in CloudFormation. Team C uses a Ruby script. We should build a self-service database provisioning platform."

**Planned solution:** Custom Go CLI, GitOps-based approval workflow, automatic backups, custom monitoring

**Timeline:** 8 weeks
**Team size:** 3 platform engineers
**Frequency:** Teams provision databases ~1 time per month (maybe 30/year across the company)

---

### What IDP Readiness Would Ask

**Document First: Do You Actually Need Automation?**

"How long does it take to provision a database today?"

"Manual process: 2-3 days (waiting for approval, then running commands), but the actual work is 20 minutes of Terraform."

→ "Step one is not a CLI. Step one is a 2-page wiki document describing the standard approach and how to use the existing Terraform module."

**The Maturity Curve**

1. **Documentation phase** (this week): Document how to provision, with a standard Terraform module
2. **Process phase** (next month): Create a PR template. Approvals happen in code review.
3. **Automation phase** (in 6 months, if needed): Auto-approve standard configurations, reject non-standard ones

**Developer Pain First**

"Is this driven by developer pain or platform engineer ideas?"

"Teams complain about waiting 2-3 days for approval."

→ "The problem isn't 'we need a CLI' — the problem is 'approval is slow.' Have you tried: faster approval SLA, self-service approval for standard configs in the PR, or async approval so it doesn't block deployment?"

**Complexity Budget**

3 platform engineers, 8 weeks, for a feature used 30 times/year.

- That's 1920 engineer-hours for ~480 operations/year
- Each operation "saves" 20 minutes (vs. manual Terraform)
- Total time saved: ~160 hours/year
- You're spending 12x the time you'd save

**Stage-Appropriate Question**

"If you had to ship this in 1 week instead of 8 weeks, what's the minimum viable version?"

"1. A documented standard. 2. A repo with the approved Terraform modules. 3. A PR checklist."

→ "That's already better than the manual chaos. Build that first. In 6 months, if teams are still complaining, build the CLI. You'll know what to build because you'll have seen the patterns."

---

### The Real Decision

**Skip the 8-week platform build.** Start with documentation, then a process, then automation _only if the pain justifies the complexity._

---

_This example demonstrates how IDP Readiness prevents premature platform automation and pushes toward documentation and process first._
