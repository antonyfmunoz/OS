"""Strategic Gap Engine — Phase 4 acceptance tests.

Tests the full pipeline: goals → reality analysis → gap detection →
priority scoring → recommendations → WorkPacket generation → learning loop.
"""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

from substrate.organism.strategic_gap_engine import (
    DecisionRecord,
    Gap,
    GapDetector,
    GapSeverity,
    Goal,
    GoalRegistry,
    GoalStatus,
    GoalType,
    Recommendation,
    RecommendationEngine,
    RecommendationStatus,
    StrategicGapEngine,
    SuccessCriterion,
    score_gap,
)


@pytest.fixture()
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture()
def goal_registry(tmp_dir):
    return GoalRegistry(store_path=os.path.join(tmp_dir, "goals.jsonl"))


@pytest.fixture()
def engine(tmp_dir):
    reg = GoalRegistry(store_path=os.path.join(tmp_dir, "goals.jsonl"))
    return StrategicGapEngine(goal_registry=reg, store_path=tmp_dir)


# ── Goal Registry ─────────────────────────────────────────────────


class TestGoalRegistry:
    def test_add_and_get(self, goal_registry):
        goal = Goal(title="Ship MVP", domain="engineering", priority=90)
        goal_registry.add(goal)
        retrieved = goal_registry.get(goal.goal_id)
        assert retrieved is not None
        assert retrieved.title == "Ship MVP"

    def test_active_goals(self, goal_registry):
        goal_registry.add(Goal(title="Active", status=GoalStatus.ACTIVE))
        goal_registry.add(Goal(title="Paused", status=GoalStatus.PAUSED))
        goal_registry.add(Goal(title="Completed", status=GoalStatus.COMPLETED))
        assert len(goal_registry.active_goals()) == 1

    def test_goals_by_domain(self, goal_registry):
        goal_registry.add(Goal(title="Eng1", domain="engineering"))
        goal_registry.add(Goal(title="Sales1", domain="sales"))
        assert len(goal_registry.goals_by_domain("engineering")) == 1

    def test_goals_by_type(self, goal_registry):
        goal_registry.add(Goal(title="G1", goal_type=GoalType.PROJECT))
        goal_registry.add(Goal(title="G2", goal_type=GoalType.MILESTONE))
        goal_registry.add(Goal(title="G3", goal_type=GoalType.PROJECT))
        assert len(goal_registry.goals_by_type(GoalType.PROJECT)) == 2

    def test_update_goal(self, goal_registry):
        goal = Goal(title="Original")
        goal_registry.add(goal)
        goal.title = "Updated"
        goal_registry.update(goal)
        assert goal_registry.get(goal.goal_id).title == "Updated"

    def test_remove_goal(self, goal_registry):
        goal = Goal(title="Deletable")
        goal_registry.add(goal)
        assert goal_registry.remove(goal.goal_id)
        assert goal_registry.get(goal.goal_id) is None

    def test_children_of(self, goal_registry):
        parent = Goal(title="Parent")
        child1 = Goal(title="Child1", parent_goal_id=parent.goal_id)
        child2 = Goal(title="Child2", parent_goal_id=parent.goal_id)
        child3 = Goal(title="Other", parent_goal_id="different")
        for g in [parent, child1, child2, child3]:
            goal_registry.add(g)
        assert len(goal_registry.children_of(parent.goal_id)) == 2

    def test_persistence(self, tmp_dir):
        path = os.path.join(tmp_dir, "goals.jsonl")
        reg1 = GoalRegistry(store_path=path)
        reg1.add(Goal(title="Persisted", domain="engineering"))
        reg2 = GoalRegistry(store_path=path)
        assert len(reg2.all_goals()) == 1
        assert reg2.all_goals()[0].title == "Persisted"

    def test_completion_ratio(self):
        goal = Goal(
            title="Test",
            success_criteria=[
                SuccessCriterion(description="A", met=True),
                SuccessCriterion(description="B", met=False),
                SuccessCriterion(description="C", met=True),
                SuccessCriterion(description="D", met=False),
            ],
        )
        assert goal.completion_ratio() == 0.5


