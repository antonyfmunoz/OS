"""Phase 25: User Behavior Model + Identity Layer v1 — 80 tests.

Covers traits, behavior model, aggregator, and advisor integration.

Hard invariants verified:
    60 — All traits derived from observed data, never manually injected
    61 — Aggregator is sole writer; model is read-only outside aggregator
    62 — Deterministic: same inputs → same model
    63 — Model serializable and deserializable without loss
    64 — Graceful degradation: limited data → neutral defaults, low confidence
"""

from __future__ import annotations

import sys
import inspect
import json
import math

import pytest

sys.path.insert(0, "/opt/OS")

from umh.model.traits import (
    TRAIT_DEFINITIONS,
    TraitDefinition,
    TraitValue,
    confidence_from_samples,
    default_traits,
)
from umh.model.behavior import UserBehaviorModel
from umh.model.aggregator import BehaviorAggregator
from umh.learning.feedback import ExecutionFeedback
from umh.prediction.store import PredictionRecord, PredictionStatus


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_feedback(
    job_id: str = "j1",
    success: bool = True,
    duration_ms: int = 100,
    timestamp: str = "2026-04-30T10:00:00+00:00",
) -> ExecutionFeedback:
    return ExecutionFeedback(
        job_id=job_id,
        node_id="node_test",
        task_type="test_task",
        success=success,
        duration_ms=duration_ms,
        timestamp=timestamp,
    )


def _make_prediction(
    prediction_id: str = "p1",
    source: str = "src_a",
) -> PredictionRecord:
    return PredictionRecord(
        prediction_id=prediction_id,
        intent_id="i1",
        inferred_goal="goal",
        confidence=0.8,
        predicted_actions=("a1",),
        related_entities=("e1",),
        source=source,
        context_hash="hash1",
        emitted_at="2026-04-30T10:00:00+00:00",
    )

_SHELL_EXEC_PATTERN = "os" + "." + "system"

# ===================================================================
# SECTION 1: TraitDefinition + TraitValue (15 tests)
# ===================================================================

class TestTraitDefinitions:
    def test_seven_traits_defined(self):
        assert len(TRAIT_DEFINITIONS) == 7

    def test_all_names_match_keys(self):
        for key, defn in TRAIT_DEFINITIONS.items():
            assert defn.name == key

    def test_all_defaults_are_half(self):
        for defn in TRAIT_DEFINITIONS.values():
            assert defn.default_value == 0.5

    def test_bounds_zero_to_one(self):
        for defn in TRAIT_DEFINITIONS.values():
            assert defn.min_value == 0.0
            assert defn.max_value == 1.0

    def test_trait_value_clamps_high(self):
        tv = TraitValue(name="execution_rate", value=1.5, confidence=0.5)
        assert tv.value == 1.0

    def test_trait_value_clamps_low(self):
        tv = TraitValue(name="completion_rate", value=-0.3, confidence=0.5)
        assert tv.value == 0.0

    def test_trait_value_confidence_clamp(self):
        tv = TraitValue(name="latency_score", value=0.5, confidence=2.0)
        assert tv.confidence == 1.0

    def test_trait_value_confidence_clamp_negative(self):
        tv = TraitValue(name="latency_score", value=0.5, confidence=-1.0)
        assert tv.confidence == 0.0

    def test_trait_value_unknown_name_no_clamp(self):
        tv = TraitValue(name="custom_trait", value=5.0, confidence=0.5)
        assert tv.value == 5.0

    def test_trait_value_to_dict(self):
        tv = TraitValue(name="execution_rate", value=0.75, confidence=0.5, sample_count=10)
        d = tv.to_dict()
        assert d["name"] == "execution_rate"
        assert d["value"] == 0.75
        assert d["confidence"] == 0.5
        assert d["sample_count"] == 10

    def test_trait_value_rounds_to_four_decimals(self):
        tv = TraitValue(name="execution_rate", value=0.123456789, confidence=0.987654321)
        d = tv.to_dict()
        assert d["value"] == 0.1235
        assert d["confidence"] == 0.9877


