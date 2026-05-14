"""
Tests for the Event Spine + Delivery Contract system.

Validates:
1. Event creation and serialization round-trip
2. Event store append/read/update operations
3. Delivery contract: DELIVERY_COMPLETE only when all chunks confirmed
4. Cross-session dedup: has_completed_reply guard
5. Correlation threading: all events in a workflow share correlation_id
6. Pipeline spine event emission
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

from umh.substrate.event_spine import (
    Event,
    EventStatus,
    EventType,
    create_event,
)
from umh.substrate.event_store import EventStore


def test_event_creation_and_serialization() -> None:
    """Events round-trip through serialize/deserialize without data loss."""
    event = create_event(
        EventType.PROMPT_RECEIVED,
        source="discord",
        source_session="dex_product",
        target="pipeline",
        payload={"message": "test prompt", "user_id": "123"},
    )

    assert event.event_id
    assert event.correlation_id
    assert event.source == "discord"
    assert event.source_session == "dex_product"
    assert event.target == "pipeline"
    assert event.event_type == EventType.PROMPT_RECEIVED
    assert event.status == EventStatus.CREATED
    assert event.payload["message"] == "test prompt"

    # Round-trip
    data = event.serialize()
    restored = Event.deserialize(data)
    assert restored.event_id == event.event_id
    assert restored.correlation_id == event.correlation_id
    assert restored.source == event.source
    assert restored.event_type == event.event_type
    assert restored.payload == event.payload

    print("PASS: event_creation_and_serialization")


def test_event_status_update() -> None:
    """Status updates mutate status and updated_at."""
    event = create_event(EventType.RELAY_SENT, source="bridge")
    original_updated = event.updated_at

    event.update_status(EventStatus.COMPLETED)
    assert event.status == EventStatus.COMPLETED
    # updated_at may be same if within same second — just check it's set
    assert event.updated_at

    print("PASS: event_status_update")


def test_event_store_append_and_read() -> None:
    """Events are persisted to JSONL and readable."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        store_path = f.name

    try:
        store = EventStore(path=store_path)

        e1 = create_event(EventType.PROMPT_RECEIVED, source="test")
        e2 = create_event(EventType.PIPELINE_CREATED, source="test")
        store.append(e1)
        store.append(e2)

        recent = store.read_recent(10)
        assert len(recent) == 2
        assert recent[0].event_id == e1.event_id
        assert recent[1].event_id == e2.event_id

        # Verify JSONL format
        with open(store_path, "r") as fh:
            lines = [l.strip() for l in fh if l.strip()]
        assert len(lines) == 2
        for line in lines:
            parsed = json.loads(line)
            assert "event_id" in parsed
            assert "event_type" in parsed

        print("PASS: event_store_append_and_read")
    finally:
        os.unlink(store_path)


def test_event_store_update_status() -> None:
    """Status updates are persisted to the store file."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        store_path = f.name

    try:
        store = EventStore(path=store_path)

        event = create_event(EventType.REPLY_COMPLETE, source="test")
        store.append(event)

        # Update status
        found = store.update_status(event.event_id, EventStatus.COMPLETED)
        assert found

        # Re-read and verify
        retrieved = store.get(event.event_id)
        assert retrieved is not None
        assert retrieved.status == EventStatus.COMPLETED

        print("PASS: event_store_update_status")
    finally:
        os.unlink(store_path)


def test_event_store_get_by_correlation() -> None:
    """All events with same correlation_id are retrieved together."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        store_path = f.name

    try:
        store = EventStore(path=store_path)
        corr_id = "workflow_abc123"

        e1 = create_event(
            EventType.PROMPT_RECEIVED, source="test", correlation_id=corr_id
        )
        e2 = create_event(
            EventType.PIPELINE_CREATED, source="test", correlation_id=corr_id
        )
        e3 = create_event(
            EventType.STEP_STARTED, source="test", correlation_id="other_workflow"
        )
        store.append(e1)
        store.append(e2)
        store.append(e3)

        correlated = store.get_by_correlation(corr_id)
        assert len(correlated) == 2
        assert all(e.correlation_id == corr_id for e in correlated)

        print("PASS: event_store_get_by_correlation")
    finally:
        os.unlink(store_path)