# ── Goal Serialization ────────────────────────────────────────────


class TestGoalSerialization:
    def test_roundtrip(self):
        goal = Goal(
            title="MVP",
            description="Ship it",
            goal_type=GoalType.PROJECT,
            status=GoalStatus.ACTIVE,
            domain="engineering",
            priority=80,
            success_criteria=[
                SuccessCriterion(description="Tests pass", target_value="100%", met=False),
            ],
            required_capabilities=["voice", "vision"],
            required_milestones=["Runtime complete"],
        )
        d = goal.to_dict()
        restored = Goal.from_dict(d)
        assert restored.title == "MVP"
        assert restored.goal_type == GoalType.PROJECT
        assert len(restored.success_criteria) == 1
        assert restored.required_capabilities == ["voice", "vision"]

    def test_gap_roundtrip(self):
        gap = Gap(
            title="Missing voice",
            severity=GapSeverity.HIGH,
            domain="engineering",
            current_state="absent",
            required_state="operational",
        )
        d = gap.to_dict()
        restored = Gap.from_dict(d)
        assert restored.severity == GapSeverity.HIGH
        assert restored.domain == "engineering"

    def test_recommendation_roundtrip(self):
        rec = Recommendation(
            title="Build voice",
            status=RecommendationStatus.PENDING,
            suggested_domain="engineering",
            priority_score=72.5,
        )
        d = rec.to_dict()
        restored = Recommendation.from_dict(d)
        assert restored.status == RecommendationStatus.PENDING
        assert restored.priority_score == 72.5


# ── Gap Detection ─────────────────────────────────────────────────


class TestGapDetector:
    def test_unmet_criteria(self):
        goal = Goal(
            title="MVP",
            domain="engineering",
            success_criteria=[
                SuccessCriterion(description="Tests pass", met=True),
                SuccessCriterion(description="Deployed", met=False, target_value="production"),
            ],
        )
        detector = GapDetector()
        gaps = detector.detect_gaps(goal, {"active_domains": [], "blocked_items": [], "recent_outcomes": []})
        assert len(gaps) == 1
        assert "Deployed" in gaps[0].title
        assert gaps[0].gap_type == "unmet_criterion"

    def test_missing_capability(self):
        goal = Goal(
            title="Voice MVP",
            domain="engineering",
            required_capabilities=["wake_phrase", "voice_transport"],
        )
        reality = {"active_domains": ["vision"], "blocked_items": [], "recent_outcomes": []}
        detector = GapDetector()
        gaps = detector.detect_gaps(goal, reality)
        assert len(gaps) == 2
        assert all(g.gap_type == "missing_capability" for g in gaps)

    def test_missing_milestone(self):
        goal = Goal(
            title="Launch",
            domain="engineering",
            required_milestones=["Runtime complete", "UI deployed"],
        )
        packets = [
            {"title": "runtime complete", "status": "completed"},
            {"title": "API setup", "status": "completed"},
        ]
        detector = GapDetector()
        gaps = detector.detect_gaps(goal, {"active_domains": [], "blocked_items": [], "recent_outcomes": []}, packets)
        assert len(gaps) == 1
        assert "UI deployed" in gaps[0].title

    def test_blocker_detection(self):
        goal = Goal(title="Ship", domain="engineering")
        reality = {
            "active_domains": ["engineering"],
            "blocked_items": [
                {"domain": "engineering", "packet_id": "wp-123", "status_reason": "test failure"},
            ],
            "recent_outcomes": [],
        }
        detector = GapDetector()
        gaps = detector.detect_gaps(goal, reality)
        assert len(gaps) == 1
        assert gaps[0].gap_type == "blocker"

    def test_dependency_gaps(self):
        goal = Goal(title="Phase 5", domain="engineering", dependencies=["phase-4", "phase-3"])
        detector = GapDetector()
        gaps = detector.detect_gaps(goal, {"active_domains": [], "blocked_items": [], "recent_outcomes": []})
        assert len(gaps) == 2
        assert all(g.gap_type == "dependency" for g in gaps)

    def test_no_gaps_when_complete(self):
        goal = Goal(
            title="Done",
            domain="engineering",
            success_criteria=[
                SuccessCriterion(description="A", met=True),
                SuccessCriterion(description="B", met=True),
            ],
        )
        detector = GapDetector()
        gaps = detector.detect_gaps(goal, {"active_domains": [], "blocked_items": [], "recent_outcomes": []})
        assert len(gaps) == 0