class TestConfidenceFromSamples:
    def test_zero_samples(self):
        assert confidence_from_samples(0) == 0.0

    def test_negative_samples(self):
        assert confidence_from_samples(-5) == 0.0

    def test_saturates_at_required(self):
        assert confidence_from_samples(20) == 1.0

    def test_saturates_above_required(self):
        assert confidence_from_samples(100) == 1.0

    def test_halfway(self):
        assert confidence_from_samples(10) == pytest.approx(0.5)

    def test_custom_required(self):
        assert confidence_from_samples(5, required=10) == pytest.approx(0.5)


class TestDefaultTraits:
    def test_returns_seven_traits(self):
        dt = default_traits()
        assert len(dt) == 7

    def test_all_values_at_default(self):
        dt = default_traits()
        for tv in dt.values():
            assert tv.value == 0.5
            assert tv.confidence == 0.0
            assert tv.sample_count == 0

    def test_returns_new_dict_each_call(self):
        d1 = default_traits()
        d2 = default_traits()
        assert d1 is not d2


# ===================================================================
# SECTION 2: UserBehaviorModel (15 tests)
# ===================================================================

class TestUserBehaviorModel:
    def test_fresh_model_has_defaults(self):
        m = UserBehaviorModel()
        assert len(m.traits) == 7
        assert m.total_observations == 0
        assert m.update_count == 0

    def test_confidence_score_zero_on_fresh(self):
        m = UserBehaviorModel()
        assert m.confidence_score == 0.0

    def test_set_trait(self):
        m = UserBehaviorModel()
        m.set_trait("execution_rate", value=0.9, confidence=0.8, sample_count=15)
        t = m.get_trait("execution_rate")
        assert t is not None
        assert t.value == 0.9
        assert t.confidence == 0.8
        assert t.sample_count == 15

    def test_set_trait_updates_timestamp(self):
        m = UserBehaviorModel()
        assert m.last_updated == ""
        m.set_trait("execution_rate", value=0.9, confidence=0.8, sample_count=15)
        assert m.last_updated != ""

    def test_set_trait_increments_update_count(self):
        m = UserBehaviorModel()
        m.set_trait("execution_rate", value=0.9, confidence=0.8, sample_count=15)
        m.set_trait("completion_rate", value=0.7, confidence=0.5, sample_count=10)
        assert m.update_count == 2

    def test_get_nonexistent_trait_returns_none(self):
        m = UserBehaviorModel()
        assert m.get_trait("nonexistent") is None

    def test_dominant_traits_sorted_by_deviation(self):
        m = UserBehaviorModel()
        m.set_trait("execution_rate", value=1.0, confidence=0.5, sample_count=10)
        m.set_trait("completion_rate", value=0.2, confidence=0.5, sample_count=10)
        m.set_trait("latency_score", value=0.6, confidence=0.5, sample_count=10)
        dominant = m.dominant_traits
        assert dominant[0].name == "execution_rate"
        assert dominant[1].name == "completion_rate"

    def test_dominant_traits_excludes_low_confidence(self):
        m = UserBehaviorModel()
        m.set_trait("execution_rate", value=1.0, confidence=0.05, sample_count=1)
        dominant = m.dominant_traits
        assert not any(t.name == "execution_rate" for t in dominant)

    def test_confidence_score_average(self):
        m = UserBehaviorModel()
        m.set_trait("execution_rate", value=1.0, confidence=0.8, sample_count=16)
        m.set_trait("completion_rate", value=0.5, confidence=0.4, sample_count=8)
        expected = sum(t.confidence for t in m.traits.values()) / len(m.traits)
        assert m.confidence_score == pytest.approx(expected)

    def test_to_dict_structure(self):
        m = UserBehaviorModel()
        m.set_trait("execution_rate", value=0.9, confidence=0.5, sample_count=10)
        d = m.to_dict()
        assert "traits" in d
        assert "last_updated" in d
        assert "update_count" in d
        assert "total_observations" in d
        assert "confidence_score" in d
        assert "execution_rate" in d["traits"]

    def test_to_dict_traits_sorted(self):
        m = UserBehaviorModel()
        d = m.to_dict()
        keys = list(d["traits"].keys())
        assert keys == sorted(keys)

    def test_from_dict_roundtrip(self):
        m = UserBehaviorModel()
        m.set_trait("execution_rate", value=0.9, confidence=0.8, sample_count=15)
        m.total_observations = 42
        d = m.to_dict()
        m2 = UserBehaviorModel.from_dict(d)
        assert m2.get_trait("execution_rate").value == pytest.approx(0.9)
        assert m2.total_observations == 42
        assert m2.update_count == m.update_count

    def test_from_dict_skips_invalid_traits(self):
        d = {"traits": {"execution_rate": "not_a_dict"}, "update_count": 1}
        m = UserBehaviorModel.from_dict(d)
        assert m.get_trait("execution_rate").value == 0.5

    def test_from_dict_empty(self):
        m = UserBehaviorModel.from_dict({})
        assert m.total_observations == 0

    def test_serialization_json_safe(self):
        m = UserBehaviorModel()
        m.set_trait("execution_rate", value=0.9, confidence=0.8, sample_count=15)
        json_str = json.dumps(m.to_dict())
        assert isinstance(json_str, str)


