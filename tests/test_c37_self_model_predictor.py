"""Tests for C37 — PredictiveSelfModel with Welford variance and hierarchical keys."""

from __future__ import annotations

import math
import os
import statistics
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.organism.self_model_predictor import (
    METRICS,
    MIN_SAMPLES,
    PredictionResult,
    PredictiveSelfModel,
    WelfordAccumulator,
    _CLASS_PRIORS,
    _COLD_DEFAULTS,
)


# ── WelfordAccumulator ──────────────────────────────────────────────────


class TestWelfordAccumulator:
    def test_empty_accumulator(self) -> None:
        acc = WelfordAccumulator()
        assert acc.count == 0
        assert acc.mean == 0.0
        assert acc.variance() == 0.0
        assert acc.stddev() == 0.0
        assert acc.ci_margin() == float("inf")

    def test_single_value(self) -> None:
        acc = WelfordAccumulator()
        acc.update(42.0)
        assert acc.count == 1
        assert acc.mean == 42.0
        assert acc.variance() == 0.0
        assert acc.ci_margin() == float("inf")

    def test_known_sequence(self) -> None:
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        acc = WelfordAccumulator()
        for v in values:
            acc.update(v)
        assert acc.count == 5
        assert abs(acc.mean - statistics.mean(values)) < 1e-9
        assert abs(acc.variance() - statistics.variance(values)) < 1e-9
        assert abs(acc.stddev() - statistics.stdev(values)) < 1e-9

    def test_ci_margin_decreases_with_samples(self) -> None:
        acc = WelfordAccumulator()
        margins: list[float] = []
        for i in range(100):
            acc.update(50.0 + (i % 10))
            if acc.count >= 2:
                margins.append(acc.ci_margin())
        assert margins[-1] < margins[0]

    def test_to_dict_roundtrip(self) -> None:
        acc = WelfordAccumulator()
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            acc.update(v)
        d = acc.to_dict()
        assert d["count"] == 5
        assert "mean" in d
        assert "variance" in d
        assert "stddev" in d


# ── PredictionResult ────────────────────────────────────────────────────


class TestPredictionResult:
    def test_dataclass_fields(self) -> None:
        pr = PredictionResult(
            predicted_value=10.0,
            lower_bound=8.0,
            upper_bound=12.0,
            confidence=0.95,
            sample_size=50,
            model_used="welford",
            feature_key="state::settings_update",
        )
        assert pr.predicted_value == 10.0
        assert pr.contains(10.0)
        assert pr.contains(8.0)
        assert pr.contains(12.0)
        assert not pr.contains(7.99)
        assert not pr.contains(12.01)

    def test_cold_default_result(self) -> None:
        pr = PredictionResult()
        assert pr.model_used == "cold_default"
        assert pr.sample_size == 0
        assert pr.confidence == 0.0

    def test_to_dict(self) -> None:
        pr = PredictionResult(predicted_value=5.0, lower_bound=3.0, upper_bound=7.0)
        d = pr.to_dict()
        assert d["value"] == 5.0
        assert "model" in d
        assert "feature_key" in d


# ── PredictiveSelfModel ─────────────────────────────────────────────────


class _FakeSpec:
    def __init__(self, risk_level: str = "low") -> None:
        self.risk_level = risk_level


class _FakeRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, _FakeSpec] = {}

    def register(self, name: str, risk_level: str = "low") -> None:
        self._specs[name] = _FakeSpec(risk_level)

    def lookup(self, name: str) -> _FakeSpec | None:
        return self._specs.get(name)


class _FakeRecord:
    def __init__(
        self,
        action_type: str = "operate",
        mutation_name: str = "settings_update",
        success: bool = True,
        duration_ms: float = 50.0,
        governance_cost_ms: float = 0.1,
        template_matched: bool = False,
    ) -> None:
        self.action_type = action_type
        self.mutation_name = mutation_name
        self.success = success
        self.duration_ms = duration_ms
        self.governance_cost_ms = governance_cost_ms
        self.template_matched = template_matched


