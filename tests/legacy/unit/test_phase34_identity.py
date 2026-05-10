"""Phase 34 — Identity Layer + Preference Formation v1.

Tests: TraitSnapshot, IdentityProfile, IdentityInfluence, BehaviorSignals,
SignalExtractor, IdentityStore, IdentityScorer, meta-planner integration,
advisor integration, hard invariants 106-110, boundary checks.

Target: 100-140 tests.
"""

from __future__ import annotations

import ast
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.arbitration import Objective, ObjectiveEvaluator
from umh.runtime.identity import (
    BehaviorSignals,
    IdentityInfluence,
    IdentityProfile,
    IdentityScorer,
    IdentityStore,
    SignalExtractor,
    TraitSnapshot,
    _DEFAULT_LEARNING_RATE,
    _DEFAULT_TRAIT_VALUE,
    _MAX_DELTA_PER_UPDATE,
    _MAX_IDENTITY_FACTOR,
    _MAX_TRAIT_VALUE,
    _MIN_IDENTITY_FACTOR,
    _MIN_TRAIT_VALUE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _obj(
    oid: str = "obj-1",
    priority: int = 5,
    effort: float = 1.0,
    value: float = 1.0,
) -> Objective:
    return Objective(
        objective_id=oid,
        description=f"Test objective {oid}",
        priority=priority,
        effort_estimate=effort,
        expected_value=value,
    )


def _store(**kw) -> IdentityStore:
    return IdentityStore(**kw)


def _scorer(store: IdentityStore | None = None, enabled: bool = True) -> IdentityScorer:
    return IdentityScorer(identity_store=store, enabled=enabled)


# ===========================================================================
# SECTION 1: TraitSnapshot
# ===========================================================================


class TestTraitSnapshot:
    def test_creation(self):
        ts = TraitSnapshot(trait_name="persistence", value=0.7, confidence=0.3, timestamp="t1")
        assert ts.trait_name == "persistence"
        assert ts.value == pytest.approx(0.7)
        assert ts.confidence == pytest.approx(0.3)
        assert ts.timestamp == "t1"

    def test_frozen(self):
        ts = TraitSnapshot(trait_name="x", value=0.5, confidence=0.1, timestamp="t")
        with pytest.raises(AttributeError):
            ts.value = 0.9  # type: ignore[misc]

    def test_to_dict(self):
        ts = TraitSnapshot(trait_name="a", value=0.33333, confidence=0.11111, timestamp="t")
        d = ts.to_dict()
        assert d["trait_name"] == "a"
        assert d["value"] == round(0.33333, 4)
        assert d["confidence"] == round(0.11111, 4)
        assert d["timestamp"] == "t"


# ===========================================================================
# SECTION 2: IdentityProfile
# ===========================================================================


class TestIdentityProfile:
    def test_creation(self):
        p = IdentityProfile(
            traits={"a": 0.6},
            preferences={"b": 0.7},
            confidence={"a": 0.3},
            update_count=5,
        )
        assert p.traits["a"] == pytest.approx(0.6)
        assert p.preferences["b"] == pytest.approx(0.7)
        assert p.update_count == 5

    def test_frozen(self):
        p = IdentityProfile(traits={}, preferences={}, confidence={}, update_count=0)
        with pytest.raises(AttributeError):
            p.update_count = 10  # type: ignore[misc]

    def test_to_dict(self):
        p = IdentityProfile(
            traits={"b": 0.5, "a": 0.6},
            preferences={"x": 0.9},
            confidence={"a": 0.3},
            update_count=2,
        )
        d = p.to_dict()
        keys = list(d["traits"].keys())
        assert keys == sorted(keys)
        assert d["update_count"] == 2

    def test_empty(self):
        p = IdentityProfile(traits={}, preferences={}, confidence={}, update_count=0)
        assert p.to_dict()["traits"] == {}


# ===========================================================================
# SECTION 3: IdentityInfluence
# ===========================================================================


class TestIdentityInfluence:
    def test_creation(self):
        ii = IdentityInfluence(
            factor=1.05,
            trait_contributions={"persistence": 0.03},
            reason="test",
        )
        assert ii.factor == pytest.approx(1.05)
        assert "persistence" in ii.trait_contributions

    def test_frozen(self):
        ii = IdentityInfluence(factor=1.0, trait_contributions={}, reason="x")
        with pytest.raises(AttributeError):
            ii.factor = 0.9  # type: ignore[misc]

    def test_to_dict(self):
        ii = IdentityInfluence(
            factor=1.123456,
            trait_contributions={"a": 0.05555},
            reason="r",
        )
        d = ii.to_dict()
        assert d["factor"] == round(1.123456, 4)
        assert d["trait_contributions"]["a"] == round(0.05555, 4)

    def test_neutral(self):
        ii = IdentityInfluence(factor=1.0, trait_contributions={}, reason="neutral")
        assert ii.factor == pytest.approx(1.0)


# ===========================================================================
# SECTION 4: BehaviorSignals
# ===========================================================================


class TestBehaviorSignals:
    def test_creation(self):
        bs = BehaviorSignals(
            completion_rate=0.8,
            switch_frequency=0.1,
            success_rate=0.7,
            avg_sequence_length=2.5,
        )
        assert bs.completion_rate == pytest.approx(0.8)
        assert bs.switch_frequency == pytest.approx(0.1)

    def test_defaults(self):
        bs = BehaviorSignals()
        assert bs.completion_rate == pytest.approx(0.5)
        assert bs.switch_frequency == pytest.approx(0.0)
        assert bs.success_rate == pytest.approx(0.5)
        assert bs.avg_sequence_length == pytest.approx(1.0)

    def test_clamped(self):
        bs = BehaviorSignals(completion_rate=2.0, switch_frequency=-1.0)
        assert bs.completion_rate == pytest.approx(1.0)
        assert bs.switch_frequency == pytest.approx(0.0)

    def test_frozen(self):
        bs = BehaviorSignals()
        with pytest.raises(AttributeError):
            bs.completion_rate = 0.9  # type: ignore[misc]

    def test_to_dict(self):
        bs = BehaviorSignals(completion_rate=0.333)
        d = bs.to_dict()
        assert d["completion_rate"] == round(0.333, 4)


# ===========================================================================
# SECTION 5: SignalExtractor
# ===========================================================================


class TestSignalExtractor:
    def test_default_signals(self):
        ext = SignalExtractor()
        sig = ext.extract()
        assert sig.completion_rate == pytest.approx(0.5)
        assert sig.switch_frequency == pytest.approx(0.0)

    def test_with_data(self):
        ext = SignalExtractor()
        sig = ext.extract(
            total_ticks=100,
            goals_completed=8,
            goals_attempted=10,
            switches=5,
            total_sequence_steps=30,
            sequences_evaluated=10,
        )
        assert sig.completion_rate == pytest.approx(0.8)
        assert sig.switch_frequency == pytest.approx(0.05)
        assert sig.success_rate == pytest.approx(0.8)
        assert sig.avg_sequence_length == pytest.approx(3.0)

    def test_zero_ticks(self):
        ext = SignalExtractor()
        sig = ext.extract(total_ticks=0)
        assert sig.switch_frequency == pytest.approx(0.0)

    def test_zero_attempted(self):
        ext = SignalExtractor()
        sig = ext.extract(goals_attempted=0)
        assert sig.completion_rate == pytest.approx(0.5)
        assert sig.success_rate == pytest.approx(0.5)


# ===========================================================================
# SECTION 6: IdentityStore — basics
# ===========================================================================


class TestIdentityStoreBasics:
    def test_empty(self):
        s = _store()
        assert s.trait_count == 0
        assert s.update_count == 0
        assert s.history_count == 0

    def test_get_trait_default(self):
        s = _store()
        assert s.get_trait("anything") == pytest.approx(_DEFAULT_TRAIT_VALUE)

    def test_get_confidence_default(self):
        s = _store()
        assert s.get_confidence("anything") == pytest.approx(0.0)

    def test_get_preference_default(self):
        s = _store()
        assert s.get_preference("anything") == pytest.approx(_DEFAULT_TRAIT_VALUE)

    def test_set_preference(self):
        s = _store()
        s.set_preference("speed", 0.8)
        assert s.get_preference("speed") == pytest.approx(0.8)

    def test_set_preference_clamped(self):
        s = _store()
        s.set_preference("x", 5.0)
        assert s.get_preference("x") == pytest.approx(1.0)
        s.set_preference("y", -1.0)
        assert s.get_preference("y") == pytest.approx(0.0)

    def test_learning_rate_property(self):
        s = _store(learning_rate=0.1)
        assert s.learning_rate == pytest.approx(0.1)

    def test_learning_rate_clamped(self):
        s = _store(learning_rate=5.0)
        assert s.learning_rate == pytest.approx(0.20)
        s2 = _store(learning_rate=0.001)
        assert s2.learning_rate == pytest.approx(0.01)

    def test_max_delta_property(self):
        s = _store(max_delta=0.1)
        assert s.max_delta == pytest.approx(0.1)


# ===========================================================================
# SECTION 7: IdentityStore — update_trait
# ===========================================================================


class TestIdentityStoreUpdateTrait:
    def test_first_update(self):
        s = _store()
        snap = s.update_trait("persistence", 0.8)
        assert snap.trait_name == "persistence"
        assert s.trait_count == 1
        assert s.update_count == 1
        assert s.history_count == 1

    def test_ema_moves_toward_signal(self):
        s = _store(learning_rate=0.1)
        s.update_trait("p", 1.0)
        val = s.get_trait("p")
        assert val > _DEFAULT_TRAIT_VALUE
        assert val < 1.0

    def test_bounded_delta(self):
        s = _store(learning_rate=1.0, max_delta=0.05)
        s.update_trait("p", 1.0)
        val = s.get_trait("p")
        assert val <= _DEFAULT_TRAIT_VALUE + 0.05 + 1e-9

    def test_multiple_updates_converge(self):
        s = _store(learning_rate=0.1)
        for _ in range(100):
            s.update_trait("p", 0.9)
        assert s.get_trait("p") == pytest.approx(0.9, abs=0.05)

    def test_value_clamped_to_range(self):
        s = _store(learning_rate=0.2)
        for _ in range(50):
            s.update_trait("p", 1.5)
        assert s.get_trait("p") <= _MAX_TRAIT_VALUE

        s2 = _store(learning_rate=0.2)
        for _ in range(50):
            s2.update_trait("p", -0.5)
        assert s2.get_trait("p") >= _MIN_TRAIT_VALUE

    def test_confidence_grows(self):
        s = _store()
        s.update_trait("p", 0.7)
        c1 = s.get_confidence("p")
        s.update_trait("p", 0.7)
        c2 = s.get_confidence("p")
        assert c2 > c1

    def test_confidence_approaches_one(self):
        s = _store()
        for _ in range(100):
            s.update_trait("p", 0.7)
        assert s.get_confidence("p") > 0.95

    def test_history_appended(self):
        s = _store()
        s.update_trait("a", 0.6)
        s.update_trait("b", 0.7)
        s.update_trait("a", 0.8)
        assert s.history_count == 3
        h = s.get_history()
        assert h[0].trait_name == "a"
        assert h[1].trait_name == "b"
        assert h[2].trait_name == "a"

    def test_custom_timestamp(self):
        s = _store()
        snap = s.update_trait("p", 0.7, timestamp="2026-01-01")
        assert snap.timestamp == "2026-01-01"


# ===========================================================================
# SECTION 8: IdentityStore — update_from_signals
# ===========================================================================


class TestIdentityStoreSignals:
    def test_updates_all_mapped_traits(self):
        s = _store()
        signals = BehaviorSignals(
            completion_rate=0.9,
            switch_frequency=0.1,
            success_rate=0.8,
            avg_sequence_length=3.0,
        )
        snapshots = s.update_from_signals(signals)
        assert len(snapshots) == 4
        names = {sn.trait_name for sn in snapshots}
        assert names == {"persistence", "ambition", "risk_tolerance", "efficiency"}

    def test_high_completion_boosts_persistence(self):
        s = _store()
        for _ in range(20):
            s.update_from_signals(BehaviorSignals(completion_rate=0.95, switch_frequency=0.02))
        assert s.get_trait("persistence") > _DEFAULT_TRAIT_VALUE

    def test_high_switching_reduces_persistence(self):
        s = _store()
        for _ in range(20):
            s.update_from_signals(BehaviorSignals(completion_rate=0.1, switch_frequency=0.9))
        assert s.get_trait("persistence") < _DEFAULT_TRAIT_VALUE

    def test_signals_produce_bounded_changes(self):
        s = _store()
        before = {
            t: s.get_trait(t) for t in ["persistence", "ambition", "risk_tolerance", "efficiency"]
        }
        s.update_from_signals(
            BehaviorSignals(
                completion_rate=1.0,
                switch_frequency=1.0,
                success_rate=1.0,
                avg_sequence_length=10.0,
            )
        )
        for t in before:
            delta = abs(s.get_trait(t) - before[t])
            assert delta <= _MAX_DELTA_PER_UPDATE + 1e-9

    def test_repeated_neutral_signals_stay_moderate(self):
        s = _store()
        for _ in range(50):
            s.update_from_signals(BehaviorSignals())
        for t in ["persistence", "ambition", "risk_tolerance", "efficiency"]:
            assert _MIN_TRAIT_VALUE <= s.get_trait(t) <= _MAX_TRAIT_VALUE
            assert abs(s.get_trait(t) - _DEFAULT_TRAIT_VALUE) < 0.30


# ===========================================================================
# SECTION 9: IdentityStore — profile, clear, to_dict
# ===========================================================================


class TestIdentityStoreProfile:
    def test_get_profile(self):
        s = _store()
        s.update_trait("p", 0.8)
        s.set_preference("fast", 0.9)
        prof = s.get_profile()
        assert isinstance(prof, IdentityProfile)
        assert "p" in prof.traits
        assert "fast" in prof.preferences
        assert prof.update_count == 1

    def test_clear(self):
        s = _store()
        s.update_trait("p", 0.8)
        s.set_preference("fast", 0.9)
        s.clear()
        assert s.trait_count == 0
        assert s.update_count == 0
        assert s.history_count == 0
        assert s.get_trait("p") == pytest.approx(_DEFAULT_TRAIT_VALUE)

    def test_to_dict(self):
        s = _store()
        s.update_trait("p", 0.8)
        d = s.to_dict()
        assert "traits" in d
        assert "confidence" in d
        assert "update_count" in d
        assert "learning_rate" in d

    def test_history_returns_copy(self):
        s = _store()
        s.update_trait("p", 0.7)
        h = s.get_history()
        h.clear()
        assert s.history_count == 1


# ===========================================================================
# SECTION 10: IdentityScorer
# ===========================================================================


class TestIdentityScorer:
    def test_disabled_returns_neutral(self):
        scorer = _scorer(store=_store(), enabled=False)
        inf = scorer.compute_factor(sequence_length=3, avg_effort=2.0)
        assert inf.factor == pytest.approx(1.0)
        assert inf.reason == "identity scoring disabled"

    def test_no_store_returns_neutral(self):
        scorer = _scorer(store=None, enabled=True)
        inf = scorer.compute_factor()
        assert inf.factor == pytest.approx(1.0)

    def test_enabled_default_traits_near_neutral(self):
        s = _store()
        scorer = _scorer(store=s, enabled=True)
        inf = scorer.compute_factor(sequence_length=2, avg_effort=1.0)
        assert inf.factor == pytest.approx(1.0)

    def test_high_persistence_boosts_long_sequences(self):
        s = _store()
        for _ in range(30):
            s.update_trait("persistence", 1.0)
        scorer = _scorer(store=s, enabled=True)
        short = scorer.compute_factor(sequence_length=1, avg_effort=1.0)
        long = scorer.compute_factor(sequence_length=4, avg_effort=1.0)
        assert long.factor > short.factor

    def test_low_persistence_penalizes_long_sequences(self):
        s = _store()
        for _ in range(30):
            s.update_trait("persistence", 0.0)
        scorer = _scorer(store=s, enabled=True)
        long = scorer.compute_factor(sequence_length=4, avg_effort=1.0)
        assert long.factor < 1.0

    def test_factor_clamped_min(self):
        s = _store()
        for _ in range(100):
            s.update_trait("persistence", 0.0)
            s.update_trait("ambition", 0.0)
            s.update_trait("efficiency", 0.0)
            s.update_trait("risk_tolerance", 0.0)
        scorer = _scorer(store=s, enabled=True)
        inf = scorer.compute_factor(sequence_length=4, avg_effort=5.0, avg_priority=10.0)
        assert inf.factor >= _MIN_IDENTITY_FACTOR

    def test_factor_clamped_max(self):
        s = _store()
        for _ in range(100):
            s.update_trait("persistence", 1.0)
            s.update_trait("ambition", 1.0)
            s.update_trait("efficiency", 1.0)
            s.update_trait("risk_tolerance", 1.0)
        scorer = _scorer(store=s, enabled=True)
        inf = scorer.compute_factor(sequence_length=4, avg_effort=2.0, avg_priority=8.0)
        assert inf.factor <= _MAX_IDENTITY_FACTOR

    def test_trait_contributions_populated(self):
        s = _store()
        for _ in range(10):
            s.update_trait("persistence", 0.9)
        scorer = _scorer(store=s, enabled=True)
        inf = scorer.compute_factor(sequence_length=3)
        assert "persistence" in inf.trait_contributions

    def test_reason_includes_trait(self):
        s = _store()
        for _ in range(10):
            s.update_trait("persistence", 0.9)
        scorer = _scorer(store=s, enabled=True)
        inf = scorer.compute_factor(sequence_length=3)
        assert "persistence" in inf.reason

    def test_properties(self):
        s = _store()
        scorer = _scorer(store=s, enabled=True)
        assert scorer.enabled is True
        assert scorer.identity_store is s

    def test_deterministic(self):
        s = _store()
        for _ in range(10):
            s.update_trait("persistence", 0.8)
        scorer = _scorer(store=s, enabled=True)
        r1 = scorer.compute_factor(sequence_length=3, avg_effort=2.0)
        r2 = scorer.compute_factor(sequence_length=3, avg_effort=2.0)
        assert r1.factor == pytest.approx(r2.factor)


# ===========================================================================
# SECTION 11: Meta-Planner Integration
# ===========================================================================


class TestMetaPlannerIntegration:
    def test_evaluator_identity_property(self):
        from umh.runtime.meta_planner import SequenceEvaluator

        s = _store()
        scorer = _scorer(store=s, enabled=True)
        ev = SequenceEvaluator(identity_scorer=scorer)
        assert ev.identity_scorer is scorer

    def test_evaluator_no_identity(self):
        from umh.runtime.meta_planner import SequenceEvaluator

        ev = SequenceEvaluator()
        assert ev.identity_scorer is None

    def test_evaluator_identity_affects_score(self):
        from umh.runtime.meta_planner import SequenceEvaluator

        s = _store()
        for _ in range(30):
            s.update_trait("persistence", 1.0)
        scorer = _scorer(store=s, enabled=True)

        ev_no_id = SequenceEvaluator()
        ev_with_id = SequenceEvaluator(identity_scorer=scorer)

        objs = [_obj("a", priority=8, value=3.0), _obj("b", priority=7, value=2.0)]
        seq_no = ev_no_id.score_sequence(objs, label="test-no")
        seq_with = ev_with_id.score_sequence(objs, label="test-with")

        assert seq_no.total_score != pytest.approx(seq_with.total_score)

    def test_evaluator_identity_disabled_no_effect(self):
        from umh.runtime.meta_planner import SequenceEvaluator

        s = _store()
        for _ in range(30):
            s.update_trait("persistence", 1.0)
        scorer = _scorer(store=s, enabled=False)

        ev_no_id = SequenceEvaluator()
        ev_disabled = SequenceEvaluator(identity_scorer=scorer)

        objs = [_obj("a", priority=8, value=3.0), _obj("b", priority=7, value=2.0)]
        seq_no = ev_no_id.score_sequence(objs, label="test-no")
        seq_dis = ev_disabled.score_sequence(objs, label="test-dis")

        assert seq_no.total_score == pytest.approx(seq_dis.total_score)

    def test_planner_identity_property(self):
        from umh.runtime.meta_planner import MetaPlanner

        s = _store()
        scorer = _scorer(store=s, enabled=True)
        mp = MetaPlanner(identity_scorer=scorer)
        assert mp.identity_scorer is scorer

    def test_planner_no_identity(self):
        from umh.runtime.meta_planner import MetaPlanner

        mp = MetaPlanner()
        assert mp.identity_scorer is None

    def test_planner_reason_includes_identity(self):
        from umh.runtime.meta_planner import MetaPlanner, SequenceEvaluator

        s = _store()
        for _ in range(10):
            s.update_trait("persistence", 0.9)
        scorer = _scorer(store=s, enabled=True)

        mp = MetaPlanner(
            sequence_evaluator=SequenceEvaluator(identity_scorer=scorer),
            identity_scorer=scorer,
        )
        objs = [
            _obj("a", priority=8, value=3.0),
            _obj("b", priority=6, value=2.0),
            _obj("c", priority=4, value=1.0),
        ]
        result = mp.plan(objs)
        assert result is not None
        assert "identity" in result.reason.lower()


# ===========================================================================
# SECTION 12: Advisor Integration
# ===========================================================================


class TestAdvisorIntegration:
    def _make_advisor(self, **kw):
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.arbitration import ArbitrationEngine
        from umh.runtime.meta_planner import MetaPlanner

        return AdvisorRuntime(
            arbitration_engine=kw.get("arb", ArbitrationEngine()),
            meta_planner=kw.get("mp", MetaPlanner()),
            identity_store=kw.get("ids", IdentityStore()),
        )

    def test_identity_store_property(self):
        advisor = self._make_advisor()
        assert advisor.identity_store is not None

    def test_no_identity_store(self):
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        assert advisor.identity_store is None

    def test_tick_identity_updated_key(self):
        advisor = self._make_advisor()
        result = advisor.tick()
        assert "identity_updated" in result

    def test_tick_updates_identity(self):
        advisor = self._make_advisor()
        advisor.add_objective(_obj("a", priority=8))
        result = advisor.tick()
        assert result["identity_updated"] is True

    def test_identity_in_get_state(self):
        advisor = self._make_advisor()
        advisor.tick()
        state = advisor.get_state()
        assert "identity" in state
        assert "traits" in state["identity"]

    def test_clear_resets_identity(self):
        advisor = self._make_advisor()
        advisor.tick()
        advisor.clear()
        store = advisor.identity_store
        assert store.update_count == 0
        assert store.trait_count == 0

    def test_no_identity_store_skips(self):
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        result = advisor.tick()
        assert result["identity_updated"] is False

    def test_traits_evolve_over_ticks(self):
        advisor = self._make_advisor()
        advisor.add_objective(_obj("a", priority=8, value=3.0))
        for _ in range(10):
            advisor.tick()
        store = advisor.identity_store
        assert store.update_count == 40
        assert store.trait_count > 0

    def test_identity_switch_tracking(self):
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.arbitration import ArbitrationEngine
        from umh.runtime.commitment import CommitmentEngine
        from umh.runtime.meta_planner import MetaPlanner

        advisor = AdvisorRuntime(
            arbitration_engine=ArbitrationEngine(),
            meta_planner=MetaPlanner(),
            commitment_engine=CommitmentEngine(),
            identity_store=IdentityStore(),
        )
        advisor.add_objective(_obj("a", priority=2, value=0.1))
        advisor.tick()

        advisor.add_objective(_obj("b", priority=10, value=5.0))
        advisor.remove_objective("a")
        advisor.tick()

        assert advisor._identity_switches >= 1


# ===========================================================================
# SECTION 13: Stability — no spikes
# ===========================================================================


class TestStability:
    def test_single_extreme_signal_bounded(self):
        s = _store()
        s.update_from_signals(
            BehaviorSignals(
                completion_rate=1.0,
                switch_frequency=0.0,
                success_rate=1.0,
                avg_sequence_length=10.0,
            )
        )
        for t in ["persistence", "ambition", "risk_tolerance", "efficiency"]:
            delta = abs(s.get_trait(t) - _DEFAULT_TRAIT_VALUE)
            assert delta <= _MAX_DELTA_PER_UPDATE + 1e-9

    def test_alternating_signals_stable(self):
        s = _store()
        for i in range(50):
            if i % 2 == 0:
                s.update_from_signals(BehaviorSignals(completion_rate=1.0, switch_frequency=0.0))
            else:
                s.update_from_signals(BehaviorSignals(completion_rate=0.0, switch_frequency=1.0))
        p = s.get_trait("persistence")
        assert 0.2 < p < 0.8

    def test_gradual_drift(self):
        s = _store()
        values = []
        for _ in range(20):
            s.update_from_signals(BehaviorSignals(completion_rate=0.9, switch_frequency=0.05))
            values.append(s.get_trait("persistence"))
        for i in range(1, len(values)):
            assert abs(values[i] - values[i - 1]) <= _MAX_DELTA_PER_UPDATE + 1e-9

    def test_scorer_stability(self):
        s = _store()
        scorer = _scorer(store=s, enabled=True)
        factors = []
        for _ in range(20):
            s.update_from_signals(BehaviorSignals(completion_rate=0.9, switch_frequency=0.05))
            inf = scorer.compute_factor(sequence_length=3, avg_effort=2.0)
            factors.append(inf.factor)
        for i in range(1, len(factors)):
            assert abs(factors[i] - factors[i - 1]) < 0.05


# ===========================================================================
# SECTION 14: Hard Invariants 106-110
# ===========================================================================


class TestHardInvariants:
    def test_inv106_updates_append_only(self):
        """History only grows, never shrinks during updates."""
        s = _store()
        for i in range(10):
            s.update_trait("p", 0.5 + i * 0.01)
            assert s.history_count == i + 1
        s.update_from_signals(BehaviorSignals())
        assert s.history_count == 14

    def test_inv106_no_history_deletion_during_update(self):
        s = _store()
        s.update_trait("a", 0.7)
        s.update_trait("b", 0.8)
        h1 = s.get_history()
        s.update_trait("a", 0.9)
        h2 = s.get_history()
        assert len(h2) == len(h1) + 1
        assert h2[0].trait_name == h1[0].trait_name
        assert h2[1].trait_name == h1[1].trait_name

    def test_inv107_identity_no_execution_mutation(self):
        """Identity module must not import execution-layer modules."""
        import umh.runtime.identity as mod

        source = open(mod.__file__).read()
        tree = ast.parse(source)
        forbidden = {"umh.cells", "umh.environments", "umh.adapters", "subprocess"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for prefix in forbidden:
                        assert not node.module.startswith(prefix), (
                            f"identity.py imports {node.module}"
                        )

    def test_inv108_multiplicative_not_overriding(self):
        """Identity factor is multiplicative: always in [0.80, 1.20]."""
        s = _store()
        for _ in range(100):
            s.update_trait("persistence", 1.0)
            s.update_trait("ambition", 1.0)
            s.update_trait("efficiency", 1.0)
            s.update_trait("risk_tolerance", 1.0)
        scorer = _scorer(store=s, enabled=True)
        inf = scorer.compute_factor(sequence_length=4, avg_effort=5.0, avg_priority=10.0)
        assert _MIN_IDENTITY_FACTOR <= inf.factor <= _MAX_IDENTITY_FACTOR

    def test_inv108_extreme_low(self):
        s = _store()
        for _ in range(100):
            s.update_trait("persistence", 0.0)
            s.update_trait("ambition", 0.0)
            s.update_trait("efficiency", 0.0)
            s.update_trait("risk_tolerance", 0.0)
        scorer = _scorer(store=s, enabled=True)
        inf = scorer.compute_factor(sequence_length=4, avg_effort=5.0, avg_priority=10.0)
        assert inf.factor >= _MIN_IDENTITY_FACTOR

    def test_inv109_bounded_delta(self):
        """Each trait update is bounded by max_delta."""
        s = _store(max_delta=0.05)
        old = s.get_trait("p")
        s.update_trait("p", 1.0)
        new = s.get_trait("p")
        assert abs(new - old) <= 0.05 + 1e-9

    def test_inv109_bounded_delta_negative(self):
        s = _store(max_delta=0.05)
        old = s.get_trait("p")
        s.update_trait("p", 0.0)
        new = s.get_trait("p")
        assert abs(new - old) <= 0.05 + 1e-9

    def test_inv110_determinism_without_identity(self):
        """Scoring is identical with and without identity when disabled."""
        from umh.runtime.meta_planner import SequenceEvaluator

        ev1 = SequenceEvaluator()
        ev2 = SequenceEvaluator(identity_scorer=_scorer(store=_store(), enabled=False))

        objs = [_obj("a", priority=8, value=3.0), _obj("b", priority=5)]
        s1 = ev1.score_sequence(objs, label="t1")
        s2 = ev2.score_sequence(objs, label="t2")
        assert s1.total_score == pytest.approx(s2.total_score)

    def test_inv110_determinism_without_identity_none(self):
        from umh.runtime.meta_planner import SequenceEvaluator

        ev1 = SequenceEvaluator()
        ev2 = SequenceEvaluator(identity_scorer=None)

        objs = [_obj("a", priority=8, value=3.0)]
        s1 = ev1.score_sequence(objs, label="t1")
        s2 = ev2.score_sequence(objs, label="t2")
        assert s1.total_score == pytest.approx(s2.total_score)


# ===========================================================================
# SECTION 15: Boundary / Export Checks
# ===========================================================================


class TestBoundaryChecks:
    def test_import_identity(self):
        from umh.runtime.identity import (
            BehaviorSignals,
            IdentityInfluence,
            IdentityProfile,
            IdentityScorer,
            IdentityStore,
            SignalExtractor,
            TraitSnapshot,
        )

        assert IdentityStore is not None

    def test_import_from_runtime(self):
        from umh.runtime import (
            BehaviorSignals,
            IdentityInfluence,
            IdentityProfile,
            IdentityScorer,
            IdentityStore,
            SignalExtractor,
            TraitSnapshot,
        )

        assert TraitSnapshot is not None

    def test_compile_identity(self):
        import py_compile

        py_compile.compile("umh/runtime/identity.py", doraise=True)

    def test_compile_meta_planner(self):
        import py_compile

        py_compile.compile("umh/runtime/meta_planner.py", doraise=True)

    def test_compile_advisor(self):
        import py_compile

        py_compile.compile("umh/runtime/advisor.py", doraise=True)

    def test_compile_init(self):
        import py_compile

        py_compile.compile("umh/runtime/__init__.py", doraise=True)

    def test_all_exports_in_init(self):
        import umh.runtime as rt

        for name in [
            "BehaviorSignals",
            "IdentityInfluence",
            "IdentityProfile",
            "IdentityScorer",
            "IdentityStore",
            "SignalExtractor",
            "TraitSnapshot",
        ]:
            assert name in rt.__all__, f"{name} missing from __all__"

    def test_end_to_end_pipeline(self):
        """Full pipeline: signals → traits → scoring → bias."""
        s = _store()
        ext = SignalExtractor()
        scorer = _scorer(store=s, enabled=True)

        for _ in range(20):
            signals = ext.extract(
                total_ticks=100,
                goals_completed=9,
                goals_attempted=10,
                switches=1,
            )
            s.update_from_signals(signals)

        assert s.get_trait("persistence") > _DEFAULT_TRAIT_VALUE
        assert s.get_trait("efficiency") > _DEFAULT_TRAIT_VALUE

        inf = scorer.compute_factor(sequence_length=3, avg_effort=1.5)
        assert inf.factor != pytest.approx(1.0, abs=0.001)

    def test_end_to_end_advisor(self):
        """Advisor tick with identity store — full integration."""
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.arbitration import ArbitrationEngine
        from umh.runtime.meta_planner import MetaPlanner

        advisor = AdvisorRuntime(
            arbitration_engine=ArbitrationEngine(),
            meta_planner=MetaPlanner(),
            identity_store=IdentityStore(),
        )
        advisor.add_objective(_obj("a", priority=8, value=3.0))
        advisor.add_objective(_obj("b", priority=5, value=1.0))

        for _ in range(5):
            result = advisor.tick()
            assert result["identity_updated"] is True

        state = advisor.get_state()
        assert state["identity"]["update_count"] == 20

    def test_trait_map_has_all_core_traits(self):
        from umh.runtime.identity import _TRAIT_SIGNAL_MAP

        assert "persistence" in _TRAIT_SIGNAL_MAP
        assert "ambition" in _TRAIT_SIGNAL_MAP
        assert "risk_tolerance" in _TRAIT_SIGNAL_MAP
        assert "efficiency" in _TRAIT_SIGNAL_MAP

    def test_scorer_neutral_with_fresh_store(self):
        s = _store()
        scorer = _scorer(store=s, enabled=True)
        inf = scorer.compute_factor(sequence_length=2, avg_effort=2.0, avg_priority=7.0)
        assert inf.factor == pytest.approx(1.0)
        assert inf.trait_contributions == {}
        assert "no trait data" in inf.reason

    def test_identity_influence_to_dict_empty(self):
        ii = IdentityInfluence(factor=1.0, trait_contributions={}, reason="none")
        d = ii.to_dict()
        assert d["trait_contributions"] == {}

    def test_behavior_signals_to_dict_all(self):
        bs = BehaviorSignals(
            completion_rate=0.1, switch_frequency=0.2, success_rate=0.3, avg_sequence_length=4.5
        )
        d = bs.to_dict()
        assert len(d) == 4
        assert d["avg_sequence_length"] == round(4.5, 4)

    def test_scorer_ambition_high_effort_boost(self):
        s = _store()
        for _ in range(30):
            s.update_trait("ambition", 1.0)
        scorer = _scorer(store=s, enabled=True)
        low_effort = scorer.compute_factor(sequence_length=2, avg_effort=0.5)
        high_effort = scorer.compute_factor(sequence_length=2, avg_effort=3.0)
        assert high_effort.factor > low_effort.factor

    def test_scorer_efficiency_low_effort_boost(self):
        s = _store()
        for _ in range(30):
            s.update_trait("efficiency", 1.0)
        scorer = _scorer(store=s, enabled=True)
        low_effort = scorer.compute_factor(sequence_length=2, avg_effort=0.5)
        high_effort = scorer.compute_factor(sequence_length=2, avg_effort=4.0)
        assert low_effort.factor > high_effort.factor
