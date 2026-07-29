"""Tests for cockpit work intelligence routes — Campaign 11.3."""

import sys
import os

# Repo root is DERIVED from the active checkout, never hardcoded. The previous
# module-scope `sys.path.insert(...)` + `os.environ.setdefault("UMH_ROOT", ...)`
# pinned a foreign campaign worktree at IMPORT time and never restored it, so it
# leaked into every module collected afterwards and hard-aborted whole shards.
from tests.repo_root import ensure_repo_on_path

ensure_repo_on_path()

import pytest
from dataclasses import dataclass, field
from typing import Any

try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from transports.api.cockpit_work_intelligence_routes import (
    configure,
    get_router,
)


# ── Mock runtimes ─────────────────────────────────────────────────────────


@dataclass
class _MockReadinessAssessment:
    work_id: str = "wp-1"
    title: str = "test"
    status: str = "ready"
    blocking_reasons: list = field(default_factory=list)
    missing_capabilities: list = field(default_factory=list)
    pending_approvals: list = field(default_factory=list)
    unresolved_dependencies: list = field(default_factory=list)
    goal_ids: list = field(default_factory=list)
    readiness_score: float = 1.0
    recommended_action: str = "execute"

    def to_dict(self):
        return {
            "work_id": self.work_id,
            "title": self.title,
            "status": self.status,
            "blocking_reasons": self.blocking_reasons,
            "readiness_score": self.readiness_score,
            "recommended_action": self.recommended_action,
        }


@dataclass
class _MockReadinessSnapshot:
    total: int = 3
    by_status: dict = field(default_factory=lambda: {"ready": 2, "blocked": 1})
    ready_work: list = field(default_factory=list)
    blocked_work: list = field(default_factory=list)
    health: str = "mostly_ready"

    def to_dict(self):
        return {
            "total": self.total,
            "by_status": self.by_status,
            "ready_count": len(self.ready_work),
            "blocked_count": len(self.blocked_work),
            "health": self.health,
        }


class _MockReadinessRuntime:
    def ready_work(self):
        return [
            _MockReadinessAssessment("wp-1"),
            _MockReadinessAssessment("wp-2"),
        ]

    def blocked_work(self):
        return [
            _MockReadinessAssessment("wp-3", status="blocked", readiness_score=0.0,
                                      blocking_reasons=["hard block"]),
        ]

    def assess(self, work_id):
        return _MockReadinessAssessment(work_id=work_id)

    def assess_all(self):
        return self.ready_work() + self.blocked_work()

    def snapshot(self):
        return _MockReadinessSnapshot()


@dataclass
class _MockDelegationReadiness:
    work_id: str = "wp-1"
    delegatable: bool = True
    recommended_executor: str = "agent-A"
    confidence: float = 0.8
    success_probability: float = 0.7

    def to_dict(self):
        return {
            "work_id": self.work_id,
            "delegatable": self.delegatable,
            "recommended_executor": self.recommended_executor,
            "confidence": self.confidence,
            "success_probability": self.success_probability,
        }


@dataclass
class _MockDelegationSnapshot:
    total_assessed: int = 3
    delegatable: int = 2
    not_delegatable: int = 1
    avg_confidence: float = 0.75
    avg_success_probability: float = 0.65
    top_missing_capabilities: list = field(default_factory=list)
    top_risk_factors: list = field(default_factory=list)

    def to_dict(self):
        return {
            "total_assessed": self.total_assessed,
            "delegatable": self.delegatable,
            "not_delegatable": self.not_delegatable,
            "avg_confidence": self.avg_confidence,
            "avg_success_probability": self.avg_success_probability,
            "top_missing_capabilities": self.top_missing_capabilities,
            "top_risk_factors": self.top_risk_factors,
        }


class _MockDelegationRuntime:
    def snapshot(self):
        return _MockDelegationSnapshot()

    def assess(self, work_id=""):
        return _MockDelegationReadiness(work_id=work_id)


@dataclass
class _MockDriftWarning:
    drift_type: str = "readiness_drift"
    severity: float = 0.7
    description: str = "block rate increasing"

    def to_dict(self):
        return {
            "drift_type": self.drift_type,
            "severity": self.severity,
            "description": self.description,
        }


