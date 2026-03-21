# SLO Agent Guide

The SLO Agent helps you determine appropriate Service Level Objective (SLO) targets for your services by analyzing code patterns, repository structure, and deployment context. This guide covers everything from quick starts to advanced integration.

## What is an SLO?

A **Service Level Objective (SLO)** is a target level of service performance. It defines what "good" looks like for your service:

- **Availability** — "The service is up and responding" (e.g., 99.9%)
- **Latency** — "Requests complete quickly" (e.g., p99 < 200ms)
- **Error Rate** — "Requests succeed" (e.g., < 0.1% errors)

SLOs are not guesses—they should be based on **business impact** and **service characteristics**.

---

## Overview

The SLO Agent analyzes:

- **Code patterns**: Database calls, HTTP requests, caching, retry logic, error handling, monitoring
- **Repository structure**: Tests, Docker, Kubernetes, monitoring setup
- **Service type**: Explicitly provided or auto-detected from code
- **Context**: User count, service criticality, business impact

It then recommends SLO targets with confidence scores and actionable recommendations.

---

## Service Types

Understanding your service type is key to appropriate SLOs.

### SaaS (User-Facing Services)

User-visible availability and latency matter directly. Examples:
- REST APIs serving user requests
- Web dashboards
- Mobile backends
- Real-time chat or notification systems

**Typical targets:**
- **Availability**: 99.9% (~43 min/month downtime)
- **Latency (p99)**: < 200ms
- **Error rate**: < 0.1%

**Why these targets?**
Users notice delays over 100ms and errors immediately. Downtime frustrates users and damages trust.

### Critical Infrastructure

Services that other services depend on. Examples:
- Authentication/authorization services
- API gateways
- Database proxies
- Service meshes
- Load balancers

**Typical targets:**
- **Availability**: 99.95% (~21 min/month downtime)
- **Latency (p99)**: < 50ms
- **Error rate**: < 0.01%

**Why these targets?**
Failures cascade across all dependent services. A 1-second latency adds to every downstream request.

### Batch Jobs

Time-flexible, scheduled tasks. Examples:
- Data pipelines and ETL
- Report generation
- Nightly backups
- Async processing queues

**Typical targets:**
- **Availability**: 95% (~1.5 days/month downtime)
- **Job duration (p95)**: < 1 hour
- **Error rate**: < 5%

**Why these targets?**
Batch jobs are not time-critical for individual users. Retries and delayed execution are acceptable.

### Background Jobs

Async workers that process queue items. Examples:
- Email delivery workers
- Notification systems
- Webhook handlers
- Async task processors

**Typical targets:**
- **Availability**: 98% (~7.2 hours/month downtime)
- **Task latency (p95)**: < 5 minutes
- **Error rate**: < 1%

**Why these targets?**
Users don't wait synchronously. Eventually-consistent delivery is acceptable. Retries and backoff are expected.

---

## Quick Start

### Basic SLO Check

Analyze code from stdin:

```bash
# Check a diff against main
git diff main | greybeard slo-check

# Check a file
greybeard slo-check --file service.py

# Check stdin directly
cat api.py | greybeard slo-check
```

### Specify Service Type

```bash
# Explicit service type
greybeard slo-check --context "service-type:saas"

# With service name
greybeard slo-check --context "service-type:saas" --context "service-name:user-api"

# With user count context
greybeard slo-check \
  --context "service-type:saas" \
  --context "users:50000"
```

### View Results

By default, results print as a table:

```bash
greybeard slo-check < api.py
```

Output:
```
Service Type: SaaS
Service Name: user-api
Confidence: 0.75

Targets:
┌──────────────────┬────────────┬─────────────────────┐
│ Metric           │ Target     │ Range               │
├──────────────────┼────────────┼─────────────────────┤
│ Availability     │ 99.9%      │ 99.5% - 99.95%      │
│ Latency (p99)    │ < 200ms    │ < 100ms - < 500ms   │
│ Error Rate       │ < 0.1%     │ < 0.05% - < 0.5%    │
└──────────────────┴────────────┴─────────────────────┘

Recommendations:
- Add timeouts to external HTTP calls
- Implement exponential backoff for retries
```

