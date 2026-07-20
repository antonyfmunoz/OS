"""PredictiveSelfModel — the organism's statistical self-prediction engine.

Tracks per-metric Welford accumulators at multiple feature-key granularities.
Produces calibrated predictions with confidence intervals. Deterministic-first:
rolling statistics, no LLM calls.

Hierarchical feature key resolution:
  Level 2: "{action_type}::{mutation_name}"  (most specific, >=10 samples)
  Level 1: "{action_type}"                   (fallback, >=10 samples)
  Level 0: "__global__"                      (last resort)
  Prior:   risk-level class prior or cold default

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import math
import os
import statistics
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

METRICS = ("governance_cost_ms", "failure_prob", "template_match", "duration_ms")
BINARY_METRICS = frozenset({"failure_prob", "template_match"})

MIN_SAMPLES = 5

_EMA_BLEND_WELFORD = 0.6
_EMA_BLEND_EMA = 0.4
_CI_FLOOR_PCT = 0.05
_CI_SMALL_SAMPLE_THRESHOLD = 30


_NEAR_ZERO_THRESHOLD = 1.0


def _prediction_error(metric: str, predicted: float, actual: float) -> float:
    if metric in BINARY_METRICS:
        return abs(predicted - actual)
    if abs(actual) < _NEAR_ZERO_THRESHOLD and abs(predicted) < _NEAR_ZERO_THRESHOLD:
        return abs(predicted - actual)
    if actual != 0:
        return abs(predicted - actual) / abs(actual)
    if predicted != 0:
        return 1.0
    return 0.0


_COLD_DEFAULTS: dict[str, float] = {
    "governance_cost_ms": 0.015,
    "failure_prob": 0.10,
    "template_match": 0.0,
    "duration_ms": 50.0,
}

_CLASS_PRIORS: dict[str, dict[str, float]] = {
    "low": {
        "governance_cost_ms": 0.012,
        "failure_prob": 0.05,
        "template_match": 0.0,
        "duration_ms": 45.0,
    },
    "medium": {
        "governance_cost_ms": 0.015,
        "failure_prob": 0.10,
        "template_match": 0.0,
        "duration_ms": 55.0,
    },
    "high": {
        "governance_cost_ms": 0.015,
        "failure_prob": 0.15,
        "template_match": 0.0,
        "duration_ms": 40.0,
    },
    "critical": {
        "governance_cost_ms": 0.020,
        "failure_prob": 0.20,
        "template_match": 0.0,
        "duration_ms": 35.0,
    },
}


# ── Welford Online Variance ─────────────────────────────────────────────


@dataclass
class WelfordAccumulator:
    """Welford's online algorithm for mean + variance in one pass."""

    count: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def update(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

    def variance(self) -> float:
        if self.count < 2:
            return 0.0
        return self.m2 / (self.count - 1)

    def stddev(self) -> float:
        return math.sqrt(self.variance())

    def ci_margin(self, confidence: float = 0.95) -> float:
        if self.count < 2:
            return float("inf")
        se = self.stddev() / math.sqrt(self.count)
        z = 1.96
        if self.count < 30:
            z *= 1.0 + 2.0 / max(self.count - 1, 1)
        return z * se

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mean": round(self.mean, 6),
            "variance": round(self.variance(), 6),
            "stddev": round(self.stddev(), 6),
        }


# ── Prediction Result ────────────────────────────────────────────────────


@dataclass
class PredictionResult:
    """Single prediction with confidence interval."""

    predicted_value: float = 0.0
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    confidence: float = 0.0
    sample_size: int = 0
    model_used: str = "cold_default"
    feature_key: str = ""

    def contains(self, actual: float) -> bool:
        return self.lower_bound <= actual <= self.upper_bound

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": round(self.predicted_value, 6),
            "lower": round(self.lower_bound, 6),
            "upper": round(self.upper_bound, 6),
            "confidence": round(self.confidence, 4),
            "sample_size": self.sample_size,
            "model": self.model_used,
            "feature_key": self.feature_key,
        }


# ── Predictive Self-Model ───────────────────────────────────────────────


