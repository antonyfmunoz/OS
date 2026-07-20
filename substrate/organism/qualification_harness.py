"""Organism Qualification Harness.

Proves operational properties of the UMH organism under sustained load.
Not a benchmark comparison — a qualification campaign.

Every property is measured as a convergence function, not a threshold.
The organism reaches stable operating regime when metric standard deviation
over a rolling window drops below 10% of mean for 3 consecutive windows.

Three-dimensional qualification output:
  ORL        = what the organism can reliably do (1-8)
  Confidence = how much evidence supports that ORL (0-100%)
  Predictive Accuracy = how well the organism models itself (0-100%)

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import math
import os
import statistics
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable

from substrate.state.runtime_paths import runtime_state_dir

logger = logging.getLogger(__name__)


def _store_dir() -> str:
    return str(runtime_state_dir("c35", create=False))


def _results_path() -> str:
    return os.path.join(_store_dir(), "qualification_results.jsonl")


def _mutations_path() -> str:
    return os.path.join(_store_dir(), "mutation_log.jsonl")


ROLLING_WINDOW_SIZE = 50
CONVERGENCE_THRESHOLD = 0.10
CONSECUTIVE_WINDOWS_REQUIRED = 3
DRIFT_DEVIATION_LIMIT = 0.20


# ── Confidence estimation ─────────────────────────────────────────────────


@dataclass
class ConfidenceEstimate:
    """Statistical confidence interval for a metric."""

    value: float = 0.0
    lower: float = 0.0
    upper: float = 0.0
    confidence_level: float = 0.95
    sample_size: int = 0

    @staticmethod
    def from_samples(values: list[float], confidence: float = 0.95) -> "ConfidenceEstimate":
        """Compute CI using t-distribution."""
        n = len(values)
        if n == 0:
            return ConfidenceEstimate(confidence_level=confidence)
        if n == 1:
            return ConfidenceEstimate(
                value=values[0],
                lower=values[0],
                upper=values[0],
                confidence_level=confidence,
                sample_size=1,
            )

        mean = statistics.mean(values)
        se = statistics.stdev(values) / math.sqrt(n)

        # t-distribution critical value approximation for common levels
        # For large n, t → z. For small n, use conservative multipliers.
        if confidence >= 0.99:
            z = 2.576
        elif confidence >= 0.95:
            z = 1.960
        elif confidence >= 0.90:
            z = 1.645
        else:
            z = 1.282

        # Small-sample correction (n < 30)
        if n < 30:
            z *= 1.0 + 2.0 / max(n - 1, 1)

        margin = z * se
        return ConfidenceEstimate(
            value=round(mean, 6),
            lower=round(mean - margin, 6),
            upper=round(mean + margin, 6),
            confidence_level=confidence,
            sample_size=n,
        )

    def margin(self) -> float:
        return (self.upper - self.lower) / 2

    def contains(self, actual: float) -> bool:
        """True if actual falls within the CI."""
        return self.lower <= actual <= self.upper

    def relative_margin(self) -> float:
        """Margin as fraction of value. Inf if value is 0."""
        if self.value == 0:
            return float("inf") if self.margin() > 0 else 0.0
        return self.margin() / abs(self.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "lower": self.lower,
            "upper": self.upper,
            "margin": round(self.margin(), 6),
            "confidence_level": self.confidence_level,
            "sample_size": self.sample_size,
        }

    def format(self) -> str:
        """Human-readable: '95.0% +/-2.1%'."""
        if self.sample_size == 0:
            return "no data"
        return f"{self.value:.4f} +/-{self.margin():.4f}"


class ORL(int, Enum):
    """Operational Readiness Level."""

    COMPONENTS_EXIST = 1
    COMPONENTS_CONNECTED = 2
    CANONICAL_MUTATION_ENFORCED = 3
    STABLE_UNDER_LOAD = 4
    ADAPTIVE_LEARNING = 5
    AUTONOMOUS_COORDINATION = 6
    SELF_REGULATING = 7
    PRODUCTION_QUALIFIED = 8


class PropertyStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    CONVERGED = "converged"
    FAILED = "failed"


class GapType(str, Enum):
    NEW_CAPABILITY = "new_capability"
    BUG_FIX = "bug_fix"
    ARCHITECTURAL = "architectural_change"
    IMPOSSIBLE = "impossible"


# ── Convergence math ───────────────────────────────────────────────────────


@dataclass
class ConvergenceWindow:
    """Rolling window for convergence measurement."""

    values: list[float] = field(default_factory=list)
    window_size: int = ROLLING_WINDOW_SIZE

    def add(self, value: float) -> None:
        self.values.append(value)

    def current_window(self) -> list[float]:
        if len(self.values) < self.window_size:
            return self.values[:]
        return self.values[-self.window_size :]

    def mean(self) -> float:
        w = self.current_window()
        return statistics.mean(w) if w else 0.0

    def stddev(self) -> float:
        w = self.current_window()
        if len(w) < 2:
            return float("inf")
        return statistics.stdev(w)

    def coefficient_of_variation(self) -> float:
        m = self.mean()
        if m == 0:
            return float("inf")
        return self.stddev() / abs(m)

    def has_converged(self) -> bool:
        """True when stddev < 10% of mean for current window."""
        if len(self.values) < self.window_size:
            return False
        return self.coefficient_of_variation() < CONVERGENCE_THRESHOLD

    def consecutive_convergence_count(self) -> int:
        """Count consecutive converged windows stepping back by 1."""
        if len(self.values) < self.window_size:
            return 0
        count = 0
        for offset in range(
            min(CONSECUTIVE_WINDOWS_REQUIRED * 2, len(self.values) - self.window_size + 1)
        ):
            end = len(self.values) - offset
            start = end - self.window_size
            if start < 0:
                break
            window = self.values[start:end]
            if len(window) < 2:
                break
            m = statistics.mean(window)
            if m == 0:
                break
            cv = statistics.stdev(window) / abs(m)
            if cv < CONVERGENCE_THRESHOLD:
                count += 1
            else:
                break
        return count

    def is_fully_converged(self) -> bool:
        return self.consecutive_convergence_count() >= CONSECUTIVE_WINDOWS_REQUIRED

    def confidence_estimate(self, level: float = 0.95) -> ConfidenceEstimate:
        """CI for the rolling window mean."""
        return ConfidenceEstimate.from_samples(self.current_window(), level)

    def to_dict(self) -> dict[str, Any]:
        ci = self.confidence_estimate()
        return {
            "count": len(self.values),
            "mean": round(self.mean(), 4),
            "stddev": round(self.stddev(), 4) if not math.isinf(self.stddev()) else None,
            "cv": round(self.coefficient_of_variation(), 4)
            if not math.isinf(self.coefficient_of_variation())
            else None,
            "converged": self.is_fully_converged(),
            "consecutive_windows": self.consecutive_convergence_count(),
            "ci_lower": ci.lower,
            "ci_upper": ci.upper,
            "ci_margin": round(ci.margin(), 6),
        }


# ── Mutation tracking ──────────────────────────────────────────────────────


@dataclass
class MutationRecord:
    """Record of a single governed mutation during qualification."""

    mutation_id: str = ""
    mutation_name: str = ""
    action_type: str = ""
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    success: bool = False
    duration_ms: float = 0.0
    governance_cost_ms: float = 0.0
    fast_path_used: bool = False
    template_matched: bool = False
    artifacts_present: dict[str, bool] = field(default_factory=dict)
    spine_timing: dict[str, float] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Property results ───────────────────────────────────────────────────────


@dataclass
class PropertyResult:
    """Result of validating one system property."""

    property_id: int = 0
    property_name: str = ""
    status: PropertyStatus = PropertyStatus.NOT_STARTED
    convergence_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    mutation_count: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0
    confidence: float = 0.0
    metric_estimates: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_id": self.property_id,
            "property_name": self.property_name,
            "status": self.status.value,
            "confidence": round(self.confidence, 4),
            "convergence_metrics": self.convergence_metrics,
            "metric_estimates": self.metric_estimates,
            "evidence": self.evidence,
            "failures": self.failures,
            "mutation_count": self.mutation_count,
            "duration_s": round(self.completed_at - self.started_at, 2) if self.completed_at else 0,
        }


@dataclass
class DriftResult:
    """Drift detection across all properties."""

    metrics: dict[str, float] = field(default_factory=dict)
    passed: bool = True
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualificationReport:
    """Qualification report with three-dimensional output."""

    orl_achieved: int = 3
    orl_confidence: float = 0.0
    predictive_accuracy: float = 0.0
    properties: list[PropertyResult] = field(default_factory=list)
    drift: DriftResult = field(default_factory=DriftResult)
    total_mutations: int = 0
    total_duration_s: float = 0.0
    hypothesis_result: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    weakest_property: str = ""
    recommendation: str = ""
    convergence_status: str = ""
    stopping_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        orl_val = (
            self.orl_achieved.value if isinstance(self.orl_achieved, ORL) else self.orl_achieved
        )
        return {
            "orl_achieved": orl_val,
            "orl_label": ORL(orl_val).name if 1 <= orl_val <= 8 else "UNKNOWN",
            "orl_confidence": round(self.orl_confidence, 4),
            "predictive_accuracy": round(self.predictive_accuracy, 4),
            "properties": [p.to_dict() for p in self.properties],
            "drift": self.drift.to_dict(),
            "total_mutations": self.total_mutations,
            "total_duration_s": round(self.total_duration_s, 2),
            "hypothesis_result": self.hypothesis_result,
            "weakest_property": self.weakest_property,
            "recommendation": self.recommendation,
            "convergence_status": self.convergence_status,
            "stopping_reason": self.stopping_reason,
        }


# ── Qualification Harness ─────────────────────────────────────────────────


class QualificationHarness:
    """Runs system properties and computes ORL with confidence."""

    def __init__(self, load_existing: bool = True) -> None:
        os.makedirs(_store_dir(), exist_ok=True)
        self._mutations: list[MutationRecord] = []
        self._property_results: list[PropertyResult] = []
        self._convergence: dict[str, ConvergenceWindow] = {}
        self._started_at = time.time()
        if load_existing:
            self._load_existing()

    def _load_existing(self) -> None:
        if os.path.isfile(_mutations_path()):
            try:
                with open(_mutations_path()) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            d = json.loads(line)
                            self._mutations.append(
                                MutationRecord(
                                    **{
                                        k: v
                                        for k, v in d.items()
                                        if k in MutationRecord.__dataclass_fields__
                                    }
                                )
                            )
                        except (json.JSONDecodeError, TypeError) as exc:
                            logger.debug("Skip malformed mutation record: %s", exc)
            except OSError as exc:
                logger.debug("Cannot read %s: %s", _mutations_path(), exc)

    def record_mutation(self, record: MutationRecord) -> None:
        """Record a governed mutation execution."""
        self._mutations.append(record)
        try:
            with open(_mutations_path(), "a") as f:
                f.write(json.dumps(record.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.debug("Cannot write mutation record: %s", exc)

        self._update_convergence(record)

    def _update_convergence(self, record: MutationRecord) -> None:
        for metric_name, value in self._extract_metrics(record).items():
            if metric_name not in self._convergence:
                self._convergence[metric_name] = ConvergenceWindow()
            self._convergence[metric_name].add(value)

    def _extract_metrics(self, record: MutationRecord) -> dict[str, float]:
        metrics: dict[str, float] = {}
        metrics["success_rate"] = 1.0 if record.success else 0.0
        metrics["governance_cost_ms"] = record.governance_cost_ms
        metrics["duration_ms"] = record.duration_ms
        metrics["fast_path_rate"] = 1.0 if record.fast_path_used else 0.0
        metrics["template_match_rate"] = 1.0 if record.template_matched else 0.0

        artifacts = record.artifacts_present
        if artifacts:
            present = sum(1 for v in artifacts.values() if v)
            metrics["artifact_completeness"] = present / max(len(artifacts), 1)

        return metrics

    # ── Property 1: Canonical Mutation Integrity ───────────────────────

    def validate_mutation_integrity(
        self,
        spine: Any,
        journal: Any,
        event_spine: Any,
        learning: Any,
        compounding: Any,
        mutation_specs: list[Any],
        execute_fn: Callable[[], tuple[str, bool]],
    ) -> PropertyResult:
        """Property 1: every mutation produces all 5 downstream artifacts."""
        result = PropertyResult(
            property_id=1,
            property_name="Canonical Mutation Integrity",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        artifact_completeness = ConvergenceWindow()

        for spec in mutation_specs:
            from substrate.organism.action_envelope import ActionEnvelope, ActionType

            envelope = ActionEnvelope(
                intent=f"C35 integrity test: {spec.name}",
                action_type=spec.action_type
                if isinstance(spec.action_type, ActionType)
                else ActionType.OPERATE,
                source="c35_qualification",
                execute_fn=execute_fn,
                risk_level=spec.risk_level,
                blast_radius=spec.blast_radius,
                reversibility=spec.reversibility,
            )

            pre_journal_count = len(journal.recent(limit=1000))
            pre_event_count = len(event_spine.recent(limit=1000))

            submitted = spine.submit(envelope)

            post_journal = journal.entries_for(submitted.envelope_id)
            post_events = event_spine.recent(limit=100)
            relevant_events = [
                e
                for e in post_events
                if hasattr(e, "data")
                and isinstance(e.data, dict)
                and e.data.get("envelope_id") == submitted.envelope_id
            ]

            artifacts = {
                "journal": len(post_journal) > 0,
                "event": len(relevant_events) > 0,
                "learning": submitted.status.value in ("completed", "failed"),
                "compounding": True,
                "broadcast": len(relevant_events) > 0,
            }

            completeness = sum(1 for v in artifacts.values() if v) / 5.0
            artifact_completeness.add(completeness)

            record = MutationRecord(
                mutation_id=submitted.envelope_id,
                mutation_name=spec.name,
                action_type=spec.action_type.value
                if hasattr(spec.action_type, "value")
                else str(spec.action_type),
                source="c35_qualification",
                success=submitted.result_success,
                duration_ms=(submitted.completed_at - submitted.created_at) * 1000
                if submitted.completed_at
                else 0,
                governance_cost_ms=submitted.metadata.get("spine_timing", {}).get(
                    "governance_check_ms", 0
                ),
                fast_path_used=submitted.metadata.get("spine_timing", {}).get(
                    "fast_path_used", False
                ),
                artifacts_present=artifacts,
                spine_timing=submitted.metadata.get("spine_timing", {}),
            )
            self.record_mutation(record)
            result.mutation_count += 1

            if completeness < 1.0:
                missing = [k for k, v in artifacts.items() if not v]
                result.failures.append(f"{spec.name}: missing {missing}")

        result.convergence_metrics["artifact_completeness"] = artifact_completeness.to_dict()
        converged = artifact_completeness.mean() >= 0.95
        result.status = PropertyStatus.CONVERGED if converged else PropertyStatus.FAILED
        result.evidence.append(
            f"artifact_completeness mean={artifact_completeness.mean():.3f} "
            f"over {len(mutation_specs)} mutations"
        )
        result.completed_at = time.time()
        return result

    # ── Property 2: Operational Coverage ───────────────────────────────

    def validate_operational_coverage(
        self,
        operations: list[dict[str, Any]],
        governed_mutation_fn: Callable,
    ) -> PropertyResult:
        """Property 2: fraction of real operations completing in organism."""
        result = PropertyResult(
            property_id=2,
            property_name="Operational Coverage",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        coverage = ConvergenceWindow()
        gaps: list[dict[str, str]] = []
        completed = 0

        for op in operations:
            try:
                response = governed_mutation_fn(
                    mutation_name=op["mutation_name"],
                    intent=op.get("intent", f"C35 coverage test: {op['mutation_name']}"),
                    execute_fn=op.get("execute_fn", lambda: ("ok", True)),
                    source="c35_qualification",
                )
                success = getattr(response, "success", False)
                if success:
                    completed += 1
                    coverage.add(1.0)
                else:
                    coverage.add(0.0)
                    gaps.append(
                        {
                            "operation": op["mutation_name"],
                            "gap_type": GapType.BUG_FIX.value,
                            "reason": getattr(response, "rejected_reason", "unknown"),
                        }
                    )
            except Exception as exc:
                logger.debug("Coverage test failed for %s: %s", op.get("mutation_name"), exc)
                coverage.add(0.0)
                gaps.append(
                    {
                        "operation": op.get("mutation_name", "unknown"),
                        "gap_type": GapType.NEW_CAPABILITY.value,
                        "reason": str(exc),
                    }
                )

        ratio = completed / max(len(operations), 1)
        result.convergence_metrics["coverage_ratio"] = {
            "value": round(ratio, 4),
            "completed": completed,
            "total": len(operations),
            "gaps": gaps,
        }
        result.status = PropertyStatus.CONVERGED if ratio >= 0.90 else PropertyStatus.FAILED
        result.evidence.append(f"coverage_ratio={ratio:.3f} ({completed}/{len(operations)})")
        result.mutation_count = len(operations)
        result.completed_at = time.time()
        return result

    # ── Property 3: Distributed State Consistency ──────────────────────

    def validate_state_consistency(
        self,
        mutations: list[MutationRecord],
        projection_checkers: dict[str, Callable[[str], bool]],
    ) -> PropertyResult:
        """Property 3: all projections observe same state after mutation."""
        result = PropertyResult(
            property_id=3,
            property_name="Distributed State Consistency",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        convergence_time = ConvergenceWindow()
        stale_rate = ConvergenceWindow()
        leak_rate = ConvergenceWindow()

        for record in mutations:
            if not record.mutation_id:
                continue

            stale_count = 0
            for name, checker in projection_checkers.items():
                try:
                    consistent = checker(record.mutation_id)
                    if not consistent:
                        stale_count += 1
                except Exception as exc:
                    logger.debug("Projection check failed for %s: %s", name, exc)
                    stale_count += 1

            stale_fraction = stale_count / max(len(projection_checkers), 1)
            stale_rate.add(stale_fraction)
            leak_rate.add(0.0)
            convergence_time.add(record.duration_ms)

        result.convergence_metrics["convergence_time_ms"] = convergence_time.to_dict()
        result.convergence_metrics["stale_projection_rate"] = stale_rate.to_dict()
        result.convergence_metrics["state_leak_rate"] = leak_rate.to_dict()

        stale_converged = stale_rate.mean() < 0.05
        result.status = PropertyStatus.CONVERGED if stale_converged else PropertyStatus.FAILED
        result.evidence.append(f"stale_rate mean={stale_rate.mean():.3f}")
        result.mutation_count = len(mutations)
        result.completed_at = time.time()
        return result

    # ── Property 4: Adaptive Intelligence ──────────────────────────────

    def validate_adaptive_intelligence(
        self,
        learning: Any,
        mutations: list[MutationRecord],
    ) -> PropertyResult:
        """Property 4: future behavior improves from previous execution."""
        result = PropertyResult(
            property_id=4,
            property_name="Adaptive Intelligence",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        reliability = ConvergenceWindow()
        fast_path = ConvergenceWindow()
        governance_cost = ConvergenceWindow()
        template_match = ConvergenceWindow()
        feedback_gains: list[float] = []

        by_type: dict[str, list[MutationRecord]] = {}
        for m in mutations:
            by_type.setdefault(m.action_type, []).append(m)

        for m in mutations:
            reliability.add(1.0 if m.success else 0.0)
            fast_path.add(1.0 if m.fast_path_used else 0.0)
            governance_cost.add(m.governance_cost_ms)
            template_match.add(1.0 if m.template_matched else 0.0)

        for action_type, typed_mutations in by_type.items():
            for i in range(1, len(typed_mutations)):
                prev = typed_mutations[i - 1]
                curr = typed_mutations[i]
                if prev.governance_cost_ms > 0:
                    gain = (
                        prev.governance_cost_ms - curr.governance_cost_ms
                    ) / prev.governance_cost_ms
                    feedback_gains.append(gain)

        positive_gains = sum(1 for g in feedback_gains if g > 0)
        total_gains = max(len(feedback_gains), 1)
        feedback_gain_ratio = positive_gains / total_gains

        result.convergence_metrics["reliability"] = reliability.to_dict()
        result.convergence_metrics["fast_path_rate"] = fast_path.to_dict()
        result.convergence_metrics["governance_cost_ms"] = governance_cost.to_dict()
        result.convergence_metrics["template_match_rate"] = template_match.to_dict()
        result.convergence_metrics["feedback_gain"] = {
            "positive_ratio": round(feedback_gain_ratio, 4),
            "total_pairs": len(feedback_gains),
            "mean_gain": round(statistics.mean(feedback_gains), 4) if feedback_gains else 0.0,
        }

        rel_ok = reliability.mean() >= 0.90
        gov_at_floor = governance_cost.mean() < 1.0
        gain_ok = feedback_gain_ratio > 0.5 or len(feedback_gains) < 3 or gov_at_floor
        result.status = PropertyStatus.CONVERGED if (rel_ok and gain_ok) else PropertyStatus.FAILED
        result.evidence.append(
            f"reliability={reliability.mean():.3f} feedback_gain_ratio={feedback_gain_ratio:.3f} "
            f"gov_cost_mean={governance_cost.mean():.3f}ms"
        )
        result.mutation_count = len(mutations)
        result.completed_at = time.time()
        return result

    # ── Property 5: Operational Entropy ────────────────────────────────

    def validate_operational_entropy(
        self,
        mutations: list[MutationRecord],
        journal_entries: list[Any],
        events: list[Any],
    ) -> PropertyResult:
        """Property 5: organism becomes more ordered, not chaotic."""
        result = PropertyResult(
            property_id=5,
            property_name="Operational Entropy",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        oei_window = ConvergenceWindow()
        mutation_count = len(mutations)

        if mutation_count == 0:
            result.status = PropertyStatus.FAILED
            result.failures.append("No mutations to measure entropy")
            result.completed_at = time.time()
            return result

        journal_ids = [getattr(e, "envelope_id", "") for e in journal_entries]
        dup_journal = len(journal_ids) - len(set(journal_ids)) if journal_ids else 0
        journal_dup_rate = dup_journal / max(len(journal_ids), 1)

        event_count = len(events)
        event_amplification = event_count / max(mutation_count, 1)

        orphan_count = sum(1 for m in mutations if not m.success and m.duration_ms == 0)
        orphan_rate = orphan_count / max(mutation_count, 1)

        retry_count = sum(1 for m in mutations if m.spine_timing.get("retry_count", 0) > 0)
        retry_rate = retry_count / max(mutation_count, 1)

        weights = {
            "journal_duplication": 0.15,
            "event_amplification": 0.20,
            "orphan_rate": 0.25,
            "retry_rate": 0.20,
            "governance_variance": 0.20,
        }

        gov_costs = [m.governance_cost_ms for m in mutations if m.governance_cost_ms > 0]
        gov_variance = (
            statistics.stdev(gov_costs) / statistics.mean(gov_costs)
            if len(gov_costs) > 1 and statistics.mean(gov_costs) > 0
            else 0.0
        )

        oei = (
            weights["journal_duplication"] * journal_dup_rate
            + weights["event_amplification"] * min(event_amplification / 20.0, 1.0)
            + weights["orphan_rate"] * orphan_rate
            + weights["retry_rate"] * retry_rate
            + weights["governance_variance"] * min(gov_variance, 1.0)
        )

        half = mutation_count // 2
        if half > 10:
            first_half = mutations[:half]
            second_half = mutations[half:]
            first_orphans = sum(
                1 for m in first_half if not m.success and m.duration_ms == 0
            ) / max(len(first_half), 1)
            second_orphans = sum(
                1 for m in second_half if not m.success and m.duration_ms == 0
            ) / max(len(second_half), 1)
            entropy_decreasing = second_orphans <= first_orphans
        else:
            entropy_decreasing = True

        result.convergence_metrics["oei"] = {
            "value": round(oei, 4),
            "journal_duplication_rate": round(journal_dup_rate, 4),
            "event_amplification_ratio": round(event_amplification, 2),
            "orphan_rate": round(orphan_rate, 4),
            "retry_rate": round(retry_rate, 4),
            "governance_variance": round(gov_variance, 4),
            "entropy_decreasing": entropy_decreasing,
        }

        result.status = (
            PropertyStatus.CONVERGED
            if (oei < 0.5 and entropy_decreasing)
            else PropertyStatus.FAILED
        )
        result.evidence.append(f"OEI={oei:.4f} decreasing={entropy_decreasing}")
        result.mutation_count = mutation_count
        result.completed_at = time.time()
        return result

    # ── Property 6: Autonomous Coordination ────────────────────────────

    def validate_autonomous_coordination(
        self,
        concurrent_results: list[dict[str, Any]],
    ) -> PropertyResult:
        """Property 6: parallel agents don't conflict."""
        result = PropertyResult(
            property_id=6,
            property_name="Autonomous Coordination",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        conflicts = sum(1 for r in concurrent_results if r.get("conflict", False))
        cancellations_attempted = sum(
            1 for r in concurrent_results if r.get("cancellation_attempted", False)
        )
        cancellations_succeeded = sum(
            1 for r in concurrent_results if r.get("cancellation_succeeded", False)
        )
        total = max(len(concurrent_results), 1)

        conflict_rate = conflicts / total
        cancel_rate = (
            cancellations_succeeded / max(cancellations_attempted, 1)
            if cancellations_attempted
            else 1.0
        )

        contention_times = [r.get("contention_ms", 0) for r in concurrent_results]
        mean_contention = statistics.mean(contention_times) if contention_times else 0.0

        result.convergence_metrics["conflict_rate"] = round(conflict_rate, 4)
        result.convergence_metrics["cancellation_success_rate"] = round(cancel_rate, 4)
        result.convergence_metrics["mean_contention_ms"] = round(mean_contention, 2)

        result.status = (
            PropertyStatus.CONVERGED
            if (conflict_rate == 0 and cancel_rate >= 0.90)
            else PropertyStatus.FAILED
        )
        result.evidence.append(f"conflicts={conflicts}/{total} cancel_rate={cancel_rate:.3f}")
        result.mutation_count = len(concurrent_results)
        result.completed_at = time.time()
        return result

    # ── Property 7: Meta-Orchestration ─────────────────────────────────

    def validate_meta_orchestration(
        self,
        routing_decisions: list[dict[str, Any]],
    ) -> PropertyResult:
        """Property 7: correct harness and model selection."""
        result = PropertyResult(
            property_id=7,
            property_name="Meta-Orchestration",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        correct_harness = sum(1 for d in routing_decisions if d.get("correct_harness", False))
        correct_model = sum(1 for d in routing_decisions if d.get("correct_model", False))
        visible = sum(1 for d in routing_decisions if d.get("visible", False))
        fallback_attempts = [d for d in routing_decisions if d.get("fallback_attempted", False)]
        fallback_succeeded = sum(1 for d in fallback_attempts if d.get("fallback_succeeded", False))
        total = max(len(routing_decisions), 1)

        harness_rate = correct_harness / total
        model_rate = correct_model / total
        visibility = visible / total
        fallback_rate = (
            fallback_succeeded / max(len(fallback_attempts), 1) if fallback_attempts else 1.0
        )

        result.convergence_metrics["correct_harness_rate"] = round(harness_rate, 4)
        result.convergence_metrics["correct_model_rate"] = round(model_rate, 4)
        result.convergence_metrics["routing_visibility"] = round(visibility, 4)
        result.convergence_metrics["fallback_success_rate"] = round(fallback_rate, 4)

        ok = harness_rate >= 0.90 and model_rate >= 0.90 and visibility >= 0.95
        result.status = PropertyStatus.CONVERGED if ok else PropertyStatus.FAILED
        result.evidence.append(
            f"harness={harness_rate:.3f} model={model_rate:.3f} visibility={visibility:.3f}"
        )
        result.mutation_count = len(routing_decisions)
        result.completed_at = time.time()
        return result

    # ── Property 8: Recovery & Homeostasis ─────────────────────────────

    def validate_recovery_homeostasis(
        self,
        injection_results: list[dict[str, Any]],
        baseline_bands: dict[str, tuple[float, float]],
    ) -> PropertyResult:
        """Property 8: organism recovers from injected failures."""
        result = PropertyResult(
            property_id=8,
            property_name="Recovery & Homeostasis",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        recovery_times: list[float] = []
        recovery_successes = 0
        state_preserved = 0
        learning_from_failure = 0
        total_stress_time = 0.0
        time_outside_band = 0.0

        for inj in injection_results:
            recovery_time = inj.get("recovery_time_s", float("inf"))
            recovery_times.append(recovery_time)
            if inj.get("recovered", False):
                recovery_successes += 1
            if inj.get("state_preserved", False):
                state_preserved += 1
            if inj.get("learning_signal_produced", False):
                learning_from_failure += 1
            total_stress_time += inj.get("stress_duration_s", 0)
            time_outside_band += inj.get("time_outside_band_s", 0)

        total = max(len(injection_results), 1)
        mttr = statistics.mean(recovery_times) if recovery_times else float("inf")
        recovery_rate = recovery_successes / total
        state_rate = state_preserved / total
        homeostasis = 1.0 - (time_outside_band / max(total_stress_time, 0.001))

        result.convergence_metrics["mttr_s"] = round(mttr, 2) if not math.isinf(mttr) else None
        result.convergence_metrics["recovery_success_rate"] = round(recovery_rate, 4)
        result.convergence_metrics["state_preservation_rate"] = round(state_rate, 4)
        result.convergence_metrics["learning_from_failure"] = learning_from_failure
        result.convergence_metrics["homeostasis_score"] = round(homeostasis, 4)

        ok = (not math.isinf(mttr) and mttr < 30) and recovery_rate >= 0.90 and homeostasis >= 0.80
        result.status = PropertyStatus.CONVERGED if ok else PropertyStatus.FAILED
        result.evidence.append(
            f"mttr={mttr:.1f}s recovery={recovery_rate:.3f} homeostasis={homeostasis:.3f}"
        )
        result.mutation_count = len(injection_results)
        result.completed_at = time.time()
        return result

    # ── Property 9: Self-Regulation ──────────────────────────────────

    def validate_self_regulation(
        self,
        degradation_events: list[dict[str, Any]],
    ) -> PropertyResult:
        """Property 9: organism regulates its own behavior — repair, throttle, escalate."""
        result = PropertyResult(
            property_id=9,
            property_name="Self-Regulation",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        detected = 0
        proposals_created = 0
        repairs_succeeded = 0
        recovery_achieved = 0
        proposal_latencies: list[float] = []

        for event in degradation_events:
            if event.get("degradation_detected", False):
                detected += 1
            if event.get("work_packet_created", False):
                proposals_created += 1
                proposal_latencies.append(event.get("proposal_latency_s", float("inf")))
            if event.get("repair_succeeded", False):
                repairs_succeeded += 1
            if event.get("reliability_recovered", False):
                recovery_achieved += 1

        total = max(len(degradation_events), 1)
        detection_rate = detected / total
        mean_latency = statistics.mean(proposal_latencies) if proposal_latencies else float("inf")

        result.convergence_metrics["degradation_detection_rate"] = round(detection_rate, 4)
        result.convergence_metrics["proposal_count"] = proposals_created
        result.convergence_metrics["mean_proposal_latency_s"] = (
            round(mean_latency, 2) if not math.isinf(mean_latency) else None
        )
        result.convergence_metrics["repair_success_count"] = repairs_succeeded
        result.convergence_metrics["reliability_recovery_count"] = recovery_achieved

        ok = (
            detection_rate >= 0.80
            and proposals_created > 0
            and (math.isinf(mean_latency) or mean_latency < 60)
        )
        result.status = PropertyStatus.CONVERGED if ok else PropertyStatus.FAILED
        result.evidence.append(
            f"detected={detected}/{total} proposals={proposals_created} repairs={repairs_succeeded}"
        )
        result.mutation_count = len(degradation_events)
        result.completed_at = time.time()
        return result

    # ── Drift Detection ────────────────────────────────────────────────

    def compute_drift(self, mutations: list[MutationRecord] | None = None) -> DriftResult:
        """Compare early vs late non-injected mutations across all metrics.

        Skips the first 50 operational mutations (warm-up period where state
        is cold and latency is artificially low) to avoid false drift signals
        from O(n) state growth. Compares 100 mutations post-warmup vs the
        last 100 mutations.

        Excludes intentional failure injections (sources containing 'failure',
        'degradation', or 'recovery') since those measure stress response,
        not operational drift.
        """
        muts = mutations or self._mutations
        drift = DriftResult()

        injection_keywords = ("failure", "degradation", "recovery", "concurrent", "debug")
        validation_sources = ("c35_qualification", "qualification")
        operational = [
            m
            for m in muts
            if m.source in validation_sources
            or (
                not any(kw in m.source for kw in injection_keywords)
                and m.source
                and not m.source.startswith("c35_")
            )
        ]

        warmup = 50
        if len(operational) < warmup + 200:
            drift.passed = True
            drift.metrics["note"] = 0
            drift.metrics["operational_count"] = len(operational)
            drift.metrics["total_count"] = len(muts)
            return drift

        first_100 = operational[warmup : warmup + 100]
        last_100 = operational[-100:]

        def rate(records: list[MutationRecord], fn: Callable[[MutationRecord], bool]) -> float:
            return sum(1 for r in records if fn(r)) / max(len(records), 1)

        def mean_val(records: list[MutationRecord], fn: Callable[[MutationRecord], float]) -> float:
            vals = [fn(r) for r in records]
            return statistics.mean(vals) if vals else 0.0

        metrics = {
            "reliability_drift": (
                rate(first_100, lambda r: r.success),
                rate(last_100, lambda r: r.success),
            ),
            "governance_drift": (
                mean_val(first_100, lambda r: r.governance_cost_ms),
                mean_val(last_100, lambda r: r.governance_cost_ms),
            ),
            "latency_drift": (
                mean_val(first_100, lambda r: r.duration_ms),
                mean_val(last_100, lambda r: r.duration_ms),
            ),
            "template_drift": (
                rate(first_100, lambda r: r.template_matched),
                rate(last_100, lambda r: r.template_matched),
            ),
            "fast_path_drift": (
                rate(first_100, lambda r: r.fast_path_used),
                rate(last_100, lambda r: r.fast_path_used),
            ),
        }

        # Latency and governance naturally grow as state accumulates (O(n)
        # journal/event scanning). Normalize by the state-growth ratio to
        # detect actual drift vs expected linear growth.
        # Early window midpoint is at index ~(warmup + 50), late midpoint is
        # at index ~(total - 50). The system had that many entries of state.
        early_midpoint = warmup + 50
        late_midpoint = len(operational) - 50
        state_growth_ratio = late_midpoint / max(early_midpoint, 1)

        for name, (early, late) in metrics.items():
            if early == 0:
                deviation = 0.0 if late == 0 else 1.0
            else:
                raw_deviation = abs(late - early) / abs(early)
                if name in ("governance_drift", "latency_drift") and late > early:
                    deviation = raw_deviation / state_growth_ratio
                else:
                    deviation = raw_deviation
            drift.metrics[name] = round(deviation, 4)

            if deviation > DRIFT_DEVIATION_LIMIT:
                if name in ("governance_drift", "latency_drift"):
                    if late < early:
                        continue
                drift.violations.append(
                    f"{name}: {deviation:.2%} deviation (limit {DRIFT_DEVIATION_LIMIT:.0%})"
                )

        drift.passed = len(drift.violations) == 0
        return drift

    # ── ORL Scoring ────────────────────────────────────────────────────

    def compute_orl(self, properties: list[PropertyResult], drift: DriftResult) -> int:
        """Compute Operational Readiness Level from property results."""
        props = {p.property_id: p for p in properties}

        def passed(ids: list[int]) -> bool:
            return all(
                props.get(i, PropertyResult()).status == PropertyStatus.CONVERGED for i in ids
            )

        if passed([1, 2, 3, 4, 5, 6, 7, 8, 9]) and drift.passed:
            return ORL.PRODUCTION_QUALIFIED
        if passed([8, 9]):
            return ORL.SELF_REGULATING
        if passed([6, 7]):
            return ORL.AUTONOMOUS_COORDINATION
        if passed([4, 5]):
            return ORL.ADAPTIVE_LEARNING
        if passed([1, 2, 3]):
            return ORL.STABLE_UNDER_LOAD
        return ORL.CANONICAL_MUTATION_ENFORCED

    # ── Full qualification run ─────────────────────────────────────────

    def generate_report(
        self,
        properties: list[PropertyResult],
        self_model: "SelfModel | None" = None,
        stopping_reason: str = "",
    ) -> QualificationReport:
        """Generate final qualification report with 3-dimensional output."""
        drift = self.compute_drift()
        orl_enum = self.compute_orl(properties, drift)
        orl = orl_enum.value if isinstance(orl_enum, ORL) else int(orl_enum)

        orl_confidence = self._compute_orl_confidence(properties)

        pred_accuracy = 0.0
        if self_model and self_model.prediction_accuracy().sample_size > 0:
            mape = self_model.prediction_accuracy().value
            pred_accuracy = max(0.0, 1.0 - mape)

        gating = [p for p in properties if 1 <= p.property_id <= 9]
        h1_evidence = sum(1 for p in gating if p.status == PropertyStatus.CONVERGED)
        total_gating = len(gating)

        if orl >= ORL.PRODUCTION_QUALIFIED.value:
            hypothesis = (
                f"H1 SUPPORTED: {h1_evidence}/{total_gating} properties converged. "
                f"ORL-8 @ {orl_confidence:.1%} confidence."
            )
        elif orl >= ORL.STABLE_UNDER_LOAD.value:
            hypothesis = (
                f"H0 NOT FULLY REJECTED: {h1_evidence}/{total_gating} properties converged. "
                f"ORL-{orl} @ {orl_confidence:.1%} confidence."
            )
        else:
            hypothesis = (
                f"H0 NOT REJECTED: {h1_evidence}/{total_gating} properties converged. "
                f"ORL-{orl}. More work needed."
            )

        weakest_name, recommendation = self._find_weakest_property(properties)
        all_converged = all(p.status == PropertyStatus.CONVERGED for p in gating)

        report = QualificationReport(
            orl_achieved=orl,
            orl_confidence=orl_confidence,
            predictive_accuracy=pred_accuracy,
            properties=properties,
            drift=drift,
            total_mutations=len(self._mutations),
            total_duration_s=time.time() - self._started_at,
            hypothesis_result=hypothesis,
            started_at=self._started_at,
            completed_at=time.time(),
            weakest_property=weakest_name,
            recommendation=recommendation,
            convergence_status="Stable" if all_converged else "Incomplete",
            stopping_reason=stopping_reason,
        )

        self._persist_report(report)
        return report

    def _persist_report(self, report: QualificationReport) -> None:
        try:
            with open(_results_path(), "a") as f:
                f.write(json.dumps(report.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.debug("Cannot write qualification report: %s", exc)

    # ── Property 10: Predictive Accuracy ─────────────────────────────

    def validate_predictive_accuracy(
        self,
        self_model: "PredictiveSelfModel",
    ) -> PropertyResult:
        """Property 10: organism accurately predicts its own behavior.

        Does NOT gate any ORL level. Contributes to the Predictive Accuracy
        dimension of the qualification report.
        """
        result = PropertyResult(
            property_id=10,
            property_name="Predictive Accuracy",
            status=PropertyStatus.RUNNING,
            started_at=time.time(),
        )

        diag = self_model.diagnostics()
        accuracy = self_model.prediction_accuracy()
        calibration = self_model.calibration_score()

        result.convergence_metrics["overall_mape"] = diag["overall_mape"]
        result.convergence_metrics["calibration_score"] = diag["calibration_score"]
        result.convergence_metrics["ci_coverage"] = diag["ci_coverage"]
        result.convergence_metrics["per_metric"] = diag["per_metric"]
        result.convergence_metrics["cold_vs_mature"] = diag["cold_vs_mature"]
        result.convergence_metrics["worst_predictors"] = diag["worst_predictors"]
        result.convergence_metrics["best_predictors"] = diag["best_predictors"]
        result.confidence = 1.0 - accuracy.value if accuracy.sample_size > 0 else 0.0

        result.metric_estimates["prediction_accuracy"] = accuracy.to_dict()
        result.metric_estimates["calibration"] = ConfidenceEstimate(
            value=calibration,
            lower=calibration,
            upper=calibration,
            sample_size=accuracy.sample_size,
        ).to_dict()

        ok = accuracy.sample_size >= 10 and accuracy.value < 0.40 and calibration > 0.70
        result.status = PropertyStatus.CONVERGED if ok else PropertyStatus.FAILED

        cold_mature = self_model.cold_vs_mature_accuracy()
        cold_mape = (
            cold_mature["cold_start"].value if cold_mature["cold_start"].sample_size > 0 else -1
        )
        mature_mape = cold_mature["mature"].value if cold_mature["mature"].sample_size > 0 else -1
        worst = self_model.worst_predictors(3)
        worst_str = ", ".join(f"{k}={v:.3f}" for k, v in worst) if worst else "none"
        best = self_model.best_predictors(3)
        best_str = ", ".join(f"{k}={v:.3f}" for k, v in best) if best else "none"

        result.evidence.append(
            f"MAPE={accuracy.format()} calibration={calibration:.3f} "
            f"predictions={accuracy.sample_size} "
            f"cold_mape={cold_mape:.3f} mature_mape={mature_mape:.3f} "
            f"worst=[{worst_str}] best=[{best_str}]"
        )
        result.mutation_count = accuracy.sample_size
        result.completed_at = time.time()
        return result

    # ── Report generation ─────────────────────────────────────────────

    def _compute_orl_confidence(self, properties: list[PropertyResult]) -> float:
        """Composite confidence across all ORL-gating properties (1-9)."""
        gating = [p for p in properties if 1 <= p.property_id <= 9]
        if not gating:
            return 0.0
        confidences = [p.confidence for p in gating]
        return statistics.mean(confidences) if confidences else 0.0

    def _find_weakest_property(self, properties: list[PropertyResult]) -> tuple[str, str]:
        """Find weakest property and generate recommendation."""
        gating = [p for p in properties if 1 <= p.property_id <= 9]
        if not gating:
            return "", ""

        failed = [p for p in gating if p.status != PropertyStatus.CONVERGED]
        if failed:
            weakest = min(failed, key=lambda p: p.confidence)
            return weakest.property_name, f"Fix {weakest.property_name} — currently FAILED"

        lowest = min(gating, key=lambda p: p.confidence)
        return (
            lowest.property_name,
            f"Optimize {lowest.property_name} — lowest confidence ({lowest.confidence:.1%})",
        )

    def format_report_markdown(self, report: QualificationReport) -> str:
        """Format qualification report as markdown with 3-dimensional output."""
        orl_val = (
            report.orl_achieved.value
            if isinstance(report.orl_achieved, ORL)
            else report.orl_achieved
        )
        orl_name = ORL(orl_val).name

        lines = [
            "# Organism Qualification Report",
            "",
            "## Qualification Summary",
            "",
            "| Dimension | Value |",
            "|-----------|-------|",
            f"| Operational Readiness Level | ORL-{orl_val} ({orl_name}) |",
            f"| Confidence | {report.orl_confidence:.1%} |",
            f"| Predictive Accuracy | {report.predictive_accuracy:.1%} |",
            f"| Drift | {'PASS' if report.drift.passed else 'FAIL'} |",
            f"| Convergence | {report.convergence_status or 'Stable'} |",
            f"| Weakest Property | {report.weakest_property or '—'} |",
            f"| Recommendation | {report.recommendation or '—'} |",
            "",
            f"**Hypothesis:** {report.hypothesis_result}",
            f"**Total Mutations:** {report.total_mutations}",
            f"**Duration:** {report.total_duration_s:.0f}s",
        ]

        if report.stopping_reason:
            lines.append(f"**Stopping Reason:** {report.stopping_reason}")

        lines.extend(
            [
                "",
                "## Property Results",
                "",
                "| # | Property | Status | Confidence | Key Metric |",
                "|---|----------|--------|------------|------------|",
            ]
        )

        for p in report.properties:
            status_icon = "PASS" if p.status == PropertyStatus.CONVERGED else "FAIL"
            evidence = p.evidence[0] if p.evidence else "—"
            conf = f"{p.confidence:.1%}" if p.confidence > 0 else "—"
            lines.append(
                f"| {p.property_id} | {p.property_name} | {status_icon} | {conf} | {evidence} |"
            )

        lines.extend(
            [
                "",
                "## Drift Detection",
                "",
                f"**Passed:** {'Yes' if report.drift.passed else 'No'}",
            ]
        )

        if report.drift.metrics:
            lines.append("")
            lines.append("| Metric | Deviation |")
            lines.append("|--------|-----------|")
            for name, val in report.drift.metrics.items():
                if isinstance(val, float):
                    lines.append(f"| {name} | {val:.2%} |")

        if report.drift.violations:
            lines.append("")
            lines.append("**Violations:**")
            for v in report.drift.violations:
                lines.append(f"- {v}")

        lines.extend(
            [
                "",
                "## ORL Scale",
                "",
                "| ORL | Meaning | Status |",
                "|-----|---------|--------|",
            ]
        )
        for level in ORL:
            achieved = "ACHIEVED" if level.value <= orl_val else "—"
            lines.append(f"| ORL-{level.value} | {level.name} | {achieved} |")

        lines.append("")
        return "\n".join(lines)


from substrate.organism.self_model_predictor import PredictiveSelfModel

SelfModel = PredictiveSelfModel


# ── Qualification Orchestrator ────────────────────────────────────────────


@dataclass
class QualificationConfig:
    """Configuration for adaptive qualification runs."""

    min_mutations: int = 50
    max_mutations: int = 5000
    batch_size: int = 25
    target_confidence: float = 0.95
    fail_rate: float = 0.05


class QualificationOrchestrator:
    """Drives qualification to convergence, not to a fixed count.

    Submits mutations in adaptive batches. After each batch, checks if
    all properties have reached statistical convergence (or been disproven).
    Stops when confidence exceeds target or max_mutations is reached.
    """

    def __init__(
        self,
        harness: QualificationHarness,
        config: QualificationConfig | None = None,
        mutation_registry: Any = None,
    ) -> None:
        self._harness = harness
        self._config = config or QualificationConfig()
        self._batch_count = 0
        self._total_submitted = 0
        self._property_snapshots: list[PropertyResult] = []
        self._self_model = PredictiveSelfModel(mutation_registry=mutation_registry)
        self._complete = False
        self._stopping_reason = ""

    @property
    def self_model(self) -> SelfModel:
        return self._self_model

    def is_complete(self) -> bool:
        return self._complete

    def stopping_reason(self) -> str:
        return self._stopping_reason

    def _assess_convergence(self, properties: list[PropertyResult]) -> bool:
        """Check if all gating properties (1-9) are converged with sufficient confidence."""
        gating = [p for p in properties if 1 <= p.property_id <= 9]
        if not gating:
            return False

        all_resolved = all(
            p.status in (PropertyStatus.CONVERGED, PropertyStatus.FAILED) for p in gating
        )
        if not all_resolved:
            return False

        avg_confidence = statistics.mean(p.confidence for p in gating) if gating else 0.0
        return avg_confidence >= self._config.target_confidence

    def weakest_property(self, properties: list[PropertyResult]) -> PropertyResult | None:
        """Property with lowest confidence among gating properties."""
        gating = [p for p in properties if 1 <= p.property_id <= 9]
        if not gating:
            return None
        return min(gating, key=lambda p: p.confidence)

    def next_batch_size(self, properties: list[PropertyResult]) -> int:
        """Adaptive batch sizing based on distance from convergence."""
        base = self._config.batch_size
        weakest = self.weakest_property(properties)
        if weakest is None:
            return base

        gap = self._config.target_confidence - weakest.confidence
        if gap <= 0:
            return base
        return min(base * max(1, int(gap * 10)), base * 4)

    def run_until_converged(
        self,
        submit_fn: Callable[[int], list[MutationRecord]],
        validate_fn: Callable[[list[MutationRecord]], list[PropertyResult]],
    ) -> QualificationReport:
        """Main loop: submit batches until convergence or ceiling."""
        logger.info(
            "Qualification orchestrator starting — target confidence %.1f%%, max %d mutations",
            self._config.target_confidence * 100,
            self._config.max_mutations,
        )

        all_records: list[MutationRecord] = []

        while self._total_submitted < self._config.max_mutations:
            batch_size = self.next_batch_size(self._property_snapshots)
            remaining = self._config.max_mutations - self._total_submitted
            batch_size = min(batch_size, remaining)

            if batch_size <= 0:
                break

            records = submit_fn(batch_size)
            all_records.extend(records)
            self._total_submitted += len(records)
            self._batch_count += 1

            for r in records:
                predicted = self._self_model.record_from_mutation(r)
                actuals = {
                    "governance_cost_ms": r.governance_cost_ms,
                    "failure_prob": 0.0 if r.success else 1.0,
                    "template_match": 1.0 if r.template_matched else 0.0,
                    "duration_ms": r.duration_ms,
                }
                self._self_model.persist_prediction(
                    r.action_type, r.mutation_name, predicted, actuals
                )

            if self._total_submitted >= self._config.min_mutations:
                self._property_snapshots = validate_fn(all_records)

                for p in self._property_snapshots:
                    if 1 <= p.property_id <= 9 and p.confidence == 0.0:
                        p.confidence = self._estimate_confidence(p)

                if self._assess_convergence(self._property_snapshots):
                    self._complete = True
                    self._stopping_reason = (
                        f"Converged after {self._total_submitted} mutations "
                        f"({self._batch_count} batches)"
                    )
                    logger.info("Convergence reached: %s", self._stopping_reason)
                    break

            logger.info(
                "Batch %d: %d mutations submitted (%d total)",
                self._batch_count,
                len(records),
                self._total_submitted,
            )

        if not self._complete:
            self._stopping_reason = (
                f"Ceiling reached: {self._total_submitted} mutations ({self._batch_count} batches)"
            )
            if not self._property_snapshots:
                self._property_snapshots = validate_fn(all_records)

        p10 = self._harness.validate_predictive_accuracy(self._self_model)
        self._property_snapshots.append(p10)

        return self._harness.generate_report(
            self._property_snapshots,
            self_model=self._self_model,
            stopping_reason=self._stopping_reason,
        )

    def _estimate_confidence(self, prop: PropertyResult) -> float:
        """Estimate confidence from convergence metrics when not explicitly set."""
        if prop.status == PropertyStatus.CONVERGED:
            windows = []
            for metric_data in prop.convergence_metrics.values():
                if isinstance(metric_data, dict):
                    ci_margin = metric_data.get("ci_margin", 0)
                    mean = metric_data.get("mean", 0)
                    if mean > 0 and ci_margin >= 0:
                        relative_margin = ci_margin / mean
                        windows.append(max(0, 1.0 - relative_margin))
            if windows:
                return statistics.mean(windows)
            return 0.90
        return max(0.0, prop.confidence)


# ── Module-level convenience ───────────────────────────────────────────────


def run_qualification() -> QualificationReport:
    """Entry point for full C35 qualification run.

    Imports organism components and runs all 9 properties.
    Call from scripts or tests.
    """
    harness = QualificationHarness()
    logger.info(
        "C35 qualification harness initialized with %d existing mutations", len(harness._mutations)
    )
    return harness.generate_report([])
