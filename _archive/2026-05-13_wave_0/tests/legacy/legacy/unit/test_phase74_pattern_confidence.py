"""Phase 74 — Pattern Confidence Evolution tests.

Tests invariants 383-393 and all confidence evolution behaviors.
"""

from __future__ import annotations

import math
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.pattern_confidence import (
    PatternConfidenceConfig,
    PatternConfidenceMemory,
    PatternConfidenceResult,
    PatternConfidenceState,
    update_all_pattern_confidences,
    update_pattern_confidence,
)


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


def _reliable_scores(n: int = 20) -> list[float]:
    return [0.8] * n


def _noisy_scores(n: int = 20) -> list[float]:
    return [0.0, 1.0] * (n // 2)


def _moderate_scores(n: int = 20) -> list[float]:
    return [0.4 + 0.02 * (i % 10) for i in range(n)]


def _mixed_scores(n: int = 20) -> list[float]:
    return [0.3, 0.5, 0.7, 0.3, 0.5, 0.7, 0.3, 0.5, 0.7, 0.3] * (n // 10 + 1)


def _cfg(**kw: object) -> PatternConfidenceConfig:
    defaults: dict[str, object] = {"enabled": True}
    defaults.update(kw)
    return PatternConfidenceConfig(**defaults)  # type: ignore[arg-type]


# ===================================================================
# Section 1: PatternConfidenceConfig
# ===================================================================


class TestPatternConfidenceConfig:
    def test_defaults(self) -> None:
        c = PatternConfidenceConfig()
        assert c.enabled is False
        assert c.neutral_confidence == 0.5
        assert c.min_samples == 10
        assert c.reinforcement_rate == 0.05
        assert c.decay_rate == 0.98
        assert c.min_confidence == 0.0
        assert c.max_confidence == 1.0
        assert c.noise_threshold == 0.30
        assert c.reliability_threshold == 0.70

    def test_min_samples_clamped(self) -> None:
        c = PatternConfidenceConfig(min_samples=0)
        assert c.min_samples == 1

    def test_neutral_confidence_clamped_low(self) -> None:
        c = PatternConfidenceConfig(neutral_confidence=-0.5)
        assert c.neutral_confidence == 0.0

    def test_neutral_confidence_clamped_high(self) -> None:
        c = PatternConfidenceConfig(neutral_confidence=2.0)
        assert c.neutral_confidence == 1.0

    def test_reinforcement_rate_clamped(self) -> None:
        c = PatternConfidenceConfig(reinforcement_rate=5.0)
        assert c.reinforcement_rate == 1.0

    def test_decay_rate_clamped(self) -> None:
        c = PatternConfidenceConfig(decay_rate=-1.0)
        assert c.decay_rate == 0.0

    def test_max_confidence_at_least_min(self) -> None:
        c = PatternConfidenceConfig(min_confidence=0.8, max_confidence=0.3)
        assert c.max_confidence >= c.min_confidence

    def test_noise_threshold_clamped(self) -> None:
        c = PatternConfidenceConfig(noise_threshold=2.0)
        assert c.noise_threshold == 1.0

    def test_to_dict(self) -> None:
        c = PatternConfidenceConfig()
        d = c.to_dict()
        assert "enabled" in d
        assert "neutral_confidence" in d
        assert "min_samples" in d
        assert "reinforcement_rate" in d
        assert "decay_rate" in d

    def test_frozen(self) -> None:
        c = PatternConfidenceConfig()
        with pytest.raises(AttributeError):
            c.enabled = True  # type: ignore[misc]


# ===================================================================
# Section 2: PatternConfidenceState
# ===================================================================


class TestPatternConfidenceState:
    def test_defaults(self) -> None:
        s = PatternConfidenceState()
        assert s.pattern_key == ""
        assert s.confidence == 0.5
        assert s.sample_count == 0
        assert s.last_seen_index == 0
        assert s.reliability == 0.0
        assert s.noise == 0.0

    def test_confidence_clamped(self) -> None:
        s = PatternConfidenceState(confidence=2.0)
        assert s.confidence == 1.0

    def test_confidence_clamped_low(self) -> None:
        s = PatternConfidenceState(confidence=-1.0)
        assert s.confidence == 0.0

    def test_sample_count_clamped(self) -> None:
        s = PatternConfidenceState(sample_count=-5)
        assert s.sample_count == 0

    def test_to_dict(self) -> None:
        s = PatternConfidenceState(pattern_key="test", confidence=0.75)
        d = s.to_dict()
        assert d["pattern_key"] == "test"
        assert d["confidence"] == 0.75

    def test_frozen(self) -> None:
        s = PatternConfidenceState()
        with pytest.raises(AttributeError):
            s.confidence = 0.9  # type: ignore[misc]


# ===================================================================
# Section 3: PatternConfidenceResult
# ===================================================================


class TestPatternConfidenceResult:
    def test_defaults(self) -> None:
        r = PatternConfidenceResult()
        assert r.pattern_key == ""
        assert r.previous_confidence == 0.5
        assert r.new_confidence == 0.5
        assert r.delta == 0.0
        assert r.used_fallback is True

    def test_confidence_clamped(self) -> None:
        r = PatternConfidenceResult(new_confidence=5.0)
        assert r.new_confidence == 1.0

    def test_to_dict_has_all_fields(self) -> None:
        r = PatternConfidenceResult(pattern_key="p1", new_confidence=0.7)
        d = r.to_dict()
        assert "pattern_key" in d
        assert "previous_confidence" in d
        assert "new_confidence" in d
        assert "delta" in d
        assert "used_fallback" in d
        assert "explanation" in d
        assert "reliability" in d
        assert "noise" in d

    def test_frozen(self) -> None:
        r = PatternConfidenceResult()
        with pytest.raises(AttributeError):
            r.new_confidence = 0.9  # type: ignore[misc]


# ===================================================================
# Section 4: Disabled config
# ===================================================================


class TestDisabledConfig:
    def test_disabled_returns_unchanged(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.6, 100, 90)
        assert r.new_confidence == 0.6
        assert r.used_fallback is True
        assert "disabled" in r.explanation

    def test_disabled_preserves_previous(self) -> None:
        r = update_pattern_confidence("p1", _noisy_scores(), 0.9, 100, 50)
        assert r.new_confidence == 0.9

    def test_disabled_with_explicit_config(self) -> None:
        cfg = PatternConfidenceConfig(enabled=False)
        r = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 90, cfg)
        assert r.used_fallback is True
        assert r.new_confidence == 0.5


# ===================================================================
# Section 5: Missing pattern data (inv 391)
# ===================================================================


class TestMissingData:
    def test_empty_scores_returns_neutral(self) -> None:
        r = update_pattern_confidence("p1", [], 0.7, 100, 90, _cfg())
        assert r.new_confidence == 0.5
        assert r.used_fallback is True
        assert "no pattern scores" in r.explanation

    def test_empty_scores_uses_config_neutral(self) -> None:
        r = update_pattern_confidence("p1", [], 0.7, 100, 90, _cfg(neutral_confidence=0.3))
        assert r.new_confidence == 0.3


# ===================================================================
# Section 6: Low-sample fallback (inv 384)
# ===================================================================


class TestLowSampleFallback:
    def test_below_min_samples_capped_at_neutral(self) -> None:
        r = update_pattern_confidence("p1", [0.8, 0.8, 0.8], 0.9, 100, 99, _cfg(min_samples=10))
        assert r.new_confidence <= 0.5
        assert r.used_fallback is True
        assert "insufficient samples" in r.explanation

    def test_below_min_samples_keeps_low_confidence(self) -> None:
        r = update_pattern_confidence("p1", [0.8, 0.8], 0.3, 100, 99, _cfg(min_samples=10))
        assert r.new_confidence == 0.3
        assert r.used_fallback is True

    def test_exactly_at_min_samples_no_fallback(self) -> None:
        r = update_pattern_confidence(
            "p1", _reliable_scores(10), 0.5, 100, 100, _cfg(min_samples=10)
        )
        assert r.used_fallback is False

    def test_one_below_min_samples_is_fallback(self) -> None:
        r = update_pattern_confidence(
            "p1", _reliable_scores(9), 0.5, 100, 100, _cfg(min_samples=10)
        )
        assert r.used_fallback is True


# ===================================================================
# Section 7: Reliable outcomes increase confidence (inv 385)
# ===================================================================


class TestReliableOutcomes:
    def test_reliable_scores_increase_from_neutral(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 100, _cfg())
        assert r.new_confidence > 0.5
        assert r.delta > 0

    def test_reliable_scores_increase_from_low(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.3, 100, 100, _cfg())
        assert r.new_confidence > 0.3

    def test_repeated_reliable_converges_upward(self) -> None:
        conf = 0.5
        cfg = _cfg()
        for _ in range(50):
            r = update_pattern_confidence("p1", _reliable_scores(), conf, 100, 100, cfg)
            conf = r.new_confidence
        assert conf > 0.8

    def test_reliability_field_populated(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 100, _cfg())
        assert r.reliability > 0.8


# ===================================================================
# Section 8: Noisy outcomes decrease confidence (inv 386)
# ===================================================================


class TestNoisyOutcomes:
    def test_noisy_scores_decrease_from_high(self) -> None:
        r = update_pattern_confidence("p1", _noisy_scores(), 0.8, 100, 100, _cfg())
        assert r.new_confidence < 0.8
        assert r.delta < 0

    def test_noisy_scores_decrease_from_neutral(self) -> None:
        r = update_pattern_confidence("p1", _noisy_scores(), 0.5, 100, 100, _cfg())
        assert r.new_confidence < 0.5

    def test_repeated_noisy_converges_downward(self) -> None:
        conf = 0.8
        cfg = _cfg()
        for _ in range(50):
            r = update_pattern_confidence("p1", _noisy_scores(), conf, 100, 100, cfg)
            conf = r.new_confidence
        assert conf < 0.2

    def test_noise_field_populated(self) -> None:
        r = update_pattern_confidence("p1", _noisy_scores(), 0.5, 100, 100, _cfg())
        assert r.noise > 0.5


# ===================================================================
# Section 9: Confidence bounded [0,1] (inv 383)
# ===================================================================


class TestConfidenceBounded:
    def test_never_exceeds_max(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.99, 100, 100, _cfg())
        assert r.new_confidence <= 1.0

    def test_never_below_min(self) -> None:
        r = update_pattern_confidence("p1", _noisy_scores(), 0.01, 100, 100, _cfg())
        assert r.new_confidence >= 0.0

    def test_max_confidence_from_config(self) -> None:
        cfg = _cfg(max_confidence=0.9)
        conf = 0.5
        for _ in range(100):
            r = update_pattern_confidence("p1", _reliable_scores(), conf, 100, 100, cfg)
            conf = r.new_confidence
        assert conf <= 0.9

    def test_min_confidence_from_config(self) -> None:
        cfg = _cfg(min_confidence=0.2)
        conf = 0.5
        for _ in range(100):
            r = update_pattern_confidence("p1", _noisy_scores(), conf, 100, 100, cfg)
            conf = r.new_confidence
        assert conf >= 0.2

    def test_clamped_after_extreme_reinforcement(self) -> None:
        cfg = _cfg(reinforcement_rate=1.0)
        r = update_pattern_confidence("p1", _reliable_scores(), 0.95, 100, 100, cfg)
        assert 0.0 <= r.new_confidence <= 1.0

    def test_clamped_after_extreme_negative(self) -> None:
        cfg = _cfg(reinforcement_rate=1.0)
        r = update_pattern_confidence("p1", _noisy_scores(), 0.05, 100, 100, cfg)
        assert 0.0 <= r.new_confidence <= 1.0


# ===================================================================
# Section 10: Decay toward neutral (inv 387)
# ===================================================================


class TestDecayTowardNeutral:
    def test_unused_pattern_decays_from_high(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.9, 200, 100, _cfg())
        assert r.new_confidence < 0.9

    def test_unused_pattern_decays_from_low(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.1, 200, 100, _cfg())
        assert r.new_confidence > 0.1

    def test_decay_does_not_overshoot_neutral(self) -> None:
        cfg = _cfg(neutral_confidence=0.5, decay_rate=0.5)
        r = update_pattern_confidence("p1", _reliable_scores(), 0.9, 200, 100, cfg)
        assert r.new_confidence >= 0.5

    def test_age_zero_no_decay(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.7, 100, 100, _cfg())
        r_no_age = update_pattern_confidence("p1", _reliable_scores(), 0.7, 100, 100, _cfg())
        assert r.new_confidence == r_no_age.new_confidence

    def test_large_age_approaches_neutral(self) -> None:
        cfg = _cfg(neutral_confidence=0.5, decay_rate=0.98)
        r = update_pattern_confidence("p1", _reliable_scores(), 0.9, 1000, 0, cfg)
        assert abs(r.new_confidence - 0.5) < 0.1

    def test_decay_rate_one_no_decay(self) -> None:
        cfg = _cfg(decay_rate=1.0)
        r = update_pattern_confidence("p1", _reliable_scores(), 0.9, 200, 100, cfg)
        r_no_age = update_pattern_confidence("p1", _reliable_scores(), 0.9, 100, 100, cfg)
        assert abs(r.new_confidence - r_no_age.new_confidence) < 1e-9

    def test_decay_rate_zero_snaps_to_neutral(self) -> None:
        cfg = _cfg(decay_rate=0.0, neutral_confidence=0.5)
        r = update_pattern_confidence("p1", _reliable_scores(), 0.9, 200, 100, cfg)
        assert abs(r.new_confidence - 0.5) < 0.1


# ===================================================================
# Section 11: Determinism (inv 388)
# ===================================================================


class TestDeterminism:
    def test_repeated_calls_identical(self) -> None:
        cfg = _cfg()
        scores = _reliable_scores()
        r1 = update_pattern_confidence("p1", scores, 0.5, 100, 90, cfg)
        r2 = update_pattern_confidence("p1", scores, 0.5, 100, 90, cfg)
        assert r1.new_confidence == r2.new_confidence
        assert r1.delta == r2.delta

    def test_batch_repeated_identical(self) -> None:
        cfg = _cfg()
        keys = ["a", "b", "c"]
        scores_map = {"a": _reliable_scores(), "b": _noisy_scores(), "c": _moderate_scores()}
        prev = {"a": 0.5, "b": 0.5, "c": 0.5}
        last_seen = {"a": 90, "b": 80, "c": 85}

        r1 = update_all_pattern_confidences(keys, scores_map, prev, 100, last_seen, cfg)
        r2 = update_all_pattern_confidences(keys, scores_map, prev, 100, last_seen, cfg)

        for a, b in zip(r1, r2):
            assert a.new_confidence == b.new_confidence


# ===================================================================
# Section 12: No mutation of PatternRecords (inv 389)
# ===================================================================


class TestNoMutation:
    def test_scores_not_mutated(self) -> None:
        scores = [0.8, 0.7, 0.9, 0.8, 0.7, 0.9, 0.8, 0.7, 0.9, 0.8, 0.7, 0.9]
        original = list(scores)
        update_pattern_confidence("p1", scores, 0.5, 100, 90, _cfg())
        assert scores == original

    def test_scores_map_not_mutated(self) -> None:
        scores_map = {"a": [0.8, 0.7, 0.9] * 5, "b": [0.1, 0.9] * 8}
        original_a = list(scores_map["a"])
        original_b = list(scores_map["b"])
        update_all_pattern_confidences(
            ["a", "b"], scores_map, {"a": 0.5, "b": 0.5}, 100, {"a": 90, "b": 90}, _cfg()
        )
        assert scores_map["a"] == original_a
        assert scores_map["b"] == original_b


# ===================================================================
# Section 13: No scoring feedback loop (inv 390)
# ===================================================================


class TestNoFeedbackLoop:
    def test_no_scoring_imports(self) -> None:
        import umh.runtime.pattern_confidence as mod

        source = open(mod.__file__).read()
        assert "from umh.runtime.pattern_aggregation" not in source
        assert "from umh.runtime.pattern_influence" not in source
        assert "from umh.runtime.pattern_matching" not in source
        assert "from umh.runtime.strategy_orchestrator" not in source

    def test_no_subprocess_imports(self) -> None:
        import umh.runtime.pattern_confidence as mod

        source = open(mod.__file__).read()
        assert "import subprocess" not in source
        assert "import os" not in source
        assert "import docker" not in source


# ===================================================================
# Section 14: Explainability (inv 392)
# ===================================================================


class TestExplainability:
    def test_disabled_explanation(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 90)
        assert "disabled" in r.explanation

    def test_insufficient_samples_explanation(self) -> None:
        r = update_pattern_confidence("p1", [0.8, 0.8], 0.5, 100, 90, _cfg())
        assert "insufficient" in r.explanation

    def test_empty_scores_explanation(self) -> None:
        r = update_pattern_confidence("p1", [], 0.5, 100, 90, _cfg())
        assert "no pattern scores" in r.explanation

    def test_reliable_explanation(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 100, _cfg())
        assert "reliable" in r.explanation or "reliability" in r.explanation

    def test_noisy_explanation(self) -> None:
        r = update_pattern_confidence("p1", _noisy_scores(), 0.5, 100, 100, _cfg())
        assert "noisy" in r.explanation or "noise" in r.explanation

    def test_decay_in_explanation(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.7, 200, 100, _cfg())
        assert "decay" in r.explanation

    def test_explanation_has_reliability(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 100, _cfg())
        assert "reliability=" in r.explanation

    def test_explanation_has_noise(self) -> None:
        r = update_pattern_confidence("p1", _noisy_scores(), 0.5, 100, 100, _cfg())
        assert "noise=" in r.explanation

    def test_explanation_has_samples(self) -> None:
        r = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 100, _cfg())
        assert "samples=" in r.explanation


