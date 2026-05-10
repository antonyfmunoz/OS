"""Tests for the adapter event router.

Covers:
1. Correct routing per event type
2. Multiple adapters receiving same event
3. Deterministic handler ordering
4. No missing handlers crash
5. Adapters called exactly once per event
6. Context passed correctly
"""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from unittest.mock import MagicMock

from umh.adapters.contracts import Adapter, AdapterContext
from umh.adapters.registry import AdapterRegistry
from umh.adapters.event_router import route_events
from umh.adapters.stubs import DiscordAdapter, NotionAdapter, WorkstationAdapter
from umh.substrate.event_scheduler import SchedulerEvent


# ─── Fixtures ─────────────────────────────────────────────────────────


def _make_event(event_type: str, session: str = "test_session") -> SchedulerEvent:
    """Create a SchedulerEvent with minimal required fields."""
    return SchedulerEvent(
        event_type=event_type,
        session_name=session,
        source="test",
        metadata={"correlation_id": "cor_test123"},
    )


def _make_state() -> dict:
    return {"phase": "open_day", "step": 1}


class _TrackingAdapter:
    """Test adapter that records every call for assertion."""

    def __init__(self, supported: set[str], name: str = "Tracker") -> None:
        self._supported = supported
        self.name = name
        self.calls: list[tuple[str, AdapterContext]] = []

    def supports(self, event_type: str) -> bool:
        return event_type in self._supported

    def handle(self, event, context: AdapterContext) -> None:
        self.calls.append((event.event_type, context))


class _FailingAdapter:
    """Test adapter that raises on handle — router must not crash."""

    def supports(self, event_type: str) -> bool:
        return event_type == "open_day_started"

    def handle(self, event, context: AdapterContext) -> None:
        raise RuntimeError("Simulated adapter failure")


# ─── 1. Correct routing per event type ───────────────────────────────


class TestCorrectRouting:
    def test_open_day_routes_to_discord(self) -> None:
        registry = AdapterRegistry()
        discord = DiscordAdapter()
        registry.register(discord)

        log = route_events([_make_event("open_day_started")], _make_state(), registry)

        assert len(log) == 1
        assert log[0]["event_type"] == "open_day_started"
        assert log[0]["adapter"] == "DiscordAdapter"
        assert log[0]["status"] == "ok"

    def test_each_event_type_routes_correctly(self) -> None:
        registry = AdapterRegistry()
        tracker = _TrackingAdapter(
            {
                "open_day_started",
                "ritual_step_executed",
                "close_day_started",
                "ritual_completed",
            }
        )
        registry.register(tracker)

        events = [
            _make_event("open_day_started"),
            _make_event("ritual_step_executed"),
            _make_event("close_day_started"),
            _make_event("ritual_completed"),
        ]
        route_events(events, _make_state(), registry)

        received_types = [call[0] for call in tracker.calls]
        assert received_types == [
            "open_day_started",
            "ritual_step_executed",
            "close_day_started",
            "ritual_completed",
        ]


# ─── 2. Multiple adapters receiving same event ───────────────────────


class TestMultipleAdapters:
    def test_all_three_stubs_receive_open_day(self) -> None:
        registry = AdapterRegistry()
        discord = DiscordAdapter()
        notion = NotionAdapter()
        workstation = WorkstationAdapter()
        registry.register(discord)
        registry.register(notion)
        registry.register(workstation)

        log = route_events([_make_event("open_day_started")], _make_state(), registry)

        adapters_called = [entry["adapter"] for entry in log]
        assert adapters_called == [
            "DiscordAdapter",
            "NotionAdapter",
            "WorkstationAdapter",
        ]
        assert all(entry["status"] == "ok" for entry in log)

    def test_two_trackers_both_called(self) -> None:
        registry = AdapterRegistry()
        t1 = _TrackingAdapter({"ritual_completed"}, "T1")
        t2 = _TrackingAdapter({"ritual_completed"}, "T2")
        registry.register(t1)
        registry.register(t2)

        route_events([_make_event("ritual_completed")], _make_state(), registry)

        assert len(t1.calls) == 1
        assert len(t2.calls) == 1


# ─── 3. Deterministic handler ordering ───────────────────────────────


