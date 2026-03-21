# SLO Agent - Service Level Objective Recommendations

The SLO Agent analyzes code and recommends appropriate Service Level Objective (SLO) targets based on service type, code patterns, and deployment context.

## Overview

SLOs are critical for setting clear expectations about reliability, latency, and error budgets. The SLO Agent helps you determine appropriate targets by analyzing:

- **Code patterns**: Database calls, HTTP requests, caching, retry logic, error handling, monitoring
- **Repository structure**: Tests, Docker, Kubernetes configuration, monitoring setup
- **Service type**: Explicit classification or auto-detected from code patterns
- **Context**: User count, criticality, business impact

## Service Types

### SaaS (User-Facing Services)
- User-visible availability and latency matter directly
- **Typical targets**: 99.9% availability, p99 latency < 200ms, < 0.1% error rate
- **Example**: REST API, web dashboard, mobile backend

### Batch Jobs
- Time-flexible, correctness-sensitive, chained dependencies common
- **Typical targets**: 95% availability, < 1 hour duration, < 5% error rate
- **Example**: Data pipeline, nightly ETL, report generation

### Critical Infrastructure
- Gateway, auth, platform services that other services depend on
- **Typical targets**: 99.95% availability, p99 latency < 50ms, < 0.01% error rate
- **Example**: Auth service, API gateway, database proxy

### Background Jobs
- Async workers, eventually-consistent, invisible to direct users
- **Typical targets**: 98% availability, task latency < 5 min, < 1% error rate
- **Example**: Email worker, notification queue, async task processor

## CLI Usage

### Basic SLO Check

```bash
# Analyze code from stdin
git diff main | greybeard slo-check

# Analyze a file
greybeard slo-check --file service.py

# Explicit service type
cat api.py | greybeard slo-check --context "service-type:saas"
```

### With Context Flags

```bash
# Specify service type
greybeard slo-check --context "service-type:critical-infra"

# Multiple context flags
greybeard slo-check \
  --context "service-type:saas" \
  --context "service-name:user-api" \
  --context "users:50000"

# With repository context
greybeard slo-check \
  --repo /path/to/api \
  --context "service-type:saas"
```

### Output Formats

```bash
# Table (default)
greybeard slo-check --output table

# JSON (for parsing/integration)
greybeard slo-check --output json

# Markdown (for documentation)
greybeard slo-check --output markdown > slo-targets.md
```

## Code Pattern Detection

The agent analyzes code for reliability-relevant patterns:

| Pattern | Detected By | Impact |
|---------|-----------|--------|
| Database calls | SELECT, INSERT, query(), execute() | Latency, availability |
| HTTP calls | requests, urllib, httpx, fetch | Timeouts, retries needed |
| Caching | redis, memcached, @cache, lru_cache | Latency optimization |
| Retry logic | retry, backoff, exponential | Failure recovery |
| Error handling | try, except, error handlers | Reliability |
| Async/await | async, await, asyncio | Concurrency model |
| Monitoring | logging, prometheus, datadog, tracing | Observability |
| Timeouts | timeout, deadline, ttl | Failure isolation |

## SLO Targets by Type

### SaaS

| Metric | Target | Range | Rationale |
|--------|--------|-------|-----------|
| Availability | 99.9% | 99.5% - 99.95% | High user visibility; ~43 min/month acceptable downtime |
| Latency (p99) | < 200ms | < 100ms - < 500ms | Interactive; users notice slow responses |
| Error Rate | < 0.1% | < 0.05% - < 0.5% | Errors are visible; user-facing impact |

### Batch

| Metric | Target | Range | Rationale |
|--------|--------|-------|-----------|
| Availability | 95% | 90% - 99% | Time-flexible; retryable; ~1.5 days/month downtime acceptable |
| Job Duration (p95) | < 1 hour | < 30min - < 4 hours | Batch windows are flexible but finite |
| Error Rate | < 5% | < 1% - < 10% | Transient failures acceptable if idempotent |

### Critical Infrastructure

| Metric | Target | Range | Rationale |
|--------|--------|-------|-----------|
| Availability | 99.95% | 99.9% - 99.99% | Impacts all downstream services; ~21 min/month |
| Latency (p99) | < 50ms | < 10ms - < 100ms | Critical path multiplier; tight budget |
| Error Rate | < 0.01% | < 0.001% - < 0.1% | Cascading failures; very low tolerance |

### Background Jobs

| Metric | Target | Range | Rationale |
|--------|--------|-------|-----------|
| Availability | 98% | 95% - 99.5% | Users don't wait synchronously; ~7.2 hours/month |
| Task Latency (p95) | < 5 min | < 1min - < 30min | Eventually-consistent; async context |
| Error Rate | < 1% | < 0.1% - < 5% | Async can retry; reasonable error budget |

## Output Example