---

## CLI Usage

### Command Syntax

```bash
greybeard slo-check [OPTIONS] [FILE]
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| `--file` | PATH | File to analyze (instead of stdin) |
| `--context` | TEXT | Context flag (repeatable). Format: `key:value` |
| `--repo` | PATH | Repository root path for structure analysis |
| `--output` | TEXT | Output format: `table` (default), `json`, `markdown` |
| `--service-type` | TEXT | Override service type detection. One of: `saas`, `critical-infra`, `batch`, `background-jobs` |
| `--help` | - | Show help and exit |

### Context Flags

Context flags provide additional information for more accurate recommendations.

**Common context flags:**

```bash
# Service information
--context "service-type:saas"
--context "service-name:user-api"
--context "team:platform"

# Business context
--context "users:50000"
--context "critical:true"
--context "sla:99.99%"

# Technical context
--context "db:postgresql"
--context "cache:redis"
--context "queue:kafka"
```

**Examples:**

```bash
# SaaS with business context
greybeard slo-check \
  --context "service-type:saas" \
  --context "service-name:user-api" \
  --context "users:50000" \
  --context "critical:true"

# Batch job with timing context
greybeard slo-check \
  --context "service-type:batch" \
  --context "runs:nightly" \
  --context "max-duration:1h"

# Critical infrastructure
greybeard slo-check \
  --repo /path/to/auth-service \
  --context "service-type:critical-infra" \
  --context "downstream-services:12"
