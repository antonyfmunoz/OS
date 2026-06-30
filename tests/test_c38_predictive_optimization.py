"""C38 Qualification-Driven Optimization Tests.

Tests Phase 1 (EMA-Welford blend), Phase 2 (fast-path population split),
and Phase 3 (robust error aggregation as secondary reporting metric).
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.self_model_predictor import (
    MIN_SAMPLES,
    PredictiveSelfModel,
    PredictionResult,
    _EMA_BLEND_EMA,
    _EMA_BLEND_WELFORD,
    _prediction_error,
)


# ── Phase 1: EMA-Welford Blend ──────────────────────────────────────────


class TestEMAWelfordBlend:
    def _build_model_with_shift(self):
        """Build model with 20 records at value X then 10 at 2X."""
        model = PredictiveSelfModel()
        for _ in range(20):
            model.record_actual(
                "test_action",
                "",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        for _ in range(10):
            model.record_actual(
                "test_action",
                "",
                {
                    "governance_cost_ms": 20.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 100.0,
                },
            )
        return model

    def test_ema_blend_tracks_shift(self):
        """Blended prediction closer to recent values than pure Welford."""
        model = self._build_model_with_shift()
        pred = model.predict("test_action")
        welford_mean_gov = (10.0 * 20 + 20.0 * 10) / 30
        assert pred["governance_cost_ms"].predicted_value > welford_mean_gov
        welford_mean_dur = (50.0 * 20 + 100.0 * 10) / 30
        assert pred["duration_ms"].predicted_value > welford_mean_dur

    def test_ema_blend_uses_welford_ci(self):
        """CI bounds come from Welford variance, not EMA."""
        model = self._build_model_with_shift()
        pred = model.predict("test_action")
        welford_mean = (10.0 * 20 + 20.0 * 10) / 30
        margin = pred["governance_cost_ms"].upper_bound - welford_mean
        assert margin > 0
        assert pred["governance_cost_ms"].lower_bound == pytest.approx(
            welford_mean - margin, abs=0.01
        )

    def test_no_ema_falls_back_to_welford(self):
        """With insufficient data for EMA blend, pure Welford used."""
        model = PredictiveSelfModel()
        for i in range(MIN_SAMPLES):
            model.record_actual(
                "test_action",
                "",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        pred = model.predict("test_action")
        assert pred["governance_cost_ms"].model_used == "welford"
        assert pred["governance_cost_ms"].predicted_value == pytest.approx(10.0, abs=0.1)

    def test_blend_activates_after_threshold(self):
        """EMA blend activates when count >= MIN_SAMPLES * 2."""
        model = PredictiveSelfModel()
        threshold = MIN_SAMPLES * 2
        for i in range(threshold + 5):
            model.record_actual(
                "blend_type",
                "",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        pred = model.predict("blend_type")
        assert pred["governance_cost_ms"].model_used == "welford+ema"

    def test_blend_weight_correctness(self):
        """Verify blend weights produce expected value."""
        model = PredictiveSelfModel()
        for _ in range(MIN_SAMPLES * 2 + 5):
            model.record_actual(
                "weight_test",
                "",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        pred = model.predict("weight_test")
        expected = _EMA_BLEND_WELFORD * 10.0 + _EMA_BLEND_EMA * 10.0
        assert pred["governance_cost_ms"].predicted_value == pytest.approx(
            expected, abs=0.1
        )


# ── Phase 2: Fast-Path Population Split ─────────────────────────────────


class TestFastPathSplit:
    def test_fp_split_separates_populations(self):
        """Fast-path and full-governance get different predictions."""
        model = PredictiveSelfModel()
        for _ in range(MIN_SAMPLES * 2 + 2):
            model.record_actual(
                "split_test",
                "",
                {
                    "governance_cost_ms": 0.001,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 20.0,
                },
                fast_path=True,
            )
            model.record_actual(
                "split_test",
                "",
                {
                    "governance_cost_ms": 5.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 80.0,
                },
                fast_path=False,
            )
        pred_fp = model.predict("split_test", fast_path=True)
        pred_full = model.predict("split_test", fast_path=False)
        assert pred_fp["governance_cost_ms"].predicted_value < 1.0
        assert pred_full["governance_cost_ms"].predicted_value > 1.0
        assert pred_fp["duration_ms"].predicted_value < 50.0
        assert pred_full["duration_ms"].predicted_value > 50.0

    def test_fp_fallback_to_general(self):
        """With few fp samples, falls back to standard accumulators."""
        model = PredictiveSelfModel()
        for _ in range(MIN_SAMPLES * 2 + 2):
            model.record_actual(
                "fallback_test",
                "",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
                fast_path=False,
            )
        for _ in range(2):
            model.record_actual(
                "fallback_test",
                "",
                {
                    "governance_cost_ms": 1.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 20.0,
                },
                fast_path=True,
            )
        pred_fp = model.predict("fallback_test", fast_path=True)
        assert pred_fp["governance_cost_ms"].predicted_value > 5.0

    def test_fp_feature_keys_structure(self):
        """Fast-path keys prepended before standard keys."""
        model = PredictiveSelfModel()
        keys = model._feature_keys("mutation_a", "filesystem", fast_path=True)
        assert keys[0] == "fp::filesystem::mutation_a"
        assert keys[1] == "fp::filesystem"
        assert "filesystem::mutation_a" in keys
        assert "filesystem" in keys
        assert "__global__" in keys

    def test_fp_feature_keys_without_fp(self):
        """Non-fast-path keys have no fp:: prefix."""
        model = PredictiveSelfModel()
        keys = model._feature_keys("mutation_a", "filesystem", fast_path=False)
        assert not any(k.startswith("fp::") for k in keys)
        assert keys[0] == "filesystem::mutation_a"

    def test_backward_compat_no_fp(self):
        """Default fast_path=False behaves identically to C37."""
        model = PredictiveSelfModel()
        for _ in range(MIN_SAMPLES * 2 + 2):
            model.record_actual(
                "compat_test",
                "",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        pred = model.predict("compat_test")
        assert "fp::" not in pred["governance_cost_ms"].feature_key

    def test_mixed_population_worse_than_split(self):
        """Splitting populations improves accuracy over mixing them."""
        errors_mixed: list[float] = []
        errors_split: list[float] = []

        fp_gov = 0.001
        full_gov = 5.0

        model_mixed = PredictiveSelfModel()
        model_split = PredictiveSelfModel()

        for _ in range(MIN_SAMPLES * 2 + 2):
            model_mixed.record_actual(
                "mix",
                "",
                {"governance_cost_ms": fp_gov, "failure_prob": 0.0,
                 "template_match": 0.0, "duration_ms": 20.0},
            )
            model_mixed.record_actual(
                "mix",
                "",
                {"governance_cost_ms": full_gov, "failure_prob": 0.0,
                 "template_match": 0.0, "duration_ms": 80.0},
            )
            model_split.record_actual(
                "mix",
                "",
                {"governance_cost_ms": fp_gov, "failure_prob": 0.0,
                 "template_match": 0.0, "duration_ms": 20.0},
                fast_path=True,
            )
            model_split.record_actual(
                "mix",
                "",
                {"governance_cost_ms": full_gov, "failure_prob": 0.0,
                 "template_match": 0.0, "duration_ms": 80.0},
                fast_path=False,
            )

        pred_mixed = model_mixed.predict("mix")
        pred_split_fp = model_split.predict("mix", fast_path=True)
        pred_split_full = model_split.predict("mix", fast_path=False)

        err_mixed_fp = abs(pred_mixed["duration_ms"].predicted_value - 20.0) / 20.0
        err_mixed_full = abs(pred_mixed["duration_ms"].predicted_value - 80.0) / 80.0
        err_split_fp = abs(pred_split_fp["duration_ms"].predicted_value - 20.0) / 20.0
        err_split_full = abs(pred_split_full["duration_ms"].predicted_value - 80.0) / 80.0

        avg_mixed = (err_mixed_fp + err_mixed_full) / 2
        avg_split = (err_split_fp + err_split_full) / 2
        assert avg_split < avg_mixed


# ── Phase 3: Robust Error Aggregation (secondary metric) ────────────────


class TestRobustErrorAggregation:
    def test_robust_accuracy_caps_errors(self):
        """Robust MAPE caps individual errors at 1.0."""
        model = PredictiveSelfModel()
        for _ in range(20):
            model.record_actual(
                "normal",
                "",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        model.record_actual(
            "outlier",
            "",
            {
                "governance_cost_ms": 0.001,
                "failure_prob": 0.0,
                "template_match": 0.0,
                "duration_ms": 1.0,
            },
        )
        primary = model.prediction_accuracy()
        robust = model.robust_prediction_accuracy()
        assert robust.value <= primary.value

    def test_robust_vs_primary_diverge_on_outliers(self):
        """Primary and robust metrics diverge when outliers present."""
        model = PredictiveSelfModel()
        for _ in range(50):
            model.record_actual(
                "stable",
                "",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        for _ in range(5):
            model.record_actual(
                "extreme",
                "",
                {
                    "governance_cost_ms": 0.0001,
                    "failure_prob": 1.0,
                    "template_match": 0.0,
                    "duration_ms": 0.1,
                },
            )
        primary = model.prediction_accuracy()
        robust = model.robust_prediction_accuracy()
        assert robust.value < primary.value

    def test_binary_metrics_unaffected_by_cap(self):
        """Binary metrics already bounded 0-1, cap doesn't change them."""
        err_binary = _prediction_error("failure_prob", 0.0, 1.0)
        assert err_binary == 1.0
        assert min(1.0, err_binary) == err_binary

    def test_diagnostics_includes_both_metrics(self):
        """diagnostics() reports both primary and robust MAPE."""
        model = PredictiveSelfModel()
        for _ in range(10):
            model.record_actual(
                "diag",
                "",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 0.0,
                    "duration_ms": 50.0,
                },
            )
        diag = model.diagnostics()
        assert "overall_mape" in diag
        assert "robust_mape" in diag


# ── Integration: C37 backward compatibility ─────────────────────────────


class TestC38BackwardCompat:
    def test_c37_api_unchanged(self):
        """All C37 public methods still work with no new required params."""
        model = PredictiveSelfModel()
        pred = model.predict("test")
        assert "governance_cost_ms" in pred
        model.record_actual(
            "test",
            "",
            {
                "governance_cost_ms": 10.0,
                "failure_prob": 0.0,
                "template_match": 0.0,
                "duration_ms": 50.0,
            },
        )
        _ = model.prediction_accuracy()
        _ = model.calibration_score()
        _ = model.per_metric_accuracy()
        _ = model.cold_vs_mature_accuracy()
        _ = model.worst_predictors()
        _ = model.best_predictors()
        _ = model.diagnostics()

    def test_existing_tests_unaffected(self):
        """SelfModel alias still works."""
        from substrate.organism.qualification_harness import SelfModel

        model = SelfModel()
        pred = model.predict("test")
        assert isinstance(pred, dict)
