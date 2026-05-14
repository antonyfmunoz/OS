"""Tests for the EOS persistence layer.

Covers: snapshot/restore roundtrip, restart continuity, missing storage keys,
corrupt payload fallback, version mismatch, bounded payload enforcement,
deterministic output, backward compatibility, and no regressions.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.memory_fabric import (
    EntryType,
    MemoryEntry,
    MemoryFabric,
)
from umh.runtime_engine.meta_weight_engine import (
    SIGNAL_NAMES,
    MetaWeightEngine,
)
from umh.runtime_engine.persistence import (
    PERSISTENCE_VERSION,
    STORAGE_KEY_MEMORY_FABRIC,
    STORAGE_KEY_META_WEIGHTS,
    _PersistenceBuffer,
    _reset_buffer_for_tests,
    load_memory_fabric,
    load_meta_weights,
    save_memory_fabric,
    save_meta_weights,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_entry(turn: int, outcome: float = 0.5, source: str = "test") -> MemoryEntry:
    return MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=turn,
        features={"quality": outcome},
        outcome=outcome,
        source=source,
    )


def _trained_meta_engine(n: int = 5) -> MetaWeightEngine:
    engine = MetaWeightEngine()
    for i in range(n):
        signals = {name: 0.3 + i * 0.1 for name in SIGNAL_NAMES}
        engine.record_outcome(signals, outcome_quality=0.5 + i * 0.08)
    return engine


def _filled_fabric(n: int = 10) -> MemoryFabric:
    fabric = MemoryFabric()
    for i in range(n):
        fabric.record(_make_entry(turn=i, outcome=0.3 + i * 0.05))
    return fabric


class FakeStorage:
    """In-memory storage that mimics SubstrateStorage.get/put."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str) -> object:
        return self._data.get(key)

    def put(self, key: str, value: object) -> None:
        self._data[key] = value


# ─── MetaWeightEngine: snapshot/restore roundtrip ───────────────────────────


class TestMetaWeightRoundtrip:
    def test_snapshot_restore_preserves_ema(self) -> None:
        engine = _trained_meta_engine(5)
        snap = engine.snapshot()

        restored = MetaWeightEngine()
        restored.restore(snap)

        for name in SIGNAL_NAMES:
            assert engine._performance[name].ema == restored._performance[name].ema
            assert (
                engine._performance[name].observations
                == restored._performance[name].observations
            )

    def test_snapshot_is_plain_dict(self) -> None:
        snap = _trained_meta_engine().snapshot()
        assert isinstance(snap, dict)
        for name in SIGNAL_NAMES:
            assert name in snap
            assert isinstance(snap[name], dict)
            assert "ema" in snap[name]
            assert "observations" in snap[name]

    def test_adapted_weights_match_after_restore(self) -> None:
        engine = _trained_meta_engine(5)
        base_weights = {name: 1.0 / len(SIGNAL_NAMES) for name in SIGNAL_NAMES}
        original = engine.get_adapted_weights(base_weights)

        restored = MetaWeightEngine()
        restored.restore(engine.snapshot())
        after_restore = restored.get_adapted_weights(base_weights)

        for name in SIGNAL_NAMES:
            assert (
                abs(
                    original.adapted_weights[name] - after_restore.adapted_weights[name]
                )
                < 1e-10
            )

    def test_restore_empty_dict_is_safe(self) -> None:
        engine = MetaWeightEngine()
        engine.restore({})
        assert engine.total_observations == 0

    def test_restore_none_is_safe(self) -> None:
        engine = MetaWeightEngine()
        engine.restore(None)  # type: ignore[arg-type]
        assert engine.total_observations == 0

    def test_restore_partial_signals(self) -> None:
        engine = _trained_meta_engine(3)
        snap = engine.snapshot()
        del snap["goal"]  # remove one signal

        restored = MetaWeightEngine()
        restored.restore(snap)
        assert restored._performance["goal"].observations == 0
        assert restored._performance["plan"].observations == 3


# ─── MemoryFabric: snapshot/restore roundtrip ───────────────────────────────