```

### Output Formats

#### Table (Default)

Human-readable table output:

```bash
greybeard slo-check --output table < api.py
```

#### JSON

Structured JSON for parsing, integration, or automation:

```bash
greybeard slo-check --output json < api.py
```

Parse with jq:

```bash
greybeard slo-check --output json < api.py | jq '.targets[] | .metric'
```

#### Markdown

Documentation-ready markdown output:

```bash
greybeard slo-check --output markdown < api.py > docs/slo-targets.md
```

Great for adding to ADRs or runbooks.

---

## Code Pattern Detection

The SLO Agent analyzes your code for patterns that impact reliability:

| Pattern | Detected By | Impact | Signal |
|---------|-----------|--------|--------|
| **Database calls** | SELECT, INSERT, query(), execute(), ORM methods | Latency, availability | Caching needed? |
| **HTTP requests** | requests, urllib, httpx, fetch, client calls | Timeouts, retries | Exponential backoff? |
| **Caching** | redis, memcached, @cache, lru_cache, cache decorators | Latency improvement | Cache hit rate? |
| **Retry logic** | retry, backoff, exponential, jitter | Failure recovery | Idempotent? |
| **Error handling** | try, except, error handlers, middleware | Reliability | Graceful degradation? |
| **Async/await** | async, await, asyncio, coroutines | Concurrency model | Resource pooling? |
| **Monitoring** | logging, prometheus, datadog, tracing, StatsD | Observability | Alert coverage? |
| **Timeouts** | timeout, deadline, ttl, max_time | Failure isolation | All calls covered? |

The agent looks for these patterns and adjusts recommendations accordingly.

---

## SLO Targets by Service Type

### SaaS

| Metric | Target | Range | Downtime/month |
|--------|--------|-------|-----------------|
| **Availability** | 99.9% | 99.5% - 99.95% | ~43 minutes |
| **Latency (p99)** | < 200ms | < 100ms - < 500ms | — |
| **Error Rate** | < 0.1% | < 0.05% - < 0.5% | — |

**Rationale:**
- Users notice latency above 100ms and errors immediately
- User-facing impact directly affects business
- High availability expectations because users depend on service

**Example targets for different user counts:**
- < 1,000 users: Can target 99.5% (more tolerance)
- 1,000-50,000 users: Target 99.9% (typical SaaS)
- > 50,000 users: Consider 99.95% or higher

### Critical Infrastructure

| Metric | Target | Range | Downtime/month |
|--------|--------|-------|-----------------|
| **Availability** | 99.95% | 99.9% - 99.99% | ~21 minutes |
| **Latency (p99)** | < 50ms | < 10ms - < 100ms | — |
| **Error Rate** | < 0.01% | < 0.001% - < 0.1% | — |

**Rationale:**
- Failures cascade across all dependent services
- Latency adds to every downstream request (multiplier effect)
- Very low error tolerance to prevent cascading failures

**Examples:**
- Auth service: 99.95% availability, < 30ms latency
- API gateway: 99.99% availability, < 20ms latency
- Service mesh: 99.95% availability, < 50ms latency

### Batch Jobs

| Metric | Target | Range | Downtime/month |
|--------|--------|-------|-----------------|
| **Availability** | 95% | 90% - 99% | ~1.5 days |
| **Duration (p95)** | < 1 hour | < 30min - < 4 hours | — |
| **Error Rate** | < 5% | < 1% - < 10% | — |

**Rationale:**
- Time-flexible; users don't wait synchronously
- Transient failures are acceptable and retryable
- Batch windows provide flexibility for recovery

**Examples:**
- Data pipeline: 95% success, < 2 hours duration
- Report generation: 95% success, < 1 hour duration
- Nightly backups: 99% success (more critical), < 4 hours

### Background Jobs

| Metric | Target | Range | Downtime/month |
|--------|--------|-------|-----------------|
| **Availability** | 98% | 95% - 99.5% | ~7.2 hours |
| **Latency (p95)** | < 5 min | < 1min - < 30min | — |
| **Error Rate** | < 1% | < 0.1% - < 5% | — |

**Rationale:**
- Users don't wait synchronously for results
- Eventually-consistent delivery is acceptable
- Async can retry and apply backoff

**Examples:**
- Email delivery: 98% success, < 5 min delivery
- Notifications: 98% success, < 10 min delivery
- Webhook handlers: 95% success (retryable), < 5 min processing

---

## Analysis Output

### JSON Structure

When using `--output json`, the output contains:

```json
{
  "service_type": "saas",
  "service_name": "user-api",
  "targets": [
    {
      "metric": "availability",
      "target": "99.9%",
      "range": ["99.5%", "99.95%"],
      "rationale": "User-facing service..."
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
    },
    "repo_structure": {
      "has_tests": true,
      "test_count": 156,
      "has_docker": true,
      "has_k8s": true,
      "has_prometheus_metrics": true
    }
  },
  "confidence": 0.75,
  "notes": [
    "Database calls detected with caching — good pattern",
    "HTTP calls have retries and timeouts — solid",
    "Add more granular error handling"
  ],
  "recommendations": [
    {
      "category": "monitoring",
      "level": "warning",
      "message": "No explicit latency metrics detected"
    }
  ]
}
```

### Confidence Scoring

Confidence reflects how certain the agent is in its recommendations (0.0 to 1.0):

- **0.9+** — Highly confident. Clear code patterns and repo structure align with service type.
- **0.75-0.9** — Confident. Most patterns detected, some ambiguity.
- **0.5-0.75** — Moderate. Limited patterns detected; context helps.
- **< 0.5** — Low confidence. Insufficient signals; user should validate.

Factors affecting confidence:
- ✅ Code patterns match service type expectations
- ✅ Repository structure is complete (tests, monitoring, deployment)
- ✅ Explicit service type provided via context
- ❌ Generic code with few patterns detected
- ❌ Missing tests or monitoring setup
- ❌ No explicit context provided

---

## Integration with greybeard

The SLO Agent integrates with greybeard's **content pack system**. Load SLO-specific packs for domain-specific guidance:

### Available SLO Content Packs

- `slo-saas` — User-facing SaaS perspective and heuristics
- `slo-critical-infra` — Platform and gateway SLO thinking
- `slo-batch` — Batch job and scheduled task guidance
- `slo-background-jobs` — Async worker and queue guidance

### Using SLO Packs

Combine SLO check results with pack-based analysis:

```bash
# Run SLO agent
greybeard slo-check --output json < service.py > slo_targets.json

