# Staff Core Pack: Real-World Example

## Scenario: Refactoring the Monolith into Microservices

### The Proposal (Without Greybeard Review)

Our engineering team wants to break up our monolithic backend into microservices:

**Benefits claimed:**

- "Better scaling for specific services"
- "Cleaner code boundaries"
- "Faster deployment cycles"
- "Teams can work independently"

**Timeline:** 12 weeks of engineering effort
**Current team size:** 6 engineers
**Current monolith age:** 3 years

---

### What Greybeard Staff-Core Would Ask

**Ownership & Accountability**

- Who owns the ordering service when things go wrong? Is it Team A, the platform team, or "whoever touched it last"?
- When this microservice has a bug, how does the incident response differ from debugging the monolith?
- In 6 months when one engineer leaves, who understands the network topology and failure cascades?

**Operational Impact**

- How does a database migration work when you have 8 services with different schemas?
- What happens if the payment service fails? What's the cascading failure mode?
- The monolith runs in 2 regions. How does the distributed system change the deployment story?

**Long-term Cost**

- We have 6 engineers. Will we need to hire to operate this, or is someone going on-call for multiple services?
- The monolith has one database. Microservices means eventual consistency. Have we modeled the failure modes?
- Debugging p99 latency in a monolith means one code path. In microservices, it's a trace through 8 services. What's the observability tax?

**The Real Question**

Before 12 weeks of work for a 6-person team, ask:

- "Is scaling actually the bottleneck right now, or is it developer productivity?"
- "Could we solve the code-boundary problem with better packages in the monolith?"
- "What problem are we trying to solve that we can't solve today?"

**Staff engineers are skeptical of complexity that doesn't pay for itself yet.**

---

_This example demonstrates how the Staff-Core pack evaluates the human and operational cost of architectural decisions, not just the technical benefits._