# ── Priority Scoring ──────────────────────────────────────────────


class TestPriorityScoring:
    def test_critical_scores_higher(self):
        gap_crit = Gap(title="Critical", severity=GapSeverity.CRITICAL, domain="engineering")
        gap_low = Gap(title="Low", severity=GapSeverity.LOW, domain="engineering")
        goal = Goal(title="Test", priority=50)
        score_c = score_gap(gap_crit, goal, [gap_crit, gap_low])
        score_l = score_gap(gap_low, goal, [gap_crit, gap_low])
        assert score_c > score_l

    def test_blocking_goals_boost_score(self):
        gap_blocks = Gap(title="Blocker", severity=GapSeverity.MEDIUM, blocking_goals=["g1", "g2", "g3"])
        gap_none = Gap(title="No block", severity=GapSeverity.MEDIUM)
        goal = Goal(title="Test", priority=50)
        assert score_gap(gap_blocks, goal, []) > score_gap(gap_none, goal, [])

    def test_high_priority_goal_boosts_score(self):
        gap = Gap(title="Test", severity=GapSeverity.MEDIUM)
        goal_high = Goal(title="Important", priority=95)
        goal_low = Goal(title="Minor", priority=10)
        assert score_gap(gap, goal_high, []) > score_gap(gap, goal_low, [])

    def test_score_range(self):
        gap = Gap(title="Test", severity=GapSeverity.MEDIUM)
        goal = Goal(title="Test", priority=50)
        score = score_gap(gap, goal, [])
        assert 0 <= score <= 100


# ── Recommendation Engine ─────────────────────────────────────────