# Run analysis with SLO pack
greybeard analyze --pack slo-saas < service.py

# Combine both for full assessment
greybeard slo-check --context "service-type:saas" < service.py
greybeard analyze --pack slo-saas < service.py
```

### Custom Packs

Create a custom pack for your team's SLO philosophy:

**`teams/slo-mycompany.yaml`:**
```yaml
pack_name: slo-mycompany
description: Company SLO philosophy and targets

perspectives:
  - name: slo-assessment
    context: |
      Our SaaS targets are:
      - Availability: 99.9% (peak hours), 99.5% (off-peak)
      - Latency: p99 < 150ms for user-facing, < 50ms for critical infra
      - Error rate: < 0.05% user-facing, < 0.01% critical infra

      Consider these when setting SLOs:
      1. Is this service user-facing or internal?
      2. What are downstream dependencies?
      3. How would 1-hour downtime impact users?
      4. Can failures be retried idempotently?
```

Load with:
```bash
greybeard analyze --pack slo-mycompany < service.py
```

---

## Python API

Use the SLO Agent programmatically:

```python
from greybeard.agents import SLOAgent

# Create agent
agent = SLOAgent()

# Analyze code
recommendation = agent.analyze(
    code_snippet="""
    @app.get("/api/users")
    async def get_users():
        users = await db.query(User)
        return {"users": users}
    """,
    service_type="saas",
    context={
        "service-name": "user-api",
        "users": "50000",
    }
)

# Access results
print(f"Service type: {recommendation.service_type}")
print(f"Confidence: {recommendation.confidence}")

# Iterate targets
for target in recommendation.targets:
    print(f"\n{target.metric}:")
    print(f"  Target: {target.target}")
    print(f"  Range: {target.range}")
    print(f"  Rationale: {target.rationale}")

# Get JSON for integration
import json
data = recommendation.to_dict()
print(json.dumps(data, indent=2))

# Access code signals
signals = recommendation.context_signals
print(f"Has DB calls: {signals['code_indicators']['has_db_calls']}")
print(f"Has caching: {signals['code_indicators']['has_caching']}")

# Get recommendations
for rec in recommendation.recommendations:
    print(f"[{rec.level}] {rec.message}")
```

### Common Workflows

**Batch analysis of multiple files:**

```python
from pathlib import Path
from greybeard.agents import SLOAgent

agent = SLOAgent()

for py_file in Path("src").glob("**/*.py"):
    with open(py_file) as f:
        code = f.read()
    
    rec = agent.analyze(code)
    if rec.confidence < 0.5:
        print(f"⚠️  {py_file}: Low confidence (0.{int(rec.confidence*100)})")
```

**Integration with CI/CD:**

```python
from greybeard.agents import SLOAgent
import sys
import json

agent = SLOAgent()

# Analyze proposed changes
recommendation = agent.analyze(
    code_snippet=sys.stdin.read(),
    service_type="saas"
)

# Fail if SLOs not met
if recommendation.confidence < 0.7:
    print(f"Confidence too low: {recommendation.confidence}")
    sys.exit(1)

# Output for workflow
print(json.dumps(recommendation.to_dict()))
```

---

## Testing & Validation

### Local Testing

Test against your own services:

```bash
# Test current service
git diff main | greybeard slo-check --context "service-type:saas"

# Test API code
find src -name "*.py" -exec sh -c '
  echo "=== $1 ===" && greybeard slo-check --file "$1"
' _ {} \;

# Compare outputs
greybeard slo-check --output json < api.py > before.json
# Make changes...
greybeard slo-check --output json < api.py > after.json
diff before.json after.json
```

### Test Coverage

The SLO Agent has **93%** test coverage:

```bash
# Run SLO Agent tests
pytest tests/test_slo_agent.py -v

# Run with coverage report
pytest tests/test_slo_agent.py --cov=greybeard.agents.slo_agent

