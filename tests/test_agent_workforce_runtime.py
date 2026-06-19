"""Tests for AgentWorkforceRuntime — Campaign 19.1."""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.workstation.agent_workforce_runtime import (
    AgentWorkforceRuntime,
    AgentWorkforceSnapshot,
    WorkforceHealth,
)


# ── Mock helpers ──────────────────────────────────────────────────────


@dataclass
class MockAgentType:
    agent_type_id: str = "builder"
    label: str = "Builder"
    allowed_domains: list[str] = field(default_factory=lambda: ["engineering"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type_id": self.agent_type_id,
            "label": self.label,
            "allowed_domains": self.allowed_domains,
        }


@dataclass
class MockDispatch:
    agent_type: str = "builder"
    work_id: str = "wp-1"
    status: str = "executing"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "work_id": self.work_id,
            "status": self.status,
        }


@dataclass
class MockDelegationSnap:
    assessments: list[Any] = field(default_factory=list)
    avg_success_probability: float = 0.85


def _empty_registry() -> MagicMock:
    m = MagicMock()
    m.list_agents.return_value = []
    m.all_agents.return_value = []
    return m


def _empty_fleet() -> MagicMock:
    m = MagicMock()
    m.active_dispatches.return_value = []
    m.snapshot.return_value = MagicMock(active_dispatches=[])
    return m


def _empty_delegation() -> MagicMock:
    m = MagicMock()
    m.pending_delegations.return_value = []
    m.snapshot.return_value = MagicMock(assessments=[], avg_success_probability=0.0)
    return m


def _empty_coord() -> MagicMock:
    m = MagicMock()
    m.queue_depth.return_value = 0
    return m


def _make_runtime(**kwargs: Any) -> AgentWorkforceRuntime:
    return AgentWorkforceRuntime(**kwargs)


def _make_empty_runtime(**kwargs: Any) -> AgentWorkforceRuntime:
    """Runtime with all deps mocked to return empty/idle."""
    defaults: dict[str, Any] = {
        "agent_registry": _empty_registry(),
        "agent_fleet": _empty_fleet(),
        "delegation_readiness": _empty_delegation(),
        "execution_coordinator": _empty_coord(),
    }
    defaults.update(kwargs)
    return AgentWorkforceRuntime(**defaults)


# ── Health derivation ──────────────────────────────────────────────


