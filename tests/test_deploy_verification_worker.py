"""Tests for C26B — Deploy Verification Worker."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.deploy_verification_worker import (
    DeployCheckResult,
    DeployCheckStatus,
    DeployVerificationResult,
    DeployVerificationWorker,
)


# ── Mock HTTP responses ──────────────────────────────────────────────────


HEALTHY_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>App</title></head>
<body>
<div id="root"></div>
<script type="module" src="/assets/index-abc123.js"></script>
</body>
</html>"""

HEALTHY_BUNDLE = """
var config = {clerkKey: "pk_test_abc123xyz"};
console.log("app loaded");
"""

BLANK_HTML = ""

NO_ROOT_HTML = """<!DOCTYPE html>
<html><body><p>Server error</p></body></html>"""

MISSING_KEY_BUNDLE = """
var config = {clerkKey: undefined};
console.log("app loaded");
"""


def make_mock_http(responses: dict[str, tuple[int, str]]):
    """Create a mock HTTP client that returns predefined responses.

    Tries exact match first, then substring match (longest pattern wins).
    """

    def mock_get(url: str) -> tuple[int, str]:
        if url in responses:
            return responses[url]
        matches = [
            (pattern, status, body)
            for pattern, (status, body) in responses.items()
            if pattern in url
        ]
        if not matches:
            return 404, "Not Found"
        matches.sort(key=lambda m: len(m[0]), reverse=True)
        return matches[0][1], matches[0][2]

    return mock_get


# ── Type tests ───────────────────────────────────────────────────────────


class TestDeployVerificationTypes:
    def test_check_result_to_dict(self):
        result = DeployCheckResult(
            check_name="health_probe",
            status=DeployCheckStatus.PASSED,
            detail="Health OK",
        )
        d = result.to_dict()
        assert d["check_name"] == "health_probe"
        assert d["status"] == "passed"

    def test_verification_result_to_dict(self):
        result = DeployVerificationResult(
            app_name="test-app",
            public_url="https://test.example.com",
            overall_passed=True,
        )
        d = result.to_dict()
        assert d["app_name"] == "test-app"
        assert d["overall_passed"] is True


# ── Worker tests ─────────────────────────────────────────────────────────