# See detailed coverage
pytest tests/test_slo_agent.py --cov=greybeard.agents.slo_agent --cov-report=html
# Open htmlcov/index.html
```

**Test categories (37 tests):**
- Basic functionality — Initialization, analysis, serialization
- Service type detection — Auto-detect SaaS, batch, critical-infra, background
- SLO target generation — Correct targets per service type
- Code analysis — Database, HTTP, caching, retry, error handling patterns
- Repository structure — Docker, Kubernetes, tests, metrics
- Context integration — Service name, explicit type, multiple flags
- Recommendations — Note generation for missing patterns
- Confidence scoring — Appropriate confidence ranges
- CLI integration — Command registration and invocation
- Serialization — JSON round-trip

---

## Examples

### Example 1: User-Facing REST API

```bash
# Analyze user API
cat src/apis/user.py | greybeard slo-check \
  --context "service-type:saas" \
  --context "service-name:user-api" \
  --context "users:50000"
```

Expected output:
```
Service Type: SaaS
Confidence: 0.82

Targets:
┌──────────────────┬────────────┬─────────────────────┐
│ Metric           │ Target     │ Range               │
├──────────────────┼────────────┼─────────────────────┤
│ Availability     │ 99.9%      │ 99.5% - 99.95%      │
│ Latency (p99)    │ < 200ms    │ < 100ms - < 500ms   │
│ Error Rate       │ < 0.1%     │ < 0.05% - < 0.5%    │
└──────────────────┴────────────┴─────────────────────┘

Code Signals:
✅ Database calls with caching detected
✅ HTTP calls with retry logic
✅ Error handling in place
⚠️  No timeout on external calls — add!
⚠️  Limited latency instrumentation
```

### Example 2: Batch Data Pipeline

```bash
# Analyze batch job
cat src/pipelines/nightly_etl.py | greybeard slo-check \
  --context "service-type:batch" \
  --context "runs:nightly" \
  --context "max-duration:1h"
```

Expected output:
```
Service Type: Batch
Confidence: 0.71

Targets:
┌──────────────────┬────────────┬─────────────────────┐
│ Metric           │ Target     │ Range               │
├──────────────────┼────────────┼─────────────────────┤
│ Availability     │ 95%        │ 90% - 99%           │
│ Duration (p95)   │ < 1 hour   │ < 30min - < 4 hours │
│ Error Rate       │ < 5%       │ < 1% - < 10%        │
└──────────────────┴────────────┴─────────────────────┘

Recommendations:
- Add idempotent handling for retries
- Implement dead-letter queue for failed items
- Add progress checkpointing for long runs
```

### Example 3: Authentication Service

```bash
# Analyze auth service
greybeard slo-check \
  --repo /path/to/auth-service \
  --context "service-type:critical-infra" \
  --context "service-name:auth" \
  --context "downstream-services:12"
```

Expected output:
```
Service Type: Critical Infrastructure
Confidence: 0.88

Targets:
┌──────────────────┬────────────┬─────────────────────┐
│ Metric           │ Target     │ Range               │
├──────────────────┼────────────┼─────────────────────┤
│ Availability     │ 99.95%     │ 99.9% - 99.99%      │
│ Latency (p99)    │ < 50ms     │ < 10ms - < 100ms    │
│ Error Rate       │ < 0.01%    │ < 0.001% - < 0.1%   │
└──────────────────┴────────────┴─────────────────────┘