class TestPredictiveSelfModel:
    def test_cold_start_returns_class_prior(self) -> None:
        reg = _FakeRegistry()
        reg.register("settings_update", "low")
        model = PredictiveSelfModel(mutation_registry=reg)
        pred = model.predict("state", "settings_update")
        for metric in METRICS:
            assert metric in pred
            assert pred[metric].model_used in ("class_prior", "cold_default")
            assert pred[metric].sample_size == 0
            assert pred[metric].confidence == 0.1

    def test_cold_start_with_risk_level(self) -> None:
        reg = _FakeRegistry()
        reg.register("deployment", "high")
        model = PredictiveSelfModel(mutation_registry=reg)
        pred = model.predict("deploy", "deployment")
        assert pred["failure_prob"].predicted_value == _CLASS_PRIORS["high"]["failure_prob"]
        assert pred["duration_ms"].predicted_value == _CLASS_PRIORS["high"]["duration_ms"]

    def test_prediction_improves_with_data(self) -> None:
        model = PredictiveSelfModel()
        cold_errors: list[float] = []
        mature_errors: list[float] = []

        for i in range(50):
            actual_duration = 100.0 + (i % 5)
            pred = model.predict("state", "settings_update")
            cold_or_mature = pred["duration_ms"].model_used
            error = abs(pred["duration_ms"].predicted_value - actual_duration)
            if cold_or_mature in ("class_prior", "cold_default"):
                cold_errors.append(error)
            else:
                mature_errors.append(error)

            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": actual_duration,
                },
            )

        assert len(mature_errors) > 0
        avg_cold = statistics.mean(cold_errors) if cold_errors else float("inf")
        avg_mature = statistics.mean(mature_errors)
        assert avg_mature < avg_cold

    def test_hierarchical_key_resolution(self) -> None:
        model = PredictiveSelfModel()
        for i in range(20):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        for i in range(20):
            model.record_actual(
                "state",
                "runtime_refresh",
                {
                    "governance_cost_ms": 0.5,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 200.0,
                },
            )

        pred_su = model.predict("state", "settings_update")
        pred_rr = model.predict("state", "runtime_refresh")
        assert pred_su["duration_ms"].feature_key == "state::settings_update"
        assert pred_rr["duration_ms"].feature_key == "state::runtime_refresh"
        assert abs(pred_su["duration_ms"].predicted_value - 50.0) < 5.0
        assert abs(pred_rr["duration_ms"].predicted_value - 200.0) < 20.0

    def test_fallback_to_action_type_when_few_samples(self) -> None:
        model = PredictiveSelfModel()
        for i in range(20):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        for i in range(3):
            model.record_actual(
                "state",
                "config_set",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 60.0,
                },
            )

        pred = model.predict("state", "config_set")
        assert pred["duration_ms"].feature_key == "state"

    def test_record_actual_updates_accumulators(self) -> None:
        model = PredictiveSelfModel()
        model.record_actual(
            "state",
            "settings_update",
            {
                "governance_cost_ms": 0.1,
                "failure_prob": 0.0,
                "template_match": 0.0,
                "duration_ms": 50.0,
            },
        )
        assert "state::settings_update" in model._accumulators
        assert "state" in model._accumulators
        assert "__global__" in model._accumulators
        assert model._accumulators["state::settings_update"]["duration_ms"].count == 1

    def test_record_from_mutation_convenience(self) -> None:
        model = PredictiveSelfModel()
        record = _FakeRecord(
            action_type="state",
            mutation_name="settings_update",
            success=True,
            duration_ms=42.0,
            governance_cost_ms=0.05,
        )
        predicted = model.record_from_mutation(record)
        assert "duration_ms" in predicted
        assert len(model._predictions) == 1

    def test_calibration_score_with_variance_ci(self) -> None:
        model = PredictiveSelfModel()
        for i in range(20):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0 + (i % 3),
                },
            )

        for i in range(30):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0 + (i % 3),
                },
            )

        cal = model.calibration_score()
        assert 0.0 <= cal <= 1.0
        assert cal > 0.3

    def test_per_metric_accuracy(self) -> None:
        model = PredictiveSelfModel()
        for i in range(20):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        pma = model.per_metric_accuracy()
        assert "duration_ms" in pma
        assert "governance_cost_ms" in pma

    def test_cold_vs_mature_split(self) -> None:
        model = PredictiveSelfModel()
        for i in range(30):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        split = model.cold_vs_mature_accuracy()
        assert "cold_start" in split
        assert "mature" in split
        assert split["cold_start"].sample_size > 0
        assert split["mature"].sample_size > 0

    def test_worst_predictors(self) -> None:
        model = PredictiveSelfModel()
        for i in range(20):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        worst = model.worst_predictors(3)
        assert isinstance(worst, list)

    def test_diagnostics_structure(self) -> None:
        model = PredictiveSelfModel()
        for i in range(15):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        diag = model.diagnostics()
        assert "overall_mape" in diag
        assert "calibration_score" in diag
        assert "ci_coverage" in diag
        assert "per_metric" in diag
        assert "cold_vs_mature" in diag
        assert "worst_predictors" in diag
        assert "best_predictors" in diag
        assert "total_predictions" in diag
        assert diag["total_predictions"] == 15

    def test_persist_prediction_creates_file(self, tmp_path: str) -> None:
        model = PredictiveSelfModel()
        model._store_dir = str(tmp_path)
        pred = model.predict("state", "settings_update")
        actuals = {
            "governance_cost_ms": 0.1,
            "failure_prob": 0.0,
            "template_match": 0.0,
            "duration_ms": 50.0,
        }
        model.persist_prediction("state", "settings_update", pred, actuals)
        import json

        path = os.path.join(str(tmp_path), "predictions.jsonl")
        assert os.path.exists(path)
        with open(path) as f:
            record = json.loads(f.readline())
        assert record["action_type"] == "state"
        assert record["mutation_name"] == "settings_update"
        assert "predictions" in record
        assert "actuals" in record

    def test_prediction_accuracy_decreases_over_time(self) -> None:
        model = PredictiveSelfModel()
        errors_early: list[float] = []
        errors_late: list[float] = []

        for i in range(40):
            actual_d = 100.0
            pred = model.predict("state", "settings_update")
            error = abs(pred["duration_ms"].predicted_value - actual_d)
            if i < 10:
                errors_early.append(error)
            elif i >= 30:
                errors_late.append(error)

            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": actual_d,
                },
            )

        avg_early = statistics.mean(errors_early)
        avg_late = statistics.mean(errors_late)
        assert avg_late < avg_early