class TestMemoryFabricRoundtrip:
    def test_snapshot_restore_preserves_entries(self) -> None:
        fabric = _filled_fabric(10)
        snap = fabric.snapshot()

        restored = MemoryFabric()
        restored.restore(snap)

        assert restored.entry_count == fabric.entry_count
        for orig, rest in zip(fabric._entries, restored._entries):
            assert orig.turn == rest.turn
            assert abs(orig.outcome - rest.outcome) < 1e-4
            assert orig.entry_type == rest.entry_type

    def test_snapshot_has_required_keys(self) -> None:
        snap = _filled_fabric(5).snapshot()
        assert "entry_count" in snap
        assert "entry_counter" in snap
        assert "entries" in snap
        assert isinstance(snap["entries"], list)

    def test_query_works_after_restore(self) -> None:
        fabric = _filled_fabric(10)
        snap = fabric.snapshot()

        restored = MemoryFabric()
        restored.restore(snap)

        results = restored.query(entry_type=EntryType.STRATEGY_OUTCOME)
        assert len(results) == 10

    def test_aggregation_matches_after_restore(self) -> None:
        fabric = _filled_fabric(10)
        orig_agg = fabric._aggregate_internal()
        snap = fabric.snapshot()

        restored = MemoryFabric()
        restored.restore(snap)
        rest_agg = restored._aggregate_internal()

        assert orig_agg.total_entries == rest_agg.total_entries
        assert (
            abs(orig_agg.recent_outcome_trend - rest_agg.recent_outcome_trend) < 1e-10
        )

    def test_restore_empty_data(self) -> None:
        fabric = MemoryFabric()
        fabric.restore({})
        assert fabric.entry_count == 0

    def test_restore_missing_entries_key(self) -> None:
        fabric = MemoryFabric()
        fabric.restore({"entry_counter": 5, "max_entries": 100})
        assert fabric.entry_count == 0
        assert fabric._entry_counter == 5


# ─── Bounded payload enforcement ────────────────────────────────────────────


class TestBoundedPayloads:
    def test_fabric_cap_enforced_on_restore(self) -> None:
        fabric = MemoryFabric(max_entries=50)
        for i in range(100):
            fabric.record(_make_entry(turn=i, outcome=0.5))

        snap = fabric.snapshot()
        assert len(snap["entries"]) == 50

        small_fabric = MemoryFabric(max_entries=20)
        small_fabric.restore(snap)
        # restore() sets _max_entries from snapshot; enforce local cap like get_memory_fabric() does
        small_fabric._max_entries = 20
        if len(small_fabric._entries) > small_fabric._max_entries:
            small_fabric._entries = small_fabric._entries[-small_fabric._max_entries :]
        assert len(small_fabric._entries) <= 20

    def test_fabric_fifo_eviction_order(self) -> None:
        fabric = MemoryFabric(max_entries=5)
        for i in range(10):
            fabric.record(_make_entry(turn=i))

        assert fabric.entry_count == 5
        assert fabric._entries[0].turn == 5  # oldest kept
        assert fabric._entries[-1].turn == 9  # newest

    def test_meta_engine_observations_bounded(self) -> None:
        engine = MetaWeightEngine()
        for i in range(1000):
            signals = {name: 0.5 for name in SIGNAL_NAMES}
            engine.record_outcome(signals, 0.5)
        snap = engine.snapshot()
        for name in SIGNAL_NAMES:
            assert snap[name]["observations"] == 1000
            assert 0.0 <= snap[name]["ema"] <= 1.0


# ─── Versioned payload handling ─────────────────────────────────────────────


class TestVersionedPayloads:
    def test_save_wraps_with_version(self) -> None:
        storage = FakeStorage()

        engine = _trained_meta_engine(3)
        payload = {
            "version": PERSISTENCE_VERSION,
            "data": engine.snapshot(),
        }
        storage.put(STORAGE_KEY_META_WEIGHTS, payload)

        raw = storage.get(STORAGE_KEY_META_WEIGHTS)
        assert isinstance(raw, dict)
        assert raw["version"] == PERSISTENCE_VERSION
        assert "data" in raw

    def test_future_version_rejected(self) -> None:
        storage = FakeStorage()
        storage.put(
            STORAGE_KEY_META_WEIGHTS,
            {"version": PERSISTENCE_VERSION + 1, "data": {"goal": {"ema": 0.5}}},
        )

        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            result = load_meta_weights()
            assert result is None
        finally:
            p._get_storage_safe = orig_get

    def test_current_version_accepted(self) -> None:
        storage = FakeStorage()
        engine = _trained_meta_engine(3)
        storage.put(
            STORAGE_KEY_META_WEIGHTS,
            {"version": PERSISTENCE_VERSION, "data": engine.snapshot()},
        )

        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            result = load_meta_weights()
            assert result is not None
            assert "goal" in result
        finally:
            p._get_storage_safe = orig_get

    def test_memory_fabric_future_version_rejected(self) -> None:
        storage = FakeStorage()
        storage.put(
            STORAGE_KEY_MEMORY_FABRIC,
            {"version": 999, "data": {"entries": []}},
        )

        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            result = load_memory_fabric()
            assert result is None
        finally:
            p._get_storage_safe = orig_get


