"""Tests for Campaign 9.5 — Decision Impact Engine."""

from __future__ import annotations

import sys
import time

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.decision_impact_engine import (
    DecisionImpact,
    DecisionImpactEngine,
)
from substrate.organism.decision_registry import StrategicDecision
from substrate.organism.assumption_tracking_runtime import AssumptionRecord


# ── Mock Helpers ──────────────────────────────────────────────────────────


class MockDecisionRegistry:
    def __init__(self, decisions: list[StrategicDecision] | None = None):
        self._decisions = {d.decision_id: d for d in (decisions or [])}

    def get(self, decision_id: str) -> StrategicDecision | None:
        return self._decisions.get(decision_id)

    def list_decisions(self) -> list[StrategicDecision]:
        return list(self._decisions.values())

    def active_decisions(self) -> list[StrategicDecision]:
        return [d for d in self._decisions.values() if d.status == "active"]


class MockGoalHierarchy:
    def __init__(self, descendants_map: dict[str, list] | None = None):
        self._descendants = descendants_map or {}

    def descendants(self, goal_id: str) -> list:
        return self._descendants.get(goal_id, [])


class MockGoalChild:
    def __init__(self, goal_id: str):
        self.goal_id = goal_id


class MockAssumptionTracking:
    def __init__(self, assumptions: list[AssumptionRecord] | None = None):
        self._assumptions = assumptions or []

    def assumptions_for_decision(self, decision_id: str) -> list[AssumptionRecord]:
        return [a for a in self._assumptions if decision_id in a.decision_refs]


# ── DecisionImpact Dataclass ─────────────────────────────────────────────


class TestDecisionImpact:
    def test_defaults(self) -> None:
        d = DecisionImpact()
        assert d.decision_id == ""
        assert d.decision_title == ""
        assert d.affected_goals == []
        assert d.affected_work_packets == []
        assert d.affected_decisions == []
        assert d.blast_radius == 0
        assert d.risk_level == "low"
        assert d.cascading_invalidations == []
        assert d.generated_at == 0.0

    def test_to_dict_keys(self) -> None:
        d = DecisionImpact()
        keys = set(d.to_dict().keys())
        expected = {
            "decision_id", "decision_title", "affected_goals",
            "affected_work_packets", "affected_decisions",
            "blast_radius", "risk_level", "cascading_invalidations",
            "generated_at",
        }
        assert keys == expected

    def test_to_dict_values(self) -> None:
        d = DecisionImpact(
            decision_id="sd-1",
            decision_title="Use Clerk",
            affected_goals=[{"goal_id": "g-1", "relationship": "direct"}],
            blast_radius=3,
            risk_level="medium",
        )
        out = d.to_dict()
        assert out["decision_id"] == "sd-1"
        assert out["decision_title"] == "Use Clerk"
        assert len(out["affected_goals"]) == 1
        assert out["blast_radius"] == 3
        assert out["risk_level"] == "medium"

    def test_from_dict_round_trip(self) -> None:
        original = DecisionImpact(
            decision_id="sd-1",
            decision_title="Use Clerk",
            affected_goals=[{"goal_id": "g-1"}],
            affected_work_packets=[{"work_packet_id": "wp-1"}],
            affected_decisions=[{"decision_id": "sd-2"}],
            blast_radius=5,
            risk_level="high",
            cascading_invalidations=["asm-1"],
            generated_at=100.0,
        )
        restored = DecisionImpact.from_dict(original.to_dict())
        assert restored.decision_id == original.decision_id
        assert restored.affected_goals == original.affected_goals
        assert restored.blast_radius == original.blast_radius
        assert restored.risk_level == original.risk_level
        assert restored.cascading_invalidations == original.cascading_invalidations

    def test_from_dict_defaults(self) -> None:
        d = DecisionImpact.from_dict({})
        assert d.decision_id == ""
        assert d.blast_radius == 0
        assert d.risk_level == "low"

    def test_to_dict_immutability(self) -> None:
        d = DecisionImpact(affected_goals=[{"goal_id": "g-1"}])
        out = d.to_dict()
        out["affected_goals"].append({"goal_id": "g-2"})
        assert len(d.affected_goals) == 1


# ── DecisionImpactEngine ─────────────────────────────────────────────────