class TestRecommendationEngine:
    def test_generates_from_gaps(self):
        gaps = [
            Gap(title="Missing voice", severity=GapSeverity.HIGH, domain="engineering", priority_score=75.0, goal_id="g1"),
            Gap(title="No sales list", severity=GapSeverity.MEDIUM, domain="sales", priority_score=50.0, goal_id="g2"),
        ]
        goals = {
            "g1": Goal(goal_id="g1", title="Voice MVP", domain="engineering"),
            "g2": Goal(goal_id="g2", title="Revenue", domain="sales"),
        }
        engine = RecommendationEngine()
        recs = engine.generate(gaps, goals)
        assert len(recs) == 2
        assert recs[0].priority_score >= recs[1].priority_score
        assert recs[0].suggested_domain in ("engineering", "sales")

    def test_includes_agents(self):
        gap = Gap(title="Deploy", severity=GapSeverity.MEDIUM, domain="engineering", priority_score=60.0, goal_id="g1")
        goals = {"g1": Goal(goal_id="g1", title="Ship", domain="engineering")}
        engine = RecommendationEngine()
        recs = engine.generate([gap], goals)
        assert len(recs) == 1
        assert len(recs[0].suggested_agents) > 0

    def test_sorted_by_priority(self):
        gaps = [
            Gap(title="Low", severity=GapSeverity.LOW, priority_score=20.0, goal_id="g1"),
            Gap(title="High", severity=GapSeverity.CRITICAL, priority_score=90.0, goal_id="g1"),
            Gap(title="Mid", severity=GapSeverity.MEDIUM, priority_score=50.0, goal_id="g1"),
        ]
        goals = {"g1": Goal(goal_id="g1", title="Test")}
        engine = RecommendationEngine()
        recs = engine.generate(gaps, goals)
        scores = [r.priority_score for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_historical_boost(self):
        gap = Gap(title="Test", severity=GapSeverity.MEDIUM, domain="engineering", priority_score=50.0, goal_id="g1")
        goals = {"g1": Goal(goal_id="g1", title="Test", domain="engineering")}
        history = [
            DecisionRecord(goal_id="engineering-1", action="approved", was_effective=True),
            DecisionRecord(goal_id="engineering-2", action="approved", was_effective=True),
        ]
        engine = RecommendationEngine()
        recs_no_history = engine.generate([gap], goals, [])
        recs_with_history = engine.generate([gap], goals, history)
        assert recs_with_history[0].priority_score >= recs_no_history[0].priority_score


# ── Strategic Gap Engine (Full Pipeline) ──────────────────────────


class TestStrategicGapEngine:
    def test_analyze_empty(self, engine):
        result = engine.analyze()
        assert result["gap_count"] == 0
        assert result["recommendation_count"] == 0

    def test_analyze_with_goals(self, engine):
        engine.goal_registry.add(Goal(
            title="Ship UMH MVP",
            domain="engineering",
            priority=90,
            success_criteria=[
                SuccessCriterion(description="Operator runtime", met=True),
                SuccessCriterion(description="Vision subsystem", met=False, target_value="complete"),
            ],
            required_capabilities=["wake_phrase"],
        ))
        result = engine.analyze()
        assert result["gap_count"] >= 2
        assert result["recommendation_count"] >= 2

    def test_approve_generates_workpacket(self, engine):
        engine.goal_registry.add(Goal(
            title="Test",
            domain="engineering",
            success_criteria=[SuccessCriterion(description="Missing thing", met=False)],
        ))
        analysis = engine.analyze()
        recs = analysis["recommendations"]
        assert len(recs) > 0

        rec_id = recs[0]["recommendation_id"]
        result = engine.approve_recommendation(rec_id, "operator approved")
        assert result["success"]
        assert "routing" in result
        assert result["routing"]["domain"]

    def test_reject_records_decision(self, engine):
        engine.goal_registry.add(Goal(
            title="Test",
            domain="engineering",
            success_criteria=[SuccessCriterion(description="X", met=False)],
        ))
        engine.analyze()
        recs = engine.get_top_recommendations()
        result = engine.reject_recommendation(recs[0].recommendation_id, "not now")
        assert result["success"]
        decisions = engine.get_decision_history()
        assert len(decisions) == 1
        assert decisions[0]["action"] == "rejected"

    def test_learning_loop(self, engine):
        engine.goal_registry.add(Goal(
            title="Test",
            domain="engineering",
            success_criteria=[SuccessCriterion(description="X", met=False)],
        ))
        engine.analyze()
        recs = engine.get_top_recommendations()
        engine.approve_recommendation(recs[0].recommendation_id)
        decisions = engine.get_decision_history()
        dec_id = decisions[0]["decision_id"]

        result = engine.record_outcome(dec_id, was_effective=True, summary="worked well")
        assert result["success"]

        updated = engine.get_decision_history()
        assert updated[0]["was_effective"] is True
        assert updated[0]["outcome_summary"] == "worked well"


# ── Acceptance Test ───────────────────────────────────────────────


class TestAcceptanceTest:
    def test_full_pipeline_ship_umh_mvp(self, engine):
        """Full acceptance scenario: Ship UMH MVP.

        Goal state:
          - Operator runtime: complete
          - WorkPacket Engine: complete
          - Vision subsystem: incomplete
          - Wake phrase: missing
          - Session routing: partial

        Expected:
          1. Gap Engine identifies missing components
          2. Produces ranked gaps
          3. Produces recommendations
          4. Generates candidate WorkPacket via approval
          5. Routes through existing governance
          6. Persists decision (learning loop)
          7. Records outcome for future learning
        """

        goal = Goal(
            title="Ship UMH MVP",
            description="Complete UMH minimum viable product",
            goal_type=GoalType.PROJECT,
            domain="engineering",
            priority=95,
            success_criteria=[
                SuccessCriterion(description="Operator runtime complete", met=True),
                SuccessCriterion(description="WorkPacket Engine complete", met=True),
                SuccessCriterion(
                    description="Vision subsystem complete",
                    met=False,
                    current_value="partial",
                    target_value="complete",
                ),
                SuccessCriterion(
                    description="Wake phrase operational",
                    met=False,
                    current_value="absent",
                    target_value="operational",
                ),
                SuccessCriterion(
                    description="Session routing complete",
                    met=False,
                    current_value="partial",
                    target_value="complete",
                ),
            ],
            required_capabilities=["wake_phrase", "session_activation"],
            required_milestones=["Runtime MVP", "Vision Alpha"],
        )
        engine.goal_registry.add(goal)

        # ── Step 1: Run analysis ──
        analysis = engine.analyze()
        assert analysis["gap_count"] >= 3, f"Expected >= 3 gaps, got {analysis['gap_count']}"

        # ── Step 2: Verify ranked gaps ──
        gaps = analysis["gaps"]
        scores = [g["priority_score"] for g in gaps]
        assert scores == sorted(scores, reverse=True), "Gaps not sorted by priority"

        # ── Step 3: Verify recommendations ──
        recs = analysis["recommendations"]
        assert len(recs) >= 3, f"Expected >= 3 recommendations, got {len(recs)}"
        for rec in recs:
            assert rec["suggested_domain"], "Recommendation missing domain"
            assert rec["impact_estimate"], "Recommendation missing impact"
            assert rec["risk_estimate"], "Recommendation missing risk"

        # ── Step 4: Approve top recommendation → WorkPacket ──
        top_rec_id = recs[0]["recommendation_id"]
        approve_result = engine.approve_recommendation(top_rec_id, "highest leverage gap")
        assert approve_result["success"], f"Approval failed: {approve_result}"
        assert "routing" in approve_result
        routing = approve_result["routing"]
        assert routing["domain"], "Routing missing domain"
        assert routing["objective"], "Routing missing objective"

        # ── Step 5: Verify governance flow ──
        assert "routing_id" in routing
        if routing.get("work_packets"):
            for wp in routing["work_packets"]:
                assert "packet_id" in wp

        # ── Step 6: Verify decision persisted ──
        decisions = engine.get_decision_history()
        assert len(decisions) >= 1
        dec = decisions[0]
        assert dec["action"] == "approved"
        assert dec["reason"] == "highest leverage gap"

        # ── Step 7: Record outcome (learning loop) ──
        outcome = engine.record_outcome(
            dec["decision_id"],
            was_effective=True,
            summary="Gap addressed, vision subsystem progressed",
        )
        assert outcome["success"]

        updated_decisions = engine.get_decision_history()
        assert updated_decisions[0]["was_effective"] is True
        assert "vision" in updated_decisions[0]["outcome_summary"]

        print("\n" + "=" * 60)
        print("  ACCEPTANCE TEST: PASSED")
        print("=" * 60)
        print(f"\n  Goal:             {goal.title}")
        print(f"  Gaps detected:    {analysis['gap_count']}")
        print(f"  Recommendations:  {len(recs)}")
        print(f"  Top rec:          {recs[0]['title']}")
        print(f"  Approved → Domain: {routing['domain']}")
        print(f"  Decision recorded: {dec['decision_id']}")
        print(f"  Outcome:          effective\n")
