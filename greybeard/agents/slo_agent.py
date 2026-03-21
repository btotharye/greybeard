"""SLO/Observability Agent for analyzing code and recommending SLO targets.

Analyzes code patterns, architecture, and deployment context to recommend
appropriate SLO targets (latency, error rate, availability) based on
service type and criticality.

Supports patterns:
  - SaaS (user-facing services, strict SLOs)
  - Batch (time-insensitive jobs, relaxed availability)
  - Critical Infrastructure (platform services, high availability)
  - Background Jobs (async workers, lenient error budgets)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ServiceType(Enum):
    """Classification of service criticality and pattern."""

    SAAS = "saas"  # User-facing, strict SLOs
    BATCH = "batch"  # Time-insensitive processing
    CRITICAL_INFRA = "critical-infra"  # Platform dependencies
    BACKGROUND_JOBS = "background-jobs"  # Async workers
    UNKNOWN = "unknown"


@dataclass
class SLOTarget:
    """A single SLO target with recommended value and rationale."""

    metric: str  # latency, error_rate, availability
    target: str  # e.g., "99.9%", "p99 < 200ms"
    rationale: str
    range: tuple[str, str] = field(default=("", ""))  # (min, max) acceptable range

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric": self.metric,
            "target": self.target,
            "rationale": self.rationale,
            "range": self.range,
        }


@dataclass
class SLORecommendation:
    """Full SLO recommendation output."""

    service_type: ServiceType
    service_name: str | None = None
    targets: list[SLOTarget] = field(default_factory=list)
    context_signals: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5  # 0.0-1.0, how confident in the recommendation
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_type": self.service_type.value,
            "service_name": self.service_name,
            "targets": [t.to_dict() for t in self.targets],
            "context_signals": self.context_signals,
            "confidence": self.confidence,
            "notes": self.notes,
        }


class SLOAgent:
    """Analyze code and recommend SLO targets."""

    def __init__(self):
        """Initialize the SLO Agent."""
        self.patterns = self._build_patterns()

    def analyze(
        self,
        code_snippet: str = "",
        repo_path: str | None = None,
        service_type: str | None = None,
        context: dict[str, str] | None = None,
    ) -> SLORecommendation:
        """
        Analyze code and recommend SLO targets.

        Args:
            code_snippet: Code to analyze (diff, file content, etc)
            repo_path: Path to repository for deeper analysis
            service_type: Explicit service type (saas, batch, critical-infra, background-jobs)
            context: Additional context like "criticality:high", "users:1000"

        Returns:
            SLORecommendation with targets and rationale.
        """
        context = context or {}
        signals = self._collect_signals(code_snippet, repo_path, context)

        # Prefer explicit service_type parameter, then check context, then detect
        if service_type:
            try:
                detected_type = ServiceType(service_type)
            except ValueError:
                detected_type = self._detect_service_type(code_snippet, signals)
        elif "service-type" in context:
            try:
                detected_type = ServiceType(context["service-type"])
            except ValueError:
                detected_type = self._detect_service_type(code_snippet, signals)
        else:
            detected_type = self._detect_service_type(code_snippet, signals)

        recommendation = SLORecommendation(
            service_type=detected_type,
            service_name=context.get("service-name"),
            context_signals=signals,
        )

        # Generate targets based on service type
        if detected_type == ServiceType.SAAS:
            recommendation.targets = self._targets_saas(signals)
            recommendation.confidence = 0.75
        elif detected_type == ServiceType.BATCH:
            recommendation.targets = self._targets_batch(signals)
            recommendation.confidence = 0.70
        elif detected_type == ServiceType.CRITICAL_INFRA:
            recommendation.targets = self._targets_critical_infra(signals)
            recommendation.confidence = 0.80
        elif detected_type == ServiceType.BACKGROUND_JOBS:
            recommendation.targets = self._targets_background_jobs(signals)
            recommendation.confidence = 0.65
        else:
            recommendation.targets = self._targets_default(signals)
            recommendation.confidence = 0.50

        recommendation.notes = self._generate_notes(signals, detected_type)

        return recommendation

    def _collect_signals(
        self,
        code_snippet: str,
        repo_path: str | None,
        context: dict[str, str],
    ) -> dict[str, Any]:
        """Collect contextual signals from code and repository."""
        signals: dict[str, Any] = {
            "code_indicators": self._analyze_code(code_snippet),
            "user_context": context,
        }

        if repo_path and Path(repo_path).exists():
            signals["repo_signals"] = self._analyze_repo(repo_path)

        return signals

    def _analyze_code(self, code_snippet: str) -> dict[str, Any]:
        """Analyze code for SLO-relevant patterns."""
        db_pattern = r"(SELECT|INSERT|UPDATE|DELETE|query|execute)"
        http_pattern = r"(requests\.|urllib|httpx|fetch|client\.get)"
        cache_pattern = r"(cache|redis|memcached|@cache|lru_cache)"
        retry_pattern = r"(retry|backoff|exponential)"
        error_pattern = r"(except|try|error|exception|catch)"
        async_pattern = r"(async|await|asyncio|concurrent)"
        monitor_pattern = r"(logging|metric|prometheus|datadog|trace|span)"
        timeout_pattern = r"(timeout|deadline|ttl)"

        indicators = {
            "has_db_calls": bool(re.search(db_pattern, code_snippet, re.I)),
            "has_http_calls": bool(re.search(http_pattern, code_snippet, re.I)),
            "has_caching": bool(re.search(cache_pattern, code_snippet, re.I)),
            "has_retry_logic": bool(re.search(retry_pattern, code_snippet, re.I)),
            "has_error_handling": bool(re.search(error_pattern, code_snippet, re.I)),
            "has_async": bool(re.search(async_pattern, code_snippet, re.I)),
            "has_monitoring": bool(re.search(monitor_pattern, code_snippet, re.I)),
            "has_timeout": bool(re.search(timeout_pattern, code_snippet, re.I)),
        }
        return indicators

    def _analyze_repo(self, repo_path: str) -> dict[str, Any]:
        """Analyze repository structure for signals."""
        path = Path(repo_path)
        has_tests = (path / "tests").exists() or (path / "test").exists()
        has_docker = (path / "Dockerfile").exists()
        k8s_dir = path / "k8s"
        helm_dir = path / "helm"
        has_k8s = k8s_dir.exists() or helm_dir.exists()

        signals = {
            "has_tests": has_tests,
            "has_docker": has_docker,
            "has_k8s": has_k8s,
        }

        # Count files
        py_files = list(path.glob("**/*.py"))
        signals["file_count"] = len(py_files)

        # Look for monitoring/observability config
        for f in path.glob("**/*"):
            if f.is_file():
                name = f.name.lower()
                if any(x in name for x in ["prometheus", "grafana", "datadog", "otel"]):
                    signals["has_monitoring_config"] = True
                    break

        return signals

    def _detect_service_type(self, code_snippet: str, signals: dict[str, Any]) -> ServiceType:
        """Detect service type from code patterns."""
        code = signals.get("code_indicators", {})

        # Batch: scheduler, cron, job patterns
        batch_pattern = r"(scheduler|cron|batch|job|queue|celery|airflow)"
        if re.search(batch_pattern, code_snippet, re.I):
            return ServiceType.BATCH

        # Background: async workers, queues
        bg_pattern = r"(worker|background|task|queue|publish|subscribe)"
        if re.search(bg_pattern, code_snippet, re.I):
            if code.get("has_async"):
                return ServiceType.BACKGROUND_JOBS

        # Critical infra: auth, gateway, core service patterns
        infra_pattern = r"(auth|gateway|router|middleware|core|platform|framework|sdk)"
        if re.search(infra_pattern, code_snippet, re.I):
            return ServiceType.CRITICAL_INFRA

        # Default: SaaS if has HTTP and user-facing indicators
        if code.get("has_http_calls"):
            saas_pattern = r"(api|endpoint|route|handler|controller)"
            if re.search(saas_pattern, code_snippet, re.I):
                return ServiceType.SAAS

        return ServiceType.UNKNOWN

    def _targets_saas(self, signals: dict[str, Any]) -> list[SLOTarget]:
        """SLO targets for user-facing SaaS services."""
        targets = [
            SLOTarget(
                metric="availability",
                target="99.9%",
                range=("99.5%", "99.95%"),
                rationale=(
                    "User-facing service; high availability expected. "
                    "99.9% = ~43 min/month downtime."
                ),
            ),
            SLOTarget(
                metric="latency (p99)",
                target="< 200ms",
                range=("< 100ms", "< 500ms"),
                rationale=(
                    "Interactive service; users expect responsive performance. "
                    "Adjust based on UX sensitivity."
                ),
            ),
            SLOTarget(
                metric="error_rate",
                target="< 0.1%",
                range=("< 0.05%", "< 0.5%"),
                rationale=(
                    "User-facing errors are visible; low error tolerance. "
                    "Monitor 5xx and client-side errors."
                ),
            ),
        ]

        code = signals.get("code_indicators", {})
        if code.get("has_db_calls") and not code.get("has_caching"):
            targets.append(
                SLOTarget(
                    metric="database_latency (p95)",
                    target="< 50ms",
                    range=("< 20ms", "< 100ms"),
                    rationale=(
                        "Unoptimized database calls can dominate latency. "
                        "Consider caching or query optimization."
                    ),
                )
            )

        return targets

    def _targets_batch(self, signals: dict[str, Any]) -> list[SLOTarget]:
        """SLO targets for batch/scheduled jobs."""
        targets = [
            SLOTarget(
                metric="availability",
                target="95%",
                range=("90%", "99%"),
                rationale=(
                    "Batch jobs tolerate higher failure rates if retryable. "
                    "95% = ~1.5 days/month downtime."
                ),
            ),
            SLOTarget(
                metric="job_duration (p95)",
                target="< 1 hour",
                range=("< 30min", "< 4 hours"),
                rationale=(
                    "Time-insensitive jobs; focus on resource efficiency over strict latency."
                ),
            ),
            SLOTarget(
                metric="error_rate",
                target="< 5%",
                range=("< 1%", "< 10%"),
                rationale=(
                    "Transient batch failures are tolerable if job is idempotent and retried."
                ),
            ),
        ]

        return targets

    def _targets_critical_infra(self, signals: dict[str, Any]) -> list[SLOTarget]:
        """SLO targets for critical infrastructure (platform, auth, gateways)."""
        targets = [
            SLOTarget(
                metric="availability",
                target="99.95%",
                range=("99.9%", "99.99%"),
                rationale=(
                    "Critical infrastructure; impacts many downstream services. "
                    "99.95% = ~21 min/month downtime."
                ),
            ),
            SLOTarget(
                metric="latency (p99)",
                target="< 50ms",
                range=("< 10ms", "< 100ms"),
                rationale=(
                    "Gateway/auth latency is multiplied across all requests. Tight SLO required."
                ),
            ),
            SLOTarget(
                metric="error_rate",
                target="< 0.01%",
                range=("< 0.001%", "< 0.1%"),
                rationale=(
                    "Critical infra errors cascade; very low tolerance. Fix bugs immediately."
                ),
            ),
        ]

        return targets

    def _targets_background_jobs(self, signals: dict[str, Any]) -> list[SLOTarget]:
        """SLO targets for background jobs and async workers."""
        targets = [
            SLOTarget(
                metric="availability",
                target="98%",
                range=("95%", "99.5%"),
                rationale=(
                    "Background jobs tolerate moderate downtime if user experience "
                    "is not blocked. 98% = ~7.2 hours/month."
                ),
            ),
            SLOTarget(
                metric="task_latency (p95)",
                target="< 5 minutes",
                range=("< 1min", "< 30min"),
                rationale=(
                    "Async context; users don't wait synchronously. Focus on eventual consistency."
                ),
            ),
            SLOTarget(
                metric="error_rate",
                target="< 1%",
                range=("< 0.1%", "< 5%"),
                rationale=(
                    "Async errors may be retried; reasonable error budget for transient failures."
                ),
            ),
        ]

        code = signals.get("code_indicators", {})
        if not code.get("has_retry_logic"):
            targets.append(
                SLOTarget(
                    metric="dlq_rate",
                    target="< 0.1%",
                    range=("0%", "< 1%"),
                    rationale=(
                        "Without retry logic, failed tasks must be rare. "
                        "Add exponential backoff + DLQ."
                    ),
                )
            )

        return targets

    def _targets_default(self, signals: dict[str, Any]) -> list[SLOTarget]:
        """Default SLO targets when service type is unknown."""
        return [
            SLOTarget(
                metric="availability",
                target="99%",
                range=("95%", "99.9%"),
                rationale="Conservative default. Refine based on service type and criticality.",
            ),
            SLOTarget(
                metric="latency (p99)",
                target="< 500ms",
                range=("< 100ms", "< 5s"),
                rationale="Broad range pending service classification.",
            ),
            SLOTarget(
                metric="error_rate",
                target="< 1%",
                range=("< 0.1%", "< 5%"),
                rationale="Moderate error tolerance pending service type.",
            ),
        ]

    def _generate_notes(self, signals: dict[str, Any], service_type: ServiceType) -> str:
        """Generate contextual notes and recommendations."""
        code = signals.get("code_indicators", {})
        notes_parts = []

        if not code.get("has_error_handling"):
            notes_parts.append(
                "⚠️  No error handling detected. Add try/except and proper error propagation."
            )

        if not code.get("has_monitoring"):
            notes_parts.append(
                "📊 No monitoring/logging detected. Instrument with metrics and structured logs."
            )

        if not code.get("has_timeout") and code.get("has_http_calls"):
            notes_parts.append(
                "⏱️  No timeout detected on external calls. "
                "Add timeouts to prevent cascading failures."
            )

        if code.get("has_db_calls") and not code.get("has_caching"):
            notes_parts.append(
                "💾 Database calls without caching. "
                "Consider Redis/memcached for frequently accessed data."
            )

        if code.get("has_http_calls") and not code.get("has_retry_logic"):
            notes_parts.append(
                "🔄 External HTTP calls without retry logic. "
                "Add exponential backoff for transient failures."
            )

        if service_type == ServiceType.BACKGROUND_JOBS and not code.get("has_retry_logic"):
            notes_parts.append(
                "🔁 Background job without retry logic. "
                "Implement exponential backoff + dead letter queue."
            )

        return "\n".join(notes_parts) if notes_parts else "No immediate concerns detected."

    def _build_patterns(self) -> dict[str, Any]:
        """Build pattern library for analysis."""
        return {
            "critical_infra": [
                "auth",
                "gateway",
                "router",
                "middleware",
                "core",
                "platform",
                "framework",
            ],
            "batch": ["scheduler", "cron", "batch", "job", "queue"],
            "async": ["worker", "background", "task", "queue", "celery", "airflow"],
        }