# ── Backward Compatibility ──────────────────────────────────────────────


class TestBackwardCompatibility:
    def test_predict_with_action_type_only(self) -> None:
        model = PredictiveSelfModel()
        pred = model.predict("state")
        assert "duration_ms" in pred
        assert "governance_cost_ms" in pred

    def test_record_from_mutation_same_fields(self) -> None:
        model = PredictiveSelfModel()
        record = _FakeRecord()
        predicted = model.record_from_mutation(record)
        assert isinstance(predicted, dict)
        for metric in METRICS:
            assert metric in predicted


# ── P10 Integration ─────────────────────────────────────────────────────


class TestP10Integration:
    def _make_trained_model(self, n: int = 100) -> PredictiveSelfModel:
        model = PredictiveSelfModel()
        for i in range(n):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0 + (i % 3),
                },
            )
        return model

    def test_p10_passes_at_60_percent_accuracy(self) -> None:
        model = self._make_trained_model(100)
        accuracy = model.prediction_accuracy()
        assert accuracy.value < 0.40

    def test_p10_fails_below_threshold(self) -> None:
        model = PredictiveSelfModel()
        for i in range(20):
            model.record_actual(
                "state",
                "settings_update",
                {
                    "governance_cost_ms": 0.1 * (i + 1),
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 10.0 * (i + 1),
                },
            )
        accuracy = model.prediction_accuracy()
        assert accuracy.value > 0.10

    def test_p10_reports_cold_vs_mature(self) -> None:
        model = self._make_trained_model(30)
        split = model.cold_vs_mature_accuracy()
        assert split["cold_start"].sample_size > 0
        assert split["mature"].sample_size > 0
        assert split["mature"].value < split["cold_start"].value

    def test_p10_reports_worst_predictors(self) -> None:
        model = self._make_trained_model(30)
        worst = model.worst_predictors(3)
        assert isinstance(worst, list)
        for item in worst:
            assert isinstance(item, tuple)
            assert len(item) == 2
