"""Phase 35 — Long-Horizon Goal System + Identity Reinforcement v1.

Tests for:
  - GoalRecord (frozen, to_dict, clamping)
  - GoalTypeStats (frozen, to_dict)
  - make_goal_record (defaults, clamping)
  - GoalMemory (append, query, stats, eviction, clear)
  - LongTermGoal (frozen, to_dict, defaults)
  - ReinforcementSignal (frozen, to_dict)
  - GoalBiasInfluence (frozen, to_dict)
  - ReinforcementScorer (formula, bounds, reason)
  - GoalBiasScorer (disabled, neutral, enabled, bounds)
  - Meta-planner integration (SequenceEvaluator, MetaPlanner)
  - Advisor integration (goal_memory property, tick, get_state, clear)
  - Stability (reinforcement convergence, bias stability)
  - Hard invariants 111-115
  - Boundary / exports / compile
"""

from __future__ import annotations

import ast
import importlib
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, "/opt/OS")


# ---------------------------------------------------------------------------
# Section 1: GoalRecord
# ---------------------------------------------------------------------------


class TestGoalRecord:
    def test_creation(self) -> None:
        from umh.runtime.goal_memory import GoalRecord

        r = GoalRecord(
            goal_id="g1",
            goal_type="revenue",
            duration_ticks=10,
            completed=True,
            success_rate=0.8,
            identity_alignment=0.7,
            reward=0.5,
            timestamp="2026-01-01T00:00:00Z",
        )
        assert r.goal_id == "g1"
        assert r.goal_type == "revenue"
        assert r.duration_ticks == 10
        assert r.completed is True
        assert r.success_rate == 0.8
        assert r.identity_alignment == 0.7
        assert r.reward == 0.5

    def test_frozen(self) -> None:
        from umh.runtime.goal_memory import GoalRecord

        r = GoalRecord("g1", "revenue", 10, True, 0.8, 0.7, 0.5, "ts")
        with pytest.raises(FrozenInstanceError):
            r.goal_id = "g2"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.goal_memory import GoalRecord

        r = GoalRecord("g1", "revenue", 10, True, 0.8, 0.7, 0.5, "ts")
        d = r.to_dict()
        assert d["goal_id"] == "g1"
        assert d["goal_type"] == "revenue"
        assert d["completed"] is True
        assert isinstance(d["success_rate"], float)

    def test_to_dict_rounding(self) -> None:
        from umh.runtime.goal_memory import GoalRecord

        r = GoalRecord("g1", "t", 1, False, 0.123456789, 0.987654321, 0.111111111, "ts")
        d = r.to_dict()
        assert d["success_rate"] == round(0.123456789, 4)
        assert d["identity_alignment"] == round(0.987654321, 4)
        assert d["reward"] == round(0.111111111, 4)


# ---------------------------------------------------------------------------
# Section 2: GoalTypeStats
# ---------------------------------------------------------------------------


class TestGoalTypeStats:
    def test_creation(self) -> None:
        from umh.runtime.goal_memory import GoalTypeStats

        s = GoalTypeStats("revenue", 5, 0.8, 12.0, 0.7, 0.6, 0.5)
        assert s.goal_type == "revenue"
        assert s.count == 5
        assert s.completion_rate == 0.8

    def test_frozen(self) -> None:
        from umh.runtime.goal_memory import GoalTypeStats

        s = GoalTypeStats("revenue", 5, 0.8, 12.0, 0.7, 0.6, 0.5)
        with pytest.raises(FrozenInstanceError):
            s.count = 10  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.goal_memory import GoalTypeStats

        s = GoalTypeStats("revenue", 5, 0.8, 12.0, 0.7, 0.6, 0.5)
        d = s.to_dict()
        assert d["goal_type"] == "revenue"
        assert d["count"] == 5
        assert isinstance(d["avg_reward"], float)

    def test_to_dict_rounding(self) -> None:
        from umh.runtime.goal_memory import GoalTypeStats

        s = GoalTypeStats("t", 1, 0.123456789, 1.0, 0.2, 0.3, 0.4)
        d = s.to_dict()
        assert d["completion_rate"] == round(0.123456789, 4)


# ---------------------------------------------------------------------------
# Section 3: make_goal_record
# ---------------------------------------------------------------------------