class TestHealthDerivation:
    def test_idle_empty_deps(self) -> None:
        rt = _make_empty_runtime()
        assert rt.health() == WorkforceHealth.IDLE

    def test_idle_no_agents(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = []
        rt = _make_runtime(agent_registry=registry)
        assert rt.health() == WorkforceHealth.IDLE

    def test_active_with_dispatches(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [MockAgentType(), MockAgentType(agent_type_id="researcher", label="Researcher")]
        fleet = MagicMock()
        fleet.active_dispatches.return_value = [MockDispatch()]
        delegation = MagicMock()
        delegation.pending_delegations.return_value = []
        rt = _make_runtime(agent_registry=registry, agent_fleet=fleet, delegation_readiness=delegation)
        assert rt.health() == WorkforceHealth.ACTIVE

    def test_overloaded(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [MockAgentType()]
        fleet = MagicMock()
        fleet.active_dispatches.return_value = [
            MockDispatch(agent_type="builder", work_id="wp-1"),
            MockDispatch(agent_type="builder", work_id="wp-2"),
        ]
        delegation = MagicMock()
        delegation.pending_delegations.return_value = []
        rt = _make_runtime(agent_registry=registry, agent_fleet=fleet, delegation_readiness=delegation)
        assert rt.health() == WorkforceHealth.OVERLOADED

    def test_constrained_pending_no_active(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [MockAgentType()]
        fleet = MagicMock()
        fleet.active_dispatches.return_value = []
        delegation = MagicMock()
        delegation.pending_delegations.return_value = [{"work_id": "wp-1"}]
        rt = _make_runtime(agent_registry=registry, agent_fleet=fleet, delegation_readiness=delegation)
        assert rt.health() == WorkforceHealth.CONSTRAINED

    def test_idle_no_dispatches_no_pending(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [MockAgentType()]
        fleet = MagicMock()
        fleet.active_dispatches.return_value = []
        delegation = MagicMock()
        delegation.pending_delegations.return_value = []
        rt = _make_runtime(agent_registry=registry, agent_fleet=fleet, delegation_readiness=delegation)
        assert rt.health() == WorkforceHealth.IDLE


# ── Snapshot ──────────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_returns_all_fields(self) -> None:
        rt = _make_empty_runtime()
        snap = rt.snapshot()
        assert isinstance(snap, AgentWorkforceSnapshot)
        assert snap.health == "idle"
        assert snap.generated_at > 0

    def test_snapshot_to_dict_keys(self) -> None:
        rt = _make_empty_runtime()
        d = rt.snapshot().to_dict()
        expected = {
            "health", "total_agent_types", "available_executor_count",
            "active_dispatches", "idle_agents", "overloaded_agents",
            "pending_delegations", "delegation_success_rate",
            "capability_coverage", "queue_depth", "generated_at",
        }
        assert set(d.keys()) == expected

    def test_snapshot_with_agents(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [
            MockAgentType(),
            MockAgentType(agent_type_id="researcher", label="Researcher", allowed_domains=["research"]),
        ]
        fleet = MagicMock()
        fleet.active_dispatches.return_value = [MockDispatch()]
        delegation = MagicMock()
        delegation.pending_delegations.return_value = []
        delegation.snapshot.return_value = MockDelegationSnap()
        rt = _make_runtime(agent_registry=registry, agent_fleet=fleet, delegation_readiness=delegation)
        snap = rt.snapshot()
        assert snap.total_agent_types == 2
        assert len(snap.active_dispatches) == 1
        assert len(snap.idle_agents) == 1
        assert snap.idle_agents[0]["agent_type_id"] == "researcher"


# ── Public API ────────────────────────────────────────────────────────


class TestPublicAPI:
    def test_idle_returns_non_active(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [
            MockAgentType(),
            MockAgentType(agent_type_id="reviewer", label="Reviewer"),
        ]
        fleet = MagicMock()
        fleet.active_dispatches.return_value = [MockDispatch(agent_type="builder")]
        rt = _make_runtime(agent_registry=registry, agent_fleet=fleet)
        idle = rt.idle()
        assert len(idle) == 1
        assert idle[0]["agent_type_id"] == "reviewer"

    def test_overloaded_detects_multi_dispatch(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [MockAgentType()]
        fleet = MagicMock()
        fleet.active_dispatches.return_value = [
            MockDispatch(agent_type="builder", work_id="1"),
            MockDispatch(agent_type="builder", work_id="2"),
        ]
        rt = _make_runtime(agent_registry=registry, agent_fleet=fleet)
        overloaded = rt.overloaded()
        assert len(overloaded) == 1
        assert overloaded[0]["active_count"] == 2

    def test_capability_gaps_includes_uncovered(self) -> None:
        registry = MagicMock()
        registry.list_agents.return_value = [MockAgentType(allowed_domains=["engineering"])]
        rt = _make_runtime(agent_registry=registry)
        gaps = rt.capability_gaps()
        assert "research" in gaps
        assert "engineering" not in gaps

    def test_summary_keys(self) -> None:
        rt = _make_empty_runtime()
        s = rt.summary()
        assert s["ok"] is True
        assert "health" in s
        assert "total_agent_types" in s


# ── Graceful degradation ─────────────────────────────────────────────


class TestGracefulDegradation:
    def test_empty_deps_produce_empty(self) -> None:
        rt = _make_empty_runtime()
        snap = rt.snapshot()
        assert snap.active_dispatches == []
        assert snap.idle_agents == []
        assert snap.pending_delegations == []

    def test_exception_in_fleet(self) -> None:
        fleet = MagicMock()
        fleet.active_dispatches.side_effect = RuntimeError("boom")
        rt = _make_runtime(agent_fleet=fleet)
        snap = rt.snapshot()
        assert snap.active_dispatches == []


# ── Type registration ─────────────────────────────────────────────────


class TestTypeRegistration:
    def test_types_registered(self) -> None:
        from substrate.canonical_types import lookup
        assert lookup("WorkforceHealth") is not None
        assert lookup("AgentWorkforceSnapshot") is not None
        assert lookup("AgentWorkforceRuntime") is not None

    def test_enum_values(self) -> None:
        assert WorkforceHealth.OPTIMAL.value == "optimal"
        assert WorkforceHealth.OVERLOADED.value == "overloaded"
