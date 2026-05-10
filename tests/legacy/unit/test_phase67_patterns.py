"""Phase 67 — Contextual Pattern Recognition Layer v1 tests.

Tests append-only pattern memory, discrete key extraction, similarity
computation, pattern matching, confidence scaling, and observational isolation.
Covers invariants 313-322.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.pattern_memory import (
    PatternKey,
    PatternMemory,
    PatternRecord,
    PatternStats,
    RiskLevel,
    StabilityLevel,
    TrendDirection,
    UrgencyLevel,
    _SUCCESS_THRESHOLD,
    extract_pattern_key,
)
from umh.runtime.pattern_matching import (
    PatternMatch,
    PatternResult,
    _compute_pattern_confidence,
    _compute_similarity,
    match_pattern,
)
from umh.runtime.regime_aggregation import (
    AggregatedRegimeState,
    DimensionName,
    DimensionRegime,
    DirectionCategory,
    NEUTRAL_AGGREGATED,
    aggregate_regimes,
)


def _key(
    trend: TrendDirection = TrendDirection.UP,
    risk: RiskLevel = RiskLevel.LOW,
    stability: StabilityLevel = StabilityLevel.HIGH,
    urgency: UrgencyLevel = UrgencyLevel.LOW,
) -> PatternKey:
    return PatternKey(
        trend_direction=trend,
        risk_level=risk,
        stability_level=stability,
        urgency_level=urgency,
    )


def _record(
    key: PatternKey | None = None,
    score: float = 0.7,
    confidence: float = 0.8,
    ts: int = 1,
) -> PatternRecord:
    return PatternRecord(
        key=key or _key(),
        outcome_score=score,
        confidence=confidence,
        timestamp=ts,
    )


def _memory_with_records(
    keys: list[PatternKey],
    scores: list[float] | None = None,
    count_per_key: int = 10,
) -> PatternMemory:
    mem = PatternMemory()
    sc = scores or [0.7] * len(keys)
    for i, k in enumerate(keys):
        for j in range(count_per_key):
            mem.append(PatternRecord(key=k, outcome_score=sc[i], timestamp=j))
    return mem


# ===========================================================================
# SECTION 1 — PatternKey basics
# ===========================================================================


class TestSection01PatternKey:
    def test_default_key(self):
        k = PatternKey()
        assert k.trend_direction == TrendDirection.NEUTRAL
        assert k.risk_level == RiskLevel.MEDIUM
        assert k.stability_level == StabilityLevel.MEDIUM
        assert k.urgency_level == UrgencyLevel.MEDIUM

    def test_to_tuple(self):
        k = _key()
        t = k.to_tuple()
        assert t == ("up", "low", "high", "low")

    def test_to_dict(self):
        d = _key().to_dict()
        assert set(d.keys()) == {
            "trend_direction",
            "risk_level",
            "stability_level",
            "urgency_level",
        }

    def test_dimensions_property(self):
        k = _key()
        assert k.dimensions == k.to_tuple()

    def test_frozen(self):
        k = _key()
        try:
            k.trend_direction = TrendDirection.DOWN  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===========================================================================
# SECTION 2 — PatternKey equality
# ===========================================================================


class TestSection02KeyEquality:
    def test_same_keys_equal(self):
        a = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        b = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        assert a == b

    def test_different_keys_not_equal(self):
        a = _key(TrendDirection.UP)
        b = _key(TrendDirection.DOWN)
        assert a != b

    def test_tuple_match(self):
        a = _key()
        b = _key()
        assert a.to_tuple() == b.to_tuple()


# ===========================================================================
# SECTION 3 — PatternKey no floats (inv 316)
# ===========================================================================


class TestSection03NoFloats:
    def test_key_values_are_strings(self):
        k = _key()
        for v in k.to_tuple():
            assert isinstance(v, str)

    def test_key_hashable(self):
        k = _key()
        s = {k.to_tuple()}
        assert k.to_tuple() in s


# ===========================================================================
# SECTION 4 — PatternRecord basics
# ===========================================================================


class TestSection04Record:
    def test_default_record(self):
        r = PatternRecord(key=_key())
        assert r.outcome_score == 0.0
        assert r.confidence == 0.0
        assert r.timestamp == 0

    def test_clamped_score_low(self):
        r = PatternRecord(key=_key(), outcome_score=-1.0)
        assert r.outcome_score == 0.0

    def test_clamped_score_high(self):
        r = PatternRecord(key=_key(), outcome_score=2.0)
        assert r.outcome_score == 1.0

    def test_clamped_confidence(self):
        r = PatternRecord(key=_key(), confidence=5.0)
        assert r.confidence == 1.0

    def test_clamped_timestamp(self):
        r = PatternRecord(key=_key(), timestamp=-5)
        assert r.timestamp == 0

    def test_frozen(self):
        r = _record()
        try:
            r.outcome_score = 0.5  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_to_dict(self):
        d = _record().to_dict()
        assert "key" in d
        assert "outcome_score" in d
        assert "confidence" in d
        assert "timestamp" in d


# ===========================================================================
# SECTION 5 — PatternMemory append-only (inv 313)
# ===========================================================================


class TestSection05MemoryAppendOnly:
    def test_empty_memory(self):
        mem = PatternMemory()
        assert mem.size == 0

    def test_append_increases_size(self):
        mem = PatternMemory()
        mem.append(_record())
        assert mem.size == 1

    def test_append_multiple(self):
        mem = PatternMemory()
        for i in range(10):
            mem.append(_record(ts=i))
        assert mem.size == 10

    def test_get_records_returns_tuple(self):
        mem = PatternMemory()
        mem.append(_record())
        records = mem.get_records()
        assert isinstance(records, tuple)

    def test_get_records_immutable(self):
        mem = PatternMemory()
        mem.append(_record())
        records = mem.get_records()
        assert len(records) == 1
        mem.append(_record(ts=2))
        assert len(records) == 1
        assert mem.size == 2


# ===========================================================================
# SECTION 6 — PatternMemory no mutation (inv 314)
# ===========================================================================


class TestSection06NoMutation:
    def test_records_preserved(self):
        mem = PatternMemory()
        r1 = _record(score=0.3, ts=1)
        r2 = _record(score=0.9, ts=2)
        mem.append(r1)
        mem.append(r2)
        records = mem.get_records()
        assert records[0].outcome_score == 0.3
        assert records[1].outcome_score == 0.9

    def test_no_delete_method(self):
        mem = PatternMemory()
        assert not hasattr(mem, "delete")
        assert not hasattr(mem, "remove")
        assert not hasattr(mem, "pop")
        assert not hasattr(mem, "clear")

    def test_frozen_records_immutable(self):
        mem = PatternMemory()
        mem.append(_record())
        r = mem.get_records()[0]
        try:
            r.outcome_score = 0.99  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===========================================================================
# SECTION 7 — PatternMemory get_records_for_key
# ===========================================================================


class TestSection07RecordsForKey:
    def test_exact_key_filter(self):
        k1 = _key(TrendDirection.UP)
        k2 = _key(TrendDirection.DOWN)
        mem = PatternMemory()
        mem.append(_record(key=k1, ts=1))
        mem.append(_record(key=k2, ts=2))
        mem.append(_record(key=k1, ts=3))
        assert len(mem.get_records_for_key(k1)) == 2
        assert len(mem.get_records_for_key(k2)) == 1

    def test_no_match(self):
        mem = PatternMemory()
        mem.append(_record(key=_key(TrendDirection.UP)))
        assert len(mem.get_records_for_key(_key(TrendDirection.DOWN))) == 0


# ===========================================================================
# SECTION 8 — PatternStats computation
# ===========================================================================


class TestSection08Stats:
    def test_empty_stats(self):
        mem = PatternMemory()
        s = mem.compute_stats(_key())
        assert s.count == 0
        assert s.avg_score == 0.0

    def test_basic_stats(self):
        mem = PatternMemory()
        k = _key()
        mem.append(PatternRecord(key=k, outcome_score=0.8))
        mem.append(PatternRecord(key=k, outcome_score=0.6))
        s = mem.compute_stats(k)
        assert s.count == 2
        assert abs(s.avg_score - 0.7) < 0.001

    def test_success_rate(self):
        mem = PatternMemory()
        k = _key()
        mem.append(PatternRecord(key=k, outcome_score=0.8))
        mem.append(PatternRecord(key=k, outcome_score=0.3))
        s = mem.compute_stats(k)
        assert abs(s.success_rate - 0.5) < 0.001

    def test_avg_confidence(self):
        mem = PatternMemory()
        k = _key()
        mem.append(PatternRecord(key=k, confidence=0.9))
        mem.append(PatternRecord(key=k, confidence=0.5))
        s = mem.compute_stats(k)
        assert abs(s.avg_confidence - 0.7) < 0.001

    def test_stats_frozen(self):
        s = PatternStats(key=_key())
        try:
            s.count = 5  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_stats_to_dict(self):
        d = PatternStats(key=_key()).to_dict()
        assert set(d.keys()) == {"key", "count", "avg_score", "success_rate", "avg_confidence"}

    def test_stats_clamped(self):
        s = PatternStats(key=_key(), avg_score=2.0, success_rate=-1.0)
        assert s.avg_score == 1.0
        assert s.success_rate == 0.0


# ===========================================================================
# SECTION 9 — PatternMemory compute_all_stats
# ===========================================================================


class TestSection09AllStats:
    def test_two_keys(self):
        k1 = _key(TrendDirection.UP)
        k2 = _key(TrendDirection.DOWN)
        mem = _memory_with_records([k1, k2], count_per_key=5)
        all_stats = mem.compute_all_stats()
        assert len(all_stats) == 2

    def test_stats_by_tuple_key(self):
        k1 = _key(TrendDirection.UP)
        mem = _memory_with_records([k1], count_per_key=3)
        all_stats = mem.compute_all_stats()
        assert k1.to_tuple() in all_stats

    def test_empty_memory_all_stats(self):
        mem = PatternMemory()
        assert len(mem.compute_all_stats()) == 0


# ===========================================================================
# SECTION 10 — PatternMemory unique_keys
# ===========================================================================


class TestSection10UniqueKeys:
    def test_unique_keys(self):
        k1 = _key(TrendDirection.UP)
        k2 = _key(TrendDirection.DOWN)
        mem = _memory_with_records([k1, k2], count_per_key=3)
        assert len(mem.unique_keys()) == 2

    def test_single_key_repeated(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=100)
        assert len(mem.unique_keys()) == 1


# ===========================================================================
# SECTION 11 — PatternMemory to_dict
# ===========================================================================


class TestSection11MemoryToDict:
    def test_to_dict_keys(self):
        mem = PatternMemory()
        d = mem.to_dict()
        assert set(d.keys()) == {"size", "unique_keys", "records"}

    def test_to_dict_values(self):
        mem = PatternMemory()
        mem.append(_record())
        d = mem.to_dict()
        assert d["size"] == 1
        assert d["unique_keys"] == 1
        assert len(d["records"]) == 1


# ===========================================================================
# SECTION 12 — TrendDirection enum
# ===========================================================================


class TestSection12TrendDirection:
    def test_up(self):
        assert TrendDirection.UP.value == "up"

    def test_down(self):
        assert TrendDirection.DOWN.value == "down"

    def test_neutral(self):
        assert TrendDirection.NEUTRAL.value == "neutral"


# ===========================================================================
# SECTION 13 — RiskLevel enum
# ===========================================================================


class TestSection13RiskLevel:
    def test_low(self):
        assert RiskLevel.LOW.value == "low"

    def test_medium(self):
        assert RiskLevel.MEDIUM.value == "medium"

    def test_high(self):
        assert RiskLevel.HIGH.value == "high"


# ===========================================================================
# SECTION 14 — StabilityLevel enum
# ===========================================================================


class TestSection14StabilityLevel:
    def test_low(self):
        assert StabilityLevel.LOW.value == "low"

    def test_high(self):
        assert StabilityLevel.HIGH.value == "high"


# ===========================================================================
# SECTION 15 — UrgencyLevel enum
# ===========================================================================


class TestSection15UrgencyLevel:
    def test_low(self):
        assert UrgencyLevel.LOW.value == "low"

    def test_high(self):
        assert UrgencyLevel.HIGH.value == "high"


# ===========================================================================
# SECTION 16 — extract_pattern_key from AggregatedRegimeState
# ===========================================================================


class TestSection16ExtractKey:
    def test_none_returns_none(self):
        assert extract_pattern_key(None) is None

    def test_neutral_aggregated(self):
        k = extract_pattern_key(NEUTRAL_AGGREGATED)
        assert k is not None
        assert k.trend_direction == TrendDirection.NEUTRAL

    def test_trend_up(self):
        agg = aggregate_regimes(trend_label="trend_up")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.trend_direction == TrendDirection.UP

    def test_trend_down(self):
        agg = aggregate_regimes(trend_label="trend_down")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.trend_direction == TrendDirection.DOWN

    def test_risk_high(self):
        agg = aggregate_regimes(risk_label="high")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.risk_level == RiskLevel.HIGH

    def test_risk_low(self):
        agg = aggregate_regimes(risk_label="low")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.risk_level == RiskLevel.LOW

    def test_stability_high(self):
        agg = aggregate_regimes(stability_label="high")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.stability_level == StabilityLevel.HIGH

    def test_stability_low(self):
        agg = aggregate_regimes(stability_label="low")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.stability_level == StabilityLevel.LOW

    def test_urgency_high(self):
        agg = aggregate_regimes(urgency_label="high")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.urgency_level == UrgencyLevel.HIGH

    def test_urgency_low(self):
        agg = aggregate_regimes(urgency_label="low")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.urgency_level == UrgencyLevel.LOW

    def test_full_state(self):
        agg = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.trend_direction == TrendDirection.UP
        assert k.risk_level == RiskLevel.HIGH
        assert k.stability_level == StabilityLevel.LOW
        assert k.urgency_level == UrgencyLevel.HIGH

    def test_unknown_label_defaults_medium(self):
        agg = aggregate_regimes(risk_label="unknown_label")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.risk_level == RiskLevel.MEDIUM


# ===========================================================================
# SECTION 17 — _compute_similarity
# ===========================================================================


class TestSection17Similarity:
    def test_exact_match(self):
        a = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        b = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        assert _compute_similarity(a, b) == 1.0

    def test_no_match(self):
        a = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        b = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        assert _compute_similarity(a, b) == 0.0

    def test_three_of_four(self):
        a = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        b = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.HIGH)
        assert _compute_similarity(a, b) == 0.75

    def test_two_of_four(self):
        a = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        b = _key(TrendDirection.UP, RiskLevel.HIGH, StabilityLevel.HIGH, UrgencyLevel.HIGH)
        assert _compute_similarity(a, b) == 0.5

    def test_one_of_four(self):
        a = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        b = _key(TrendDirection.UP, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        assert _compute_similarity(a, b) == 0.25

    def test_bounded_01(self):
        for td in TrendDirection:
            for rl in RiskLevel:
                a = _key(td, rl)
                b = _key()
                sim = _compute_similarity(a, b)
                assert 0.0 <= sim <= 1.0


# ===========================================================================
# SECTION 18 — _compute_pattern_confidence
# ===========================================================================


class TestSection18Confidence:
    def test_zero_samples(self):
        assert _compute_pattern_confidence(0, 10) == 0.0

    def test_below_min(self):
        c = _compute_pattern_confidence(5, 10)
        assert abs(c - 0.5) < 0.001

    def test_at_min(self):
        c = _compute_pattern_confidence(10, 10)
        assert abs(c - 1.0) < 0.001

    def test_above_min_saturates(self):
        c = _compute_pattern_confidence(100, 10)
        assert c == 1.0

    def test_min_zero(self):
        c = _compute_pattern_confidence(5, 0)
        assert c == 1.0

    def test_min_zero_no_samples(self):
        c = _compute_pattern_confidence(0, 0)
        assert c == 0.0


# ===========================================================================
# SECTION 19 — PatternMatch basics
# ===========================================================================


class TestSection19Match:
    def test_default_match(self):
        m = PatternMatch(matched_key=_key())
        assert m.similarity == 0.0
        assert m.sample_size == 0
        assert m.stats is None

    def test_clamped_similarity(self):
        m = PatternMatch(matched_key=_key(), similarity=2.0)
        assert m.similarity == 1.0

    def test_clamped_similarity_low(self):
        m = PatternMatch(matched_key=_key(), similarity=-1.0)
        assert m.similarity == 0.0

    def test_frozen(self):
        m = PatternMatch(matched_key=_key())
        try:
            m.similarity = 0.5  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_to_dict(self):
        d = PatternMatch(matched_key=_key()).to_dict()
        assert set(d.keys()) == {"matched_key", "similarity", "stats", "sample_size"}


# ===========================================================================
# SECTION 20 — PatternResult basics
# ===========================================================================


class TestSection20Result:
    def test_default_result(self):
        r = PatternResult()
        assert r.matched is False
        assert r.best_match is None
        assert r.all_matches == ()
        assert r.confidence == 0.0

    def test_clamped_confidence(self):
        r = PatternResult(confidence=5.0)
        assert r.confidence == 1.0

    def test_frozen(self):
        r = PatternResult()
        try:
            r.matched = True  # type: ignore[misc]
            assert False
        except AttributeError:
            pass

    def test_to_dict_keys(self):
        d = PatternResult().to_dict()
        expected = {
            "matched",
            "best_match",
            "all_matches",
            "query_key",
            "confidence",
            "total_patterns_searched",
            "explanation",
        }
        assert set(d.keys()) == expected

    def test_to_dict_count(self):
        d = PatternResult().to_dict()
        assert len(d) == 7


# ===========================================================================
# SECTION 21 — match_pattern: no query key (inv 317)
# ===========================================================================


class TestSection21NoQueryKey:
    def test_none_key_no_match(self):
        r = match_pattern(query_key=None)
        assert r.matched is False
        assert "no query key" in r.explanation


# ===========================================================================
# SECTION 22 — match_pattern: empty memory
# ===========================================================================


class TestSection22EmptyMemory:
    def test_empty_memory_no_match(self):
        r = match_pattern(query_key=_key(), memory=PatternMemory())
        assert r.matched is False
        assert "no patterns" in r.explanation

    def test_none_memory_no_match(self):
        r = match_pattern(query_key=_key(), memory=None)
        assert r.matched is False


# ===========================================================================
# SECTION 23 — match_pattern: exact match
# ===========================================================================


class TestSection23ExactMatch:
    def test_exact_match_found(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem, min_similarity=0.5)
        assert r.matched is True
        assert r.best_match is not None
        assert r.best_match.similarity == 1.0

    def test_exact_match_stats(self):
        k = _key()
        mem = _memory_with_records([k], scores=[0.8], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        assert r.best_match is not None
        assert r.best_match.stats is not None
        assert abs(r.best_match.stats.avg_score - 0.8) < 0.001

    def test_exact_match_confidence(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=20)
        r = match_pattern(query_key=k, memory=mem, min_samples=10)
        assert r.confidence == 1.0


# ===========================================================================
# SECTION 24 — match_pattern: partial match
# ===========================================================================


class TestSection24PartialMatch:
    def test_three_of_four_match(self):
        k_stored = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k_query = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.HIGH)
        mem = _memory_with_records([k_stored], count_per_key=10)
        r = match_pattern(query_key=k_query, memory=mem, min_similarity=0.5)
        assert r.matched is True
        assert r.best_match is not None
        assert abs(r.best_match.similarity - 0.75) < 0.001

    def test_two_of_four_at_threshold(self):
        k_stored = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k_query = _key(TrendDirection.UP, RiskLevel.HIGH, StabilityLevel.HIGH, UrgencyLevel.HIGH)
        mem = _memory_with_records([k_stored], count_per_key=10)
        r = match_pattern(query_key=k_query, memory=mem, min_similarity=0.5)
        assert r.matched is True
        assert abs(r.best_match.similarity - 0.5) < 0.001

    def test_below_threshold_no_match(self):
        k_stored = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k_query = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        mem = _memory_with_records([k_stored], count_per_key=10)
        r = match_pattern(query_key=k_query, memory=mem, min_similarity=0.5)
        assert r.matched is False


# ===========================================================================
# SECTION 25 — match_pattern: no match
# ===========================================================================


class TestSection25NoMatch:
    def test_completely_different(self):
        k_stored = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k_query = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        mem = _memory_with_records([k_stored], count_per_key=10)
        r = match_pattern(query_key=k_query, memory=mem, min_similarity=0.5)
        assert r.matched is False
        assert r.best_match is None


# ===========================================================================
# SECTION 26 — Similarity bounded [0,1] (inv 318)
# ===========================================================================


class TestSection26SimilarityBounded:
    def test_all_combos_bounded(self):
        for td1 in TrendDirection:
            for td2 in TrendDirection:
                a = _key(trend=td1)
                b = _key(trend=td2)
                sim = _compute_similarity(a, b)
                assert 0.0 <= sim <= 1.0


# ===========================================================================
# SECTION 27 — Determinism (inv 315)
# ===========================================================================


class TestSection27Determinism:
    def test_100_runs_identical(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        results = [match_pattern(query_key=k, memory=mem) for _ in range(100)]
        first = results[0]
        assert all(r.matched == first.matched for r in results)
        assert all(r.confidence == first.confidence for r in results)

    def test_similarity_deterministic(self):
        a = _key(TrendDirection.UP)
        b = _key(TrendDirection.DOWN)
        results = [_compute_similarity(a, b) for _ in range(50)]
        assert all(r == results[0] for r in results)


# ===========================================================================
# SECTION 28 — Low sample → low confidence (inv 322)
# ===========================================================================


class TestSection28LowSampleConfidence:
    def test_1_sample(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=1)
        r = match_pattern(query_key=k, memory=mem, min_samples=10)
        assert r.confidence == 0.1

    def test_5_samples(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=5)
        r = match_pattern(query_key=k, memory=mem, min_samples=10)
        assert abs(r.confidence - 0.5) < 0.001

    def test_10_samples_saturates(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem, min_samples=10)
        assert r.confidence == 1.0


# ===========================================================================
# SECTION 29 — No scoring impact (inv 320)
# ===========================================================================


class TestSection29NoScoringImpact:
    def test_pattern_result_has_no_score_field(self):
        r = PatternResult()
        assert not hasattr(r, "score_adjustment")
        assert not hasattr(r, "scoring_factor")

    def test_match_does_not_modify_scores(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        assert r.matched is True
        assert not hasattr(r, "score")


# ===========================================================================
# SECTION 30 — Explainability (inv 321)
# ===========================================================================


class TestSection30Explainability:
    def test_match_has_explanation(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        assert len(r.explanation) > 0

    def test_explanation_contains_similarity(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        assert "best=" in r.explanation

    def test_explanation_contains_samples(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        assert "samples=" in r.explanation

    def test_explanation_contains_stats(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        assert "avg_score=" in r.explanation


# ===========================================================================
# SECTION 31 — No combinatorial explosion (inv 319)
# ===========================================================================


class TestSection31NoExplosion:
    def test_many_keys_bounded_search(self):
        keys = [
            _key(td, rl, sl, ul)
            for td in TrendDirection
            for rl in RiskLevel
            for sl in [StabilityLevel.HIGH]
            for ul in [UrgencyLevel.LOW]
        ]
        mem = _memory_with_records(keys, count_per_key=2)
        r = match_pattern(query_key=_key(), memory=mem)
        assert r.total_patterns_searched == len(keys)


# ===========================================================================
# SECTION 32 — Multiple matches sorted by similarity
# ===========================================================================


class TestSection32MultipleMatches:
    def test_sorted_by_similarity(self):
        k_exact = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k_partial = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.HIGH)
        mem = _memory_with_records([k_exact, k_partial], count_per_key=10)
        query = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        r = match_pattern(query_key=query, memory=mem, min_similarity=0.5)
        assert r.matched is True
        assert len(r.all_matches) == 2
        assert r.all_matches[0].similarity >= r.all_matches[1].similarity

    def test_best_match_is_first(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.UP, RiskLevel.HIGH, StabilityLevel.HIGH, UrgencyLevel.LOW)
        mem = _memory_with_records([k1, k2], count_per_key=10)
        query = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        r = match_pattern(query_key=query, memory=mem, min_similarity=0.5)
        assert r.best_match is not None
        assert r.best_match.similarity == 1.0


# ===========================================================================
# SECTION 33 — Success threshold
# ===========================================================================


class TestSection33SuccessThreshold:
    def test_above_threshold_is_success(self):
        k = _key()
        mem = PatternMemory()
        mem.append(PatternRecord(key=k, outcome_score=_SUCCESS_THRESHOLD + 0.01))
        s = mem.compute_stats(k)
        assert s.success_rate == 1.0

    def test_below_threshold_not_success(self):
        k = _key()
        mem = PatternMemory()
        mem.append(PatternRecord(key=k, outcome_score=_SUCCESS_THRESHOLD - 0.01))
        s = mem.compute_stats(k)
        assert s.success_rate == 0.0


# ===========================================================================
# SECTION 34 — No circular dependency (inv 307 pattern)
# ===========================================================================


class TestSection34NoCicular:
    def test_pattern_memory_imports(self):
        import inspect

        import umh.runtime.pattern_memory as m

        src = inspect.getsource(m)
        allowed = {"regime_aggregation"}
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"

    def test_pattern_matching_imports(self):
        import inspect

        import umh.runtime.pattern_matching as m

        src = inspect.getsource(m)
        allowed = {"pattern_memory"}
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"


# ===========================================================================
# SECTION 35 — __init__.py exports
# ===========================================================================


class TestSection35Exports:
    def test_pattern_key_exported(self):
        from umh.runtime import PatternKey as PK

        assert PK is PatternKey

    def test_pattern_memory_exported(self):
        from umh.runtime import PatternMemory as PM

        assert PM is PatternMemory

    def test_pattern_record_exported(self):
        from umh.runtime import PatternRecord as PR

        assert PR is PatternRecord

    def test_pattern_stats_exported(self):
        from umh.runtime import PatternStats as PS

        assert PS is PatternStats

    def test_pattern_match_exported(self):
        from umh.runtime import PatternMatch as PMa

        assert PMa is PatternMatch

    def test_pattern_result_exported(self):
        from umh.runtime import PatternResult as PRe

        assert PRe is PatternResult

    def test_match_pattern_exported(self):
        from umh.runtime import match_pattern as mp

        assert mp is match_pattern

    def test_extract_pattern_key_exported(self):
        from umh.runtime import extract_pattern_key as epk

        assert epk is extract_pattern_key

    def test_trend_direction_exported(self):
        from umh.runtime import TrendDirection as TD

        assert TD is TrendDirection


# ===========================================================================
# SECTION 36 — Edge: all defaults
# ===========================================================================


class TestSection36AllDefaults:
    def test_default_key_matches_default_key(self):
        k = PatternKey()
        assert _compute_similarity(k, k) == 1.0

    def test_default_match_result(self):
        r = match_pattern()
        assert r.matched is False


# ===========================================================================
# SECTION 37 — Memory with mixed outcomes
# ===========================================================================


class TestSection37MixedOutcomes:
    def test_mixed_outcomes_stats(self):
        k = _key()
        mem = PatternMemory()
        for i in range(10):
            mem.append(PatternRecord(key=k, outcome_score=i / 10.0))
        s = mem.compute_stats(k)
        assert s.count == 10
        assert 0.4 < s.avg_score < 0.5

    def test_mixed_success_rate(self):
        k = _key()
        mem = PatternMemory()
        for i in range(10):
            mem.append(PatternRecord(key=k, outcome_score=i / 10.0))
        s = mem.compute_stats(k)
        expected_successes = sum(1 for i in range(10) if i / 10.0 >= _SUCCESS_THRESHOLD)
        assert abs(s.success_rate - expected_successes / 10.0) < 0.001


# ===========================================================================
# SECTION 38 — Large memory
# ===========================================================================


class TestSection38LargeMemory:
    def test_1000_records(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=1000)
        assert mem.size == 1000
        s = mem.compute_stats(k)
        assert s.count == 1000

    def test_many_keys_search(self):
        keys = [_key(td) for td in TrendDirection]
        mem = _memory_with_records(keys, count_per_key=100)
        r = match_pattern(query_key=_key(TrendDirection.UP), memory=mem)
        assert r.matched is True
        assert r.best_match is not None
        assert r.best_match.similarity == 1.0


# ===========================================================================
# SECTION 39 — Similarity symmetry
# ===========================================================================


class TestSection39Symmetry:
    def test_symmetric(self):
        a = _key(TrendDirection.UP, RiskLevel.LOW)
        b = _key(TrendDirection.DOWN, RiskLevel.HIGH)
        assert _compute_similarity(a, b) == _compute_similarity(b, a)

    def test_symmetric_partial(self):
        a = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        b = _key(TrendDirection.UP, RiskLevel.HIGH, StabilityLevel.HIGH, UrgencyLevel.HIGH)
        assert _compute_similarity(a, b) == _compute_similarity(b, a)


# ===========================================================================
# SECTION 40 — match_pattern with custom min_similarity
# ===========================================================================


class TestSection40CustomThreshold:
    def test_high_threshold_strict(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.HIGH)
        mem = _memory_with_records([k2], count_per_key=10)
        r = match_pattern(query_key=k1, memory=mem, min_similarity=1.0)
        assert r.matched is False

    def test_low_threshold_permissive(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.UP, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        mem = _memory_with_records([k2], count_per_key=10)
        r = match_pattern(query_key=k1, memory=mem, min_similarity=0.25)
        assert r.matched is True

    def test_zero_threshold_matches_all(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        mem = _memory_with_records([k2], count_per_key=10)
        r = match_pattern(query_key=k1, memory=mem, min_similarity=0.0)
        assert r.matched is True


# ===========================================================================
# SECTION 41 — match_pattern: query_key in result
# ===========================================================================


class TestSection41QueryKeyInResult:
    def test_query_key_returned(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        assert r.query_key == k

    def test_query_key_none_when_none(self):
        r = match_pattern(query_key=None)
        assert r.query_key is None


# ===========================================================================
# SECTION 42 — PatternMatch sample_size
# ===========================================================================


class TestSection42SampleSize:
    def test_sample_size_from_stats(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=15)
        r = match_pattern(query_key=k, memory=mem)
        assert r.best_match is not None
        assert r.best_match.sample_size == 15


# ===========================================================================
# SECTION 43 — All match fields populated
# ===========================================================================


class TestSection43MatchFields:
    def test_all_fields(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        assert r.matched is True
        assert r.best_match is not None
        assert r.best_match.matched_key == k
        assert r.best_match.similarity == 1.0
        assert r.best_match.stats is not None
        assert r.best_match.sample_size == 10
        assert r.confidence > 0.0
        assert r.total_patterns_searched == 1


# ===========================================================================
# SECTION 44 — Direction mapping exhaustive
# ===========================================================================


class TestSection44DirectionMapping:
    def test_spike_up_maps_to_up(self):
        agg = aggregate_regimes(trend_label="spike_up")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.trend_direction == TrendDirection.UP

    def test_spike_down_maps_to_down(self):
        agg = aggregate_regimes(trend_label="spike_down")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.trend_direction == TrendDirection.DOWN

    def test_stable_maps_to_neutral(self):
        agg = aggregate_regimes(trend_label="stable")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.trend_direction == TrendDirection.NEUTRAL


# ===========================================================================
# SECTION 45 — Memory isolation between keys
# ===========================================================================


class TestSection45KeyIsolation:
    def test_stats_independent(self):
        k1 = _key(TrendDirection.UP)
        k2 = _key(TrendDirection.DOWN)
        mem = PatternMemory()
        for _ in range(5):
            mem.append(PatternRecord(key=k1, outcome_score=0.9))
        for _ in range(5):
            mem.append(PatternRecord(key=k2, outcome_score=0.3))
        s1 = mem.compute_stats(k1)
        s2 = mem.compute_stats(k2)
        assert abs(s1.avg_score - 0.9) < 0.001
        assert abs(s2.avg_score - 0.3) < 0.001


# ===========================================================================
# SECTION 46 — Similarity with all identical dimensions
# ===========================================================================


class TestSection46IdenticalDimensions:
    def test_all_values_identical(self):
        k = _key(
            TrendDirection.NEUTRAL, RiskLevel.MEDIUM, StabilityLevel.MEDIUM, UrgencyLevel.MEDIUM
        )
        assert _compute_similarity(k, k) == 1.0


# ===========================================================================
# SECTION 47 — match_pattern: total_patterns_searched
# ===========================================================================


class TestSection47SearchCount:
    def test_count_correct(self):
        keys = [_key(td) for td in TrendDirection]
        mem = _memory_with_records(keys, count_per_key=5)
        r = match_pattern(query_key=_key(), memory=mem, min_similarity=0.0)
        assert r.total_patterns_searched == 3


# ===========================================================================
# SECTION 48 — Memory ordering preserved
# ===========================================================================


class TestSection48Ordering:
    def test_insertion_order_preserved(self):
        mem = PatternMemory()
        for i in range(10):
            mem.append(PatternRecord(key=_key(), outcome_score=i / 10.0, timestamp=i))
        records = mem.get_records()
        assert all(records[i].timestamp == i for i in range(10))


# ===========================================================================
# SECTION 49 — PatternResult to_dict structure
# ===========================================================================


class TestSection49ResultToDict:
    def test_matched_result_to_dict(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        d = r.to_dict()
        assert d["matched"] is True
        assert d["best_match"] is not None
        assert isinstance(d["all_matches"], list)
        assert d["query_key"] is not None

    def test_unmatched_result_to_dict(self):
        r = match_pattern(query_key=None)
        d = r.to_dict()
        assert d["matched"] is False
        assert d["best_match"] is None


# ===========================================================================
# SECTION 50 — Edge: single record in memory
# ===========================================================================


class TestSection50SingleRecord:
    def test_single_record_match(self):
        k = _key()
        mem = PatternMemory()
        mem.append(PatternRecord(key=k, outcome_score=0.8))
        r = match_pattern(query_key=k, memory=mem, min_samples=10)
        assert r.matched is True
        assert r.confidence == 0.1

    def test_single_record_stats(self):
        k = _key()
        mem = PatternMemory()
        mem.append(PatternRecord(key=k, outcome_score=0.8))
        s = mem.compute_stats(k)
        assert s.count == 1
        assert s.avg_score == 0.8


# ===========================================================================
# SECTION 51 — min_similarity edge values
# ===========================================================================


class TestSection51MinSimilarityEdges:
    def test_min_similarity_1_requires_exact(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=5)
        r = match_pattern(query_key=k, memory=mem, min_similarity=1.0)
        assert r.matched is True
        assert r.best_match.similarity == 1.0

    def test_min_similarity_0_matches_everything(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        k2 = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        mem = _memory_with_records([k2], count_per_key=5)
        r = match_pattern(query_key=k1, memory=mem, min_similarity=0.0)
        assert r.matched is True


# ===========================================================================
# SECTION 52 — Confidence scaling linear
# ===========================================================================


class TestSection52ConfidenceScaling:
    def test_linear_scaling(self):
        for n in range(1, 20):
            c = _compute_pattern_confidence(n, 20)
            expected = min(1.0, n / 20.0)
            assert abs(c - expected) < 0.001


# ===========================================================================
# SECTION 53 — Pattern key as dict key
# ===========================================================================


class TestSection53KeyAsDict:
    def test_tuple_as_dict_key(self):
        k1 = _key(TrendDirection.UP)
        k2 = _key(TrendDirection.DOWN)
        d = {k1.to_tuple(): "a", k2.to_tuple(): "b"}
        assert d[k1.to_tuple()] == "a"
        assert d[k2.to_tuple()] == "b"

    def test_frozen_key_hashable(self):
        k = _key()
        s = {k}
        assert k in s


# ===========================================================================
# SECTION 54 — PatternStats: all zeros for empty
# ===========================================================================


class TestSection54EmptyStats:
    def test_all_zeros(self):
        s = PatternStats(key=_key())
        assert s.count == 0
        assert s.avg_score == 0.0
        assert s.success_rate == 0.0
        assert s.avg_confidence == 0.0


# ===========================================================================
# SECTION 55 — match_pattern: all_matches count
# ===========================================================================


class TestSection55AllMatchesCount:
    def test_correct_count(self):
        keys = [
            _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW),
            _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.HIGH),
            _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.LOW, UrgencyLevel.HIGH),
            _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH),
        ]
        mem = _memory_with_records(keys, count_per_key=5)
        query = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.LOW)
        r = match_pattern(query_key=query, memory=mem, min_similarity=0.5)
        assert len(r.all_matches) >= 2


# ===========================================================================
# SECTION 56 — No mutation of memory during match (inv 314)
# ===========================================================================


class TestSection56NoMutationDuringMatch:
    def test_size_unchanged(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        before = mem.size
        match_pattern(query_key=k, memory=mem)
        assert mem.size == before

    def test_records_unchanged(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=5)
        before = mem.get_records()
        match_pattern(query_key=k, memory=mem)
        after = mem.get_records()
        assert before == after


# ===========================================================================
# SECTION 57 — extract_pattern_key with partial aggregation
# ===========================================================================


class TestSection57PartialAggregation:
    def test_only_trend(self):
        agg = aggregate_regimes(trend_label="trend_up")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.trend_direction == TrendDirection.UP
        assert k.risk_level == RiskLevel.MEDIUM

    def test_only_risk(self):
        agg = aggregate_regimes(risk_label="high")
        k = extract_pattern_key(agg)
        assert k is not None
        assert k.risk_level == RiskLevel.HIGH
        assert k.trend_direction == TrendDirection.NEUTRAL


# ===========================================================================
# SECTION 58 — Regression: Phase 59 aggregation unchanged
# ===========================================================================


class TestSection58AggregationRegression:
    def test_aggregate_regimes_unchanged(self):
        agg = aggregate_regimes(
            trend_label="trend_up",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        assert agg.dominant_dimension is not None
        assert agg.alignment_score >= 0.0


# ===========================================================================
# SECTION 59 — Pattern key roundtrip
# ===========================================================================


class TestSection59Roundtrip:
    def test_key_from_tuple(self):
        k = _key(TrendDirection.UP, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        t = k.to_tuple()
        k2 = PatternKey(
            trend_direction=TrendDirection(t[0]),
            risk_level=RiskLevel(t[1]),
            stability_level=StabilityLevel(t[2]),
            urgency_level=UrgencyLevel(t[3]),
        )
        assert k == k2


# ===========================================================================
# SECTION 60 — Pattern match with stats in to_dict
# ===========================================================================


class TestSection60MatchStatsDict:
    def test_stats_in_match_to_dict(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        r = match_pattern(query_key=k, memory=mem)
        d = r.best_match.to_dict()
        assert d["stats"] is not None
        assert "avg_score" in d["stats"]

    def test_no_stats_in_empty(self):
        m = PatternMatch(matched_key=_key())
        d = m.to_dict()
        assert d["stats"] is None


# ===========================================================================
# SECTION 61 — Edge: many keys with same similarity
# ===========================================================================


class TestSection61TiedSimilarity:
    def test_tie_broken_by_key_tuple(self):
        k1 = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH, UrgencyLevel.HIGH)
        k2 = _key(TrendDirection.UP, RiskLevel.HIGH, StabilityLevel.HIGH, UrgencyLevel.LOW)
        mem = _memory_with_records([k1, k2], count_per_key=5)
        query = _key(TrendDirection.UP, RiskLevel.MEDIUM, StabilityLevel.HIGH, UrgencyLevel.MEDIUM)
        r = match_pattern(query_key=query, memory=mem, min_similarity=0.25)
        assert r.matched is True
        assert len(r.all_matches) >= 2


# ===========================================================================
# SECTION 62 — PatternResult with no matches explanation
# ===========================================================================


class TestSection62NoMatchExplanation:
    def test_no_match_explanation(self):
        k_stored = _key(TrendDirection.UP)
        k_query = _key(TrendDirection.DOWN, RiskLevel.HIGH, StabilityLevel.LOW, UrgencyLevel.HIGH)
        mem = _memory_with_records([k_stored], count_per_key=5)
        r = match_pattern(query_key=k_query, memory=mem, min_similarity=0.5)
        assert "no matches" in r.explanation


# ===========================================================================
# SECTION 63 — Memory: high volume different keys
# ===========================================================================


class TestSection63HighVolume:
    def test_27_unique_keys(self):
        keys = []
        for td in TrendDirection:
            for rl in RiskLevel:
                for sl in StabilityLevel:
                    keys.append(_key(td, rl, sl))
        mem = _memory_with_records(keys, count_per_key=2)
        assert len(mem.unique_keys()) == 27

    def test_matching_in_27_keys(self):
        keys = []
        for td in TrendDirection:
            for rl in RiskLevel:
                for sl in StabilityLevel:
                    keys.append(_key(td, rl, sl))
        mem = _memory_with_records(keys, count_per_key=2)
        query = _key(TrendDirection.UP, RiskLevel.LOW, StabilityLevel.HIGH)
        r = match_pattern(query_key=query, memory=mem, min_similarity=0.5)
        assert r.matched is True
        assert r.best_match.similarity == 1.0


# ===========================================================================
# SECTION 64 — match_pattern: min_samples parameter
# ===========================================================================


class TestSection64MinSamplesParam:
    def test_high_min_samples_low_confidence(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=5)
        r = match_pattern(query_key=k, memory=mem, min_samples=100)
        assert r.confidence == 0.05

    def test_low_min_samples_high_confidence(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=5)
        r = match_pattern(query_key=k, memory=mem, min_samples=3)
        assert r.confidence == 1.0


# ===========================================================================
# SECTION 65 — All enum combinations for pattern key
# ===========================================================================


class TestSection65AllEnumCombinations:
    def test_all_trend_directions(self):
        for td in TrendDirection:
            k = _key(trend=td)
            assert k.trend_direction == td

    def test_all_risk_levels(self):
        for rl in RiskLevel:
            k = _key(risk=rl)
            assert k.risk_level == rl

    def test_all_stability_levels(self):
        for sl in StabilityLevel:
            k = _key(stability=sl)
            assert k.stability_level == sl

    def test_all_urgency_levels(self):
        for ul in UrgencyLevel:
            k = _key(urgency=ul)
            assert k.urgency_level == ul


# ===========================================================================
# SECTION 66 — Confidence bounded [0,1]
# ===========================================================================


class TestSection66ConfidenceBounded:
    def test_confidence_never_exceeds_1(self):
        for n in range(0, 50):
            c = _compute_pattern_confidence(n, 10)
            assert 0.0 <= c <= 1.0


# ===========================================================================
# SECTION 67 — Pattern result query_key persists
# ===========================================================================


class TestSection67QueryKeyPersists:
    def test_query_key_in_result(self):
        k = _key(TrendDirection.DOWN, RiskLevel.HIGH)
        r = match_pattern(query_key=k, memory=PatternMemory())
        assert r.query_key is not None
        assert r.query_key.trend_direction == TrendDirection.DOWN
        assert r.query_key.risk_level == RiskLevel.HIGH


# ===========================================================================
# SECTION 68 — Idempotent matching
# ===========================================================================


class TestSection68Idempotent:
    def test_repeated_match_same_result(self):
        k = _key()
        mem = _memory_with_records([k], count_per_key=10)
        results = [match_pattern(query_key=k, memory=mem) for _ in range(10)]
        assert all(r.confidence == results[0].confidence for r in results)
        assert all(r.matched == results[0].matched for r in results)