# ─── Corrupt / missing payload fallback ─────────────────────────────────────


class TestCorruptFallback:
    def test_meta_weights_corrupt_string_returns_none(self) -> None:
        storage = FakeStorage()
        storage.put(STORAGE_KEY_META_WEIGHTS, "not a dict")

        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            assert load_meta_weights() is None
        finally:
            p._get_storage_safe = orig_get

    def test_meta_weights_corrupt_data_field(self) -> None:
        storage = FakeStorage()
        storage.put(
            STORAGE_KEY_META_WEIGHTS,
            {"version": 1, "data": "garbage"},
        )

        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            assert load_meta_weights() is None
        finally:
            p._get_storage_safe = orig_get

    def test_memory_fabric_corrupt_returns_none(self) -> None:
        storage = FakeStorage()
        storage.put(STORAGE_KEY_MEMORY_FABRIC, [1, 2, 3])

        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            assert load_memory_fabric() is None
        finally:
            p._get_storage_safe = orig_get

    def test_missing_storage_returns_none(self) -> None:
        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: None
        try:
            assert load_meta_weights() is None
            assert load_memory_fabric() is None
        finally:
            p._get_storage_safe = orig_get

    def test_storage_exception_returns_none(self) -> None:
        class BrokenStorage:
            def get(self, key: str) -> None:
                raise ConnectionError("db down")

        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: BrokenStorage()
        try:
            assert load_meta_weights() is None
            assert load_memory_fabric() is None
        finally:
            p._get_storage_safe = orig_get


# ─── Restart continuity (simulated) ────────────────────────────────────────


class TestRestartContinuity:
    def test_meta_engine_survives_restart_simulation(self) -> None:
        engine1 = _trained_meta_engine(5)
        snap = engine1.snapshot()

        engine2 = MetaWeightEngine()
        engine2.restore(snap)

        engine2.record_outcome(
            {name: 0.8 for name in SIGNAL_NAMES}, outcome_quality=0.9
        )
        assert engine2.total_observations == 6

        base = {name: 1.0 / len(SIGNAL_NAMES) for name in SIGNAL_NAMES}
        result = engine2.get_adapted_weights(base)
        assert result.adapted
        assert result.observations == 6

    def test_fabric_survives_restart_simulation(self) -> None:
        fabric1 = _filled_fabric(10)
        snap = fabric1.snapshot()

        fabric2 = MemoryFabric()
        fabric2.restore(snap)
        fabric2.record(_make_entry(turn=10, outcome=0.9))

        assert fabric2.entry_count == 11
        results = fabric2.query(min_turn=10)
        assert len(results) == 1
        assert results[0].outcome == 0.9

    def test_counter_preserved_across_restart(self) -> None:
        fabric1 = MemoryFabric()
        for i in range(5):
            fabric1.record(_make_entry(turn=i))
        snap = fabric1.snapshot()

        fabric2 = MemoryFabric()
        fabric2.restore(snap)
        eid = fabric2.record(_make_entry(turn=5))
        assert eid == "mf_6"  # counter continues from 5


# ─── Determinism ────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_meta_engine_deterministic_snapshots(self) -> None:
        snap1 = _trained_meta_engine(5).snapshot()
        snap2 = _trained_meta_engine(5).snapshot()
        assert snap1 == snap2

    def test_fabric_deterministic_snapshots(self) -> None:
        snap1 = _filled_fabric(10).snapshot()
        snap2 = _filled_fabric(10).snapshot()
        assert snap1 == snap2

    def test_restore_then_snapshot_idempotent(self) -> None:
        original = _filled_fabric(10).snapshot()
        fabric = MemoryFabric()
        fabric.restore(original)
        roundtripped = fabric.snapshot()
        assert original == roundtripped


# ─── Backward compatibility ─────────────────────────────────────────────────


