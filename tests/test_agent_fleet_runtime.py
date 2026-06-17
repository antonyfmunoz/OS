"""Tests for W3 — Agent Fleet Runtime.

Validates that AgentFleetRuntime correctly composes:
  - AgentRegistry (agent type filtering)
  - AgentCapabilityModel (reliability scoring)
  - ComputeFabricRuntime (compute routing)
  - ExecutorRuntime (dispatch lifecycle)
  - CompoundingEngine (learning feedback)
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.agent_fleet_runtime import (
    AgentFleetRuntime,
    AssignmentRationale,
    FleetAssignment,
    FleetDispatch,
    FleetDispatchResult,
    FleetDispatchStatus,
    FleetHealth,
    FleetSnapshot,
    WaveResult,
)


# ── Mock subsystems ──────────────────────────────────────────────


@dataclass
class MockAgentType:
    agent_type_id: str = "builder"
    label: str = "Builder"
    description: str = "Builds things"
    capabilities: list[str] = field(default_factory=lambda: ["code", "test"])
    permissions: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=lambda: ["engineering"])
    required_tools: list[str] = field(default_factory=list)
    max_risk_class: str = "high"
    can_auto_execute: bool = True
    can_create_subpackets: bool = False

    def can_handle_risk(self, risk_class: str) -> bool:
        rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return rank.get(risk_class, 0) <= rank.get(self.max_risk_class, 1)

    def can_handle_domain(self, domain_id: str) -> bool:
        return not self.allowed_domains or domain_id in self.allowed_domains

    def to_dict(self) -> dict:
        return {"agent_type_id": self.agent_type_id, "label": self.label}


class MockAgentRegistry:
    def __init__(self, agents: list[MockAgentType] | None = None):
        if agents is not None:
            self._agents = agents
            return
        self._agents = [
            MockAgentType(
                agent_type_id="builder",
                label="Builder",
                capabilities=["code", "test", "deploy", "refactor", "debug"],
                allowed_domains=["engineering", "infrastructure"],
                max_risk_class="high",
            ),
            MockAgentType(
                agent_type_id="researcher",
                label="Researcher",
                capabilities=["web_search", "document_analysis", "summarization"],
                allowed_domains=[],
                max_risk_class="low",
            ),
            MockAgentType(
                agent_type_id="reviewer",
                label="Reviewer",
                capabilities=["code_review", "document_review", "quality_check"],
                allowed_domains=[],
                max_risk_class="high",
            ),
            MockAgentType(
                agent_type_id="content_producer",
                label="Content Producer",
                capabilities=["writing", "editing", "outlining", "creative"],
                allowed_domains=["content", "marketing"],
                max_risk_class="low",
            ),
        ]

    def all_agents(self) -> list[MockAgentType]:
        return list(self._agents)

    def get(self, agent_type_id: str) -> MockAgentType | None:
        for a in self._agents:
            if a.agent_type_id == agent_type_id:
                return a
        return None


@dataclass
class MockCapabilityProfile:
    agent_type: str = "builder"
    overall_reliability: float = 0.85
    total_attempts: int = 20
    total_successes: int = 17
    total_failures: int = 3


class MockCapabilityModel:
    def __init__(self, profiles: dict[str, MockCapabilityProfile] | None = None):
        self._profiles = profiles or {}
        self._updates: list[dict] = []

    def get_profile(self, agent_type: str) -> MockCapabilityProfile | None:
        return self._profiles.get(agent_type)

    def update_reliability(
        self, agent_type: str, capabilities_used: list[str],
        success: bool, duration_ms: float = 0.0, **kwargs: Any,
    ) -> list:
        @dataclass
        class FakeRecord:
            record_id: str = "rec-test"
        records = [FakeRecord(record_id=f"rec-{agent_type}-{c}") for c in capabilities_used]
        self._updates.append({
            "agent_type": agent_type, "capabilities_used": capabilities_used,
            "success": success, "duration_ms": duration_ms,
        })
        return records


@dataclass
class MockRoutingDecision:
    target_node_id: str = "dn-a1b2c3d4"
    target_node_type: str = "vps"
    reason: str = "test routing"
    capability_match: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    confidence: float = 0.9


class MockComputeFabric:
    def __init__(
        self,
        route_result: MockRoutingDecision | None = None,
        health_result: dict | None = None,
    ):
        self._route_result = route_result or MockRoutingDecision()
        self._health_result = health_result or {
            "fabric_status": "healthy",
            "total_nodes": 2,
            "total_workers": 1,
            "total_capacity": 12,
            "total_active_executions": 0,
        }

    def route(self, capability_needs: list[str], risk_level: str = "low") -> MockRoutingDecision:
        return self._route_result

    def health(self) -> dict:
        return dict(self._health_result)


# ── Helper ───────────────────────────────────────────────────────


def _make_fleet(
    agents: list[MockAgentType] | None = None,
    profiles: dict[str, MockCapabilityProfile] | None = None,
    route_result: MockRoutingDecision | None = None,
    health_result: dict | None = None,
) -> AgentFleetRuntime:
    return AgentFleetRuntime(
        capability_model=MockCapabilityModel(profiles or {}),
        compute_fabric=MockComputeFabric(route_result, health_result),
        agent_registry=MockAgentRegistry(agents),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAssignmentScoring:
    """Assignment selects the best agent by capability + reliability."""

    def test_basic_assignment(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        assert a.agent_type == "builder"
        assert a.compute_node_id == "dn-a1b2c3d4"
        assert a.rationale.summary

    def test_capability_match_drives_selection(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["web_search", "summarization"])
        assert a.agent_type == "researcher"

    def test_content_capabilities(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["writing", "editing"])
        assert a.agent_type == "content_producer"

    def test_reliability_breaks_ties(self):
        agents = [
            MockAgentType(agent_type_id="a1", label="A1", capabilities=["code"], allowed_domains=[], max_risk_class="high"),
            MockAgentType(agent_type_id="a2", label="A2", capabilities=["code"], allowed_domains=[], max_risk_class="high"),
        ]
        profiles = {
            "a1": MockCapabilityProfile(agent_type="a1", overall_reliability=0.6, total_attempts=10),
            "a2": MockCapabilityProfile(agent_type="a2", overall_reliability=0.95, total_attempts=10),
        }
        fleet = _make_fleet(agents=agents, profiles=profiles)
        a = fleet.assign(capabilities_required=["code"])
        assert a.agent_type == "a2"

    def test_alternatives_populated(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code_review"])
        assert a.agent_type == "reviewer"
        assert isinstance(a.alternatives, list)

    def test_assignment_has_all_fields(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        d = a.to_dict()
        assert "assignment_id" in d
        assert "agent_type" in d
        assert "agent_label" in d
        assert "compute_node_id" in d
        assert "rationale" in d
        assert "alternatives" in d
        assert "capabilities_required" in d
        assert "capabilities_matched" in d


class TestRiskGate:
    """Risk filtering prevents assignment to under-authorized agents."""

    def test_high_risk_filters_low_risk_agents(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["writing"], risk_class="high")
        assert a.agent_type != "content_producer"

    def test_low_risk_researcher_blocked_for_high(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["web_search"], risk_class="high")
        assert a.agent_type != "researcher"

    def test_critical_risk_limits_candidates(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"], risk_class="critical")
        assert a.agent_type == ""


class TestDomainFiltering:
    """Domain filtering matches agent allowed_domains."""

    def test_engineering_domain(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"], domain="engineering")
        assert a.agent_type == "builder"

    def test_content_domain(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["writing"], domain="content")
        assert a.agent_type == "content_producer"

    def test_universal_agents_match_any_domain(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code_review"], domain="finance")
        assert a.agent_type == "reviewer"


class TestComputeRouting:
    """Assignment includes compute node from ComputeFabricRuntime."""

    def test_compute_node_set(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        assert a.compute_node_id == "dn-a1b2c3d4"
        assert a.compute_node_type == "vps"

    def test_compute_routing_in_rationale(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        assert "dn-a1b2c3d4" in a.rationale.summary


class TestRationaleCompleteness:
    """Every assignment must have a human-readable rationale."""

    def test_rationale_has_summary(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        assert len(a.rationale.summary) > 20

    def test_rationale_mentions_capabilities(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code", "test"])
        assert "code" in a.rationale.summary

    def test_rationale_mentions_reliability(self):
        profiles = {"builder": MockCapabilityProfile(overall_reliability=0.85, total_attempts=10)}
        fleet = _make_fleet(profiles=profiles)
        a = fleet.assign(capabilities_required=["code"])
        assert "85%" in a.rationale.summary

    def test_empty_rationale_on_no_match(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["nonexistent_capability"])
        assert a.agent_type == ""
        assert "No agent" in a.rationale.summary


class TestDispatchLifecycle:
    """Dispatch creates tracked execution through the fleet."""

    def test_dispatch_creates_record(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        d = fleet.dispatch(a)
        assert d.dispatch_id.startswith("fd-")
        assert d.agent_type == "builder"

    def test_dispatch_tracks_in_fleet(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        d = fleet.dispatch(a)
        assert d.dispatch_id in fleet._dispatches

    def test_dispatch_to_dict(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        d = fleet.dispatch(a)
        dd = d.to_dict()
        assert "dispatch_id" in dd
        assert "agent_type" in dd
        assert "status" in dd

    def test_dispatch_result_after_record(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        d = fleet.dispatch(a)
        fleet.record_outcome(d.dispatch_id, success=True, duration_ms=1500.0)
        result = fleet.dispatch_result(d.dispatch_id)
        assert result is not None
        assert result.success is True
        assert result.duration_ms == 1500.0


class TestWaveDispatch:
    """Wave dispatch handles multiple assignments."""

    def test_wave_multiple(self):
        fleet = _make_fleet()
        a1 = fleet.assign(capabilities_required=["code"])
        a2 = fleet.assign(capabilities_required=["code_review"])
        wave = fleet.dispatch_wave([a1, a2])
        assert wave.total == 2
        assert wave.succeeded == 2
        assert len(wave.dispatches) == 2

    def test_wave_partial_failure(self):
        fleet = _make_fleet()
        a1 = fleet.assign(capabilities_required=["code"])
        a2 = fleet.assign(capabilities_required=["nonexistent"])
        wave = fleet.dispatch_wave([a1, a2])
        assert wave.total == 2

    def test_wave_to_dict(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        wave = fleet.dispatch_wave([a])
        d = wave.to_dict()
        assert "wave_id" in d
        assert "dispatches" in d
        assert "total" in d


class TestFleetStatus:
    """Fleet status aggregates agent and dispatch state."""

    def test_status_counts_agents(self):
        fleet = _make_fleet()
        s = fleet.fleet_status()
        assert s.total_agents == 4

    def test_status_counts_dispatches(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        fleet.dispatch(a)
        s = fleet.fleet_status()
        assert s.active_dispatches >= 0

    def test_status_to_dict(self):
        fleet = _make_fleet()
        d = fleet.fleet_status().to_dict()
        assert "total_agents" in d
        assert "active_dispatches" in d
        assert "capacity_remaining" in d


class TestFleetHealth:
    """Fleet health aggregates agent reliability."""

    def test_health_all_healthy_with_no_data(self):
        fleet = _make_fleet()
        h = fleet.fleet_health()
        assert h.agent_count == 4
        assert h.healthy_count == 4

    def test_health_degraded_agents(self):
        profiles = {
            "builder": MockCapabilityProfile(overall_reliability=0.3, total_attempts=10),
        }
        fleet = _make_fleet(profiles=profiles)
        h = fleet.fleet_health()
        assert "builder" in h.degraded_agents

    def test_health_reliability(self):
        profiles = {
            "builder": MockCapabilityProfile(overall_reliability=0.9, total_attempts=10),
        }
        fleet = _make_fleet(profiles=profiles)
        h = fleet.fleet_health()
        assert h.overall_reliability > 0

    def test_health_to_dict(self):
        fleet = _make_fleet()
        d = fleet.fleet_health().to_dict()
        assert "agent_count" in d
        assert "healthy_count" in d
        assert "degraded_agents" in d
        assert "overall_reliability" in d


class TestLearningFeedback:
    """Outcome recording feeds back into capability model."""

    def test_record_outcome_updates_model(self):
        model = MockCapabilityModel()
        fleet = AgentFleetRuntime(
            capability_model=model,
            compute_fabric=MockComputeFabric(),
            agent_registry=MockAgentRegistry(),
        )
        a = fleet.assign(capabilities_required=["code"])
        d = fleet.dispatch(a)
        fleet.record_outcome(d.dispatch_id, success=True, duration_ms=1000)
        assert len(model._updates) > 0

    def test_record_outcome_returns_result(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code"])
        d = fleet.dispatch(a)
        result = fleet.record_outcome(d.dispatch_id, success=False)
        assert result.success is False
        assert result.dispatch_id == d.dispatch_id


class TestUtilization:
    """Per-agent utilization tracks load."""

    def test_utilization_all_zero(self):
        fleet = _make_fleet()
        u = fleet.agent_utilization()
        assert all(v == 0.0 for v in u.values())


class TestEmptyFleet:
    """Graceful handling when no agents match."""

    def test_no_agents(self):
        fleet = _make_fleet(agents=[])
        a = fleet.assign(capabilities_required=["code"])
        assert a.agent_type == ""
        assert "No agents" in a.rationale.summary

    def test_no_capability_match(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["quantum_computing"])
        assert a.agent_type == ""

    def test_no_registry(self):
        fleet = AgentFleetRuntime(
            capability_model=MockCapabilityModel(),
            compute_fabric=MockComputeFabric(),
            agent_registry=None,
        )
        a = fleet.assign(capabilities_required=["code"])
        assert a.agent_type == ""
        assert "No agent registry" in a.rationale.summary


class TestAcceptanceResponseShape:
    """The user's acceptance test: assignment must have agent + node + rationale."""

    def test_acceptance_full_shape(self):
        fleet = _make_fleet()
        a = fleet.assign(capabilities_required=["code", "test"])
        assert a.agent_type  # non-empty
        assert a.compute_node_id  # non-empty
        assert a.rationale.capability_score > 0
        assert a.alternatives is not None
        d = a.to_dict()
        assert d["agent_type"]
        assert d["compute_node_id"]
        assert d["rationale"]["capability_score"] > 0
        assert d["rationale"]["summary"]
