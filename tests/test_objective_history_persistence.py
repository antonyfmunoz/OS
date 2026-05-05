"""Tests for objective history persistence.

Covers: restart continuity of trend detection, EMA stability across restart,
bounded history enforcement, corrupt/missing payload fallback, determinism,
and no regression in optimizer / regime / exploration / decision adapter.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.objective_optimizer import (
    Trend,
    compute_optimization_signal,
)
from umh.runtime_engine.objective_decision_adapter import (
    compute_decision_signal,
)
from umh.runtime_engine.persistence import (
    MAX_OBJECTIVE_HISTORY,
    PERSISTENCE_VERSION,
    STORAGE_KEY_OBJECTIVE_HISTORY,
    _PersistenceBuffer,
    _reset_buffer_for_tests,
    load_objective_history,
    save_objective_history,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


class FakeStorage:
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str) -> object:
        return self._data.get(key)

    def put(self, key: str, value: object) -> None:
        self._data[key] = value


def _improving_history(n: int = 10) -> list[float]:
    return [0.4 + i * 0.03 for i in range(n)]


def _degrading_history(n: int = 10) -> list[float]:
    return [0.8 - i * 0.03 for i in range(n)]


def _flat_history(n: int = 10) -> list[float]:
    return [0.5] * n


def _with_storage(storage: FakeStorage):
    """Context manager that patches storage for persistence functions."""
    import umh.runtime_engine.persistence as p

    class _Ctx:
        def __enter__(self):
            self._orig = p._get_storage_safe
            p._get_storage_safe = lambda: storage
            _reset_buffer_for_tests()
            return storage

        def __exit__(self, *args):
            p._get_storage_safe = self._orig
            _reset_buffer_for_tests()

    return _Ctx()


# ─── Restart continuity of trend detection ──────────────────────────────────


class TestRestartContinuity:
    def test_trend_survives_restart(self) -> None:
        """Trend computed from persisted history matches pre-restart trend."""
        history = _improving_history(10)
        signal_before = compute_optimization_signal(history)
        assert signal_before.trend == Trend.IMPROVING

        # Simulate restart: persist then load
        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history(history)
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        assert loaded is not None
        signal_after = compute_optimization_signal(loaded)
        assert signal_after.trend == signal_before.trend
        assert abs(signal_after.ema_delta - signal_before.ema_delta) < 1e-10

    def test_degrading_trend_survives_restart(self) -> None:
        history = _degrading_history(10)
        signal_before = compute_optimization_signal(history)
        assert signal_before.trend == Trend.DEGRADING

        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history(history)
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        signal_after = compute_optimization_signal(loaded)
        assert signal_after.trend == Trend.DEGRADING

    def test_flat_trend_survives_restart(self) -> None:
        history = _flat_history(10)
        signal_before = compute_optimization_signal(history)
        assert signal_before.trend == Trend.FLAT

        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history(history)
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        signal_after = compute_optimization_signal(loaded)
        assert signal_after.trend == Trend.FLAT

    def test_history_continues_across_restart(self) -> None:
        """New values appended to restored history produce continuous trend."""
        session1 = _improving_history(8)
        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history(session1)
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        assert loaded is not None
        session2 = loaded + [0.65, 0.68, 0.71]
        signal = compute_optimization_signal(session2)
        assert signal.trend == Trend.IMPROVING


# ─── EMA stability across restart ──────────────────────────────────────────


class TestEMAStability:
    def test_ema_delta_identical_after_roundtrip(self) -> None:
        history = _improving_history(20)
        signal_orig = compute_optimization_signal(history)

        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history(history)
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        signal_restored = compute_optimization_signal(loaded)
        assert signal_orig.ema_delta == signal_restored.ema_delta

    def test_ema_continuity_with_new_data(self) -> None:
        """EMA computed incrementally matches EMA computed on full history."""
        full_history = _improving_history(15)

        session1 = full_history[:10]
        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history(session1)
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        combined = loaded + full_history[10:]
        signal_combined = compute_optimization_signal(combined)
        signal_full = compute_optimization_signal(full_history)
        assert abs(signal_combined.ema_delta - signal_full.ema_delta) < 1e-10

    def test_adjustments_stable_across_restart(self) -> None:
        history = _improving_history(10)
        sig1 = compute_optimization_signal(history)

        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history(history)
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        sig2 = compute_optimization_signal(loaded)
        assert sig1.exploration_adjustment == sig2.exploration_adjustment
        assert sig1.policy_bias == sig2.policy_bias
        assert sig1.confidence_adjustment == sig2.confidence_adjustment


# ─── Bounded history enforcement ────────────────────────────────────────────


class TestBoundedHistory:
    def test_save_caps_at_max(self) -> None:
        large = [0.5 + i * 0.001 for i in range(MAX_OBJECTIVE_HISTORY + 100)]
        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history(large)
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        assert loaded is not None
        assert len(loaded) <= MAX_OBJECTIVE_HISTORY

    def test_load_caps_oversized_payload(self) -> None:
        storage = FakeStorage()
        oversized = [0.5] * (MAX_OBJECTIVE_HISTORY + 50)
        storage.put(
            STORAGE_KEY_OBJECTIVE_HISTORY,
            {"version": 1, "data": {"objective_values": oversized}},
        )

        import umh.runtime_engine.persistence as p

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            loaded = load_objective_history()
            assert loaded is not None
            assert len(loaded) <= MAX_OBJECTIVE_HISTORY
        finally:
            p._get_storage_safe = orig

    def test_fifo_order_preserved(self) -> None:
        values = list(range(MAX_OBJECTIVE_HISTORY + 50))
        floats = [float(v) for v in values]
        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history(floats)
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        assert loaded is not None
        assert loaded[0] == float(50)
        assert loaded[-1] == float(MAX_OBJECTIVE_HISTORY + 49)


# ─── Corrupt / missing payload fallback ─────────────────────────────────────


class TestCorruptFallback:
    def test_missing_key_returns_none(self) -> None:
        storage = FakeStorage()
        import umh.runtime_engine.persistence as p

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            assert load_objective_history() is None
        finally:
            p._get_storage_safe = orig

    def test_corrupt_string_returns_none(self) -> None:
        storage = FakeStorage()
        storage.put(STORAGE_KEY_OBJECTIVE_HISTORY, "garbage")
        import umh.runtime_engine.persistence as p

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            assert load_objective_history() is None
        finally:
            p._get_storage_safe = orig

    def test_future_version_returns_none(self) -> None:
        storage = FakeStorage()
        storage.put(
            STORAGE_KEY_OBJECTIVE_HISTORY,
            {"version": 999, "data": {"objective_values": [0.5]}},
        )
        import umh.runtime_engine.persistence as p

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            assert load_objective_history() is None
        finally:
            p._get_storage_safe = orig

    def test_corrupt_data_field_returns_none(self) -> None:
        storage = FakeStorage()
        storage.put(
            STORAGE_KEY_OBJECTIVE_HISTORY,
            {"version": 1, "data": "not a dict"},
        )
        import umh.runtime_engine.persistence as p

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            assert load_objective_history() is None
        finally:
            p._get_storage_safe = orig

    def test_corrupt_values_field_returns_none(self) -> None:
        storage = FakeStorage()
        storage.put(
            STORAGE_KEY_OBJECTIVE_HISTORY,
            {"version": 1, "data": {"objective_values": "not a list"}},
        )
        import umh.runtime_engine.persistence as p

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            assert load_objective_history() is None
        finally:
            p._get_storage_safe = orig

    def test_no_storage_returns_none(self) -> None:
        import umh.runtime_engine.persistence as p

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: None
        try:
            assert load_objective_history() is None
        finally:
            p._get_storage_safe = orig

    def test_storage_exception_returns_none(self) -> None:
        class BrokenStorage:
            def get(self, key: str) -> None:
                raise ConnectionError("db down")

        import umh.runtime_engine.persistence as p

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: BrokenStorage()
        try:
            assert load_objective_history() is None
        finally:
            p._get_storage_safe = orig


# ─── Versioned payload structure ────────────────────────────────────────────


class TestVersionedPayloads:
    def test_save_produces_versioned_payload(self) -> None:
        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history([0.5, 0.6, 0.7])
            from umh.runtime_engine.persistence import flush

            flush()

        raw = storage.get(STORAGE_KEY_OBJECTIVE_HISTORY)
        assert isinstance(raw, dict)
        assert raw["version"] == PERSISTENCE_VERSION
        assert "data" in raw
        assert "objective_values" in raw["data"]
        assert raw["data"]["objective_values"] == [0.5, 0.6, 0.7]


# ─── Buffer mechanics ──────────────────────────────────────────────────────


class TestBufferMechanics:
    def test_buffer_mark_objective_history(self) -> None:
        buf = _PersistenceBuffer()
        buf.mark_objective_history({"test": True})
        assert buf._objective_history_dirty
        assert buf._objective_history_data == {"test": True}

    def test_flush_with_no_storage_does_not_crash(self) -> None:
        import umh.runtime_engine.persistence as p

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: None
        try:
            _reset_buffer_for_tests()
            save_objective_history([0.5, 0.6])
            from umh.runtime_engine.persistence import flush

            flush()
        finally:
            p._get_storage_safe = orig
            _reset_buffer_for_tests()

    def test_full_roundtrip_with_fake_storage(self) -> None:
        storage = FakeStorage()
        with _with_storage(storage):
            save_objective_history([0.3, 0.4, 0.5, 0.6])
            from umh.runtime_engine.persistence import flush

            flush()
            loaded = load_objective_history()

        assert loaded == [0.3, 0.4, 0.5, 0.6]


# ─── Determinism ────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_optimizer_deterministic_across_roundtrip(self) -> None:
        history = [0.4 + i * 0.02 for i in range(15)]
        sig1 = compute_optimization_signal(history)
        sig2 = compute_optimization_signal(list(history))
        assert sig1.ema_delta == sig2.ema_delta
        assert sig1.trend == sig2.trend
        assert sig1.exploration_adjustment == sig2.exploration_adjustment

    def test_decision_adapter_deterministic_across_roundtrip(self) -> None:
        history = _improving_history(10)
        sig1 = compute_decision_signal(history)
        sig2 = compute_decision_signal(list(history))
        assert sig1.ema_delta == sig2.ema_delta
        assert sig1.strategy_shift == sig2.strategy_shift


# ─── No regression: optimizer still works correctly ─────────────────────────


class TestOptimizerNoRegression:
    def test_insufficient_history_returns_no_signal(self) -> None:
        sig = compute_optimization_signal([0.5, 0.6])
        assert sig.trend == Trend.FLAT
        assert sig.ema_delta == 0.0
        assert not sig.is_active

    def test_improving_history_produces_improving(self) -> None:
        sig = compute_optimization_signal(_improving_history(10))
        assert sig.trend == Trend.IMPROVING
        assert sig.exploration_adjustment < 0.0
        assert sig.policy_bias > 0.0
        assert sig.confidence_adjustment > 0.0

    def test_degrading_history_produces_degrading(self) -> None:
        sig = compute_optimization_signal(_degrading_history(10))
        assert sig.trend == Trend.DEGRADING
        assert sig.exploration_adjustment > 0.0
        assert sig.policy_bias < 0.0
        assert sig.confidence_adjustment < 0.0

    def test_flat_history_produces_flat(self) -> None:
        sig = compute_optimization_signal(_flat_history(10))
        assert sig.trend == Trend.FLAT
        assert not sig.is_active


# ─── No regression: decision adapter ───────────────────────────────────────


class TestDecisionAdapterNoRegression:
    def test_improving_produces_positive_shift(self) -> None:
        sig = compute_decision_signal(_improving_history(10))
        assert sig.trend == "improving"
        assert sig.strategy_shift > 0.0
        assert sig.goal_scale > 1.0

    def test_degrading_produces_negative_shift(self) -> None:
        sig = compute_decision_signal(_degrading_history(10))
        assert sig.trend == "degrading"
        assert sig.strategy_shift < 0.0
        assert sig.goal_scale < 1.0

    def test_flat_produces_minimal_shift(self) -> None:
        sig = compute_decision_signal(_flat_history(10))
        assert sig.trend == "flat"
        assert sig.goal_scale == 1.0


# ─── No regression: regime engine ──────────────────────────────────────────


class TestRegimeNoRegression:
    def test_regime_engine_import(self) -> None:
        from umh.runtime_engine.regime_engine import NO_REGIME_BREAK

        assert NO_REGIME_BREAK.active is False

    def test_regime_with_objective_trend(self) -> None:
        from umh.runtime_engine.regime_engine import compute_regime_signal

        signal = compute_regime_signal(
            reward_history=[0.5] * 20,
            strategy_scores={"A": 0.5, "B": 0.5},
            objective_trend="flat",
        )
        assert signal.active is False


# ─── No regression: exploration engine ─────────────────────────────────────


class TestExplorationNoRegression:
    def test_exploration_engine_import(self) -> None:
        from umh.runtime_engine.exploration_engine import compute_exploration_signal

        sig = compute_exploration_signal(
            plan_confidence=0.5,
            objective_trend="flat",
            failure_streak=0,
            strategy_scores={"A": 0.5, "B": 0.5},
        )
        assert sig is not None

    def test_exploration_with_degrading_trend(self) -> None:
        from umh.runtime_engine.exploration_engine import compute_exploration_signal

        sig = compute_exploration_signal(
            plan_confidence=0.3,
            objective_trend="degrading",
            failure_streak=2,
            strategy_scores={"A": 0.5, "B": 0.5},
        )
        assert sig is not None


# ─── DecisionTrace fields ──────────────────────────────────────────────────


class TestDecisionTraceFields:
    def test_objective_history_fields_exist(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            objective_history_length=15,
            objective_persisted=True,
        )
        assert trace.objective_history_length == 15
        assert trace.objective_persisted is True

    def test_fields_default_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        assert trace.objective_history_length is None
        assert trace.objective_persisted is None

    def test_fields_in_to_dict_when_set(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            objective_history_length=20,
            objective_persisted=True,
        )
        d = trace.to_dict()
        assert d["objective_history_length"] == 20
        assert d["objective_persisted"] is True

    def test_fields_omitted_from_dict_when_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        d = trace.to_dict()
        assert "objective_history_length" not in d
        assert "objective_persisted" not in d


# ─── Persistence status includes objective_history ──────────────────────────


class TestPersistenceStatus:
    def test_status_includes_objective_history(self) -> None:
        storage = FakeStorage()
        storage.put(
            STORAGE_KEY_OBJECTIVE_HISTORY,
            {"version": 1, "data": {"objective_values": [0.5]}},
        )

        import umh.runtime_engine.persistence as p
        from umh.runtime_engine.persistence import get_persistence_status

        orig = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            status = get_persistence_status()
            assert "objective_history" in status["persisted_components"]
        finally:
            p._get_storage_safe = orig


# ─── No regressions: existing persistence functions ─────────────────────────


class TestNoRegressions:
    def test_existing_functions_still_importable(self) -> None:
        from umh.runtime_engine.persistence import (
            flush,
            load_memory_fabric,
            load_meta_weights,
            load_strategy_memory,
            save_memory_fabric,
            save_meta_weights,
            save_strategy_memory,
        )

        assert callable(flush)
        assert callable(load_meta_weights)
        assert callable(save_meta_weights)
        assert callable(load_memory_fabric)
        assert callable(save_memory_fabric)
        assert callable(load_strategy_memory)
        assert callable(save_strategy_memory)

    def test_existing_buffer_slots_untouched(self) -> None:
        buf = _PersistenceBuffer()
        assert hasattr(buf, "_strategy_dirty")
        assert hasattr(buf, "_meta_weights_dirty")
        assert hasattr(buf, "_memory_fabric_dirty")
        assert hasattr(buf, "_objective_history_dirty")