class TestMakeGoalRecord:
    def test_defaults(self) -> None:
        from umh.runtime.goal_memory import make_goal_record

        r = make_goal_record(goal_id="g1", goal_type="revenue", duration_ticks=5, completed=True)
        assert r.success_rate == 0.0
        assert r.identity_alignment == 0.5
        assert r.reward == 0.0
        assert r.timestamp != ""

    def test_clamping_success_rate(self) -> None:
        from umh.runtime.goal_memory import make_goal_record

        r = make_goal_record(
            goal_id="g1", goal_type="t", duration_ticks=1, completed=True, success_rate=1.5
        )
        assert r.success_rate == 1.0
        r2 = make_goal_record(
            goal_id="g1", goal_type="t", duration_ticks=1, completed=True, success_rate=-0.5
        )
        assert r2.success_rate == 0.0

    def test_clamping_alignment(self) -> None:
        from umh.runtime.goal_memory import make_goal_record

        r = make_goal_record(
            goal_id="g1", goal_type="t", duration_ticks=1, completed=True, identity_alignment=2.0
        )
        assert r.identity_alignment == 1.0

    def test_clamping_reward(self) -> None:
        from umh.runtime.goal_memory import make_goal_record

        r = make_goal_record(
            goal_id="g1", goal_type="t", duration_ticks=1, completed=True, reward=5.0
        )
        assert r.reward == 1.0
        r2 = make_goal_record(
            goal_id="g1", goal_type="t", duration_ticks=1, completed=True, reward=-5.0
        )
        assert r2.reward == -1.0

    def test_negative_duration(self) -> None:
        from umh.runtime.goal_memory import make_goal_record

        r = make_goal_record(goal_id="g1", goal_type="t", duration_ticks=-5, completed=True)
        assert r.duration_ticks == 0

    def test_custom_timestamp(self) -> None:
        from umh.runtime.goal_memory import make_goal_record

        r = make_goal_record(
            goal_id="g1", goal_type="t", duration_ticks=1, completed=True, timestamp="custom-ts"
        )
        assert r.timestamp == "custom-ts"


# ---------------------------------------------------------------------------
# Section 4: GoalMemory basics
# ---------------------------------------------------------------------------