class PredictiveSelfModel:
    """Organism's predictive model of its own execution behavior.

    Tracks per-metric Welford accumulators at multiple feature-key
    granularities. Produces calibrated predictions with confidence
    intervals. Deterministic-first: rolling statistics, no LLM calls.
    """

    def __init__(self, mutation_registry: Any = None) -> None:
        self._accumulators: dict[str, dict[str, WelfordAccumulator]] = {}
        self._ema: dict[str, dict[str, float]] = {}
        self._alpha = 0.3
        self._predictions: list[tuple[dict[str, PredictionResult], dict[str, float], str, str]] = []
        self._calibration_hits: int = 0
        self._calibration_total: int = 0
        self._registry = mutation_registry
        from substrate.state.runtime_paths import runtime_state_dir

        self._store_dir = str(runtime_state_dir("qualification", create=False))

    # ── Feature key hierarchy ────────────────────────────────────────

    def _feature_keys(
        self, mutation_name: str, action_type: str, fast_path: bool = False
    ) -> list[str]:
        keys: list[str] = []
        if fast_path:
            if mutation_name and action_type:
                keys.append(f"fp::{action_type}::{mutation_name}")
            if action_type:
                keys.append(f"fp::{action_type}")
        if mutation_name and action_type:
            keys.append(f"{action_type}::{mutation_name}")
        if action_type:
            keys.append(action_type)
        keys.append("__global__")
        return keys

    def _resolve_risk(self, mutation_name: str) -> str:
        if self._registry and mutation_name:
            spec = self._registry.lookup(mutation_name)
            if spec:
                return getattr(spec, "risk_level", "")
        return ""

    def _get_accumulator(self, feature_key: str, metric: str) -> WelfordAccumulator:
        if feature_key not in self._accumulators:
            self._accumulators[feature_key] = {}
        if metric not in self._accumulators[feature_key]:
            self._accumulators[feature_key][metric] = WelfordAccumulator()
        return self._accumulators[feature_key][metric]

    # ── Prediction ───────────────────────────────────────────────────

    def predict(
        self,
        action_type: str,
        mutation_name: str = "",
        risk_level: str = "",
        fast_path: bool = False,
    ) -> dict[str, PredictionResult]:
        if not risk_level and mutation_name:
            risk_level = self._resolve_risk(mutation_name)

        keys = self._feature_keys(mutation_name, action_type, fast_path=fast_path)
        results: dict[str, PredictionResult] = {}
        for metric in METRICS:
            results[metric] = self._predict_metric(
                metric, keys, risk_level, action_type=action_type
            )
        return results

    def _predict_metric(
        self,
        metric: str,
        feature_keys: list[str],
        risk_level: str,
        action_type: str = "",
    ) -> PredictionResult:
        for key in feature_keys:
            acc = self._accumulators.get(key, {}).get(metric)
            if acc and acc.count >= MIN_SAMPLES:
                raw_margin = max(acc.ci_margin(), abs(acc.mean) * _CI_FLOOR_PCT)
                if acc.count < _CI_SMALL_SAMPLE_THRESHOLD:
                    margin = raw_margin * math.sqrt(_CI_SMALL_SAMPLE_THRESHOLD / acc.count)
                else:
                    margin = raw_margin
                confidence = min(1.0, acc.count / 100.0)
                predicted = acc.mean
                model = "welford"
                if (
                    not key.startswith("fp::")
                    and key != "__global__"
                    and acc.count >= MIN_SAMPLES * 2
                ):
                    ema_val = self._ema.get(key, {}).get(metric)
                    if ema_val is not None:
                        predicted = _EMA_BLEND_WELFORD * acc.mean + _EMA_BLEND_EMA * ema_val
                        model = "welford+ema"
                return PredictionResult(
                    predicted_value=predicted,
                    lower_bound=acc.mean - margin,
                    upper_bound=acc.mean + margin,
                    confidence=confidence,
                    sample_size=acc.count,
                    model_used=model,
                    feature_key=key,
                )

        prior = _CLASS_PRIORS.get(risk_level, {})
        default_val = prior.get(metric, _COLD_DEFAULTS[metric])
        wide = max(abs(default_val) * 5.0, 1.0)
        return PredictionResult(
            predicted_value=default_val,
            lower_bound=default_val - wide,
            upper_bound=default_val + wide,
            confidence=0.1,
            sample_size=0,
            model_used="class_prior" if risk_level in _CLASS_PRIORS else "cold_default",
            feature_key=f"prior::{risk_level}" if risk_level else "cold_default",
        )

    # ── Recording ────────────────────────────────────────────────────

    def record_actual(
        self,
        action_type: str,
        mutation_name: str,
        actuals: dict[str, float],
        risk_level: str = "",
        fast_path: bool = False,
    ) -> dict[str, PredictionResult]:
        if not risk_level and mutation_name:
            risk_level = self._resolve_risk(mutation_name)

        predicted = self.predict(action_type, mutation_name, risk_level, fast_path=fast_path)
        self._predictions.append((predicted, actuals, action_type, mutation_name))

        for metric in METRICS:
            if metric in predicted and metric in actuals:
                pred = predicted[metric]
                actual_val = actuals[metric]
                self._calibration_total += 1
                if pred.contains(actual_val):
                    self._calibration_hits += 1

        keys = self._feature_keys(mutation_name, action_type, fast_path=fast_path)
        for key in keys:
            for metric, val in actuals.items():
                if metric in METRICS:
                    acc = self._get_accumulator(key, metric)
                    acc.update(val)

        for metric, val in actuals.items():
            if metric in METRICS:
                self._update_ema(action_type, metric, val)
                for key in keys:
                    if key != "__global__":
                        self._update_ema_keyed(key, metric, val)

        return predicted

    def record_from_mutation(self, record: Any) -> dict[str, PredictionResult]:
        actuals = {
            "governance_cost_ms": record.governance_cost_ms,
            "failure_prob": 0.0 if record.success else 1.0,
            "template_match": 1.0 if record.template_matched else 0.0,
            "duration_ms": record.duration_ms,
        }
        fp = getattr(record, "fast_path_used", False)
        return self.record_actual(
            action_type=record.action_type,
            mutation_name=record.mutation_name,
            actuals=actuals,
            fast_path=fp,
        )

    # ── EMA tracking ──────────────────────────────────────────────

    def _update_ema(self, action_type: str, metric: str, value: float) -> None:
        if action_type not in self._ema:
            self._ema[action_type] = {}
        prev = self._ema[action_type].get(metric, value)
        self._ema[action_type][metric] = self._alpha * value + (1 - self._alpha) * prev

    def _update_ema_keyed(self, feature_key: str, metric: str, value: float) -> None:
        if feature_key not in self._ema:
            self._ema[feature_key] = {}
        prev = self._ema[feature_key].get(metric, value)
        self._ema[feature_key][metric] = self._alpha * value + (1 - self._alpha) * prev

    # ── Accuracy metrics ─────────────────────────────────────────────

    def prediction_accuracy(self) -> Any:
        from substrate.organism.qualification_harness import ConfidenceEstimate

        if not self._predictions:
            return ConfidenceEstimate()

        errors: list[float] = []
        for pred_dict, actual_dict, _, _ in self._predictions:
            for metric in METRICS:
                if metric not in pred_dict or metric not in actual_dict:
                    continue
                p = pred_dict[metric].predicted_value
                a = actual_dict[metric]
                err = _prediction_error(metric, p, a)
                if err > 0 or a != 0 or p != 0:
                    errors.append(err)

        if not errors:
            return ConfidenceEstimate()
        return ConfidenceEstimate.from_samples(errors)

    def robust_prediction_accuracy(self) -> Any:
        """Secondary metric: capped MAPE (max 1.0 per error) for outlier-robust reporting."""
        from substrate.organism.qualification_harness import ConfidenceEstimate

        if not self._predictions:
            return ConfidenceEstimate()

        errors: list[float] = []
        for pred_dict, actual_dict, _, _ in self._predictions:
            for metric in METRICS:
                if metric not in pred_dict or metric not in actual_dict:
                    continue
                p = pred_dict[metric].predicted_value
                a = actual_dict[metric]
                err = min(1.0, _prediction_error(metric, p, a))
                if err > 0 or a != 0 or p != 0:
                    errors.append(err)

        if not errors:
            return ConfidenceEstimate()
        return ConfidenceEstimate.from_samples(errors)

    def calibration_score(self) -> float:
        if self._calibration_total == 0:
            return 0.0
        return self._calibration_hits / self._calibration_total

    def per_metric_accuracy(self) -> dict[str, Any]:
        from substrate.organism.qualification_harness import ConfidenceEstimate

        by_metric: dict[str, list[float]] = {}
        for pred_dict, actual_dict, _, _ in self._predictions:
            for metric in METRICS:
                if metric not in pred_dict or metric not in actual_dict:
                    continue
                p = pred_dict[metric].predicted_value
                a = actual_dict[metric]
                error = _prediction_error(metric, p, a)
                by_metric.setdefault(metric, []).append(error)
        return {k: ConfidenceEstimate.from_samples(v) for k, v in by_metric.items()}

    def per_action_type_accuracy(self) -> dict[str, Any]:
        from substrate.organism.qualification_harness import ConfidenceEstimate

        by_type: dict[str, list[float]] = {}
        for pred_dict, actual_dict, action_type, _ in self._predictions:
            for metric in METRICS:
                if metric not in pred_dict or metric not in actual_dict:
                    continue
                p = pred_dict[metric].predicted_value
                a = actual_dict[metric]
                error = _prediction_error(metric, p, a)
                by_type.setdefault(action_type, []).append(error)
        return {k: ConfidenceEstimate.from_samples(v) for k, v in by_type.items()}

    def cold_vs_mature_accuracy(self) -> dict[str, Any]:
        from substrate.organism.qualification_harness import ConfidenceEstimate

        cold_errors: list[float] = []
        mature_errors: list[float] = []
        for pred_dict, actual_dict, _, _ in self._predictions:
            for metric in METRICS:
                if metric not in pred_dict or metric not in actual_dict:
                    continue
                pred = pred_dict[metric]
                p = pred.predicted_value
                a = actual_dict[metric]
                error = _prediction_error(metric, p, a)
                if pred.model_used in ("class_prior", "cold_default"):
                    cold_errors.append(error)
                else:
                    mature_errors.append(error)
        return {
            "cold_start": (
                ConfidenceEstimate.from_samples(cold_errors)
                if cold_errors
                else ConfidenceEstimate()
            ),
            "mature": (
                ConfidenceEstimate.from_samples(mature_errors)
                if mature_errors
                else ConfidenceEstimate()
            ),
        }

    def worst_predictors(self, n: int = 5) -> list[tuple[str, float]]:
        by_key: dict[str, list[float]] = {}
        for pred_dict, actual_dict, _, _ in self._predictions:
            for metric in METRICS:
                if metric not in pred_dict or metric not in actual_dict:
                    continue
                pred = pred_dict[metric]
                p = pred.predicted_value
                a = actual_dict[metric]
                error = _prediction_error(metric, p, a)
                by_key.setdefault(pred.feature_key, []).append(error)
        averages = [(k, statistics.mean(v)) for k, v in by_key.items() if len(v) >= 5]
        averages.sort(key=lambda x: x[1], reverse=True)
        return averages[:n]

    def best_predictors(self, n: int = 5) -> list[tuple[str, float]]:
        by_key: dict[str, list[float]] = {}
        for pred_dict, actual_dict, _, _ in self._predictions:
            for metric in METRICS:
                if metric not in pred_dict or metric not in actual_dict:
                    continue
                pred = pred_dict[metric]
                p = pred.predicted_value
                a = actual_dict[metric]
                error = _prediction_error(metric, p, a)
                by_key.setdefault(pred.feature_key, []).append(error)
        averages = [(k, statistics.mean(v)) for k, v in by_key.items() if len(v) >= 5]
        averages.sort(key=lambda x: x[1])
        return averages[:n]

    # ── Persistence ──────────────────────────────────────────────────

    def persist_prediction(
        self,
        action_type: str,
        mutation_name: str,
        predicted: dict[str, PredictionResult],
        actuals: dict[str, float],
    ) -> None:
        os.makedirs(self._store_dir, exist_ok=True)
        path = os.path.join(self._store_dir, "predictions.jsonl")
        record = {
            "timestamp": time.time(),
            "action_type": action_type,
            "mutation_name": mutation_name,
            "predictions": {k: v.to_dict() for k, v in predicted.items()},
            "actuals": actuals,
            "calibration_score": self.calibration_score(),
        }
        try:
            with open(path, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except OSError as exc:
            logger.debug("Cannot write prediction record: %s", exc)

    # ── Diagnostics ──────────────────────────────────────────────────

    def diagnostics(self) -> dict[str, Any]:
        accuracy = self.prediction_accuracy()
        robust = self.robust_prediction_accuracy()
        cold_mature = self.cold_vs_mature_accuracy()
        return {
            "overall_mape": accuracy.to_dict(),
            "robust_mape": robust.to_dict(),
            "calibration_score": round(self.calibration_score(), 4),
            "ci_coverage": round(self.calibration_score(), 4),
            "per_metric": {k: v.to_dict() for k, v in self.per_metric_accuracy().items()},
            "cold_vs_mature": {k: v.to_dict() for k, v in cold_mature.items()},
            "worst_predictors": self.worst_predictors(),
            "best_predictors": self.best_predictors(),
            "total_predictions": len(self._predictions),
            "accumulator_count": sum(len(v) for v in self._accumulators.values()),
            "feature_keys_tracked": len(self._accumulators),
        }
