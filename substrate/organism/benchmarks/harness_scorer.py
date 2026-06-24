"""C29 Harness Superiority — Scoring engine.

Computes all comparative, HTI, UMH-metric, and MVP-verdict scoring for the
C29 Harness Superiority benchmark. Every formula is deterministic — zero LLM
calls in measurement. Track A (Legacy) uses unweighted means; Track B (UMH)
uses evidence-weighted means (Class A=1.0, B=0.625, C=0.125).

Reuses the weighted-scoring pattern from composite_scorer.py (C23B).
"""

from __future__ import annotations

import logging
import statistics
from typing import Any, Callable

from substrate.organism.benchmarks.harness_superiority import (
    EVIDENCE_WEIGHTS,
    EvidenceClass,
    EvidenceConfidence,
    MetricWithConfidence,
    MVPTrustVerdict,
    MVPVerdictLevel,
    TrackResult,
    WorkdayCoverage,
)

logger = logging.getLogger(__name__)


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def weighted_mean(results: list[TrackResult], extract_fn: Callable[[TrackResult], float | None]) -> float:
    """Evidence-weighted mean. Class A=1.0, B=0.625, C=0.125. Skips None values."""
    total_weight = 0.0
    weighted_sum = 0.0
    for r in results:
        val = extract_fn(r)
        if val is None:
            continue
        w = EVIDENCE_WEIGHTS.get(r.evidence_class, 0.125)
        weighted_sum += val * w
        total_weight += w
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def unweighted_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _extract_values(results: list[TrackResult], extract_fn: Callable[[TrackResult], float | None]) -> list[float]:
    """Collect non-None extracted values (for unweighted legacy means)."""
    out: list[float] = []
    for r in results:
        val = extract_fn(r)
        if val is not None:
            out.append(val)
    return out


# ---------------------------------------------------------------------------
# Per-result extractors — shared by HarnessScorer dimensions and HTI/metrics.
# Each returns None when the relevant sub-result is absent, so the value is
# skipped from the mean rather than counted as zero.
# ---------------------------------------------------------------------------

def _x_capability(r: TrackResult) -> float | None:
    if r.outcome == "SUCCESS":
        return r.quality_score / 100.0
    return r.quality_score / 200.0


def _x_execution(r: TrackResult) -> float | None:
    success = 1.0 if r.outcome == "SUCCESS" else 0.0
    verified = 1.0 if r.verification_passed else 0.0
    return success * verified


def _x_cognitive_load(r: TrackResult) -> float | None:
    if r.cognitive_load is None:
        return None
    return r.cognitive_load.cognitive_load_score


def _x_interruption(r: TrackResult) -> float | None:
    if r.interruption_test is None:
        return None
    recovery = 1.0 if r.interruption_test.work_recovery_complete else 0.0
    return r.interruption_test.context_accuracy * recovery


def _x_continuity(r: TrackResult) -> float | None:
    if r.continuity_test is None:
        return None
    preserved = 1.0 if r.continuity_test.context_preserved else 0.0
    resume = max(r.continuity_test.resume_time_seconds, 1.0)
    return preserved * min(30.0 / resume, 1.0)


def _x_governance(r: TrackResult) -> float | None:
    if r.governance_test is None:
        return None
    required = max(r.governance_test.approvals_required, 1)
    enforced_rate = r.governance_test.approvals_enforced / required
    proof = 1.0 if r.governance_test.proof_generated else 0.0
    return enforced_rate * proof


def _x_awareness(r: TrackResult) -> float | None:
    if r.awareness_snapshot is None:
        return None
    return r.awareness_snapshot.awareness_score


def _x_recovery(r: TrackResult) -> float | None:
    if r.recovery_needed:
        return 1.0 if r.recovery_successful else 0.0
    return 1.0


def _x_meta_ide(r: TrackResult) -> float | None:
    if r.meta_ide_test is None:
        return None
    return r.meta_ide_test.meta_ide_score


def _x_cost(r: TrackResult) -> float | None:
    if r.resource_cost is None:
        return None
    return r.resource_cost.operator_minutes


# ---------------------------------------------------------------------------
# HarnessScorer — 10 comparative dimensions (Legacy vs UMH).
# ---------------------------------------------------------------------------