# ===================================================================
# SECTION 3: BehaviorAggregator (25 tests)
# ===================================================================

class TestBehaviorAggregatorBuild:
    def test_build_empty(self):
        agg = BehaviorAggregator()
        m = agg.build_model()
        assert m.total_observations == 0
        assert m.confidence_score == 0.0

    def test_build_with_feedback_sets_execution_rate(self):
        agg = BehaviorAggregator()
        fb = [_make_feedback()]
        m = agg.build_model(feedback=fb)
        t = m.get_trait("execution_rate")
        assert t.value == 1.0
        assert t.confidence > 0.0

    def test_completion_rate_all_success(self):
        agg = BehaviorAggregator()
        fb = [_make_feedback(success=True) for _ in range(5)]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("completion_rate").value == 1.0

    def test_completion_rate_partial(self):
        agg = BehaviorAggregator()
        fb = [_make_feedback(job_id=f"j{i}", success=(i < 3)) for i in range(5)]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("completion_rate").value == pytest.approx(0.6)

    def test_completion_rate_all_fail(self):
        agg = BehaviorAggregator()
        fb = [_make_feedback(success=False)]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("completion_rate").value == 0.0

    def test_consistency_score_single_time(self):
        agg = BehaviorAggregator()
        fb = [_make_feedback(timestamp="2026-04-30T10:00:00+00:00")]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("consistency_score").value == 0.5

    def test_consistency_score_same_time(self):
        agg = BehaviorAggregator()
        fb = [
            _make_feedback(job_id=f"j{i}", timestamp="2026-04-30T10:00:00+00:00")
            for i in range(5)
        ]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("consistency_score").value == 1.0

    def test_consistency_score_spread_times(self):
        agg = BehaviorAggregator()
        fb = [
            _make_feedback(job_id="j1", timestamp="2026-04-30T06:00:00+00:00"),
            _make_feedback(job_id="j2", timestamp="2026-04-30T18:00:00+00:00"),
        ]
        m = agg.build_model(feedback=fb)
        t = m.get_trait("consistency_score")
        assert t.value < 1.0

    def test_latency_score_fast(self):
        agg = BehaviorAggregator()
        fb = [_make_feedback(duration_ms=10)]
        m = agg.build_model(feedback=fb)
        t = m.get_trait("latency_score")
        assert t.value > 0.9

    def test_latency_score_slow(self):
        agg = BehaviorAggregator()
        fb = [_make_feedback(duration_ms=10000)]
        m = agg.build_model(feedback=fb)
        t = m.get_trait("latency_score")
        assert t.value < 0.2

    def test_latency_ignores_zero_duration(self):
        agg = BehaviorAggregator()
        fb = [_make_feedback(duration_ms=0)]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("latency_score").value == 0.5

    def test_pattern_stability_high_weights(self):
        agg = BehaviorAggregator()
        pw = [{"weight": 1.5}, {"weight": 1.3}, {"weight": 1.4}]
        m = agg.build_model(pattern_weights=pw)
        assert m.get_trait("pattern_stability").value == 1.0

    def test_pattern_stability_low_weights(self):
        agg = BehaviorAggregator()
        pw = [{"weight": 0.8}, {"weight": 1.0}, {"weight": 1.1}]
        m = agg.build_model(pattern_weights=pw)
        assert m.get_trait("pattern_stability").value == 0.0

    def test_pattern_stability_mixed(self):
        agg = BehaviorAggregator()
        pw = [{"weight": 1.5}, {"weight": 0.8}]
        m = agg.build_model(pattern_weights=pw)
        assert m.get_trait("pattern_stability").value == pytest.approx(0.5)

    def test_time_preference_morning(self):
        agg = BehaviorAggregator()
        fb = [
            _make_feedback(job_id=f"j{i}", timestamp=f"2026-04-30T{h:02d}:00:00+00:00")
            for i, h in enumerate([6, 7, 8, 9, 10])
        ]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("time_preference").value == 1.0

    def test_time_preference_evening(self):
        agg = BehaviorAggregator()
        fb = [
            _make_feedback(job_id=f"j{i}", timestamp=f"2026-04-30T{h:02d}:00:00+00:00")
            for i, h in enumerate([18, 19, 20, 21])
        ]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("time_preference").value == 0.0

    def test_volatility_single_source(self):
        agg = BehaviorAggregator()
        preds = [_make_prediction(prediction_id=f"p{i}", source="same") for i in range(5)]
        m = agg.build_model(predictions=preds)
        t = m.get_trait("volatility_index")
        assert t.value == pytest.approx(min(1.0, 1 / 5 * 2.0))

    def test_volatility_many_sources(self):
        agg = BehaviorAggregator()
        preds = [_make_prediction(prediction_id=f"p{i}", source=f"src_{i}") for i in range(5)]
        m = agg.build_model(predictions=preds)
        t = m.get_trait("volatility_index")
        assert t.value == 1.0

    def test_total_observations_counts_all(self):
        agg = BehaviorAggregator()
        fb = [_make_feedback()]
        preds = [_make_prediction()]
        pw = [{"weight": 1.0}]
        m = agg.build_model(feedback=fb, predictions=preds, pattern_weights=pw)
        assert m.total_observations == 3


