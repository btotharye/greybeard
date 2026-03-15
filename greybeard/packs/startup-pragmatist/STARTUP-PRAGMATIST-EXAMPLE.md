# Startup Pragmatist Pack: Real-World Example

## Scenario: Building a Distributed Message Queue

### The Proposal

"We're processing 100 events/second. Our current single-server Redis queue can't keep up. We should build a distributed message queue system."

**Proposal:** Implement Kafka from scratch, with a custom management plane and monitoring

**Current situation:**

- 8 engineers total
- Series A company, 18 months of runway
- 4 engineers needed to ship the product, 4 needed to build this queue system
- Kubernetes cluster already running

---

### What Startup Pragmatist Would Say

**Do You Actually Have The Problem?**

"You're processing 100 events/second today. What's the actual bottleneck?"

"Redis is at 80% CPU."

"On what operations? Enqueue only, or also dequeue?"

→ This is the first pragmatic question: **"Do we actually need distributed, or do we just need a better single-instance solution?"**

**Simpler Options (In Order)**

1. **Optimize Redis usage** (1 week): Better data structures, pipelining, different persistence options → might get you to 200 events/second

2. **Managed message queue** (1 day): AWS SQS / SNS or GCP Pub/Sub → handles 10,000s/sec, $100/month, zero ops overhead

3. **RabbitMQ** (1 week): Single instance, handles thousands/sec, battles-tested, ops is boring

4. **Kafka** (6 weeks minimum): Distributed, complex, requires operational expertise you don't have

**The Opportunity Cost Question**

"If you spend 6 weeks building Kafka plumbing, you can't build 6 weeks of product. What customer-facing features are you delaying?"

"Maybe... three months of features."

→ "So you're paying 3 months of product delay to avoid paying $2000/month for managed infrastructure. That's a bad tradeoff at this stage."

**Stage-Appropriate Complexity**

At Seed/Series A:

- You have product/engineer/customer fit questions to answer
- You don't have operations/scale expertise
- You can't afford 2 engineers to maintain custom distributed systems

**The Pragmatic Path**

1. **Immediate** (this week): Switch to AWS SQS, keep current code, see if it solves the problem
2. **In 6 months** (when you have real product-market fit): If you're at 1000 events/second and SQS is no longer cost-effective, reassess
3. **If you assess then**: You'll have more options (managed Kafka from Confluent, etc.) and more operational maturity

---

### The Real Question

"Is this complexity a feature of the solution, or a problem we actually have?"

You have a problem: "100 events/second is too many for our current queue."

The solution isn't "build Kafka." The solution is "pick something that handles 1000+ events/second for <$1000/month."

That's probably a managed service.

---

_This example demonstrates how Startup Pragmatist forces you to match complexity to your actual stage and constraints — shipping customer value often beats building "the right way."_
