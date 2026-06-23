"""Tests for C26C — Projection Certification Framework."""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.projection_certification import (
    CertificationLevel,
    LevelCheckResult,
    ProjectionCertification,
    ProjectionCertificationEngine,
    ProjectionConfig,
    ProjectionRegistry,
)


# ── Mock HTTP ────────────────────────────────────────────────────────────

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

BROKEN_HTML = """<!DOCTYPE html><html><body><p>Error</p></body></html>"""

MISSING_KEY_BUNDLE = """
var config = {clerkKey: undefined};
console.log("app loaded");
"""


def make_mock_http(responses: dict[str, tuple[int, str]]):
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


class TestCertificationTypes:
    def test_certification_level_ordering(self):
        assert CertificationLevel.L0_ARTIFACT < CertificationLevel.L5_OUTCOME
        assert CertificationLevel.L3_UI > CertificationLevel.L2_DEPLOY

    def test_level_check_result_to_dict(self):
        result = LevelCheckResult(
            level=CertificationLevel.L2_DEPLOY,
            passed=True,
            detail="Health OK",
        )
        d = result.to_dict()
        assert d["level"] == "L2_DEPLOY"
        assert d["level_value"] == 2
        assert d["passed"] is True

    def test_projection_certification_to_dict(self):
        cert = ProjectionCertification(
            projection_name="eos",
            current_level=CertificationLevel.L3_UI,
        )
        d = cert.to_dict()
        assert d["projection_name"] == "eos"
        assert d["current_level"] == "L3_UI"
        assert d["is_fully_certified"] is False

    def test_fully_certified_property(self):
        cert = ProjectionCertification(
            current_level=CertificationLevel.L5_OUTCOME,
        )
        assert cert.is_fully_certified is True

    def test_not_fully_certified(self):
        cert = ProjectionCertification(
            current_level=CertificationLevel.L4_WORKFLOW,
        )
        assert cert.is_fully_certified is False


class TestProjectionConfig:
    def test_from_dict(self):
        config = ProjectionConfig.from_dict(
            "eos",
            {
                "app_name": "eos-app",
                "health_url": "/api/health",
                "public_url": "https://entrepreneuros.net",
                "critical_bundle_values": ["pk_test_"],
                "l4_workflow": "clerk_login_renders",
            },
        )
        assert config.name == "eos"
        assert config.app_name == "eos-app"
        assert config.critical_bundle_values == ["pk_test_"]

    def test_from_dict_defaults(self):
        config = ProjectionConfig.from_dict("minimal", {})
        assert config.health_url == "/api/health"
        assert config.critical_bundle_values == []
        assert config.l4_workflow == ""


# ── Registry tests ───────────────────────────────────────────────────────


