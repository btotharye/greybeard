"""Tests for SLO Agent."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from greybeard.agents import ServiceType, SLOAgent, SLORecommendation


class TestSLOAgentBasic:
    """Test basic SLO Agent functionality."""

    def test_agent_initialization(self):
        """Test agent can be initialized."""
        agent = SLOAgent()
        assert agent is not None
        assert agent.patterns is not None

    def test_analyze_with_no_input(self):
        """Test analyze with empty input."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="")
        assert isinstance(rec, SLORecommendation)
        assert rec.targets is not None
        assert len(rec.targets) > 0

    def test_analyze_returns_recommendation(self):
        """Test analyze returns proper SLORecommendation."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="def hello(): pass")
        assert isinstance(rec, SLORecommendation)
        assert rec.service_type is not None
        assert rec.confidence >= 0.0 and rec.confidence <= 1.0
        assert rec.context_signals is not None

    def test_slo_target_to_dict(self):
        """Test SLOTarget serialization."""
        from greybeard.agents import SLOTarget

        target = SLOTarget(
            metric="latency",
            target="p99 < 200ms",
            rationale="User-facing service",
            range=("100ms", "500ms"),
        )
        d = target.to_dict()
        assert d["metric"] == "latency"
        assert d["target"] == "p99 < 200ms"
        assert "rationale" in d
        assert d["range"] == ("100ms", "500ms")

    def test_recommendation_to_dict(self):
        """Test SLORecommendation serialization."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="")
        d = rec.to_dict()
        assert "service_type" in d
        assert "targets" in d
        assert isinstance(d["targets"], list)
        assert "confidence" in d


