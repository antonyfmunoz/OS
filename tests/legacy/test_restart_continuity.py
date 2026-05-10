"""Tests for restart continuity — restarted runs align with uninterrupted.

Covers:
1. State snapshot/restore produces identical behavior
2. Restart divergence reduced with persistence
3. Runtime state persistence roundtrip
4. Determinism across restart boundaries
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.benchmark_env import (
    EOSWithCorrectionSystem,
)
from umh.runtime_engine.long_horizon_benchmark import (
    NoisyStationaryScenario,
    StaticStableScenario,
    simulate_restart_continuity,
)


class TestStateSnapshotRestore:
    def test_snapshot_restore_produces_same_decisions(self):

        system1 = EOSWithCorrectionSystem()
        system1.reset()

        scenario = StaticStableScenario(seed=42)
        scenario.reset(42)

        for step in range(100):
            env = scenario.get_state(step)
            action = system1.choose_action(env)
            reward, success = scenario.evaluate_action(action, step)
            system1.observe_outcome(action, reward, success, step)

        snap = system1.get_state_snapshot()

        system2 = EOSWithCorrectionSystem()
        system2.reset()
        system2.restore_state_snapshot(snap)

        scenario.reset(42)
        for step in range(100):
            scenario.get_state(step)

        env = scenario.get_state(100)
        action1 = system1.choose_action(env)

        system2._step = 100
        system2._build_rules(env.available_actions)
        action2 = system2.choose_action(env)

        assert action1 == action2

    def test_snapshot_includes_trap_state(self):
        system = EOSWithCorrectionSystem()
        system.reset()

        scenario = StaticStableScenario(seed=42)
        scenario.reset(42)

        for step in range(50):
            env = scenario.get_state(step)
            action = system.choose_action(env)
            reward, success = scenario.evaluate_action(action, step)
            system.observe_outcome(action, reward, success, step)

        snap = system.get_state_snapshot()
        assert "trap_detector" in snap
        assert "recent_rewards" in snap
        assert "failure_streak" in snap
        assert "memory_state" in snap


class TestRestartDivergenceReduced:
    def test_corrected_restart_divergence_in_static(self):
        rc = simulate_restart_continuity(
            system_factory=EOSWithCorrectionSystem,
            scenario=StaticStableScenario(seed=42),
            horizon=500,
            seed=42,
            restart_interval=100,
        )
        assert rc.divergence < 0.10

    def test_corrected_restart_divergence_in_noisy(self):
        rc = simulate_restart_continuity(
            system_factory=EOSWithCorrectionSystem,
            scenario=NoisyStationaryScenario(seed=42),
            horizon=500,
            seed=42,
            restart_interval=100,
        )
        assert rc.divergence < 0.20


class TestPersistenceRoundtrip:
    def test_save_load_runtime_state(self):
        from contextlib import contextmanager

        class FakeStorage:
            def __init__(self):
                self._store = {}

            def put(self, key, value):
                self._store[key] = value

            def get(self, key):
                return self._store.get(key)

        @contextmanager
        def _with_storage(storage):
            import umh.runtime_engine.persistence as p

            original = p._get_storage_safe
            p._get_storage_safe = lambda: storage
            try:
                yield
            finally:
                p._get_storage_safe = original

        from umh.runtime_engine.persistence import (
            load_runtime_state,
            save_runtime_state,
            flush,
            _reset_buffer_for_tests,
        )

        _reset_buffer_for_tests()
        store = FakeStorage()

        with _with_storage(store):
            state = {
                "reward_ema": 0.85,
                "reward_peak": 0.95,
                "failure_streak": 2,
                "recent_actions": ["action_0", "action_1", "action_0"],
            }
            save_runtime_state(state)
            flush()

            loaded = load_runtime_state()
            assert loaded is not None
            assert abs(loaded["reward_ema"] - 0.85) < 1e-6
            assert loaded["failure_streak"] == 2
            assert loaded["recent_actions"] == ["action_0", "action_1", "action_0"]

    def test_load_missing_returns_none(self):
        from contextlib import contextmanager

        class EmptyStorage:
            def get(self, key):
                return None

        @contextmanager
        def _with_storage(storage):
            import umh.runtime_engine.persistence as p

            original = p._get_storage_safe
            p._get_storage_safe = lambda: storage
            try:
                yield
            finally:
                p._get_storage_safe = original

        from umh.runtime_engine.persistence import load_runtime_state, _reset_buffer_for_tests

        _reset_buffer_for_tests()
        with _with_storage(EmptyStorage()):
            loaded = load_runtime_state()
            assert loaded is None

    def test_recent_actions_capped(self):
        from contextlib import contextmanager

        class FakeStorage:
            def __init__(self):
                self._store = {}

            def put(self, key, value):
                self._store[key] = value

            def get(self, key):
                return self._store.get(key)

        @contextmanager
        def _with_storage(storage):
            import umh.runtime_engine.persistence as p

            original = p._get_storage_safe
            p._get_storage_safe = lambda: storage
            try:
                yield
            finally:
                p._get_storage_safe = original

        from umh.runtime_engine.persistence import (
            MAX_RECENT_ACTIONS,
            load_runtime_state,
            save_runtime_state,
            flush,
            _reset_buffer_for_tests,
        )

        _reset_buffer_for_tests()
        store = FakeStorage()

        with _with_storage(store):
            state = {
                "recent_actions": [f"action_{i % 4}" for i in range(200)],
            }
            save_runtime_state(state)
            flush()

            loaded = load_runtime_state()
            assert loaded is not None
            assert len(loaded["recent_actions"]) <= MAX_RECENT_ACTIONS


class TestRestartDeterminism:
    def test_identical_seeds_identical_restart_results(self):
        rc1 = simulate_restart_continuity(
            system_factory=EOSWithCorrectionSystem,
            scenario=StaticStableScenario(seed=42),
            horizon=200,
            seed=42,
        )
        rc2 = simulate_restart_continuity(
            system_factory=EOSWithCorrectionSystem,
            scenario=StaticStableScenario(seed=42),
            horizon=200,
            seed=42,
        )
        assert rc1.uninterrupted_avg_reward == rc2.uninterrupted_avg_reward
        assert rc1.restarted_avg_reward == rc2.restarted_avg_reward
        assert rc1.divergence == rc2.divergence


class TestDecisionTraceFields:
    def test_correction_fields_exist(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=0,
            trap_signal_active=True,
            trap_adjustment=0.03,
            restart_state_loaded=True,
            meta_signal_strength=0.42,
            stability_guard_active=False,
        )
        assert trace.trap_signal_active is True
        assert trace.trap_adjustment == 0.03
        assert trace.restart_state_loaded is True
        assert abs(trace.meta_signal_strength - 0.42) < 1e-6
        assert trace.stability_guard_active is False

    def test_correction_fields_in_to_dict(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=0,
            trap_signal_active=True,
            trap_adjustment=0.03,
            meta_signal_strength=0.5,
            stability_guard_active=True,
        )
        d = trace.to_dict()
        assert "trap_signal_active" in d
        assert "trap_adjustment" in d
        assert "meta_signal_strength" in d
        assert "stability_guard_active" in d

    def test_correction_fields_omitted_when_none(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=0)
        d = trace.to_dict()
        assert "trap_signal_active" not in d
        assert "trap_adjustment" not in d
        assert "restart_state_loaded" not in d
        assert "meta_signal_strength" not in d
        assert "stability_guard_active" not in d