# ===================================================================
# Section 15: Default unchanged (inv 393)
# ===================================================================


class TestDefaultUnchanged:
    def test_default_config_disabled(self) -> None:
        c = PatternConfidenceConfig()
        assert c.enabled is False

    def test_disabled_no_change(self) -> None:
        for prev in [0.0, 0.3, 0.5, 0.7, 1.0]:
            r = update_pattern_confidence("p1", _reliable_scores(), prev, 100, 90)
            assert r.new_confidence == prev


# ===================================================================
# Section 16: Batch computation
# ===================================================================


class TestBatchComputation:
    def test_batch_returns_one_per_key(self) -> None:
        keys = ["a", "b", "c"]
        scores_map = {"a": _reliable_scores(), "b": _noisy_scores(), "c": _moderate_scores()}
        prev = {"a": 0.5, "b": 0.5, "c": 0.5}
        last_seen = {"a": 90, "b": 80, "c": 85}

        results = update_all_pattern_confidences(keys, scores_map, prev, 100, last_seen, _cfg())
        assert len(results) == 3
        assert results[0].pattern_key == "a"
        assert results[1].pattern_key == "b"
        assert results[2].pattern_key == "c"

    def test_batch_missing_key_uses_neutral(self) -> None:
        keys = ["a", "missing"]
        scores_map = {"a": _reliable_scores()}
        prev = {"a": 0.5}
        last_seen = {"a": 90}

        results = update_all_pattern_confidences(keys, scores_map, prev, 100, last_seen, _cfg())
        assert len(results) == 2
        assert results[1].new_confidence == 0.5
        assert results[1].used_fallback is True

    def test_batch_disabled(self) -> None:
        results = update_all_pattern_confidences(
            ["a"], {"a": _reliable_scores()}, {"a": 0.5}, 100, {"a": 90}
        )
        assert results[0].used_fallback is True

    def test_batch_reliable_increases(self) -> None:
        results = update_all_pattern_confidences(
            ["a"], {"a": _reliable_scores()}, {"a": 0.5}, 100, {"a": 100}, _cfg()
        )
        assert results[0].new_confidence > 0.5

    def test_batch_noisy_decreases(self) -> None:
        results = update_all_pattern_confidences(
            ["a"], {"a": _noisy_scores()}, {"a": 0.5}, 100, {"a": 100}, _cfg()
        )
        assert results[0].new_confidence < 0.5