class TestGoalMemoryBasics:
    def test_empty(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        assert m.count == 0
        assert m.get_all() == []
        assert m.get_types() == []

    def test_append(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        r = make_goal_record(goal_id="g1", goal_type="revenue", duration_ticks=5, completed=True)
        m.append(r)
        assert m.count == 1
        assert m.get_all()[0].goal_id == "g1"

    def test_append_multiple(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        for i in range(5):
            m.append(
                make_goal_record(goal_id=f"g{i}", goal_type="t", duration_ticks=1, completed=True)
            )
        assert m.count == 5

    def test_query_by_type(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.append(
            make_goal_record(goal_id="g1", goal_type="revenue", duration_ticks=5, completed=True)
        )
        m.append(
            make_goal_record(goal_id="g2", goal_type="growth", duration_ticks=3, completed=False)
        )
        m.append(
            make_goal_record(goal_id="g3", goal_type="revenue", duration_ticks=7, completed=True)
        )
        rev = m.query_by_type("revenue")
        assert len(rev) == 2
        assert all(r.goal_type == "revenue" for r in rev)

    def test_query_by_type_empty(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        assert m.query_by_type("nonexistent") == []

    def test_query_by_goal_id(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.append(make_goal_record(goal_id="g1", goal_type="t", duration_ticks=5, completed=True))
        m.append(make_goal_record(goal_id="g1", goal_type="t", duration_ticks=3, completed=False))
        m.append(make_goal_record(goal_id="g2", goal_type="t", duration_ticks=7, completed=True))
        results = m.query_by_goal_id("g1")
        assert len(results) == 2

    def test_get_types(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.append(
            make_goal_record(goal_id="g1", goal_type="revenue", duration_ticks=1, completed=True)
        )
        m.append(
            make_goal_record(goal_id="g2", goal_type="growth", duration_ticks=1, completed=True)
        )
        m.append(
            make_goal_record(goal_id="g3", goal_type="revenue", duration_ticks=1, completed=True)
        )
        types = m.get_types()
        assert types == ["growth", "revenue"]

    def test_max_records_clamped(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory(max_records=10)
        assert m.max_records == 50  # clamped to _MIN_MAX_RECORDS

    def test_max_records_clamped_high(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory(max_records=5000)
        assert m.max_records == 2000

    def test_clear(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.append(make_goal_record(goal_id="g1", goal_type="t", duration_ticks=1, completed=True))
        m.clear()
        assert m.count == 0

    def test_to_dict(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.append(make_goal_record(goal_id="g1", goal_type="t", duration_ticks=1, completed=True))
        d = m.to_dict()
        assert d["count"] == 1
        assert "records" in d
        assert "types" in d


# ---------------------------------------------------------------------------
# Section 5: GoalMemory eviction
# ---------------------------------------------------------------------------


class TestGoalMemoryEviction:
    def test_eviction_at_capacity(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory(max_records=50)
        for i in range(60):
            m.append(
                make_goal_record(goal_id=f"g{i}", goal_type="t", duration_ticks=1, completed=True)
            )
        assert m.count == 50
        all_records = m.get_all()
        assert all_records[0].goal_id == "g10"
        assert all_records[-1].goal_id == "g59"

    def test_eviction_preserves_newest(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory(max_records=50)
        for i in range(100):
            m.append(
                make_goal_record(goal_id=f"g{i}", goal_type="t", duration_ticks=1, completed=True)
            )
        assert m.count == 50
        all_records = m.get_all()
        assert all_records[0].goal_id == "g50"

    def test_no_eviction_under_capacity(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory(max_records=50)
        for i in range(30):
            m.append(
                make_goal_record(goal_id=f"g{i}", goal_type="t", duration_ticks=1, completed=True)
            )
        assert m.count == 30


# ---------------------------------------------------------------------------
# Section 6: GoalMemory statistics
# ---------------------------------------------------------------------------


class TestGoalMemoryStats:
    def test_compute_stats_single(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=10,
                completed=True,
                success_rate=0.8,
                identity_alignment=0.7,
                reward=0.5,
            )
        )
        stats = m.compute_stats("revenue")
        assert stats is not None
        assert stats.count == 1
        assert stats.completion_rate == 1.0
        assert stats.avg_success_rate == 0.8

    def test_compute_stats_multiple(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=10,
                completed=True,
                success_rate=0.8,
                identity_alignment=0.6,
                reward=0.5,
            )
        )
        m.append(
            make_goal_record(
                goal_id="g2",
                goal_type="revenue",
                duration_ticks=20,
                completed=False,
                success_rate=0.4,
                identity_alignment=0.8,
                reward=0.2,
            )
        )
        stats = m.compute_stats("revenue")
        assert stats is not None
        assert stats.count == 2
        assert stats.completion_rate == 0.5
        assert abs(stats.avg_success_rate - 0.6) < 0.001
        assert abs(stats.avg_identity_alignment - 0.7) < 0.001
        assert abs(stats.avg_duration - 15.0) < 0.001

    def test_compute_stats_missing_type(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        assert m.compute_stats("nonexistent") is None

    def test_compute_all_stats(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=10,
                completed=True,
                success_rate=0.8,
            )
        )
        m.append(
            make_goal_record(
                goal_id="g2", goal_type="growth", duration_ticks=5, completed=True, success_rate=0.6
            )
        )
        all_stats = m.compute_all_stats()
        assert len(all_stats) == 2
        types = [s.goal_type for s in all_stats]
        assert "revenue" in types
        assert "growth" in types

    def test_compute_all_stats_empty(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        assert m.compute_all_stats() == []


# ---------------------------------------------------------------------------
# Section 7: LongTermGoal
# ---------------------------------------------------------------------------


class TestLongTermGoal:
    def test_creation(self) -> None:
        from umh.runtime.goals import LongTermGoal

        g = LongTermGoal(goal_id="ltg1", goal_type="revenue", description="hit $10k/mo")
        assert g.goal_id == "ltg1"
        assert g.goal_type == "revenue"
        assert g.weight == 1.0

    def test_frozen(self) -> None:
        from umh.runtime.goals import LongTermGoal

        g = LongTermGoal(goal_id="ltg1", goal_type="revenue", description="hit $10k/mo")
        with pytest.raises(FrozenInstanceError):
            g.weight = 2.0  # type: ignore[misc]

    def test_defaults(self) -> None:
        from umh.runtime.goals import LongTermGoal

        g = LongTermGoal(goal_id="ltg1", goal_type="revenue", description="d")
        assert g.persistence_weight == 0.3
        assert g.alignment_weight == 0.4
        assert g.success_weight == 0.3

    def test_to_dict(self) -> None:
        from umh.runtime.goals import LongTermGoal

        g = LongTermGoal(goal_id="ltg1", goal_type="revenue", description="d", weight=1.5)
        d = g.to_dict()
        assert d["goal_id"] == "ltg1"
        assert d["weight"] == 1.5

    def test_custom_weights(self) -> None:
        from umh.runtime.goals import LongTermGoal

        g = LongTermGoal(
            goal_id="ltg1",
            goal_type="revenue",
            description="d",
            persistence_weight=0.5,
            alignment_weight=0.3,
            success_weight=0.2,
        )
        assert g.persistence_weight == 0.5
        assert g.alignment_weight == 0.3
        assert g.success_weight == 0.2


# ---------------------------------------------------------------------------
# Section 8: ReinforcementSignal
# ---------------------------------------------------------------------------


class TestReinforcementSignal:
    def test_creation(self) -> None:
        from umh.runtime.goals import ReinforcementSignal

        s = ReinforcementSignal("revenue", 0.8, 0.9, 0.7, 0.6, 5, "reason")
        assert s.goal_type == "revenue"
        assert s.reinforcement == 0.8

    def test_frozen(self) -> None:
        from umh.runtime.goals import ReinforcementSignal

        s = ReinforcementSignal("revenue", 0.8, 0.9, 0.7, 0.6, 5, "reason")
        with pytest.raises(FrozenInstanceError):
            s.reinforcement = 1.0  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.goals import ReinforcementSignal

        s = ReinforcementSignal("revenue", 0.8, 0.9, 0.7, 0.6, 5, "reason")
        d = s.to_dict()
        assert d["goal_type"] == "revenue"
        assert d["record_count"] == 5

    def test_to_dict_rounding(self) -> None:
        from umh.runtime.goals import ReinforcementSignal

        s = ReinforcementSignal("t", 0.123456789, 0.1, 0.2, 0.3, 1, "r")
        d = s.to_dict()
        assert d["reinforcement"] == round(0.123456789, 4)


# ---------------------------------------------------------------------------
# Section 9: GoalBiasInfluence
# ---------------------------------------------------------------------------


class TestGoalBiasInfluence:
    def test_creation(self) -> None:
        from umh.runtime.goals import GoalBiasInfluence

        b = GoalBiasInfluence(
            factor=1.1, reinforcement_signal=None, goal_type="revenue", reason="r"
        )
        assert b.factor == 1.1
        assert b.goal_type == "revenue"

    def test_frozen(self) -> None:
        from umh.runtime.goals import GoalBiasInfluence

        b = GoalBiasInfluence(factor=1.1, reinforcement_signal=None, goal_type="t", reason="r")
        with pytest.raises(FrozenInstanceError):
            b.factor = 1.0  # type: ignore[misc]

    def test_to_dict_no_signal(self) -> None:
        from umh.runtime.goals import GoalBiasInfluence

        b = GoalBiasInfluence(factor=1.0, reinforcement_signal=None, goal_type="t", reason="r")
        d = b.to_dict()
        assert d["factor"] == 1.0
        assert "reinforcement" not in d

    def test_to_dict_with_signal(self) -> None:
        from umh.runtime.goals import GoalBiasInfluence, ReinforcementSignal

        sig = ReinforcementSignal("t", 0.8, 0.9, 0.7, 0.6, 5, "reason")
        b = GoalBiasInfluence(factor=1.1, reinforcement_signal=sig, goal_type="t", reason="r")
        d = b.to_dict()
        assert "reinforcement" in d
        assert d["reinforcement"]["goal_type"] == "t"


# ---------------------------------------------------------------------------
# Section 10: ReinforcementScorer
# ---------------------------------------------------------------------------


class TestReinforcementScorer:
    def _make_stats(self, **kwargs):
        from umh.runtime.goal_memory import GoalTypeStats

        defaults = {
            "goal_type": "revenue",
            "count": 5,
            "completion_rate": 0.8,
            "avg_duration": 50.0,
            "avg_success_rate": 0.7,
            "avg_identity_alignment": 0.8,
            "avg_reward": 0.5,
        }
        defaults.update(kwargs)
        return GoalTypeStats(**defaults)

    def test_basic_computation(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer(max_duration=100)
        stats = self._make_stats(avg_success_rate=0.8, avg_identity_alignment=0.7, avg_duration=50)
        signal = scorer.compute(stats)
        expected = 0.8 * 0.7 * 0.5  # 0.28, clamped to 0.5
        assert signal.reinforcement == 0.5

    def test_high_all_components(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer(max_duration=100)
        stats = self._make_stats(avg_success_rate=1.0, avg_identity_alignment=1.0, avg_duration=100)
        signal = scorer.compute(stats)
        assert signal.reinforcement == 1.0

    def test_clamped_minimum(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer(max_duration=100)
        stats = self._make_stats(avg_success_rate=0.0, avg_identity_alignment=0.0, avg_duration=0)
        signal = scorer.compute(stats)
        assert signal.reinforcement == 0.5

    def test_duration_factor(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer(max_duration=100)
        stats = self._make_stats(avg_duration=200)
        signal = scorer.compute(stats)
        assert signal.duration_component == 1.0

    def test_components_stored(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer(max_duration=100)
        stats = self._make_stats(avg_success_rate=0.9, avg_identity_alignment=0.8, avg_duration=50)
        signal = scorer.compute(stats)
        assert signal.success_component == 0.9
        assert signal.alignment_component == 0.8
        assert signal.duration_component == 0.5

    def test_reason_strong(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer()
        stats = self._make_stats(avg_success_rate=0.8, count=10)
        signal = scorer.compute(stats)
        assert "strong success" in signal.reason

    def test_reason_weak(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer()
        stats = self._make_stats(avg_success_rate=0.2, count=1)
        signal = scorer.compute(stats)
        assert "weak success" in signal.reason
        assert "limited data" in signal.reason

    def test_reason_emerging(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer()
        stats = self._make_stats(count=3)
        signal = scorer.compute(stats)
        assert "emerging" in signal.reason

    def test_max_duration_clamped(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer(max_duration=0)
        assert scorer.max_duration == 1

    def test_record_count_in_signal(self) -> None:
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer()
        stats = self._make_stats(count=7)
        signal = scorer.compute(stats)
        assert signal.record_count == 7


# ---------------------------------------------------------------------------
# Section 11: GoalBiasScorer
# ---------------------------------------------------------------------------


class TestGoalBiasScorer:
    def test_disabled(self) -> None:
        from umh.runtime.goals import GoalBiasScorer

        scorer = GoalBiasScorer(enabled=False)
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor == 1.0
        assert "disabled" in result.reason

    def test_no_memory(self) -> None:
        from umh.runtime.goals import GoalBiasScorer

        scorer = GoalBiasScorer(goal_memory=None, enabled=True)
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor == 1.0

    def test_no_goal_type(self) -> None:
        from umh.runtime.goal_memory import GoalMemory
        from umh.runtime.goals import GoalBiasScorer

        scorer = GoalBiasScorer(goal_memory=GoalMemory(), enabled=True)
        result = scorer.compute_factor(goal_type="")
        assert result.factor == 1.0
        assert "no goal type" in result.reason

    def test_no_history(self) -> None:
        from umh.runtime.goal_memory import GoalMemory
        from umh.runtime.goals import GoalBiasScorer

        scorer = GoalBiasScorer(goal_memory=GoalMemory(), enabled=True)
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor == 1.0
        assert "no history" in result.reason

    def test_with_history_positive(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=1.0,
                identity_alignment=1.0,
                reward=1.0,
            )
        )
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor > 1.0
        assert result.reinforcement_signal is not None

    def test_with_history_neutral(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=50,
                completed=False,
                success_rate=0.5,
                identity_alignment=0.5,
                reward=0.0,
            )
        )
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert 0.85 <= result.factor <= 1.15

    def test_factor_clamped_min(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=1,
                completed=False,
                success_rate=0.0,
                identity_alignment=0.0,
                reward=-1.0,
            )
        )
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor >= 0.85

    def test_factor_clamped_max(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        for _ in range(10):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=200,
                    completed=True,
                    success_rate=1.0,
                    identity_alignment=1.0,
                    reward=1.0,
                )
            )
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue", goal_weight=5.0)
        assert result.factor <= 1.15

    def test_goal_weight_scales_bias(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=0.9,
                identity_alignment=0.9,
                reward=0.8,
            )
        )
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        low_weight = scorer.compute_factor(goal_type="revenue", goal_weight=0.1)
        high_weight = scorer.compute_factor(goal_type="revenue", goal_weight=2.0)
        assert high_weight.factor >= low_weight.factor

    def test_properties(self) -> None:
        from umh.runtime.goal_memory import GoalMemory
        from umh.runtime.goals import GoalBiasScorer

        mem = GoalMemory()
        scorer = GoalBiasScorer(goal_memory=mem, enabled=True)
        assert scorer.enabled is True
        assert scorer.goal_memory is mem
        assert scorer.reinforcement_scorer is not None

    def test_reason_includes_goal_type(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=50,
                completed=True,
                success_rate=0.8,
                identity_alignment=0.7,
                reward=0.5,
            )
        )
        scorer = GoalBiasScorer(goal_memory=mem, enabled=True)
        result = scorer.compute_factor(goal_type="revenue")
        assert "revenue" in result.reason


# ---------------------------------------------------------------------------
# Section 12: Meta-planner integration
# ---------------------------------------------------------------------------


class TestMetaPlannerIntegration:
    def _make_objective(
        self, oid: str, priority: int = 5, effort: float = 1.0, goal_type: str = ""
    ):
        from umh.runtime.arbitration import Objective

        metadata = {}
        if goal_type:
            metadata["goal_type"] = goal_type
        return Objective(
            objective_id=oid,
            description=f"Objective {oid}",
            priority=priority,
            effort_estimate=effort,
            expected_value=1.0,
            metadata=metadata,
        )

    def test_evaluator_property(self) -> None:
        from umh.runtime.goals import GoalBiasScorer
        from umh.runtime.meta_planner import SequenceEvaluator

        scorer = GoalBiasScorer(enabled=True)
        ev = SequenceEvaluator(goal_bias_scorer=scorer)
        assert ev.goal_bias_scorer is scorer

    def test_evaluator_none_default(self) -> None:
        from umh.runtime.meta_planner import SequenceEvaluator

        ev = SequenceEvaluator()
        assert ev.goal_bias_scorer is None

    def test_score_affected_by_bias(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer
        from umh.runtime.meta_planner import SequenceEvaluator

        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=1.0,
                    identity_alignment=1.0,
                    reward=1.0,
                )
            )
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        ev_with = SequenceEvaluator(goal_bias_scorer=scorer)
        ev_without = SequenceEvaluator()

        objs = [self._make_objective("o1", goal_type="revenue")]
        score_with = ev_with.score_sequence(objs, label="with")
        score_without = ev_without.score_sequence(objs, label="without")
        assert score_with.total_score != score_without.total_score

    def test_no_bias_when_disabled(self) -> None:
        from umh.runtime.goals import GoalBiasScorer
        from umh.runtime.meta_planner import SequenceEvaluator

        scorer = GoalBiasScorer(enabled=False)
        ev_with = SequenceEvaluator(goal_bias_scorer=scorer)
        ev_without = SequenceEvaluator()

        objs = [self._make_objective("o1")]
        score_with = ev_with.score_sequence(objs, label="with")
        score_without = ev_without.score_sequence(objs, label="without")
        assert abs(score_with.total_score - score_without.total_score) < 0.0001

    def test_planner_property(self) -> None:
        from umh.runtime.goals import GoalBiasScorer
        from umh.runtime.meta_planner import MetaPlanner

        scorer = GoalBiasScorer(enabled=True)
        planner = MetaPlanner(goal_bias_scorer=scorer)
        assert planner.goal_bias_scorer is scorer

    def test_planner_none_default(self) -> None:
        from umh.runtime.meta_planner import MetaPlanner

        planner = MetaPlanner()
        assert planner.goal_bias_scorer is None

    def test_reason_includes_goal_bias(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer
        from umh.runtime.meta_planner import MetaPlanner, SequenceEvaluator

        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=1.0,
                    identity_alignment=1.0,
                    reward=1.0,
                )
            )
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        ev = SequenceEvaluator(goal_bias_scorer=scorer)
        planner = MetaPlanner(sequence_evaluator=ev, goal_bias_scorer=scorer)
        objs = [
            self._make_objective("o1", priority=8, goal_type="revenue"),
            self._make_objective("o2", priority=6, goal_type="revenue"),
            self._make_objective("o3", priority=4, goal_type="revenue"),
        ]
        result = planner.plan(objs)
        assert result is not None
        assert "goal bias" in result.reason


# ---------------------------------------------------------------------------
# Section 13: Advisor integration
# ---------------------------------------------------------------------------


class TestAdvisorIntegration:
    def test_goal_memory_property(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.goal_memory import GoalMemory

        mem = GoalMemory()
        advisor = AdvisorRuntime(goal_memory=mem)
        assert advisor.goal_memory is mem

    def test_goal_memory_none_default(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        assert advisor.goal_memory is None

    def test_goal_bias_scorer_property(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.goals import GoalBiasScorer

        scorer = GoalBiasScorer()
        advisor = AdvisorRuntime(goal_bias_scorer=scorer)
        assert advisor.goal_bias_scorer is scorer

    def test_tick_key_present(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert "goal_memory_recorded" in result
        advisor.stop()

    def test_get_state_with_memory(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.goal_memory import GoalMemory

        mem = GoalMemory()
        advisor = AdvisorRuntime(goal_memory=mem)
        state = advisor.get_state()
        assert "goal_memory_count" in state
        assert state["goal_memory_count"] == 0

    def test_clear_clears_memory(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        mem = GoalMemory()
        mem.append(make_goal_record(goal_id="g1", goal_type="t", duration_ticks=1, completed=True))
        advisor = AdvisorRuntime(goal_memory=mem)
        assert mem.count == 1
        advisor.clear()
        assert mem.count == 0

    def test_no_memory_no_crash(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert result["goal_memory_recorded"] is False
        advisor.stop()


# ---------------------------------------------------------------------------
# Section 14: End-to-end pipeline
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def _make_objective(self, oid: str, priority: int = 5, goal_type: str = ""):
        from umh.runtime.arbitration import Objective

        metadata = {}
        if goal_type:
            metadata["goal_type"] = goal_type
        return Objective(
            objective_id=oid,
            description=f"Objective {oid}",
            priority=priority,
            effort_estimate=1.0,
            expected_value=1.0,
            metadata=metadata,
        )

    def test_e2e_goal_memory_to_bias(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        for i in range(10):
            mem.append(
                make_goal_record(
                    goal_id=f"g{i}",
                    goal_type="revenue",
                    duration_ticks=50 + i * 5,
                    completed=i % 2 == 0,
                    success_rate=0.5 + i * 0.05,
                    identity_alignment=0.6 + i * 0.03,
                    reward=0.3 + i * 0.07,
                )
            )

        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert 0.85 <= result.factor <= 1.15
        assert result.reinforcement_signal is not None
        assert result.reinforcement_signal.record_count == 10

    def test_e2e_scoring_chain(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer
        from umh.runtime.identity import IdentityScorer, IdentityStore
        from umh.runtime.meta_planner import SequenceEvaluator

        id_store = IdentityStore()
        id_scorer = IdentityScorer(identity_store=id_store, enabled=True)

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=0.9,
                identity_alignment=0.8,
                reward=0.7,
            )
        )
        goal_scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )

        ev = SequenceEvaluator(identity_scorer=id_scorer, goal_bias_scorer=goal_scorer)
        objs = [self._make_objective("o1", priority=7, goal_type="revenue")]
        result = ev.score_sequence(objs, label="test")
        assert result.total_score > 0

    def test_e2e_multiple_types(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=1.0,
                    identity_alignment=1.0,
                    reward=1.0,
                )
            )
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g2",
                    goal_type="growth",
                    duration_ticks=10,
                    completed=False,
                    success_rate=0.1,
                    identity_alignment=0.2,
                    reward=-0.5,
                )
            )

        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        rev = scorer.compute_factor(goal_type="revenue")
        growth = scorer.compute_factor(goal_type="growth")
        assert rev.factor > growth.factor


# ---------------------------------------------------------------------------
# Section 15: Stability
# ---------------------------------------------------------------------------


class TestStability:
    def test_reinforcement_converges(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        factors: list[float] = []
        for i in range(20):
            mem.append(
                make_goal_record(
                    goal_id=f"g{i}",
                    goal_type="revenue",
                    duration_ticks=50,
                    completed=True,
                    success_rate=0.7,
                    identity_alignment=0.7,
                    reward=0.5,
                )
            )
            result = scorer.compute_factor(goal_type="revenue")
            factors.append(result.factor)

        # Factor should stabilize (all same since consistent signals)
        for f in factors:
            assert abs(f - factors[-1]) < 0.01

    def test_bias_stability_under_mixed_signals(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        for i in range(20):
            success = 1.0 if i % 2 == 0 else 0.0
            mem.append(
                make_goal_record(
                    goal_id=f"g{i}",
                    goal_type="revenue",
                    duration_ticks=50,
                    completed=i % 2 == 0,
                    success_rate=success,
                    identity_alignment=0.5,
                    reward=success * 0.5,
                )
            )
        result = scorer.compute_factor(goal_type="revenue")
        assert 0.85 <= result.factor <= 1.15

    def test_different_types_independent(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        for _ in range(10):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=1.0,
                    identity_alignment=1.0,
                    reward=1.0,
                )
            )
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        rev = scorer.compute_factor(goal_type="revenue")
        growth = scorer.compute_factor(goal_type="growth")
        assert rev.factor > 1.0
        assert growth.factor == 1.0

    def test_scorer_deterministic(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=80,
                completed=True,
                success_rate=0.85,
                identity_alignment=0.9,
                reward=0.7,
            )
        )
        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        r1 = scorer.compute_factor(goal_type="revenue")
        r2 = scorer.compute_factor(goal_type="revenue")
        assert r1.factor == r2.factor


# ---------------------------------------------------------------------------
# Section 16: Hard Invariants 111-115
# ---------------------------------------------------------------------------


class TestHardInvariants:
    def test_inv111_append_only_memory(self) -> None:
        """INV 111: Goal memory must be append-only (no mutation of existing records)."""
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        mem = GoalMemory()
        r1 = make_goal_record(
            goal_id="g1", goal_type="t", duration_ticks=5, completed=True, success_rate=0.8
        )
        mem.append(r1)
        r2 = make_goal_record(
            goal_id="g2", goal_type="t", duration_ticks=3, completed=False, success_rate=0.3
        )
        mem.append(r2)

        all_records = mem.get_all()
        assert len(all_records) == 2
        assert all_records[0].goal_id == "g1"
        assert all_records[0].success_rate == 0.8
        assert all_records[1].goal_id == "g2"

    def test_inv111_records_immutable(self) -> None:
        """INV 111: Individual records are frozen and cannot be mutated."""
        from umh.runtime.goal_memory import make_goal_record

        r = make_goal_record(goal_id="g1", goal_type="t", duration_ticks=5, completed=True)
        with pytest.raises(FrozenInstanceError):
            r.success_rate = 0.99  # type: ignore[misc]

    def test_inv112_no_mutation_of_past_records(self) -> None:
        """INV 112: Adding new records must not alter existing records."""
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        mem = GoalMemory()
        r1 = make_goal_record(
            goal_id="g1", goal_type="t", duration_ticks=5, completed=True, success_rate=0.8
        )
        mem.append(r1)

        snapshot_before = mem.get_all()[0]

        for i in range(10):
            mem.append(
                make_goal_record(
                    goal_id=f"g{i + 2}", goal_type="t", duration_ticks=i, completed=False
                )
            )

        all_records = mem.get_all()
        first = all_records[0]
        assert first.goal_id == snapshot_before.goal_id
        assert first.success_rate == snapshot_before.success_rate
        assert first.completed == snapshot_before.completed

    def test_inv113_no_override_of_planning(self) -> None:
        """INV 113: Goal bias must NOT override planning — factor in [0.85, 1.15]."""
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        for _ in range(20):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=200,
                    completed=True,
                    success_rate=1.0,
                    identity_alignment=1.0,
                    reward=1.0,
                )
            )

        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue", goal_weight=10.0)
        assert 0.85 <= result.factor <= 1.15

    def test_inv113_extreme_low(self) -> None:
        """INV 113: Even with terrible history, factor stays >= 0.85."""
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer

        mem = GoalMemory()
        for _ in range(20):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=1,
                    completed=False,
                    success_rate=0.0,
                    identity_alignment=0.0,
                    reward=-1.0,
                )
            )

        scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue", goal_weight=10.0)
        assert result.factor >= 0.85

    def test_inv114_bounded_reinforcement(self) -> None:
        """INV 114: Reinforcement signal must be bounded [0.5, 1.5]."""
        from umh.runtime.goal_memory import GoalTypeStats
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer(max_duration=100)

        extreme_high = GoalTypeStats("t", 10, 1.0, 200.0, 1.0, 1.0, 1.0)
        sig = scorer.compute(extreme_high)
        assert 0.5 <= sig.reinforcement <= 1.5

        extreme_low = GoalTypeStats("t", 10, 0.0, 0.0, 0.0, 0.0, -1.0)
        sig2 = scorer.compute(extreme_low)
        assert 0.5 <= sig2.reinforcement <= 1.5

    def test_inv114_bounded_reinforcement_varied(self) -> None:
        """INV 114: Various reinforcement scenarios all stay bounded."""
        from umh.runtime.goal_memory import GoalTypeStats
        from umh.runtime.goals import ReinforcementScorer

        scorer = ReinforcementScorer(max_duration=50)
        test_cases = [
            GoalTypeStats("t", 1, 0.0, 0.0, 0.0, 0.0, 0.0),
            GoalTypeStats("t", 100, 1.0, 1000.0, 1.0, 1.0, 1.0),
            GoalTypeStats("t", 5, 0.5, 25.0, 0.5, 0.5, 0.0),
            GoalTypeStats("t", 3, 0.0, 5.0, 0.1, 0.1, -0.5),
        ]
        for stats in test_cases:
            sig = scorer.compute(stats)
            assert 0.5 <= sig.reinforcement <= 1.5, f"Failed for {stats}"

    def test_inv115_no_execution_state_mutation(self) -> None:
        """INV 115: goals.py must not import from umh/cells, umh/environments, umh/adapters."""
        source_path = "/opt/OS/umh/runtime/goals.py"
        with open(source_path) as f:
            tree = ast.parse(f.read())

        forbidden = {"umh.cells", "umh.environments", "umh.adapters", "subprocess"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for fb in forbidden:
                        assert not node.module.startswith(fb), f"Forbidden import: {node.module}"
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        for fb in forbidden:
                            assert not alias.name.startswith(fb), f"Forbidden import: {alias.name}"

    def test_inv115_goal_memory_no_execution_state(self) -> None:
        """INV 115: goal_memory.py must not import from umh/cells, umh/environments, umh/adapters."""
        source_path = "/opt/OS/umh/runtime/goal_memory.py"
        with open(source_path) as f:
            tree = ast.parse(f.read())

        forbidden = {"umh.cells", "umh.environments", "umh.adapters", "subprocess"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for fb in forbidden:
                        assert not node.module.startswith(fb), f"Forbidden import: {node.module}"
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        for fb in forbidden:
                            assert not alias.name.startswith(fb), f"Forbidden import: {alias.name}"


# ---------------------------------------------------------------------------
# Section 17: Boundary / Exports / Compile
# ---------------------------------------------------------------------------


class TestBoundaryExports:
    def test_import_goal_memory(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, GoalRecord, GoalTypeStats, make_goal_record

        assert GoalMemory is not None
        assert GoalRecord is not None
        assert GoalTypeStats is not None
        assert make_goal_record is not None

    def test_import_goals(self) -> None:
        from umh.runtime.goals import (
            GoalBiasInfluence,
            GoalBiasScorer,
            LongTermGoal,
            ReinforcementScorer,
            ReinforcementSignal,
        )

        assert GoalBiasInfluence is not None
        assert GoalBiasScorer is not None
        assert LongTermGoal is not None
        assert ReinforcementScorer is not None
        assert ReinforcementSignal is not None

    def test_compile_goal_memory(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/goal_memory.py", doraise=True)

    def test_compile_goals(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/goals.py", doraise=True)

    def test_compile_meta_planner(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/meta_planner.py", doraise=True)

    def test_compile_advisor(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/advisor.py", doraise=True)

    def test_compile_init(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_runtime_exports_goal_memory(self) -> None:
        from umh.runtime import GoalMemory, GoalRecord, GoalTypeStats, make_goal_record

        assert GoalMemory is not None

    def test_runtime_exports_goals(self) -> None:
        from umh.runtime import (
            GoalBiasInfluence,
            GoalBiasScorer,
            LongTermGoal,
            ReinforcementScorer,
            ReinforcementSignal,
        )

        assert GoalBiasScorer is not None

    def test_all_exports_present(self) -> None:
        import umh.runtime as rt

        expected = [
            "GoalMemory",
            "GoalRecord",
            "GoalTypeStats",
            "make_goal_record",
            "GoalBiasInfluence",
            "GoalBiasScorer",
            "LongTermGoal",
            "ReinforcementScorer",
            "ReinforcementSignal",
        ]
        for name in expected:
            assert name in rt.__all__, f"{name} not in __all__"

    def test_get_all_returns_copy(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        mem = GoalMemory()
        mem.append(make_goal_record(goal_id="g1", goal_type="t", duration_ticks=1, completed=True))
        copy1 = mem.get_all()
        copy2 = mem.get_all()
        assert copy1 is not copy2
        assert copy1 == copy2

    def test_reinforcement_signal_to_dict(self) -> None:
        from umh.runtime.goals import ReinforcementSignal

        s = ReinforcementSignal("revenue", 0.7, 0.8, 0.9, 0.5, 3, "reason")
        d = s.to_dict()
        assert "reinforcement" in d
        assert "success_component" in d

    def test_goal_bias_influence_to_dict(self) -> None:
        from umh.runtime.goals import GoalBiasInfluence

        b = GoalBiasInfluence(
            factor=1.05, reinforcement_signal=None, goal_type="revenue", reason="r"
        )
        d = b.to_dict()
        assert d["factor"] == 1.05
        assert d["goal_type"] == "revenue"

    def test_long_term_goal_to_dict(self) -> None:
        from umh.runtime.goals import LongTermGoal

        g = LongTermGoal(goal_id="ltg1", goal_type="revenue", description="goal")
        d = g.to_dict()
        assert d["goal_id"] == "ltg1"
        assert "persistence_weight" in d

    def test_goal_type_stats_to_dict(self) -> None:
        from umh.runtime.goal_memory import GoalTypeStats

        s = GoalTypeStats("revenue", 5, 0.8, 10.0, 0.7, 0.6, 0.5)
        d = s.to_dict()
        assert d["count"] == 5
        assert "avg_reward" in d
