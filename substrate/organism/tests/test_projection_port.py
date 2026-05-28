"""Tests for projection-agnostic organism state port."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.projection_port import (
    OrganismStatePort,
    ProjectionSubscriber,
    StateSlice,
)
from substrate.organism.event_spine import EventDomain, EventSpine


class MockProjection(ProjectionSubscriber):
    def __init__(self, projection_id: str, slices: set[StateSlice] | None = None):
        self._id = projection_id
        self._slices = slices
        self.received: list[dict] = []

    @property
    def subscriber_id(self) -> str:
        return self._id

    def accepts_slices(self) -> set[StateSlice] | None:
        return self._slices

    def on_state_update(self, slice_type: StateSlice, data: dict) -> None:
        self.received.append({"slice": slice_type, "data": data})


def test_register_projection():
    port = OrganismStatePort()
    proj = MockProjection("cockpit")
    port.register(proj)
    assert "cockpit" in port.registered_projections()


def test_unregister_projection():
    port = OrganismStatePort()
    proj = MockProjection("cockpit")
    port.register(proj)
    port.unregister("cockpit")
    assert "cockpit" not in port.registered_projections()


def test_broadcast_to_all():
    port = OrganismStatePort()
    p1 = MockProjection("cockpit")
    p2 = MockProjection("eos")
    port.register(p1)
    port.register(p2)

    port.broadcast(StateSlice.RUNTIMES, {"count": 3})
    assert len(p1.received) == 1
    assert len(p2.received) == 1


def test_filtered_broadcast():
    port = OrganismStatePort()
    runtime_only = MockProjection("runtime-watcher", slices={StateSlice.RUNTIMES})
    all_slices = MockProjection("full-view")
    port.register(runtime_only)
    port.register(all_slices)

    port.broadcast(StateSlice.RUNTIMES, {"count": 3})
    port.broadcast(StateSlice.OBJECTIVES, {"active": 2})

    assert len(runtime_only.received) == 1
    assert len(all_slices.received) == 2


def test_subscriber_error_isolation():
    port = OrganismStatePort()

    class BadProjection(ProjectionSubscriber):
        @property
        def subscriber_id(self) -> str:
            return "bad"
        def accepts_slices(self):
            return None
        def on_state_update(self, slice_type, data):
            raise RuntimeError("boom")

    good = MockProjection("good")
    port.register(BadProjection())
    port.register(good)

    port.broadcast(StateSlice.RUNTIMES, {"x": 1})
    assert len(good.received) == 1


def test_spine_bridge():
    spine = EventSpine()
    port = OrganismStatePort()
    proj = MockProjection("cockpit")
    port.register(proj)

    port.bridge_from_spine(spine, {
        EventDomain.RUNTIME: StateSlice.RUNTIMES,
        EventDomain.OBJECTIVE: StateSlice.OBJECTIVES,
    })

    spine.emit(EventDomain.RUNTIME, "runtime_available", "graph", {"id": "rt1"})
    assert len(proj.received) == 1
    assert proj.received[0]["slice"] == StateSlice.RUNTIMES


def test_state_slices_cover_domains():
    required = {
        "runtimes", "objectives", "governance", "leverage",
        "workcells", "economy", "observability",
    }
    actual = {s.value for s in StateSlice}
    assert required.issubset(actual), f"missing slices: {required - actual}"