Critical Signals:
✅ 12 downstream services depend on this
✅ Comprehensive monitoring and tracing
⚠️  Latency budget tight — optimize cache
🔴 No circuit breaker on external auth provider
```

---

## Troubleshooting

### Low Confidence Score

If you're getting confidence < 0.5:

1. **Check service type**: Ensure `--context "service-type:..."` is correct
2. **Add context**: More context flags improve confidence
3. **Verify code patterns**: Add monitoring, error handling, timeouts
4. **Run from repo root**: `--repo .` helps detect structure

```bash
# Debug: see what was detected
greybeard slo-check --output json < api.py | jq '.context_signals'
```

### Unexpected Targets

If targets don't match your expectations:

1. **Verify service type**: Is it correctly auto-detected or explicitly set?
2. **Check code patterns**: Run with `--output json` to see detected signals
3. **Add context**: Business context (user count, criticality) matters
4. **Review rationale**: Each target has a `rationale` explaining the choice

### Missing Recommendations

If no recommendations appear:

- Your code already has good patterns!
- Or detection might be missing some patterns
- Review the code signals in JSON output to see what was detected

---

## Best Practices

### 1. Set SLOs Early

Don't wait until production to think about SLOs. Use the SLO Agent early:

```bash
# During design/prototyping
git diff main | greybeard slo-check --context "service-type:saas"

# Before first deployment
greybeard slo-check \
  --repo . \
  --context "service-type:saas" \
  --context "launch:critical"
```

### 2. Document SLO Decisions

Save SLO recommendations to your ADR:

```bash
greybeard slo-check --output markdown > docs/adr/slo-targets.md
```

Then add to your ADR template:

```markdown
## SLO Targets

**Generated by SLO Agent on 2024-03-21**

[paste markdown output here]

**Team decision**: [Accept/Modify/Override with justification]
```

### 3. Validate Code Patterns

Before deploying, ensure code has the patterns your SLOs require:

- **SaaS 99.9%**: Needs retries, timeouts, error handling ✅
- **Critical infra**: Needs minimal latency, comprehensive monitoring ✅
- **Batch**: Needs idempotent retries and DLQ ✅

Use the context_signals output to validate:

```bash
greybeard slo-check --output json < api.py | jq '.context_signals.code_indicators'
```

### 4. Iterate with Your Team

Use the `--mentor` or `--coach` modes with greybeard for deeper discussion:

```bash
# Get mentoring on SLO philosophy
echo "We're building a user-facing API" | greybeard analyze --mode mentor

# Get help explaining to stakeholders
greybeard analyze --mode coach --context "audience:executives"
```

### 5. Monitor Against SLOs

Once targets are set, monitor them:

```yaml
# prometheus/recording_rules.yaml
groups:
  - name: slo.saas
    interval: 30s
    rules:
      - record: slo:availability:4w
        expr: (1 - rate(errors_total[4w]) / rate(requests_total[4w])) * 100
      
      - record: slo:latency:p99:4w
        expr: histogram_quantile(0.99, rate(request_duration_seconds_bucket[4w]))
      
      - record: slo:error_rate:4w
        expr: rate(errors_total[4w]) / rate(requests_total[4w]) * 100
```

---

## FAQ

**Q: Should all services have 99.9% availability?**

No. SLOs should match business needs:
- Low-traffic internal tools: 95% is fine
- User-facing: 99.9% is typical
- Critical infrastructure: 99.95%+

**Q: What if my code doesn't match the detected service type?**

Explicitly specify with `--context "service-type:..."`. The agent auto-detects but can be overridden.

**Q: How do I set SLOs for a microservice mesh?**

Set SLOs per service:
1. SaaS frontend: 99.9%
2. Critical infra services (auth, gateway): 99.95%
3. Backend workers: 98%

The compound availability might be lower, so design accordingly.

**Q: Can I use different SLOs for different time periods?**

Yes! Use time-based SLOs:
- Peak hours (9am-5pm): 99.95% (stricter)
- Off-peak: 99.5% (relaxed)
- Maintenance windows: excluded from SLO calculations

**Q: How do I track error budgets?**

Use monitoring:

```yaml
# If target is 99.9%, error budget is 0.1%
error_budget_threshold = (1 - 0.999) * 100  # 0.1%
remaining_budget = error_budget_threshold - actual_error_rate
```

When approaching zero budget, freeze deployments and focus on reliability.

---

## Next Steps

- Read [Creating Agents](creating_agents.md) for custom analysis agents
- Review [Content Packs](../guides/packs.md) to build custom SLO packs
- Check [CLI Reference](../reference/cli.md) for all commands
- See [Interactive Mode](interactive-mode.md) for deeper exploration
