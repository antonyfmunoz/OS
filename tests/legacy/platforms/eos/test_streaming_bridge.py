"""Tests for the StreamingBridge — real-time execution narration."""

from __future__ import annotations

import sys
import threading

sys.path.insert(0, "/opt/OS")

import pytest

from runtime.platforms.eos.streaming_bridge import (
    StreamEvent,
    StreamEventType,
    StreamingBridge,
    cancel_speech,
    get_streaming_bridge,
    stream_event,
)


@pytest.fixture(autouse=True)
def _reset_bridge():
    """Reset singleton before and after each test."""
    StreamingBridge.reset_default_for_tests()
    yield
    StreamingBridge.reset_default_for_tests()


# ─── Singleton ──────────────────────────────────────────────────────────────


def test_singleton_returns_same_instance():
    a = StreamingBridge.default()
    b = StreamingBridge.default()
    assert a is b


def test_reset_creates_new_instance():
    a = StreamingBridge.default()
    StreamingBridge.reset_default_for_tests()
    b = StreamingBridge.default()
    assert a is not b


# ─── Event Emission ─────────────────────────────────────────────────────────


def test_stream_event_returns_event():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)  # Don't actually speak in tests

    event = bridge.stream_event(
        StreamEventType.TASK_STARTED,
        "Starting task...",
        payload={"task_id": "t_123"},
        source="test",
    )

    assert isinstance(event, StreamEvent)
    assert event.event_type == StreamEventType.TASK_STARTED
    assert event.message == "Starting task..."
    assert event.payload["task_id"] == "t_123"
    assert event.source == "test"


def test_module_level_stream_event():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    event = stream_event(
        StreamEventType.INFO,
        "test message",
        source="test",
    )
    assert event.event_type == StreamEventType.INFO


def test_event_serialization():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    event = bridge.stream_event(
        StreamEventType.ACTION_EXECUTED,
        "Clicking button...",
        payload={"selector": "#btn"},
        source="browser",
    )

    d = event.to_dict()
    assert d["event_type"] == "action_executed"
    assert d["message"] == "Clicking button..."
    assert d["payload"]["selector"] == "#btn"
    assert d["source"] == "browser"
    assert "event_id" in d
    assert "created_at" in d


# ─── History ────────────────────────────────────────────────────────────────


def test_recent_events():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    for i in range(5):
        bridge.stream_event(StreamEventType.INFO, f"event {i}", source="test")

    recent = bridge.recent_events(limit=3)
    assert len(recent) == 3
    assert recent[-1].message == "event 4"


def test_events_since():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    events = []
    for i in range(5):
        e = bridge.stream_event(StreamEventType.INFO, f"event {i}", source="test")
        events.append(e)

    after = bridge.events_since(events[2].event_id)
    assert len(after) == 2
    assert after[0].message == "event 3"
    assert after[1].message == "event 4"


def test_clear_history():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    bridge.stream_event(StreamEventType.INFO, "test", source="test")
    assert len(bridge.recent_events()) == 1

    bridge.clear_history()
    assert len(bridge.recent_events()) == 0


# ─── Subscribers ────────────────────────────────────────────────────────────


def test_subscriber_receives_events():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    received: list[StreamEvent] = []
    bridge.subscribe(received.append)

    bridge.stream_event(StreamEventType.TASK_STARTED, "go", source="test")

    assert len(received) == 1
    assert received[0].message == "go"


def test_unsubscribe():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    received: list[StreamEvent] = []
    bridge.subscribe(received.append)
    bridge.unsubscribe(received.append)

    bridge.stream_event(StreamEventType.INFO, "ignored", source="test")

    assert len(received) == 0


def test_subscriber_error_does_not_crash():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    def bad_callback(event):
        raise RuntimeError("boom")

    bridge.subscribe(bad_callback)

    # Should not raise
    event = bridge.stream_event(StreamEventType.INFO, "test", source="test")
    assert event is not None


# ─── Session ────────────────────────────────────────────────────────────────


def test_session_binding():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    bridge.set_session("sess_abc")
    event = bridge.stream_event(StreamEventType.INFO, "test", source="test")

    assert event.session_id == "sess_abc"


# ─── Event Types ────────────────────────────────────────────────────────────


def test_all_event_types_valid():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    for etype in StreamEventType:
        event = bridge.stream_event(etype, f"testing {etype.value}", source="test")
        assert event.event_type == etype


# ─── Thread Safety ──────────────────────────────────────────────────────────


def test_concurrent_event_emission():
    bridge = get_streaming_bridge()
    bridge.set_tts_enabled(False)

    errors: list[str] = []

    def emit(n: int) -> None:
        try:
            for i in range(10):
                bridge.stream_event(
                    StreamEventType.INFO, f"thread {n} event {i}", source="test"
                )
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=emit, args=(n,)) for n in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(bridge.recent_events(limit=200)) == 50