class TestDeployVerificationWorker:
    def test_all_checks_pass(self):
        """Happy path — health, HTML, and bundle all pass."""
        mock = make_mock_http(
            {
                "https://app.example.com/api/health": (200, '{"status": "ok"}'),
                "https://app.example.com": (200, HEALTHY_HTML),
                "https://app.example.com/assets/index-abc123.js": (200, HEALTHY_BUNDLE),
            }
        )
        worker = DeployVerificationWorker(http_client=mock)
        result = worker.verify_deployment(
            app_name="test-app",
            public_url="https://app.example.com",
            expected_bundle_values=["pk_test_"],
            health_timeout_seconds=1.0,
            health_poll_interval=0.1,
        )
        assert result.overall_passed is True
        assert len(result.critical_failures) == 0
        assert len(result.checks) == 3
        assert all(
            c.status == DeployCheckStatus.PASSED for c in result.checks
        )

    def test_health_failure_stops_pipeline(self):
        """If health fails, no further checks run."""
        mock = make_mock_http(
            {"https://broken.example.com/api/health": (500, "Internal Server Error")}
        )
        worker = DeployVerificationWorker(http_client=mock)
        result = worker.verify_deployment(
            app_name="broken-app",
            public_url="https://broken.example.com",
            health_timeout_seconds=0.3,
            health_poll_interval=0.1,
        )
        assert result.overall_passed is False
        assert len(result.checks) == 1
        assert result.checks[0].check_name == "health_probe"
        assert result.checks[0].status == DeployCheckStatus.FAILED
        assert len(result.critical_failures) == 1

    def test_missing_root_div(self):
        """Health passes but HTML has no root div."""
        mock = make_mock_http(
            {
                "https://app.example.com/api/health": (200, '{"status": "ok"}'),
                "https://app.example.com": (200, NO_ROOT_HTML),
            }
        )
        worker = DeployVerificationWorker(http_client=mock)
        result = worker.verify_deployment(
            app_name="no-root-app",
            public_url="https://app.example.com",
            health_timeout_seconds=0.5,
            health_poll_interval=0.1,
        )
        assert result.overall_passed is False
        html_check = next(
            c for c in result.checks if c.check_name == "html_root"
        )
        assert html_check.status == DeployCheckStatus.FAILED

    def test_c25_white_screen_bug_detected(self):
        """Simulates the C25 bug — health 200, HTML OK, but Clerk key missing from bundle."""
        mock = make_mock_http(
            {
                "https://app.example.com/api/health": (200, '{"status": "ok"}'),
                "https://app.example.com": (200, HEALTHY_HTML),
                "https://app.example.com/assets/index-abc123.js": (200, MISSING_KEY_BUNDLE),
            }
        )
        worker = DeployVerificationWorker(http_client=mock)
        result = worker.verify_deployment(
            app_name="eos-app",
            public_url="https://app.example.com",
            expected_bundle_values=["pk_test_aGlwLX"],
            health_timeout_seconds=0.5,
            health_poll_interval=0.1,
        )
        assert result.overall_passed is False
        bundle_check = next(
            c for c in result.checks if c.check_name == "bundle_values"
        )
        assert bundle_check.status == DeployCheckStatus.FAILED
        assert "pk_test_aGlwLX" in bundle_check.detail
        assert len(result.critical_failures) >= 1

    def test_no_bundle_values_skips_check(self):
        """When no expected_bundle_values, only health + HTML are checked."""
        mock = make_mock_http(
            {
                "https://app.example.com/api/health": (200, '{"status": "ok"}'),
                "https://app.example.com": (200, HEALTHY_HTML),
            }
        )
        worker = DeployVerificationWorker(http_client=mock)
        result = worker.verify_deployment(
            app_name="simple-app",
            public_url="https://app.example.com",
            health_timeout_seconds=0.5,
            health_poll_interval=0.1,
        )
        assert result.overall_passed is True
        assert len(result.checks) == 2

    def test_blank_page_detected(self):
        """Blank HTML response detected as failure."""
        mock = make_mock_http(
            {
                "https://app.example.com/api/health": (200, '{"status": "ok"}'),
                "https://app.example.com": (200, BLANK_HTML),
            }
        )
        worker = DeployVerificationWorker(http_client=mock)
        result = worker.verify_deployment(
            app_name="blank-app",
            public_url="https://app.example.com",
            health_timeout_seconds=0.5,
            health_poll_interval=0.1,
        )
        assert result.overall_passed is False
        html_check = next(
            c for c in result.checks if c.check_name == "html_root"
        )
        assert html_check.status == DeployCheckStatus.FAILED

    def test_telemetry_emission(self):
        """Verify telemetry events are emitted."""
        events: list[dict] = []

        class MockEmitter:
            def emit(self, event_type, **kwargs):
                events.append({"type": event_type, **kwargs})

        mock = make_mock_http(
            {
                "https://app.example.com/api/health": (200, '{"status": "ok"}'),
                "https://app.example.com": (200, HEALTHY_HTML),
            }
        )
        worker = DeployVerificationWorker(
            http_client=mock, telemetry_emitter=MockEmitter()
        )
        worker.verify_deployment(
            app_name="telem-app",
            public_url="https://app.example.com",
            health_timeout_seconds=0.5,
            health_poll_interval=0.1,
        )
        assert len(events) == 2
        assert events[0]["type"] == "deploy_verification_started"
        assert events[1]["type"] == "deploy_verification_passed"

    def test_critical_attention_on_failure(self):
        """Verify CRITICAL attention item emitted on failure."""
        attention_items: list = []

        mock = make_mock_http(
            {"https://fail.example.com/api/health": (500, "error")}
        )
        worker = DeployVerificationWorker(
            http_client=mock,
            attention_emitter=lambda item: attention_items.append(item),
        )
        worker.verify_deployment(
            app_name="fail-app",
            public_url="https://fail.example.com",
            health_timeout_seconds=0.3,
            health_poll_interval=0.1,
        )
        assert len(attention_items) == 1
        item = attention_items[0]
        assert item.severity.value == "critical"
        assert "fail-app" in item.title

    def test_reality_observation_written(self):
        """Verify reality model observation written."""
        observations: list = []

        class MockReality:
            def record(self, obs):
                observations.append(obs)

        mock = make_mock_http(
            {
                "https://app.example.com/api/health": (200, '{"status": "ok"}'),
                "https://app.example.com": (200, HEALTHY_HTML),
            }
        )
        worker = DeployVerificationWorker(
            http_client=mock, reality_model=MockReality()
        )
        worker.verify_deployment(
            app_name="obs-app",
            public_url="https://app.example.com",
            health_timeout_seconds=0.5,
            health_poll_interval=0.1,
        )
        assert len(observations) == 1
        assert "PASSED" in observations[0].content
        assert "deployment" == observations[0].domain


# ── Canonical type registration ──────────────────────────────────────────


class TestDeployCanonicalTypes:
    def test_types_registered(self):
        from substrate.canonical_types import lookup

        for name in [
            "DeployCheckStatus",
            "DeployCheckResult",
            "DeployVerificationResult",
        ]:
            result = lookup(name)
            assert result is not None, f"{name} not registered"
            assert "substrate.organism.deploy_verification_worker" in result[0]
