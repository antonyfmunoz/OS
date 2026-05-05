"""Replay determinism proof — event log captures enough to rebuild state.

Validates three properties of the event-sourced execution fabric:

1. Replay produces the same state hash as the original run.
2. Replay is itself idempotent (replaying twice yields the same hash).
3. The causal chain is reconstructable from the event log.

We are NOT re-executing handlers during replay. We replay the *recorded
mutations* from each EventEnvelope in sequence. This is purely a state
reconstruction test — proving that the event log captures enough
information to rebuild state.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.event_scheduler import EventScheduler, SchedulerEvent
from umh.substrate.execution_authority import ExecutionAuthority
from umh.substrate.execution_contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionResult,
    ExecutionStatus,
)
from umh.substrate.execution_result_handler import ExecutionResultHandler
from umh.substrate.execution_router import ExecutionRouter
from umh.substrate.execution_worker import ExecutionWorker
from umh.substrate.nodes import Node, NodeRegistry, NodeRole, NodeStatus, NodeType
from umh.substrate.runtime_state_store import RuntimeStateStore


# ---------------------------------------------------------------------------
# Test harness (extended from test_execution_integration.py)
# ---------------------------------------------------------------------------


def make_replay_harness(
    emission_map: dict | None = None,
    adapter_execute_fn=None,
):
    """Wire up a complete execution fabric with event logging for replay tests.

    Returns (store, scheduler, event_log, tmp_path) so the caller can read
    back the event log and replay mutations.
    """
    store = RuntimeStateStore()

    # Event log backed by a temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    tmp.close()
    event_log = EventLogRuntime(log_path=tmp.name)

    # Registry with test node
    registry = NodeRegistry(persist=False)
    registry.upsert(
        Node(
            node_id="vps-primary",
            node_type=NodeType.VPS,
            role=NodeRole.ORCHESTRATOR,
            capabilities=[
                "reasoning",
                "extract_response",
                "clean_output",
                "test_primitive",
            ],
            status=NodeStatus.ONLINE,
        )
    )

    # Router
    router = ExecutionRouter(registry=registry)

    # Authority
    authority = ExecutionAuthority(router)

    # Worker with mock adapter
    worker = ExecutionWorker(store)

    class TestAdapter:
        adapter_id = "test_adapter"

        @property
        def node_id(self):
            return "vps-primary"

        @property
        def capabilities(self):
            return frozenset({"extract_response", "clean_output", "test_primitive"})

        def execute(self, request):
            if adapter_execute_fn:
                return adapter_execute_fn(request)
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                primitive_name=request.primitive_name,
                status=ExecutionStatus.SUCCEEDED,
                outputs={"result_key": f"executed_{request.primitive_name}"},
                node_id="vps-primary",
                idempotency_key=request.idempotency_key,
            )

        def health(self):
            return {"status": "healthy"}

    worker.register_adapter(TestAdapter())

    # Result handler
    result_handler = ExecutionResultHandler(
        primitive_emission_map=emission_map or {},
    )

    # Scheduler with event log
    scheduler = EventScheduler(store, event_log=event_log)

    # Wire subscriptions
    scheduler.subscribe(
        "stability_reached",
        authority.make_handler(
            "extract_response",
            ExecutionClass.PURE,
            requires=["cleaned_output", "gate_verdict"],
            constraints=ExecutionConstraints(timeout_s=10, max_retries=2),
        ),
        name="authority:extract_response",
    )

    scheduler.subscribe(
        "execution_requested",
        worker.handle_execution_requested,
        name="worker",
    )
    scheduler.subscribe(
        "execution_retried",
        worker.handle_execution_requested,
        name="worker:retry",
    )

    for evt_type in [
        "execution_completed",
        "execution_failed",
        "execution_timed_out",
        "execution_rejected",
    ]:
        scheduler.subscribe(
            evt_type,
            result_handler.handle_result,
            name=f"result_handler:{evt_type}",
        )

    return store, scheduler, event_log, tmp.name


def _cleanup(tmp_path: str) -> None:
    """Remove temporary event log file."""
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


def _run_full_lifecycle(emission_map=None, adapter_execute_fn=None):
    """Run a full lifecycle and return (store, scheduler, event_log, run_result, initial_snapshot, tmp_path).

    The initial_snapshot captures state *after* pre-setting required values
    but *before* the scheduler runs. This is the base state for replay.
    """
    store, scheduler, event_log, tmp_path = make_replay_harness(
        emission_map=emission_map,
        adapter_execute_fn=adapter_execute_fn,
    )

    # Pre-set required state (these are inputs, not event-sourced mutations)
    store.set("cleaned_output", "some text")
    store.set("gate_verdict", "CONFIRMED")

    # Snapshot the initial state before the scheduler runs
    initial_snapshot = store.snapshot()

    # Emit the lifecycle trigger
    scheduler.emit(
        SchedulerEvent(
            event_type="stability_reached",
            session_name="test_session",
            source="test",
        )
    )

    run_result = scheduler.run()
    return store, scheduler, event_log, run_result, initial_snapshot, tmp_path


def _replay_mutations(envelopes, initial_snapshot=None) -> RuntimeStateStore:
    """Create a store from initial snapshot and apply all mutations from event envelopes.

    If initial_snapshot is provided, the store starts with that state
    (representing the pre-event-fabric inputs). Then event log mutations
    are applied on top, reconstructing the final state.
    """
    replay_store = RuntimeStateStore()
    if initial_snapshot:
        replay_store.load_snapshot(initial_snapshot)
    for envelope in envelopes:
        if envelope.state_mutations:
            replay_store.apply_mutations(envelope.state_mutations)
    return replay_store


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_replay_produces_same_state():
    """Run a full lifecycle, capture state hash, replay mutations, verify identical hash.

    This proves the event log captures all state-mutating information needed
    to reconstruct the final state. Replay starts from the same initial
    snapshot (pre-event inputs) and applies logged mutations in order.
    """
    store, scheduler, event_log, _, initial_snapshot, tmp_path = _run_full_lifecycle(
        emission_map={"extract_response": ["response_extracted"]},
    )

    try:
        # Sanity: the lifecycle actually ran
        assert store.get("result_key") == "executed_extract_response"
        completed = store.get("completed_executions", [])
        assert len(completed) == 1

        # Capture final state hash from the original run
        original_hash = store.compute_state_hash()

        # Read the event log
        envelopes = event_log.read_all()
        assert len(envelopes) > 0, "Event log should have logged events with mutations"

        # Verify that we have state mutations recorded
        total_mutations = sum(len(e.state_mutations) for e in envelopes)
        assert total_mutations > 0, "Event log should contain state mutations"

        # Replay: start from initial snapshot, apply mutations from each envelope
        replay_store = _replay_mutations(envelopes, initial_snapshot=initial_snapshot)
        replay_hash = replay_store.compute_state_hash()

        # The replay hash must match the original
        assert replay_hash == original_hash, (
            f"Replay state hash {replay_hash} does not match "
            f"original state hash {original_hash}"
        )

        # Double-check: specific state values also match
        assert replay_store.get("result_key") == store.get("result_key")
        assert replay_store.get("completed_executions") == store.get(
            "completed_executions"
        )
    finally:
        _cleanup(tmp_path)


def test_replay_idempotent():
    """Replay twice from the same event log — both replays produce the same hash.

    This proves replay itself is deterministic: the same sequence of
    mutations always produces the same final state.
    """
    store, _, event_log, _, initial_snapshot, tmp_path = _run_full_lifecycle(
        emission_map={"extract_response": ["response_extracted"]},
    )

    try:
        # Read the event log once
        envelopes = event_log.read_all()
        assert len(envelopes) > 0

        # First replay
        replay_store_1 = _replay_mutations(envelopes, initial_snapshot=initial_snapshot)
        hash_1 = replay_store_1.compute_state_hash()

        # Second replay
        replay_store_2 = _replay_mutations(envelopes, initial_snapshot=initial_snapshot)
        hash_2 = replay_store_2.compute_state_hash()

        # Both replays must produce the identical hash
        assert hash_1 == hash_2, (
            f"Replay is not idempotent: hash_1={hash_1} != hash_2={hash_2}"
        )

        # And both must match the original run
        original_hash = store.compute_state_hash()
        assert hash_1 == original_hash, (
            f"Replay hash {hash_1} does not match original {original_hash}"
        )
    finally:
        _cleanup(tmp_path)


def test_causal_chain_reconstructable():
    """Verify the event log forms a coherent causal chain via correlation keys.

    For every logged event, we check:
    1. Each event has a unique event_id.
    2. Events with mutations are ordered by sequence_number (monotonic, gap-free).
    3. Events sharing the same execution_id form a logical chain
       (authority dispatch -> result handler completion).
    4. The event types appear in a valid lifecycle order.
    """
    _, _, event_log, _, _, tmp_path = _run_full_lifecycle(
        emission_map={"extract_response": ["response_extracted"]},
    )

    try:
        envelopes = event_log.read_all()
        assert len(envelopes) > 0

        # 1. All event_ids must be unique
        event_ids = [e.event_id for e in envelopes]
        assert len(event_ids) == len(set(event_ids)), (
            f"Duplicate event_ids found: {event_ids}"
        )

        # 2. Sequence numbers are monotonic and gap-free
        seq_numbers = [e.sequence_number for e in envelopes]
        for i, seq in enumerate(seq_numbers):
            assert seq == i, (
                f"Gap in sequence: expected {i}, got {seq}. Full: {seq_numbers}"
            )

        # 3. Extract execution_ids from metadata to verify correlation
        #    Authority handler writes execution_id into metadata.
        #    Result handler writes execution_id into metadata.
        execution_ids_seen: dict[str, list[str]] = {}
        for envelope in envelopes:
            exec_id = envelope.metadata.get("execution_id")
            if exec_id:
                execution_ids_seen.setdefault(exec_id, []).append(envelope.event_type)

        # There should be at least one execution_id that appears in both
        # the authority dispatch event and the result handler event.
        assert len(execution_ids_seen) > 0, "No execution_ids found in event metadata"

        for exec_id, event_types in execution_ids_seen.items():
            # The authority logs at stability_reached, the result handler logs
            # at execution_completed — both share the same execution_id,
            # so the primary chain must have at least 2 events.
            assert len(event_types) >= 2, (
                f"execution_id {exec_id} only appears in {len(event_types)} events, "
                f"expected >= 2 for authority dispatch + result handler"
            )

        # 4. The event types logged must follow a valid ordering.
        #    Only events with mutations get logged:
        #    - stability_reached (authority handler returns mutations)
        #    - execution_completed (result handler returns mutations)
        #    And potentially response_extracted if it had a handler with mutations.
        logged_event_types = [e.event_type for e in envelopes]

        # stability_reached must come before execution_completed
        if (
            "stability_reached" in logged_event_types
            and "execution_completed" in logged_event_types
        ):
            sr_idx = logged_event_types.index("stability_reached")
            ec_idx = logged_event_types.index("execution_completed")
            assert sr_idx < ec_idx, (
                f"stability_reached (idx={sr_idx}) should precede "
                f"execution_completed (idx={ec_idx})"
            )

        # Verify the logged event types are all valid lifecycle types
        valid_types = {
            "stability_reached",
            "execution_requested",
            "execution_completed",
            "execution_failed",
            "execution_timed_out",
            "execution_rejected",
            "execution_retried",
            "response_extracted",
        }
        for et in logged_event_types:
            assert et in valid_types, (
                f"Unexpected event type logged: {et}. Valid: {valid_types}"
            )
    finally:
        _cleanup(tmp_path)
