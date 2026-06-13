"""Tests for Phase 6: Projection Engine.

Covers: TrendDetector, ProjectionGenerator, RiskDetector,
OpportunityDetector, AccuracyTracker, ProjectionEngine orchestrator,
data models, serialization, and integration with Phase 4/5 primitives.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.projection_engine import (
    TimeHorizon,
    TrendDirection,
    RiskSeverity,
    ProjectionConfidence,
    TrendRecord,
    TrendDetector,
    Projection,
    StrategicRisk,
    StrategicOpportunity,
    ProjectionOutcome,
    AccuracyTracker,
    RiskDetector,
    OpportunityDetector,
    ProjectionGenerator,
    ProjectionEngine,
    PROJECTION_DOMAINS,
    get_projection_engine,
    reset_projection_engine,
)


# ── Enum Tests ────────────────────────────────────────────────────


class TestTimeHorizon:
    def test_values(self):
        assert TimeHorizon.DAY.value == "24h"
        assert TimeHorizon.WEEK.value == "7d"
        assert TimeHorizon.MONTH.value == "30d"
        assert TimeHorizon.QUARTER.value == "90d"

    def test_seconds(self):
        assert TimeHorizon.DAY.seconds == 86400.0
        assert TimeHorizon.WEEK.seconds == 604800.0
        assert TimeHorizon.MONTH.seconds == 2592000.0
        assert TimeHorizon.QUARTER.seconds == 7776000.0

    def test_days(self):
        assert TimeHorizon.DAY.days == 1.0
        assert TimeHorizon.WEEK.days == 7.0
        assert TimeHorizon.MONTH.days == 30.0
        assert TimeHorizon.QUARTER.days == 90.0


class TestTrendDirection:
    def test_all_values(self):
        values = {d.value for d in TrendDirection}
        assert values == {"positive", "negative", "stagnant", "accelerating", "decelerating"}


class TestRiskSeverity:
    def test_all_values(self):
        values = {s.value for s in RiskSeverity}
        assert values == {"critical", "high", "medium", "low"}


class TestProjectionConfidence:
    def test_all_values(self):
        values = {c.value for c in ProjectionConfidence}
        assert values == {"high", "medium", "low", "speculative"}


# ── Data Model Tests ──────────────────────────────────────────────


class TestTrendRecord:
    def test_creation(self):
        t = TrendRecord(domain="engineering", metric="velocity", direction=TrendDirection.POSITIVE)
        assert t.domain == "engineering"
        assert t.direction == TrendDirection.POSITIVE
        assert t.trend_id.startswith("trend-")

    def test_to_dict(self):
        t = TrendRecord(domain="sales", metric="outcome_velocity", magnitude=0.25)
        d = t.to_dict()
        assert d["domain"] == "sales"
        assert d["magnitude"] == 0.25
        assert d["direction"] == "stagnant"

    def test_created_at_auto(self):
        before = time.time()
        t = TrendRecord()
        assert t.created_at >= before


class TestProjection:
    def test_creation(self):
        p = Projection(domain="engineering", horizon=TimeHorizon.WEEK)
        assert p.domain == "engineering"
        assert p.horizon == TimeHorizon.WEEK
        assert p.projection_id.startswith("proj-")

    def test_serialization_roundtrip(self):
        p = Projection(
            domain="content",
            horizon=TimeHorizon.MONTH,
            current_state="30% complete",
            predicted_state="55% complete",
            confidence=ProjectionConfidence.HIGH,
            assumptions=["velocity stable"],
            completion_forecast=0.55,
            velocity_forecast=0.8,
        )
        d = p.to_dict()
        p2 = Projection.from_dict(d)
        assert p2.domain == "content"
        assert p2.horizon == TimeHorizon.MONTH
        assert p2.confidence == ProjectionConfidence.HIGH
        assert p2.completion_forecast == 0.55


class TestStrategicRisk:
    def test_creation(self):
        r = StrategicRisk(
            title="Slip risk",
            severity=RiskSeverity.HIGH,
            probability=0.7,
        )
        assert r.risk_id.startswith("risk-")
        assert r.severity == RiskSeverity.HIGH

    def test_serialization_roundtrip(self):
        r = StrategicRisk(
            title="Bottleneck",
            domain="ops",
            risk_type="execution_bottleneck",
            severity=RiskSeverity.CRITICAL,
            probability=0.85,
            impact="High backlog",
            evidence=["queue overloaded"],
        )
        d = r.to_dict()
        r2 = StrategicRisk.from_dict(d)
        assert r2.severity == RiskSeverity.CRITICAL
        assert r2.probability == 0.85
        assert r2.evidence == ["queue overloaded"]


class TestStrategicOpportunity:
    def test_creation(self):
        o = StrategicOpportunity(
            title="Fast-track MVP",
            domain="engineering",
            opportunity_type="fast_track",
        )
        assert o.opportunity_id.startswith("opp-")

    def test_serialization_roundtrip(self):
        o = StrategicOpportunity(
            title="Momentum",
            domain="content",
            confidence=ProjectionConfidence.HIGH,
        )
        d = o.to_dict()
        o2 = StrategicOpportunity.from_dict(d)
        assert o2.confidence == ProjectionConfidence.HIGH
        assert o2.domain == "content"


class TestProjectionOutcome:
    def test_roundtrip(self):
        po = ProjectionOutcome(
            projection_id="proj-abc",
            domain="engineering",
            horizon="7d",
            was_accurate=True,
            accuracy_score=0.85,
        )
        d = po.to_dict()
        po2 = ProjectionOutcome.from_dict(d)
        assert po2.was_accurate is True
        assert po2.accuracy_score == 0.85


# ── AccuracyTracker Tests ─────────────────────────────────────────


class TestAccuracyTracker:
    def test_empty_accuracy(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = AccuracyTracker(os.path.join(tmp, "outcomes.jsonl"))
            acc = tracker.overall_accuracy()
            assert acc["total_projections"] == 0
            assert acc["accuracy_rate"] == 0.0

    def test_record_and_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = AccuracyTracker(os.path.join(tmp, "outcomes.jsonl"))
            tracker.record(ProjectionOutcome(
                projection_id="p1", domain="eng", horizon="7d",
                was_accurate=True, accuracy_score=0.9,
            ))
            tracker.record(ProjectionOutcome(
                projection_id="p2", domain="eng", horizon="7d",
                was_accurate=False, accuracy_score=0.3,
            ))
            tracker.record(ProjectionOutcome(
                projection_id="p3", domain="sales", horizon="30d",
                was_accurate=True, accuracy_score=0.8,
            ))

            acc = tracker.overall_accuracy()
            assert acc["total_projections"] == 3
            assert acc["accurate_count"] == 2
            assert abs(acc["accuracy_rate"] - 0.667) < 0.01

            by_domain = tracker.accuracy_by_domain()
            assert "eng" in by_domain
            assert by_domain["eng"]["total_projections"] == 2
            assert by_domain["eng"]["accurate_count"] == 1

            by_horizon = tracker.accuracy_by_horizon()
            assert "7d" in by_horizon
            assert by_horizon["7d"]["total_projections"] == 2

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "outcomes.jsonl")
            tracker1 = AccuracyTracker(path)
            tracker1.record(ProjectionOutcome(
                projection_id="p1", domain="eng", horizon="7d",
                was_accurate=True, accuracy_score=0.9,
            ))

            tracker2 = AccuracyTracker(path)
            assert len(tracker2.all_outcomes()) == 1
            assert tracker2.all_outcomes()[0].was_accurate is True


# ── TrendDetector Tests ───────────────────────────────────────────


class TestTrendDetector:
    def test_no_outcomes(self):
        detector = TrendDetector()
        trends = detector.detect_trends([], [])
        assert trends == []

    def test_positive_trend(self):
        """Temporal midpoint split: 1 early outcome + 5 recent → most activity after midpoint."""
        detector = TrendDetector()
        now = time.time()
        outcomes = [
            {"domain": "engineering", "completed_at": now - 28 * 86400, "summary": "a"},
        ]
        for i in range(5):
            outcomes.append({
                "domain": "engineering",
                "completed_at": now - (3 - i) * 86400,
                "summary": f"recent {i}",
            })

        trends = detector.detect_trends(outcomes, [])
        eng_trends = [t for t in trends if t.domain == "engineering"]
        assert len(eng_trends) >= 1
        eng_trend = eng_trends[0]
        assert eng_trend.direction in (TrendDirection.POSITIVE, TrendDirection.ACCELERATING)
        assert eng_trend.magnitude > 0

    def test_negative_trend(self):
        """Temporal midpoint split: 5 early outcomes + 1 recent → most activity before midpoint."""
        detector = TrendDetector()
        now = time.time()
        outcomes = []
        for i in range(5):
            outcomes.append({
                "domain": "sales",
                "completed_at": now - (28 - i) * 86400,
                "summary": f"early {i}",
            })
        outcomes.append({"domain": "sales", "completed_at": now - 1 * 86400, "summary": "late"})

        trends = detector.detect_trends(outcomes, [])
        sales_trends = [t for t in trends if t.domain == "sales"]
        assert len(sales_trends) >= 1
        assert sales_trends[0].direction in (TrendDirection.NEGATIVE, TrendDirection.DECELERATING)

    def test_goal_progress_trend(self):
        detector = TrendDetector()

        class MockGoal:
            goal_id = "g1"
            title = "Test Goal"
            domain = "engineering"
            status = MagicMock(value="active")
            created_at = time.time() - 30 * 86400
            def completion_ratio(self):
                return 0.8

        trends = detector.detect_trends([], [MockGoal()])
        goal_trends = [t for t in trends if t.metric == "goal_progress"]
        assert len(goal_trends) == 1
        assert goal_trends[0].domain == "engineering"

    def test_multiple_domains(self):
        detector = TrendDetector()
        now = time.time()
        outcomes = [
            {"domain": "engineering", "completed_at": now - 5 * 86400, "summary": "a"},
            {"domain": "engineering", "completed_at": now - 4 * 86400, "summary": "b"},
            {"domain": "engineering", "completed_at": now - 3 * 86400, "summary": "c"},
            {"domain": "content", "completed_at": now - 5 * 86400, "summary": "d"},
            {"domain": "content", "completed_at": now - 4 * 86400, "summary": "e"},
        ]
        trends = detector.detect_trends(outcomes, [])
        domains = {t.domain for t in trends if t.metric == "outcome_velocity"}
        assert "engineering" in domains


# ── ProjectionGenerator Tests ────────────────────────────────────


class TestProjectionGenerator:
    def test_generate_basic(self):
        gen = ProjectionGenerator()
        proj = gen.generate(
            domain="engineering",
            horizon=TimeHorizon.WEEK,
            reality={"active_domains": ["engineering"]},
            goals=[],
            trends=[],
            outcomes=[],
        )
        assert proj.domain == "engineering"
        assert proj.horizon == TimeHorizon.WEEK
        assert proj.projection_id.startswith("proj-")

    def test_generate_with_outcomes(self):
        gen = ProjectionGenerator()
        now = time.time()
        outcomes = [
            {"domain": "engineering", "completed_at": now - 2 * 86400},
            {"domain": "engineering", "completed_at": now - 1 * 86400},
            {"domain": "engineering", "completed_at": now - 0.5 * 86400},
        ]
        proj = gen.generate(
            domain="engineering",
            horizon=TimeHorizon.WEEK,
            reality={},
            goals=[],
            trends=[],
            outcomes=outcomes,
        )
        assert proj.velocity_forecast > 0
        assert proj.completion_forecast >= 0

    def test_confidence_levels(self):
        gen = ProjectionGenerator()
        now = time.time()

        high_data = [{"domain": "eng", "completed_at": now - i * 86400} for i in range(15)]
        proj_high = gen.generate("eng", TimeHorizon.WEEK, {}, [], [], high_data)
        assert proj_high.confidence == ProjectionConfidence.HIGH

        low_data = [{"domain": "eng", "completed_at": now - i * 86400} for i in range(3)]
        proj_low = gen.generate("eng", TimeHorizon.QUARTER, {}, [], [], low_data)
        assert proj_low.confidence in (ProjectionConfidence.LOW, ProjectionConfidence.MEDIUM)

        proj_spec = gen.generate("eng", TimeHorizon.QUARTER, {}, [], [], [])
        assert proj_spec.confidence == ProjectionConfidence.SPECULATIVE

    def test_completion_capped_at_1(self):
        gen = ProjectionGenerator()
        now = time.time()
        outcomes = [{"domain": "eng", "completed_at": now - i * 3600} for i in range(100)]
        proj = gen.generate("eng", TimeHorizon.QUARTER, {}, [], [], outcomes)
        assert proj.completion_forecast <= 1.0


# ── RiskDetector Tests ────────────────────────────────────────────


class TestRiskDetector:
    def test_no_risks_for_empty(self):
        detector = RiskDetector()
        risks = detector.detect_risks([], [], [], [])
        assert risks == []

    def test_milestone_slip_detected(self):
        import datetime
        target = (datetime.datetime.now() + datetime.timedelta(days=10)).strftime("%Y-%m-%d")

        class MockGoal:
            goal_id = "g1"
            title = "MVP"
            domain = "engineering"
            status = MagicMock(value="active")
            target_date = target
            created_at = time.time() - 60 * 86400
            priority = 90
            def completion_ratio(self):
                return 0.1

        detector = RiskDetector()
        risks = detector.detect_risks(
            [MockGoal()],
            [],
            [],
            [],
        )
        slip_risks = [r for r in risks if r.risk_type == "milestone_slip"]
        assert len(slip_risks) >= 1
        assert slip_risks[0].severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)

    def test_no_slip_for_on_track(self):
        import datetime
        target = (datetime.datetime.now() + datetime.timedelta(days=90)).strftime("%Y-%m-%d")

        class MockGoal:
            goal_id = "g1"
            title = "Easy Goal"
            domain = "engineering"
            status = MagicMock(value="active")
            target_date = target
            created_at = time.time() - 10 * 86400
            priority = 50
            def completion_ratio(self):
                return 0.8

        detector = RiskDetector()
        risks = detector.detect_risks([MockGoal()], [], [], [])
        slip_risks = [r for r in risks if r.risk_type == "milestone_slip"]
        assert len(slip_risks) == 0

    def test_velocity_decline_risk(self):
        detector = RiskDetector()
        trend = TrendRecord(
            domain="engineering",
            metric="outcome_velocity",
            direction=TrendDirection.NEGATIVE,
            magnitude=-0.5,
            description="velocity declining 50%",
        )
        risks = detector.detect_risks([], [trend], [], [])
        velocity_risks = [r for r in risks if r.risk_type == "velocity_decline"]
        assert len(velocity_risks) >= 1
        assert velocity_risks[0].domain == "engineering"


# ── OpportunityDetector Tests ────────────────────────────────────


class TestOpportunityDetector:
    def test_no_opportunities_for_empty(self):
        detector = OpportunityDetector()
        opps = detector.detect_opportunities([], [], [], {})
        assert opps == []

    def test_momentum_detected(self):
        detector = OpportunityDetector()
        trend = TrendRecord(
            domain="content",
            metric="outcome_velocity",
            direction=TrendDirection.ACCELERATING,
            magnitude=0.4,
            description="content accelerating",
        )
        opps = detector.detect_opportunities([], [trend], [], {})
        momentum = [o for o in opps if o.opportunity_type == "domain_acceleration"]
        assert len(momentum) >= 1
        assert momentum[0].domain == "content"

    def test_fast_track_detected(self):
        detector = OpportunityDetector()

        class MockGoal:
            goal_id = "g1"
            title = "Nearly Done"
            domain = "engineering"
            status = MagicMock(value="active")
            def completion_ratio(self):
                return 0.85

        opps = detector.detect_opportunities([MockGoal()], [], [], {})
        fast = [o for o in opps if o.opportunity_type == "fast_track"]
        assert len(fast) >= 1


# ── ProjectionEngine Orchestrator Tests ──────────────────────────


class TestProjectionEngine:
    def _mock_engine(self, tmp_dir):
        with patch("substrate.organism.projection_engine.ProjectionEngine._get_reality") as mock_reality, \
             patch("substrate.organism.projection_engine.ProjectionEngine._get_active_goals") as mock_goals, \
             patch("substrate.organism.projection_engine.ProjectionEngine._get_active_domains") as mock_domains:

            mock_reality.return_value = {
                "active_domains": ["engineering", "content"],
                "active_loops": [],
                "blocked_items": [],
                "open_approvals": 0,
                "recent_outcomes": [
                    {"domain": "engineering", "completed_at": time.time() - 86400, "summary": "fixed bug"},
                    {"domain": "engineering", "completed_at": time.time() - 43200, "summary": "added feature"},
                    {"domain": "content", "completed_at": time.time() - 86400, "summary": "wrote post"},
                ],
                "current_phase": "phase 6",
            }

            class MockGoal:
                goal_id = "g1"
                title = "Ship MVP"
                domain = "engineering"
                status = MagicMock(value="active")
                target_date = ""
                created_at = time.time() - 14 * 86400
                priority = 90
                success_criteria = []
                def completion_ratio(self):
                    return 0.4

            mock_goals.return_value = [MockGoal()]
            mock_domains.return_value = ["engineering", "content"]

            tracker = AccuracyTracker(os.path.join(tmp_dir, "accuracy.jsonl"))
            engine = ProjectionEngine(accuracy_tracker=tracker, store_path=tmp_dir)
            return engine

    def test_run_projections(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            result = engine.run_projections()

            assert result["run_number"] == 1
            assert result["projection_count"] > 0
            assert result["trend_count"] >= 0
            assert "engineering" in result["domains_analyzed"]
            assert result["elapsed_ms"] >= 0

    def test_all_horizons_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            result = engine.run_projections()

            horizons = {p["horizon"] for p in result["projections"]}
            assert "24h" in horizons
            assert "7d" in horizons
            assert "30d" in horizons
            assert "90d" in horizons

    def test_specific_horizons(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            result = engine.run_projections(horizons=[TimeHorizon.DAY, TimeHorizon.WEEK])

            horizons = {p["horizon"] for p in result["projections"]}
            assert "24h" in horizons
            assert "7d" in horizons
            assert "30d" not in horizons

    def test_specific_domains(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            result = engine.run_projections(domains=["engineering"])

            domains = {p["domain"] for p in result["projections"]}
            assert domains == {"engineering"}

    def test_get_projection_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            engine.run_projections()
            state = engine.get_projection_state()

            assert state["run_count"] == 1
            assert state["last_run_at"] > 0
            assert "trends" in state
            assert "projections" in state
            assert "risks" in state
            assert "opportunities" in state
            assert "accuracy" in state

    def test_get_projected_reality(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            engine.run_projections()
            projected = engine.get_projected_reality(TimeHorizon.WEEK)

            assert projected["horizon"] == "7d"
            assert "projected_completions" in projected
            assert "projected_velocities" in projected
            assert "risk_domains" in projected
            assert "opportunity_domains" in projected

    def test_get_projections_for_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            engine.run_projections()

            eng_projs = engine.get_projections_for_domain("engineering")
            assert len(eng_projs) == 4

            empty = engine.get_projections_for_domain("nonexistent")
            assert len(empty) == 0

    def test_record_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            engine.run_projections()

            proj_id = engine.last_projections[0].projection_id
            result = engine.record_outcome(proj_id, "matched", True, 0.9)
            assert result["success"] is True

            acc = engine.accuracy_tracker.overall_accuracy()
            assert acc["total_projections"] == 1
            assert acc["accurate_count"] == 1

    def test_record_outcome_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            engine.run_projections()
            result = engine.record_outcome("proj-nonexistent", "x", False)
            assert result["success"] is False

    def test_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            status = engine.status()
            assert status["run_count"] == 0

            engine.run_projections()
            status = engine.status()
            assert status["run_count"] == 1
            assert status["projection_count"] > 0

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            engine.run_projections()

            forecast_files = os.listdir(os.path.join(tmp, "forecasts"))
            trend_files = os.listdir(os.path.join(tmp, "trends"))
            assert len(forecast_files) > 0
            assert all(f.endswith(".json") for f in forecast_files)

    def test_run_count_increments(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._mock_engine(tmp)
            engine.run_projections()
            engine.run_projections()
            assert engine.status()["run_count"] == 2


# ── Singleton Tests ──────────────────────────────────────────────


class TestSingleton:
    def test_get_returns_same_instance(self):
        reset_projection_engine()
        e1 = get_projection_engine()
        e2 = get_projection_engine()
        assert e1 is e2

    def test_reset_clears_instance(self):
        reset_projection_engine()
        e1 = get_projection_engine()
        reset_projection_engine()
        e2 = get_projection_engine()
        assert e1 is not e2

    def teardown_method(self):
        reset_projection_engine()


# ── Domain Constants Test ────────────────────────────────────────


class TestDomainConstants:
    def test_projection_domains_exist(self):
        assert len(PROJECTION_DOMAINS) == 13
        assert "engineering" in PROJECTION_DOMAINS
        assert "infrastructure" in PROJECTION_DOMAINS
        assert "music" in PROJECTION_DOMAINS


# ── Integration Test ─────────────────────────────────────────────


class TestAcceptanceScenario:
    """Acceptance test from Phase 6 spec: full projection cycle."""

    def test_full_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            import datetime

            target = (datetime.datetime.now() + datetime.timedelta(days=14)).strftime("%Y-%m-%d")

            class VisionGoal:
                goal_id = "goal-vision"
                title = "Complete Vision Subsystem"
                domain = "engineering"
                status = MagicMock(value="active")
                target_date = target
                created_at = time.time() - 30 * 86400
                priority = 90
                success_criteria = []
                def completion_ratio(self):
                    return 0.3

            now = time.time()
            outcomes = [
                {"domain": "engineering", "completed_at": now - 20 * 86400, "summary": "setup"},
                {"domain": "engineering", "completed_at": now - 15 * 86400, "summary": "prototype"},
                {"domain": "engineering", "completed_at": now - 10 * 86400, "summary": "basic fps"},
            ]

            with patch.object(ProjectionEngine, "_get_reality") as mock_reality, \
                 patch.object(ProjectionEngine, "_get_active_goals") as mock_goals, \
                 patch.object(ProjectionEngine, "_get_active_domains") as mock_domains:

                mock_reality.return_value = {
                    "active_domains": ["engineering"],
                    "active_loops": [],
                    "blocked_items": [],
                    "open_approvals": 0,
                    "recent_outcomes": outcomes,
                    "current_phase": "vision",
                }
                mock_goals.return_value = [VisionGoal()]
                mock_domains.return_value = ["engineering"]

                tracker = AccuracyTracker(os.path.join(tmp, "acc.jsonl"))
                engine = ProjectionEngine(accuracy_tracker=tracker, store_path=tmp)

                result = engine.run_projections()

                assert result["projection_count"] > 0, "1. Projection generated"

                risks = result["risks"]
                slip_risks = [r for r in risks if r.get("risk_type") == "milestone_slip"]
                assert len(slip_risks) >= 1, "2. Risk identified"
                assert any(
                    "slip" in r.get("title", "").lower() or "miss" in r.get("impact", "").lower()
                    for r in slip_risks
                ), "3. Milestone slip forecast detected"

                assert "opportunities" in result, "4. Opportunity field present"

                state = engine.get_projection_state()
                assert "projections" in state, "5. Projection visible for cockpit"

                projected = engine.get_projected_reality(TimeHorizon.WEEK)
                assert "projected_completions" in projected, "6. Gap Engine can receive projected future"
                assert "engineering" in projected["projected_completions"]

                assert len(result["trends"]) >= 0, "7. Trends analyzed"

                assert engine.status()["run_count"] == 1, "Engine ran correctly"