class _MockPortfolioHealth:
    def __init__(self, value="healthy"):
        self.value = value


@dataclass
class _MockPortfolioSnapshot:
    total_work: int = 10
    ready: int = 6
    blocked: int = 2
    health: Any = field(default_factory=lambda: _MockPortfolioHealth("healthy"))
    capability_health: str = "healthy"
    goals_at_risk: list = field(default_factory=list)
    drift_warnings: list = field(default_factory=list)

    def to_dict(self):
        return {
            "total_work": self.total_work,
            "ready": self.ready,
            "blocked": self.blocked,
            "health": self.health.value if hasattr(self.health, "value") else str(self.health),
            "capability_health": self.capability_health,
            "goals_at_risk": self.goals_at_risk,
        }


class _MockPortfolioRuntime:
    def snapshot(self):
        return _MockPortfolioSnapshot()

    def detect_drift(self):
        return [_MockDriftWarning()]

    def velocity(self):
        return {"completions_per_day": 2.5, "block_rate_change_7d": -0.05}

    def health(self):
        return _MockPortfolioHealth("healthy")


# ── Test setup ────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset module-level singletons before each test."""
    configure(readiness=None, delegation=None, portfolio=None)
    yield
    configure(readiness=None, delegation=None, portfolio=None)


@pytest.fixture
def client():
    if not HAS_FASTAPI:
        pytest.skip("fastapi not installed")
    configure(
        readiness=_MockReadinessRuntime(),
        delegation=_MockDelegationRuntime(),
        portfolio=_MockPortfolioRuntime(),
    )
    app = FastAPI()
    app.include_router(get_router())
    return TestClient(app)


# ── Route Tests ───────────────────────────────────────────────────────────


class TestOverviewRoute:
    def test_returns_portfolio(self, client):
        resp = client.get("/work-intelligence/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "portfolio" in data
        assert data["portfolio"]["total_work"] == 10

    def test_missing_runtime(self, client):
        configure(portfolio=None)
        import transports.api.cockpit_work_intelligence_routes as mod
        mod._portfolio_runtime = None
        resp = client.get("/work-intelligence/overview")
        assert resp.status_code == 200


class TestReadyRoute:
    def test_returns_ready_work(self, client):
        resp = client.get("/work-intelligence/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "ready" in data
        assert data["count"] == 2
        assert data["ready"][0]["work_id"] == "wp-1"


class TestBlockedRoute:
    def test_returns_blocked_work(self, client):
        resp = client.get("/work-intelligence/blocked")
        assert resp.status_code == 200
        data = resp.json()
        assert "blocked" in data
        assert data["count"] == 1
        assert data["blocked"][0]["status"] == "blocked"

    def test_blocked_detail(self, client):
        resp = client.get("/work-intelligence/blocked/wp-1")
        assert resp.status_code == 200
        data = resp.json()
        assert "assessment" in data
        assert data["assessment"]["work_id"] == "wp-1"


class TestDelegationRoute:
    def test_delegation_overview(self, client):
        resp = client.get("/work-intelligence/delegation")
        assert resp.status_code == 200
        data = resp.json()
        assert "delegation" in data
        assert data["delegation"]["delegatable"] == 2

    def test_delegation_detail(self, client):
        resp = client.get("/work-intelligence/delegation/wp-1")
        assert resp.status_code == 200
        data = resp.json()
        assert "delegation" in data
        assert data["delegation"]["work_id"] == "wp-1"


class TestDriftRoute:
    def test_returns_drift(self, client):
        resp = client.get("/work-intelligence/drift")
        assert resp.status_code == 200
        data = resp.json()
        assert "drift" in data
        assert data["count"] == 1
        assert data["drift"][0]["drift_type"] == "readiness_drift"


class TestVelocityRoute:
    def test_returns_velocity(self, client):
        resp = client.get("/work-intelligence/velocity")
        assert resp.status_code == 200
        data = resp.json()
        assert "velocity" in data
        assert data["velocity"]["completions_per_day"] == 2.5


class TestHealthRoute:
    def test_returns_health(self, client):
        resp = client.get("/work-intelligence/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["health"] == "healthy"
        assert data["capability_health"] == "healthy"
        assert "goals_at_risk" in data
        assert "goals_at_risk_count" in data
