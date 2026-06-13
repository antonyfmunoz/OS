"""Tests for Phase 7: Continuity Runtime."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.continuity_runtime import (
    AttentionModel,
    AttentionState,
    BriefSection,
    ChangeCategory,
    ContinuityRuntime,
    ContinuitySnapshot,
    OperatorBrief,
    OperatorBriefGenerator,
    ResumeReport,
    ResumeStateEngine,
    SessionHandoff,
    SnapshotCollector,
    TimelineEngine,
    TimelineEvent,
    TimelineEventType,
    WorkContinuityGraph,
    WorkLineage,
    get_continuity_runtime,
    reset_continuity_runtime,
)


# ── Enum Tests ─────────────────────────────────────────────────────────


class TestAttentionState:
    def test_values(self):
        assert AttentionState.ACTIVE.value == "active"
        assert AttentionState.AWAY.value == "away"
        assert AttentionState.OFFLINE.value == "offline"
        assert AttentionState.SLEEPING.value == "sleeping"

    def test_is_present(self):
        assert AttentionState.ACTIVE.is_present is True
        assert AttentionState.AWAY.is_present is False
        assert AttentionState.OFFLINE.is_present is False

    def test_is_absent(self):
        assert AttentionState.ACTIVE.is_absent is False
        assert AttentionState.AWAY.is_absent is True
        assert AttentionState.OFFLINE.is_absent is True
        assert AttentionState.SLEEPING.is_absent is True


class TestTimelineEventType:
    def test_all_values(self):
        types = [e.value for e in TimelineEventType]
        assert "decision" in types
        assert "outcome" in types
        assert "learning" in types
        assert "approval" in types
        assert "execution" in types
        assert "session_start" in types
        assert "session_end" in types
        assert "attention_change" in types


class TestChangeCategory:
    def test_all_values(self):
        cats = [c.value for c in ChangeCategory]
        assert "completed" in cats
        assert "failed" in cats
        assert "blocked" in cats
        assert "available" in cats
        assert "needs_review" in cats


class TestBriefSection:
    def test_all_values(self):
        sections = [s.value for s in BriefSection]
        assert "mission_status" in sections
        assert "current_reality" in sections
        assert "critical_changes" in sections
        assert "pending_decisions" in sections
        assert "recommended_actions" in sections


# ── Data Model Tests ───────────────────────────────────────────────────


class TestContinuitySnapshot:
    def test_creation(self):
        snap = ContinuitySnapshot()
        assert snap.snapshot_id.startswith("snap-")
        assert snap.captured_at > 0
        assert snap.active_profile_mode == ""
        assert snap.active_objectives == []

    def test_serialization_roundtrip(self):
        snap = ContinuitySnapshot(
            active_profile_mode="developer",
            active_objectives=[{"id": "g1", "title": "Ship MVP"}],
            blocked_items=[{"id": "wp1", "title": "Blocked task"}],
            operator_attention="away",
        )
        d = snap.to_dict()
        restored = ContinuitySnapshot.from_dict(d)
        assert restored.active_profile_mode == "developer"
        assert len(restored.active_objectives) == 1
        assert restored.operator_attention == "away"

    def test_compute_hash(self):
        snap1 = ContinuitySnapshot(active_profile_mode="developer")
        snap2 = ContinuitySnapshot(active_profile_mode="research")
        assert snap1.compute_hash() != snap2.compute_hash()

    def test_same_data_same_hash(self):
        snap1 = ContinuitySnapshot(snapshot_id="x", captured_at=1000, active_profile_mode="dev")
        snap2 = ContinuitySnapshot(snapshot_id="x", captured_at=1000, active_profile_mode="dev")
        assert snap1.compute_hash() == snap2.compute_hash()


class TestTimelineEvent:
    def test_creation(self):
        event = TimelineEvent(event_type="decision", summary="Approved work packet")
        assert event.event_id.startswith("evt-")
        assert event.timestamp > 0
        assert event.event_type == "decision"

    def test_roundtrip(self):
        event = TimelineEvent(
            event_type="outcome",
            summary="Test passed",
            details={"count": 5},
            related_ids=["wp-1", "wp-2"],
        )
        d = event.to_dict()
        restored = TimelineEvent.from_dict(d)
        assert restored.event_type == "outcome"
        assert restored.details["count"] == 5
        assert len(restored.related_ids) == 2


class TestResumeReport:
    def test_creation(self):
        report = ResumeReport()
        assert report.generated_at > 0
        assert report.total_changes == 0
        assert report.has_critical_changes is False

    def test_total_changes(self):
        report = ResumeReport(
            completed=[{"id": "1"}],
            failed=[{"id": "2"}],
            blocked=[{"id": "3"}],
        )
        assert report.total_changes == 3

    def test_has_critical_changes(self):
        report = ResumeReport(failed=[{"id": "1"}])
        assert report.has_critical_changes is True

    def test_roundtrip(self):
        report = ResumeReport(
            absence_duration_seconds=3600,
            completed=[{"id": "1", "title": "Done"}],
            recommended_actions=["Review outcomes"],
        )
        d = report.to_dict()
        restored = ResumeReport.from_dict(d)
        assert restored.absence_duration_seconds == 3600
        assert len(restored.completed) == 1


class TestOperatorBrief:
    def test_creation(self):
        brief = OperatorBrief()
        assert brief.brief_id.startswith("brief-")
        assert brief.generated_at > 0

    def test_roundtrip(self):
        brief = OperatorBrief(
            mission_status="3 objectives, 2 active — progressing",
            critical_changes=["1 item failed"],
            active_objectives_count=3,
            risk_count=2,
        )
        d = brief.to_dict()
        restored = OperatorBrief.from_dict(d)
        assert restored.active_objectives_count == 3
        assert restored.risk_count == 2


class TestWorkLineage:
    def test_creation(self):
        lineage = WorkLineage(
            objective_id="g1",
            objective_title="Ship MVP",
            work_packet_ids=["wp1", "wp2"],
            outcome_ids=["out1"],
        )
        assert lineage.lineage_id.startswith("lin-")
        assert lineage.depth == 2

    def test_roundtrip(self):
        lineage = WorkLineage(
            objective_id="g1",
            objective_title="Ship MVP",
            work_packet_ids=["wp1"],
            recommendation_ids=["rec1"],
        )
        d = lineage.to_dict()
        restored = WorkLineage.from_dict(d)
        assert restored.objective_id == "g1"
        assert restored.work_packet_ids == ["wp1"]


class TestSessionHandoff:
    def test_creation(self):
        handoff = SessionHandoff(
            from_session_id="s1",
            to_session_id="s2",
            from_profile="developer",
            to_profile="research",
        )
        assert handoff.handoff_id.startswith("handoff-")
        assert handoff.timestamp > 0

    def test_roundtrip(self):
        handoff = SessionHandoff(
            from_session_id="s1",
            to_session_id="s2",
            context_items=["3 objectives", "2 work packets"],
        )
        d = handoff.to_dict()
        restored = SessionHandoff.from_dict(d)
        assert restored.from_session_id == "s1"
        assert len(restored.context_items) == 2


# ── Attention Model Tests ──────────────────────────────────────────────


class TestAttentionModel:
    def test_initial_state(self):
        model = AttentionModel()
        assert model.state == AttentionState.OFFLINE

    def test_record_interaction(self):
        model = AttentionModel()
        model.record_interaction()
        assert model.state == AttentionState.ACTIVE
        assert model.last_interaction > 0

    def test_transition_to_away(self):
        model = AttentionModel()
        model._away_threshold_seconds = 0.01
        model.record_interaction()
        model._last_interaction = time.time() - 1.0
        model.update_from_presence()
        assert model.state in (AttentionState.AWAY, AttentionState.OFFLINE)

    def test_to_dict(self):
        model = AttentionModel()
        model.record_interaction()
        d = model.to_dict()
        assert "state" in d
        assert d["state"] == "active"
        assert "last_interaction" in d
        assert "seconds_since_interaction" in d


# ── Timeline Engine Tests ──────────────────────────────────────────────


class TestTimelineEngine:
    def test_record_and_query(self):
        with tempfile.TemporaryDirectory() as td:
            engine = TimelineEngine(data_dir=td)
            engine.record_event("decision", "Approved work")
            engine.record_event("outcome", "Tests passed")
            events = engine.get_events()
            assert len(events) == 2

    def test_filter_by_type(self):
        with tempfile.TemporaryDirectory() as td:
            engine = TimelineEngine(data_dir=td)
            engine.record_event("decision", "Approved")
            engine.record_event("outcome", "Completed")
            engine.record_event("decision", "Rejected")
            decisions = engine.get_events(event_type="decision")
            assert len(decisions) == 2

    def test_filter_by_time(self):
        with tempfile.TemporaryDirectory() as td:
            engine = TimelineEngine(data_dir=td)
            e1 = engine.record_event("decision", "Old event")
            cutoff = time.time()
            e2 = engine.record_event("outcome", "New event")
            recent = engine.get_events(since=cutoff)
            assert len(recent) >= 1

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            engine1 = TimelineEngine(data_dir=td)
            engine1.record_event("decision", "Persisted event")

            engine2 = TimelineEngine(data_dir=td)
            events = engine2.get_events()
            assert len(events) == 1
            assert events[0].summary == "Persisted event"

    def test_events_between(self):
        with tempfile.TemporaryDirectory() as td:
            engine = TimelineEngine(data_dir=td)
            t1 = time.time()
            engine.record_event("decision", "First")
            t2 = time.time()
            engine.record_event("outcome", "Second")
            t3 = time.time()
            events = engine.get_events_between(t1, t3)
            assert len(events) == 2


# ── Resume State Engine Tests ──────────────────────────────────────────


class TestResumeStateEngine:
    def test_no_changes(self):
        engine = ResumeStateEngine()
        before = ContinuitySnapshot(captured_at=1000)
        after = ContinuitySnapshot(captured_at=2000)
        report = engine.generate_resume(before, after)
        assert report.total_changes == 0
        assert report.absence_duration_seconds == 1000

    def test_detect_completed(self):
        engine = ResumeStateEngine()
        before = ContinuitySnapshot(
            captured_at=1000,
            active_work_packets=[
                {"packet_id": "wp1", "title": "Task A", "domain": "engineering"},
                {"packet_id": "wp2", "title": "Task B", "domain": "sales"},
            ],
        )
        after = ContinuitySnapshot(
            captured_at=2000,
            active_work_packets=[
                {"packet_id": "wp2", "title": "Task B", "domain": "sales"},
            ],
        )
        report = engine.generate_resume(before, after)
        assert len(report.completed) == 1
        assert report.completed[0]["id"] == "wp1"

    def test_detect_failed(self):
        engine = ResumeStateEngine()
        before = ContinuitySnapshot(
            captured_at=1000,
            active_work_packets=[
                {"packet_id": "wp1", "title": "Task A", "status": "active"},
            ],
        )
        after = ContinuitySnapshot(
            captured_at=2000,
            active_work_packets=[
                {"packet_id": "wp1", "title": "Task A", "status": "failed"},
            ],
        )
        report = engine.generate_resume(before, after)
        assert len(report.failed) == 1

    def test_detect_newly_blocked(self):
        engine = ResumeStateEngine()
        before = ContinuitySnapshot(captured_at=1000, blocked_items=[])
        after = ContinuitySnapshot(
            captured_at=2000,
            blocked_items=[{"id": "wp3", "title": "Blocked", "reason": "needs auth"}],
        )
        report = engine.generate_resume(before, after)
        assert len(report.blocked) == 1
        assert report.blocked[0]["reason"] == "needs auth"

    def test_detect_became_available(self):
        engine = ResumeStateEngine()
        before = ContinuitySnapshot(
            captured_at=1000,
            blocked_items=[{"id": "wp3", "title": "Was blocked"}],
        )
        after = ContinuitySnapshot(captured_at=2000, blocked_items=[])
        report = engine.generate_resume(before, after)
        assert len(report.became_available) == 1
        assert report.became_available[0]["id"] == "wp3"

    def test_detect_needs_review(self):
        engine = ResumeStateEngine()
        before = ContinuitySnapshot(captured_at=1000, approvals_waiting=[])
        after = ContinuitySnapshot(
            captured_at=2000,
            approvals_waiting=[{"id": "a1", "title": "Approve deploy", "risk_level": "high"}],
        )
        report = engine.generate_resume(before, after)
        assert len(report.needs_review) >= 1

    def test_detect_new_risk(self):
        engine = ResumeStateEngine()
        before = ContinuitySnapshot(captured_at=1000, active_risks=[])
        after = ContinuitySnapshot(
            captured_at=2000,
            active_risks=[{"risk_id": "r1", "type": "milestone_slip", "severity": "high"}],
        )
        report = engine.generate_resume(before, after)
        risk_reviews = [r for r in report.needs_review if r["category"] == "new_risk"]
        assert len(risk_reviews) == 1

    def test_recommended_actions(self):
        engine = ResumeStateEngine()
        before = ContinuitySnapshot(captured_at=1000)
        after = ContinuitySnapshot(
            captured_at=2000,
            approvals_waiting=[{"id": "a1", "title": "Deploy"}],
            blocked_items=[{"id": "wp1", "title": "Blocked"}],
        )
        report = engine.generate_resume(before, after)
        assert len(report.recommended_actions) >= 2

    def test_profile_change_detected(self):
        engine = ResumeStateEngine()
        before = ContinuitySnapshot(captured_at=1000, active_profile_mode="developer")
        after = ContinuitySnapshot(captured_at=2000, active_profile_mode="research")
        report = engine.generate_resume(before, after)
        profile_changes = [c for c in report.changes if c["type"] == "profile_change"]
        assert len(profile_changes) == 1


# ── Work Continuity Graph Tests ────────────────────────────────────────


class TestWorkContinuityGraph:
    def test_build_lineage(self):
        graph = WorkContinuityGraph()
        lineages = graph.build_lineage(
            objectives=[{"goal_id": "g1", "title": "Ship MVP", "domain": "engineering"}],
            work_packets=[{"packet_id": "wp1", "domain": "engineering", "status": "active"}],
            outcomes=[{"outcome_id": "out1", "domain": "engineering"}],
            projections=[{"projection_id": "proj1", "domain": "engineering"}],
            recommendations=[{"recommendation_id": "rec1", "domain": "engineering"}],
        )
        assert len(lineages) == 1
        lin = lineages[0]
        assert lin.objective_id == "g1"
        assert "wp1" in lin.work_packet_ids
        assert "out1" in lin.outcome_ids
        assert "proj1" in lin.projection_ids

    def test_get_lineage_for_objective(self):
        graph = WorkContinuityGraph()
        lineages = graph.build_lineage(
            objectives=[
                {"goal_id": "g1", "title": "MVP", "domain": "engineering"},
                {"goal_id": "g2", "title": "Marketing", "domain": "marketing"},
            ],
            work_packets=[],
            outcomes=[],
            projections=[],
            recommendations=[],
        )
        result = graph.get_lineage_for_objective(lineages, "g2")
        assert result is not None
        assert result.objective_title == "Marketing"

    def test_next_work_packets(self):
        graph = WorkContinuityGraph()
        lineages = graph.build_lineage(
            objectives=[{"goal_id": "g1", "title": "MVP", "domain": "engineering"}],
            work_packets=[
                {"packet_id": "wp1", "domain": "engineering", "status": "completed"},
                {"packet_id": "wp2", "domain": "engineering", "status": "pending"},
            ],
            outcomes=[],
            projections=[],
            recommendations=[],
        )
        assert "wp2" in lineages[0].next_work_packet_ids
        assert "wp1" not in lineages[0].next_work_packet_ids


# ── Operator Brief Generator Tests ─────────────────────────────────────


class TestOperatorBriefGenerator:
    def test_generate_idle(self):
        gen = OperatorBriefGenerator()
        snap = ContinuitySnapshot()
        brief = gen.generate(snap)
        assert brief.brief_id.startswith("brief-")
        assert "idle" in brief.mission_status.lower()

    def test_generate_with_work(self):
        gen = OperatorBriefGenerator()
        snap = ContinuitySnapshot(
            active_objectives=[{"id": "g1", "title": "MVP"}],
            active_work_packets=[{"id": "wp1", "title": "Task"}],
            active_profile_mode="developer",
        )
        brief = gen.generate(snap)
        assert brief.active_objectives_count == 1
        assert brief.active_work_count == 1
        assert "progressing" in brief.mission_status.lower()

    def test_generate_with_risks(self):
        gen = OperatorBriefGenerator()
        snap = ContinuitySnapshot(
            active_objectives=[{"id": "g1"}],
            active_work_packets=[{"id": "wp1"}],
            active_risks=[{"severity": "high", "type": "milestone_slip"}],
        )
        brief = gen.generate(snap)
        assert brief.risk_count == 1
        assert "risk" in brief.mission_status.lower()

    def test_generate_with_blocked(self):
        gen = OperatorBriefGenerator()
        snap = ContinuitySnapshot(
            active_objectives=[{"id": "g1"}],
            active_work_packets=[{"id": "wp1"}],
            blocked_items=[{"id": "wp2", "title": "Blocked"}],
        )
        brief = gen.generate(snap)
        assert brief.blocked_count == 1
        assert "blocked" in brief.mission_status.lower()

    def test_generate_with_resume(self):
        gen = OperatorBriefGenerator()
        snap = ContinuitySnapshot(
            active_objectives=[{"id": "g1"}],
        )
        resume = ResumeReport(
            completed=[{"id": "wp1", "title": "Done"}],
            failed=[{"id": "wp2", "title": "Failed"}],
            recommended_actions=["Review failures"],
        )
        brief = gen.generate(snap, resume)
        assert len(brief.critical_changes) >= 2
        assert "Review failures" in brief.recommended_actions

    def test_pending_decisions(self):
        gen = OperatorBriefGenerator()
        snap = ContinuitySnapshot(
            approvals_waiting=[{"id": "a1", "title": "Deploy cockpit", "risk_level": "high"}],
            current_recommendations=[{"type": "automation", "title": "Auto-deploy"}],
        )
        brief = gen.generate(snap)
        assert len(brief.pending_decisions) >= 2


# ── Session Handoff Tests ──────────────────────────────────────────────


class TestSessionHandoff:
    def test_context_items(self):
        handoff = SessionHandoff(
            from_session_id="s1",
            to_session_id="s2",
            context_items=["3 objectives", "2 packets", "1 blocked"],
        )
        d = handoff.to_dict()
        assert len(d["context_items"]) == 3


# ── Continuity Runtime Integration Tests ───────────────────────────────


class TestContinuityRuntime:
    def _make_runtime(self, td: str) -> ContinuityRuntime:
        return ContinuityRuntime(data_dir=td)

    def test_capture_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            snap = rt.capture_snapshot()
            assert snap.snapshot_id.startswith("snap-")
            assert rt._run_count == 1

    def test_status(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            status = rt.status()
            assert status["state"] == "idle"
            rt.capture_snapshot()
            status = rt.status()
            assert status["state"] == "active"

    def test_record_departure(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            snap = rt.record_departure()
            assert rt._departure_snapshot is not None
            assert rt._departure_snapshot.snapshot_id == snap.snapshot_id

    def test_generate_resume(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            rt.record_departure()
            report = rt.generate_resume()
            assert isinstance(report, ResumeReport)
            assert report.absence_duration_seconds >= 0
            assert rt._departure_snapshot is None

    def test_generate_brief(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            brief = rt.generate_brief(include_resume=False)
            assert brief.brief_id.startswith("brief-")
            assert rt._last_brief is not None

    def test_build_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            rt.capture_snapshot()
            lineages = rt.build_lineage()
            assert isinstance(lineages, list)

    def test_record_session_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            handoff = rt.record_session_handoff("s1", "s2", "developer", "research")
            assert handoff.from_session_id == "s1"
            assert handoff.to_session_id == "s2"
            assert len(rt._session_handoffs) == 1

    def test_record_interaction(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            rt.record_interaction()
            assert rt.attention.state == AttentionState.ACTIVE

    def test_get_timeline(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            rt.timeline.record_event("decision", "Test decision")
            events = rt.get_timeline()
            assert len(events) >= 1

    def test_snapshot_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            snap = rt.capture_snapshot()
            snap_path = os.path.join(td, "snapshots", f"{snap.snapshot_id}.json")
            assert os.path.exists(snap_path)

    def test_get_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            assert rt.get_snapshot() is None
            rt.capture_snapshot()
            snap = rt.get_snapshot()
            assert snap is not None
            assert "snapshot_id" in snap

    def test_get_last_brief(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            assert rt.get_last_brief() is None
            rt.generate_brief(include_resume=False)
            brief = rt.get_last_brief()
            assert brief is not None
            assert "brief_id" in brief

    def test_get_handoffs(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._make_runtime(td)
            rt.record_session_handoff("s1", "s2")
            handoffs = rt.get_handoffs()
            assert len(handoffs) == 1


# ── Singleton Tests ────────────────────────────────────────────────────


class TestSingleton:
    def test_get_returns_same_instance(self):
        reset_continuity_runtime()
        a = get_continuity_runtime()
        b = get_continuity_runtime()
        assert a is b
        reset_continuity_runtime()

    def test_reset_clears_instance(self):
        reset_continuity_runtime()
        a = get_continuity_runtime()
        reset_continuity_runtime()
        b = get_continuity_runtime()
        assert a is not b
        reset_continuity_runtime()


# ── Acceptance Tests ───────────────────────────────────────────────────


class TestAcceptance:
    def test_resume_after_restart(self):
        """Verify continuity survives restart via persistence."""
        with tempfile.TemporaryDirectory() as td:
            rt1 = ContinuityRuntime(data_dir=td)
            rt1.capture_snapshot()
            rt1.timeline.record_event("decision", "Pre-restart decision")
            snap1_id = rt1._last_snapshot.snapshot_id

            rt2 = ContinuityRuntime(data_dir=td)
            events = rt2.get_timeline()
            assert len(events) >= 1
            assert events[0]["summary"] == "Pre-restart decision"

    def test_resume_after_session_transfer(self):
        """Verify session handoff preserves continuity context."""
        with tempfile.TemporaryDirectory() as td:
            rt = ContinuityRuntime(data_dir=td)
            rt.capture_snapshot()
            handoff = rt.record_session_handoff("dev-session", "research-session", "developer", "research")
            assert handoff.snapshot_id
            assert len(handoff.context_items) >= 1

    def test_resume_after_approval_wait(self):
        """Verify approval changes are detected on resume."""
        with tempfile.TemporaryDirectory() as td:
            rt = ContinuityRuntime(data_dir=td)
            before = ContinuitySnapshot(captured_at=1000, approvals_waiting=[])
            rt._departure_snapshot = before
            rt._last_snapshot = before

            after = ContinuitySnapshot(
                captured_at=5000,
                approvals_waiting=[{"id": "a1", "title": "Deploy", "risk_level": "high"}],
            )
            engine = ResumeStateEngine()
            report = engine.generate_resume(before, after)
            assert len(report.needs_review) >= 1

    def test_resume_after_work_completion(self):
        """Verify completed work is detected on resume."""
        with tempfile.TemporaryDirectory() as td:
            rt = ContinuityRuntime(data_dir=td)
            before = ContinuitySnapshot(
                captured_at=1000,
                active_work_packets=[
                    {"packet_id": "wp1", "title": "Build feature", "domain": "engineering"},
                    {"packet_id": "wp2", "title": "Write tests", "domain": "engineering"},
                ],
            )
            after = ContinuitySnapshot(
                captured_at=5000,
                active_work_packets=[
                    {"packet_id": "wp2", "title": "Write tests", "domain": "engineering"},
                ],
            )
            engine = ResumeStateEngine()
            report = engine.generate_resume(before, after)
            assert len(report.completed) == 1
            assert report.completed[0]["title"] == "Build feature"

    def test_resume_after_projection_update(self):
        """Verify new risks from projections are detected on resume."""
        with tempfile.TemporaryDirectory() as td:
            rt = ContinuityRuntime(data_dir=td)
            before = ContinuitySnapshot(captured_at=1000, active_risks=[])
            after = ContinuitySnapshot(
                captured_at=5000,
                active_risks=[
                    {"risk_id": "r1", "type": "milestone_slip", "severity": "critical"},
                    {"risk_id": "r2", "type": "velocity_decline", "severity": "high"},
                ],
            )
            engine = ResumeStateEngine()
            report = engine.generate_resume(before, after)
            risk_reviews = [r for r in report.needs_review if r["category"] == "new_risk"]
            assert len(risk_reviews) == 2

    def test_full_continuity_cycle(self):
        """End-to-end: capture → depart → resume → brief → handoff."""
        with tempfile.TemporaryDirectory() as td:
            rt = ContinuityRuntime(data_dir=td)

            snap = rt.capture_snapshot()
            assert snap.snapshot_id

            rt.record_interaction()
            assert rt.attention.state == AttentionState.ACTIVE

            departure = rt.record_departure()
            assert rt._departure_snapshot is not None

            resume = rt.generate_resume()
            assert isinstance(resume, ResumeReport)
            assert rt._departure_snapshot is None

            brief = rt.generate_brief(include_resume=False)
            assert brief.brief_id.startswith("brief-")
            assert brief.mission_status

            handoff = rt.record_session_handoff("session-1", "session-2")
            assert handoff.snapshot_id

            lineages = rt.build_lineage()
            assert isinstance(lineages, list)

            timeline = rt.get_timeline()
            assert len(timeline) >= 2

            status = rt.status()
            assert status["run_count"] >= 3
            assert status["handoff_count"] == 1
