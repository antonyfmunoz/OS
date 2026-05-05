"""Tests for runtime state rehydration from checkpoint + event replay.

Coverage:
  1. Cold start (no checkpoint, no log)
  2. Log-only replay (no checkpoint)
  3. Checkpoint + replay
  4. Session filtering
  5. Deterministic hash after replay
  6. Drift detection (tampered mutation_hash)
  7. Partial replay after checkpoint
  8. Integration: run → log → checkpoint → restart → hydrate → compare
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")

from umh.substrate.checkpoint_runtime import CheckpointRuntime, compute_snapshot_hash
from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.runtime_bootstrap import (
    _reset_for_testing,
    get_checkpoint_runtime,
    get_event_log_runtime,
    get_runtime_state_store,
    initialize_runtime_state,
)
from umh.substrate.runtime_rehydration import (
    RuntimeRehydrationResult,
    hydrate_runtime_state,
)
from umh.substrate.runtime_state_store import RuntimeStateStore


# ─── Helpers ────────────────────────────────────────────────────────────


def _make_runtimes(
    tmp_path: Path,
) -> tuple[EventLogRuntime, CheckpointRuntime, RuntimeStateStore]:
    """Create isolated runtimes backed by temp directory."""
    log = EventLogRuntime(log_path=tmp_path / "events.jsonl")
    cp = CheckpointRuntime(checkpoint_dir=tmp_path / "checkpoints")
    store = RuntimeStateStore()
    return log, cp, store


def _append_event(
    log: EventLogRuntime,
    *,
    seq_session: str = "test-session",
    event_type: str = "test_event",
    mutations: list[dict] | None = None,
) -> str:
    """Append an event and return its event_id."""
    result = log.append(
        event_type=event_type,
        session_name=seq_session,
        source="test",
        state_mutations=mutations or [],
    )
    assert result.ok, f"append failed: {result.error}"
    return result.event_id


# ─── Test cases ─────────────────────────────────────────────────────────


class TestRuntimeRehydration:
    """Unit tests for hydrate_runtime_state()."""

    def test_cold_start_no_checkpoint_no_log(self, tmp_path: Path) -> None:
        """Empty system: no checkpoint, no events → empty state."""
        log, cp, store = _make_runtimes(tmp_path)

        result = hydrate_runtime_state(log, cp, store)

        assert result.checkpoint_loaded is False
        assert result.checkpoint_sequence is None
        assert result.events_replayed == 0
        assert result.drift_detected is False
        assert result.drift_details == []
        assert result.final_state_hash != ""  # hash of empty dict
        assert store.snapshot() == {}

    def test_log_only_replay(self, tmp_path: Path) -> None:
        """Replay from event log with no checkpoint (cold start from seq 0)."""
        log, cp, store = _make_runtimes(tmp_path)

        # Write 3 events with mutations
        _append_event(
            log,
            event_type="finalization_succeeded",
            mutations=[{"op": "SET", "key": "status", "value": "finalized"}],
        )
        _append_event(
            log,
            event_type="publication_confirmed",
            mutations=[{"op": "SET", "key": "published", "value": True}],
        )
        _append_event(
            log,
            event_type="clear_confirmed",
            mutations=[{"op": "INCREMENT", "key": "generation"}],
        )

        result = hydrate_runtime_state(log, cp, store)

        assert result.checkpoint_loaded is False
        assert result.checkpoint_sequence is None
        assert result.events_replayed == 3
        assert result.drift_detected is False
        assert store.get("status") == "finalized"
        assert store.get("published") is True
        assert store.get("generation") == 1

    def test_checkpoint_plus_replay(self, tmp_path: Path) -> None:
        """Load checkpoint, then replay only subsequent events."""
        log, cp, store = _make_runtimes(tmp_path)

        # Simulate pre-checkpoint state
        _append_event(
            log,
            event_type="evt_0",
            mutations=[{"op": "SET", "key": "base", "value": "from_log"}],
        )
        _append_event(
            log,
            event_type="evt_1",
            mutations=[{"op": "SET", "key": "count", "value": 10}],
        )

        # Write checkpoint at seq 1
        cp.write_checkpoint(
            sequence_number=1,
            event_id="evt_cp",
            state_snapshot={"base": "from_log", "count": 10},
        )

        # Events after checkpoint
        _append_event(
            log,
            event_type="evt_2",
            mutations=[{"op": "INCREMENT", "key": "count", "value": 5}],
        )
        _append_event(
            log,
            event_type="evt_3",
            mutations=[{"op": "SET", "key": "final", "value": True}],
        )

        result = hydrate_runtime_state(log, cp, store)

        assert result.checkpoint_loaded is True
        assert result.checkpoint_sequence == 1
        assert result.events_replayed == 2  # only evt_2 and evt_3
        assert store.get("base") == "from_log"  # from checkpoint
        assert store.get("count") == 15  # 10 from checkpoint + 5 from replay
        assert store.get("final") is True  # from replay

    def test_session_filtering(self, tmp_path: Path) -> None:
        """Only replay events matching the requested session_name."""
        log, cp, store = _make_runtimes(tmp_path)

        # Events from two different sessions
        _append_event(
            log,
            seq_session="session-A",
            event_type="evt_a",
            mutations=[{"op": "SET", "key": "owner", "value": "A"}],
        )
        _append_event(
            log,
            seq_session="session-B",
            event_type="evt_b",
            mutations=[{"op": "SET", "key": "owner", "value": "B"}],
        )
        _append_event(
            log,
            seq_session="session-A",
            event_type="evt_a2",
            mutations=[{"op": "INCREMENT", "key": "a_count"}],
        )

        result = hydrate_runtime_state(log, cp, store, session_name="session-A")

        assert result.events_replayed == 2  # only session-A events
        assert store.get("owner") == "A"
        assert store.get("a_count") == 1

    def test_deterministic_hash(self, tmp_path: Path) -> None:
        """Same events always produce the same final_state_hash."""
        hashes: list[str] = []

        for _ in range(3):
            log, cp, store = _make_runtimes(tmp_path / f"run_{len(hashes)}")
            _append_event(
                log,
                mutations=[{"op": "SET", "key": "x", "value": 42}],
            )
            _append_event(
                log,
                mutations=[{"op": "SET", "key": "y", "value": "hello"}],
            )
            result = hydrate_runtime_state(log, cp, store)
            hashes.append(result.final_state_hash)

        assert len(set(hashes)) == 1, f"Non-deterministic hashes: {hashes}"

    def test_drift_detection_tampered_hash(self, tmp_path: Path) -> None:
        """Drift detection catches events with wrong mutation_hash."""
        log, cp, store = _make_runtimes(tmp_path)

        # Write a normal event
        _append_event(
            log,
            event_type="good_event",
            mutations=[{"op": "SET", "key": "ok", "value": True}],
        )

        # Manually write a tampered event to the log file
        tampered_line = json.dumps(
            {
                "sequence_number": 1,
                "event_id": "evt_tampered",
                "causal_event_id": None,
                "session_name": "test-session",
                "run_id": None,
                "event_type": "tampered_event",
                "source": "test",
                "event_time": "2026-01-01T00:00:00+00:00",
                "log_time": "2026-01-01T00:00:00+00:00",
                "payload": {},
                "state_mutations": [{"op": "SET", "key": "bad", "value": True}],
                "mutation_hash": "0000000000000000000000000000000000000000000000000000000000000000",
                "metadata": {},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        with open(tmp_path / "events.jsonl", "a") as f:
            f.write(tampered_line + "\n")

        # Force counter recovery so the runtime knows about the new line
        log.recover_counter_from_disk()

        result = hydrate_runtime_state(log, cp, store, verify=True)

        assert result.drift_detected is True
        assert len(result.drift_details) == 1
        assert result.drift_details[0]["event_id"] == "evt_tampered"
        assert result.drift_details[0]["sequence_number"] == 1
        # State was still applied despite drift
        assert store.get("ok") is True
        assert store.get("bad") is True

    def test_partial_replay_after_checkpoint(self, tmp_path: Path) -> None:
        """Checkpoint at seq 5, events 0-9 on disk → only 6-9 replayed."""
        log, cp, store = _make_runtimes(tmp_path)

        # Write 10 events
        for i in range(10):
            _append_event(
                log,
                event_type=f"evt_{i}",
                mutations=[{"op": "SET", "key": f"k{i}", "value": i}],
            )

        # Checkpoint captures state up through seq 5
        checkpoint_state = {f"k{i}": i for i in range(6)}
        cp.write_checkpoint(
            sequence_number=5,
            event_id="evt_5",
            state_snapshot=checkpoint_state,
        )

        result = hydrate_runtime_state(log, cp, store)

        assert result.checkpoint_loaded is True
        assert result.checkpoint_sequence == 5
        assert result.events_replayed == 4  # seq 6, 7, 8, 9

        # All 10 keys present (6 from checkpoint + 4 from replay)
        for i in range(10):
            assert store.get(f"k{i}") == i

    def test_no_verify_skips_hash_check(self, tmp_path: Path) -> None:
        """When verify=False, mutation_hash mismatches are not reported."""
        log, cp, store = _make_runtimes(tmp_path)

        _append_event(log, mutations=[{"op": "SET", "key": "x", "value": 1}])

        # Tamper the log
        tampered_line = json.dumps(
            {
                "sequence_number": 1,
                "event_id": "evt_bad",
                "causal_event_id": None,
                "session_name": "test-session",
                "run_id": None,
                "event_type": "bad",
                "source": "test",
                "event_time": "2026-01-01T00:00:00+00:00",
                "log_time": "2026-01-01T00:00:00+00:00",
                "payload": {},
                "state_mutations": [{"op": "SET", "key": "y", "value": 2}],
                "mutation_hash": "FAKE_HASH",
                "metadata": {},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        with open(tmp_path / "events.jsonl", "a") as f:
            f.write(tampered_line + "\n")
        log.recover_counter_from_disk()

        result = hydrate_runtime_state(log, cp, store, verify=False)

        assert result.drift_detected is False
        assert result.drift_details == []
        assert store.get("y") == 2  # mutation still applied

    def test_events_with_empty_mutations_counted(self, tmp_path: Path) -> None:
        """Events with no state_mutations still count as replayed."""
        log, cp, store = _make_runtimes(tmp_path)

        _append_event(log, event_type="info_only", mutations=[])
        _append_event(
            log,
            event_type="with_mutation",
            mutations=[{"op": "SET", "key": "a", "value": 1}],
        )

        result = hydrate_runtime_state(log, cp, store)

        assert result.events_replayed == 2
        assert store.get("a") == 1


class TestRuntimeRehydrationIntegration:
    """Integration test: run → log → checkpoint → restart → hydrate → compare."""

    def setup_method(self) -> None:
        _reset_for_testing()

    def test_full_cycle_restart_recovery(self, tmp_path: Path) -> None:
        """Simulate a full run, checkpoint, restart, and verify state matches."""
        log_file = tmp_path / "events.jsonl"
        cp_dir = tmp_path / "checkpoints"
        _reset_for_testing(log_path=log_file, checkpoint_dir=cp_dir)

        # ── Phase A: Original run ──────────────────────────────────
        log = get_event_log_runtime()
        cp = get_checkpoint_runtime()
        store = get_runtime_state_store()

        # Simulate lifecycle events with state mutations
        mutations_1 = [
            {"op": "SET", "key": "status", "value": "running"},
            {"op": "SET", "key": "session", "value": "cc-vps"},
        ]
        r1 = log.append(
            event_type="run_started",
            session_name="cc-vps",
            source="lifecycle_manager",
            state_mutations=mutations_1,
        )
        assert r1.ok
        store.apply_mutations(mutations_1)

        mutations_2 = [
            {"op": "SET", "key": "status", "value": "finalized"},
            {"op": "INCREMENT", "key": "generation"},
        ]
        r2 = log.append(
            event_type="finalization_succeeded",
            session_name="cc-vps",
            source="watcher",
            causal_event_id=r1.event_id,
            state_mutations=mutations_2,
        )
        assert r2.ok
        store.apply_mutations(mutations_2)

        # Checkpoint at seq 1
        snap = store.snapshot()
        cp_result = cp.write_checkpoint(
            sequence_number=r2.sequence_number,
            event_id=r2.event_id,
            state_snapshot=snap,
        )
        assert cp_result.ok

        # More events after checkpoint
        mutations_3 = [
            {"op": "SET", "key": "published", "value": True},
        ]
        r3 = log.append(
            event_type="publication_confirmed",
            session_name="cc-vps",
            source="discord_bridge",
            causal_event_id=r2.event_id,
            state_mutations=mutations_3,
        )
        assert r3.ok
        store.apply_mutations(mutations_3)

        mutations_4 = [
            {"op": "SET", "key": "clear_status", "value": "confirmed"},
        ]
        r4 = log.append(
            event_type="clear_confirmed",
            session_name="cc-vps",
            source="session_control",
            causal_event_id=r3.event_id,
            state_mutations=mutations_4,
        )
        assert r4.ok
        store.apply_mutations(mutations_4)

        # Capture the expected final state
        original_state = store.snapshot()
        original_hash = store.compute_state_hash()

        # ── Phase B: Simulate restart ──────────────────────────────
        # Reset singletons to simulate process restart
        _reset_for_testing(log_path=log_file, checkpoint_dir=cp_dir)

        # Hydrate from disk
        recovered_store, hydration_result = initialize_runtime_state(
            session_name="cc-vps"
        )

        # ── Assertions ─────────────────────────────────────────────
        assert hydration_result.checkpoint_loaded is True
        assert hydration_result.checkpoint_sequence == 1
        assert hydration_result.events_replayed == 2  # seq 2 and 3
        assert hydration_result.drift_detected is False

        # Recovered state matches original
        recovered_state = recovered_store.snapshot()
        assert recovered_state == original_state

        # Hash matches
        assert hydration_result.final_state_hash == original_hash

        # Specific values correct
        assert recovered_store.get("status") == "finalized"
        assert recovered_store.get("session") == "cc-vps"
        assert recovered_store.get("generation") == 1
        assert recovered_store.get("published") is True
        assert recovered_store.get("clear_status") == "confirmed"

    def test_cold_start_via_bootstrap(self, tmp_path: Path) -> None:
        """initialize_runtime_state works on a completely empty system."""
        _reset_for_testing(
            log_path=tmp_path / "events.jsonl",
            checkpoint_dir=tmp_path / "checkpoints",
        )

        store, result = initialize_runtime_state()

        assert result.checkpoint_loaded is False
        assert result.events_replayed == 0
        assert result.drift_detected is False
        assert store.snapshot() == {}


class TestRuntimeStateStoreExtensions:
    """Tests for the new apply_event_envelope() and compute_state_hash() methods."""

    def test_apply_event_envelope(self) -> None:
        """apply_event_envelope extracts and applies mutations."""
        from umh.substrate.event_log_runtime import EventEnvelope

        store = RuntimeStateStore()
        envelope = EventEnvelope(
            sequence_number=0,
            event_id="evt_test",
            causal_event_id=None,
            session_name="test",
            run_id=None,
            event_type="test",
            source="test",
            event_time="2026-01-01T00:00:00+00:00",
            log_time="2026-01-01T00:00:00+00:00",
            state_mutations=[
                {"op": "SET", "key": "a", "value": 1},
                {"op": "INCREMENT", "key": "b", "value": 5},
            ],
        )

        store.apply_event_envelope(envelope)

        assert store.get("a") == 1
        assert store.get("b") == 5

    def test_apply_event_envelope_empty_mutations(self) -> None:
        """apply_event_envelope no-ops on empty mutations."""
        from umh.substrate.event_log_runtime import EventEnvelope

        store = RuntimeStateStore()
        store.set("existing", "value")

        envelope = EventEnvelope(
            sequence_number=0,
            event_id="evt_noop",
            causal_event_id=None,
            session_name="test",
            run_id=None,
            event_type="info",
            source="test",
            event_time="2026-01-01T00:00:00+00:00",
            log_time="2026-01-01T00:00:00+00:00",
            state_mutations=[],
        )

        store.apply_event_envelope(envelope)
        assert store.get("existing") == "value"

    def test_compute_state_hash_deterministic(self) -> None:
        """Same state always produces the same hash."""
        store1 = RuntimeStateStore()
        store1.set("x", 1)
        store1.set("y", [2, 3])

        store2 = RuntimeStateStore()
        store2.set("y", [2, 3])
        store2.set("x", 1)  # different insertion order

        assert store1.compute_state_hash() == store2.compute_state_hash()

    def test_compute_state_hash_changes_on_mutation(self) -> None:
        """Hash changes when state changes."""
        store = RuntimeStateStore()
        store.set("x", 1)
        hash_before = store.compute_state_hash()

        store.set("x", 2)
        hash_after = store.compute_state_hash()

        assert hash_before != hash_after

    def test_compute_state_hash_length(self) -> None:
        """Hash is 16 hex characters."""
        store = RuntimeStateStore()
        store.set("data", {"nested": True})
        h = store.compute_state_hash()
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)