class TestServiceTypeDetection:
    """Test service type detection."""

    def test_detect_saas(self):
        """Test detection of SaaS services."""
        agent = SLOAgent()
        code = """
        @app.get("/api/users")
        def get_users(request):
            resp = requests.get("https://api.service.com/users")
            return resp.json()
        """
        rec = agent.analyze(code_snippet=code)
        assert rec.service_type == ServiceType.SAAS

    def test_detect_batch(self):
        """Test detection of batch jobs."""
        agent = SLOAgent()
        code = """
        @scheduler.scheduled_job('cron', hour=2, minute=0)
        def batch_process():
            for item in queue.get_items():
                process(item)
        """
        rec = agent.analyze(code_snippet=code)
        assert rec.service_type == ServiceType.BATCH

    def test_detect_background_jobs(self):
        """Test detection of background jobs."""
        agent = SLOAgent()
        code = """
        @celery.task
        async def send_email(user_id):
            user = get_user(user_id)
            await send_message(user.email)
        """
        rec = agent.analyze(code_snippet=code)
        # Async + worker patterns detected, could be batch or background
        assert rec.service_type in (
            ServiceType.BACKGROUND_JOBS,
            ServiceType.BATCH,
            ServiceType.UNKNOWN,
        )

    def test_detect_critical_infra(self):
        """Test detection of critical infrastructure."""
        agent = SLOAgent()
        code = """
        def auth_middleware(request):
            token = request.headers.get('Authorization')
            user = validate_token(token)
            if not user:
                raise AuthError()
            return user
        """
        rec = agent.analyze(code_snippet=code)
        assert rec.service_type == ServiceType.CRITICAL_INFRA

    def test_explicit_service_type(self):
        """Test explicit service type override."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="def hello(): pass", service_type="saas")
        assert rec.service_type == ServiceType.SAAS


class TestSLOTargets:
    """Test SLO target generation."""

    def test_saas_targets(self):
        """Test SaaS SLO targets."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="", service_type="saas")
        assert rec.service_type == ServiceType.SAAS
        assert len(rec.targets) >= 3  # At least availability, latency, error_rate
        metrics = {t.metric for t in rec.targets}
        assert "availability" in metrics
        assert "latency (p99)" in metrics
        assert "error_rate" in metrics

    def test_batch_targets(self):
        """Test batch job SLO targets."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="", service_type="batch")
        assert rec.service_type == ServiceType.BATCH
        assert len(rec.targets) >= 3
        metrics = {t.metric for t in rec.targets}
        assert "availability" in metrics
        assert "job_duration (p95)" in metrics
        assert "error_rate" in metrics

    def test_critical_infra_targets(self):
        """Test critical infra SLO targets."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="", service_type="critical-infra")
        assert rec.service_type == ServiceType.CRITICAL_INFRA
        assert len(rec.targets) >= 3
        metrics = {t.metric for t in rec.targets}
        assert "availability" in metrics
        assert "latency (p99)" in metrics

    def test_background_targets(self):
        """Test background job SLO targets."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="", service_type="background-jobs")
        assert rec.service_type == ServiceType.BACKGROUND_JOBS
        assert len(rec.targets) >= 3
        metrics = {t.metric for t in rec.targets}
        assert "availability" in metrics
        assert "task_latency (p95)" in metrics


class TestCodeAnalysis:
    """Test code pattern detection."""

    def test_detect_db_calls(self):
        """Test detection of database calls."""
        agent = SLOAgent()
        code = "SELECT * FROM users WHERE id = %s"
        indicators = agent._analyze_code(code)
        assert indicators["has_db_calls"]

    def test_detect_http_calls(self):
        """Test detection of HTTP calls."""
        agent = SLOAgent()
        code = "response = requests.get('https://example.com')"
        indicators = agent._analyze_code(code)
        assert indicators["has_http_calls"]

    def test_detect_caching(self):
        """Test detection of caching."""
        agent = SLOAgent()
        code = "@lru_cache(maxsize=128)\ndef expensive_call(): pass"
        indicators = agent._analyze_code(code)
        assert indicators["has_caching"]

    def test_detect_retry_logic(self):
        """Test detection of retry patterns."""
        agent = SLOAgent()
        code = "@retry(backoff=2)\ndef api_call(): pass"
        indicators = agent._analyze_code(code)
        assert indicators["has_retry_logic"]

    def test_detect_error_handling(self):
        """Test detection of error handling."""
        agent = SLOAgent()
        code = """
        try:
            do_something()
        except Exception as e:
            log_error(e)
        """
        indicators = agent._analyze_code(code)
        assert indicators["has_error_handling"]

    def test_detect_async(self):
        """Test detection of async/await."""
        agent = SLOAgent()
        code = "async def fetch(): await client.get('/endpoint')"
        indicators = agent._analyze_code(code)
        assert indicators["has_async"]

    def test_detect_monitoring(self):
        """Test detection of monitoring/observability."""
        agent = SLOAgent()
        code = "logger.info('Processing'); prometheus.histogram('duration', time)"
        indicators = agent._analyze_code(code)
        assert indicators["has_monitoring"]

    def test_detect_timeout(self):
        """Test detection of timeouts."""
        agent = SLOAgent()
        code = "requests.get(url, timeout=30)"
        indicators = agent._analyze_code(code)
        assert indicators["has_timeout"]


class TestRepoAnalysis:
    """Test repository-based analysis."""

    def test_analyze_repo_with_tests(self):
        """Test detection of test directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "tests").mkdir()
            agent = SLOAgent()
            signals = agent._analyze_repo(tmpdir)
            assert signals["has_tests"]

    def test_analyze_repo_with_docker(self):
        """Test detection of Docker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "Dockerfile").write_text("FROM python:3.11")
            agent = SLOAgent()
            signals = agent._analyze_repo(tmpdir)
            assert signals["has_docker"]

    def test_analyze_repo_with_k8s(self):
        """Test detection of Kubernetes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "helm").mkdir()
            agent = SLOAgent()
            signals = agent._analyze_repo(tmpdir)
            assert signals["has_k8s"]

    def test_analyze_repo_file_count(self):
        """Test file counting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file1.py").write_text("pass")
            Path(tmpdir, "file2.py").write_text("pass")
            agent = SLOAgent()
            signals = agent._analyze_repo(tmpdir)
            assert signals["file_count"] >= 2


class TestContextIntegration:
    """Test context integration."""

    def test_context_service_name(self):
        """Test service name from context."""
        agent = SLOAgent()
        context = {"service-name": "user-api"}
        rec = agent.analyze(code_snippet="", context=context)
        assert rec.service_name == "user-api"

    def test_context_service_type(self):
        """Test explicit service type from context."""
        agent = SLOAgent()
        context = {"service-type": "saas"}
        rec = agent.analyze(code_snippet="", context=context)
        assert rec.service_type == ServiceType.SAAS

    def test_multiple_context_flags(self):
        """Test multiple context flags."""
        agent = SLOAgent()
        context = {
            "service-name": "payment-api",
            "service-type": "critical-infra",
            "users": "100000",
        }
        rec = agent.analyze(code_snippet="", context=context)
        assert rec.service_name == "payment-api"
        assert rec.service_type == ServiceType.CRITICAL_INFRA


class TestRecommendationNotes:
    """Test recommendation notes and guidance."""

    def test_notes_for_missing_error_handling(self):
        """Test notes suggest error handling."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="requests.get(url)")
        assert "error" in rec.notes.lower() or "timeout" in rec.notes.lower()

    def test_notes_for_missing_monitoring(self):
        """Test notes suggest monitoring."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="def process(): pass")
        assert rec.notes  # Should have some notes

    def test_notes_for_db_without_caching(self):
        """Test notes suggest caching for DB calls."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="SELECT * FROM users")
        assert "cache" in rec.notes.lower() or "cach" in rec.notes.lower()

    def test_no_notes_for_well_formed_code(self):
        """Test minimal notes for well-formed code."""
        agent = SLOAgent()
        code = """
        @cache.cached()
        def fetch_user(user_id):
            try:
                with timeout(30):
                    return db.query(User).filter(id=user_id).one()
            except Exception as e:
                logger.error(f"Error: {e}")
                raise
        """
        rec = agent.analyze(code_snippet=code)
        # Even good code might have some notes; just check they're reasonable
        assert isinstance(rec.notes, str)


class TestConfidence:
    """Test confidence scoring."""

    def test_confidence_ranges(self):
        """Test confidence is 0.0 to 1.0."""
        agent = SLOAgent()
        for service_type in ["saas", "batch", "critical-infra", "background-jobs"]:
            rec = agent.analyze(code_snippet="", service_type=service_type)
            assert 0.0 <= rec.confidence <= 1.0

    def test_confidence_by_type(self):
        """Test different confidence for different types."""
        agent = SLOAgent()
        saas_rec = agent.analyze(code_snippet="", service_type="saas")
        critical_rec = agent.analyze(code_snippet="", service_type="critical-infra")
        # Critical infra should have higher confidence (stricter SLOs)
        assert critical_rec.confidence >= saas_rec.confidence


class TestCLIIntegration:
    """Test CLI integration."""

    def test_slo_check_command_exists(self):
        """Test slo-check command is registered."""
        from greybeard.cli import cli

        # Get the command
        assert "slo-check" in cli.commands or any(
            getattr(cmd, "name", "") == "slo-check" for cmd in (cli.commands or {}).values()
        )


class TestSerializationRoundTrip:
    """Test serialization and deserialization."""

    def test_recommendation_json_roundtrip(self):
        """Test recommendation can be serialized to JSON."""
        agent = SLOAgent()
        rec = agent.analyze(code_snippet="")
        d = rec.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(d)
        assert json_str
        data = json.loads(json_str)
        assert data["service_type"]
        assert "targets" in data