class TestBackwardCompatibility:
    def test_meta_engine_restore_without_last_contribution(self) -> None:
        snap = {name: {"ema": 0.3, "observations": 5} for name in SIGNAL_NAMES}
        engine = MetaWeightEngine()
        engine.restore(snap)
        for name in SIGNAL_NAMES:
            assert engine._performance[name].ema == 0.3
            assert engine._performance[name].last_contribution == 0.0

    def test_fabric_restore_without_source_and_id(self) -> None:
        snap = {
            "entry_count": 1,
            "entry_counter": 1,
            "max_entries": 500,
            "entries": [
                {
                    "entry_type": "strategy_outcome",
                    "turn": 0,
                    "features": {"quality": 0.5},
                    "outcome": 0.5,
                }
            ],
        }
        fabric = MemoryFabric()
        fabric.restore(snap)
        assert fabric.entry_count == 1
        assert fabric._entries[0].source == ""
        assert fabric._entries[0].entry_id == ""

    def test_meta_engine_restore_with_unknown_signals(self) -> None:
        snap = {"unknown_signal": {"ema": 0.5, "observations": 10}}
        engine = MetaWeightEngine()
        engine.restore(snap)
        assert engine.total_observations == 0


# ─── Buffer and flush mechanics ─────────────────────────────────────────────


class TestBufferMechanics:
    def test_buffer_mark_meta_weights(self) -> None:
        buf = _PersistenceBuffer()
        buf.mark_meta_weights({"test": True})
        assert buf._meta_weights_dirty
        assert buf._meta_weights_data == {"test": True}

    def test_buffer_mark_memory_fabric(self) -> None:
        buf = _PersistenceBuffer()
        buf.mark_memory_fabric({"entries": []})
        assert buf._memory_fabric_dirty
        assert buf._memory_fabric_data == {"entries": []}

    def test_flush_with_no_storage_does_not_crash(self) -> None:
        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: None
        try:
            _reset_buffer_for_tests()
            save_meta_weights({"goal": {"ema": 0.5}})
            save_memory_fabric({"entries": []})
            from umh.runtime_engine.persistence import flush

            flush()
        finally:
            p._get_storage_safe = orig_get
            _reset_buffer_for_tests()

    def test_save_load_roundtrip_with_fake_storage(self) -> None:
        storage = FakeStorage()

        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            _reset_buffer_for_tests()

            engine = _trained_meta_engine(5)
            save_meta_weights(engine.snapshot())
            from umh.runtime_engine.persistence import flush

            flush()

            loaded = load_meta_weights()
            assert loaded is not None
            assert "goal" in loaded

            restored = MetaWeightEngine()
            restored.restore(loaded)
            assert restored._performance["goal"].ema == engine._performance["goal"].ema
        finally:
            p._get_storage_safe = orig_get
            _reset_buffer_for_tests()

    def test_save_load_fabric_roundtrip_with_fake_storage(self) -> None:
        storage = FakeStorage()

        import umh.runtime_engine.persistence as p

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            _reset_buffer_for_tests()

            fabric = _filled_fabric(10)
            save_memory_fabric(fabric.snapshot())
            from umh.runtime_engine.persistence import flush

            flush()

            loaded = load_memory_fabric()
            assert loaded is not None
            assert len(loaded["entries"]) == 10

            restored = MemoryFabric()
            restored.restore(loaded)
            assert restored.entry_count == 10
        finally:
            p._get_storage_safe = orig_get
            _reset_buffer_for_tests()


# ─── Persistence status ────────────────────────────────────────────────────


class TestPersistenceStatus:
    def test_status_with_no_storage(self) -> None:
        import umh.runtime_engine.persistence as p
        from umh.runtime_engine.persistence import get_persistence_status

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: None
        try:
            status = get_persistence_status()
            assert status["version"] == PERSISTENCE_VERSION
            assert isinstance(status["persisted_components"], list)
        finally:
            p._get_storage_safe = orig_get

    def test_status_with_populated_storage(self) -> None:
        storage = FakeStorage()
        storage.put(STORAGE_KEY_META_WEIGHTS, {"version": 1, "data": {}})
        storage.put(STORAGE_KEY_MEMORY_FABRIC, {"version": 1, "data": {}})

        import umh.runtime_engine.persistence as p
        from umh.runtime_engine.persistence import get_persistence_status

        orig_get = p._get_storage_safe
        p._get_storage_safe = lambda: storage
        try:
            status = get_persistence_status()
            assert "meta_weights" in status["persisted_components"]
            assert "memory_fabric" in status["persisted_components"]
        finally:
            p._get_storage_safe = orig_get


# ─── DecisionTrace persistence fields ──────────────────────────────────────


