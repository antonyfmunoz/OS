"""C29 Harness Superiority — data model tests.

Covers every enum, dataclass roundtrip, auto-computed field, and the
TaskRegistry / ResultStore persistence layers.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.benchmarks.harness_superiority import (
    EVIDENCE_WEIGHTS,
    AwarenessSnapshot,
    BenchmarkCategory,
    BenchmarkTask,
    BrowserEvidence,
    CognitiveLoadResult,
    Complexity,
    ContinuityResult,
    EscapeEvent,
    EvidenceClass,
    EvidenceConfidence,
    GovernanceResult,
    InterruptionResult,
    LongitudinalCheckpoint,
    MetaIDEResult,
    MetricWithConfidence,
    MVPTrustVerdict,
    MVPVerdictLevel,
    Outcome,
    OperatorTrustResult,
    PreviewResult,
    RealityDriftResult,
    ResourceCost,
    ResultStore,
    TaskRegistry,
    Track,
    TrackResult,
    VoiceResult,
    WorkdayCoverage,
)


# ===========================================================================
# Enums
# ===========================================================================


class TestEnums:
    def test_benchmark_category_values(self):
        assert BenchmarkCategory.BUG_FIX.value == "BUG_FIX"
        assert BenchmarkCategory.FEATURE.value == "FEATURE"
        assert BenchmarkCategory.REFACTOR.value == "REFACTOR"
        assert BenchmarkCategory.DEPLOY.value == "DEPLOY"
        assert BenchmarkCategory.RECOVERY.value == "RECOVERY"

    def test_benchmark_category_count(self):
        assert len(list(BenchmarkCategory)) == 5

    def test_benchmark_category_roundtrip(self):
        for cat in BenchmarkCategory:
            assert BenchmarkCategory(cat.value) is cat

    def test_evidence_class_values(self):
        assert EvidenceClass.A_PRODUCTION.value == "A_PRODUCTION"
        assert EvidenceClass.B_CONTROLLED.value == "B_CONTROLLED"
        assert EvidenceClass.C_SYNTHETIC.value == "C_SYNTHETIC"

    def test_evidence_class_count(self):
        assert len(list(EvidenceClass)) == 3

    def test_evidence_class_roundtrip(self):
        for ec in EvidenceClass:
            assert EvidenceClass(ec.value) is ec

    def test_evidence_confidence_values(self):
        assert EvidenceConfidence.HIGH.value == "HIGH"
        assert EvidenceConfidence.MEDIUM.value == "MEDIUM"
        assert EvidenceConfidence.LOW.value == "LOW"

    def test_evidence_confidence_roundtrip(self):
        for c in EvidenceConfidence:
            assert EvidenceConfidence(c.value) is c

    def test_outcome_values(self):
        assert Outcome.SUCCESS.value == "SUCCESS"
        assert Outcome.PARTIAL.value == "PARTIAL"
        assert Outcome.FAILED.value == "FAILED"

    def test_outcome_roundtrip(self):
        for o in Outcome:
            assert Outcome(o.value) is o

    def test_outcome_str_comparison(self):
        # Outcome is a str enum; scorer compares r.outcome == "SUCCESS".
        assert Outcome.SUCCESS == "SUCCESS"
        assert Outcome.FAILED != "SUCCESS"

    def test_complexity_values(self):
        assert Complexity.LOW.value == "LOW"
        assert Complexity.MEDIUM.value == "MEDIUM"
        assert Complexity.HIGH.value == "HIGH"

    def test_complexity_roundtrip(self):
        for c in Complexity:
            assert Complexity(c.value) is c

    def test_track_values(self):
        assert Track.A_LEGACY.value == "A_LEGACY"
        assert Track.B_UMH.value == "B_UMH"

    def test_track_roundtrip(self):
        for t in Track:
            assert Track(t.value) is t

    def test_mvp_verdict_level_values(self):
        assert MVPVerdictLevel.NOT_READY.value == "NOT_READY"
        assert MVPVerdictLevel.PARTIALLY_TRUSTED.value == "PARTIALLY_TRUSTED"
        assert MVPVerdictLevel.PRIMARY_WORKSTATION.value == "PRIMARY_WORKSTATION"
        assert MVPVerdictLevel.CERTIFIED_DAILY_DRIVER.value == "CERTIFIED_DAILY_DRIVER"

    def test_mvp_verdict_level_count(self):
        assert len(list(MVPVerdictLevel)) == 4

    def test_mvp_verdict_level_roundtrip(self):
        for v in MVPVerdictLevel:
            assert MVPVerdictLevel(v.value) is v


class TestEvidenceWeights:
    def test_class_a_weight(self):
        assert EVIDENCE_WEIGHTS[EvidenceClass.A_PRODUCTION] == 1.0

    def test_class_b_weight(self):
        assert EVIDENCE_WEIGHTS[EvidenceClass.B_CONTROLLED] == 0.625

    def test_class_c_weight(self):
        assert EVIDENCE_WEIGHTS[EvidenceClass.C_SYNTHETIC] == 0.125

    def test_all_classes_have_weights(self):
        for ec in EvidenceClass:
            assert ec in EVIDENCE_WEIGHTS

    def test_weight_ordering(self):
        assert (
            EVIDENCE_WEIGHTS[EvidenceClass.A_PRODUCTION]
            > EVIDENCE_WEIGHTS[EvidenceClass.B_CONTROLLED]
            > EVIDENCE_WEIGHTS[EvidenceClass.C_SYNTHETIC]
        )


# ===========================================================================
# BenchmarkTask
# ===========================================================================


class TestBenchmarkTask:
    def _make(self):
        return BenchmarkTask(
            task_id="c29-001",
            category=BenchmarkCategory.BUG_FIX,
            project="UMH",
            title="Fix login redirect",
            description="The redirect loops after login",
            complexity=Complexity.MEDIUM,
            expected_deliverables=["patch", "test"],
            created_at="2026-06-23T10:00:00",
        )

    def test_construction_all_fields(self):
        t = self._make()
        assert t.task_id == "c29-001"
        assert t.category is BenchmarkCategory.BUG_FIX
        assert t.project == "UMH"
        assert t.title == "Fix login redirect"
        assert t.complexity is Complexity.MEDIUM
        assert t.expected_deliverables == ["patch", "test"]
        assert t.created_at == "2026-06-23T10:00:00"

    def test_defaults(self):
        t = BenchmarkTask(
            task_id="c29-002",
            category=BenchmarkCategory.FEATURE,
            project="CreatorOS",
            title="t",
            description="d",
            complexity=Complexity.LOW,
        )
        assert t.expected_deliverables == []
        assert t.created_at == ""

    def test_to_dict(self):
        d = self._make().to_dict()
        assert d["category"] == "BUG_FIX"
        assert d["complexity"] == "MEDIUM"
        assert d["expected_deliverables"] == ["patch", "test"]
        assert isinstance(d["category"], str)

    def test_roundtrip(self):
        t = self._make()
        assert BenchmarkTask.from_dict(t.to_dict()) == t

    def test_from_dict_missing_optional(self):
        t = BenchmarkTask.from_dict(
            {
                "task_id": "x",
                "category": "DEPLOY",
                "project": "LyfeOS",
                "title": "t",
                "description": "d",
                "complexity": "HIGH",
            }
        )
        assert t.expected_deliverables == []
        assert t.created_at == ""

    def test_to_dict_copies_list(self):
        t = self._make()
        d = t.to_dict()
        d["expected_deliverables"].append("mutated")
        assert t.expected_deliverables == ["patch", "test"]


# ===========================================================================
# Simple nested sub-result roundtrips
# ===========================================================================


class TestEscapeEvent:
    def test_roundtrip(self):
        e = EscapeEvent(
            timestamp="2026-06-23T10:00:00",
            tool="terminal",
            reason="needed raw shell",
            could_cockpit_handle=False,
        )
        assert EscapeEvent.from_dict(e.to_dict()) == e

    def test_bool_coercion(self):
        e = EscapeEvent.from_dict(
            {"timestamp": "t", "tool": "x", "reason": "r", "could_cockpit_handle": 1}
        )
        assert e.could_cockpit_handle is True


class TestContinuityResult:
    def test_roundtrip(self):
        c = ContinuityResult(
            interruption_duration_seconds=120.0,
            context_preserved=True,
            resume_time_seconds=15.0,
            decisions_recalled=4,
            decisions_total=5,
            intent_preserved=True,
        )
        assert ContinuityResult.from_dict(c.to_dict()) == c

    def test_type_coercion(self):
        c = ContinuityResult.from_dict(
            {
                "interruption_duration_seconds": "120",
                "context_preserved": 1,
                "resume_time_seconds": "15",
                "decisions_recalled": "4",
                "decisions_total": "5",
                "intent_preserved": 0,
            }
        )
        assert c.interruption_duration_seconds == 120.0
        assert c.context_preserved is True
        assert c.intent_preserved is False
        assert c.decisions_recalled == 4


class TestGovernanceResult:
    def test_roundtrip(self):
        g = GovernanceResult(
            approvals_required=3,
            approvals_enforced=3,
            proof_generated=True,
            verification_enforced=True,
            false_history_tested=True,
            false_history_blocked=True,
        )
        assert GovernanceResult.from_dict(g.to_dict()) == g


class TestVoiceResult:
    def test_roundtrip(self):
        v = VoiceResult(
            commands_attempted=10,
            commands_recognized=9,
            intents_correct=8,
            routes_correct=8,
            recovery_after_failure=True,
        )
        assert VoiceResult.from_dict(v.to_dict()) == v


class TestPreviewResult:
    def test_roundtrip(self):
        p = PreviewResult(
            preview_loaded=True,
            mobile_viewport=True,
            tablet_viewport=False,
            desktop_viewport=True,
            expand_collapse=True,
            health_visible=False,
        )
        assert PreviewResult.from_dict(p.to_dict()) == p


class TestBrowserEvidence:
    def test_roundtrip_full(self):
        b = BrowserEvidence(
            screenshots=["s1.png"],
            console_errors=["err"],
            console_log=["log"],
            network_errors=["neterr"],
            network_traces=["trace"],
            execution_traces=["exec"],
            proof_package_id="pp-1",
            verification_result="PASS",
        )
        assert BrowserEvidence.from_dict(b.to_dict()) == b

    def test_defaults(self):
        b = BrowserEvidence()
        assert b.screenshots == []
        assert b.proof_package_id == ""
        assert BrowserEvidence.from_dict(b.to_dict()) == b


class TestInterruptionResult:
    def test_roundtrip(self):
        i = InterruptionResult(
            interruption_type="MEETING",
            interruption_from="task-a",
            interruption_to="away",
            away_duration_seconds=1800.0,
            resume_time_seconds=12.0,
            context_accuracy=0.9,
            decisions_recalled=4,
            decisions_total=5,
            work_recovery_complete=True,
        )
        assert InterruptionResult.from_dict(i.to_dict()) == i


class TestRealityDriftResult:
    def test_roundtrip(self):
        r = RealityDriftResult(
            drift_type="STALE_BRANCH",
            drift_present=True,
            drift_detected=True,
            detection_time_seconds=3.0,
            false_positive=False,
            detection_method="automated",
        )
        assert RealityDriftResult.from_dict(r.to_dict()) == r


class TestResourceCost:
    def test_roundtrip(self):
        c = ResourceCost(
            tokens_used=10000,
            compute_seconds=42.5,
            operator_minutes=8.0,
            clicks=30,
            panel_changes=5,
            commands_issued=12,
            cost_per_deliverable=2.0,
        )
        assert ResourceCost.from_dict(c.to_dict()) == c


class TestLongitudinalCheckpoint:
    def test_roundtrip_full(self):
        cp = LongitudinalCheckpoint(
            checkpoint_number=1,
            runs_completed_at_checkpoint=10,
            challenge_tasks=["q1", "q2"],
            correct_answers=8,
            total_questions=10,
            track_a_recall_score=0.6,
            track_b_recall_score=0.9,
            time_to_answer_seconds=5.0,
        )
        assert LongitudinalCheckpoint.from_dict(cp.to_dict()) == cp

    def test_defaults(self):
        cp = LongitudinalCheckpoint(
            checkpoint_number=1, runs_completed_at_checkpoint=5
        )
        assert cp.challenge_tasks == []
        assert cp.correct_answers == 0
        assert LongitudinalCheckpoint.from_dict(cp.to_dict()) == cp


class TestMetricWithConfidence:
    def test_roundtrip(self):
        m = MetricWithConfidence(
            name="CPR",
            value=0.97,
            confidence=EvidenceConfidence.HIGH,
            class_a_count=10,
            class_b_count=3,
            class_c_count=2,
        )
        assert MetricWithConfidence.from_dict(m.to_dict()) == m

    def test_to_dict_confidence_is_str(self):
        m = MetricWithConfidence(
            name="VC",
            value=0.5,
            confidence=EvidenceConfidence.LOW,
            class_a_count=0,
            class_b_count=0,
            class_c_count=4,
        )
        assert m.to_dict()["confidence"] == "LOW"


class TestMVPTrustVerdict:
    def test_roundtrip(self):
        v = MVPTrustVerdict(
            would_choose_first="yes",
            would_stay_in="yes",
            trusts_with_production="yes",
            recommends_replacing_legacy="yes",
            projection_acceleration_justified="yes",
            verdict=MVPVerdictLevel.PRIMARY_WORKSTATION,
            evidence_summary="strong",
        )
        assert MVPTrustVerdict.from_dict(v.to_dict()) == v

    def test_to_dict_verdict_is_str(self):
        v = MVPTrustVerdict(
            would_choose_first="",
            would_stay_in="",
            trusts_with_production="",
            recommends_replacing_legacy="",
            projection_acceleration_justified="",
            verdict=MVPVerdictLevel.NOT_READY,
            evidence_summary="",
        )
        assert v.to_dict()["verdict"] == "NOT_READY"


# ===========================================================================
# Auto-computed fields
# ===========================================================================


class TestCognitiveLoadResult:
    def test_score_formula(self):
        # total = 1+1+1+1+1 = 5 -> 1.0 - min(5/20,1) = 0.75
        c = CognitiveLoadResult(1, 1, 1, 1, 1)
        assert c.cognitive_load_score == pytest.approx(0.75)

    def test_all_zero_is_one(self):
        c = CognitiveLoadResult(0, 0, 0, 0, 0)
        assert c.cognitive_load_score == 1.0

    def test_saturates_at_zero(self):
        # total = 25 -> min(25/20,1)=1 -> score 0.0
        c = CognitiveLoadResult(5, 5, 5, 5, 5)
        assert c.cognitive_load_score == 0.0

    def test_exactly_twenty_is_zero(self):
        c = CognitiveLoadResult(4, 4, 4, 4, 4)
        assert c.cognitive_load_score == 0.0

    def test_explicit_score_preserved(self):
        c = CognitiveLoadResult(10, 10, 10, 10, 10, cognitive_load_score=0.42)
        assert c.cognitive_load_score == 0.42

    def test_roundtrip_preserves_score(self):
        c = CognitiveLoadResult(2, 1, 0, 1, 0)
        c2 = CognitiveLoadResult.from_dict(c.to_dict())
        assert c2.cognitive_load_score == c.cognitive_load_score
        assert c2 == c

    def test_from_dict_recomputes_when_absent(self):
        c = CognitiveLoadResult.from_dict(
            {
                "reconstruction_steps": 1,
                "clarification_questions": 1,
                "context_searches": 1,
                "panel_hops": 1,
                "memory_recovery_actions": 1,
            }
        )
        assert c.cognitive_load_score == pytest.approx(0.75)


class TestAwarenessSnapshot:
    def test_all_true_is_one(self):
        a = AwarenessSnapshot(
            repos_visible=True,
            branches_visible=True,
            builds_visible=True,
            deployments_visible=True,
            containers_visible=True,
            previews_visible=True,
            sessions_visible=True,
            executions_visible=True,
            agents_visible=True,
            device_mesh_visible=True,
        )
        assert a.awareness_score == 1.0

    def test_all_false_is_zero(self):
        assert AwarenessSnapshot().awareness_score == 0.0

    def test_mixed(self):
        a = AwarenessSnapshot(repos_visible=True, branches_visible=True, builds_visible=True)
        assert a.awareness_score == pytest.approx(0.3)

    def test_roundtrip(self):
        a = AwarenessSnapshot(repos_visible=True, agents_visible=True)
        a2 = AwarenessSnapshot.from_dict(a.to_dict())
        assert a2 == a
        assert a2.awareness_score == pytest.approx(0.2)


class TestMetaIDEResult:
    def test_all_true_is_one(self):
        m = MetaIDEResult(
            workspace_aware=True,
            repo_aware=True,
            branch_aware=True,
            execution_aware=True,
            preview_aware=True,
            proof_aware=True,
            continuity_aware=True,
        )
        assert m.meta_ide_score == 1.0

    def test_all_false_is_zero(self):
        assert MetaIDEResult().meta_ide_score == 0.0

    def test_mixed(self):
        m = MetaIDEResult(workspace_aware=True, repo_aware=True, branch_aware=True)
        assert m.meta_ide_score == pytest.approx(3 / 7)

    def test_roundtrip(self):
        m = MetaIDEResult(workspace_aware=True, proof_aware=True)
        m2 = MetaIDEResult.from_dict(m.to_dict())
        assert m2 == m
        assert m2.meta_ide_score == pytest.approx(2 / 7)


class TestWorkdayCoverage:
    def test_all_true_is_one(self):
        w = WorkdayCoverage(
            coding=True,
            debugging=True,
            review=True,
            deployment=True,
            planning=True,
            continuity=True,
            documentation=True,
            approvals=True,
            knowledge_retrieval=True,
            runtime_inspection=True,
        )
        assert w.coverage_score == 1.0

    def test_all_false_is_zero(self):
        assert WorkdayCoverage().coverage_score == 0.0

    def test_mixed(self):
        w = WorkdayCoverage(coding=True, debugging=True, review=True, deployment=True)
        assert w.coverage_score == pytest.approx(0.4)

    def test_roundtrip(self):
        w = WorkdayCoverage(coding=True, deployment=True)
        w2 = WorkdayCoverage.from_dict(w.to_dict())
        assert w2 == w
        assert w2.coverage_score == pytest.approx(0.2)


class TestOperatorTrustResult:
    def test_trust_delta_auto(self):
        o = OperatorTrustResult(
            confidence_before=2,
            confidence_after=5,
            verification_needed=False,
            manual_double_checks=0,
        )
        assert o.trust_delta == 3

    def test_trust_delta_negative(self):
        o = OperatorTrustResult(
            confidence_before=4,
            confidence_after=2,
            verification_needed=True,
            manual_double_checks=3,
        )
        assert o.trust_delta == -2

    def test_explicit_delta_preserved(self):
        o = OperatorTrustResult(
            confidence_before=1,
            confidence_after=1,
            verification_needed=False,
            manual_double_checks=0,
            trust_delta=99,
        )
        assert o.trust_delta == 99

    def test_roundtrip(self):
        o = OperatorTrustResult(
            confidence_before=3,
            confidence_after=4,
            verification_needed=True,
            manual_double_checks=1,
        )
        assert OperatorTrustResult.from_dict(o.to_dict()) == o


# ===========================================================================
# TrackResult — the central record
# ===========================================================================


def _full_track_result() -> TrackResult:
    return TrackResult(
        task_id="c29-001",
        track=Track.B_UMH,
        evidence_class=EvidenceClass.A_PRODUCTION,
        started_at="2026-06-23T10:00:00",
        completed_at="2026-06-23T10:30:00",
        duration_seconds=1800.0,
        outcome=Outcome.SUCCESS,
        deliverables_met=["patch", "test"],
        quality_score=92.0,
        verification_method="browser",
        verification_passed=True,
        recovery_needed=True,
        recovery_successful=True,
        recovery_time_seconds=10.0,
        context_switches=2,
        manual_reconstructions=0,
        tools_used=["cockpit", "meta_ide"],
        escapes=[
            EscapeEvent(
                timestamp="t", tool="terminal", reason="r", could_cockpit_handle=False
            )
        ],
        continuity_test=ContinuityResult(
            interruption_duration_seconds=60.0,
            context_preserved=True,
            resume_time_seconds=12.0,
            decisions_recalled=4,
            decisions_total=5,
            intent_preserved=True,
        ),
        governance_test=GovernanceResult(
            approvals_required=2,
            approvals_enforced=2,
            proof_generated=True,
            verification_enforced=True,
            false_history_tested=True,
            false_history_blocked=True,
        ),
        awareness_snapshot=AwarenessSnapshot(repos_visible=True, branches_visible=True),
        cognitive_load=CognitiveLoadResult(1, 1, 1, 0, 0),
        interruption_test=InterruptionResult(
            interruption_type="MEETING",
            interruption_from="a",
            interruption_to="away",
            away_duration_seconds=900.0,
            resume_time_seconds=8.0,
            context_accuracy=0.9,
            decisions_recalled=4,
            decisions_total=5,
            work_recovery_complete=True,
        ),
        reality_drift=RealityDriftResult(
            drift_type="STALE_BRANCH",
            drift_present=True,
            drift_detected=True,
            detection_time_seconds=2.0,
            false_positive=False,
            detection_method="automated",
        ),
        operator_trust=OperatorTrustResult(
            confidence_before=3,
            confidence_after=5,
            verification_needed=False,
            manual_double_checks=0,
        ),
        meta_ide_test=MetaIDEResult(workspace_aware=True, repo_aware=True),
        resource_cost=ResourceCost(
            tokens_used=5000,
            compute_seconds=10.0,
            operator_minutes=6.0,
            clicks=20,
            panel_changes=3,
            commands_issued=8,
            cost_per_deliverable=3.0,
        ),
        browser_evidence=BrowserEvidence(screenshots=["s.png"], proof_package_id="pp"),
        voice_test=VoiceResult(
            commands_attempted=5,
            commands_recognized=5,
            intents_correct=5,
            routes_correct=5,
            recovery_after_failure=True,
        ),
        preview_test=PreviewResult(
            preview_loaded=True,
            mobile_viewport=True,
            tablet_viewport=True,
            desktop_viewport=True,
            expand_collapse=True,
            health_visible=True,
        ),
        notes="full result",
    )


class TestTrackResult:
    def test_construction_minimal(self):
        r = TrackResult(
            task_id="t",
            track=Track.A_LEGACY,
            evidence_class=EvidenceClass.C_SYNTHETIC,
            started_at="s",
            completed_at="c",
            duration_seconds=1.0,
            outcome=Outcome.FAILED,
        )
        assert r.deliverables_met == []
        assert r.quality_score == 0.0
        assert r.continuity_test is None
        assert r.escapes == []

    def test_to_dict_enum_serialization(self):
        r = _full_track_result()
        d = r.to_dict()
        assert d["track"] == "B_UMH"
        assert d["evidence_class"] == "A_PRODUCTION"
        assert d["outcome"] == "SUCCESS"

    def test_to_dict_nested_serialization(self):
        d = _full_track_result().to_dict()
        assert d["continuity_test"]["context_preserved"] is True
        assert d["governance_test"]["approvals_required"] == 2
        assert d["escapes"][0]["tool"] == "terminal"
        assert d["cognitive_load"]["cognitive_load_score"] == pytest.approx(0.85)

    def test_roundtrip_full(self):
        r = _full_track_result()
        assert TrackResult.from_dict(r.to_dict()) == r

    def test_roundtrip_minimal(self):
        r = TrackResult(
            task_id="t",
            track=Track.A_LEGACY,
            evidence_class=EvidenceClass.B_CONTROLLED,
            started_at="s",
            completed_at="c",
            duration_seconds=2.0,
            outcome=Outcome.PARTIAL,
        )
        assert TrackResult.from_dict(r.to_dict()) == r

    def test_from_dict_none_nested(self):
        r = _full_track_result()
        d = r.to_dict()
        for key in (
            "continuity_test",
            "governance_test",
            "awareness_snapshot",
            "cognitive_load",
            "interruption_test",
            "reality_drift",
            "operator_trust",
            "meta_ide_test",
            "resource_cost",
            "browser_evidence",
            "voice_test",
            "preview_test",
        ):
            d[key] = None
        r2 = TrackResult.from_dict(d)
        assert r2.continuity_test is None
        assert r2.meta_ide_test is None
        assert r2.browser_evidence is None

    def test_from_dict_nested_reconstructed_as_types(self):
        r2 = TrackResult.from_dict(_full_track_result().to_dict())
        assert isinstance(r2.continuity_test, ContinuityResult)
        assert isinstance(r2.meta_ide_test, MetaIDEResult)
        assert isinstance(r2.escapes[0], EscapeEvent)
        assert isinstance(r2.awareness_snapshot, AwarenessSnapshot)

    @pytest.mark.parametrize(
        "ec",
        [
            EvidenceClass.A_PRODUCTION,
            EvidenceClass.B_CONTROLLED,
            EvidenceClass.C_SYNTHETIC,
        ],
    )
    def test_each_evidence_class(self, ec):
        r = _full_track_result()
        r.evidence_class = ec
        assert TrackResult.from_dict(r.to_dict()).evidence_class is ec

    def test_escapes_list_roundtrip(self):
        r = _full_track_result()
        r.escapes = [
            EscapeEvent(timestamp="1", tool="a", reason="r1", could_cockpit_handle=True),
            EscapeEvent(timestamp="2", tool="b", reason="r2", could_cockpit_handle=False),
        ]
        r2 = TrackResult.from_dict(r.to_dict())
        assert len(r2.escapes) == 2
        assert r2.escapes == r.escapes


# ===========================================================================
# TaskRegistry
# ===========================================================================


@pytest.fixture
def registry(tmp_path):
    return TaskRegistry(path=tmp_path / "tasks.jsonl")


def _task(task_id, category=BenchmarkCategory.BUG_FIX, project="UMH"):
    return BenchmarkTask(
        task_id=task_id,
        category=category,
        project=project,
        title="t",
        description="d",
        complexity=Complexity.LOW,
    )


class TestTaskRegistry:
    def test_register_and_get(self, registry):
        t = _task("c29-001")
        registry.register(t)
        assert registry.get("c29-001") == t

    def test_get_nonexistent(self, registry):
        assert registry.get("missing") is None

    def test_list_all_empty(self, registry):
        assert registry.list_all() == []

    def test_list_all(self, registry):
        registry.register(_task("a"))
        registry.register(_task("b"))
        ids = {t.task_id for t in registry.list_all()}
        assert ids == {"a", "b"}

    def test_count(self, registry):
        assert registry.count() == 0
        registry.register(_task("a"))
        registry.register(_task("b"))
        assert registry.count() == 2

    def test_list_by_category(self, registry):
        registry.register(_task("a", category=BenchmarkCategory.BUG_FIX))
        registry.register(_task("b", category=BenchmarkCategory.FEATURE))
        registry.register(_task("c", category=BenchmarkCategory.BUG_FIX))
        bug = registry.list_by_category(BenchmarkCategory.BUG_FIX)
        assert {t.task_id for t in bug} == {"a", "c"}

    def test_list_by_category_empty(self, registry):
        registry.register(_task("a", category=BenchmarkCategory.BUG_FIX))
        assert registry.list_by_category(BenchmarkCategory.DEPLOY) == []

    def test_list_by_project(self, registry):
        registry.register(_task("a", project="UMH"))
        registry.register(_task("b", project="CreatorOS"))
        registry.register(_task("c", project="UMH"))
        umh = registry.list_by_project("UMH")
        assert {t.task_id for t in umh} == {"a", "c"}

    def test_list_by_project_empty(self, registry):
        registry.register(_task("a", project="UMH"))
        assert registry.list_by_project("Nope") == []

    def test_register_multiple_persists(self, registry, tmp_path):
        for i in range(5):
            registry.register(_task(f"t{i}"))
        # New instance reading same file.
        fresh = TaskRegistry(path=tmp_path / "tasks.jsonl")
        assert fresh.count() == 5

    def test_default_path_under_umh_root(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_ROOT", str(tmp_path))
        reg = TaskRegistry()
        reg.register(_task("a"))
        assert (tmp_path / "data" / "certification" / "c29" / "tasks.jsonl").exists()


# ===========================================================================
# ResultStore
# ===========================================================================


@pytest.fixture
def store(tmp_path):
    return ResultStore(path=tmp_path / "results.jsonl")


def _result(task_id, track=Track.B_UMH, ec=EvidenceClass.A_PRODUCTION):
    return TrackResult(
        task_id=task_id,
        track=track,
        evidence_class=ec,
        started_at="s",
        completed_at="c",
        duration_seconds=1.0,
        outcome=Outcome.SUCCESS,
    )


class TestResultStore:
    def test_record_and_get_results(self, store):
        r = _result("c29-001")
        store.record(r)
        got = store.get_results("c29-001")
        assert len(got) == 1
        assert got[0] == r

    def test_get_results_empty(self, store):
        assert store.get_results("missing") == []

    def test_list_all_empty(self, store):
        assert store.list_all() == []

    def test_list_all(self, store):
        store.record(_result("a"))
        store.record(_result("b"))
        assert store.count() == 2

    def test_count(self, store):
        assert store.count() == 0
        store.record(_result("a"))
        assert store.count() == 1

    def test_list_by_track(self, store):
        store.record(_result("a", track=Track.A_LEGACY))
        store.record(_result("b", track=Track.B_UMH))
        store.record(_result("c", track=Track.B_UMH))
        umh = store.list_by_track(Track.B_UMH)
        assert {r.task_id for r in umh} == {"b", "c"}

    def test_list_by_evidence_class(self, store):
        store.record(_result("a", ec=EvidenceClass.A_PRODUCTION))
        store.record(_result("b", ec=EvidenceClass.C_SYNTHETIC))
        store.record(_result("c", ec=EvidenceClass.A_PRODUCTION))
        a = store.list_by_evidence_class(EvidenceClass.A_PRODUCTION)
        assert {r.task_id for r in a} == {"a", "c"}

    def test_get_track_results(self, store):
        store.record(_result("a", track=Track.A_LEGACY))
        store.record(_result("a", track=Track.B_UMH))
        legacy = store.get_track_results("a", Track.A_LEGACY)
        assert len(legacy) == 1
        assert legacy[0].track is Track.A_LEGACY

    def test_multiple_results_same_task(self, store):
        store.record(_result("a", track=Track.A_LEGACY))
        store.record(_result("a", track=Track.B_UMH))
        assert len(store.get_results("a")) == 2

    def test_evidence_distribution(self, store):
        store.record(_result("a", ec=EvidenceClass.A_PRODUCTION))
        store.record(_result("b", ec=EvidenceClass.A_PRODUCTION))
        store.record(_result("c", ec=EvidenceClass.B_CONTROLLED))
        store.record(_result("d", ec=EvidenceClass.C_SYNTHETIC))
        dist = store.evidence_distribution()
        assert dist == {
            "A_PRODUCTION": 2,
            "B_CONTROLLED": 1,
            "C_SYNTHETIC": 1,
        }

    def test_evidence_distribution_empty(self, store):
        dist = store.evidence_distribution()
        assert dist == {
            "A_PRODUCTION": 0,
            "B_CONTROLLED": 0,
            "C_SYNTHETIC": 0,
        }

    def test_full_result_persists(self, store, tmp_path):
        store.record(_full_track_result())
        fresh = ResultStore(path=tmp_path / "results.jsonl")
        got = fresh.get_results("c29-001")
        assert len(got) == 1
        assert got[0] == _full_track_result()

    def test_default_path_under_umh_root(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_ROOT", str(tmp_path))
        st = ResultStore()
        st.record(_result("a"))
        assert (tmp_path / "data" / "certification" / "c29" / "results.jsonl").exists()
