# Example: Startup Pragmatist Input
# Feed this to: cat examples/inputs/startup-pragmatist-example.md | greybeard analyze --pack startup-pragmatist

# Design Doc: Event Bus Architecture for Herp Ops

## Summary
We are proposing to replace direct database writes with an event-driven architecture
using Apache Kafka. All services will publish domain events to Kafka topics. A separate
consumer service will handle persistence, cache invalidation, and downstream notifications.

## Motivation
- Decouples producers from consumers
- Enables event replay for debugging
- Future-proof for microservices expansion
- Industry standard pattern used at Netflix, Uber, LinkedIn

## Proposed Architecture
- Kafka cluster (3 brokers, replication factor 3)
- Schema Registry for Avro event schemas
- Producer SDK library shared across services
- Consumer group per downstream concern (DB write, cache, notifications, analytics)
- Dead letter queue for failed events
- Event sourcing for the reptile aggregate

## Current Scale
- 3 registered users
- ~50 API requests/day
- Single Railway service (1 instance)
- Single Postgres database
- 1 engineer (part-time)

## Timeline
- Week 1-2: Kafka cluster setup and SDK
- Week 3-4: Migrate feeding log writes to events
- Week 5-8: Migrate all writes to event-driven
- Week 9-12: Event sourcing for reptile aggregate

## Risks
- Complexity increase
- Operational overhead of Kafka
- Learning curve for event sourcing