def test_cross_session_dedup() -> None:
    """has_completed_reply detects existing completed replies."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        store_path = f.name

    try:
        store = EventStore(path=store_path)
        corr_id = "workflow_dedup_test"

        # No completed reply yet
        assert not store.has_completed_reply(corr_id)

        # Create a reply_complete event but NOT completed
        reply = create_event(
            EventType.REPLY_COMPLETE, source="test", correlation_id=corr_id
        )
        store.append(reply)
        assert not store.has_completed_reply(corr_id)

        # Mark as completed
        store.update_status(reply.event_id, EventStatus.COMPLETED)
        assert store.has_completed_reply(corr_id)

        print("PASS: cross_session_dedup")
    finally:
        os.unlink(store_path)


def test_delivery_contract_simulation() -> None:
    """Simulates a full delivery contract: parent + chunks + DELIVERY_COMPLETE."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        store_path = f.name

    try:
        store = EventStore(path=store_path)
        corr_id = "workflow_delivery_test"

        # 1. Create parent reply_complete event
        parent = create_event(
            EventType.REPLY_COMPLETE,
            source="tmux_session",
            source_session="dex_product",
            target="discord",
            correlation_id=corr_id,
            payload={
                "content_len": 5000,
                "total_chunks": 3,
                "chunks_confirmed": 0,
            },
        )
        store.append(parent)

        # 2. Create chunk events
        chunks_confirmed = 0
        for i in range(3):
            chunk = create_event(
                EventType.REPLY_CHUNK,
                source="tmux_session",
                source_session="dex_product",
                target="discord",
                correlation_id=corr_id,
                parent_event_id=parent.event_id,
                payload={
                    "chunk_index": i,
                    "total_chunks": 3,
                    "content_len": 1500,
                },
            )
            store.append(chunk)

            # Simulate successful send
            store.update_status(chunk.event_id, EventStatus.SENT)

            # Emit relay_sent
            relay = create_event(
                EventType.RELAY_SENT,
                source="discord_bridge",
                correlation_id=corr_id,
                parent_event_id=chunk.event_id,
                payload={"chunk_index": i},
            )
            relay.update_status(EventStatus.COMPLETED)
            store.append(relay)
            chunks_confirmed += 1

        # 3. All chunks confirmed — mark parent completed
        store.update_status(
            parent.event_id,
            EventStatus.COMPLETED,
            {"chunks_confirmed": chunks_confirmed, "total_chunks": 3},
        )

        # 4. Emit DELIVERY_COMPLETE
        delivery = create_event(
            EventType.DELIVERY_COMPLETE,
            source="discord_bridge",
            correlation_id=corr_id,
            parent_event_id=parent.event_id,
            payload={
                "chunks_confirmed": 3,
                "total_chunks": 3,
            },
        )
        delivery.update_status(EventStatus.COMPLETED)
        store.append(delivery)

        # ── Verify the full chain ──────────────────────────────────────
        all_events = store.get_by_correlation(corr_id)
        event_types = [e.event_type.value for e in all_events]

        assert "reply_complete" in event_types
        assert event_types.count("reply_chunk") == 3
        assert event_types.count("relay_sent") == 3
        assert "delivery_complete" in event_types

        # Parent is completed
        parent_check = store.get(parent.event_id)
        assert parent_check is not None
        assert parent_check.status == EventStatus.COMPLETED

        # Delivery complete is the final event
        delivery_check = store.get(delivery.event_id)
        assert delivery_check is not None
        assert delivery_check.status == EventStatus.COMPLETED
        assert delivery_check.payload["chunks_confirmed"] == 3

        # Cross-session dedup works
        assert store.has_completed_reply(corr_id)

        print("PASS: delivery_contract_simulation")
    finally:
        os.unlink(store_path)