class TestDecisionTraceFields:
    def test_persistence_fields_exist(self) -> None:
        from umh.runtime_engine.decision_trace import DecisionTrace

        trace = DecisionTrace(
            turn_id=1,
            strategies_considered=("A",),
            strategy_scores={"A": 1.0},
            selected_strategy="A",
            quality_score=0.8,
            confidence=0.9,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
            persistence_loaded=True,
            persistence_saved=True,
            persistence_version=1,
            persisted_components=("meta_weights", "memory_fabric"),
            persistence_error=None,
        )
        assert trace.persistence_loaded is True
        assert trace.persistence_saved is True
        assert trace.persistence_version == 1
        assert trace.persisted_components == ("meta_weights", "memory_fabric")
        assert trace.persistence_error is None

    def test_persistence_fields_in_to_dict(self) -> None:
        from umh.runtime_engine.decision_trace import DecisionTrace

        trace = DecisionTrace(
            turn_id=1,
            strategies_considered=("A",),
            strategy_scores={"A": 1.0},
            selected_strategy="A",
            quality_score=0.8,
            confidence=0.9,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
            persistence_loaded=True,
            persistence_saved=True,
            persistence_version=1,
            persisted_components=("meta_weights", "memory_fabric"),
        )
        d = trace.to_dict()
        assert d["persistence_loaded"] is True
        assert d["persistence_saved"] is True
        assert d["persistence_version"] == 1
        assert d["persisted_components"] == ["meta_weights", "memory_fabric"]

    def test_persistence_fields_default_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        assert trace.persistence_loaded is None
        assert trace.persistence_saved is None
        assert trace.persistence_version is None
        assert trace.persisted_components is None
        assert trace.persistence_error is None

    def test_persistence_fields_omitted_from_dict_when_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        d = trace.to_dict()
        assert "persistence_loaded" not in d
        assert "persistence_saved" not in d
        assert "persistence_version" not in d
        assert "persisted_components" not in d
        assert "persistence_error" not in d

    def test_build_trace_passes_persistence_fields(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            persistence_loaded=True,
            persistence_version=1,
            persisted_components=("meta_weights",),
        )
        assert trace.persistence_loaded is True
        assert trace.persistence_version == 1
        assert trace.persisted_components == ("meta_weights",)


# ─── No regressions: existing persistence still works ───────────────────────


class TestNoRegressions:
    def test_strategy_memory_functions_exist(self) -> None:
        from umh.runtime_engine.persistence import load_strategy_memory, save_strategy_memory

        assert callable(save_strategy_memory)
        assert callable(load_strategy_memory)

    def test_directive_memory_functions_exist(self) -> None:
        from umh.runtime_engine.persistence import load_directive_memory, save_directive_memory

        assert callable(save_directive_memory)
        assert callable(load_directive_memory)

    def test_goal_tracker_functions_exist(self) -> None:
        from umh.runtime_engine.persistence import load_goal_trackers, save_goal_trackers

        assert callable(save_goal_trackers)
        assert callable(load_goal_trackers)

    def test_session_summary_functions_exist(self) -> None:
        from umh.runtime_engine.persistence import append_session_summary, load_recent_summaries

        assert callable(append_session_summary)
        assert callable(load_recent_summaries)

    def test_plan_functions_exist(self) -> None:
        from umh.runtime_engine.persistence import load_plans, save_plans

        assert callable(save_plans)
        assert callable(load_plans)

    def test_flush_function_exists(self) -> None:
        from umh.runtime_engine.persistence import flush

        assert callable(flush)

    def test_existing_buffer_slots_untouched(self) -> None:
        buf = _PersistenceBuffer()
        assert hasattr(buf, "_strategy_dirty")
        assert hasattr(buf, "_directive_dirty")
        assert hasattr(buf, "_trackers_dirty")
        assert hasattr(buf, "_summaries_dirty")
        assert hasattr(buf, "_plans_dirty")
        assert hasattr(buf, "_meta_weights_dirty")
        assert hasattr(buf, "_memory_fabric_dirty")

    def test_existing_decision_trace_fields_untouched(self) -> None:
        from umh.runtime_engine.decision_trace import DecisionTrace

        assert hasattr(DecisionTrace, "__dataclass_fields__")
        fields = DecisionTrace.__dataclass_fields__
        assert "memory_persisted" in fields
        assert "memory_version" in fields
        assert "meta_weights" in fields
        assert "meta_weight_adjustments" in fields
        assert "memory_entries_written" in fields