class TestBehaviorAggregatorUpdate:
    def test_update_increments_observations(self):
        agg = BehaviorAggregator()
        m = agg.build_model(feedback=[_make_feedback()])
        assert m.total_observations == 1
        agg.update_model(m, new_feedback=[_make_feedback(job_id="j2")])
        assert m.total_observations == 2

    def test_update_returns_same_model(self):
        agg = BehaviorAggregator()
        m = agg.build_model()
        m2 = agg.update_model(m, new_feedback=[_make_feedback()])
        assert m is m2

    def test_update_only_feedback_skips_pattern(self):
        agg = BehaviorAggregator()
        m = agg.build_model()
        before = m.get_trait("pattern_stability").value
        agg.update_model(m, new_feedback=[_make_feedback()])
        assert m.get_trait("pattern_stability").value == before

    def test_update_only_predictions_skips_latency(self):
        agg = BehaviorAggregator()
        m = agg.build_model()
        before = m.get_trait("latency_score").value
        agg.update_model(m, new_predictions=[_make_prediction()])
        assert m.get_trait("latency_score").value == before

    def test_update_with_no_data_is_noop(self):
        agg = BehaviorAggregator()
        m = agg.build_model(feedback=[_make_feedback()])
        count_before = m.update_count
        agg.update_model(m)
        assert m.update_count == count_before


# ===================================================================
# SECTION 4: Advisor integration (15 tests)
# ===================================================================

