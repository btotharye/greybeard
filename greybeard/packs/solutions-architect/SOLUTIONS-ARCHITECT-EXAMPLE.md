# Solutions Architect Pack: Real-World Example

## Scenario: Internal Approval Workflow System

### The Proposal

"We need an internal approval workflow system. Teams have different approval requirements:

- Finance needs 2-level sign-off
- HR needs specific role approval
- Engineering needs team lead approval

We should build a flexible workflow engine to handle all these cases."

**Scope:** 6-week project, custom domain language for workflow definitions, audit trail, notifications

---

### What Solutions Architect Would Ask

**Is This a Technology Problem?**

The first question: "Are the different approval flows actually different, or are they the same thing with different role assignments?"

Answer: "They're mostly the same — someone requests approval, one or more people approve, the system records it and notifies them."

→ **This is not a "requirement for complexity" — it's a requirement to model roles correctly.**

**Build vs Buy vs Process**

"Jira Approvals, Notion, Zapier, or a dozen other tools can handle this for $50/month. What makes this expensive to build ourselves?"

"We need custom integrations with our HR system."

→ "That's a real constraint. But do you need a custom workflow engine, or do you need a 2-week integration layer between a standard approval platform and your HR system?"

**Entity Modeling: Where Does This Really Live?**

"Approval workflows are fundamentally about your org structure — who can approve what. You already have an org structure somewhere. Is the problem 'we need a workflow engine' or 'we need to make our org structure queryable for approvals'?"

**Simpler Alternative**

Before building a workflow engine:

1. Model two entities: **requests** and **required_approvers**
2. Build a simple table: "For insurance claims, the required approvers are: [role list]"
3. Build the notification/UI around that table
4. If 80% of your cases fit this model, you've solved the problem for 20% of the complexity

---

### The Architecture Question

**The problem:** "We need flexible, configurable approval workflows"

**The tempting solution:** "Build a domain-specific language or workflow builder"

**The architectural decision:** "Start with a data-driven approach (configuration tables), and only build a DSL if you discover you can't express your actual requirements in that simpler model."

The DSL can wait 6 months. You don't need it today.

---

_This example demonstrates how Solutions Architect separates the actual problem (modeling approval authority) from the proposed technical solution (workflow engine) and finds simpler alternatives._