class HarnessScorer:
    """Computes 10 comparative scores between Track A (Legacy) and Track B (UMH).

    Legacy results use unweighted means (no evidence class weighting applies).
    UMH results use evidence-weighted means.
    """

    DIMENSION_WEIGHTS: dict[str, float] = {
        "capability": 0.12,
        "execution": 0.10,
        "cognitive_load": 0.15,
        "interruption_resistance": 0.15,
        "continuity": 0.12,
        "governance": 0.08,
        "awareness": 0.05,
        "recovery": 0.05,
        "meta_ide": 0.08,
        "cost_efficiency": 0.10,
    }

    def __init__(self, legacy_results: list[TrackResult], umh_results: list[TrackResult]) -> None:
        self._legacy = legacy_results
        self._umh = umh_results

    # -- generic helpers --------------------------------------------------

    def _legacy_score(self, extract_fn: Callable[[TrackResult], float | None]) -> float:
        return unweighted_mean(_extract_values(self._legacy, extract_fn))

    def _umh_score(self, extract_fn: Callable[[TrackResult], float | None]) -> float:
        return weighted_mean(self._umh, extract_fn)

    def _pair(self, extract_fn: Callable[[TrackResult], float | None]) -> tuple[float, float]:
        return self._legacy_score(extract_fn), self._umh_score(extract_fn)

    # -- the 10 dimensions ------------------------------------------------

    def _score_capability(self) -> tuple[float, float]:
        return self._pair(_x_capability)

    def _score_execution(self) -> tuple[float, float]:
        # Execution = success_rate * verification_rate; modeled per-result as
        # (success AND verified). Track-level mean of that product.
        return self._pair(_x_execution)

    def _score_cognitive_load(self) -> tuple[float, float]:
        return self._pair(_x_cognitive_load)

    def _score_interruption_resistance(self) -> tuple[float, float]:
        return self._pair(_x_interruption)

    def _score_continuity(self) -> tuple[float, float]:
        return self._pair(_x_continuity)

    def _score_governance(self) -> tuple[float, float]:
        return self._pair(_x_governance)

    def _score_awareness(self) -> tuple[float, float]:
        return self._pair(_x_awareness)

    def _score_recovery(self) -> tuple[float, float]:
        return self._pair(_x_recovery)

    def _score_meta_ide(self) -> tuple[float, float]:
        return self._pair(_x_meta_ide)

    def _score_cost_efficiency(self) -> tuple[float, float]:
        """Lower operator cost per deliverable is better.

        UMH cost-efficiency = 1.0 - clamp(umh_cost / legacy_cost, 0, 2) / 2.
        Legacy is the baseline reference (efficiency 0.5 by construction).
        """
        legacy_cost = self._legacy_score(_x_cost)
        umh_cost = self._umh_score(_x_cost)
        if legacy_cost <= 0:
            # No legacy cost baseline — treat both as neutral.
            return 0.5, 0.5
        legacy_eff = 0.5
        ratio = clamp(umh_cost / max(legacy_cost, 0.01), 0.0, 2.0)
        umh_eff = 1.0 - ratio / 2.0
        return legacy_eff, umh_eff

    # -- aggregation ------------------------------------------------------

    def compute_all(self) -> dict[str, dict[str, float]]:
        """Returns {dimension: {legacy, umh, delta, weight}}."""
        dims: dict[str, dict[str, float]] = {}
        for name in self.DIMENSION_WEIGHTS:
            method = getattr(self, f"_score_{name}")
            legacy_score, umh_score = method()
            dims[name] = {
                "legacy": round(legacy_score, 4),
                "umh": round(umh_score, 4),
                "delta": round(umh_score - legacy_score, 4),
                "weight": self.DIMENSION_WEIGHTS[name],
            }
        return dims

    def composite_score(self, track: str = "umh") -> float:
        """Weighted composite across all 10 dimensions for the given track."""
        dims = self.compute_all()
        total = sum(d[track] * d["weight"] for d in dims.values())
        return round(total, 4)

    def umh_wins(self) -> dict[str, bool]:
        """Per-dimension: does UMH meet-or-exceed Legacy?"""
        dims = self.compute_all()
        return {name: d["umh"] >= d["legacy"] for name, d in dims.items()}