class TestDecisionImpactEngine:
    def test_assess_no_deps(self) -> None:
        engine = DecisionImpactEngine()
        result = engine.assess("sd-1")
        assert result.decision_id == "sd-1"
        assert result.decision_title == ""
        assert result.blast_radius == 0

    def test_assess_with_registry(self) -> None:
        d = StrategicDecision(decision_id="sd-1", title="Use Clerk", status="active")
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert result.decision_title == "Use Clerk"

    def test_assess_missing_decision(self) -> None:
        reg = MockDecisionRegistry([])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("nonexistent")
        assert result.decision_title == ""
        assert result.blast_radius == 0

    def test_assess_affected_goals_direct(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1", "g-2"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert len(result.affected_goals) == 2
        assert all(g["relationship"] == "direct" for g in result.affected_goals)

    def test_assess_affected_goals_with_hierarchy(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        hier = MockGoalHierarchy({
            "g-1": [MockGoalChild("g-1a"), MockGoalChild("g-1b")],
        })
        engine = DecisionImpactEngine(decision_registry=reg, goal_hierarchy=hier)
        result = engine.assess("sd-1")
        assert len(result.affected_goals) == 3
        direct = [g for g in result.affected_goals if g["relationship"] == "direct"]
        descendants = [g for g in result.affected_goals if g["relationship"] == "descendant"]
        assert len(direct) == 1
        assert len(descendants) == 2

    def test_assess_deduplicates_goals(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        hier = MockGoalHierarchy({"g-1": [MockGoalChild("g-1")]})
        engine = DecisionImpactEngine(decision_registry=reg, goal_hierarchy=hier)
        result = engine.assess("sd-1")
        assert len(result.affected_goals) == 1

    def test_assess_affected_work_packets(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            work_packet_refs=["wp-1", "wp-2"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert len(result.affected_work_packets) == 2
        assert result.affected_work_packets[0]["work_packet_id"] == "wp-1"

    def test_assess_finds_superseding_decisions(self) -> None:
        d1 = StrategicDecision(decision_id="sd-1", title="Old", status="active")
        d2 = StrategicDecision(decision_id="sd-2", title="New", status="active", supersedes="sd-1")
        reg = MockDecisionRegistry([d1, d2])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert len(result.affected_decisions) == 1
        assert result.affected_decisions[0]["relationship"] == "supersedes_this"

    def test_assess_cascading_invalidations(self) -> None:
        d = StrategicDecision(decision_id="sd-1", title="Test", status="active")
        reg = MockDecisionRegistry([d])
        asm1 = AssumptionRecord(assumption_id="asm-1", decision_refs=["sd-1"])
        asm2 = AssumptionRecord(assumption_id="asm-2", decision_refs=["sd-1"])
        asm_track = MockAssumptionTracking([asm1, asm2])
        engine = DecisionImpactEngine(
            decision_registry=reg, assumption_tracking=asm_track
        )
        result = engine.assess("sd-1")
        assert len(result.cascading_invalidations) == 2
        assert "asm-1" in result.cascading_invalidations

    def test_blast_radius_sum(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"], work_packet_refs=["wp-1"],
        )
        asm = AssumptionRecord(assumption_id="asm-1", decision_refs=["sd-1"])
        reg = MockDecisionRegistry([d])
        asm_track = MockAssumptionTracking([asm])
        engine = DecisionImpactEngine(
            decision_registry=reg, assumption_tracking=asm_track
        )
        result = engine.assess("sd-1")
        expected = (
            len(result.affected_goals)
            + len(result.affected_work_packets)
            + len(result.affected_decisions)
            + len(result.cascading_invalidations)
        )
        assert result.blast_radius == expected

    def test_risk_classification_low(self) -> None:
        d = StrategicDecision(decision_id="sd-1", title="T", status="active")
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert result.risk_level == "low"

    def test_risk_classification_medium(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="T", status="active",
            goal_refs=["g-1", "g-2"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert result.risk_level == "medium"

    def test_risk_classification_high(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="T", status="active",
            goal_refs=["g-1", "g-2", "g-3", "g-4", "g-5"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert result.risk_level == "high"

    def test_risk_classification_critical(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="T", status="active",
            goal_refs=[f"g-{i}" for i in range(10)],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert result.risk_level == "critical"

    def test_assess_change_invalidated_escalates(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="T", status="active",
            goal_refs=["g-1", "g-2", "g-3", "g-4", "g-5"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess_change("sd-1", "invalidated")
        assert result.risk_level == "critical"

    def test_assess_change_superseded_escalates(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="T", status="active",
            goal_refs=["g-1", "g-2", "g-3"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess_change("sd-1", "superseded")
        assert result.risk_level == "high"

    def test_assess_change_active_no_escalation(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="T", status="active",
            goal_refs=["g-1", "g-2", "g-3"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess_change("sd-1", "active")
        assert result.risk_level == "medium"

    def test_highest_impact_sorted(self) -> None:
        d1 = StrategicDecision(
            decision_id="sd-1", title="Small", status="active",
            goal_refs=["g-1"],
        )
        d2 = StrategicDecision(
            decision_id="sd-2", title="Big", status="active",
            goal_refs=["g-1", "g-2", "g-3", "g-4", "g-5"],
        )
        reg = MockDecisionRegistry([d1, d2])
        engine = DecisionImpactEngine(decision_registry=reg)
        results = engine.highest_impact()
        assert results[0].decision_title == "Big"
        assert results[1].decision_title == "Small"

    def test_highest_impact_respects_limit(self) -> None:
        decisions = [
            StrategicDecision(decision_id=f"sd-{i}", title=f"D{i}", status="active")
            for i in range(10)
        ]
        reg = MockDecisionRegistry(decisions)
        engine = DecisionImpactEngine(decision_registry=reg)
        results = engine.highest_impact(limit=3)
        assert len(results) == 3

    def test_highest_impact_no_registry(self) -> None:
        engine = DecisionImpactEngine()
        assert engine.highest_impact() == []

    def test_summary_keys(self) -> None:
        d = StrategicDecision(decision_id="sd-1", title="T", status="active")
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        s = engine.summary()
        expected = {
            "total_assessed", "high_impact_count",
            "average_blast_radius", "generated_at",
        }
        assert set(s.keys()) == expected

    def test_summary_with_data(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="T", status="active",
            goal_refs=["g-1", "g-2", "g-3", "g-4", "g-5"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        s = engine.summary()
        assert s["total_assessed"] == 1
        assert s["high_impact_count"] == 1
        assert s["average_blast_radius"] == 5.0

    def test_summary_empty(self) -> None:
        engine = DecisionImpactEngine()
        s = engine.summary()
        assert s["total_assessed"] == 0
        assert s["high_impact_count"] == 0
        assert s["average_blast_radius"] == 0.0

    def test_graceful_no_assumption_tracking(self) -> None:
        d = StrategicDecision(decision_id="sd-1", title="T", status="active")
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert result.cascading_invalidations == []

    def test_graceful_no_goal_hierarchy(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="T", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionImpactEngine(decision_registry=reg)
        result = engine.assess("sd-1")
        assert len(result.affected_goals) == 1
        assert result.affected_goals[0]["relationship"] == "direct"
