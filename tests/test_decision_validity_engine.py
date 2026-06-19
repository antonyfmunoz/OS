"""Tests for Campaign 9.3 — Decision Validity Engine."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.decision_validity_engine import (
    DecisionValidityEngine,
    DecisionValidity,
    ValidityStatus,
)
from substrate.organism.decision_registry import StrategicDecision
from substrate.organism.assumption_tracking_runtime import (
    AssumptionRecord,
    AssumptionStatus,
)


# ── Mock helpers ──────────────────────────────────────────────────────────


class MockDecisionRegistry:
    def __init__(self, decisions: list[StrategicDecision] | None = None) -> None:
        self._decisions = {d.decision_id: d for d in (decisions or [])}

    def get(self, decision_id: str) -> StrategicDecision | None:
        return self._decisions.get(decision_id)

    def active_decisions(self) -> list[StrategicDecision]:
        return [d for d in self._decisions.values() if d.status == "active"]


class MockAssumptionTracking:
    def __init__(self, assumptions: list[AssumptionRecord] | None = None) -> None:
        self._assumptions = {a.assumption_id: a for a in (assumptions or [])}

    def get(self, assumption_id: str) -> AssumptionRecord | None:
        return self._assumptions.get(assumption_id)


@dataclass
class MockAlignmentReport:
    alignment_score: float = 0.8


class MockGoalAlignment:
    def __init__(self, score: float = 0.8) -> None:
        self._score = score

    def report(self) -> MockAlignmentReport:
        return MockAlignmentReport(alignment_score=self._score)


class MockOutcomeTracking:
    def __init__(self, completions: dict[str, float] | None = None) -> None:
        self._completions = completions or {}

    def completion(self, goal_id: str) -> float:
        return self._completions.get(goal_id, 0.0)


# ── ValidityStatus ────────────────────────────────────────────────────────


class TestValidityStatus:
    def test_values(self) -> None:
        assert ValidityStatus.VALID.value == "valid"
        assert ValidityStatus.WATCH.value == "watch"
        assert ValidityStatus.AT_RISK.value == "at_risk"
        assert ValidityStatus.INVALID.value == "invalid"

    def test_count(self) -> None:
        assert len(ValidityStatus) == 4

    def test_string_enum(self) -> None:
        assert isinstance(ValidityStatus.VALID, str)
        assert ValidityStatus.VALID == "valid"


# ── DecisionValidity ──────────────────────────────────────────────────────


class TestDecisionValidity:
    def test_defaults(self) -> None:
        v = DecisionValidity()
        assert v.decision_id == ""
        assert v.validity == "valid"
        assert v.assumption_health == {}
        assert v.risk_factors == []

    def test_to_dict_keys(self) -> None:
        v = DecisionValidity()
        keys = set(v.to_dict().keys())
        expected = {
            "decision_id", "decision_title", "validity",
            "assumption_health", "goal_alignment", "outcome_progress",
            "risk_factors", "recommendation", "generated_at",
        }
        assert keys == expected

    def test_to_dict_values(self) -> None:
        v = DecisionValidity(
            decision_id="sd-1",
            decision_title="Use Clerk",
            validity="at_risk",
            recommendation="review",
        )
        out = v.to_dict()
        assert out["decision_id"] == "sd-1"
        assert out["validity"] == "at_risk"
        assert out["recommendation"] == "review"

    def test_from_dict_round_trip(self) -> None:
        original = DecisionValidity(
            decision_id="sd-1",
            decision_title="Test",
            validity="watch",
            assumption_health={"total": 2, "invalidated": 1},
            goal_alignment="drifted",
            outcome_progress=0.5,
            risk_factors=["goal alignment drifted"],
            recommendation="monitor",
            generated_at=1000.0,
        )
        restored = DecisionValidity.from_dict(original.to_dict())
        assert restored.decision_id == original.decision_id
        assert restored.validity == original.validity
        assert restored.assumption_health == original.assumption_health
        assert restored.goal_alignment == original.goal_alignment
        assert restored.outcome_progress == original.outcome_progress
        assert restored.risk_factors == original.risk_factors
        assert restored.recommendation == original.recommendation

    def test_from_dict_defaults(self) -> None:
        v = DecisionValidity.from_dict({})
        assert v.validity == "valid"
        assert v.risk_factors == []

    def test_to_dict_immutability(self) -> None:
        v = DecisionValidity(risk_factors=["a"])
        out = v.to_dict()
        out["risk_factors"].append("b")
        assert v.risk_factors == ["a"]


# ── DecisionValidityEngine ────────────────────────────────────────────────


class TestDecisionValidityEngine:
    def test_evaluate_no_deps(self) -> None:
        engine = DecisionValidityEngine()
        result = engine.evaluate("sd-1")
        assert result.validity == "invalid"
        assert result.recommendation == "not_found"

    def test_evaluate_missing_decision(self) -> None:
        reg = MockDecisionRegistry([])
        engine = DecisionValidityEngine(decision_registry=reg)
        result = engine.evaluate("nonexistent")
        assert result.validity == "invalid"
        assert result.recommendation == "not_found"

    def test_evaluate_healthy_decision(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Use Clerk", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        ga = MockGoalAlignment(score=0.9)
        ot = MockOutcomeTracking({"g-1": 0.5})
        engine = DecisionValidityEngine(
            decision_registry=reg, goal_alignment=ga, outcome_tracking=ot,
        )
        result = engine.evaluate("sd-1")
        assert result.decision_title == "Use Clerk"
        assert result.validity == "valid"
        assert result.recommendation == "maintain"

    def test_evaluate_all_assumptions_invalidated(self) -> None:
        asm1 = AssumptionRecord(assumption_id="asm-1", status="invalidated")
        asm2 = AssumptionRecord(assumption_id="asm-2", status="invalidated")
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            assumptions=["asm-1", "asm-2"],
        )
        reg = MockDecisionRegistry([d])
        at = MockAssumptionTracking([asm1, asm2])
        engine = DecisionValidityEngine(decision_registry=reg, assumption_tracking=at)
        result = engine.evaluate("sd-1")
        assert result.validity == "invalid"
        assert result.recommendation == "invalidate"

    def test_evaluate_majority_assumptions_invalidated(self) -> None:
        asm1 = AssumptionRecord(assumption_id="asm-1", status="invalidated")
        asm2 = AssumptionRecord(assumption_id="asm-2", status="invalidated")
        asm3 = AssumptionRecord(assumption_id="asm-3", status="active")
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            assumptions=["asm-1", "asm-2", "asm-3"],
        )
        reg = MockDecisionRegistry([d])
        at = MockAssumptionTracking([asm1, asm2, asm3])
        engine = DecisionValidityEngine(decision_registry=reg, assumption_tracking=at)
        result = engine.evaluate("sd-1")
        # 2/3 >= 0.5 → INVALID + supersede
        assert result.validity == "invalid"
        assert result.recommendation == "supersede"

    def test_evaluate_some_assumptions_invalidated(self) -> None:
        asm1 = AssumptionRecord(assumption_id="asm-1", status="invalidated")
        asm2 = AssumptionRecord(assumption_id="asm-2", status="active")
        asm3 = AssumptionRecord(assumption_id="asm-3", status="active")
        asm4 = AssumptionRecord(assumption_id="asm-4", status="active")
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            assumptions=["asm-1", "asm-2", "asm-3", "asm-4"],
        )
        reg = MockDecisionRegistry([d])
        at = MockAssumptionTracking([asm1, asm2, asm3, asm4])
        engine = DecisionValidityEngine(decision_registry=reg, assumption_tracking=at)
        result = engine.evaluate("sd-1")
        # 1/4 < 0.5 → AT_RISK + review
        assert result.validity == "at_risk"
        assert result.recommendation == "review"

    def test_evaluate_goals_orphaned(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        ga = MockGoalAlignment(score=0.2)  # < 0.4 → orphaned
        engine = DecisionValidityEngine(decision_registry=reg, goal_alignment=ga)
        result = engine.evaluate("sd-1")
        assert result.goal_alignment == "orphaned"
        assert result.validity == "at_risk"
        assert result.recommendation == "review"

    def test_evaluate_goals_drifted(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        ga = MockGoalAlignment(score=0.5)  # >= 0.4 and < 0.7 → drifted
        engine = DecisionValidityEngine(decision_registry=reg, goal_alignment=ga)
        result = engine.evaluate("sd-1")
        assert result.goal_alignment == "drifted"
        assert result.validity == "watch"
        assert result.recommendation == "monitor"

    def test_evaluate_goals_aligned(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        ga = MockGoalAlignment(score=0.9)  # >= 0.7 → aligned
        engine = DecisionValidityEngine(decision_registry=reg, goal_alignment=ga)
        result = engine.evaluate("sd-1")
        assert result.goal_alignment == "aligned"

    def test_evaluate_no_goals_returns_no_goals(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=[],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionValidityEngine(decision_registry=reg)
        result = engine.evaluate("sd-1")
        assert result.goal_alignment == "no_goals"

    def test_evaluate_outcome_progress(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1", "g-2"],
        )
        reg = MockDecisionRegistry([d])
        ot = MockOutcomeTracking({"g-1": 0.6, "g-2": 0.8})
        engine = DecisionValidityEngine(decision_registry=reg, outcome_tracking=ot)
        result = engine.evaluate("sd-1")
        assert abs(result.outcome_progress - 0.7) < 0.01

    def test_evaluate_near_zero_progress_risk(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        ot = MockOutcomeTracking({"g-1": 0.0})
        engine = DecisionValidityEngine(decision_registry=reg, outcome_tracking=ot)
        result = engine.evaluate("sd-1")
        assert "near-zero outcome progress" in result.risk_factors

    def test_evaluate_assumption_health_dict(self) -> None:
        asm1 = AssumptionRecord(assumption_id="asm-1", status="active")
        asm2 = AssumptionRecord(assumption_id="asm-2", status="validated")
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            assumptions=["asm-1", "asm-2"],
        )
        reg = MockDecisionRegistry([d])
        at = MockAssumptionTracking([asm1, asm2])
        engine = DecisionValidityEngine(decision_registry=reg, assumption_tracking=at)
        result = engine.evaluate("sd-1")
        ah = result.assumption_health
        assert ah["total"] == 2
        assert ah["active"] == 1
        assert ah["validated"] == 1
        assert ah["invalidated"] == 0

    def test_evaluate_unknown_assumption(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            assumptions=["asm-missing"],
        )
        reg = MockDecisionRegistry([d])
        at = MockAssumptionTracking([])  # asm-missing not found
        engine = DecisionValidityEngine(decision_registry=reg, assumption_tracking=at)
        result = engine.evaluate("sd-1")
        assert result.assumption_health["unknown"] == 1
        assert result.assumption_health["total"] == 1

    def test_evaluate_no_assumption_tracking(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            assumptions=["asm-1"],
        )
        reg = MockDecisionRegistry([d])
        engine = DecisionValidityEngine(decision_registry=reg)
        result = engine.evaluate("sd-1")
        assert result.assumption_health["total"] == 0

    def test_risk_factor_invalidated_assumptions(self) -> None:
        asm1 = AssumptionRecord(assumption_id="asm-1", status="invalidated")
        asm2 = AssumptionRecord(assumption_id="asm-2", status="active")
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            assumptions=["asm-1", "asm-2"],
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        at = MockAssumptionTracking([asm1, asm2])
        ga = MockGoalAlignment(score=0.9)
        ot = MockOutcomeTracking({"g-1": 0.8})
        engine = DecisionValidityEngine(
            decision_registry=reg, assumption_tracking=at,
            goal_alignment=ga, outcome_tracking=ot,
        )
        result = engine.evaluate("sd-1")
        assert any("invalidated" in r for r in result.risk_factors)

    def test_risk_factor_majority_untracked(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            assumptions=["asm-1", "asm-2", "asm-3"],
        )
        reg = MockDecisionRegistry([d])
        at = MockAssumptionTracking([])  # none found → all unknown
        engine = DecisionValidityEngine(decision_registry=reg, assumption_tracking=at)
        result = engine.evaluate("sd-1")
        assert any("untracked" in r for r in result.risk_factors)

    def test_evaluate_all(self) -> None:
        d1 = StrategicDecision(decision_id="sd-1", title="A", status="active")
        d2 = StrategicDecision(decision_id="sd-2", title="B", status="active")
        reg = MockDecisionRegistry([d1, d2])
        engine = DecisionValidityEngine(decision_registry=reg)
        results = engine.evaluate_all()
        assert len(results) == 2
        ids = {r.decision_id for r in results}
        assert ids == {"sd-1", "sd-2"}

    def test_evaluate_all_no_registry(self) -> None:
        engine = DecisionValidityEngine()
        assert engine.evaluate_all() == []

    def test_at_risk_filter(self) -> None:
        asm1 = AssumptionRecord(assumption_id="asm-1", status="invalidated")
        asm2 = AssumptionRecord(assumption_id="asm-2", status="active")
        asm3 = AssumptionRecord(assumption_id="asm-3", status="active")
        asm4 = AssumptionRecord(assumption_id="asm-4", status="active")
        d1 = StrategicDecision(
            decision_id="sd-1", title="Risky", status="active",
            assumptions=["asm-1", "asm-2", "asm-3", "asm-4"],
            goal_refs=["g-1"],
        )
        d2 = StrategicDecision(
            decision_id="sd-2", title="Healthy", status="active",
            goal_refs=["g-2"],
        )
        reg = MockDecisionRegistry([d1, d2])
        at = MockAssumptionTracking([asm1, asm2, asm3, asm4])
        ga = MockGoalAlignment(score=0.9)
        ot = MockOutcomeTracking({"g-1": 0.5, "g-2": 0.5})
        engine = DecisionValidityEngine(
            decision_registry=reg, assumption_tracking=at,
            goal_alignment=ga, outcome_tracking=ot,
        )
        risky = engine.at_risk()
        assert len(risky) == 1
        assert risky[0].decision_id == "sd-1"

    def test_invalid_filter(self) -> None:
        asm1 = AssumptionRecord(assumption_id="asm-1", status="invalidated")
        d1 = StrategicDecision(
            decision_id="sd-1", title="Invalid", status="active",
            assumptions=["asm-1"],
        )
        d2 = StrategicDecision(decision_id="sd-2", title="Healthy", status="active")
        reg = MockDecisionRegistry([d1, d2])
        at = MockAssumptionTracking([asm1])
        engine = DecisionValidityEngine(decision_registry=reg, assumption_tracking=at)
        invalids = engine.invalid()
        assert len(invalids) == 1
        assert invalids[0].decision_id == "sd-1"

    def test_summary_keys(self) -> None:
        d = StrategicDecision(decision_id="sd-1", title="A", status="active")
        reg = MockDecisionRegistry([d])
        engine = DecisionValidityEngine(decision_registry=reg)
        s = engine.summary()
        expected = {
            "total_evaluated", "by_validity", "at_risk_count",
            "invalid_count", "recommendations", "generated_at",
        }
        assert set(s.keys()) == expected

    def test_summary_counts(self) -> None:
        asm1 = AssumptionRecord(assumption_id="asm-1", status="invalidated")
        d1 = StrategicDecision(
            decision_id="sd-1", title="Invalid", status="active",
            assumptions=["asm-1"],
        )
        d2 = StrategicDecision(decision_id="sd-2", title="Healthy", status="active")
        reg = MockDecisionRegistry([d1, d2])
        at = MockAssumptionTracking([asm1])
        engine = DecisionValidityEngine(decision_registry=reg, assumption_tracking=at)
        s = engine.summary()
        assert s["total_evaluated"] == 2
        assert s["invalid_count"] == 1

    def test_summary_recommendations(self) -> None:
        asm1 = AssumptionRecord(assumption_id="asm-1", status="invalidated")
        d = StrategicDecision(
            decision_id="sd-1", title="Invalid", status="active",
            assumptions=["asm-1"],
        )
        reg = MockDecisionRegistry([d])
        at = MockAssumptionTracking([asm1])
        engine = DecisionValidityEngine(decision_registry=reg, assumption_tracking=at)
        s = engine.summary()
        recs = s["recommendations"]
        assert len(recs) >= 1
        assert recs[0]["decision_id"] == "sd-1"
        assert recs[0]["recommendation"] == "invalidate"

    def test_summary_no_recommendations_for_maintain(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Healthy", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        ga = MockGoalAlignment(score=0.9)
        ot = MockOutcomeTracking({"g-1": 0.5})
        engine = DecisionValidityEngine(
            decision_registry=reg, goal_alignment=ga, outcome_tracking=ot,
        )
        s = engine.summary()
        assert s["recommendations"] == []

    def test_generated_at_set(self) -> None:
        d = StrategicDecision(decision_id="sd-1", title="Test", status="active")
        reg = MockDecisionRegistry([d])
        engine = DecisionValidityEngine(decision_registry=reg)
        before = time.time()
        result = engine.evaluate("sd-1")
        assert result.generated_at >= before

    def test_classify_two_risks_gives_watch(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        ga = MockGoalAlignment(score=0.5)  # drifted → 1 risk
        ot = MockOutcomeTracking({"g-1": 0.0})  # near-zero → 2nd risk
        engine = DecisionValidityEngine(
            decision_registry=reg, goal_alignment=ga, outcome_tracking=ot,
        )
        result = engine.evaluate("sd-1")
        assert result.validity == "watch"
        assert result.recommendation == "monitor"

    def test_classify_single_risk_gives_watch(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        ga = MockGoalAlignment(score=0.9)  # aligned
        ot = MockOutcomeTracking({"g-1": 0.0})  # near-zero progress → 1 risk
        engine = DecisionValidityEngine(
            decision_registry=reg, goal_alignment=ga, outcome_tracking=ot,
        )
        result = engine.evaluate("sd-1")
        assert result.validity == "watch"
        assert result.recommendation == "monitor"

    def test_classify_no_risks_valid(self) -> None:
        d = StrategicDecision(
            decision_id="sd-1", title="Test", status="active",
            goal_refs=["g-1"],
        )
        reg = MockDecisionRegistry([d])
        ga = MockGoalAlignment(score=0.9)
        ot = MockOutcomeTracking({"g-1": 0.5})  # progress > 0.1
        engine = DecisionValidityEngine(
            decision_registry=reg, goal_alignment=ga, outcome_tracking=ot,
        )
        result = engine.evaluate("sd-1")
        assert result.validity == "valid"
        assert result.recommendation == "maintain"