# ---------------------------------------------------------------------------
# HTICalculator — Harness Trustworthiness Index (Track B only, 11 components).
# ---------------------------------------------------------------------------

class HTICalculator:
    """Harness Trustworthiness Index — computed from Track B (UMH) results only."""

    COMPONENT_WEIGHTS: dict[str, float] = {
        "execution_reliability": 0.15,
        "continuity": 0.15,
        "cognitive_load": 0.15,
        "reality_correspondence": 0.10,
        "governance": 0.10,
        "verification_coverage": 0.10,
        "recovery_capability": 0.05,
        "workspace_awareness": 0.05,
        "meta_ide": 0.05,
        "multi_machine": 0.05,
        "operator_trust": 0.05,
    }

    def __init__(self, umh_results: list[TrackResult]) -> None:
        self._results = umh_results

    def _execution_reliability(self) -> float:
        if not self._results:
            return 0.0
        success_rate = unweighted_mean(
            [1.0 if r.outcome == "SUCCESS" else 0.0 for r in self._results]
        )
        verification_rate = unweighted_mean(
            [1.0 if r.verification_passed else 0.0 for r in self._results]
        )
        return success_rate * verification_rate

    def _continuity(self) -> float:
        preserved = weighted_mean(
            self._results,
            lambda r: (1.0 if r.continuity_test.context_preserved else 0.0)
            if r.continuity_test else None,
        )
        ttrcs = [
            r.continuity_test.resume_time_seconds
            for r in self._results
            if r.continuity_test is not None
        ]
        if not ttrcs:
            return 0.0
        mean_ttrc = max(unweighted_mean(ttrcs), 1.0)
        return preserved * clamp(30.0 / mean_ttrc, 0.0, 1.0)

    def _cognitive_load(self) -> float:
        return weighted_mean(self._results, _x_cognitive_load)

    def _reality_correspondence(self) -> float:
        drifts = [r for r in self._results if r.reality_drift is not None]
        if not drifts:
            return 0.0
        present = [r for r in drifts if r.reality_drift.drift_present]
        if not present:
            # Checked and found no drift — system matches reality
            false_positive_rate = unweighted_mean(
                [1.0 if r.reality_drift.false_positive else 0.0 for r in drifts]
            )
            return clamp(1.0 - false_positive_rate, 0.0, 1.0)
        detected_rate = unweighted_mean(
            [1.0 if r.reality_drift.drift_detected else 0.0 for r in present]
        )
        false_positive_rate = unweighted_mean(
            [1.0 if r.reality_drift.false_positive else 0.0 for r in drifts]
        )
        return clamp(detected_rate - false_positive_rate, 0.0, 1.0)

    def _governance(self) -> float:
        return weighted_mean(self._results, _x_governance)

    def _verification_coverage(self) -> float:
        if not self._results:
            return 0.0
        with_proof = sum(
            1 for r in self._results
            if r.governance_test is not None and r.governance_test.proof_generated
        )
        return with_proof / len(self._results)

    def _recovery_capability(self) -> float:
        attempts = [r for r in self._results if r.recovery_needed]
        if not attempts:
            return 1.0
        successful = sum(1 for r in attempts if r.recovery_successful)
        return successful / len(attempts)

    def _workspace_awareness(self) -> float:
        return weighted_mean(self._results, _x_awareness)

    def _meta_ide(self) -> float:
        return weighted_mean(self._results, _x_meta_ide)

    def _multi_machine(self) -> float:
        # Placeholder until multi-machine telemetry lands (beast_connected_rate).
        return 0.5

    def _operator_trust(self) -> float:
        confidence = weighted_mean(
            self._results,
            lambda r: r.operator_trust.confidence_after / 5.0 if r.operator_trust else None,
        )
        trust_results = [r for r in self._results if r.operator_trust is not None]
        if not trust_results:
            return 0.0
        double_check_rate = unweighted_mean(
            [1.0 if r.operator_trust.verification_needed else 0.0 for r in trust_results]
        )
        return confidence * (1.0 - double_check_rate)

    def compute(self) -> dict[str, float]:
        """Returns {component: score} for all 11 components."""
        return {
            "execution_reliability": self._execution_reliability(),
            "continuity": self._continuity(),
            "cognitive_load": self._cognitive_load(),
            "reality_correspondence": self._reality_correspondence(),
            "governance": self._governance(),
            "verification_coverage": self._verification_coverage(),
            "recovery_capability": self._recovery_capability(),
            "workspace_awareness": self._workspace_awareness(),
            "meta_ide": self._meta_ide(),
            "multi_machine": self._multi_machine(),
            "operator_trust": self._operator_trust(),
        }

    def hti_score(self) -> float:
        """Weighted HTI score, 0-100."""
        components = self.compute()
        total = sum(components[k] * self.COMPONENT_WEIGHTS[k] for k in self.COMPONENT_WEIGHTS)
        return round(total * 100, 2)