```json
{
  "service_type": "saas",
  "service_name": "user-api",
  "targets": [
    {
      "metric": "availability",
      "target": "99.9%",
      "range": ["99.5%", "99.95%"],
      "rationale": "User-facing service; high availability expected. 99.9% = ~43 min/month downtime."
    },
    {
      "metric": "latency (p99)",
      "target": "< 200ms",
      "range": ["< 100ms", "< 500ms"],
      "rationale": "Interactive service; users expect responsive performance."
    },
    {
      "metric": "error_rate",
      "target": "< 0.1%",
      "range": ["< 0.05%", "< 0.5%"],
      "rationale": "User-facing errors are visible; low error tolerance."
    }
  ],
  "context_signals": {
    "code_indicators": {
      "has_db_calls": true,
      "has_http_calls": true,
      "has_caching": true,
      "has_retry_logic": true,
      "has_error_handling": true,
      "has_async": false,
      "has_monitoring": true,
      "has_timeout": true
    }
  },
  "confidence": 0.75,
  "notes": "Database calls have caching. HTTP calls have retries and timeouts. Good observability."
}
```

## Recommendations & Notes

The agent generates context-specific recommendations:

- ⚠️ **Error Handling**: No try/except detected → add proper error handling
- 📊 **Monitoring**: No logging detected → instrument with metrics and logs
- ⏱️ **Timeouts**: No timeouts on external calls → prevent cascading failures
- 💾 **Caching**: DB calls without cache → consider Redis/memcached
- 🔄 **Retries**: HTTP calls without retry logic → add exponential backoff
- 🔁 **Dead Letter Queue**: Background jobs without retries → implement DLQ

## Integration with greybeard

The SLO Agent integrates with greybeard's content pack system. Use SLO-specific packs for domain-specific guidance:

```bash
# Load SLO pack for SaaS perspective
greybeard analyze --pack slo-saas < code.py

# Load SLO pack for batch jobs
greybeard analyze --pack slo-batch < pipeline.py

# Load SLO pack for critical infra
greybeard analyze --pack slo-critical-infra < auth_service.py
```

## Available SLO Packs

- `slo-saas` - User-facing SaaS perspectives and heuristics
- `slo-batch` - Batch job and scheduled task guidance
- `slo-critical-infra` - Platform and gateway SLO thinking
- `slo-background-jobs` - Async worker and queue guidance

## Python API

```python
from greybeard.agents import SLOAgent

agent = SLOAgent()

# Analyze code with context
recommendation = agent.analyze(
    code_snippet="""
    @app.get("/api/users")
    def get_users():
        return db.query(User).all()
    """,
    service_type="saas",
    context={
        "service-name": "user-api",
        "users": "50000",
    }
)

# Get targets
for target in recommendation.targets:
    print(f"{target.metric}: {target.target}")
    print(f"  Rationale: {target.rationale}")

# Get JSON for integration
import json
data = recommendation.to_dict()
print(json.dumps(data, indent=2))
```

## Testing

The SLO Agent has comprehensive test coverage:

```bash
# Run all SLO Agent tests
pytest tests/test_slo_agent.py -v

# Run with coverage
pytest tests/test_slo_agent.py --cov=greybeard.agents.slo_agent

# Run specific test class
pytest tests/test_slo_agent.py::TestServiceTypeDetection -v
```

Test coverage: **93%** of agent code

Test categories:
- **Basic functionality** (5 tests) - Initialization, analysis, serialization
- **Service type detection** (5 tests) - Auto-detect SaaS, batch, critical-infra, background
- **SLO target generation** (4 tests) - Proper targets for each type
- **Code analysis** (8 tests) - Pattern detection (DB, HTTP, caching, retries, etc.)
- **Repository analysis** (4 tests) - Docker, K8s, tests, file counting
- **Context integration** (3 tests) - Service name, explicit type, multiple flags
- **Recommendations** (4 tests) - Note generation for missing patterns
- **Confidence scoring** (2 tests) - Confidence ranges and type-specific scoring
- **CLI integration** (1 test) - Command registration
- **Serialization** (1 test) - JSON round-trip

## Architecture

```
greybeard/
├── agents/
│   ├── __init__.py           # Exports SLOAgent, SLORecommendation, etc.
│   └── slo_agent.py          # SLOAgent implementation
├── cli_slo.py                # slo-check CLI command
├── cli.py                    # CLI integration (imports slo_check)
└── packs/
    └── slo-patterns/
        ├── saas.yaml         # SaaS SLO pack
        ├── batch.yaml        # Batch job SLO pack
        ├── critical-infra.yaml # Critical infrastructure SLO pack
        └── background-jobs.yaml # Background job SLO pack

tests/
└── test_slo_agent.py         # 37 comprehensive tests
```

## Future Enhancements

- **Machine learning**: Train on production SLOs to improve recommendations
- **Cost analysis**: Estimate infrastructure cost for different SLO levels
- **Trend detection**: Analyze historical performance vs. SLO targets
- **Multi-service orchestration**: Recommend SLOs for service meshes
- **Budget calculations**: Error budget tracking and alerts
- **LLM-powered guidance**: Use LLM to provide detailed SLO recommendations based on code context

## References

- [Google SRE Book - Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Prometheus - SLO Best Practices](https://prometheus.io/docs/)
- [AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/)