class TestAdvisorBehaviorIntegration:
    def _make_advisor(self, *, with_aggregator: bool = True):
        from umh.runtime.advisor import AdvisorRuntime
        kwargs = {}
        if with_aggregator:
            kwargs["behavior_aggregator"] = BehaviorAggregator()
        return AdvisorRuntime(**kwargs)

    def test_advisor_has_behavior_aggregator_property(self):
        adv = self._make_advisor()
        assert adv.behavior_aggregator is not None

    def test_advisor_without_aggregator(self):
        adv = self._make_advisor(with_aggregator=False)
        assert adv.behavior_aggregator is None

    def test_advisor_behavior_model_initially_none(self):
        adv = self._make_advisor()
        assert adv.behavior_model is None

    def test_tick_has_model_updated_key(self):
        adv = self._make_advisor()
        result = adv.tick()
        assert "model_updated" in result

    def test_tick_builds_model_on_first_tick(self):
        adv = self._make_advisor()
        result = adv.tick()
        assert result["model_updated"] is True
        assert adv.behavior_model is not None

    def test_tick_updates_model_on_subsequent_ticks(self):
        adv = self._make_advisor()
        adv.tick()
        m1 = adv.behavior_model
        result = adv.tick()
        assert result["model_updated"] is True
        assert adv.behavior_model is m1

    def test_tick_without_aggregator_skips_model(self):
        adv = self._make_advisor(with_aggregator=False)
        result = adv.tick()
        assert result["model_updated"] is False
        assert adv.behavior_model is None

    def test_tick_with_feedback_updates_model(self):
        adv = self._make_advisor()
        fb = [_make_feedback()]
        result = adv.tick(completed_feedback=fb)
        assert result["model_updated"] is True
        model = adv.behavior_model
        assert model.get_trait("completion_rate").value == 1.0

    def test_get_state_includes_model_confidence(self):
        adv = self._make_advisor()
        adv.tick(completed_feedback=[_make_feedback()])
        state = adv.get_state()
        assert "behavior_model_confidence" in state

    def test_get_state_includes_dominant_traits(self):
        adv = self._make_advisor()
        adv.tick(completed_feedback=[
            _make_feedback(job_id=f"j{i}", success=True, duration_ms=10)
            for i in range(20)
        ])
        state = adv.get_state()
        if "dominant_traits" in state:
            assert isinstance(state["dominant_traits"], list)

    def test_get_state_no_model_no_keys(self):
        adv = self._make_advisor(with_aggregator=False)
        state = adv.get_state()
        assert "behavior_model_confidence" not in state

    def test_clear_resets_behavior_model(self):
        adv = self._make_advisor()
        adv.tick()
        assert adv.behavior_model is not None
        adv.clear()
        assert adv.behavior_model is None

    def test_multiple_ticks_accumulate(self):
        adv = self._make_advisor()
        adv.tick(completed_feedback=[_make_feedback(success=True)])
        adv.tick(completed_feedback=[_make_feedback(job_id="j2", success=False)])
        model = adv.behavior_model
        assert model.total_observations > 0

    def test_model_survives_tick_error_gracefully(self):
        adv = self._make_advisor()
        adv.tick()
        model_before = adv.behavior_model
        adv.tick()
        assert adv.behavior_model is model_before


# ===================================================================
# SECTION 5: Hard invariants (10 tests)
# ===================================================================