# ---------------------------------------------------------------------------
# UMHMetricCalculator — 10 UMH-specific metrics with targets + confidence.
# ---------------------------------------------------------------------------

class UMHMetricCalculator:
    """Computes 10 UMH-specific metrics with targets and evidence confidence."""

    TARGETS: dict[str, float] = {
        "CPR": 0.95,
        "RCR": 0.95,
        "GCR": 0.90,
        "VC": 0.95,
        "TTRC": 30.0,
        "OER": 0.10,
        "CLS": 0.80,
        "IRS": 0.85,
        "DDC": 0.80,
        "OTS": 0.80,
    }

    # Metrics where a LOWER value passes the target (TTRC seconds, OER rate).
    LOWER_IS_BETTER = {"TTRC", "OER"}

    def __init__(
        self,
        umh_results: list[TrackResult],
        workday_coverage: WorkdayCoverage | None = None,
    ) -> None:
        self._results = umh_results
        self._workday = workday_coverage

    # -- confidence -------------------------------------------------------

    def _compute_confidence(
        self, results_used: list[TrackResult]
    ) -> tuple[EvidenceConfidence, int, int, int]:
        a = sum(1 for r in results_used if r.evidence_class == EvidenceClass.A_PRODUCTION)
        b = sum(1 for r in results_used if r.evidence_class == EvidenceClass.B_CONTROLLED)
        c = sum(1 for r in results_used if r.evidence_class == EvidenceClass.C_SYNTHETIC)
        total = a + b + c
        if total == 0:
            return EvidenceConfidence.LOW, 0, 0, 0
        if a / total >= 0.5:
            return EvidenceConfidence.HIGH, a, b, c
        if (a + b) / total >= 0.5:
            return EvidenceConfidence.MEDIUM, a, b, c
        return EvidenceConfidence.LOW, a, b, c

    def _build(
        self,
        name: str,
        value: float,
        results_used: list[TrackResult],
    ) -> MetricWithConfidence:
        confidence, a, b, c = self._compute_confidence(results_used)
        return MetricWithConfidence(
            name=name,
            value=round(value, 4),
            confidence=confidence,
            class_a_count=a,
            class_b_count=b,
            class_c_count=c,
        )

    # -- individual metrics ----------------------------------------------

    def _cpr(self) -> MetricWithConfidence:
        used = [r for r in self._results if r.continuity_test is not None]
        if not used:
            return self._build("CPR", 0.0, [])
        preserved = sum(1 for r in used if r.continuity_test.context_preserved)
        return self._build("CPR", preserved / len(used), used)

    def _rcr(self) -> MetricWithConfidence:
        checked = [r for r in self._results if r.reality_drift is not None]
        present = [r for r in checked if r.reality_drift.drift_present]
        if not checked:
            return self._build("RCR", 0.0, [])
        if not present:
            # System was checked and found no drift — 100% correspondence
            return self._build("RCR", 1.0, checked)
        detected = sum(1 for r in present if r.reality_drift.drift_detected)
        return self._build("RCR", detected / len(present), present)

    def _gcr(self) -> MetricWithConfidence:
        used = [r for r in self._results if r.governance_test is not None]
        required = sum(r.governance_test.approvals_required for r in used)
        if required <= 0:
            return self._build("GCR", 0.0, used)
        enforced = sum(r.governance_test.approvals_enforced for r in used)
        return self._build("GCR", enforced / required, used)

    def _vc(self) -> MetricWithConfidence:
        if not self._results:
            return self._build("VC", 0.0, [])
        with_proof = sum(
            1 for r in self._results
            if r.governance_test is not None and r.governance_test.proof_generated
        )
        return self._build("VC", with_proof / len(self._results), self._results)

    def _ttrc(self) -> MetricWithConfidence:
        used = [r for r in self._results if r.continuity_test is not None]
        times = [r.continuity_test.resume_time_seconds for r in used]
        if not times:
            return self._build("TTRC", 0.0, [])
        return self._build("TTRC", statistics.median(times), used)

    def _oer(self) -> MetricWithConfidence:
        total_escapes = sum(len(r.escapes) for r in self._results)
        total_interactions = sum(
            max(len(r.tools_used), 1) for r in self._results
        )
        if total_interactions <= 0:
            return self._build("OER", 0.0, self._results)
        return self._build("OER", total_escapes / total_interactions, self._results)

    def _cls(self) -> MetricWithConfidence:
        used = [r for r in self._results if r.cognitive_load is not None]
        value = weighted_mean(self._results, _x_cognitive_load)
        return self._build("CLS", value, used)

    def _irs(self) -> MetricWithConfidence:
        used = [r for r in self._results if r.interruption_test is not None]
        value = weighted_mean(self._results, _x_interruption)
        return self._build("IRS", value, used)

    def _ddc(self) -> MetricWithConfidence:
        value = self._workday.coverage_score if self._workday is not None else 0.0
        # DDC is an aggregate over all runs; confidence drawn from full corpus.
        return self._build("DDC", value, self._results)

    def _ots(self) -> MetricWithConfidence:
        used = [r for r in self._results if r.operator_trust is not None]
        value = weighted_mean(
            self._results,
            lambda r: r.operator_trust.confidence_after / 5.0 if r.operator_trust else None,
        )
        return self._build("OTS", value, used)

    def compute_all(self) -> dict[str, MetricWithConfidence]:
        """Returns all 10 metrics with evidence confidence."""
        return {
            "CPR": self._cpr(),
            "RCR": self._rcr(),
            "GCR": self._gcr(),
            "VC": self._vc(),
            "TTRC": self._ttrc(),
            "OER": self._oer(),
            "CLS": self._cls(),
            "IRS": self._irs(),
            "DDC": self._ddc(),
            "OTS": self._ots(),
        }

    def metric_passes(self, name: str, value: float) -> bool:
        target = self.TARGETS[name]
        if name in self.LOWER_IS_BETTER:
            return value < target
        return value >= target

    def all_pass(self) -> bool:
        """Check if all 10 metrics meet their targets."""
        metrics = self.compute_all()
        return all(self.metric_passes(name, m.value) for name, m in metrics.items())

    def pass_report(self) -> dict[str, dict[str, Any]]:
        """Per-metric: value, target, passed, confidence."""
        metrics = self.compute_all()
        report: dict[str, dict[str, Any]] = {}
        for name, m in metrics.items():
            report[name] = {
                "value": m.value,
                "target": self.TARGETS[name],
                "passed": self.metric_passes(name, m.value),
                "confidence": m.confidence.value if hasattr(m.confidence, "value") else str(m.confidence),
                "class_a": m.class_a_count,
                "class_b": m.class_b_count,
                "class_c": m.class_c_count,
            }
        return report