class TestProjectionRegistry:
    def test_load_from_file(self):
        data = {
            "eos": {
                "app_name": "eos-app",
                "public_url": "https://entrepreneuros.net",
            },
            "cos": {
                "app_name": "cos-app",
                "public_url": "https://creatoros.net",
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name

        try:
            registry = ProjectionRegistry(config_path=path)
            assert "eos" in registry.names
            assert "cos" in registry.names
            assert len(registry.all()) == 2
            eos = registry.get("eos")
            assert eos is not None
            assert eos.app_name == "eos-app"
        finally:
            os.unlink(path)

    def test_missing_file(self):
        registry = ProjectionRegistry(config_path="/nonexistent/path.json")
        assert registry.names == []
        assert registry.get("anything") is None

    def test_get_nonexistent(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({}, f)
            path = f.name
        try:
            registry = ProjectionRegistry(config_path=path)
            assert registry.get("nonexistent") is None
        finally:
            os.unlink(path)

    def test_loads_real_registry(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            "umh",
            "projection_registry.json",
        )
        if os.path.exists(path):
            registry = ProjectionRegistry(config_path=path)
            assert len(registry.names) >= 3
            for name in ["lyfeos", "eos", "cos"]:
                config = registry.get(name)
                assert config is not None, f"{name} missing from registry"
                assert config.public_url, f"{name} has no public_url"


# ── Engine tests ─────────────────────────────────────────────────────────


class TestProjectionCertificationEngine:
    def _make_engine(self, http_responses):
        data = {
            "test-app": {
                "app_name": "test-app",
                "public_url": "https://app.example.com",
                "critical_bundle_values": ["pk_test_"],
                "l4_workflow": "",
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            f.flush()
            registry = ProjectionRegistry(config_path=f.name)

        mock = make_mock_http(http_responses)
        engine = ProjectionCertificationEngine(
            registry=registry, http_client=mock
        )
        engine._tmp_path = f.name
        return engine

    def test_full_certification_passes(self):
        engine = self._make_engine(
            {
                "https://app.example.com/api/health": (200, '{"status":"ok"}'),
                "https://app.example.com": (200, HEALTHY_HTML),
                "https://app.example.com/assets/index-abc123.js": (
                    200,
                    HEALTHY_BUNDLE,
                ),
            }
        )
        try:
            cert = engine.certify("test-app")
            assert cert.current_level == CertificationLevel.L5_OUTCOME
            assert cert.is_fully_certified
            assert len(cert.level_results) == 6
            assert all(r.passed for r in cert.level_results)
        finally:
            os.unlink(engine._tmp_path)

    def test_health_failure_stops_at_l2(self):
        engine = self._make_engine(
            {
                "https://app.example.com/api/health": (500, "error"),
            }
        )
        try:
            cert = engine.certify("test-app")
            assert cert.current_level == CertificationLevel.L1_BUILD
            assert cert.failure_level == CertificationLevel.L2_DEPLOY
            assert not cert.is_fully_certified
            assert len(cert.level_results) == 3
        finally:
            os.unlink(engine._tmp_path)

    def test_bundle_missing_stops_at_l3(self):
        """Simulates the C25 white screen — health passes but Clerk key missing."""
        engine = self._make_engine(
            {
                "https://app.example.com/api/health": (200, '{"status":"ok"}'),
                "https://app.example.com": (200, HEALTHY_HTML),
                "https://app.example.com/assets/index-abc123.js": (
                    200,
                    MISSING_KEY_BUNDLE,
                ),
            }
        )
        try:
            cert = engine.certify("test-app")
            assert cert.current_level == CertificationLevel.L2_DEPLOY
            assert cert.failure_level == CertificationLevel.L3_UI
            assert "missing" in cert.failure_detail.lower()
        finally:
            os.unlink(engine._tmp_path)

    def test_unknown_projection(self):
        engine = self._make_engine({})
        try:
            cert = engine.certify("nonexistent")
            assert cert.current_level == CertificationLevel.L0_ARTIFACT
            assert "not found" in cert.failure_detail.lower()
        finally:
            os.unlink(engine._tmp_path)

    def test_certify_all(self):
        data = {
            "app1": {
                "app_name": "app1",
                "public_url": "https://app1.example.com",
            },
            "app2": {
                "app_name": "app2",
                "public_url": "https://app2.example.com",
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            f.flush()
            registry = ProjectionRegistry(config_path=f.name)

        mock = make_mock_http(
            {
                "https://app1.example.com/api/health": (200, '{"status":"ok"}'),
                "https://app1.example.com": (200, HEALTHY_HTML),
                "https://app2.example.com/api/health": (500, "down"),
            }
        )
        engine = ProjectionCertificationEngine(
            registry=registry, http_client=mock
        )
        try:
            results = engine.certify_all()
            assert len(results) == 2
            assert "app1" in results
            assert "app2" in results
            assert results["app2"].failure_level == CertificationLevel.L2_DEPLOY
        finally:
            os.unlink(f.name)

    def test_summary(self):
        engine = self._make_engine(
            {
                "https://app.example.com/api/health": (200, '{"status":"ok"}'),
                "https://app.example.com": (200, HEALTHY_HTML),
                "https://app.example.com/assets/index-abc123.js": (
                    200,
                    HEALTHY_BUNDLE,
                ),
            }
        )
        try:
            engine.certify("test-app")
            summary = engine.summary()
            assert "test-app" in summary
            assert summary["test-app"]["level"] == "L5_OUTCOME"
            assert summary["test-app"]["fully_certified"] is True
        finally:
            os.unlink(engine._tmp_path)

    def test_no_bundle_values_skips_l3(self):
        """When no critical_bundle_values configured, L3 check passes (skipped)."""
        data = {
            "simple": {
                "app_name": "simple",
                "public_url": "https://simple.example.com",
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            f.flush()
            registry = ProjectionRegistry(config_path=f.name)

        mock = make_mock_http(
            {
                "https://simple.example.com/api/health": (
                    200,
                    '{"status":"ok"}',
                ),
                "https://simple.example.com": (200, HEALTHY_HTML),
            }
        )
        engine = ProjectionCertificationEngine(
            registry=registry, http_client=mock
        )
        try:
            cert = engine.certify("simple")
            assert cert.current_level == CertificationLevel.L5_OUTCOME
        finally:
            os.unlink(f.name)

    def test_no_js_bundles_in_html(self):
        """HTML with no JS scripts fails L3."""
        engine = self._make_engine(
            {
                "https://app.example.com/api/health": (200, '{"status":"ok"}'),
                "https://app.example.com": (200, BROKEN_HTML),
            }
        )
        try:
            cert = engine.certify("test-app")
            assert cert.current_level == CertificationLevel.L2_DEPLOY
            assert cert.failure_level == CertificationLevel.L3_UI
        finally:
            os.unlink(engine._tmp_path)


# ── Core invariant ───────────────────────────────────────────────────────


class TestCertificationInvariants:
    def test_failed_level_cannot_reach_higher(self):
        """If L2 fails, the engine must NOT reach L3+."""
        engine = TestProjectionCertificationEngine()._make_engine(
            {"https://app.example.com/api/health": (500, "error")}
        )
        try:
            cert = engine.certify("test-app")
            for result in cert.level_results:
                if result.level > CertificationLevel.L2_DEPLOY:
                    pytest.fail(
                        f"Reached {result.level.name} despite L2 failure"
                    )
        finally:
            os.unlink(engine._tmp_path)

    def test_levels_are_sequential(self):
        """Level results must be in ascending order."""
        engine = TestProjectionCertificationEngine()._make_engine(
            {
                "https://app.example.com/api/health": (200, '{"status":"ok"}'),
                "https://app.example.com": (200, HEALTHY_HTML),
                "https://app.example.com/assets/index-abc123.js": (
                    200,
                    HEALTHY_BUNDLE,
                ),
            }
        )
        try:
            cert = engine.certify("test-app")
            levels = [r.level for r in cert.level_results]
            assert levels == sorted(levels)
        finally:
            os.unlink(engine._tmp_path)


# ── Canonical type registration ──────────────────────────────────────────


class TestCertificationCanonicalTypes:
    def test_types_registered(self):
        from substrate.canonical_types import lookup

        for name in [
            "CertificationLevel",
            "LevelCheckResult",
            "ProjectionCertification",
            "ProjectionConfig",
        ]:
            result = lookup(name)
            assert result is not None, f"{name} not registered"
            assert "substrate.organism.projection_certification" in result[0]
