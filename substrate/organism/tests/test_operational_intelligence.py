"""Tests for Phase 7.0 Operational Intelligence engines."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from substrate.organism.bottleneck_engine import (
    Bottleneck,
    BottleneckCategory,
    BottleneckEngine,
    BottleneckEvidence,
    BottleneckSeverity,
    BottleneckThresholds,
)
from substrate.organism.leverage_engine import LeverageEngine, LeverageOpportunity
from substrate.organism.next_action_engine import ActionPriority, NextActionEngine
from substrate.organism.readiness_model import DIMENSION_WEIGHTS, ReadinessModel


class TestBottleneckEngine:
    def test_empty_detect(self) -> None:
        engine = BottleneckEngine()
        result = engine.detect()
        assert result == []
        assert engine.active == []

    def test_high_failure_rate_detection(self) -> None:
        engine = BottleneckEngine()
        result = engine.detect(leverage_inputs={"failure_rate": 0.5})
        assert len(result) == 1
        bn = result[0]
        assert bn.category == BottleneckCategory.HIGH_FAILURE_RATE
        assert bn.severity == BottleneckSeverity.HIGH
        assert bn.bottleneck_id.startswith("bn-")
        assert bn.confidence > 0.7
        assert len(bn.evidence) == 1
        assert bn.evidence[0].signal == "failure_rate"
        assert bn.recommendation != ""

    def test_approval_backlog_detection(self) -> None:
        engine = BottleneckEngine()
        result = engine.detect(pending_approvals=30)
        assert any(b.category == BottleneckCategory.APPROVAL_BACKLOG for b in result)

    def test_governance_block_detection(self) -> None:
        engine = BottleneckEngine()
        result = engine.detect(governance_state={"total_submitted": 10, "total_blocked": 8})
        assert any(b.category == BottleneckCategory.GOVERNANCE_BLOCK for b in result)

    def test_recurrence_escalation(self) -> None:
        engine = BottleneckEngine()
        for _ in range(6):
            result = engine.detect(leverage_inputs={"failure_rate": 0.5})
        assert result[0].severity == BottleneckSeverity.CRITICAL
        assert result[0].recurrence_count > 5

    def test_bottleneck_to_dict(self) -> None:
        bn = Bottleneck(
            category=BottleneckCategory.HIGH_FAILURE_RATE,
            severity=BottleneckSeverity.HIGH,
            source="test",
            description="test bottleneck",
            confidence=0.85,
            evidence=[BottleneckEvidence("test_signal", "50%", "<20%")],
            recommendation="fix it",
        )
        d = bn.to_dict()
        assert "bottleneck_id" in d
        assert d["confidence"] == 0.85
        assert len(d["evidence"]) == 1
        assert d["recommendation"] == "fix it"

    def test_slow_runtime_detection(self) -> None:
        engine = BottleneckEngine()
        result = engine.detect(runtime_stats=[
            {"runtime_id": "test-rt", "avg_latency_ms": 10000}
        ])
        assert len(result) == 1
        assert result[0].category == BottleneckCategory.SLOW_RUNTIME

    def test_queue_buildup(self) -> None:
        engine = BottleneckEngine()
        result = engine.detect(queue_depth=100)
        assert any(b.category == BottleneckCategory.QUEUE_BUILDUP for b in result)


class TestLeverageEngine:
    def test_empty_compute(self) -> None:
        engine = LeverageEngine()
        result = engine.compute()
        assert result == []

    def test_bottleneck_to_opportunity(self) -> None:
        engine = LeverageEngine()
        bottlenecks = [{
            "category": "high_failure_rate",
            "severity": "high",
            "description": "Task failure rate exceeds threshold",
            "recommendation": "Investigate failing tasks",
            "confidence": 0.9,
            "recurrence_count": 3,
            "evidence": [{"signal": "failure_rate", "observed": "50%", "expected": "<20%"}],
            "source": "leverage_metrics",
            "metric_value": 0.5,
            "threshold": 0.2,
        }]
        result = engine.compute(bottlenecks=bottlenecks)
        assert len(result) >= 1
        opp = result[0]
        assert opp.impact_score > 0
        assert opp.confidence > 0
        assert len(opp.evidence) > 0
        assert opp.reasoning != ""

    def test_pending_approvals_opportunity(self) -> None:
        engine = LeverageEngine()
        result = engine.compute(pending_approvals=5)
        assert len(result) == 1
        assert "approval" in result[0].action.lower()
        assert result[0].confidence == 1.0

    def test_ranking_order(self) -> None:
        engine = LeverageEngine()
        bottlenecks = [
            {"category": "high_failure_rate", "severity": "critical", "recommendation": "Fix critical", "confidence": 1.0, "recurrence_count": 1, "evidence": [], "source": "test", "description": "critical"},
            {"category": "unused_runtime", "severity": "low", "recommendation": "Remove idle", "confidence": 0.8, "recurrence_count": 1, "evidence": [], "source": "test", "description": "low"},
        ]
        result = engine.compute(bottlenecks=bottlenecks, pending_approvals=3)
        scores = [o.impact_score for o in result]
        assert scores == sorted(scores, reverse=True)

    def test_mode_promotion_opportunity(self) -> None:
        engine = LeverageEngine()
        result = engine.compute(execution_mode={"current_mode": "assisted", "reliability": 0.92})
        assert any("promote" in o.action.lower() or "autonomous" in o.action.lower() for o in result)

    def test_to_dict(self) -> None:
        engine = LeverageEngine()
        engine.compute(pending_approvals=3)
        d = engine.to_dict()
        assert "total_opportunities" in d
        assert d["total_opportunities"] == 1
        assert len(d["top_opportunities"]) == 1


class TestNextActionEngine:
    def test_empty_compute(self) -> None:
        engine = NextActionEngine()
        result = engine.compute()
        assert result == []

    def test_from_leverage_opportunities(self) -> None:
        engine = NextActionEngine()
        opportunities = [{
            "action": "Fix failure rate",
            "impact_score": 0.85,
            "confidence": 0.9,
            "category": "bottleneck:high_failure_rate",
            "impact_description": "Reduce task failures",
            "reasoning": "High failure rate blocks throughput",
            "evidence": [{"source": "bottleneck_engine", "signal": "failure_rate", "detail": "50%"}],
        }]
        result = engine.compute(leverage_opportunities=opportunities)
        assert len(result) >= 1
        act = result[0]
        assert act.action == "Fix failure rate"
        assert act.priority in (ActionPriority.CRITICAL, ActionPriority.HIGH)
        assert len(act.evidence) > 0

    def test_pending_approvals_action(self) -> None:
        engine = NextActionEngine()
        result = engine.compute(pending_approvals=10)
        assert len(result) == 1
        assert result[0].category.value == "approve"

    def test_readiness_gaps_action(self) -> None:
        engine = NextActionEngine()
        gaps = [{"dimension": "deployment", "score": 30, "explanation": "DNS not configured", "gap_factors": ["dns_routing"]}]
        result = engine.compute(readiness_gaps=gaps)
        assert len(result) == 1
        assert "deployment" in result[0].action.lower()

    def test_deduplication(self) -> None:
        engine = NextActionEngine()
        opportunities = [
            {"action": "Fix A", "impact_score": 0.8, "confidence": 0.9, "category": "bottleneck:failure", "evidence": [], "reasoning": ""},
            {"action": "Fix B", "impact_score": 0.7, "confidence": 0.8, "category": "bottleneck:failure", "evidence": [], "reasoning": ""},
        ]
        result = engine.compute(leverage_opportunities=opportunities)
        assert len(result) == 1

    def test_to_dict(self) -> None:
        engine = NextActionEngine()
        engine.compute(pending_approvals=5)
        d = engine.to_dict()
        assert d["total_actions"] == 1
        assert len(d["actions"]) == 1


class TestReadinessModel:
    def test_empty_compute(self) -> None:
        model = ReadinessModel()
        report = model.compute()
        assert report.composite_score >= 0
        assert len(report.dimensions) == 6
        assert report.overall_status in ("operational", "degraded", "limited", "critical")

    def test_weights_sum_to_one(self) -> None:
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_dimensions_present(self) -> None:
        model = ReadinessModel()
        report = model.compute()
        dim_names = {d.dimension for d in report.dimensions}
        assert dim_names == {"execution", "governance", "deployment", "operator", "memory", "composition"}

    def test_high_readiness(self) -> None:
        model = ReadinessModel()
        report = model.compute(
            execution_state={"success_rate": 0.95, "registered_mutations": 22, "current_mode": "autonomous", "pending_count": 0, "active_count": 3},
            governance_state={"guard_active": True, "gateway_active": True, "total_submitted": 100, "total_blocked": 20, "total_violations": 0, "journal_active": True},
            deployment_state={"services_up": 3, "services_total": 3, "build_current": True, "dns_correct": True, "tls_valid": True, "api_responsive": True},
            operator_state={"pending_approvals": 0, "intervention_rate": 0.05, "operator_compression": {"total_patterns": 15}},
            memory_state={"total_observations": 100, "total_skills": 30, "total_memories": 50, "journal_entries": 200},
            composition_state={"runtimes_available": 8, "runtimes_total": 8, "agents_registered": 5, "event_spine_active": True, "tick_running": True, "connected_subsystems": 10},
        )
        assert report.composite_score >= 70
        assert report.overall_status in ("operational", "degraded")

    def test_low_readiness(self) -> None:
        model = ReadinessModel()
        report = model.compute(
            execution_state={"success_rate": 0.0, "current_mode": "manual"},
            governance_state={},
            deployment_state={},
            operator_state={},
            memory_state={},
            composition_state={},
        )
        assert report.composite_score < 50

    def test_gaps(self) -> None:
        model = ReadinessModel()
        report = model.compute()
        gaps = report.gaps(threshold=60)
        assert isinstance(gaps, list)

    def test_to_dict_structure(self) -> None:
        model = ReadinessModel()
        report = model.compute()
        d = report.to_dict()
        assert "composite_score" in d
        assert "dimensions" in d
        assert "weight_documentation" in d
        assert d["weight_documentation"] == DIMENSION_WEIGHTS

    def test_explanation_present(self) -> None:
        model = ReadinessModel()
        report = model.compute()
        for dim in report.dimensions:
            assert dim.explanation != ""


class TestIntegration:
    def test_full_pipeline(self) -> None:
        bottleneck_engine = BottleneckEngine()
        leverage_engine = LeverageEngine()
        next_action_engine = NextActionEngine()
        readiness_model = ReadinessModel()

        bottlenecks = bottleneck_engine.detect(
            leverage_inputs={"failure_rate": 0.4},
            pending_approvals=5,
        )
        assert len(bottlenecks) >= 1

        bottleneck_data = [b.to_dict() for b in bottlenecks]
        opportunities = leverage_engine.compute(
            bottlenecks=bottleneck_data,
            pending_approvals=5,
        )
        assert len(opportunities) >= 1

        readiness = readiness_model.compute(
            execution_state={"success_rate": 0.6, "current_mode": "assisted"},
            governance_state={"guard_active": True, "gateway_active": True, "journal_active": True},
        )

        actions = next_action_engine.compute(
            leverage_opportunities=[o.to_dict() for o in opportunities],
            pending_approvals=5,
            readiness_gaps=readiness.gaps(threshold=60),
        )
        assert len(actions) >= 1

        for action in actions:
            d = action.to_dict()
            assert d["action"] != ""
            assert d["reason"] != ""
            assert d["priority"] in ("critical", "high", "medium", "low")
            assert len(d["evidence"]) >= 0

    def test_event_emission(self) -> None:
        from substrate.organism.event_spine import EventSpine
        spine = EventSpine(max_events=100)

        bottleneck_engine = BottleneckEngine(event_spine=spine)
        leverage_engine = LeverageEngine(event_spine=spine)
        next_action_engine = NextActionEngine(event_spine=spine)
        readiness_model = ReadinessModel(event_spine=spine)

        bottleneck_engine.detect(leverage_inputs={"failure_rate": 0.5})
        leverage_engine.compute(pending_approvals=3)
        next_action_engine.compute(pending_approvals=3)
        readiness_model.compute(execution_state={"success_rate": 0.5})

        events = spine.recent(limit=20)
        event_types = {e.event_type for e in events}
        assert "bottleneck_detected" in event_types
        assert "leverage_changed" in event_types
        assert "next_action_changed" in event_types


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
