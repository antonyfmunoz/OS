"""Tests for the event-driven scheduler and lifecycle handlers.

Coverage:
  1. Basic event routing
  2. Guard blocking
  3. Event chaining (A → B → C)
  4. No duplicate execution (dedup)
  5. State mutations applied correctly
  6. Emitted events logged + replayable
  7. Full lifecycle via events only
  8. Integration: event-driven vs legacy path equivalence
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")

from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.event_scheduler import (
    EventScheduler,
    ExecutionResult,
    RunResult,
    SchedulerEvent,
)
from umh.substrate.lifecycle_handlers import (
    create_lifecycle_scheduler,
    guard_clear_not_requested,
    guard_not_finalized,
    guard_terminal_ready,
    handle_clear_confirmed,
    handle_clear_requested,
    handle_finalization_succeeded,
    handle_publication_confirmed,
    handle_run_completion_proposed,
    handle_terminal_seal,
)
from umh.substrate.runtime_state_store import RuntimeStateStore


# ─── Helpers ────────────────────────────────────────────────────────────


def _make_scheduler(
    tmp_path: Path | None = None,
    with_log: bool = False,
) -> tuple[EventScheduler, RuntimeStateStore, EventLogRuntime | None]:
    """Create an isolated scheduler + store, optionally with event log."""
    store = RuntimeStateStore()
    log = None
    if with_log and tmp_path is not None:
        log = EventLogRuntime(log_path=tmp_path / "events.jsonl")
    scheduler = EventScheduler(store=store, event_log=log)
    return scheduler, store, log


def _simple_handler(store: RuntimeStateStore, event: SchedulerEvent) -> ExecutionResult:
    """Handler that sets a key to mark it was called."""
    return ExecutionResult(
        mutations=[{"op": "SET", "key": f"handled_{event.event_type}", "value": True}],
    )


def _chaining_handler(
    next_event_type: str,
) -> callable:
    """Factory: returns a handler that emits a follow-up event."""

    def handler(store: RuntimeStateStore, event: SchedulerEvent) -> ExecutionResult:
        return ExecutionResult(
            mutations=[
                {"op": "SET", "key": f"handled_{event.event_type}", "value": True}
            ],
            emitted_events=[
                SchedulerEvent(
                    event_type=next_event_type,
                    session_name=event.session_name,
                    source=event.source,
                )
            ],
        )

    return handler


# ─── Core Scheduler Tests ──────────────────────────────────────────────


class TestEventScheduler:
    """Tests for EventScheduler core mechanics."""

    def test_basic_routing(self) -> None:
        """Events route to their subscribed handlers."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        scheduler.subscribe("test_event", _simple_handler, name="basic")
        scheduler.emit(
            SchedulerEvent(event_type="test_event", session_name="s1", source="test")
        )

        result = scheduler.run()

        assert result.events_processed == 1
        assert result.total_handlers_called == 1
        assert store.get("handled_test_event") is True

    def test_no_subscribers_no_error(self) -> None:
        """Events with no subscribers are processed without error."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        scheduler.emit(
            SchedulerEvent(event_type="unknown_event", session_name="s1", source="test")
        )
        result = scheduler.run()

        assert result.events_processed == 1
        assert result.total_handlers_called == 0

    def test_guard_blocking(self) -> None:
        """Guard returning False prevents handler execution."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        def always_block(s: RuntimeStateStore, e: SchedulerEvent) -> bool:
            return False

        scheduler.subscribe(
            "guarded_event", _simple_handler, guard=always_block, name="blocked"
        )
        scheduler.emit(
            SchedulerEvent(event_type="guarded_event", session_name="s1", source="test")
        )

        result = scheduler.run()

        assert result.events_processed == 1
        assert result.total_handlers_called == 0
        assert store.get("handled_guarded_event") is None

    def test_guard_passing(self) -> None:
        """Guard returning True allows handler execution."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        def always_pass(s: RuntimeStateStore, e: SchedulerEvent) -> bool:
            return True

        scheduler.subscribe(
            "guarded_event", _simple_handler, guard=always_pass, name="passed"
        )
        scheduler.emit(
            SchedulerEvent(event_type="guarded_event", session_name="s1", source="test")
        )

        result = scheduler.run()

        assert result.events_processed == 1
        assert result.total_handlers_called == 1
        assert store.get("handled_guarded_event") is True

    def test_event_chaining_a_b_c(self) -> None:
        """Handler emitting events creates a chain: A → B → C."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        scheduler.subscribe("event_a", _chaining_handler("event_b"), name="a→b")
        scheduler.subscribe("event_b", _chaining_handler("event_c"), name="b→c")
        scheduler.subscribe("event_c", _simple_handler, name="c_terminal")

        scheduler.emit(
            SchedulerEvent(event_type="event_a", session_name="s1", source="test")
        )
        result = scheduler.run()

        assert result.events_processed == 3
        assert store.get("handled_event_a") is True
        assert store.get("handled_event_b") is True
        assert store.get("handled_event_c") is True

    def test_dedup_prevents_double_execution(self) -> None:
        """Same event_id emitted twice is only processed once."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        call_count = {"n": 0}

        def counting_handler(
            s: RuntimeStateStore, e: SchedulerEvent
        ) -> ExecutionResult:
            call_count["n"] += 1
            return ExecutionResult(
                mutations=[{"op": "INCREMENT", "key": "count"}],
            )

        scheduler.subscribe("counted_event", counting_handler, name="counter")

        event = SchedulerEvent(
            event_type="counted_event",
            session_name="s1",
            source="test",
            event_id="fixed_id_001",
        )
        scheduler.emit(event)
        scheduler.emit(event)  # duplicate

        result = scheduler.run()

        assert result.events_processed == 1
        assert result.events_skipped_dedup == 1
        assert call_count["n"] == 1
        assert store.get("count") == 1

    def test_multiple_subscribers_same_event(self) -> None:
        """Multiple handlers subscribed to same event type all execute."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        def handler_a(s: RuntimeStateStore, e: SchedulerEvent) -> ExecutionResult:
            return ExecutionResult(
                mutations=[{"op": "SET", "key": "a_ran", "value": True}]
            )

        def handler_b(s: RuntimeStateStore, e: SchedulerEvent) -> ExecutionResult:
            return ExecutionResult(
                mutations=[{"op": "SET", "key": "b_ran", "value": True}]
            )

        scheduler.subscribe("multi_event", handler_a, name="handler_a")
        scheduler.subscribe("multi_event", handler_b, name="handler_b")
        scheduler.emit(
            SchedulerEvent(event_type="multi_event", session_name="s1", source="test")
        )

        result = scheduler.run()

        assert result.total_handlers_called == 2
        assert store.get("a_ran") is True
        assert store.get("b_ran") is True

    def test_handler_exception_does_not_crash_scheduler(self) -> None:
        """A failing handler is caught; other handlers still run."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        def bad_handler(s: RuntimeStateStore, e: SchedulerEvent) -> ExecutionResult:
            raise RuntimeError("handler exploded")

        scheduler.subscribe("event", bad_handler, name="bad")
        scheduler.subscribe("event", _simple_handler, name="good")
        scheduler.emit(
            SchedulerEvent(event_type="event", session_name="s1", source="test")
        )

        result = scheduler.run()

        assert result.total_handler_failures == 1
        assert result.total_handlers_called == 1  # good handler
        assert store.get("handled_event") is True

    def test_state_mutations_applied_correctly(self) -> None:
        """Mutations from handlers are applied to the store."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        def complex_handler(s: RuntimeStateStore, e: SchedulerEvent) -> ExecutionResult:
            return ExecutionResult(
                mutations=[
                    {"op": "SET", "key": "status", "value": "finalized"},
                    {"op": "INCREMENT", "key": "gen"},
                    {"op": "APPEND_UNIQUE", "key": "tags", "value": "done"},
                ]
            )

        scheduler.subscribe("complex", complex_handler, name="complex")
        scheduler.emit(
            SchedulerEvent(event_type="complex", session_name="s1", source="test")
        )
        scheduler.run()

        assert store.get("status") == "finalized"
        assert store.get("gen") == 1
        assert store.get("tags") == ["done"]

    def test_emitted_events_logged_to_event_log(self, tmp_path: Path) -> None:
        """When event_log is provided, mutations are written to it."""
        scheduler, store, log = _make_scheduler(tmp_path, with_log=True)

        def mutating_handler(
            s: RuntimeStateStore, e: SchedulerEvent
        ) -> ExecutionResult:
            return ExecutionResult(
                mutations=[{"op": "SET", "key": "logged", "value": True}]
            )

        scheduler.subscribe("log_test", mutating_handler, name="logger")
        scheduler.emit(
            SchedulerEvent(
                event_type="log_test", session_name="test-session", source="test"
            )
        )
        scheduler.run()

        events = log.read_all()
        assert len(events) == 1
        assert events[0].event_type == "log_test"
        assert events[0].state_mutations == [
            {"op": "SET", "key": "logged", "value": True}
        ]

    def test_circuit_breaker(self) -> None:
        """Circuit breaker prevents infinite loops."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)
        scheduler._max_iterations = 5

        # Self-referencing handler that always emits another event
        def infinite_handler(
            s: RuntimeStateStore, e: SchedulerEvent
        ) -> ExecutionResult:
            return ExecutionResult(
                mutations=[{"op": "INCREMENT", "key": "loops"}],
                emitted_events=[
                    SchedulerEvent(
                        event_type="loop_event", session_name="s1", source="test"
                    )
                ],
            )

        scheduler.subscribe("loop_event", infinite_handler, name="looper")
        scheduler.emit(
            SchedulerEvent(event_type="loop_event", session_name="s1", source="test")
        )

        result = scheduler.run()

        # Should stop at circuit breaker, not run forever
        assert result.events_processed <= 5
        assert store.get("loops") <= 5

    def test_reset_clears_everything(self) -> None:
        """reset() clears queue, dedup, and subscribers."""
        store = RuntimeStateStore()
        scheduler = EventScheduler(store=store)

        scheduler.subscribe("event", _simple_handler, name="sub")
        scheduler.emit(
            SchedulerEvent(event_type="event", session_name="s1", source="test")
        )
        scheduler.reset()

        assert scheduler.pending_count() == 0
        # Subscriber also cleared — running should process nothing
        scheduler.emit(
            SchedulerEvent(event_type="event", session_name="s1", source="test")
        )
        result = scheduler.run()
        assert result.total_handlers_called == 0


# ─── Lifecycle Handler Tests ───────────────────────────────────────────


class TestLifecycleHandlers:
    """Tests for individual lifecycle handlers and their guards."""

    def test_guard_not_finalized_blocks_when_finalized(self) -> None:
        """guard_not_finalized returns False when already finalized."""
        store = RuntimeStateStore()
        store.set("finalization_status", "succeeded")
        event = SchedulerEvent(event_type="test", session_name="s", source="t")
        assert guard_not_finalized(store, event) is False

    def test_guard_not_finalized_passes_when_not_finalized(self) -> None:
        """guard_not_finalized returns True when not finalized."""
        store = RuntimeStateStore()
        event = SchedulerEvent(event_type="test", session_name="s", source="t")
        assert guard_not_finalized(store, event) is True

    def test_guard_clear_not_requested_blocks(self) -> None:
        """guard_clear_not_requested returns False when clear requested."""
        store = RuntimeStateStore()
        store.set("clear_status", "requested")
        event = SchedulerEvent(event_type="test", session_name="s", source="t")
        assert guard_clear_not_requested(store, event) is False

    def test_guard_terminal_ready_all_conditions_met(self) -> None:
        """guard_terminal_ready passes when publication + clear both done."""
        store = RuntimeStateStore()
        store.set("publication_confirmed", True)
        store.set("clear_status", "confirmed")
        event = SchedulerEvent(event_type="test", session_name="s", source="t")
        assert guard_terminal_ready(store, event) is True

    def test_guard_terminal_ready_blocks_without_publication(self) -> None:
        """guard_terminal_ready blocks when publication not confirmed."""
        store = RuntimeStateStore()
        store.set("clear_status", "confirmed")
        event = SchedulerEvent(event_type="test", session_name="s", source="t")
        assert guard_terminal_ready(store, event) is False

    def test_guard_terminal_ready_allows_no_clear_policy(self) -> None:
        """guard_terminal_ready passes with no_clear_policy override."""
        store = RuntimeStateStore()
        store.set("publication_confirmed", True)
        store.set("no_clear_policy", True)
        event = SchedulerEvent(event_type="test", session_name="s", source="t")
        assert guard_terminal_ready(store, event) is True

    def test_handle_finalization_succeeded(self) -> None:
        """Finalization handler sets state and emits publication."""
        store = RuntimeStateStore()
        event = SchedulerEvent(
            event_type="finalization_succeeded",
            session_name="cc-vps",
            source="watcher",
            run_id="run_001",
        )
        result = handle_finalization_succeeded(store, event)

        assert any(m["key"] == "finalization_status" for m in result.mutations)
        assert len(result.emitted_events) == 1
        assert result.emitted_events[0].event_type == "publication_confirmed"

    def test_handle_publication_confirmed(self) -> None:
        """Publication handler sets state and emits clear_requested."""
        store = RuntimeStateStore()
        event = SchedulerEvent(
            event_type="publication_confirmed",
            session_name="cc-vps",
            source="discord",
            run_id="run_001",
        )
        result = handle_publication_confirmed(store, event)

        assert any(
            m["key"] == "publication_confirmed" and m["value"] is True
            for m in result.mutations
        )
        assert len(result.emitted_events) == 1
        assert result.emitted_events[0].event_type == "clear_requested"

    def test_handle_terminal_seal_no_followup(self) -> None:
        """Terminal seal handler emits no follow-up events."""
        store = RuntimeStateStore()
        event = SchedulerEvent(
            event_type="terminal_seal_applied",
            session_name="cc-vps",
            source="lifecycle",
        )
        result = handle_terminal_seal(store, event)

        assert any(
            m["key"] == "terminally_finalized" and m["value"] is True
            for m in result.mutations
        )
        assert result.emitted_events == []


# ─── Full Lifecycle Chain Test ─────────────────────────────────────────


class TestLifecycleEventChain:
    """Test the complete lifecycle chain driven purely by events."""

    def test_full_lifecycle_via_events(self, tmp_path: Path) -> None:
        """Single event triggers the full chain via event-driven execution.

        Chain: finalization_succeeded → publication_confirmed →
               clear_requested → clear_confirmed → terminal_seal_applied
        """
        store = RuntimeStateStore()
        log = EventLogRuntime(log_path=tmp_path / "events.jsonl")
        scheduler = create_lifecycle_scheduler(store=store, event_log=log)

        # Kick off the chain with a single event
        scheduler.emit(
            SchedulerEvent(
                event_type="finalization_succeeded",
                session_name="cc-vps",
                source="watcher",
                run_id="run_001",
            )
        )

        result = scheduler.run()

        # All 5 events in the chain should have been processed
        assert result.events_processed == 5

        # Final state should reflect complete lifecycle
        assert store.get("finalization_status") == "succeeded"
        assert store.get("status") == "cleared"
        assert store.get("publication_confirmed") is True
        assert store.get("clear_status") == "confirmed"
        assert store.get("terminally_finalized") is True

        # All events should be in the log
        events = log.read_all()
        event_types = [e.event_type for e in events]
        assert "finalization_succeeded" in event_types
        assert "publication_confirmed" in event_types
        assert "clear_requested" in event_types
        assert "clear_confirmed" in event_types
        assert "terminal_seal_applied" in event_types

    def test_lifecycle_chain_structural_determinism(self, tmp_path: Path) -> None:
        """Running the chain twice produces identical structural state.

        Timestamps vary between runs, so we compare the lifecycle-
        significant keys (not the full hash). This proves the state
        machine transitions are deterministic.
        """
        snapshots = []

        for i in range(2):
            store = RuntimeStateStore()
            log = EventLogRuntime(log_path=tmp_path / f"events_{i}.jsonl")
            scheduler = create_lifecycle_scheduler(store=store, event_log=log)

            scheduler.emit(
                SchedulerEvent(
                    event_type="finalization_succeeded",
                    session_name="cc-vps",
                    source="watcher",
                    run_id="run_001",
                )
            )
            scheduler.run()
            snapshots.append(store.snapshot())

        # Structural keys must be identical
        structural_keys = [
            "finalization_status",
            "status",
            "publication_confirmed",
            "clear_status",
            "terminally_finalized",
        ]
        for key in structural_keys:
            assert snapshots[0][key] == snapshots[1][key], (
                f"Non-deterministic on '{key}': "
                f"{snapshots[0][key]} != {snapshots[1][key]}"
            )

    def test_chain_replayable_from_log(self, tmp_path: Path) -> None:
        """State can be reconstructed by replaying the logged events."""
        from umh.substrate.runtime_rehydration import hydrate_runtime_state
        from umh.substrate.checkpoint_runtime import CheckpointRuntime

        # Run the lifecycle chain
        store_original = RuntimeStateStore()
        log = EventLogRuntime(log_path=tmp_path / "events.jsonl")
        scheduler = create_lifecycle_scheduler(store=store_original, event_log=log)

        scheduler.emit(
            SchedulerEvent(
                event_type="finalization_succeeded",
                session_name="cc-vps",
                source="watcher",
                run_id="run_001",
            )
        )
        scheduler.run()
        original_hash = store_original.compute_state_hash()

        # Replay from the event log into a fresh store
        store_replayed = RuntimeStateStore()
        cp = CheckpointRuntime(checkpoint_dir=tmp_path / "checkpoints")
        # Read the same log file, no checkpoint
        replay_log = EventLogRuntime(log_path=tmp_path / "events.jsonl")

        rehydration_result = hydrate_runtime_state(replay_log, cp, store_replayed)

        replayed_hash = store_replayed.compute_state_hash()

        assert replayed_hash == original_hash
        assert rehydration_result.drift_detected is False
        assert store_replayed.get("terminally_finalized") is True

    def test_guard_prevents_double_finalization(self, tmp_path: Path) -> None:
        """Emitting finalization_succeeded twice only processes it once."""
        store = RuntimeStateStore()
        scheduler = create_lifecycle_scheduler(store=store)

        event = SchedulerEvent(
            event_type="finalization_succeeded",
            session_name="cc-vps",
            source="watcher",
        )

        # First chain runs fully
        scheduler.emit(event)
        result1 = scheduler.run()
        assert result1.events_processed >= 5

        # Second emission — guard blocks because already finalized
        scheduler.emit(
            SchedulerEvent(
                event_type="finalization_succeeded",
                session_name="cc-vps",
                source="watcher",
                event_id="different_id",  # different event_id to bypass dedup
            )
        )
        result2 = scheduler.run()

        # The finalization handler should be blocked by guard_not_published
        # since publication is already confirmed
        assert result2.events_processed == 1
        assert result2.total_handlers_called == 0  # guard blocked it


class TestLifecycleEventDrivenIntegration:
    """Integration: event-driven path produces equivalent state to manual."""

    def test_event_driven_matches_manual_state(self, tmp_path: Path) -> None:
        """State from event-driven chain matches manually-applied mutations.

        This proves the event system can replace the legacy imperative path.
        """
        # ── Path A: Manual (simulating legacy) ────────────────────
        store_manual = RuntimeStateStore()
        store_manual.apply_mutations(
            [
                {"op": "SET", "key": "finalization_status", "value": "succeeded"},
                {"op": "SET", "key": "status", "value": "finalized"},
            ]
        )
        store_manual.apply_mutations(
            [
                {"op": "SET", "key": "publication_confirmed", "value": True},
            ]
        )
        store_manual.apply_mutations(
            [
                {"op": "SET", "key": "clear_status", "value": "requested"},
                {"op": "SET", "key": "status", "value": "clear_requested"},
            ]
        )
        store_manual.apply_mutations(
            [
                {"op": "SET", "key": "clear_status", "value": "confirmed"},
                {"op": "SET", "key": "status", "value": "cleared"},
            ]
        )
        store_manual.apply_mutations(
            [
                {"op": "SET", "key": "terminally_finalized", "value": True},
            ]
        )

        # ── Path B: Event-driven ──────────────────────────────────
        store_event = RuntimeStateStore()
        scheduler = create_lifecycle_scheduler(store=store_event)

        scheduler.emit(
            SchedulerEvent(
                event_type="finalization_succeeded",
                session_name="cc-vps",
                source="watcher",
            )
        )
        scheduler.run()

        # ── Compare structural keys ───────────────────────────────
        # Both paths should agree on these lifecycle state keys
        keys_to_compare = [
            "finalization_status",
            "status",
            "publication_confirmed",
            "clear_status",
            "terminally_finalized",
        ]

        for key in keys_to_compare:
            manual_val = store_manual.get(key)
            event_val = store_event.get(key)
            assert manual_val == event_val, (
                f"Mismatch on '{key}': manual={manual_val}, event={event_val}"
            )