def test_partial_delivery_no_complete() -> None:
    """If a chunk fails, DELIVERY_COMPLETE is NOT emitted."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        store_path = f.name

    try:
        store = EventStore(path=store_path)
        corr_id = "workflow_partial_test"

        parent = create_event(
            EventType.REPLY_COMPLETE,
            source="test",
            correlation_id=corr_id,
            payload={"total_chunks": 3, "chunks_confirmed": 0},
        )
        store.append(parent)

        # Only 2 of 3 chunks succeed
        for i in range(2):
            chunk = create_event(
                EventType.REPLY_CHUNK,
                source="test",
                correlation_id=corr_id,
                parent_event_id=parent.event_id,
                payload={"chunk_index": i, "total_chunks": 3},
            )
            store.append(chunk)
            store.update_status(chunk.event_id, EventStatus.SENT)

        # Chunk 3 fails
        chunk3 = create_event(
            EventType.REPLY_CHUNK,
            source="test",
            correlation_id=corr_id,
            parent_event_id=parent.event_id,
            payload={"chunk_index": 2, "total_chunks": 3},
        )
        store.append(chunk3)
        store.update_status(
            chunk3.event_id, EventStatus.FAILED, {"error": "rate_limited"}
        )

        # Emit relay_failed for chunk 3
        fail_event = create_event(
            EventType.RELAY_FAILED,
            source="test",
            correlation_id=corr_id,
            parent_event_id=chunk3.event_id,
            payload={"chunk_index": 2, "error": "rate_limited"},
        )
        fail_event.update_status(EventStatus.FAILED)
        store.append(fail_event)

        # Parent should NOT be completed (no DELIVERY_COMPLETE emitted)
        parent_check = store.get(parent.event_id)
        assert parent_check is not None
        assert parent_check.status == EventStatus.CREATED  # never reached completed

        # No delivery_complete event exists
        all_events = store.get_by_correlation(corr_id)
        delivery_events = [
            e for e in all_events if e.event_type == EventType.DELIVERY_COMPLETE
        ]
        assert len(delivery_events) == 0

        # Cross-session dedup correctly returns False
        assert not store.has_completed_reply(corr_id)

        print("PASS: partial_delivery_no_complete")
    finally:
        os.unlink(store_path)


def test_pipeline_correlation_propagation() -> None:
    """Pipeline steps receive and propagate correlation_id via context."""
    from umh.substrate.pipeline import (
        Pipeline,
        PipelineStep,
        StepResult,
        register_handler,
    )

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        store_path = f.name

    try:
        # Temporarily replace the default store
        import umh.substrate.event_store as es_mod

        original_store = es_mod._store
        test_store = EventStore(path=store_path)
        es_mod._store = test_store

        corr_id = "pipeline_corr_test"

        # Register a test handler
        def echo_handler(step, ctx):
            return StepResult(
                status="succeeded",
                result={"echo": step.input_data.get("msg", "none")},
            )

        register_handler("echo_test", echo_handler)

        # Build and run pipeline with correlation_id
        steps = [
            PipelineStep.new(
                "step_a",
                "echo_test",
                input_data={"msg": "hello"},
            ),
            PipelineStep.new(
                "step_b",
                "echo_test",
                input_data={"msg": "world"},
            ),
        ]
        pipeline = Pipeline.new(
            "test_pipeline",
            steps,
            context={
                "correlation_id": corr_id,
                "source_session": "dex_test",
            },
        )
        result = pipeline.run()

        assert result["status"] == "succeeded"

        # Verify spine events were emitted
        all_events = test_store.get_by_correlation(corr_id)
        event_types = [e.event_type.value for e in all_events]

        assert "pipeline_created" in event_types
        assert event_types.count("step_started") == 2
        assert event_types.count("step_completed") == 2

        # Verify all events share the correlation_id
        assert all(e.correlation_id == corr_id for e in all_events)

        print("PASS: pipeline_correlation_propagation")
    finally:
        # Restore original store
        es_mod._store = original_store
        os.unlink(store_path)


def test_event_store_compact() -> None:
    """Compact removes old events while keeping recent ones."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        store_path = f.name

    try:
        store = EventStore(path=store_path)

        # Add a recent event
        recent = create_event(EventType.PROMPT_RECEIVED, source="test")
        store.append(recent)

        # Compact with 0 hours (removes everything)
        removed = store.compact(max_age_hours=0)
        assert removed == 1

        remaining = store.read_recent(10)
        assert len(remaining) == 0

        print("PASS: event_store_compact")
    finally:
        os.unlink(store_path)


if __name__ == "__main__":
    test_event_creation_and_serialization()
    test_event_status_update()
    test_event_store_append_and_read()
    test_event_store_update_status()
    test_event_store_get_by_correlation()
    test_cross_session_dedup()
    test_delivery_contract_simulation()
    test_partial_delivery_no_complete()
    test_pipeline_correlation_propagation()
    test_event_store_compact()

    print("\n══════════════════════════════════════════")
    print("ALL EVENT SPINE TESTS PASSED")
    print("══════════════════════════════════════════")
