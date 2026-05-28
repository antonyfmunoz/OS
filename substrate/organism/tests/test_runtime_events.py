"""Tests for runtime event bus wiring."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
)
from substrate.organism.runtime_supervisor import RuntimeSupervisor


def test_graph_emits_register_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register(
        "test-rt", RuntimeClass.LOCAL_MODEL,
        frozenset({RuntimeCapability.REASON}),
    )

    events = spine.recent(limit=50)
    reg_events = [e for e in events if e.event_type == "runtime_registered"]
    assert len(reg_events) == 1
    assert reg_events[0].domain == EventDomain.RUNTIME
    assert reg_events[0].data["runtime_id"] == "test-rt"


def test_graph_emits_status_change_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register("rt1", RuntimeClass.LOCAL_MODEL, frozenset({RuntimeCapability.REASON}))
    graph.update_status("rt1", AvailabilityStatus.DEGRADED)

    events = spine.recent(limit=50)
    status_events = [e for e in events if e.event_type == "runtime_status_changed"]
    assert len(status_events) == 1
    assert status_events[0].data["new_status"] == "degraded"


def test_graph_emits_failure_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register("rt1", RuntimeClass.LOCAL_MODEL, frozenset({RuntimeCapability.REASON}))
    graph.record_failure("rt1")

    events = spine.recent(limit=50)
    fail_events = [e for e in events if e.event_type == "runtime_failure_recorded"]
    assert len(fail_events) == 1


def test_supervisor_emits_crash_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register("rt1", RuntimeClass.LOCAL_MODEL, frozenset({RuntimeCapability.REASON}))
    supervisor = RuntimeSupervisor(graph, event_spine=spine)
    supervisor.supervise("rt1")
    supervisor.record_crash("rt1", error="segfault")

    events = spine.recent(limit=50)
    crash_events = [e for e in events if e.event_type == "runtime_crashed"]
    assert len(crash_events) == 1
    assert crash_events[0].domain == EventDomain.SUPERVISOR
    assert crash_events[0].data["error"] == "segfault"


def test_supervisor_emits_recovery_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register("rt1", RuntimeClass.LOCAL_MODEL, frozenset({RuntimeCapability.REASON}))
    supervisor = RuntimeSupervisor(graph, event_spine=spine)
    supervisor.supervise("rt1")
    supervisor.record_recovery_success("rt1", latency_ms=50)

    events = spine.recent(limit=50)
    recovery_events = [e for e in events if e.event_type == "runtime_recovered"]
    assert len(recovery_events) == 1


def test_supervisor_emits_recovery_failure_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register("rt1", RuntimeClass.LOCAL_MODEL, frozenset({RuntimeCapability.REASON}))
    supervisor = RuntimeSupervisor(graph, event_spine=spine)
    supervisor.supervise("rt1")
    supervisor.record_recovery_failure("rt1", error="timeout")

    events = spine.recent(limit=50)
    fail_events = [e for e in events if e.event_type == "runtime_recovery_failed"]
    assert len(fail_events) == 1
    assert fail_events[0].data["error"] == "timeout"
