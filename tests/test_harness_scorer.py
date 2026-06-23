"""C29 Harness Superiority — scoring engine tests.

Covers weighted_mean, the 10 HarnessScorer dimensions, the 11 HTI components,
the 10 UMH metrics, and the MVPVerdictEngine — with heavy focus on the four
hard evidence-classification rules and the litmus-test standard.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.benchmarks.harness_superiority import (
    AwarenessSnapshot,
    CognitiveLoadResult,
    ContinuityResult,
    EscapeEvent,
    EvidenceClass,
    EvidenceConfidence,
    GovernanceResult,
    InterruptionResult,
    MetaIDEResult,
    MVPVerdictLevel,
    Outcome,
    OperatorTrustResult,
    RealityDriftResult,
    ResourceCost,
    Track,
    TrackResult,
    WorkdayCoverage,
)
from substrate.organism.benchmarks.harness_scorer import (
    HarnessScorer,
    HTICalculator,
    MVPVerdictEngine,
    UMHMetricCalculator,
    unweighted_mean,
    weighted_mean,
)


# ===========================================================================
# Factory
# ===========================================================================


def make_result(
    task_id="t",
    track=Track.B_UMH,
    evidence_class=EvidenceClass.A_PRODUCTION,
    outcome=Outcome.SUCCESS,
    quality=90.0,
    verification_passed=True,
    recovery_needed=False,
    recovery_successful=True,
    cognitive_score=0.85,
    context_accuracy=0.9,
    work_recovery=True,
    resume_time=12.0,
    context_preserved=True,
    approvals_required=2,
    approvals_enforced=2,
    proof_generated=True,
    awareness=1.0,
    meta_ide=1.0,
    operator_minutes=6.0,
    confidence_after=5,
    verification_needed=False,
    drift_present=True,
    drift_detected=True,
    false_positive=False,
    tools_used=None,
    escapes=None,
    deliverables=None,
) -> TrackResult:
    """Build a TrackResult with sensible defaults; override per dimension.

    Awareness/meta_ide are fractions (0-1); the snapshot/result is built so
    its derived score matches via the count-based formula closely enough for
    perfect (1.0) and zero (0.0) cases used in tests.
    """
    n_aware = round(awareness * 10)
    aware_fields = [
        "repos_visible",
        "branches_visible",
        "builds_visible",
        "deployments_visible",
        "containers_visible",
        "previews_visible",
        "sessions_visible",
        "executions_visible",
        "agents_visible",
        "device_mesh_visible",
    ]
    snapshot = AwarenessSnapshot(**{aware_fields[i]: True for i in range(n_aware)})

    n_meta = round(meta_ide * 7)
    meta_fields = [
        "workspace_aware",
        "repo_aware",
        "branch_aware",
        "execution_aware",
        "preview_aware",
        "proof_aware",
        "continuity_aware",
    ]
    meta = MetaIDEResult(**{meta_fields[i]: True for i in range(n_meta)})

    return TrackResult(
        task_id=task_id,
        track=track,
        evidence_class=evidence_class,
        started_at="s",
        completed_at="c",
        duration_seconds=1.0,
        outcome=outcome,
        deliverables_met=deliverables if deliverables is not None else ["d"],
        quality_score=quality,
        verification_passed=verification_passed,
        recovery_needed=recovery_needed,
        recovery_successful=recovery_successful,
        tools_used=tools_used if tools_used is not None else ["a", "b"],
        escapes=escapes if escapes is not None else [],
        continuity_test=ContinuityResult(
            interruption_duration_seconds=10.0,
            context_preserved=context_preserved,
            resume_time_seconds=resume_time,
            decisions_recalled=4,
            decisions_total=5,
            intent_preserved=True,
        ),
        governance_test=GovernanceResult(
            approvals_required=approvals_required,
            approvals_enforced=approvals_enforced,
            proof_generated=proof_generated,
            verification_enforced=True,
            false_history_tested=True,
            false_history_blocked=True,
        ),
        awareness_snapshot=snapshot,
        cognitive_load=CognitiveLoadResult(0, 0, 0, 0, 0, cognitive_load_score=cognitive_score),
        interruption_test=InterruptionResult(
            interruption_type="MEETING",
            interruption_from="a",
            interruption_to="away",
            away_duration_seconds=60.0,
            resume_time_seconds=resume_time,
            context_accuracy=context_accuracy,
            decisions_recalled=4,
            decisions_total=5,
            work_recovery_complete=work_recovery,
        ),
        reality_drift=RealityDriftResult(
            drift_type="STALE_BRANCH",
            drift_present=drift_present,
            drift_detected=drift_detected,
            detection_time_seconds=2.0,
            false_positive=false_positive,
            detection_method="automated",
        ),
        operator_trust=OperatorTrustResult(
            confidence_before=3,
            confidence_after=confidence_after,
            verification_needed=verification_needed,
            manual_double_checks=0,
        ),
        meta_ide_test=meta,
        resource_cost=ResourceCost(
            tokens_used=1000,
            compute_seconds=1.0,
            operator_minutes=operator_minutes,
            clicks=10,
            panel_changes=2,
            commands_issued=4,
            cost_per_deliverable=1.0,
        ),
    )


def perfect_umh(n=20, evidence_class=EvidenceClass.A_PRODUCTION):
    return [make_result(task_id=f"u{i}", evidence_class=evidence_class) for i in range(n)]


def weak_umh(n, evidence_class=EvidenceClass.A_PRODUCTION):
    """Failing/weak UMH results."""
    return [
        make_result(
            task_id=f"w{i}",
            evidence_class=evidence_class,
            outcome=Outcome.FAILED,
            quality=10.0,
            verification_passed=False,
            cognitive_score=0.1,
            context_accuracy=0.1,
            work_recovery=False,
            resume_time=300.0,
            context_preserved=False,
            approvals_enforced=0,
            proof_generated=False,
            awareness=0.0,
            meta_ide=0.0,
            confidence_after=1,
            verification_needed=True,
            drift_detected=False,
            operator_minutes=120.0,
        )
        for i in range(n)
    ]


def legacy_baseline(n=20):
    """Mediocre legacy track results (no evidence weighting applies)."""
    return [
        make_result(
            task_id=f"l{i}",
            track=Track.A_LEGACY,
            evidence_class=EvidenceClass.A_PRODUCTION,
            quality=60.0,
            cognitive_score=0.4,
            context_accuracy=0.5,
            resume_time=120.0,
            awareness=0.3,
            meta_ide=0.2,
            confidence_after=3,
            verification_needed=True,
            operator_minutes=20.0,
        )
        for i in range(n)
    ]


# ===========================================================================
# weighted_mean / unweighted_mean
# ===========================================================================


class TestWeightedMean:
    def test_all_class_a_equals_simple_mean(self):
        rs = [
            make_result(quality=80.0, evidence_class=EvidenceClass.A_PRODUCTION),
            make_result(quality=100.0, evidence_class=EvidenceClass.A_PRODUCTION),
        ]
        val = weighted_mean(rs, lambda r: r.quality_score)
        assert val == pytest.approx(90.0)

    def test_all_class_c_equals_simple_mean(self):
        # Same weight cancels -> ratios preserved -> simple mean.
        rs = [
            make_result(quality=80.0, evidence_class=EvidenceClass.C_SYNTHETIC),
            make_result(quality=100.0, evidence_class=EvidenceClass.C_SYNTHETIC),
        ]
        assert weighted_mean(rs, lambda r: r.quality_score) == pytest.approx(90.0)

    def test_mixed_a_counts_more_than_c(self):
        # A weight 1.0 (value 100), C weight 0.125 (value 0).
        rs = [
            make_result(quality=100.0, evidence_class=EvidenceClass.A_PRODUCTION),
            make_result(quality=0.0, evidence_class=EvidenceClass.C_SYNTHETIC),
        ]
        val = weighted_mean(rs, lambda r: r.quality_score)
        # (100*1.0 + 0*0.125) / (1.0 + 0.125) = 100/1.125 ~= 88.9
        assert val == pytest.approx(100.0 / 1.125)
        assert val > 50.0  # A dominates

    def test_a_eight_times_c(self):
        assert (
            pytest.approx(1.0 / 0.125) == 8.0
        )  # weight ratio sanity

    def test_empty_list(self):
        assert weighted_mean([], lambda r: r.quality_score) == 0.0

    def test_none_extract_skipped(self):
        rs = [
            make_result(quality=100.0),
            make_result(quality=50.0),
        ]
        # Skip second result by returning None.
        val = weighted_mean(
            rs, lambda r: r.quality_score if r.quality_score > 60 else None
        )
        assert val == pytest.approx(100.0)

    def test_all_none_is_zero(self):
        rs = [make_result(), make_result()]
        assert weighted_mean(rs, lambda r: None) == 0.0


class TestUnweightedMean:
    def test_basic(self):
        assert unweighted_mean([1.0, 2.0, 3.0]) == pytest.approx(2.0)

    def test_empty(self):
        assert unweighted_mean([]) == 0.0


# ===========================================================================
# HarnessScorer — 10 dimensions
# ===========================================================================


class TestHarnessScorer:
    def test_compute_all_returns_ten_dimensions(self):
        s = HarnessScorer(legacy_baseline(), perfect_umh())
        dims = s.compute_all()
        assert set(dims.keys()) == set(HarnessScorer.DIMENSION_WEIGHTS.keys())
        assert len(dims) == 10

    def test_dimension_weights_sum_to_one(self):
        assert sum(HarnessScorer.DIMENSION_WEIGHTS.values()) == pytest.approx(1.0)

    def test_perfect_umh_capability_high(self):
        s = HarnessScorer([], perfect_umh())
        cap = s.compute_all()["capability"]
        assert cap["umh"] == pytest.approx(0.9)  # quality 90 / 100

    def test_perfect_umh_execution_is_one(self):
        s = HarnessScorer([], perfect_umh())
        assert s.compute_all()["execution"]["umh"] == pytest.approx(1.0)

    def test_failed_umh_execution_is_zero(self):
        s = HarnessScorer([], weak_umh(10))
        assert s.compute_all()["execution"]["umh"] == 0.0

    def test_cognitive_load_perfect(self):
        s = HarnessScorer([], [make_result(cognitive_score=1.0) for _ in range(5)])
        assert s.compute_all()["cognitive_load"]["umh"] == pytest.approx(1.0)

    def test_umh_beats_legacy_positive_delta(self):
        s = HarnessScorer(legacy_baseline(), perfect_umh())
        dims = s.compute_all()
        assert dims["cognitive_load"]["delta"] > 0
        assert dims["awareness"]["delta"] > 0

    def test_legacy_beats_umh_negative_delta(self):
        s = HarnessScorer(legacy_baseline(), weak_umh(10))
        dims = s.compute_all()
        assert dims["cognitive_load"]["delta"] < 0

    def test_missing_cognitive_load_handled(self):
        r = make_result()
        r.cognitive_load = None
        s = HarnessScorer([], [r])
        # No values -> weighted_mean returns 0.0, no error.
        assert s.compute_all()["cognitive_load"]["umh"] == 0.0

    def test_awareness_perfect(self):
        s = HarnessScorer([], [make_result(awareness=1.0) for _ in range(3)])
        assert s.compute_all()["awareness"]["umh"] == pytest.approx(1.0)

    def test_recovery_no_need_is_one(self):
        s = HarnessScorer([], [make_result(recovery_needed=False) for _ in range(3)])
        assert s.compute_all()["recovery"]["umh"] == pytest.approx(1.0)

    def test_recovery_failed_is_zero(self):
        rs = [
            make_result(recovery_needed=True, recovery_successful=False)
            for _ in range(3)
        ]
        s = HarnessScorer([], rs)
        assert s.compute_all()["recovery"]["umh"] == 0.0

    def test_meta_ide_perfect(self):
        s = HarnessScorer([], [make_result(meta_ide=1.0) for _ in range(3)])
        assert s.compute_all()["meta_ide"]["umh"] == pytest.approx(1.0)

    def test_cost_efficiency_no_legacy_baseline_neutral(self):
        s = HarnessScorer([], perfect_umh())
        ce = s.compute_all()["cost_efficiency"]
        assert ce["legacy"] == 0.5
        assert ce["umh"] == 0.5

    def test_cost_efficiency_cheaper_umh_wins(self):
        legacy = legacy_baseline()  # operator_minutes 20
        umh = [make_result(operator_minutes=2.0) for _ in range(5)]  # much cheaper
        s = HarnessScorer(legacy, umh)
        ce = s.compute_all()["cost_efficiency"]
        assert ce["umh"] > ce["legacy"]

    def test_cost_efficiency_expensive_umh_loses(self):
        legacy = legacy_baseline()  # operator_minutes 20
        umh = [make_result(operator_minutes=60.0) for _ in range(5)]
        s = HarnessScorer(legacy, umh)
        ce = s.compute_all()["cost_efficiency"]
        assert ce["umh"] < ce["legacy"]

    def test_composite_perfect_umh_high(self):
        s = HarnessScorer(legacy_baseline(), perfect_umh())
        comp = s.composite_score("umh")
        assert comp > 0.7

    def test_composite_legacy_track(self):
        s = HarnessScorer(legacy_baseline(), perfect_umh())
        assert 0.0 <= s.composite_score("legacy") <= 1.0

    def test_umh_wins_dict(self):
        s = HarnessScorer(legacy_baseline(), perfect_umh())
        wins = s.umh_wins()
        assert all(wins.values())

    def test_umh_wins_when_weak_loses(self):
        s = HarnessScorer(legacy_baseline(), weak_umh(10))
        wins = s.umh_wins()
        assert not all(wins.values())


# ===========================================================================
# HTICalculator — 11 components
# ===========================================================================


class TestHTICalculator:
    def test_compute_returns_eleven_components(self):
        hti = HTICalculator(perfect_umh())
        comps = hti.compute()
        assert set(comps.keys()) == set(HTICalculator.COMPONENT_WEIGHTS.keys())
        assert len(comps) == 11

    def test_component_weights_sum_to_one(self):
        assert sum(HTICalculator.COMPONENT_WEIGHTS.values()) == pytest.approx(1.0)

    def test_perfect_umh_hti_high(self):
        hti = HTICalculator(perfect_umh())
        # multi_machine is a fixed 0.5 placeholder, so max is below 100.
        assert hti.hti_score() > 85.0

    def test_all_failure_hti_low(self):
        hti = HTICalculator(weak_umh(10))
        assert hti.hti_score() < 30.0

    def test_empty_results_hti(self):
        hti = HTICalculator([])
        # multi_machine (0.5) and recovery_capability (1.0, no attempts) are the
        # only non-zero components: 0.5*0.05 + 1.0*0.05 = 0.075 -> HTI 7.5.
        score = hti.hti_score()
        assert score == pytest.approx(7.5)

    def test_execution_reliability_perfect(self):
        hti = HTICalculator(perfect_umh())
        assert hti.compute()["execution_reliability"] == pytest.approx(1.0)

    def test_execution_reliability_failed(self):
        hti = HTICalculator(weak_umh(5))
        assert hti.compute()["execution_reliability"] == 0.0

    def test_verification_coverage(self):
        rs = perfect_umh(4) + weak_umh(4)  # 4 with proof, 4 without
        hti = HTICalculator(rs)
        assert hti.compute()["verification_coverage"] == pytest.approx(0.5)

    def test_recovery_capability_no_attempts_is_one(self):
        hti = HTICalculator([make_result(recovery_needed=False) for _ in range(3)])
        assert hti.compute()["recovery_capability"] == 1.0

    def test_multi_machine_placeholder(self):
        hti = HTICalculator(perfect_umh())
        assert hti.compute()["multi_machine"] == 0.5

    def test_reality_correspondence_perfect(self):
        rs = [make_result(drift_present=True, drift_detected=True, false_positive=False) for _ in range(5)]
        hti = HTICalculator(rs)
        assert hti.compute()["reality_correspondence"] == pytest.approx(1.0)

    def test_operator_trust_high(self):
        rs = [make_result(confidence_after=5, verification_needed=False) for _ in range(5)]
        hti = HTICalculator(rs)
        assert hti.compute()["operator_trust"] == pytest.approx(1.0)


# ===========================================================================
# UMHMetricCalculator — 10 metrics
# ===========================================================================


class TestUMHMetricCalculator:
    def test_compute_all_returns_ten(self):
        calc = UMHMetricCalculator(perfect_umh(), WorkdayCoverage())
        metrics = calc.compute_all()
        assert set(metrics.keys()) == set(UMHMetricCalculator.TARGETS.keys())
        assert len(metrics) == 10

    def test_cpr_value(self):
        calc = UMHMetricCalculator(perfect_umh())
        assert calc.compute_all()["CPR"].value == pytest.approx(1.0)

    def test_rcr_value(self):
        calc = UMHMetricCalculator(perfect_umh())
        assert calc.compute_all()["RCR"].value == pytest.approx(1.0)

    def test_gcr_value(self):
        calc = UMHMetricCalculator(perfect_umh())
        assert calc.compute_all()["GCR"].value == pytest.approx(1.0)

    def test_vc_value(self):
        calc = UMHMetricCalculator(perfect_umh())
        assert calc.compute_all()["VC"].value == pytest.approx(1.0)

    def test_ttrc_median(self):
        rs = [make_result(resume_time=t) for t in (10.0, 20.0, 30.0)]
        calc = UMHMetricCalculator(rs)
        assert calc.compute_all()["TTRC"].value == pytest.approx(20.0)

    def test_oer_value(self):
        # 1 escape across 2 tools_used per result, 3 results -> 3/6 = 0.5
        rs = [
            make_result(
                tools_used=["a", "b"],
                escapes=[EscapeEvent(timestamp="t", tool="x", reason="r", could_cockpit_handle=False)],
            )
            for _ in range(3)
        ]
        calc = UMHMetricCalculator(rs)
        assert calc.compute_all()["OER"].value == pytest.approx(0.5)

    def test_oer_zero_escapes(self):
        calc = UMHMetricCalculator(perfect_umh())
        assert calc.compute_all()["OER"].value == 0.0

    def test_cls_value(self):
        calc = UMHMetricCalculator([make_result(cognitive_score=0.85) for _ in range(3)])
        assert calc.compute_all()["CLS"].value == pytest.approx(0.85)

    def test_irs_value(self):
        rs = [make_result(context_accuracy=1.0, work_recovery=True) for _ in range(3)]
        calc = UMHMetricCalculator(rs)
        assert calc.compute_all()["IRS"].value == pytest.approx(1.0)

    def test_ddc_from_workday(self):
        wd = WorkdayCoverage(coding=True, debugging=True, review=True, deployment=True)
        calc = UMHMetricCalculator(perfect_umh(), wd)
        assert calc.compute_all()["DDC"].value == pytest.approx(0.4)

    def test_ddc_no_workday_is_zero(self):
        calc = UMHMetricCalculator(perfect_umh())
        assert calc.compute_all()["DDC"].value == 0.0

    def test_ots_value(self):
        rs = [make_result(confidence_after=5) for _ in range(3)]
        calc = UMHMetricCalculator(rs)
        assert calc.compute_all()["OTS"].value == pytest.approx(1.0)

    # -- confidence --------------------------------------------------------

    def test_confidence_all_class_a_high(self):
        calc = UMHMetricCalculator(perfect_umh(10, EvidenceClass.A_PRODUCTION))
        assert calc.compute_all()["CPR"].confidence is EvidenceConfidence.HIGH

    def test_confidence_all_class_c_low(self):
        calc = UMHMetricCalculator(perfect_umh(10, EvidenceClass.C_SYNTHETIC))
        assert calc.compute_all()["CPR"].confidence is EvidenceConfidence.LOW

    def test_confidence_mixed_ab_medium_or_high(self):
        rs = perfect_umh(5, EvidenceClass.A_PRODUCTION) + perfect_umh(5, EvidenceClass.B_CONTROLLED)
        calc = UMHMetricCalculator(rs)
        conf = calc.compute_all()["CPR"].confidence
        assert conf in (EvidenceConfidence.MEDIUM, EvidenceConfidence.HIGH)

    def test_confidence_majority_b_medium(self):
        rs = perfect_umh(2, EvidenceClass.A_PRODUCTION) + perfect_umh(8, EvidenceClass.B_CONTROLLED)
        calc = UMHMetricCalculator(rs)
        # a/total = 0.2 < 0.5, (a+b)/total = 1.0 >= 0.5 -> MEDIUM
        assert calc.compute_all()["CPR"].confidence is EvidenceConfidence.MEDIUM

    # -- pass logic --------------------------------------------------------

    def test_all_pass_perfect(self):
        wd = WorkdayCoverage(
            coding=True, debugging=True, review=True, deployment=True,
            planning=True, continuity=True, documentation=True, approvals=True,
            knowledge_retrieval=True, runtime_inspection=True,
        )
        calc = UMHMetricCalculator(perfect_umh(), wd)
        assert calc.all_pass() is True

    def test_all_pass_false_when_one_fails(self):
        wd = WorkdayCoverage(coding=True)  # DDC = 0.1 < 0.80
        calc = UMHMetricCalculator(perfect_umh(), wd)
        assert calc.all_pass() is False

    def test_lower_is_better_ttrc(self):
        calc = UMHMetricCalculator(perfect_umh())
        # TTRC target 30, lower passes. resume_time 12 < 30.
        assert calc.metric_passes("TTRC", 12.0) is True
        assert calc.metric_passes("TTRC", 40.0) is False

    def test_lower_is_better_oer(self):
        calc = UMHMetricCalculator(perfect_umh())
        assert calc.metric_passes("OER", 0.05) is True
        assert calc.metric_passes("OER", 0.20) is False

    def test_higher_is_better_cpr(self):
        calc = UMHMetricCalculator(perfect_umh())
        assert calc.metric_passes("CPR", 0.96) is True
        assert calc.metric_passes("CPR", 0.90) is False


# ===========================================================================
# MVPVerdictEngine — evidence classification rules
# ===========================================================================


def full_workday() -> WorkdayCoverage:
    return WorkdayCoverage(
        coding=True, debugging=True, review=True, deployment=True,
        planning=True, continuity=True, documentation=True, approvals=True,
        knowledge_retrieval=True, runtime_inspection=True,
    )


def build_engine(umh, legacy, workday=None):
    if workday is None:
        workday = full_workday()
    scorer = HarnessScorer(legacy, umh)
    hti = HTICalculator(umh)
    metrics = UMHMetricCalculator(umh, workday)
    return MVPVerdictEngine(scorer, hti, metrics)


def verdict_value(verdict):
    """derive_verdict() stores verdict as a raw string; normalise to enum value."""
    v = verdict.verdict
    return v.value if hasattr(v, "value") else v


class TestRule1NoSyntheticOnly:
    def test_all_class_c_auto_fails_metrics(self):
        umh = perfect_umh(20, EvidenceClass.C_SYNTHETIC)
        metrics = UMHMetricCalculator(umh, full_workday())
        engine = build_engine(umh, legacy_baseline())
        synthetic_only = engine._validate_no_synthetic_only(metrics.compute_all())
        # Every metric drawing only on Class C runs has 0 A + 0 B -> all fail.
        assert len(synthetic_only) > 0

    def test_class_a_metric_not_flagged(self):
        umh = perfect_umh(20, EvidenceClass.A_PRODUCTION)
        metrics = UMHMetricCalculator(umh, full_workday())
        engine = build_engine(umh, legacy_baseline())
        synthetic_only = engine._validate_no_synthetic_only(metrics.compute_all())
        assert synthetic_only == []

    def test_all_synthetic_verdict_not_ready(self):
        umh = perfect_umh(20, EvidenceClass.C_SYNTHETIC)
        engine = build_engine(umh, legacy_baseline())
        assert verdict_value(engine.derive_verdict()) == MVPVerdictLevel.NOT_READY.value


class TestRule2LitmusTest:
    def test_litmus_passes_all_class_a(self):
        umh = perfect_umh(20, EvidenceClass.A_PRODUCTION)
        engine = build_engine(umh, legacy_baseline())
        assert engine._litmus_test(umh, legacy_baseline()) is True

    def test_litmus_passes_mostly_a_some_c(self):
        umh = perfect_umh(15, EvidenceClass.A_PRODUCTION) + perfect_umh(5, EvidenceClass.C_SYNTHETIC)
        engine = build_engine(umh, legacy_baseline())
        assert engine._litmus_test(umh, legacy_baseline()) is True

    def test_litmus_fails_insufficient_real_evidence(self):
        umh = perfect_umh(5, EvidenceClass.A_PRODUCTION) + perfect_umh(15, EvidenceClass.C_SYNTHETIC)
        engine = build_engine(umh, legacy_baseline())
        # Only 5 real runs < 15 MIN_PRODUCTION_RUNS.
        assert engine._litmus_test(umh, legacy_baseline()) is False

    def test_litmus_fails_all_synthetic(self):
        umh = perfect_umh(20, EvidenceClass.C_SYNTHETIC)
        engine = build_engine(umh, legacy_baseline())
        assert engine._litmus_test(umh, legacy_baseline()) is False


class TestRule3MinimumProductionEvidence:
    def test_fourteen_class_a_capped_partial(self):
        umh = perfect_umh(14, EvidenceClass.A_PRODUCTION)
        engine = build_engine(umh, legacy_baseline())
        v = verdict_value(engine.derive_verdict())
        # 14 < 15 MIN -> cannot exceed PARTIALLY_TRUSTED.
        order = [m.value for m in MVPVerdictEngine._ORDER]
        assert order.index(v) <= order.index(MVPVerdictLevel.PARTIALLY_TRUSTED.value)

    def test_fifteen_class_a_can_exceed_partial(self):
        umh = perfect_umh(20, EvidenceClass.A_PRODUCTION)
        engine = build_engine(umh, legacy_baseline())
        v = verdict_value(engine.derive_verdict())
        order = [m.value for m in MVPVerdictEngine._ORDER]
        assert order.index(v) > order.index(MVPVerdictLevel.PARTIALLY_TRUSTED.value)

    def test_ab_combined_meets_minimum(self):
        umh = perfect_umh(10, EvidenceClass.A_PRODUCTION) + perfect_umh(5, EvidenceClass.B_CONTROLLED)
        engine = build_engine(umh, legacy_baseline())
        v = verdict_value(engine.derive_verdict())
        order = [m.value for m in MVPVerdictEngine._ORDER]
        # 15 A+B runs -> not capped by Rule 3.
        assert order.index(v) > order.index(MVPVerdictLevel.PARTIALLY_TRUSTED.value)


class TestRule4SyntheticCannotLift:
    def test_decisive_from_ab_only(self):
        umh = perfect_umh(20, EvidenceClass.A_PRODUCTION)
        engine = build_engine(umh, legacy_baseline())
        decisive = engine._synthetic_cannot_lift(umh, legacy_baseline())
        order = [m.value for m in MVPVerdictEngine._ORDER]
        assert order.index(decisive.value) > order.index(MVPVerdictLevel.PARTIALLY_TRUSTED.value)

    def test_no_ab_returns_not_ready(self):
        umh = perfect_umh(20, EvidenceClass.C_SYNTHETIC)
        engine = build_engine(umh, legacy_baseline())
        assert engine._synthetic_cannot_lift(umh, legacy_baseline()) is MVPVerdictLevel.NOT_READY

    def test_synthetic_does_not_lift_weak_real(self):
        # 5 weak real + 15 strong synthetic. Real evidence is weak + below min.
        umh = weak_umh(5, EvidenceClass.A_PRODUCTION) + perfect_umh(15, EvidenceClass.C_SYNTHETIC)
        engine = build_engine(umh, legacy_baseline())
        v = verdict_value(engine.derive_verdict())
        order = [m.value for m in MVPVerdictEngine._ORDER]
        assert order.index(v) <= order.index(MVPVerdictLevel.PARTIALLY_TRUSTED.value)


class TestVerdictLevels:
    def test_certified_daily_driver(self):
        umh = perfect_umh(25, EvidenceClass.A_PRODUCTION)
        engine = build_engine(umh, legacy_baseline())
        assert verdict_value(engine.derive_verdict()) == MVPVerdictLevel.CERTIFIED_DAILY_DRIVER.value

    def test_not_ready_all_failure(self):
        umh = weak_umh(20, EvidenceClass.A_PRODUCTION)
        engine = build_engine(umh, legacy_baseline())
        assert verdict_value(engine.derive_verdict()) == MVPVerdictLevel.NOT_READY.value

    def test_base_verdict_certified(self):
        umh = perfect_umh(25, EvidenceClass.A_PRODUCTION)
        engine = build_engine(umh, legacy_baseline())
        dims = engine._scorer.compute_all()
        hti = engine._hti.hti_score()
        metrics = engine._metrics.compute_all()
        assert engine._base_verdict(hti, dims, metrics) == MVPVerdictLevel.CERTIFIED_DAILY_DRIVER

    def test_base_verdict_not_ready(self):
        umh = weak_umh(20, EvidenceClass.A_PRODUCTION)
        engine = build_engine(umh, legacy_baseline())
        dims = engine._scorer.compute_all()
        hti = engine._hti.hti_score()
        metrics = engine._metrics.compute_all()
        assert engine._base_verdict(hti, dims, metrics) == MVPVerdictLevel.NOT_READY


class TestGoldenTest:
    def test_verdict_unchanged_when_synthetic_removed(self):
        """The litmus standard: removing synthetic runs must not change verdict."""
        real = perfect_umh(25, EvidenceClass.A_PRODUCTION)
        synthetic = perfect_umh(15, EvidenceClass.C_SYNTHETIC)
        legacy = legacy_baseline()

        with_synthetic = verdict_value(build_engine(real + synthetic, legacy).derive_verdict())
        without_synthetic = verdict_value(build_engine(real, legacy).derive_verdict())

        assert with_synthetic == without_synthetic
        assert with_synthetic == MVPVerdictLevel.CERTIFIED_DAILY_DRIVER.value

    def test_synthetic_addition_cannot_raise_verdict(self):
        # Strong synthetic added to insufficient real evidence cannot lift it.
        real = perfect_umh(10, EvidenceClass.A_PRODUCTION)  # below min 15
        synthetic = perfect_umh(20, EvidenceClass.C_SYNTHETIC)
        legacy = legacy_baseline()

        without = verdict_value(build_engine(real, legacy).derive_verdict())
        with_syn = verdict_value(build_engine(real + synthetic, legacy).derive_verdict())

        order = [m.value for m in MVPVerdictEngine._ORDER]
        assert order.index(with_syn) <= order.index(without) or with_syn == without


class TestVerdictEdgeCases:
    def test_empty_results_not_ready(self):
        engine = build_engine([], [])
        assert verdict_value(engine.derive_verdict()) == MVPVerdictLevel.NOT_READY.value

    def test_single_result_no_error(self):
        engine = build_engine([make_result()], [make_result(track=Track.A_LEGACY)])
        v = engine.derive_verdict()
        assert verdict_value(v) in [m.value for m in MVPVerdictLevel]

    def test_evidence_summary_populated(self):
        umh = perfect_umh(20, EvidenceClass.A_PRODUCTION)
        engine = build_engine(umh, legacy_baseline())
        v = engine.derive_verdict()
        assert "HTI" in v.evidence_summary
        assert "verdict" in v.evidence_summary.lower()

    def test_results_with_no_optional_tests(self):
        rs = [
            TrackResult(
                task_id=f"t{i}",
                track=Track.B_UMH,
                evidence_class=EvidenceClass.A_PRODUCTION,
                started_at="s",
                completed_at="c",
                duration_seconds=1.0,
                outcome=Outcome.SUCCESS,
                verification_passed=True,
            )
            for i in range(20)
        ]
        engine = build_engine(rs, [])
        # Missing sub-results -> dimensions return 0.0, no crash.
        v = engine.derive_verdict()
        assert verdict_value(v) in [m.value for m in MVPVerdictLevel]