class TestDeterministicOrdering:
    def test_insertion_order_preserved(self) -> None:
        """Handlers are called in registration order, every time."""
        call_order: list[str] = []

        class A:
            def supports(self, et: str) -> bool:
                return et == "open_day_started"

            def handle(self, event, context) -> None:
                call_order.append("A")

        class B:
            def supports(self, et: str) -> bool:
                return et == "open_day_started"

            def handle(self, event, context) -> None:
                call_order.append("B")

        class C:
            def supports(self, et: str) -> bool:
                return et == "open_day_started"

            def handle(self, event, context) -> None:
                call_order.append("C")

        registry = AdapterRegistry()
        registry.register(A())
        registry.register(B())
        registry.register(C())

        # Run 3 times — order must be identical
        for _ in range(3):
            call_order.clear()
            route_events([_make_event("open_day_started")], _make_state(), registry)
            assert call_order == ["A", "B", "C"]


# ─── 4. No missing handlers crash ────────────────────────────────────


class TestNoHandlersCrash:
    def test_unknown_event_type_returns_no_handler(self) -> None:
        registry = AdapterRegistry()
        registry.register(DiscordAdapter())

        log = route_events([_make_event("unknown_event")], _make_state(), registry)

        assert len(log) == 1
        assert log[0]["status"] == "no_handler"
        assert log[0]["adapter"] is None

    def test_empty_registry_no_crash(self) -> None:
        registry = AdapterRegistry()
        log = route_events([_make_event("open_day_started")], _make_state(), registry)

        assert len(log) == 1
        assert log[0]["status"] == "no_handler"

    def test_failing_adapter_does_not_crash_router(self) -> None:
        registry = AdapterRegistry()
        registry.register(_FailingAdapter())

        log = route_events([_make_event("open_day_started")], _make_state(), registry)

        assert len(log) == 1
        assert log[0]["status"] == "error"


# ─── 5. Adapters called exactly once per event ───────────────────────


class TestExactlyOnce:
    def test_single_event_single_call(self) -> None:
        tracker = _TrackingAdapter({"open_day_started"})
        registry = AdapterRegistry()
        registry.register(tracker)

        route_events([_make_event("open_day_started")], _make_state(), registry)

        assert len(tracker.calls) == 1

    def test_three_events_three_calls(self) -> None:
        tracker = _TrackingAdapter(
            {"open_day_started", "ritual_step_executed", "close_day_started"}
        )
        registry = AdapterRegistry()
        registry.register(tracker)

        events = [
            _make_event("open_day_started"),
            _make_event("ritual_step_executed"),
            _make_event("close_day_started"),
        ]
        route_events(events, _make_state(), registry)

        assert len(tracker.calls) == 3

    def test_duplicate_registration_ignored(self) -> None:
        """Same adapter instance registered twice — only called once."""
        tracker = _TrackingAdapter({"open_day_started"})
        registry = AdapterRegistry()
        registry.register(tracker)
        registry.register(tracker)  # duplicate

        route_events([_make_event("open_day_started")], _make_state(), registry)

        assert len(tracker.calls) == 1
        assert registry.registered_count == 1


# ─── 6. Context passed correctly ──────────────────────────────────────


class TestContextPassing:
    def test_context_contains_session_id(self) -> None:
        tracker = _TrackingAdapter({"open_day_started"})
        registry = AdapterRegistry()
        registry.register(tracker)

        route_events(
            [_make_event("open_day_started", session="my_session")],
            _make_state(),
            registry,
        )

        _, ctx = tracker.calls[0]
        assert ctx.runtime_session_id == "my_session"

    def test_context_contains_correlation_id(self) -> None:
        tracker = _TrackingAdapter({"open_day_started"})
        registry = AdapterRegistry()
        registry.register(tracker)

        route_events([_make_event("open_day_started")], _make_state(), registry)

        _, ctx = tracker.calls[0]
        assert ctx.correlation_id == "cor_test123"

    def test_context_contains_state_snapshot(self) -> None:
        tracker = _TrackingAdapter({"open_day_started"})
        registry = AdapterRegistry()
        registry.register(tracker)

        state = {"phase": "open_day", "step": 42}
        route_events([_make_event("open_day_started")], state, registry)

        _, ctx = tracker.calls[0]
        assert ctx.state_snapshot == {"phase": "open_day", "step": 42}

    def test_context_metadata_has_event_id(self) -> None:
        tracker = _TrackingAdapter({"open_day_started"})
        registry = AdapterRegistry()
        registry.register(tracker)

        event = _make_event("open_day_started")
        route_events([event], _make_state(), registry)

        _, ctx = tracker.calls[0]
        assert ctx.metadata["event_id"] == event.event_id
        assert ctx.metadata["source"] == "test"

    def test_context_is_frozen(self) -> None:
        """AdapterContext is a frozen dataclass — immutable."""
        ctx = AdapterContext(
            state_snapshot={},
            runtime_session_id="s",
            correlation_id="c",
        )
        with pytest.raises(AttributeError):
            ctx.runtime_session_id = "modified"  # type: ignore[misc]
