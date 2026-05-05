"""Phases 51-54 — Learning Control Block.

Tests covering:
- Phase 51: Outcome persistence (JSONL), temporal decay
- Phase 52: Controlled feedback influence with policy
- Phase 53: Adaptive learning strength
- Phase 54: Exploration vs exploitation policy
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import time

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime.outcome import OutcomeStatus, StrategyOutcome, StrategyStats
from umh.runtime.outcome_memory import OutcomeMemory
from umh.runtime.outcome_persistence import (
    FileOutcomePersistenceBackend,
    PersistenceResult,
    _line_to_outcome,
    _outcome_to_line,
)
from umh.runtime.outcome_decay import (
    DecayConfig,
    DecayResult,
    compute_decay_weight,
    compute_decayed_stats,
)
from umh.runtime.feedback_policy import (
    FeedbackInfluenceResult,
    FeedbackPolicy,
    compute_feedback_factor,
)
from umh.runtime.learning_strength import (
    LearningStrengthConfig,
    LearningStrengthResult,
    compute_learning_strength,
)
from umh.runtime.exploration import (
    ExplorationDecision,
    ExplorationPolicy,
    SelectionMode,
    select_candidate,
)


def _make_outcome(
    outcome_id: str = "o1",
    strategy_name: str = "aggressive",
    state_signature: str = "state_a",
    status: OutcomeStatus = OutcomeStatus.SUCCESS,
    success_score: float = 0.8,
    latency: float = 1.0,
    effort: float = 0.5,
    timestamp: str = "",
) -> StrategyOutcome:
    return StrategyOutcome(
        outcome_id=outcome_id,
        decision_id="d1",
        action_name="act",
        strategy_name=strategy_name,
        state_signature=state_signature,
        status=status,
        success_score=success_score,
        latency=latency,
        effort=effort,
        timestamp=timestamp,
    )


def _make_stats(
    strategy_name: str = "aggressive",
    total_count: int = 10,
    success_count: int = 7,
    failure_count: int = 3,
    average_success_score: float = 0.7,
) -> StrategyStats:
    return StrategyStats(
        strategy_name=strategy_name,
        total_count=total_count,
        success_count=success_count,
        failure_count=failure_count,
        partial_count=0,
        unknown_count=0,
        average_success_score=average_success_score,
        average_latency=1.0,
        average_effort=0.5,
    )


# ═══════════════════════════════════════════════════════════════════════
# PHASE 51 — PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════


# ── Section 1: JSONL serialization ───────────────────────────────────


class TestJsonlSerialization:
    def test_outcome_to_line(self):
        o = _make_outcome()
        line = _outcome_to_line(o)
        d = json.loads(line)
        assert d["outcome_id"] == "o1"

    def test_line_to_outcome(self):
        o = _make_outcome(success_score=0.75)
        line = _outcome_to_line(o)
        restored = _line_to_outcome(line)
        assert restored is not None
        assert restored.outcome_id == "o1"
        assert restored.success_score == 0.75

    def test_roundtrip(self):
        o = _make_outcome(status=OutcomeStatus.FAILURE, effort=0.3)
        line = _outcome_to_line(o)
        restored = _line_to_outcome(line)
        assert restored.status == OutcomeStatus.FAILURE
        assert restored.effort == 0.3

    def test_corrupted_line_returns_none(self):
        assert _line_to_outcome("not json") is None

    def test_empty_line_returns_none(self):
        assert _line_to_outcome("") is None

    def test_missing_field_returns_none(self):
        assert _line_to_outcome('{"outcome_id":"x"}') is None


# ── Section 2: File persistence backend ──────────────────────────────


class TestFilePersistence:
    def test_append_creates_file(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            backend = FileOutcomePersistenceBackend(path)
            assert backend.append_outcome(_make_outcome())
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_append_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            backend.append_outcome(_make_outcome(outcome_id="a"))
            backend.append_outcome(_make_outcome(outcome_id="b"))
            loaded = backend.load_outcomes()
            assert len(loaded) == 2
            assert loaded[0].outcome_id == "a"
            assert loaded[1].outcome_id == "b"
        finally:
            os.unlink(path)

    def test_load_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            assert backend.load_outcomes() == []
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        backend = FileOutcomePersistenceBackend("/tmp/nonexistent_outcome.jsonl")
        assert backend.load_outcomes() == []

    def test_corrupted_lines_skipped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
            o = _make_outcome()
            f.write(_outcome_to_line(o) + "\n")
            f.write("corrupted garbage\n")
            f.write(_outcome_to_line(_make_outcome(outcome_id="o2")) + "\n")
        try:
            backend = FileOutcomePersistenceBackend(path)
            loaded = backend.load_outcomes()
            assert len(loaded) == 2
        finally:
            os.unlink(path)

    def test_load_result_counts(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
            f.write(_outcome_to_line(_make_outcome()) + "\n")
            f.write("bad line\n")
        try:
            backend = FileOutcomePersistenceBackend(path)
            result = backend.load_result()
            assert result.success is True
            assert result.records_loaded == 1
            assert result.records_skipped == 1
        finally:
            os.unlink(path)

    def test_path_property(self):
        backend = FileOutcomePersistenceBackend("/tmp/test.jsonl")
        assert backend.path == "/tmp/test.jsonl"


# ── Section 3: Persistence result ────────────────────────────────────


class TestPersistenceResult:
    def test_success(self):
        r = PersistenceResult(success=True, records_loaded=5)
        assert r.success is True
        assert r.records_loaded == 5

    def test_to_dict(self):
        r = PersistenceResult(success=False, error="disk full")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "disk full"

    def test_frozen(self):
        r = PersistenceResult(success=True)
        with pytest.raises(AttributeError):
            r.success = False


# ── Section 4: OutcomeMemory with persistence ────────────────────────


class TestMemoryWithPersistence:
    def test_load_on_init(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
            f.write(_outcome_to_line(_make_outcome(outcome_id="pre")) + "\n")
        try:
            backend = FileOutcomePersistenceBackend(path)
            mem = OutcomeMemory(persistence_backend=backend)
            assert mem.count == 1
            assert mem.list_outcomes()[0].outcome_id == "pre"
        finally:
            os.unlink(path)

    def test_append_persists(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            mem = OutcomeMemory(persistence_backend=backend)
            mem.append(_make_outcome(outcome_id="new"))
            loaded = backend.load_outcomes()
            assert len(loaded) == 1
            assert loaded[0].outcome_id == "new"
        finally:
            os.unlink(path)

    def test_persistence_failure_does_not_crash(self):
        class FailBackend:
            def append_outcome(self, o):
                raise OSError("disk dead")

            def load_outcomes(self):
                return []

        mem = OutcomeMemory(persistence_backend=FailBackend())
        mem.append(_make_outcome())
        assert mem.count == 1
        assert mem.persistence_errors == 1

    def test_without_persistence(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome())
        assert mem.count == 1
        assert mem.persistence_errors == 0


# ── Section 5: Append-only invariant on persistence (inv 191) ────────


class TestPersistenceAppendOnly:
    def test_no_delete_on_backend(self):
        backend = FileOutcomePersistenceBackend("/tmp/test.jsonl")
        assert not hasattr(backend, "delete")
        assert not hasattr(backend, "remove")
        assert not hasattr(backend, "clear")

    def test_file_only_grows(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            backend.append_outcome(_make_outcome(outcome_id="a"))
            size1 = os.path.getsize(path)
            backend.append_outcome(_make_outcome(outcome_id="b"))
            size2 = os.path.getsize(path)
            assert size2 > size1
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════════════
# PHASE 51 — TEMPORAL DECAY
# ═══════════════════════════════════════════════════════════════════════


# ── Section 6: DecayConfig ───────────────────────────────────────────


class TestDecayConfig:
    def test_defaults(self):
        c = DecayConfig()
        assert c.half_life_seconds == 86400.0
        assert c.min_weight == 0.01
        assert c.max_weight == 1.0

    def test_clamp_half_life(self):
        c = DecayConfig(half_life_seconds=-10)
        assert c.half_life_seconds == 1.0

    def test_clamp_min_weight(self):
        c = DecayConfig(min_weight=-0.5)
        assert c.min_weight == 0.0

    def test_clamp_max_weight(self):
        c = DecayConfig(max_weight=5.0)
        assert c.max_weight == 1.0

    def test_frozen(self):
        c = DecayConfig()
        with pytest.raises(AttributeError):
            c.half_life_seconds = 100


# ── Section 7: Decay weight computation ──────────────────────────────


class TestDecayWeight:
    def test_zero_age_max_weight(self):
        c = DecayConfig()
        assert compute_decay_weight(0.0, c) == 1.0

    def test_one_half_life(self):
        c = DecayConfig(half_life_seconds=100.0)
        w = compute_decay_weight(100.0, c)
        assert abs(w - 0.5) < 1e-9

    def test_two_half_lives(self):
        c = DecayConfig(half_life_seconds=100.0)
        w = compute_decay_weight(200.0, c)
        assert abs(w - 0.25) < 1e-9

    def test_very_old_clamp_to_min(self):
        c = DecayConfig(half_life_seconds=100.0, min_weight=0.01)
        w = compute_decay_weight(100000.0, c)
        assert w == 0.01

    def test_negative_age_max_weight(self):
        c = DecayConfig()
        assert compute_decay_weight(-50.0, c) == 1.0

    def test_deterministic(self):
        c = DecayConfig(half_life_seconds=3600.0)
        w1 = compute_decay_weight(1800.0, c)
        w2 = compute_decay_weight(1800.0, c)
        assert w1 == w2


# ── Section 8: Decayed stats computation ─────────────────────────────


class TestDecayedStats:
    def test_empty_outcomes(self):
        r = compute_decayed_stats([], time.time())
        assert r.raw_count == 0
        assert r.effective_count == 0.0

    def test_single_recent_outcome(self):
        now = time.time()
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        o = _make_outcome(success_score=0.9, timestamp=ts)
        r = compute_decayed_stats([o], now)
        assert r.raw_count == 1
        assert r.effective_count > 0.9
        assert abs(r.weighted_average_score - 0.9) < 0.05

    def test_recent_favored_over_old(self):
        now = time.time()
        recent_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        old_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 864000))
        recent = _make_outcome(outcome_id="r", success_score=1.0, timestamp=recent_ts)
        old = _make_outcome(outcome_id="o", success_score=0.0, timestamp=old_ts)
        r = compute_decayed_stats([recent, old], now)
        assert r.weighted_average_score > 0.5

    def test_all_same_age(self):
        now = time.time()
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        outcomes = [
            _make_outcome(outcome_id=f"o{i}", success_score=0.6, timestamp=ts) for i in range(5)
        ]
        r = compute_decayed_stats(outcomes, now)
        assert abs(r.weighted_average_score - 0.6) < 0.01

    def test_success_rate_weighted(self):
        now = time.time()
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        outcomes = [
            _make_outcome(outcome_id="s1", status=OutcomeStatus.SUCCESS, timestamp=ts),
            _make_outcome(outcome_id="f1", status=OutcomeStatus.FAILURE, timestamp=ts),
        ]
        r = compute_decayed_stats(outcomes, now)
        assert abs(r.weighted_success_rate - 0.5) < 0.01

    def test_to_dict(self):
        r = DecayResult(
            raw_count=5,
            effective_count=3.5,
            weighted_success_rate=0.7,
            weighted_average_score=0.65,
            weighted_average_latency=1.2,
            weighted_average_effort=0.4,
        )
        d = r.to_dict()
        assert d["raw_count"] == 5
        assert d["effective_count"] == 3.5

    def test_frozen(self):
        r = DecayResult(0, 0.0, 0.0, 0.0, 0.0, 0.0)
        with pytest.raises(AttributeError):
            r.raw_count = 5

    def test_deterministic(self):
        now = time.time()
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600))
        outcomes = [
            _make_outcome(outcome_id=f"o{i}", success_score=0.7, timestamp=ts) for i in range(5)
        ]
        r1 = compute_decayed_stats(outcomes, now)
        r2 = compute_decayed_stats(outcomes, now)
        assert r1.weighted_average_score == r2.weighted_average_score


# ═══════════════════════════════════════════════════════════════════════
# PHASE 52 — FEEDBACK POLICY
# ═══════════════════════════════════════════════════════════════════════


# ── Section 9: FeedbackPolicy defaults ───────────────────────────────


class TestFeedbackPolicyDefaults:
    def test_disabled_by_default(self):
        p = FeedbackPolicy()
        assert p.enabled is False

    def test_default_samples(self):
        p = FeedbackPolicy()
        assert p.min_effective_samples == 10

    def test_default_bounds(self):
        p = FeedbackPolicy()
        assert p.max_boost == 0.10
        assert p.max_penalty == 0.10

    def test_clamp_samples(self):
        p = FeedbackPolicy(min_effective_samples=0)
        assert p.min_effective_samples == 1

    def test_clamp_boost(self):
        p = FeedbackPolicy(max_boost=0.5)
        assert p.max_boost == 0.25

    def test_clamp_penalty(self):
        p = FeedbackPolicy(max_penalty=-0.1)
        assert p.max_penalty == 0.0

    def test_frozen(self):
        p = FeedbackPolicy()
        with pytest.raises(AttributeError):
            p.enabled = True


# ── Section 10: Feedback disabled returns neutral (inv 198) ──────────


class TestFeedbackDisabled:
    def test_disabled_returns_neutral(self):
        stats = _make_stats()
        r = compute_feedback_factor(stats)
        assert r.factor == 1.0
        assert r.enabled is False

    def test_disabled_explicit(self):
        stats = _make_stats()
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=False))
        assert r.factor == 1.0

    def test_disabled_reason(self):
        stats = _make_stats()
        r = compute_feedback_factor(stats)
        assert "disabled" in r.reason


# ── Section 11: Insufficient samples neutral (inv 199) ──────────────


class TestFeedbackInsufficientSamples:
    def test_few_samples_neutral(self):
        stats = _make_stats(total_count=5)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert r.factor == 1.0

    def test_insufficient_reason(self):
        stats = _make_stats(total_count=3)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert "insufficient" in r.reason

    def test_confidence_partial(self):
        stats = _make_stats(total_count=5)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True, min_effective_samples=10))
        assert abs(r.confidence - 0.5) < 1e-9


# ── Section 12: Positive history boosts (inv 196) ───────────────────


class TestFeedbackBoost:
    def test_high_score_boosts(self):
        stats = _make_stats(total_count=10, average_success_score=0.9)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert r.factor > 1.0
        assert r.factor <= 1.10

    def test_max_boost_clamped(self):
        stats = _make_stats(total_count=10, average_success_score=1.0)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True, max_boost=0.10))
        assert r.factor <= 1.10

    def test_boost_explanation(self):
        stats = _make_stats(total_count=10, average_success_score=0.8)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert "boost" in r.reason


# ── Section 13: Negative history penalizes ───────────────────────────


class TestFeedbackPenalty:
    def test_low_score_penalizes(self):
        stats = _make_stats(total_count=10, average_success_score=0.1)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert r.factor < 1.0
        assert r.factor >= 0.90

    def test_min_penalty_clamped(self):
        stats = _make_stats(total_count=10, average_success_score=0.0)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True, max_penalty=0.10))
        assert r.factor >= 0.90

    def test_penalty_explanation(self):
        stats = _make_stats(total_count=10, average_success_score=0.2)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert "penalty" in r.reason


# ── Section 14: Feedback does not override base (inv 197) ────────────


class TestFeedbackBounded:
    def test_factor_within_bounds(self):
        for score in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            stats = _make_stats(total_count=20, average_success_score=score)
            r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
            assert 0.90 <= r.factor <= 1.10

    def test_neutral_at_0_5(self):
        stats = _make_stats(total_count=10, average_success_score=0.5)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert r.factor == 1.0


# ── Section 15: Feedback explanation (inv 200) ───────────────────────


class TestFeedbackExplanation:
    def test_explanation_has_score(self):
        stats = _make_stats(total_count=10, average_success_score=0.7)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert "avg_score" in r.reason

    def test_explanation_has_samples(self):
        stats = _make_stats(total_count=15)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert "samples=15" in r.reason

    def test_explanation_has_confidence(self):
        stats = _make_stats(total_count=10)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
        assert "confidence" in r.reason


# ── Section 16: FeedbackInfluenceResult ──────────────────────────────


class TestFeedbackInfluenceResult:
    def test_to_dict(self):
        r = FeedbackInfluenceResult(
            factor=1.05,
            confidence=0.8,
            reason="boost",
            effective_samples=15,
            weighted_success_rate=0.7,
            enabled=True,
        )
        d = r.to_dict()
        assert d["factor"] == 1.05
        assert d["enabled"] is True

    def test_frozen(self):
        r = FeedbackInfluenceResult(1.0, 0.0, "", 0, 0.0, False)
        with pytest.raises(AttributeError):
            r.factor = 1.1


# ═══════════════════════════════════════════════════════════════════════
# PHASE 53 — LEARNING STRENGTH
# ═══════════════════════════════════════════════════════════════════════


# ── Section 17: LearningStrengthConfig ───────────────────────────────


class TestLearningStrengthConfig:
    def test_defaults(self):
        c = LearningStrengthConfig()
        assert c.min_strength == 0.25
        assert c.max_strength == 1.0
        assert c.required_samples == 20
        assert c.volatility_penalty == 0.5

    def test_clamp_min(self):
        c = LearningStrengthConfig(min_strength=-1.0)
        assert c.min_strength == 0.0

    def test_clamp_max(self):
        c = LearningStrengthConfig(max_strength=5.0)
        assert c.max_strength == 1.0

    def test_clamp_samples(self):
        c = LearningStrengthConfig(required_samples=0)
        assert c.required_samples == 1

    def test_frozen(self):
        c = LearningStrengthConfig()
        with pytest.raises(AttributeError):
            c.min_strength = 0.5


# ── Section 18: Sparse data reduces strength (inv 203) ──────────────


class TestSparseDataStrength:
    def test_no_outcomes_min_strength(self):
        r = compute_learning_strength([])
        assert r.strength == 0.25
        assert r.reason == "no outcomes"

    def test_few_outcomes_low_strength(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.8) for i in range(5)]
        r = compute_learning_strength(outcomes)
        assert r.strength < 1.0

    def test_sample_factor_partial(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.8) for i in range(10)]
        r = compute_learning_strength(outcomes)
        assert r.sample_factor == 0.5


# ── Section 19: Volatility reduces strength (inv 204) ───────────────


class TestVolatileStrength:
    def test_high_volatility_lower_strength(self):
        outcomes = []
        for i in range(20):
            score = 1.0 if i % 2 == 0 else 0.0
            outcomes.append(_make_outcome(outcome_id=f"o{i}", success_score=score))
        r = compute_learning_strength(outcomes)
        assert r.volatility > 0.4
        assert r.strength < 1.0

    def test_volatility_reason(self):
        outcomes = []
        for i in range(20):
            score = 1.0 if i % 2 == 0 else 0.0
            outcomes.append(_make_outcome(outcome_id=f"o{i}", success_score=score))
        r = compute_learning_strength(outcomes)
        assert "volatility" in r.reason.lower() or "vol" in r.reason.lower()


# ── Section 20: Stable patterns increase strength (inv 205) ─────────


class TestStableStrength:
    def test_stable_high_count_high_strength(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.8) for i in range(20)]
        r = compute_learning_strength(outcomes)
        assert r.strength > 0.8
        assert r.volatility < 0.1

    def test_stable_reason(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.8) for i in range(20)]
        r = compute_learning_strength(outcomes)
        assert "stable" in r.reason


# ── Section 21: Strength bounded (inv 202) ───────────────────────────


class TestStrengthBounded:
    def test_always_above_min(self):
        outcomes = []
        for i in range(20):
            score = 1.0 if i % 2 == 0 else 0.0
            outcomes.append(_make_outcome(outcome_id=f"o{i}", success_score=score))
        r = compute_learning_strength(outcomes)
        assert r.strength >= 0.25

    def test_always_below_max(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.8) for i in range(100)]
        r = compute_learning_strength(outcomes)
        assert r.strength <= 1.0


# ── Section 22: Strength deterministic (inv 201) ────────────────────


class TestStrengthDeterministic:
    def test_same_input_same_output(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.6) for i in range(15)]
        r1 = compute_learning_strength(outcomes)
        r2 = compute_learning_strength(outcomes)
        assert r1.strength == r2.strength
        assert r1.volatility == r2.volatility


# ── Section 23: LearningStrengthResult ───────────────────────────────


class TestLearningStrengthResult:
    def test_to_dict(self):
        r = LearningStrengthResult(
            strength=0.75,
            confidence=0.8,
            volatility=0.1,
            sample_factor=0.9,
            reason="moderate",
        )
        d = r.to_dict()
        assert d["strength"] == 0.75
        assert "reason" in d

    def test_frozen(self):
        r = LearningStrengthResult(0.5, 0.5, 0.1, 0.5, "test")
        with pytest.raises(AttributeError):
            r.strength = 1.0


# ── Section 24: Learning strength dampens feedback ───────────────────


class TestStrengthDampensFeedback:
    def test_low_strength_reduces_factor(self):
        stats = _make_stats(total_count=10, average_success_score=0.9)
        r_full = compute_feedback_factor(stats, FeedbackPolicy(enabled=True), learning_strength=1.0)
        r_half = compute_feedback_factor(stats, FeedbackPolicy(enabled=True), learning_strength=0.5)
        assert r_full.factor > r_half.factor

    def test_zero_strength_neutral(self):
        stats = _make_stats(total_count=10, average_success_score=0.9)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True), learning_strength=0.0)
        assert r.factor == 1.0

    def test_full_strength_unchanged(self):
        stats = _make_stats(total_count=10, average_success_score=0.8)
        r_default = compute_feedback_factor(
            stats, FeedbackPolicy(enabled=True), learning_strength=1.0
        )
        r_full = compute_feedback_factor(stats, FeedbackPolicy(enabled=True), learning_strength=1.0)
        assert r_default.factor == r_full.factor


# ═══════════════════════════════════════════════════════════════════════
# PHASE 54 — EXPLORATION VS EXPLOITATION
# ═══════════════════════════════════════════════════════════════════════


# ── Section 25: ExplorationPolicy defaults ───────────────────────────


class TestExplorationPolicyDefaults:
    def test_disabled_by_default(self):
        p = ExplorationPolicy()
        assert p.enabled is False

    def test_default_rate(self):
        p = ExplorationPolicy()
        assert p.exploration_rate == 0.05

    def test_default_confidence(self):
        p = ExplorationPolicy()
        assert p.min_confidence_for_exploitation == 0.7

    def test_rate_clamp_high(self):
        p = ExplorationPolicy(exploration_rate=0.5)
        assert p.exploration_rate == 0.25

    def test_rate_clamp_low(self):
        p = ExplorationPolicy(exploration_rate=-0.1)
        assert p.exploration_rate == 0.0

    def test_frozen(self):
        p = ExplorationPolicy()
        with pytest.raises(AttributeError):
            p.enabled = True


# ── Section 26: Exploitation selects best ────────────────────────────


class TestExploitationSelectsBest:
    def test_best_score_selected(self):
        r = select_candidate(["a", "b", "c"], [0.3, 0.9, 0.5], 0.8)
        assert r.selected_candidate == "b"
        assert r.mode == SelectionMode.EXPLOIT

    def test_first_when_tied(self):
        r = select_candidate(["a", "b"], [0.5, 0.5], 0.8)
        assert r.selected_candidate == "a"

    def test_single_candidate(self):
        r = select_candidate(["only"], [0.5], 0.8)
        assert r.selected_candidate == "only"
        assert r.mode == SelectionMode.EXPLOIT


# ── Section 27: Exploration disabled selects best (inv 206) ─────────


class TestExplorationDisabledExploits:
    def test_disabled_always_exploits(self):
        r = select_candidate(
            ["a", "b", "c"],
            [0.3, 0.9, 0.5],
            0.2,
            ExplorationPolicy(enabled=False),
        )
        assert r.selected_candidate == "b"
        assert r.mode == SelectionMode.EXPLOIT

    def test_disabled_reason(self):
        r = select_candidate(["a"], [0.5], 0.5, ExplorationPolicy(enabled=False))
        assert "disabled" in r.reason


# ── Section 28: High confidence exploits (inv 207) ──────────────────


class TestHighConfidenceExploits:
    def test_high_confidence_exploits(self):
        r = select_candidate(
            ["a", "b"],
            [0.3, 0.9],
            0.9,
            ExplorationPolicy(enabled=True, min_confidence_for_exploitation=0.7),
        )
        assert r.selected_candidate == "b"
        assert r.mode == SelectionMode.EXPLOIT

    def test_at_threshold_exploits(self):
        r = select_candidate(
            ["a", "b"],
            [0.3, 0.9],
            0.7,
            ExplorationPolicy(enabled=True, min_confidence_for_exploitation=0.7),
        )
        assert r.mode == SelectionMode.EXPLOIT


# ── Section 29: Low confidence explores ──────────────────────────────


class TestLowConfidenceExplores:
    def test_low_confidence_explores(self):
        r = select_candidate(
            ["a", "b", "c"],
            [0.9, 0.3, 0.5],
            0.3,
            ExplorationPolicy(enabled=True, min_confidence_for_exploitation=0.7),
        )
        assert r.mode == SelectionMode.EXPLORE
        assert r.selected_candidate != "a"

    def test_explore_selects_second_best_without_seed(self):
        r = select_candidate(
            ["a", "b", "c"],
            [0.9, 0.3, 0.5],
            0.3,
            ExplorationPolicy(enabled=True),
        )
        assert r.selected_candidate == "c"

    def test_explore_reason(self):
        r = select_candidate(
            ["a", "b"],
            [0.9, 0.3],
            0.3,
            ExplorationPolicy(enabled=True),
        )
        assert "low confidence" in r.reason


# ── Section 30: Seeded selection deterministic (inv 210) ─────────────


class TestSeededSelection:
    def test_seeded_deterministic(self):
        r1 = select_candidate(
            ["a", "b", "c"],
            [0.9, 0.3, 0.5],
            0.3,
            ExplorationPolicy(enabled=True, seed=42),
        )
        r2 = select_candidate(
            ["a", "b", "c"],
            [0.9, 0.3, 0.5],
            0.3,
            ExplorationPolicy(enabled=True, seed=42),
        )
        assert r1.selected_candidate == r2.selected_candidate

    def test_different_seeds_may_differ(self):
        r1 = select_candidate(
            ["a", "b", "c", "d"],
            [0.9, 0.3, 0.5, 0.4],
            0.3,
            ExplorationPolicy(enabled=True, seed=0),
        )
        r2 = select_candidate(
            ["a", "b", "c", "d"],
            [0.9, 0.3, 0.5, 0.4],
            0.3,
            ExplorationPolicy(enabled=True, seed=1),
        )
        assert r1.mode == SelectionMode.EXPLORE
        assert r2.mode == SelectionMode.EXPLORE


# ── Section 31: Exploration rate bounded (inv 209) ───────────────────


class TestExplorationRateBounded:
    def test_rate_in_decision(self):
        r = select_candidate(
            ["a", "b"],
            [0.9, 0.3],
            0.3,
            ExplorationPolicy(enabled=True, exploration_rate=0.15),
        )
        assert r.exploration_rate == 0.15

    def test_rate_clamped_in_policy(self):
        p = ExplorationPolicy(exploration_rate=0.5)
        assert p.exploration_rate == 0.25


# ── Section 32: Empty candidates ─────────────────────────────────────


class TestEmptyCandidates:
    def test_no_candidates(self):
        r = select_candidate([], [], 0.5)
        assert r.selected_index == -1
        assert r.selected_candidate == ""
        assert r.mode == SelectionMode.EXPLOIT

    def test_mismatched_scores_padded(self):
        r = select_candidate(["a", "b", "c"], [0.5], 0.8)
        assert r.selected_candidate == "a"

    def test_extra_scores_trimmed(self):
        r = select_candidate(["a"], [0.5, 0.9], 0.8)
        assert r.selected_candidate == "a"


# ── Section 33: ExplorationDecision ──────────────────────────────────


class TestExplorationDecision:
    def test_to_dict(self):
        r = select_candidate(["a", "b"], [0.5, 0.9], 0.8)
        d = r.to_dict()
        assert d["selected_candidate"] == "b"
        assert d["mode"] == "exploit"

    def test_frozen(self):
        r = select_candidate(["a"], [0.5], 0.5)
        with pytest.raises(AttributeError):
            r.selected_candidate = "x"


# ── Section 34: SelectionMode enum ───────────────────────────────────


class TestSelectionMode:
    def test_exploit(self):
        assert SelectionMode.EXPLOIT.value == "exploit"

    def test_explore(self):
        assert SelectionMode.EXPLORE.value == "explore"

    def test_two_members(self):
        assert len(SelectionMode) == 2


# ═══════════════════════════════════════════════════════════════════════
# CROSS-PHASE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════


# ── Section 35: Full pipeline integration ────────────────────────────


class TestFullPipeline:
    def test_outcome_persist_decay_feedback_strength(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            mem = OutcomeMemory(persistence_backend=backend)

            now = time.time()
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
            for i in range(15):
                mem.append(
                    _make_outcome(
                        outcome_id=f"o{i}",
                        success_score=0.8,
                        timestamp=ts,
                    )
                )

            outcomes = mem.list_outcomes()
            strength_r = compute_learning_strength(outcomes)
            assert strength_r.strength > 0.5

            stats = mem.compute_strategy_stats("aggressive")
            policy = FeedbackPolicy(enabled=True)
            fb = compute_feedback_factor(stats, policy, learning_strength=strength_r.strength)
            assert fb.factor > 1.0
            assert fb.enabled is True
        finally:
            os.unlink(path)

    def test_pipeline_with_exploration(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.7) for i in range(10)]
        strength_r = compute_learning_strength(outcomes)

        signal = StrategyStats(
            strategy_name="x",
            total_count=10,
            success_count=7,
            failure_count=3,
            partial_count=0,
            unknown_count=0,
            average_success_score=0.7,
            average_latency=1.0,
            average_effort=0.5,
        )
        fb = compute_feedback_factor(signal, FeedbackPolicy(enabled=True), strength_r.strength)

        candidates = ["agg", "con", "bal"]
        scores = [fb.factor, 0.95, 0.90]
        decision = select_candidate(
            candidates,
            scores,
            fb.confidence,
            ExplorationPolicy(enabled=True),
        )
        assert decision.selected_candidate in candidates


# ── Section 36: Import surface ───────────────────────────────────────


class TestImportSurface:
    def test_all_importable(self):
        from umh.runtime import (
            FileOutcomePersistenceBackend,
            PersistenceResult,
            DecayConfig,
            DecayResult,
            compute_decay_weight,
            compute_decayed_stats,
            FeedbackInfluenceResult,
            FeedbackPolicy,
            compute_feedback_factor,
            LearningStrengthConfig,
            LearningStrengthResult,
            compute_learning_strength,
            ExplorationDecision,
            ExplorationPolicy,
            SelectionMode,
            select_candidate,
        )

        assert FileOutcomePersistenceBackend is not None
        assert PersistenceResult is not None
        assert DecayConfig is not None
        assert DecayResult is not None
        assert compute_decay_weight is not None
        assert compute_decayed_stats is not None
        assert FeedbackInfluenceResult is not None
        assert FeedbackPolicy is not None
        assert compute_feedback_factor is not None
        assert LearningStrengthConfig is not None
        assert LearningStrengthResult is not None
        assert compute_learning_strength is not None
        assert ExplorationDecision is not None
        assert ExplorationPolicy is not None
        assert SelectionMode is not None
        assert select_candidate is not None


# ── Section 37: No boundary violations ───────────────────────────────


class TestBoundaryViolations:
    def test_no_cells_in_persistence(self):
        import umh.runtime.outcome_persistence as mod

        source = open(mod.__file__).read()
        assert "umh.cells" not in source

    def test_no_cells_in_decay(self):
        import umh.runtime.outcome_decay as mod

        source = open(mod.__file__).read()
        assert "umh.cells" not in source

    def test_no_cells_in_policy(self):
        import umh.runtime.feedback_policy as mod

        source = open(mod.__file__).read()
        assert "umh.cells" not in source

    def test_no_cells_in_strength(self):
        import umh.runtime.learning_strength as mod

        source = open(mod.__file__).read()
        assert "umh.cells" not in source

    def test_no_cells_in_exploration(self):
        import umh.runtime.exploration as mod

        source = open(mod.__file__).read()
        assert "umh.cells" not in source


# ── Section 38: Historical immutability (inv 192) ───────────────────


class TestHistoricalImmutability:
    def test_persistence_outcomes_frozen(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            backend.append_outcome(_make_outcome())
            loaded = backend.load_outcomes()
            with pytest.raises(AttributeError):
                loaded[0].success_score = 0.99
        finally:
            os.unlink(path)


# ── Section 39: Default behavior unchanged (inv 198) ────────────────


class TestDefaultBehaviorUnchanged:
    def test_feedback_default_neutral(self):
        stats = _make_stats(total_count=100, average_success_score=1.0)
        r = compute_feedback_factor(stats)
        assert r.factor == 1.0

    def test_exploration_default_exploits(self):
        r = select_candidate(["a", "b"], [0.3, 0.9], 0.1)
        assert r.mode == SelectionMode.EXPLOIT

    def test_memory_default_no_persistence(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome())
        assert mem.persistence_errors == 0


# ── Section 40: Decay old data survives (inv 195) ───────────────────


class TestDecayOldDataSurvives:
    def test_old_data_still_contributes(self):
        now = time.time()
        old_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 864000))
        outcomes = [_make_outcome(success_score=1.0, timestamp=old_ts)]
        r = compute_decayed_stats(outcomes, now)
        assert r.effective_count > 0.0
        assert r.weighted_average_score > 0.0

    def test_decay_never_zero(self):
        now = time.time()
        very_old_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 86400000))
        outcomes = [_make_outcome(success_score=0.5, timestamp=very_old_ts)]
        cfg = DecayConfig(min_weight=0.001)
        r = compute_decayed_stats(outcomes, now, cfg)
        assert r.effective_count >= 0.001


# ── Section 41: Exploration never selects invalid (inv 208) ─────────


class TestExplorationNeverInvalid:
    def test_only_valid_candidates_selected(self):
        for seed in range(20):
            r = select_candidate(
                ["a", "b", "c"],
                [0.9, 0.5, 0.3],
                0.2,
                ExplorationPolicy(enabled=True, seed=seed),
            )
            assert r.selected_candidate in ["a", "b", "c"]

    def test_single_candidate_never_explores(self):
        r = select_candidate(
            ["only"],
            [0.5],
            0.1,
            ExplorationPolicy(enabled=True),
        )
        assert r.selected_candidate == "only"
        assert r.mode == SelectionMode.EXPLOIT


# ── Section 42: Feedback with learning strength end-to-end ──────────


class TestFeedbackStrengthEndToEnd:
    def test_volatile_outcomes_dampen_feedback(self):
        volatile = []
        for i in range(20):
            score = 1.0 if i % 2 == 0 else 0.0
            volatile.append(_make_outcome(outcome_id=f"v{i}", success_score=score))
        ls = compute_learning_strength(volatile)

        stats = _make_stats(total_count=20, average_success_score=0.5)
        fb = compute_feedback_factor(stats, FeedbackPolicy(enabled=True), ls.strength)
        assert fb.factor == 1.0

    def test_stable_outcomes_full_feedback(self):
        stable = [_make_outcome(outcome_id=f"s{i}", success_score=0.9) for i in range(20)]
        ls = compute_learning_strength(stable)
        assert ls.strength > 0.8

        stats = _make_stats(total_count=20, average_success_score=0.9)
        fb = compute_feedback_factor(stats, FeedbackPolicy(enabled=True), ls.strength)
        assert fb.factor > 1.0


# ── Section 43: Persistence to_dict updated ─────────────────────────


class TestMemoryToDictUpdated:
    def test_persistence_errors_in_dict(self):
        mem = OutcomeMemory()
        d = mem.to_dict()
        assert "persistence_errors" in d
        assert d["persistence_errors"] == 0


# ── Section 44: Serialization roundtrip edge cases ─────────────────


class TestSerializationEdgeCases:
    def test_metadata_preserved(self):
        o = _make_outcome()
        o2 = StrategyOutcome(
            outcome_id="m1",
            decision_id="d1",
            action_name="act",
            strategy_name="agg",
            state_signature="s1",
            metadata={"key": "value", "nested": {"a": 1}},
        )
        line = _outcome_to_line(o2)
        restored = _line_to_outcome(line)
        assert restored.metadata["key"] == "value"
        assert restored.metadata["nested"]["a"] == 1

    def test_all_statuses_roundtrip(self):
        for status in OutcomeStatus:
            o = _make_outcome(status=status)
            line = _outcome_to_line(o)
            restored = _line_to_outcome(line)
            assert restored.status == status

    def test_zero_scores_roundtrip(self):
        o = _make_outcome(success_score=0.0, latency=0.0, effort=0.0)
        line = _outcome_to_line(o)
        restored = _line_to_outcome(line)
        assert restored.success_score == 0.0
        assert restored.latency == 0.0
        assert restored.effort == 0.0

    def test_max_scores_roundtrip(self):
        o = _make_outcome(success_score=1.0, effort=1.0)
        line = _outcome_to_line(o)
        restored = _line_to_outcome(line)
        assert restored.success_score == 1.0
        assert restored.effort == 1.0

    def test_timestamp_preserved(self):
        o = _make_outcome(timestamp="2026-01-15T10:30:00Z")
        line = _outcome_to_line(o)
        restored = _line_to_outcome(line)
        assert restored.timestamp == "2026-01-15T10:30:00Z"

    def test_partial_json_returns_none(self):
        assert _line_to_outcome('{"outcome_id": "x", "decision_id": "d"') is None

    def test_wrong_type_returns_none(self):
        assert _line_to_outcome("[1, 2, 3]") is None


# ── Section 45: File persistence multi-append ───────────────────────


class TestFilePersistenceMultiAppend:
    def test_many_appends(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            for i in range(50):
                assert backend.append_outcome(_make_outcome(outcome_id=f"o{i}"))
            loaded = backend.load_outcomes()
            assert len(loaded) == 50
            assert loaded[49].outcome_id == "o49"
        finally:
            os.unlink(path)

    def test_append_after_load(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            backend.append_outcome(_make_outcome(outcome_id="first"))
            loaded1 = backend.load_outcomes()
            assert len(loaded1) == 1
            backend.append_outcome(_make_outcome(outcome_id="second"))
            loaded2 = backend.load_outcomes()
            assert len(loaded2) == 2
        finally:
            os.unlink(path)

    def test_interleaved_read_write(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            backend.append_outcome(_make_outcome(outcome_id="a"))
            assert len(backend.load_outcomes()) == 1
            backend.append_outcome(_make_outcome(outcome_id="b"))
            assert len(backend.load_outcomes()) == 2
            backend.append_outcome(_make_outcome(outcome_id="c"))
            assert len(backend.load_outcomes()) == 3
        finally:
            os.unlink(path)


# ── Section 46: Decay config edge cases ─────────────────────────────


class TestDecayConfigEdge:
    def test_min_equals_max(self):
        c = DecayConfig(min_weight=0.5, max_weight=0.5)
        assert c.min_weight == 0.5
        assert c.max_weight == 0.5

    def test_min_greater_than_max_clamped(self):
        c = DecayConfig(min_weight=0.8, max_weight=0.3)
        assert c.max_weight >= c.min_weight

    def test_very_short_half_life(self):
        c = DecayConfig(half_life_seconds=0.5)
        assert c.half_life_seconds == 1.0

    def test_very_long_half_life(self):
        c = DecayConfig(half_life_seconds=86400 * 365)
        w = compute_decay_weight(3600.0, c)
        assert w > 0.99


# ── Section 47: Decay weight mathematical properties ────────────────


class TestDecayWeightMath:
    def test_monotonically_decreasing(self):
        c = DecayConfig(half_life_seconds=100.0)
        prev = compute_decay_weight(0.0, c)
        for age in [10, 20, 50, 100, 200, 500]:
            w = compute_decay_weight(float(age), c)
            assert w <= prev
            prev = w

    def test_three_half_lives(self):
        c = DecayConfig(half_life_seconds=100.0, min_weight=0.0)
        w = compute_decay_weight(300.0, c)
        assert abs(w - 0.125) < 1e-9

    def test_small_age_close_to_max(self):
        c = DecayConfig(half_life_seconds=86400.0)
        w = compute_decay_weight(1.0, c)
        assert w > 0.999

    def test_custom_max_weight(self):
        c = DecayConfig(max_weight=0.8)
        w = compute_decay_weight(0.0, c)
        assert w == 0.8


# ── Section 48: Decayed stats with varied timestamps ────────────────


class TestDecayedStatsTimestamps:
    def test_no_timestamp_treated_as_recent(self):
        o = _make_outcome(success_score=0.9, timestamp="")
        now = time.time()
        r = compute_decayed_stats([o], now)
        assert r.weighted_average_score > 0.85

    def test_invalid_timestamp_treated_as_recent(self):
        o = _make_outcome(success_score=0.7, timestamp="not-a-date")
        now = time.time()
        r = compute_decayed_stats([o], now)
        assert r.weighted_average_score > 0.65

    def test_future_timestamp_max_weight(self):
        now = time.time()
        future_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + 3600))
        o = _make_outcome(success_score=0.5, timestamp=future_ts)
        r = compute_decayed_stats([o], now)
        assert r.effective_count >= 0.99

    def test_latency_and_effort_weighted(self):
        now = time.time()
        recent_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        o = _make_outcome(success_score=0.5, latency=2.0, effort=0.3, timestamp=recent_ts)
        r = compute_decayed_stats([o], now)
        assert abs(r.weighted_average_latency - 2.0) < 0.1
        assert abs(r.weighted_average_effort - 0.3) < 0.1


# ── Section 49: Feedback policy config clamping exhaustive ──────────


class TestFeedbackPolicyClamping:
    def test_boost_negative_clamped(self):
        p = FeedbackPolicy(max_boost=-1.0)
        assert p.max_boost == 0.0

    def test_penalty_over_max_clamped(self):
        p = FeedbackPolicy(max_penalty=0.5)
        assert p.max_penalty == 0.25

    def test_samples_very_large(self):
        p = FeedbackPolicy(min_effective_samples=10000)
        assert p.min_effective_samples == 10000

    def test_neutral_factor_preserved(self):
        p = FeedbackPolicy(neutral_factor=0.95)
        assert p.neutral_factor == 0.95


# ── Section 50: Feedback factor sweep ───────────────────────────────


class TestFeedbackFactorSweep:
    def test_monotonic_with_score(self):
        scores = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        factors = []
        for s in scores:
            stats = _make_stats(total_count=20, average_success_score=s)
            r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True))
            factors.append(r.factor)
        for i in range(1, len(factors)):
            assert factors[i] >= factors[i - 1]

    def test_symmetric_around_neutral(self):
        s_high = _make_stats(total_count=20, average_success_score=0.7)
        s_low = _make_stats(total_count=20, average_success_score=0.3)
        r_high = compute_feedback_factor(s_high, FeedbackPolicy(enabled=True))
        r_low = compute_feedback_factor(s_low, FeedbackPolicy(enabled=True))
        assert abs((r_high.factor - 1.0) - (1.0 - r_low.factor)) < 1e-9

    def test_exactly_at_threshold_sufficient(self):
        stats = _make_stats(total_count=10, average_success_score=0.8)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True, min_effective_samples=10))
        assert r.factor > 1.0


# ── Section 51: Learning strength config edge cases ─────────────────


class TestLearningStrengthConfigEdge:
    def test_max_less_than_min_clamped(self):
        c = LearningStrengthConfig(min_strength=0.8, max_strength=0.3)
        assert c.max_strength >= c.min_strength

    def test_volatility_penalty_at_zero(self):
        c = LearningStrengthConfig(volatility_penalty=0.0)
        outcomes = []
        for i in range(20):
            score = 1.0 if i % 2 == 0 else 0.0
            outcomes.append(_make_outcome(outcome_id=f"o{i}", success_score=score))
        r = compute_learning_strength(outcomes, c)
        assert r.strength == c.max_strength

    def test_volatility_penalty_at_max(self):
        c = LearningStrengthConfig(volatility_penalty=1.0)
        outcomes = []
        for i in range(20):
            score = 1.0 if i % 2 == 0 else 0.0
            outcomes.append(_make_outcome(outcome_id=f"o{i}", success_score=score))
        r = compute_learning_strength(outcomes, c)
        assert r.strength < 0.6


# ── Section 52: Single outcome learning strength ────────────────────


class TestSingleOutcomeStrength:
    def test_single_outcome_low_confidence(self):
        o = [_make_outcome()]
        r = compute_learning_strength(o)
        assert r.confidence < 0.1
        assert r.sample_factor < 0.1

    def test_single_outcome_zero_volatility(self):
        o = [_make_outcome()]
        r = compute_learning_strength(o)
        assert r.volatility == 0.0


# ── Section 53: Exploration with many candidates ────────────────────


class TestExplorationManyCandidates:
    def test_ten_candidates(self):
        cands = [f"c{i}" for i in range(10)]
        scores = [float(i) / 10 for i in range(10)]
        r = select_candidate(cands, scores, 0.3, ExplorationPolicy(enabled=True))
        assert r.mode == SelectionMode.EXPLORE
        assert r.selected_candidate != "c9"
        assert r.selected_candidate in cands

    def test_all_same_scores(self):
        cands = ["a", "b", "c"]
        scores = [0.5, 0.5, 0.5]
        r = select_candidate(cands, scores, 0.3, ExplorationPolicy(enabled=True))
        assert r.selected_candidate in cands

    def test_explore_never_selects_best(self):
        cands = ["best", "alt1", "alt2"]
        scores = [0.99, 0.1, 0.2]
        for seed in range(10):
            r = select_candidate(cands, scores, 0.2, ExplorationPolicy(enabled=True, seed=seed))
            if r.mode == SelectionMode.EXPLORE:
                assert r.selected_candidate != "best"


# ── Section 54: Exploration confidence boundary ─────────────────────


class TestExplorationConfidenceBoundary:
    def test_just_below_threshold(self):
        r = select_candidate(
            ["a", "b"],
            [0.9, 0.3],
            0.699,
            ExplorationPolicy(enabled=True, min_confidence_for_exploitation=0.7),
        )
        assert r.mode == SelectionMode.EXPLORE

    def test_just_at_threshold(self):
        r = select_candidate(
            ["a", "b"],
            [0.9, 0.3],
            0.7,
            ExplorationPolicy(enabled=True, min_confidence_for_exploitation=0.7),
        )
        assert r.mode == SelectionMode.EXPLOIT

    def test_zero_confidence_explores(self):
        r = select_candidate(
            ["a", "b"],
            [0.9, 0.3],
            0.0,
            ExplorationPolicy(enabled=True),
        )
        assert r.mode == SelectionMode.EXPLORE


# ── Section 55: No I/O in pure modules ──────────────────────────────


class TestNoIOInPureModules:
    def test_no_os_import_in_decay(self):
        import umh.runtime.outcome_decay as mod

        source = open(mod.__file__).read()
        assert "import os" not in source

    def test_no_os_import_in_policy(self):
        import umh.runtime.feedback_policy as mod

        source = open(mod.__file__).read()
        assert "import os" not in source

    def test_no_os_import_in_strength(self):
        import umh.runtime.learning_strength as mod

        source = open(mod.__file__).read()
        assert "import os" not in source

    def test_no_os_import_in_exploration(self):
        import umh.runtime.exploration as mod

        source = open(mod.__file__).read()
        assert "import os" not in source

    def test_no_subprocess_import_in_persistence(self):
        import umh.runtime.outcome_persistence as mod

        source = open(mod.__file__).read()
        assert "import subprocess" not in source


# ── Section 56: Feedback learning strength interaction ──────────────


class TestFeedbackLearningStrengthInteraction:
    def test_strength_scales_boost_linearly(self):
        stats = _make_stats(total_count=20, average_success_score=1.0)
        p = FeedbackPolicy(enabled=True)
        r_full = compute_feedback_factor(stats, p, learning_strength=1.0)
        r_half = compute_feedback_factor(stats, p, learning_strength=0.5)
        boost_full = r_full.factor - 1.0
        boost_half = r_half.factor - 1.0
        assert abs(boost_half - boost_full * 0.5) < 1e-9

    def test_strength_scales_penalty_linearly(self):
        stats = _make_stats(total_count=20, average_success_score=0.0)
        p = FeedbackPolicy(enabled=True)
        r_full = compute_feedback_factor(stats, p, learning_strength=1.0)
        r_half = compute_feedback_factor(stats, p, learning_strength=0.5)
        pen_full = 1.0 - r_full.factor
        pen_half = 1.0 - r_half.factor
        assert abs(pen_half - pen_full * 0.5) < 1e-9

    def test_negative_strength_clamped(self):
        stats = _make_stats(total_count=10, average_success_score=0.9)
        r = compute_feedback_factor(stats, FeedbackPolicy(enabled=True), learning_strength=-1.0)
        assert r.factor == 1.0


# ── Section 57: Persistence result edge cases ───────────────────────


class TestPersistenceResultEdge:
    def test_default_zeros(self):
        r = PersistenceResult(success=True)
        assert r.records_written == 0
        assert r.records_loaded == 0
        assert r.records_skipped == 0
        assert r.error == ""

    def test_error_string_preserved(self):
        r = PersistenceResult(success=False, error="permission denied /var/data.jsonl")
        d = r.to_dict()
        assert "permission denied" in d["error"]

    def test_all_fields_in_dict(self):
        r = PersistenceResult(
            success=True, records_written=3, records_loaded=10, records_skipped=2, error=""
        )
        d = r.to_dict()
        assert set(d.keys()) == {
            "success",
            "records_written",
            "records_loaded",
            "records_skipped",
            "error",
        }


# ── Section 58: OutcomeMemory persistence error counting ────────────


class TestPersistenceErrorCounting:
    def test_return_false_increments(self):
        class FalseBackend:
            def append_outcome(self, o):
                return False

            def load_outcomes(self):
                return []

        mem = OutcomeMemory(persistence_backend=FalseBackend())
        mem.append(_make_outcome())
        mem.append(_make_outcome(outcome_id="o2"))
        assert mem.persistence_errors == 2
        assert mem.count == 2

    def test_exception_increments(self):
        class ExcBackend:
            def append_outcome(self, o):
                raise RuntimeError("boom")

            def load_outcomes(self):
                return []

        mem = OutcomeMemory(persistence_backend=ExcBackend())
        mem.append(_make_outcome())
        assert mem.persistence_errors == 1

    def test_mixed_success_failure(self):
        call_count = 0

        class MixedBackend:
            def append_outcome(self, o):
                nonlocal call_count
                call_count += 1
                return call_count % 2 == 1

            def load_outcomes(self):
                return []

        mem = OutcomeMemory(persistence_backend=MixedBackend())
        for i in range(4):
            mem.append(_make_outcome(outcome_id=f"o{i}"))
        assert mem.count == 4
        assert mem.persistence_errors == 2


# ── Section 59: Decay result frozen and to_dict ─────────────────────


class TestDecayResultDetails:
    def test_all_dict_keys(self):
        r = DecayResult(10, 8.5, 0.75, 0.6, 1.5, 0.4)
        d = r.to_dict()
        assert set(d.keys()) == {
            "raw_count",
            "effective_count",
            "weighted_success_rate",
            "weighted_average_score",
            "weighted_average_latency",
            "weighted_average_effort",
        }

    def test_dict_values_rounded(self):
        r = DecayResult(1, 0.123456789, 0.987654321, 0.111111, 0.222222, 0.333333)
        d = r.to_dict()
        assert d["effective_count"] == 0.1235
        assert d["weighted_success_rate"] == 0.9877


# ── Section 60: Learning strength result to_dict ────────────────────


class TestLearningStrengthResultDict:
    def test_all_keys(self):
        r = LearningStrengthResult(0.5, 0.6, 0.15, 0.75, "moderate")
        d = r.to_dict()
        assert set(d.keys()) == {"strength", "confidence", "volatility", "sample_factor", "reason"}

    def test_values_rounded(self):
        r = LearningStrengthResult(0.123456, 0.654321, 0.111111, 0.999999, "test")
        d = r.to_dict()
        assert d["strength"] == 0.1235
        assert d["confidence"] == 0.6543


# ── Section 61: Exploration decision dict ───────────────────────────


class TestExplorationDecisionDict:
    def test_explore_mode_in_dict(self):
        r = select_candidate(["a", "b"], [0.9, 0.3], 0.2, ExplorationPolicy(enabled=True))
        d = r.to_dict()
        assert d["mode"] == "explore"

    def test_confidence_rounded(self):
        r = select_candidate(["a"], [0.5], 0.12345)
        d = r.to_dict()
        assert d["confidence"] == 0.1235


# ── Section 62: FeedbackInfluenceResult dict completeness ───────────


class TestFeedbackInfluenceResultDict:
    def test_all_keys(self):
        r = FeedbackInfluenceResult(1.05, 0.8, "boost", 15, 0.7, True)
        d = r.to_dict()
        assert set(d.keys()) == {
            "factor",
            "confidence",
            "reason",
            "effective_samples",
            "weighted_success_rate",
            "enabled",
        }

    def test_values_rounded(self):
        r = FeedbackInfluenceResult(1.05678, 0.87654, "test", 10, 0.123456, True)
        d = r.to_dict()
        assert d["factor"] == 1.0568
        assert d["weighted_success_rate"] == 0.1235


# ── Section 63: End-to-end pipeline with decay ─────────────────────


class TestEndToEndWithDecay:
    def test_persist_decay_strength_feedback_explore(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend = FileOutcomePersistenceBackend(path)
            mem = OutcomeMemory(persistence_backend=backend)

            now = time.time()
            for i in range(25):
                age = i * 3600
                ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - age))
                mem.append(
                    _make_outcome(
                        outcome_id=f"o{i}",
                        success_score=0.7 + (i % 3) * 0.1,
                        timestamp=ts,
                    )
                )

            outcomes = mem.list_outcomes()
            decay_r = compute_decayed_stats(outcomes, now)
            assert decay_r.raw_count == 25
            assert decay_r.effective_count > 0

            strength_r = compute_learning_strength(outcomes)
            assert strength_r.strength > 0.5

            stats = mem.compute_strategy_stats("aggressive")
            fb = compute_feedback_factor(stats, FeedbackPolicy(enabled=True), strength_r.strength)
            assert 0.90 <= fb.factor <= 1.10

            decision = select_candidate(
                ["agg", "con", "bal"],
                [fb.factor, 0.95, 0.90],
                fb.confidence,
                ExplorationPolicy(enabled=True),
            )
            assert decision.selected_candidate in ["agg", "con", "bal"]
        finally:
            os.unlink(path)

    def test_reload_persisted_outcomes(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            backend1 = FileOutcomePersistenceBackend(path)
            mem1 = OutcomeMemory(persistence_backend=backend1)
            for i in range(10):
                mem1.append(_make_outcome(outcome_id=f"o{i}", success_score=0.8))

            backend2 = FileOutcomePersistenceBackend(path)
            mem2 = OutcomeMemory(persistence_backend=backend2)
            assert mem2.count == 10

            stats2 = mem2.compute_strategy_stats("aggressive")
            assert stats2.total_count == 10
        finally:
            os.unlink(path)
