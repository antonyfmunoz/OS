"""Tests for Phase 5: Strategic Tick Loop.

Tests the autonomous tick loop, change detection, candidate queue,
drift detection, profile-aware prioritization, and recommendation lifecycle.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.strategic_tick_loop import (
    TickFrequency,
    RecommendationLifecycle,
    DriftSeverity,
    RealityDelta,
    ChangeDetector,
    CandidateWorkItem,
    CandidateWorkQueue,
    DriftWarning,
    DriftDetector,
    TickRecord,
    StrategicTickLoop,
    apply_profile_weighting,
    _snapshot_hash,
    get_tick_loop,
    reset_tick_loop,
)


# ── TickFrequency ────────────────────────────────────────────────────


class TestTickFrequency:
    def test_frequency_seconds(self):
        assert TickFrequency.FAST.seconds == 30.0
        assert TickFrequency.NORMAL.seconds == 60.0
        assert TickFrequency.RELAXED.seconds == 300.0
        assert TickFrequency.SLOW.seconds == 900.0
        assert TickFrequency.MANUAL.seconds == 0.0

    def test_frequency_values(self):
        assert TickFrequency.FAST.value == "30s"
        assert TickFrequency.NORMAL.value == "1m"


# ── ChangeDetector ───────────────────────────────────────────────────


class TestChangeDetector:
    def test_first_snapshot_always_changed(self):
        detector = ChangeDetector()
        snapshot = {"active_domains": ["engineering"], "recent_outcomes": [], "open_approvals": 0,
                    "active_loops": [], "blocked_items": []}
        delta = detector.detect(snapshot)
        assert delta.has_meaningful_change is True
        assert delta.previous_hash == ""

    def test_identical_snapshot_no_change(self):
        detector = ChangeDetector()
        snapshot = {"active_domains": [], "recent_outcomes": [], "open_approvals": 0,
                    "active_loops": [], "blocked_items": []}
        detector.detect(snapshot)
        delta = detector.detect(snapshot)
        assert delta.has_meaningful_change is False

    def test_new_outcome_detected(self):
        detector = ChangeDetector()
        s1 = {"active_domains": [], "recent_outcomes": [], "open_approvals": 0,
              "active_loops": [], "blocked_items": []}
        detector.detect(s1)

        s2 = dict(s1)
        s2["recent_outcomes"] = [{"packet_id": "pk-1", "summary": "deployed"}]
        delta = detector.detect(s2)
        assert delta.has_meaningful_change is True
        assert len(delta.new_outcomes) == 1

    def test_new_failure_detected(self):
        detector = ChangeDetector()
        s1 = {"active_domains": [], "recent_outcomes": [], "open_approvals": 0,
              "active_loops": [], "blocked_items": []}
        detector.detect(s1)

        s2 = dict(s1)
        s2["recent_outcomes"] = [{"packet_id": "pk-2", "summary": "build failed with error"}]
        delta = detector.detect(s2)
        assert delta.has_meaningful_change is True
        assert len(delta.new_failures) == 1
        assert len(delta.new_outcomes) == 0

    def test_new_approval_detected(self):
        detector = ChangeDetector()
        s1 = {"active_domains": [], "recent_outcomes": [], "open_approvals": 0,
              "active_loops": [], "blocked_items": []}
        detector.detect(s1)

        s2 = dict(s1)
        s2["open_approvals"] = 3
        delta = detector.detect(s2)
        assert delta.has_meaningful_change is True
        assert delta.new_approvals == 3

    def test_domain_change_detected(self):
        detector = ChangeDetector()
        s1 = {"active_domains": ["engineering"], "recent_outcomes": [], "open_approvals": 0,
              "active_loops": [], "blocked_items": []}
        detector.detect(s1)

        s2 = dict(s1)
        s2["active_domains"] = ["engineering", "music"]
        delta = detector.detect(s2)
        assert delta.has_meaningful_change is True
        assert "music" in delta.domain_changes

    def test_goal_change_detected(self):
        detector = ChangeDetector()
        s1 = {"active_domains": [], "recent_outcomes": [], "open_approvals": 0,
              "active_loops": [], "blocked_items": []}
        detector.detect(s1, {"goal-1"})

        delta = detector.detect(s1, {"goal-1", "goal-2"})
        assert delta.has_meaningful_change is True
        assert "goal-2" in delta.goal_changes

    def test_new_packet_detected(self):
        detector = ChangeDetector()
        s1 = {"active_domains": [], "recent_outcomes": [], "open_approvals": 0,
              "active_loops": [], "blocked_items": []}
        detector.detect(s1)

        s2 = dict(s1)
        s2["active_loops"] = [{"packet_id": "wp-new", "title": "Fix auth"}]
        delta = detector.detect(s2)
        assert delta.has_meaningful_change is True
        assert len(delta.new_packets) == 1


class TestSnapshotHash:
    def test_deterministic(self):
        s = {"a": 1, "b": [2, 3]}
        assert _snapshot_hash(s) == _snapshot_hash(s)

    def test_different_snapshots_different_hash(self):
        s1 = {"a": 1}
        s2 = {"a": 2}
        assert _snapshot_hash(s1) != _snapshot_hash(s2)


# ── CandidateWorkQueue ───────────────────────────────────────────────


class TestCandidateWorkQueue:
    def test_add_and_retrieve(self, tmp_path):
        q = CandidateWorkQueue(str(tmp_path / "queue.jsonl"))
        item = CandidateWorkItem(title="Fix auth", domain="engineering", priority_score=85.0)
        q.add(item)
        assert q.get(item.candidate_id) is not None
        assert q.get(item.candidate_id).title == "Fix auth"

    def test_pending_sorted_by_priority(self, tmp_path):
        q = CandidateWorkQueue(str(tmp_path / "queue.jsonl"))
        q.add(CandidateWorkItem(title="Low", priority_score=20.0))
        q.add(CandidateWorkItem(title="High", priority_score=90.0))
        q.add(CandidateWorkItem(title="Med", priority_score=50.0))
        pending = q.pending()
        assert len(pending) == 3
        assert pending[0].title == "High"
        assert pending[1].title == "Med"
        assert pending[2].title == "Low"

    def test_lifecycle_update(self, tmp_path):
        q = CandidateWorkQueue(str(tmp_path / "queue.jsonl"))
        item = CandidateWorkItem(title="Test", priority_score=50.0)
        q.add(item)
        assert q.update_lifecycle(item.candidate_id, RecommendationLifecycle.ACCEPTED)
        assert q.get(item.candidate_id).lifecycle == RecommendationLifecycle.ACCEPTED
        assert len(q.pending()) == 0

    def test_expire_old(self, tmp_path):
        q = CandidateWorkQueue(str(tmp_path / "queue.jsonl"))
        item = CandidateWorkItem(title="Old", priority_score=50.0)
        item.proposed_at = time.time() - 86400 * 4  # 4 days old
        q.add(item)
        expired = q.expire_old(max_age_hours=72.0)
        assert expired == 1
        assert q.get(item.candidate_id).lifecycle == RecommendationLifecycle.EXPIRED

    def test_populate_from_recommendations(self, tmp_path):
        q = CandidateWorkQueue(str(tmp_path / "queue.jsonl"))
        recs = [
            {"recommendation_id": "rec-1", "title": "Fix A", "suggested_domain": "eng", "priority_score": 80.0},
            {"recommendation_id": "rec-2", "title": "Fix B", "suggested_domain": "ops", "priority_score": 60.0},
        ]
        added = q.populate_from_recommendations(recs)
        assert added == 2
        assert len(q.all_items()) == 2
        # dedup: same recs again
        added2 = q.populate_from_recommendations(recs)
        assert added2 == 0

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "queue.jsonl")
        q1 = CandidateWorkQueue(path)
        q1.add(CandidateWorkItem(title="Persisted", priority_score=70.0))
        q2 = CandidateWorkQueue(path)
        assert len(q2.all_items()) == 1
        assert q2.all_items()[0].title == "Persisted"

    def test_by_domain(self, tmp_path):
        q = CandidateWorkQueue(str(tmp_path / "queue.jsonl"))
        q.add(CandidateWorkItem(title="A", domain="eng"))
        q.add(CandidateWorkItem(title="B", domain="music"))
        q.add(CandidateWorkItem(title="C", domain="eng"))
        assert len(q.by_domain("eng")) == 2
        assert len(q.by_domain("music")) == 1


# ── CandidateWorkItem Serialization ─────────────────────────────────


class TestCandidateWorkItemSerialization:
    def test_roundtrip(self):
        item = CandidateWorkItem(
            title="Test", domain="eng", priority_score=75.0,
            impact="high", risk="low", dependencies=["dep-1"],
            lifecycle=RecommendationLifecycle.REVIEWED,
        )
        d = item.to_dict()
        restored = CandidateWorkItem.from_dict(d)
        assert restored.title == item.title
        assert restored.domain == item.domain
        assert restored.lifecycle == RecommendationLifecycle.REVIEWED
        assert restored.dependencies == ["dep-1"]


# ── DriftDetector ────────────────────────────────────────────────────


class MockGoal:
    def __init__(self, goal_id, title, domain, status_val="active",
                 updated_at=None, criteria_met=0, criteria_total=0):
        self.goal_id = goal_id
        self.title = title
        self.domain = domain
        self.status = type("S", (), {"value": status_val})()
        self.updated_at = updated_at or time.time()
        self._met = criteria_met
        self._total = criteria_total

    def completion_ratio(self):
        if self._total == 0:
            return 0.0
        return self._met / self._total


class TestDriftDetector:
    def test_no_drift_recent_activity(self):
        d = DriftDetector()
        goals = [MockGoal("g1", "Ship MVP", "engineering", updated_at=time.time())]
        warnings = d.detect_drift(goals, [])
        assert len(warnings) == 0

    def test_warning_after_7_days(self):
        d = DriftDetector()
        goals = [MockGoal("g1", "Vision", "engineering",
                          updated_at=time.time() - 86400 * 10)]
        warnings = d.detect_drift(goals, [])
        assert len(warnings) == 1
        assert warnings[0].severity == DriftSeverity.WARNING

    def test_alert_after_14_days(self):
        d = DriftDetector()
        goals = [MockGoal("g1", "Vision", "engineering",
                          updated_at=time.time() - 86400 * 20)]
        warnings = d.detect_drift(goals, [])
        assert len(warnings) == 1
        assert warnings[0].severity == DriftSeverity.ALERT

    def test_critical_after_30_days(self):
        d = DriftDetector()
        goals = [MockGoal("g1", "Vision", "engineering",
                          updated_at=time.time() - 86400 * 35)]
        warnings = d.detect_drift(goals, [])
        assert len(warnings) == 1
        assert warnings[0].severity == DriftSeverity.CRITICAL

    def test_skips_paused_goals(self):
        d = DriftDetector()
        goals = [MockGoal("g1", "Paused", "engineering", status_val="paused",
                          updated_at=time.time() - 86400 * 60)]
        warnings = d.detect_drift(goals, [])
        assert len(warnings) == 0

    def test_recent_outcome_prevents_drift(self):
        d = DriftDetector()
        goals = [MockGoal("g1", "Vision", "engineering",
                          updated_at=time.time() - 86400 * 20)]
        outcomes = [{"domain": "engineering", "completed_at": time.time()}]
        warnings = d.detect_drift(goals, outcomes)
        assert len(warnings) == 0

    def test_sorted_by_stagnation(self):
        d = DriftDetector()
        goals = [
            MockGoal("g1", "Less stale", "eng", updated_at=time.time() - 86400 * 10),
            MockGoal("g2", "More stale", "ops", updated_at=time.time() - 86400 * 25),
        ]
        warnings = d.detect_drift(goals, [])
        assert len(warnings) == 2
        assert warnings[0].goal_title == "More stale"


class TestDriftWarningSerialization:
    def test_roundtrip(self):
        w = DriftWarning(goal_id="g1", goal_title="Test", severity=DriftSeverity.ALERT, days_stagnant=15.5)
        d = w.to_dict()
        restored = DriftWarning.from_dict(d)
        assert restored.goal_id == "g1"
        assert restored.severity == DriftSeverity.ALERT
        assert restored.days_stagnant == 15.5


# ── Profile Weighting ────────────────────────────────────────────────


class TestProfileWeighting:
    def test_no_profiles_no_change(self):
        recs = [{"title": "A", "priority_score": 80.0, "suggested_domain": "engineering"}]
        result = apply_profile_weighting(recs, [])
        assert result[0]["priority_score"] == 80.0

    def test_developer_boosts_engineering(self):
        recs = [
            {"title": "Eng", "priority_score": 50.0, "suggested_domain": "engineering"},
            {"title": "Music", "priority_score": 50.0, "suggested_domain": "music"},
        ]
        result = apply_profile_weighting(recs, ["developer"])
        eng = next(r for r in result if r["title"] == "Eng")
        music = next(r for r in result if r["title"] == "Music")
        assert eng["priority_score"] > music["priority_score"]
        assert eng["profile_boosted"] is True
        assert music["profile_boosted"] is False

    def test_music_profile_boosts_music(self):
        recs = [
            {"title": "Eng", "priority_score": 50.0, "suggested_domain": "engineering"},
            {"title": "Music", "priority_score": 50.0, "suggested_domain": "music"},
        ]
        result = apply_profile_weighting(recs, ["music"])
        music = next(r for r in result if r["title"] == "Music")
        assert music["profile_boosted"] is True

    def test_multiple_profiles_compound(self):
        recs = [
            {"title": "Eng", "priority_score": 50.0, "suggested_domain": "engineering"},
            {"title": "Music", "priority_score": 50.0, "suggested_domain": "music"},
        ]
        result = apply_profile_weighting(recs, ["developer", "music"])
        # Both should be boosted since both profiles match
        eng = next(r for r in result if r["title"] == "Eng")
        music = next(r for r in result if r["title"] == "Music")
        assert eng["profile_boosted"] is True
        assert music["profile_boosted"] is True

    def test_result_sorted_by_score(self):
        recs = [
            {"title": "A", "priority_score": 30.0, "suggested_domain": "engineering"},
            {"title": "B", "priority_score": 90.0, "suggested_domain": "music"},
            {"title": "C", "priority_score": 60.0, "suggested_domain": "research"},
        ]
        result = apply_profile_weighting(recs, ["developer"])
        scores = [r["priority_score"] for r in result]
        assert scores == sorted(scores, reverse=True)


# ── TickRecord ───────────────────────────────────────────────────────


class TestTickRecord:
    def test_serialization(self):
        record = TickRecord(
            cycle_number=5, change_detected=True, analysis_ran=True,
            gaps_found=3, recommendations_generated=2, candidates_added=1,
            drift_warnings=1, elapsed_ms=45.5,
        )
        d = record.to_dict()
        assert d["cycle_number"] == 5
        assert d["change_detected"] is True
        assert d["gaps_found"] == 3
        assert d["elapsed_ms"] == 45.5


# ── StrategicTickLoop ────────────────────────────────────────────────


class TestStrategicTickLoop:
    def test_initial_state(self, tmp_path):
        loop = StrategicTickLoop(candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")))
        assert loop.cycle_count == 0
        assert loop.is_running is False
        assert loop.is_paused is False
        assert loop.last_analysis is None

    def test_start_stop(self, tmp_path):
        loop = StrategicTickLoop(candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")))
        loop.start()
        assert loop.is_running is True
        loop.stop()
        assert loop.is_running is False

    def test_pause_resume(self, tmp_path):
        loop = StrategicTickLoop(candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")))
        loop.start()
        loop.pause()
        assert loop.is_paused is True
        record = loop.execute_tick()
        assert record.skipped_reason == "paused"
        loop.resume()
        assert loop.is_paused is False

    def test_frequency_setting(self, tmp_path):
        loop = StrategicTickLoop(
            frequency=TickFrequency.FAST,
            candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")),
        )
        assert loop.frequency == TickFrequency.FAST
        loop.frequency = TickFrequency.SLOW
        assert loop.frequency == TickFrequency.SLOW

    def test_set_profiles(self, tmp_path):
        loop = StrategicTickLoop(candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")))
        loop.set_active_profiles(["developer", "music"])
        status = loop.status()
        assert status["active_profiles"] == ["developer", "music"]

    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._get_reality")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._get_current_goal_ids")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._get_active_goals")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._run_analysis")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._check_operator_presence")
    def test_tick_with_change(self, mock_presence, mock_analysis, mock_goals,
                               mock_goal_ids, mock_reality, tmp_path):
        mock_reality.return_value = {
            "active_domains": ["engineering"],
            "recent_outcomes": [{"packet_id": "pk-1", "summary": "deployed"}],
            "open_approvals": 0,
            "active_loops": [],
            "blocked_items": [],
        }
        mock_goal_ids.return_value = {"goal-1"}
        mock_goals.return_value = []
        mock_analysis.return_value = {
            "gap_count": 2,
            "recommendation_count": 1,
            "recommendations": [
                {"recommendation_id": "rec-1", "title": "Fix auth",
                 "suggested_domain": "engineering", "priority_score": 80.0},
            ],
        }
        mock_presence.return_value = True

        loop = StrategicTickLoop(candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")))
        record = loop.execute_tick()

        assert record.change_detected is True
        assert record.analysis_ran is True
        assert record.gaps_found == 2
        assert record.recommendations_generated == 1
        assert record.candidates_added == 1
        assert record.operator_present is True

    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._get_reality")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._get_current_goal_ids")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._check_operator_presence")
    def test_tick_no_change_skips_analysis(self, mock_presence, mock_goal_ids, mock_reality, tmp_path):
        snapshot = {
            "active_domains": [], "recent_outcomes": [],
            "open_approvals": 0, "active_loops": [], "blocked_items": [],
        }
        mock_reality.return_value = snapshot
        mock_goal_ids.return_value = set()
        mock_presence.return_value = False

        loop = StrategicTickLoop(candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")))
        # First tick: always triggers (no previous snapshot)
        r1 = loop.execute_tick()
        # Second tick: same snapshot, should skip
        r2 = loop.execute_tick()
        assert r2.change_detected is False
        assert r2.analysis_ran is False
        assert r2.skipped_reason == "no_change"

    def test_status(self, tmp_path):
        loop = StrategicTickLoop(
            frequency=TickFrequency.RELAXED,
            candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")),
        )
        status = loop.status()
        assert status["running"] is False
        assert status["frequency"] == "5m"
        assert status["cycle_count"] == 0

    def test_strategic_state(self, tmp_path):
        loop = StrategicTickLoop(candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")))
        state = loop.get_strategic_state()
        assert "tick" in state
        assert "candidate_queue" in state
        assert "drift_warnings" in state
        assert state["tick"]["running"] is False

    def test_tick_history_bounded(self, tmp_path):
        loop = StrategicTickLoop(candidate_queue=CandidateWorkQueue(str(tmp_path / "q.jsonl")))
        for _ in range(110):
            loop._tick_history.append(TickRecord(cycle_number=loop._cycle_count))
            loop._cycle_count += 1
        loop._record_tick(TickRecord(cycle_number=111), time.monotonic_ns())
        assert len(loop.tick_history) <= 100


# ── Singleton ────────────────────────────────────────────────────────


class TestSingleton:
    def test_get_and_reset(self):
        reset_tick_loop()
        loop1 = get_tick_loop()
        loop2 = get_tick_loop()
        assert loop1 is loop2
        reset_tick_loop()
        loop3 = get_tick_loop()
        assert loop3 is not loop1


# ── Acceptance Test ──────────────────────────────────────────────────


class TestAcceptanceTest:
    """Full scenario: goals exist, reality changes, tick detects, analyzes,
    ranks, recommends, queues, detects drift — no automatic execution."""

    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._get_reality")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._get_current_goal_ids")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._get_active_goals")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._run_analysis")
    @patch("substrate.organism.strategic_tick_loop.StrategicTickLoop._check_operator_presence")
    def test_full_cycle(self, mock_presence, mock_analysis, mock_goals,
                         mock_goal_ids, mock_reality, tmp_path):
        """Acceptance test from spec:
        Goals: Ship UMH MVP, Complete Vision System
        Reality: Vision incomplete, wake phrase missing, session routing partial
        Expected: changes detected, gaps analyzed, priorities ranked,
        recommendations generated, candidates queued, drift evaluated,
        no automatic execution."""

        # Mock reality state
        mock_reality.return_value = {
            "active_domains": ["engineering", "operator"],
            "recent_outcomes": [
                {"packet_id": "pk-runtime", "summary": "operator runtime complete", "domain": "operator"},
            ],
            "open_approvals": 1,
            "active_loops": [
                {"packet_id": "wp-session", "title": "session routing", "domain": "engineering"},
            ],
            "blocked_items": [],
        }
        mock_goal_ids.return_value = {"goal-mvp", "goal-vision"}

        # Mock stale vision goal for drift detection
        vision_goal = MockGoal(
            "goal-vision", "Complete Vision System", "vision",
            updated_at=time.time() - 86400 * 16,  # 16 days stale → ALERT
            criteria_met=1, criteria_total=5,
        )
        mvp_goal = MockGoal(
            "goal-mvp", "Ship UMH MVP", "engineering",
            updated_at=time.time(),
            criteria_met=3, criteria_total=5,
        )
        mock_goals.return_value = [vision_goal, mvp_goal]

        # Mock analysis result
        mock_analysis.return_value = {
            "gap_count": 4,
            "recommendation_count": 3,
            "recommendations": [
                {"recommendation_id": "rec-wake", "title": "Implement wake phrase",
                 "suggested_domain": "vision", "priority_score": 85.0,
                 "impact_estimate": "high", "risk_estimate": "low", "dependency_chain": []},
                {"recommendation_id": "rec-session", "title": "Complete session routing",
                 "suggested_domain": "engineering", "priority_score": 70.0,
                 "impact_estimate": "medium", "risk_estimate": "low", "dependency_chain": []},
                {"recommendation_id": "rec-binary", "title": "Binary WebSocket frames",
                 "suggested_domain": "vision", "priority_score": 60.0,
                 "impact_estimate": "medium", "risk_estimate": "medium", "dependency_chain": ["rec-wake"]},
            ],
        }
        mock_presence.return_value = True

        # Execute
        queue = CandidateWorkQueue(str(tmp_path / "q.jsonl"))
        loop = StrategicTickLoop(
            frequency=TickFrequency.NORMAL,
            candidate_queue=queue,
        )
        loop.set_active_profiles(["developer"])

        # 1. Execute tick
        record = loop.execute_tick()

        # 2. Verify change detected
        assert record.change_detected is True

        # 3. Verify gap engine ran
        assert record.analysis_ran is True
        assert record.gaps_found == 4

        # 4. Verify priorities calculated
        assert record.recommendations_generated == 3

        # 5. Verify candidate queue populated
        assert record.candidates_added == 3
        pending = queue.pending()
        assert len(pending) == 3
        # Developer profile should boost engineering domains
        assert pending[0].priority_score > 0

        # 6. Verify drift evaluated
        assert record.drift_warnings == 1
        drift = loop.last_drift_warnings
        assert len(drift) == 1
        assert drift[0].goal_title == "Complete Vision System"
        assert drift[0].severity == DriftSeverity.ALERT

        # 7. Verify recommendations visible (via strategic state)
        state = loop.get_strategic_state()
        assert state["candidate_queue"]["pending"] == 3
        assert len(state["drift_warnings"]) == 1
        assert state["tick"]["cycle_count"] == 1
        assert state["active_profiles"] == ["developer"]
        assert state["operator_present"] is True

        # 8. Verify no automatic execution occurred
        # (The tick loop never calls approve/execute — only analyzes and queues)
        assert record.skipped_reason == ""

        # 9. Verify history recorded
        assert len(loop.tick_history) == 1
        assert loop.tick_history[0].tick_id == record.tick_id

        # 10. Verify second tick with same data skips analysis
        record2 = loop.execute_tick()
        assert record2.change_detected is False
        assert record2.analysis_ran is False
        assert record2.skipped_reason == "no_change"
