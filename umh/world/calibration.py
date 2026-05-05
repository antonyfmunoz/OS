"""WorldCalibration — prediction vs reality error measurement for EOS.

Closes the loop between simulated futures and actual observed outcomes.
Every simulation prediction is stored, matched against later reality,
and scored to produce bounded error signals and model bias estimates.

All logic is deterministic, bounded, and domain-agnostic.
No LLM calls. No embeddings. No randomness. No external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from umh.world.types import (
    PrimitiveValue,
    StateFact,
    WorldSnapshot,
)
from umh.world.reasoning import (
    EntityAssessment,
    WorldUnderstanding,
    get_entity_assessment,
)

# ─── Constants ───────────────────────────────────────────────────

MAX_PREDICTION_RECORDS = 200
MAX_CALIBRATION_SUMMARIES = 200
ERROR_CLAMP = 1.0
BIAS_EMA_ALPHA = 0.2

# ─── Data models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class PredictionRecord:
    """Stored prediction from a simulation run."""

    action_id: str
    predicted_snapshot: WorldSnapshot
    predicted_understanding: WorldUnderstanding
    horizon: int
    timestamp_step: int

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "horizon": self.horizon,
            "timestamp_step": self.timestamp_step,
            "predicted_version": self.predicted_snapshot.version,
            "predicted_entity_count": len(self.predicted_snapshot.entities),
        }


@dataclass(frozen=True)
class OutcomeRecord:
    """Captured actual world state for comparison."""

    action_id: str
    actual_snapshot: WorldSnapshot
    actual_understanding: WorldUnderstanding
    timestamp_step: int

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "timestamp_step": self.timestamp_step,
            "actual_version": self.actual_snapshot.version,
            "actual_entity_count": len(self.actual_snapshot.entities),
        }


@dataclass(frozen=True)
class CalibrationError:
    """One entity-key level prediction error."""

    entity_id: str
    key: str
    predicted: PrimitiveValue
    actual: PrimitiveValue
    error_magnitude: float
    error_type: str

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "key": self.key,
            "predicted": self.predicted,
            "actual": self.actual,
            "error_magnitude": round(self.error_magnitude, 6),
            "error_type": self.error_type,
        }


@dataclass(frozen=True)
class CalibrationSummary:
    """Aggregate error summary for one prediction-outcome pair."""

    action_id: str
    avg_error: float
    max_error: float
    stability_error: float
    trend_error: float
    confidence_score: float
    error_count: int
    timestamp_step: int

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "avg_error": round(self.avg_error, 6),
            "max_error": round(self.max_error, 6),
            "stability_error": round(self.stability_error, 6),
            "trend_error": round(self.trend_error, 6),
            "confidence_score": round(self.confidence_score, 6),
            "error_count": self.error_count,
            "timestamp_step": self.timestamp_step,
        }


@dataclass(frozen=True)
class ModelBias:
    """Aggregated bias signals from calibration history."""

    trend_bias: float
    risk_propagation_bias: float
    stability_drift_bias: float
    confidence_bias: float

    def to_dict(self) -> dict:
        return {
            "trend_bias": round(self.trend_bias, 6),
            "risk_propagation_bias": round(self.risk_propagation_bias, 6),
            "stability_drift_bias": round(self.stability_drift_bias, 6),
            "confidence_bias": round(self.confidence_bias, 6),
        }


# ─── Error computation ──────────────────────────────────────────


def compute_fact_errors(
    predicted: WorldSnapshot,
    actual: WorldSnapshot,
) -> list[CalibrationError]:
    """Compare predicted vs actual state facts for all entities."""
    errors: list[CalibrationError] = []

    predicted_facts: dict[tuple[str, str], StateFact] = {
        (f.entity_id, f.key): f for f in predicted.state_facts
    }
    actual_facts: dict[tuple[str, str], StateFact] = {
        (f.entity_id, f.key): f for f in actual.state_facts
    }

    all_keys = sorted(set(predicted_facts.keys()) | set(actual_facts.keys()))

    for key in all_keys:
        p_fact = predicted_facts.get(key)
        a_fact = actual_facts.get(key)

        if p_fact is not None and a_fact is None:
            errors.append(
                CalibrationError(
                    entity_id=key[0],
                    key=key[1],
                    predicted=p_fact.value,
                    actual=None,
                    error_magnitude=ERROR_CLAMP,
                    error_type="missing",
                )
            )
            continue

        if p_fact is None and a_fact is not None:
            errors.append(
                CalibrationError(
                    entity_id=key[0],
                    key=key[1],
                    predicted=None,
                    actual=a_fact.value,
                    error_magnitude=ERROR_CLAMP,
                    error_type="missing",
                )
            )
            continue

        assert p_fact is not None and a_fact is not None

        p_val = p_fact.value
        a_val = a_fact.value

        if isinstance(p_val, bool) or isinstance(a_val, bool):
            mag = 0.0 if p_val == a_val else ERROR_CLAMP
            errors.append(
                CalibrationError(
                    entity_id=key[0],
                    key=key[1],
                    predicted=p_val,
                    actual=a_val,
                    error_magnitude=mag,
                    error_type="categorical",
                )
            )
        elif isinstance(p_val, (int, float)) and isinstance(a_val, (int, float)):
            diff = abs(float(p_val) - float(a_val))
            scale = max(abs(float(p_val)), abs(float(a_val)), 1.0)
            mag = min(ERROR_CLAMP, diff / scale)
            errors.append(
                CalibrationError(
                    entity_id=key[0],
                    key=key[1],
                    predicted=p_val,
                    actual=a_val,
                    error_magnitude=mag,
                    error_type="numeric",
                )
            )
        else:
            mag = 0.0 if p_val == a_val else ERROR_CLAMP
            errors.append(
                CalibrationError(
                    entity_id=key[0],
                    key=key[1],
                    predicted=p_val,
                    actual=a_val,
                    error_magnitude=mag,
                    error_type="categorical",
                )
            )

    return errors


def compute_classification_errors(
    predicted: WorldUnderstanding,
    actual: WorldUnderstanding,
) -> tuple[float, float]:
    """Compare predicted vs actual health/stability classifications.

    Returns (trend_error, stability_error) both in [0, 1].
    """
    p_map: dict[str, EntityAssessment] = {
        a.entity_id: a for a in predicted.entity_assessments
    }
    a_map: dict[str, EntityAssessment] = {
        a.entity_id: a for a in actual.entity_assessments
    }

    all_ids = sorted(set(p_map.keys()) | set(a_map.keys()))
    if not all_ids:
        return 0.0, 0.0

    health_mismatches = 0
    stability_mismatches = 0
    total = len(all_ids)

    for eid in all_ids:
        p_assess = p_map.get(eid)
        a_assess = a_map.get(eid)

        if p_assess is None or a_assess is None:
            health_mismatches += 1
            stability_mismatches += 1
            continue

        if p_assess.health != a_assess.health:
            health_mismatches += 1
        if p_assess.stability != a_assess.stability:
            stability_mismatches += 1

    trend_error = min(ERROR_CLAMP, health_mismatches / total)
    stability_error = min(ERROR_CLAMP, stability_mismatches / total)
    return trend_error, stability_error


# ─── Calibration summary ────────────────────────────────────────


def build_calibration_summary(
    action_id: str,
    fact_errors: list[CalibrationError],
    trend_error: float,
    stability_error: float,
    timestamp_step: int,
) -> CalibrationSummary:
    """Build a CalibrationSummary from computed errors."""
    if not fact_errors:
        return CalibrationSummary(
            action_id=action_id,
            avg_error=0.0,
            max_error=0.0,
            stability_error=stability_error,
            trend_error=trend_error,
            confidence_score=1.0,
            error_count=0,
            timestamp_step=timestamp_step,
        )

    magnitudes = [e.error_magnitude for e in fact_errors]
    avg_err = sum(magnitudes) / len(magnitudes)
    max_err = max(magnitudes)

    confidence = max(0.0, min(1.0, 1.0 - avg_err))

    return CalibrationSummary(
        action_id=action_id,
        avg_error=min(ERROR_CLAMP, avg_err),
        max_error=min(ERROR_CLAMP, max_err),
        stability_error=stability_error,
        trend_error=trend_error,
        confidence_score=confidence,
        error_count=len(fact_errors),
        timestamp_step=timestamp_step,
    )


# ─── Model bias computation ─────────────────────────────────────


def compute_model_bias(summaries: list[CalibrationSummary]) -> ModelBias:
    """Compute aggregated bias signals from calibration history.

    Each bias is in [-1, 1]:
    - positive = simulation overestimates (too optimistic)
    - negative = simulation underestimates (too pessimistic)
    """
    if not summaries:
        return ModelBias(
            trend_bias=0.0,
            risk_propagation_bias=0.0,
            stability_drift_bias=0.0,
            confidence_bias=0.0,
        )

    trend_errors = [s.trend_error for s in summaries]
    stability_errors = [s.stability_error for s in summaries]
    avg_errors = [s.avg_error for s in summaries]
    confidences = [s.confidence_score for s in summaries]

    trend_bias = _ema(trend_errors)
    risk_bias = _ema(avg_errors)
    stability_bias = _ema(stability_errors)

    confidence_avg = sum(confidences) / len(confidences)
    confidence_bias = confidence_avg - 0.5

    return ModelBias(
        trend_bias=_clamp_bias(trend_bias),
        risk_propagation_bias=_clamp_bias(risk_bias),
        stability_drift_bias=_clamp_bias(stability_bias),
        confidence_bias=_clamp_bias(confidence_bias),
    )


def _ema(values: list[float]) -> float:
    """Exponential moving average with recency weighting."""
    if not values:
        return 0.0
    result = values[0]
    for v in values[1:]:
        result = BIAS_EMA_ALPHA * v + (1.0 - BIAS_EMA_ALPHA) * result
    return result


def _clamp_bias(v: float) -> float:
    return max(-1.0, min(1.0, v))


# ─── Calibration Memory ─────────────────────────────────────────


class CalibrationMemory:
    """Bounded buffer of predictions, outcomes, and summaries."""

    def __init__(self, max_records: int = MAX_PREDICTION_RECORDS) -> None:
        self._max_records = max_records
        self._predictions: list[PredictionRecord] = []
        self._outcomes: list[OutcomeRecord] = []
        self._summaries: list[CalibrationSummary] = []

    def record_prediction(self, record: PredictionRecord) -> None:
        self._predictions.append(record)
        if len(self._predictions) > self._max_records:
            self._predictions = self._predictions[-self._max_records :]

    def record_outcome(self, record: OutcomeRecord) -> None:
        self._outcomes.append(record)
        if len(self._outcomes) > self._max_records:
            self._outcomes = self._outcomes[-self._max_records :]

    def add_summary(self, summary: CalibrationSummary) -> None:
        self._summaries.append(summary)
        if len(self._summaries) > MAX_CALIBRATION_SUMMARIES:
            self._summaries = self._summaries[-MAX_CALIBRATION_SUMMARIES:]

    @property
    def predictions(self) -> list[PredictionRecord]:
        return list(self._predictions)

    @property
    def outcomes(self) -> list[OutcomeRecord]:
        return list(self._outcomes)

    @property
    def summaries(self) -> list[CalibrationSummary]:
        return list(self._summaries)

    def pending_count(self) -> int:
        matched_ids = {s.action_id for s in self._summaries}
        return sum(1 for p in self._predictions if p.action_id not in matched_ids)

    def summary(self) -> dict:
        return {
            "prediction_count": len(self._predictions),
            "outcome_count": len(self._outcomes),
            "summary_count": len(self._summaries),
            "pending_count": self.pending_count(),
        }


# ─── World Calibration Engine ───────────────────────────────────


class WorldCalibrationEngine:
    """Measures simulation accuracy against observed reality.

    Workflow per turn:
    1. After simulation: record_prediction(...)
    2. After observation: record_outcome(...)
    3. match_predictions(current_step) — pairs mature predictions with outcomes
    4. get_model_bias() — aggregated bias signals for downstream use
    """

    def __init__(self, memory: CalibrationMemory | None = None) -> None:
        self._memory = memory or CalibrationMemory()

    @property
    def memory(self) -> CalibrationMemory:
        return self._memory

    def record_prediction(
        self,
        action_id: str,
        predicted_snapshot: WorldSnapshot,
        predicted_understanding: WorldUnderstanding,
        horizon: int,
        timestamp_step: int,
    ) -> PredictionRecord:
        """Store a simulation prediction for later comparison."""
        record = PredictionRecord(
            action_id=action_id,
            predicted_snapshot=predicted_snapshot,
            predicted_understanding=predicted_understanding,
            horizon=horizon,
            timestamp_step=timestamp_step,
        )
        self._memory.record_prediction(record)
        return record

    def record_outcome(
        self,
        action_id: str,
        actual_snapshot: WorldSnapshot,
        actual_understanding: WorldUnderstanding,
        timestamp_step: int,
    ) -> OutcomeRecord:
        """Capture the actual world state for comparison."""
        record = OutcomeRecord(
            action_id=action_id,
            actual_snapshot=actual_snapshot,
            actual_understanding=actual_understanding,
            timestamp_step=timestamp_step,
        )
        self._memory.record_outcome(record)
        return record

    def compute_error(
        self,
        prediction: PredictionRecord,
        outcome: OutcomeRecord,
    ) -> tuple[list[CalibrationError], CalibrationSummary]:
        """Compare a single prediction against its observed outcome."""
        fact_errors = compute_fact_errors(
            prediction.predicted_snapshot,
            outcome.actual_snapshot,
        )
        trend_error, stability_error = compute_classification_errors(
            prediction.predicted_understanding,
            outcome.actual_understanding,
        )
        summary = build_calibration_summary(
            action_id=prediction.action_id,
            fact_errors=fact_errors,
            trend_error=trend_error,
            stability_error=stability_error,
            timestamp_step=outcome.timestamp_step,
        )
        return fact_errors, summary

    def match_predictions(
        self,
        current_step: int,
    ) -> list[CalibrationSummary]:
        """Match mature predictions with outcomes and compute errors.

        A prediction is mature when current_step >= prediction.timestamp_step + horizon.
        Matching is by action_id: find the earliest outcome at or after the maturity step.
        """
        matched_ids = {s.action_id for s in self._memory.summaries}
        new_summaries: list[CalibrationSummary] = []

        outcome_by_id: dict[str, list[OutcomeRecord]] = {}
        for o in self._memory.outcomes:
            outcome_by_id.setdefault(o.action_id, []).append(o)

        for pred in self._memory.predictions:
            if pred.action_id in matched_ids:
                continue

            maturity = pred.timestamp_step + pred.horizon
            if current_step < maturity:
                continue

            candidates = outcome_by_id.get(pred.action_id, [])
            best_outcome: OutcomeRecord | None = None
            for o in candidates:
                if o.timestamp_step >= maturity:
                    if (
                        best_outcome is None
                        or o.timestamp_step < best_outcome.timestamp_step
                    ):
                        best_outcome = o

            if best_outcome is None:
                continue

            _, summary = self.compute_error(pred, best_outcome)
            self._memory.add_summary(summary)
            new_summaries.append(summary)
            matched_ids.add(pred.action_id)

        return new_summaries

    def get_model_bias(self) -> ModelBias:
        """Compute current aggregated model bias from calibration history."""
        return compute_model_bias(self._memory.summaries)

    def get_latest_summary(self) -> CalibrationSummary | None:
        """Return the most recent calibration summary."""
        if not self._memory.summaries:
            return None
        return self._memory.summaries[-1]

    def get_calibration_trace_fields(self) -> dict:
        """Extract trace-ready fields from current calibration state."""
        bias = self.get_model_bias()
        latest = self.get_latest_summary()
        return {
            "calibration_error": latest.avg_error if latest else None,
            "calibration_confidence": latest.confidence_score if latest else None,
            "calibration_trend_bias": bias.trend_bias,
            "calibration_risk_bias": bias.risk_propagation_bias,
        }