# ===================================================================
# Section 17: PatternConfidenceMemory
# ===================================================================


class TestPatternConfidenceMemory:
    def test_initial_empty(self) -> None:
        mem = PatternConfidenceMemory()
        assert mem.size == 0

    def test_get_unknown_returns_neutral(self) -> None:
        mem = PatternConfidenceMemory()
        s = mem.get("unknown")
        assert s.confidence == 0.5
        assert s.pattern_key == "unknown"

    def test_get_unknown_respects_custom_neutral(self) -> None:
        mem = PatternConfidenceMemory(neutral_confidence=0.3)
        s = mem.get("unknown")
        assert s.confidence == 0.3

    def test_update_stores_state(self) -> None:
        mem = PatternConfidenceMemory()
        mem.update("p1", _reliable_scores(), 100, _cfg())
        assert mem.size == 1
        s = mem.get("p1")
        assert s.pattern_key == "p1"

    def test_update_returns_result(self) -> None:
        mem = PatternConfidenceMemory()
        r = mem.update("p1", _reliable_scores(), 100, _cfg())
        assert isinstance(r, PatternConfidenceResult)
        assert r.pattern_key == "p1"

    def test_multiple_updates_accumulate(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        mem.update("p1", _reliable_scores(), 100, cfg)
        r1 = mem.get("p1")
        mem.update("p1", _reliable_scores(), 101, cfg)
        r2 = mem.get("p1")
        assert r2.confidence >= r1.confidence

    def test_snapshot_sorted(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        mem.update("c", _reliable_scores(), 100, cfg)
        mem.update("a", _reliable_scores(), 100, cfg)
        mem.update("b", _reliable_scores(), 100, cfg)
        snap = mem.snapshot()
        assert list(snap.keys()) == ["a", "b", "c"]

    def test_to_dict(self) -> None:
        mem = PatternConfidenceMemory()
        mem.update("p1", _reliable_scores(), 100, _cfg())
        d = mem.to_dict()
        assert "size" in d
        assert "states" in d
        assert d["size"] == 1


# ===================================================================
# Section 18: Memory decay_unused
# ===================================================================


class TestMemoryDecayUnused:
    def test_decay_unused_disabled(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = PatternConfidenceConfig(enabled=False)
        mem._states["p1"] = PatternConfidenceState(
            pattern_key="p1", confidence=0.8, last_seen_index=50
        )
        results = mem.decay_unused(100, cfg)
        assert len(results) == 0

    def test_decay_unused_applies(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        mem._states["p1"] = PatternConfidenceState(
            pattern_key="p1", confidence=0.8, last_seen_index=50
        )
        results = mem.decay_unused(100, cfg)
        assert len(results) == 1
        assert results[0].new_confidence < 0.8

    def test_decay_unused_skips_current(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        mem._states["p1"] = PatternConfidenceState(
            pattern_key="p1", confidence=0.8, last_seen_index=100
        )
        results = mem.decay_unused(100, cfg)
        assert len(results) == 0

    def test_decay_unused_updates_state(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        mem._states["p1"] = PatternConfidenceState(
            pattern_key="p1", confidence=0.8, last_seen_index=50
        )
        mem.decay_unused(100, cfg)
        s = mem.get("p1")
        assert s.confidence < 0.8

    def test_decay_unused_sorted_order(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        mem._states["b"] = PatternConfidenceState(
            pattern_key="b", confidence=0.8, last_seen_index=50
        )
        mem._states["a"] = PatternConfidenceState(
            pattern_key="a", confidence=0.7, last_seen_index=40
        )
        results = mem.decay_unused(100, cfg)
        assert results[0].pattern_key == "a"
        assert results[1].pattern_key == "b"


# ===================================================================
# Section 19: Reinforcement rate effect
# ===================================================================


class TestReinforcementRate:
    def test_higher_rate_faster_convergence(self) -> None:
        cfg_slow = _cfg(reinforcement_rate=0.01)
        cfg_fast = _cfg(reinforcement_rate=0.10)

        r_slow = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 100, cfg_slow)
        r_fast = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 100, cfg_fast)

        assert r_fast.delta > r_slow.delta

    def test_zero_rate_no_change(self) -> None:
        cfg = _cfg(reinforcement_rate=0.0)
        r = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 100, cfg)
        assert r.new_confidence == 0.5

    def test_max_rate_jumps_to_target(self) -> None:
        cfg = _cfg(reinforcement_rate=1.0)
        r = update_pattern_confidence("p1", _reliable_scores(), 0.5, 100, 100, cfg)
        assert abs(r.new_confidence - r.reliability) < 0.01


# ===================================================================
# Section 20: Convergence behavior
# ===================================================================


class TestConvergence:
    def test_reliable_converges_to_high(self) -> None:
        conf = 0.5
        cfg = _cfg(reinforcement_rate=0.1)
        for _ in range(200):
            r = update_pattern_confidence("p1", _reliable_scores(), conf, 100, 100, cfg)
            conf = r.new_confidence
        assert conf > 0.95

    def test_noisy_converges_to_low(self) -> None:
        conf = 0.5
        cfg = _cfg(reinforcement_rate=0.1)
        for _ in range(200):
            r = update_pattern_confidence("p1", _noisy_scores(), conf, 100, 100, cfg)
            conf = r.new_confidence
        assert conf < 0.05

    def test_moderate_converges_to_moderate(self) -> None:
        conf = 0.5
        cfg = _cfg(reinforcement_rate=0.1)
        for _ in range(200):
            r = update_pattern_confidence("p1", _moderate_scores(), conf, 100, 100, cfg)
            conf = r.new_confidence
        assert 0.3 < conf < 1.0


# ===================================================================
# Section 21: Invariant 383 — bounded [0,1]
# ===================================================================


class TestInv383Bounded:
    def test_extreme_reliable(self) -> None:
        r = update_pattern_confidence("p", [1.0] * 20, 1.0, 100, 100, _cfg(reinforcement_rate=1.0))
        assert 0.0 <= r.new_confidence <= 1.0

    def test_extreme_noisy(self) -> None:
        r = update_pattern_confidence(
            "p", _noisy_scores(), 0.0, 100, 100, _cfg(reinforcement_rate=1.0)
        )
        assert 0.0 <= r.new_confidence <= 1.0

    def test_large_decay(self) -> None:
        r = update_pattern_confidence("p", _reliable_scores(), 0.99, 10000, 0, _cfg(decay_rate=0.5))
        assert 0.0 <= r.new_confidence <= 1.0


# ===================================================================
# Section 22: Invariant 384 — low-sample remains low
# ===================================================================


class TestInv384LowSample:
    def test_two_samples_capped(self) -> None:
        r = update_pattern_confidence("p", [1.0, 1.0], 0.9, 100, 100, _cfg())
        assert r.new_confidence <= 0.5

    def test_min_samples_1_allows_single_sample(self) -> None:
        r = update_pattern_confidence("p", [0.8] * 1, 0.5, 100, 100, _cfg(min_samples=1))
        assert r.used_fallback is False


# ===================================================================
# Section 23: Invariant 385-386 — reliable up, noisy down
# ===================================================================


class TestInv385_386Direction:
    def test_reliable_delta_positive(self) -> None:
        r = update_pattern_confidence("p", _reliable_scores(), 0.5, 100, 100, _cfg())
        assert r.delta > 0

    def test_noisy_delta_negative(self) -> None:
        r = update_pattern_confidence("p", _noisy_scores(), 0.5, 100, 100, _cfg())
        assert r.delta < 0

    def test_reliable_noise_low(self) -> None:
        r = update_pattern_confidence("p", _reliable_scores(), 0.5, 100, 100, _cfg())
        assert r.noise < 0.1

    def test_noisy_noise_high(self) -> None:
        r = update_pattern_confidence("p", _noisy_scores(), 0.5, 100, 100, _cfg())
        assert r.noise > 0.9


# ===================================================================
# Section 24: Invariant 387 — decay toward neutral
# ===================================================================


class TestInv387Decay:
    def test_above_neutral_decays_down(self) -> None:
        r = update_pattern_confidence("p", _reliable_scores(), 0.9, 200, 100, _cfg())
        assert r.new_confidence < 0.9

    def test_below_neutral_decays_up(self) -> None:
        cfg = _cfg(reinforcement_rate=0.0)
        r = update_pattern_confidence("p", _reliable_scores(), 0.1, 200, 100, cfg)
        assert r.new_confidence > 0.1

    def test_at_neutral_no_decay_effect(self) -> None:
        cfg = _cfg(reinforcement_rate=0.0, neutral_confidence=0.5)
        r = update_pattern_confidence("p", _reliable_scores(), 0.5, 200, 100, cfg)
        assert abs(r.new_confidence - 0.5) < 1e-9


# ===================================================================
# Section 25: Invariant 388 — determinism
# ===================================================================


class TestInv388Determinism:
    def test_memory_snapshot_deterministic(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        mem.update("b", _reliable_scores(), 100, cfg)
        mem.update("a", _noisy_scores(), 100, cfg)
        s1 = mem.snapshot()
        s2 = mem.snapshot()
        assert list(s1.keys()) == list(s2.keys())
        for k in s1:
            assert s1[k].confidence == s2[k].confidence


# ===================================================================
# Section 26: Invariant 389 — no record mutation
# ===================================================================


class TestInv389NoRecordMutation:
    def test_state_frozen(self) -> None:
        s = PatternConfidenceState(pattern_key="p", confidence=0.5)
        with pytest.raises(AttributeError):
            s.confidence = 0.9  # type: ignore[misc]

    def test_result_frozen(self) -> None:
        r = PatternConfidenceResult(pattern_key="p", new_confidence=0.7)
        with pytest.raises(AttributeError):
            r.new_confidence = 0.1  # type: ignore[misc]

    def test_config_frozen(self) -> None:
        c = PatternConfidenceConfig()
        with pytest.raises(AttributeError):
            c.enabled = True  # type: ignore[misc]


# ===================================================================
# Section 27: Invariant 390 — no scoring feedback loop
# ===================================================================


class TestInv390NoScoringLoop:
    def test_uses_variance_not_mean(self) -> None:
        same_mean_low_var = [0.5] * 20
        same_mean_high_var = [0.0, 1.0] * 10
        r_low = update_pattern_confidence("p", same_mean_low_var, 0.5, 100, 100, _cfg())
        r_high = update_pattern_confidence("p", same_mean_high_var, 0.5, 100, 100, _cfg())
        assert r_low.reliability > r_high.reliability
        assert r_low.new_confidence > r_high.new_confidence


# ===================================================================
# Section 28: Invariant 391 — missing data neutral
# ===================================================================


class TestInv391MissingData:
    def test_no_scores_neutral(self) -> None:
        r = update_pattern_confidence("p", [], 0.5, 100, 90, _cfg())
        assert r.new_confidence == 0.5

    def test_no_scores_custom_neutral(self) -> None:
        r = update_pattern_confidence("p", [], 0.5, 100, 90, _cfg(neutral_confidence=0.4))
        assert r.new_confidence == 0.4

    def test_batch_missing_key_neutral(self) -> None:
        results = update_all_pattern_confidences(["missing"], {}, {}, 100, {}, _cfg())
        assert results[0].new_confidence == 0.5


# ===================================================================
# Section 29: Invariant 392 — explainability
# ===================================================================


class TestInv392Explainability:
    def test_result_has_all_fields(self) -> None:
        r = update_pattern_confidence("p", _reliable_scores(), 0.5, 100, 100, _cfg())
        d = r.to_dict()
        for field in [
            "pattern_key",
            "previous_confidence",
            "new_confidence",
            "sample_count",
            "reliability",
            "noise",
            "delta",
            "used_fallback",
            "explanation",
        ]:
            assert field in d

    def test_state_has_all_fields(self) -> None:
        s = PatternConfidenceState(pattern_key="p", confidence=0.6)
        d = s.to_dict()
        for field in [
            "pattern_key",
            "confidence",
            "sample_count",
            "last_seen_index",
            "reliability",
            "noise",
            "explanation",
        ]:
            assert field in d


# ===================================================================
# Section 30: Invariant 393 — default unchanged
# ===================================================================


class TestInv393DefaultUnchanged:
    def test_default_config_no_evolution(self) -> None:
        r = update_pattern_confidence("p", _reliable_scores(), 0.3, 100, 50)
        assert r.new_confidence == 0.3

    def test_default_batch_no_evolution(self) -> None:
        results = update_all_pattern_confidences(
            ["a", "b"],
            {"a": _reliable_scores(), "b": _noisy_scores()},
            {"a": 0.7, "b": 0.3},
            100,
            {"a": 90, "b": 90},
        )
        assert results[0].new_confidence == 0.7
        assert results[1].new_confidence == 0.3


# ===================================================================
# Section 31: Edge cases
# ===================================================================


class TestEdgeCases:
    def test_single_score_below_min_samples(self) -> None:
        r = update_pattern_confidence("p", [0.5], 0.5, 100, 100, _cfg(min_samples=10))
        assert r.used_fallback is True

    def test_all_identical_scores(self) -> None:
        r = update_pattern_confidence("p", [0.5] * 20, 0.5, 100, 100, _cfg())
        assert r.noise == 0.0
        assert r.reliability == 1.0

    def test_all_zero_scores(self) -> None:
        r = update_pattern_confidence("p", [0.0] * 20, 0.5, 100, 100, _cfg())
        assert r.noise == 0.0
        assert r.reliability == 1.0
        assert r.new_confidence > 0.5

    def test_all_one_scores(self) -> None:
        r = update_pattern_confidence("p", [1.0] * 20, 0.5, 100, 100, _cfg())
        assert r.noise == 0.0
        assert r.new_confidence > 0.5

    def test_alternating_01(self) -> None:
        r = update_pattern_confidence("p", [0.0, 1.0] * 10, 0.5, 100, 100, _cfg())
        assert r.noise == 1.0
        assert r.reliability == 0.0

    def test_very_large_sample(self) -> None:
        r = update_pattern_confidence("p", [0.8] * 10000, 0.5, 100, 100, _cfg())
        assert r.used_fallback is False

    def test_negative_age_treated_as_zero(self) -> None:
        r = update_pattern_confidence("p", _reliable_scores(), 0.5, 50, 100, _cfg())
        r_zero = update_pattern_confidence("p", _reliable_scores(), 0.5, 100, 100, _cfg())
        assert r.new_confidence == r_zero.new_confidence

    def test_previous_confidence_at_boundary_zero(self) -> None:
        r = update_pattern_confidence("p", _reliable_scores(), 0.0, 100, 100, _cfg())
        assert r.new_confidence >= 0.0

    def test_previous_confidence_at_boundary_one(self) -> None:
        r = update_pattern_confidence("p", _noisy_scores(), 1.0, 100, 100, _cfg())
        assert r.new_confidence <= 1.0


# ===================================================================
# Section 32: Update formula verification
# ===================================================================


class TestUpdateFormula:
    def test_reinforcement_formula(self) -> None:
        cfg = _cfg(reinforcement_rate=0.05)
        scores = [0.5] * 20
        from umh.runtime.pattern_half_life import compute_pattern_reliability

        reliability = compute_pattern_reliability(scores)
        prev = 0.5
        expected_delta = 0.05 * (reliability - prev)
        expected = prev + expected_delta

        r = update_pattern_confidence("p", scores, prev, 100, 100, cfg)
        assert abs(r.new_confidence - expected) < 1e-9

    def test_decay_formula(self) -> None:
        cfg = _cfg(reinforcement_rate=0.0, decay_rate=0.98, neutral_confidence=0.5)
        prev = 0.8
        age = 10
        expected_after_reinforcement = prev
        decay_factor = 0.98**10
        expected = 0.5 + (expected_after_reinforcement - 0.5) * decay_factor

        r = update_pattern_confidence("p", _reliable_scores(), prev, 110, 100, cfg)
        assert abs(r.new_confidence - expected) < 1e-9

    def test_combined_formula(self) -> None:
        cfg = _cfg(reinforcement_rate=0.05, decay_rate=0.98, neutral_confidence=0.5)
        scores = _reliable_scores()
        from umh.runtime.pattern_half_life import compute_pattern_reliability

        reliability = compute_pattern_reliability(scores)
        prev = 0.6
        delta = 0.05 * (reliability - prev)
        after_reinforce = prev + delta
        age = 5
        decay_factor = 0.98**5
        expected = 0.5 + (after_reinforce - 0.5) * decay_factor

        r = update_pattern_confidence("p", scores, prev, 105, 100, cfg)
        assert abs(r.new_confidence - expected) < 1e-9


# ===================================================================
# Section 33: Parameter sweep
# ===================================================================


class TestParameterSweep:
    def test_reinforcement_rate_sweep(self) -> None:
        for rate in [0.01, 0.05, 0.10, 0.20, 0.50, 1.0]:
            cfg = _cfg(reinforcement_rate=rate)
            r = update_pattern_confidence("p", _reliable_scores(), 0.5, 100, 100, cfg)
            assert 0.0 <= r.new_confidence <= 1.0
            assert r.delta >= 0

    def test_decay_rate_sweep(self) -> None:
        for decay in [0.0, 0.5, 0.9, 0.95, 0.98, 0.99, 1.0]:
            cfg = _cfg(decay_rate=decay)
            r = update_pattern_confidence("p", _reliable_scores(), 0.8, 200, 100, cfg)
            assert 0.0 <= r.new_confidence <= 1.0

    def test_neutral_confidence_sweep(self) -> None:
        for neutral in [0.0, 0.2, 0.5, 0.8, 1.0]:
            cfg = _cfg(neutral_confidence=neutral)
            r = update_pattern_confidence("p", [], 0.5, 100, 90, cfg)
            assert r.new_confidence == neutral

    def test_noise_threshold_sweep(self) -> None:
        for thresh in [0.1, 0.3, 0.5, 0.7, 0.9]:
            cfg = _cfg(noise_threshold=thresh)
            r = update_pattern_confidence("p", _noisy_scores(), 0.5, 100, 100, cfg)
            assert 0.0 <= r.new_confidence <= 1.0


# ===================================================================
# Section 34: Imports
# ===================================================================


class TestImports:
    def test_import_from_runtime_init(self) -> None:
        from umh.runtime import (
            PatternConfidenceConfig,
            PatternConfidenceMemory,
            PatternConfidenceResult,
            PatternConfidenceState,
            update_all_pattern_confidences,
            update_pattern_confidence,
        )

        assert PatternConfidenceConfig is not None
        assert PatternConfidenceMemory is not None
        assert PatternConfidenceResult is not None
        assert PatternConfidenceState is not None
        assert update_all_pattern_confidences is not None
        assert update_pattern_confidence is not None

    def test_import_from_module_direct(self) -> None:
        from umh.runtime.pattern_confidence import (
            PatternConfidenceConfig,
            PatternConfidenceMemory,
            PatternConfidenceResult,
            PatternConfidenceState,
            update_all_pattern_confidences,
            update_pattern_confidence,
        )

        assert callable(update_pattern_confidence)
        assert callable(update_all_pattern_confidences)


# ===================================================================
# Section 35: Backward compatibility
# ===================================================================


class TestBackwardCompat:
    def test_phase73_imports_intact(self) -> None:
        from umh.runtime import (
            PatternHalfLifeConfig,
            PatternHalfLifeResult,
            compute_all_pattern_half_lives,
            compute_pattern_half_life,
            compute_pattern_noise,
            compute_pattern_reliability,
        )

        assert PatternHalfLifeConfig is not None

    def test_phase70_imports_intact(self) -> None:
        from umh.runtime import (
            TemporalContribution,
            TemporalPatternConfig,
            TemporalWeightingResult,
            apply_temporal_weights,
            compute_decay_factor,
        )

        assert TemporalPatternConfig is not None

    def test_phase71_imports_intact(self) -> None:
        from umh.runtime import (
            AdaptiveHalfLifeConfig,
            AdaptiveHalfLifeResult,
            compute_adaptive_half_life,
            compute_volatility,
        )

        assert AdaptiveHalfLifeConfig is not None

    def test_phase72_imports_intact(self) -> None:
        from umh.runtime import (
            RegimeCategory,
            RegimeHalfLifeConfig,
            RegimeHalfLifeResult,
            classify_regime_category,
            compute_regime_half_life,
        )

        assert RegimeHalfLifeConfig is not None

    def test_phase67_imports_intact(self) -> None:
        from umh.runtime import (
            PatternKey,
            PatternMemory,
            PatternRecord,
            PatternStats,
        )

        assert PatternKey is not None

    def test_phase68_imports_intact(self) -> None:
        from umh.runtime import (
            PatternInfluenceConfig,
            PatternInfluenceResult,
            compute_pattern_influence,
        )

        assert PatternInfluenceConfig is not None

    def test_phase69_imports_intact(self) -> None:
        from umh.runtime import (
            PatternAggregationResult,
            PatternContribution,
            compute_pattern_aggregation,
        )

        assert PatternAggregationResult is not None


# ===================================================================
# Section 36: Regression — Phase 73 reuse
# ===================================================================


class TestPhase73Reuse:
    def test_noise_formula_consistent(self) -> None:
        from umh.runtime.pattern_half_life import compute_pattern_noise

        scores = _noisy_scores()
        noise = compute_pattern_noise(scores)
        r = update_pattern_confidence("p", scores, 0.5, 100, 100, _cfg())
        assert abs(r.noise - noise) < 1e-9

    def test_reliability_formula_consistent(self) -> None:
        from umh.runtime.pattern_half_life import compute_pattern_reliability

        scores = _reliable_scores()
        rel = compute_pattern_reliability(scores)
        r = update_pattern_confidence("p", scores, 0.5, 100, 100, _cfg())
        assert abs(r.reliability - rel) < 1e-9


# ===================================================================
# Section 37: Memory multi-step evolution
# ===================================================================


class TestMemoryMultiStep:
    def test_confidence_grows_over_updates(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        for i in range(20):
            mem.update("p1", _reliable_scores(), 100 + i, cfg)
        s = mem.get("p1")
        assert s.confidence > 0.6

    def test_confidence_shrinks_over_noisy_updates(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        for i in range(20):
            mem.update("p1", _noisy_scores(), 100 + i, cfg)
        s = mem.get("p1")
        assert s.confidence < 0.4

    def test_mixed_patterns_diverge(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        for i in range(30):
            mem.update("reliable", _reliable_scores(), 100 + i, cfg)
            mem.update("noisy", _noisy_scores(), 100 + i, cfg)
        s_reliable = mem.get("reliable")
        s_noisy = mem.get("noisy")
        assert s_reliable.confidence > s_noisy.confidence

    def test_decay_unused_brings_toward_neutral(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        for i in range(10):
            mem.update("p1", _reliable_scores(), 100 + i, cfg)
        before = mem.get("p1").confidence
        mem.decay_unused(200, cfg)
        after = mem.get("p1").confidence
        assert after < before
        assert after >= 0.5


# ===================================================================
# Section 38: Category classification
# ===================================================================


class TestCategoryClassification:
    def test_reliable_category(self) -> None:
        r = update_pattern_confidence("p", _reliable_scores(), 0.5, 100, 100, _cfg())
        assert "reliable" in r.explanation

    def test_noisy_category(self) -> None:
        r = update_pattern_confidence("p", _noisy_scores(), 0.5, 100, 100, _cfg())
        assert "noisy" in r.explanation

    def test_neutral_category(self) -> None:
        from umh.runtime.pattern_half_life import compute_pattern_noise, compute_pattern_reliability

        scores = [0.2, 0.5, 0.8, 0.2, 0.5, 0.8, 0.2, 0.5, 0.8, 0.2] * 2
        noise = compute_pattern_noise(scores)
        rel = compute_pattern_reliability(scores)
        cfg = _cfg(reliability_threshold=rel + 0.01, noise_threshold=noise + 0.01)
        r = update_pattern_confidence("p", scores, 0.5, 100, 100, cfg)
        assert "neutral" in r.explanation


# ===================================================================
# Section 39: Integration — aggregation unchanged without evolved confidence
# ===================================================================


class TestAggregationUnchanged:
    def test_pattern_aggregation_imports_unchanged(self) -> None:
        from umh.runtime.pattern_aggregation import compute_pattern_aggregation

        r = compute_pattern_aggregation()
        assert r.applied is False

    def test_pattern_confidence_module_importable(self) -> None:
        import umh.runtime.pattern_confidence

        assert hasattr(umh.runtime.pattern_confidence, "PatternConfidenceConfig")
        assert hasattr(umh.runtime.pattern_confidence, "PatternConfidenceMemory")
        assert hasattr(umh.runtime.pattern_confidence, "update_pattern_confidence")


# ===================================================================
# Section 40: Stress tests
# ===================================================================


class TestStress:
    def test_many_patterns(self) -> None:
        keys = [f"pattern_{i}" for i in range(100)]
        scores_map = {k: _reliable_scores() for k in keys}
        prev = {k: 0.5 for k in keys}
        last_seen = {k: 90 for k in keys}
        results = update_all_pattern_confidences(keys, scores_map, prev, 100, last_seen, _cfg())
        assert len(results) == 100
        assert all(r.new_confidence > 0.5 for r in results)

    def test_large_score_vector(self) -> None:
        scores = [0.8] * 100000
        r = update_pattern_confidence("p", scores, 0.5, 100, 100, _cfg())
        assert r.used_fallback is False
        assert r.new_confidence > 0.5

    def test_memory_many_updates(self) -> None:
        mem = PatternConfidenceMemory()
        cfg = _cfg()
        for i in range(500):
            mem.update(f"p_{i % 10}", _reliable_scores(), i, cfg)
        assert mem.size == 10
        snap = mem.snapshot()
        assert len(snap) == 10