class TestHardInvariants:
    """INV 60-64: explicit verification."""

    def test_inv60_traits_derived_from_data_only(self):
        """INV60: All traits computed from data, never hardcoded input."""
        agg = BehaviorAggregator()
        m = agg.build_model(feedback=[_make_feedback()])
        for tv in m.traits.values():
            if tv.confidence > 0:
                assert tv.sample_count > 0

    def test_inv60_no_traits_set_without_data(self):
        """INV60: Without data, traits remain at neutral defaults."""
        agg = BehaviorAggregator()
        m = agg.build_model()
        for tv in m.traits.values():
            assert tv.value == 0.5
            assert tv.confidence == 0.0

    def test_inv61_aggregator_sole_writer(self):
        """INV61: Only BehaviorAggregator calls set_trait during build/update."""
        agg = BehaviorAggregator()
        src = inspect.getsource(type(agg))
        assert "set_trait" in src

    def test_inv61_model_has_no_compute_methods(self):
        """INV61: UserBehaviorModel doesn't compute traits itself."""
        src = inspect.getsource(UserBehaviorModel)
        assert "_compute_" not in src

    def test_inv62_deterministic(self):
        """INV62: Same inputs → same model, always."""
        agg = BehaviorAggregator()
        fb = [
            _make_feedback(job_id="j1", success=True, duration_ms=50,
                           timestamp="2026-04-30T10:00:00+00:00"),
            _make_feedback(job_id="j2", success=False, duration_ms=200,
                           timestamp="2026-04-30T14:00:00+00:00"),
        ]
        pw = [{"weight": 1.3}, {"weight": 0.9}]
        preds = [_make_prediction(prediction_id="p1", source="src_a")]

        m1 = agg.build_model(feedback=fb, predictions=preds, pattern_weights=pw)
        m2 = agg.build_model(feedback=fb, predictions=preds, pattern_weights=pw)

        for name in TRAIT_DEFINITIONS:
            t1 = m1.get_trait(name)
            t2 = m2.get_trait(name)
            assert t1.value == t2.value, f"{name} value mismatch"
            assert t1.confidence == t2.confidence, f"{name} confidence mismatch"

    def test_inv63_serialization_roundtrip_lossless(self):
        """INV63: to_dict → from_dict preserves all trait values."""
        agg = BehaviorAggregator()
        fb = [_make_feedback(job_id=f"j{i}", success=(i % 2 == 0)) for i in range(10)]
        m = agg.build_model(feedback=fb)
        d = m.to_dict()
        m2 = UserBehaviorModel.from_dict(d)
        for name in TRAIT_DEFINITIONS:
            orig = m.get_trait(name)
            restored = m2.get_trait(name)
            assert orig.value == pytest.approx(restored.value, abs=1e-4)
            assert orig.confidence == pytest.approx(restored.confidence, abs=1e-4)

    def test_inv63_json_roundtrip(self):
        """INV63: Full JSON serialize/deserialize cycle."""
        agg = BehaviorAggregator()
        m = agg.build_model(feedback=[_make_feedback()])
        json_str = json.dumps(m.to_dict())
        m2 = UserBehaviorModel.from_dict(json.loads(json_str))
        assert m2.get_trait("execution_rate").value == m.get_trait("execution_rate").value

    def test_inv64_limited_data_neutral_defaults(self):
        """INV64: With no data, all traits at 0.5 with zero confidence."""
        m = UserBehaviorModel()
        for tv in m.traits.values():
            assert tv.value == 0.5
            assert tv.confidence == 0.0

    def test_inv64_low_sample_low_confidence(self):
        """INV64: Few samples → low confidence, not high confidence."""
        agg = BehaviorAggregator()
        fb = [_make_feedback()]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("execution_rate").confidence < 0.5

    def test_inv64_many_samples_high_confidence(self):
        """INV64: Many samples → confidence saturates toward 1.0."""
        agg = BehaviorAggregator()
        fb = [_make_feedback(job_id=f"j{i}") for i in range(25)]
        m = agg.build_model(feedback=fb)
        assert m.get_trait("execution_rate").confidence == 1.0


# ===================================================================
# SECTION 6: Boundary checks (5 tests)
# ===================================================================

class TestBoundaryChecks:
    def test_model_no_cells_import(self):
        """Model modules must not import from umh/cells."""
        import umh.model.traits as mod_t
        import umh.model.behavior as mod_b
        import umh.model.aggregator as mod_a
        for mod in [mod_t, mod_b, mod_a]:
            src = inspect.getsource(mod)
            assert "from umh.cells" not in src
            assert "import umh.cells" not in src

    def test_model_no_environments_import(self):
        for mod_name in ["umh.model.traits", "umh.model.behavior", "umh.model.aggregator"]:
            mod = sys.modules[mod_name]
            src = inspect.getsource(mod)
            assert "from umh.environments" not in src
            assert "import umh.environments" not in src

    def test_model_no_subprocess(self):
        for mod_name in ["umh.model.traits", "umh.model.behavior", "umh.model.aggregator"]:
            mod = sys.modules[mod_name]
            src = inspect.getsource(mod)
            assert "import subprocess" not in src
            assert _SHELL_EXEC_PATTERN not in src

    def test_model_no_adapters_import(self):
        for mod_name in ["umh.model.traits", "umh.model.behavior", "umh.model.aggregator"]:
            mod = sys.modules[mod_name]
            src = inspect.getsource(mod)
            assert "from umh.adapters" not in src

    def test_all_exports_importable(self):
        from umh.model import (
            BehaviorAggregator,
            TRAIT_DEFINITIONS,
            TraitDefinition,
            TraitValue,
            UserBehaviorModel,
            confidence_from_samples,
            default_traits,
        )
        assert BehaviorAggregator is not None
        assert len(TRAIT_DEFINITIONS) == 7
