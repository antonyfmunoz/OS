"""Tests for the unified organism event spine."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from substrate.organism.event_spine import (
    EventDomain,
    EventPriority,
    EventSpine,
    OrganismEvent,
)


def test_event_creation():
    event = OrganismEvent(
        domain=EventDomain.RUNTIME,
        event_type="runtime_available",
        source="runtime_graph",
        data={"runtime_id": "cc-opus", "status": "available"},
    )
    assert event.domain == EventDomain.RUNTIME
    assert event.event_type == "runtime_available"
    assert event.source == "runtime_graph"
    assert event.data["runtime_id"] == "cc-opus"
    assert event.timestamp > 0
    assert event.event_id != ""
    d = event.to_dict()
    assert d["domain"] == "runtime"
    assert d["event_type"] == "runtime_available"


def test_event_priority_default():
    event = OrganismEvent(
        domain=EventDomain.GOVERNANCE,
        event_type="kill_switch_activated",
        source="recursion_governor",
        data={},
    )
    assert event.priority == EventPriority.NORMAL


def test_event_priority_critical():
    event = OrganismEvent(
        domain=EventDomain.GOVERNANCE,
        event_type="kill_switch_activated",
        source="recursion_governor",
        data={},
        priority=EventPriority.CRITICAL,
    )
    assert event.priority == EventPriority.CRITICAL


def test_spine_emit_and_recent():
    spine = EventSpine()
    spine.emit(EventDomain.RUNTIME, "runtime_available", "graph", {"id": "r1"})
    spine.emit(EventDomain.GOVERNANCE, "approval_required", "governor", {"id": "a1"})

    recent = spine.recent(limit=10)
    assert len(recent) == 2
    assert recent[0].event_type == "runtime_available"
    assert recent[1].event_type == "approval_required"


def test_spine_subscribe_and_receive():
    spine = EventSpine()
    received: list[OrganismEvent] = []

    def handler(event: OrganismEvent) -> None:
        received.append(event)

    spine.subscribe("test-sub", handler)
    spine.emit(EventDomain.RUNTIME, "runtime_available", "graph", {"id": "r1"})

    assert len(received) == 1
    assert received[0].event_type == "runtime_available"


def test_spine_subscribe_with_domain_filter():
    spine = EventSpine()
    runtime_events: list[OrganismEvent] = []
    governance_events: list[OrganismEvent] = []

    spine.subscribe("runtime-watcher", lambda e: runtime_events.append(e),
                    domains={EventDomain.RUNTIME})
    spine.subscribe("gov-watcher", lambda e: governance_events.append(e),
                    domains={EventDomain.GOVERNANCE})

    spine.emit(EventDomain.RUNTIME, "runtime_available", "graph", {})
    spine.emit(EventDomain.GOVERNANCE, "approval_required", "governor", {})
    spine.emit(EventDomain.RUNTIME, "runtime_degraded", "supervisor", {})

    assert len(runtime_events) == 2
    assert len(governance_events) == 1


def test_spine_unsubscribe():
    spine = EventSpine()
    received: list[OrganismEvent] = []
    spine.subscribe("sub1", lambda e: received.append(e))

    spine.emit(EventDomain.RUNTIME, "test", "src", {})
    assert len(received) == 1

    spine.unsubscribe("sub1")
    spine.emit(EventDomain.RUNTIME, "test2", "src", {})
    assert len(received) == 1


def test_spine_replay():
    spine = EventSpine()
    spine.emit(EventDomain.RUNTIME, "ev1", "src", {})
    spine.emit(EventDomain.GOVERNANCE, "ev2", "src", {})
    spine.emit(EventDomain.RUNTIME, "ev3", "src", {})

    replayed = spine.replay(domains={EventDomain.RUNTIME})
    assert len(replayed) == 2
    assert replayed[0].event_type == "ev1"
    assert replayed[1].event_type == "ev3"


def test_spine_replay_since():
    spine = EventSpine()
    spine.emit(EventDomain.RUNTIME, "old", "src", {})
    cutoff = time.time()
    time.sleep(0.01)
    spine.emit(EventDomain.RUNTIME, "new", "src", {})

    replayed = spine.replay(since=cutoff)
    assert len(replayed) == 1
    assert replayed[0].event_type == "new"


def test_spine_snapshot():
    spine = EventSpine()
    spine.emit(EventDomain.RUNTIME, "ev1", "src", {"a": 1})
    spine.emit(EventDomain.GOVERNANCE, "ev2", "src", {"b": 2})

    snap = spine.snapshot()
    assert snap["total_events"] == 2
    assert "runtime" in snap["events_by_domain"]
    assert "governance" in snap["events_by_domain"]
    assert snap["events_by_domain"]["runtime"] == 1
    assert snap["events_by_domain"]["governance"] == 1


def test_spine_max_events_bounded():
    spine = EventSpine(max_events=5)
    for i in range(10):
        spine.emit(EventDomain.RUNTIME, f"ev{i}", "src", {})

    recent = spine.recent(limit=100)
    assert len(recent) == 5
    assert recent[0].event_type == "ev5"


def test_spine_subscriber_error_isolation():
    spine = EventSpine()
    good_received: list[OrganismEvent] = []

    def bad_handler(event: OrganismEvent) -> None:
        raise RuntimeError("boom")

    def good_handler(event: OrganismEvent) -> None:
        good_received.append(event)

    spine.subscribe("bad", bad_handler)
    spine.subscribe("good", good_handler)

    spine.emit(EventDomain.RUNTIME, "test", "src", {})
    assert len(good_received) == 1


def test_event_domains_cover_all_required():
    required = {
        "runtime", "governance", "advisor", "workcell", "objective",
        "execution", "leverage", "supervisor", "filesystem", "tmux",
        "docker", "projection", "transport", "recursion", "memory",
        "observability",
    }
    actual = {d.value for d in EventDomain}
    assert required.issubset(actual), f"missing domains: {required - actual}"


def test_spine_correlation_id():
    spine = EventSpine()
    spine.emit(EventDomain.OBJECTIVE, "started", "coord", {},
               correlation_id="obj-123")
    spine.emit(EventDomain.OBJECTIVE, "completed", "coord", {},
               correlation_id="obj-123")

    recent = spine.recent(limit=10)
    assert all(e.correlation_id == "obj-123" for e in recent)


def test_jsonl_persistence(tmp_path):
    path = str(tmp_path / "events.jsonl")
    spine = EventSpine(persist_path=path)
    spine.emit(EventDomain.EXECUTION, "test_event", "test_src", {"key": "val"})
    spine.emit(EventDomain.RUNTIME, "rt_event", "rt_src", {"rt": 1})

    spine2 = EventSpine(persist_path=path)
    count = spine2.recover()
    assert count == 2
    events = spine2.recent(10)
    assert events[0].event_type == "test_event"
    assert events[1].event_type == "rt_event"
    assert events[0].source == "test_src"


def test_jsonl_recovery_empty_file(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text("")
    spine = EventSpine(persist_path=str(path))
    assert spine.recover() == 0


def test_jsonl_no_persist_path():
    spine = EventSpine()
    spine.emit(EventDomain.RUNTIME, "test", "src", {})
    assert spine.recover() == 0


def test_snapshot_includes_persist_path(tmp_path):
    path = str(tmp_path / "events.jsonl")
    spine = EventSpine(persist_path=path)
    snap = spine.snapshot()
    assert snap["persist_path"] == path

    spine2 = EventSpine()
    snap2 = spine2.snapshot()
    assert snap2["persist_path"] is None