# ---------------------------------------------------------------------------
# MVPVerdictEngine — verdict derivation + 4 hard evidence rules.
# ---------------------------------------------------------------------------

class MVPVerdictEngine:
    """Derives the MVP Trust Verdict from scores with evidence classification rules."""

    MIN_PRODUCTION_RUNS = 15

    def __init__(
        self,
        harness_scorer: HarnessScorer,
        hti_calculator: HTICalculator,
        metric_calculator: UMHMetricCalculator,
    ) -> None:
        self._scorer = harness_scorer
        self._hti = hti_calculator
        self._metrics = metric_calculator

    # -- base verdict (scores only) --------------------------------------

    def _base_verdict(
        self,
        hti: float,
        dims: dict[str, dict[str, float]],
        metrics: dict[str, MetricWithConfidence],
    ) -> MVPVerdictLevel:
        """Deterministic verdict from scores only."""
        wins = {name: d["umh"] >= d["legacy"] for name, d in dims.items()}
        all_pass = all(wins.values())
        win_count = sum(1 for v in wins.values() if v)
        most_pass = win_count >= (len(wins) * 0.7)

        cls = metrics["CLS"].value
        irs = metrics["IRS"].value
        ddc = metrics["DDC"].value
        ots = metrics["OTS"].value

        exec_pass = wins.get("execution", False)
        capability_pass = wins.get("capability", False)

        # CERTIFIED_DAILY_DRIVER
        if (
            hti > 90
            and all_pass
            and cls > 0.80
            and irs > 0.85
            and ddc > 0.80
            and ots > 0.80
        ):
            return MVPVerdictLevel.CERTIFIED_DAILY_DRIVER

        # PRIMARY_WORKSTATION
        if hti > 85 and most_pass and cls > 0.70 and irs > 0.75:
            return MVPVerdictLevel.PRIMARY_WORKSTATION

        # PARTIALLY_TRUSTED
        if hti > 75 and exec_pass and capability_pass:
            return MVPVerdictLevel.PARTIALLY_TRUSTED

        return MVPVerdictLevel.NOT_READY

    # -- Rule 1: no synthetic-only metrics -------------------------------

    def _validate_no_synthetic_only(
        self, metrics: dict[str, MetricWithConfidence]
    ) -> list[str]:
        """Any metric with 0 Class A + 0 Class B runs = auto-fail."""
        failures: list[str] = []
        for name, m in metrics.items():
            if m.class_a_count == 0 and m.class_b_count == 0:
                failures.append(name)
        return failures

    # -- Rule 2: litmus test (remove Class C, must hold at PRIMARY) -------

    def _litmus_test(
        self,
        umh_results: list[TrackResult],
        legacy_results: list[TrackResult],
    ) -> bool:
        """Re-derive verdict with all Class C runs removed.

        Must hold at PRIMARY_WORKSTATION or better with real evidence only.
        """
        real_umh = [r for r in umh_results if r.evidence_class != EvidenceClass.C_SYNTHETIC]
        real_legacy = [r for r in legacy_results if r.evidence_class != EvidenceClass.C_SYNTHETIC]
        if len(real_umh) < self.MIN_PRODUCTION_RUNS:
            return False
        real_scorer = HarnessScorer(real_legacy, real_umh)
        real_hti = HTICalculator(real_umh)
        real_metrics = UMHMetricCalculator(real_umh, self._metrics._workday)
        real_verdict = self._base_verdict(
            real_hti.hti_score(),
            real_scorer.compute_all(),
            real_metrics.compute_all(),
        )
        return real_verdict in (
            MVPVerdictLevel.PRIMARY_WORKSTATION,
            MVPVerdictLevel.CERTIFIED_DAILY_DRIVER,
        )

    # -- Rule 4: synthetic cannot lift (decisive A+B-only verdict) -------

    def _synthetic_cannot_lift(
        self,
        umh_results: list[TrackResult],
        legacy_results: list[TrackResult],
    ) -> MVPVerdictLevel:
        """Compute the decisive verdict from A+B evidence only."""
        ab_umh = [r for r in umh_results if r.evidence_class != EvidenceClass.C_SYNTHETIC]
        ab_legacy = [r for r in legacy_results if r.evidence_class != EvidenceClass.C_SYNTHETIC]
        if not ab_umh:
            return MVPVerdictLevel.NOT_READY
        ab_scorer = HarnessScorer(ab_legacy, ab_umh)
        ab_hti = HTICalculator(ab_umh)
        ab_metrics = UMHMetricCalculator(ab_umh, self._metrics._workday)
        return self._base_verdict(
            ab_hti.hti_score(),
            ab_scorer.compute_all(),
            ab_metrics.compute_all(),
        )

    # -- verdict ordering helpers ----------------------------------------

    _ORDER = [
        MVPVerdictLevel.NOT_READY,
        MVPVerdictLevel.PARTIALLY_TRUSTED,
        MVPVerdictLevel.PRIMARY_WORKSTATION,
        MVPVerdictLevel.CERTIFIED_DAILY_DRIVER,
    ]

    def _rank(self, verdict: MVPVerdictLevel) -> int:
        return self._ORDER.index(verdict)

    def _min_verdict(self, a: MVPVerdictLevel, b: MVPVerdictLevel) -> MVPVerdictLevel:
        return a if self._rank(a) <= self._rank(b) else b

    # -- final derivation -------------------------------------------------

    def derive_verdict(self) -> MVPTrustVerdict:
        """Full verdict derivation with all 4 hard rules applied."""
        umh_results = self._hti._results
        legacy_results = self._scorer._legacy
        dims = self._scorer.compute_all()
        hti = self._hti.hti_score()
        metrics = self._metrics.compute_all()

        notes: list[str] = []

        # Base verdict (all evidence, for reference/diagnostics).
        base = self._base_verdict(hti, dims, metrics)

        # Rule 4: decisive verdict from A+B evidence only.
        decisive = self._synthetic_cannot_lift(umh_results, legacy_results)
        final = decisive
        if self._rank(base) > self._rank(decisive):
            notes.append(
                "Synthetic evidence cannot lift verdict: capped at A+B-only "
                f"verdict ({decisive.value})."
            )

        # Rule 1: no synthetic-only metrics.
        synthetic_only = self._validate_no_synthetic_only(metrics)
        if synthetic_only:
            notes.append(
                "Auto-fail metrics with no Class A/B evidence: "
                + ", ".join(synthetic_only) + "."
            )
            final = MVPVerdictLevel.NOT_READY

        # Rule 3: minimum 15 Class A+B runs for any verdict above PARTIALLY.
        ab_count = sum(
            1 for r in umh_results if r.evidence_class != EvidenceClass.C_SYNTHETIC
        )
        if ab_count < self.MIN_PRODUCTION_RUNS:
            if self._rank(final) > self._rank(MVPVerdictLevel.PARTIALLY_TRUSTED):
                notes.append(
                    f"Insufficient production evidence ({ab_count} Class A+B runs, "
                    f"need {self.MIN_PRODUCTION_RUNS}): capped at PARTIALLY_TRUSTED."
                )
            final = self._min_verdict(final, MVPVerdictLevel.PARTIALLY_TRUSTED)

        # Rule 2: litmus test.
        if not self._litmus_test(umh_results, legacy_results):
            if self._rank(final) > self._rank(MVPVerdictLevel.PARTIALLY_TRUSTED):
                notes.append(
                    "Verdict downgraded: would not hold without synthetic evidence."
                )
            final = self._min_verdict(final, MVPVerdictLevel.PARTIALLY_TRUSTED)

        evidence_summary = self._build_summary(hti, dims, metrics, base, final, notes)

        return MVPTrustVerdict(
            would_choose_first="",
            would_stay_in="",
            trusts_with_production="",
            recommends_replacing_legacy="",
            projection_acceleration_justified="",
            verdict=final.value,
            evidence_summary=evidence_summary,
        )

    def _build_summary(
        self,
        hti: float,
        dims: dict[str, dict[str, float]],
        metrics: dict[str, MetricWithConfidence],
        base: MVPVerdictLevel,
        final: MVPVerdictLevel,
        notes: list[str],
    ) -> str:
        win_count = sum(1 for d in dims.values() if d["umh"] >= d["legacy"])
        parts = [
            f"HTI {hti:.1f}; UMH meets-or-exceeds Legacy on {win_count}/{len(dims)} "
            f"comparative dimensions; CLS {metrics['CLS'].value:.2f}, "
            f"IRS {metrics['IRS'].value:.2f}, DDC {metrics['DDC'].value:.2f}, "
            f"OTS {metrics['OTS'].value:.2f}.",
            f"Base verdict {base.value}; final verdict {final.value} after "
            f"evidence rules.",
        ]
        if notes:
            parts.append(" ".join(notes))
        return " ".join(parts)
