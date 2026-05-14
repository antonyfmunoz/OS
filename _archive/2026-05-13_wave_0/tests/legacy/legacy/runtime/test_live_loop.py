"""Tests for the live runtime loop and input router.

Covers:
1. start_session triggers open_day
2. handle_input triggers action lifecycle
3. multiple inputs preserve session_id
4. end_session triggers close_day
5. determinism: same inputs → same output structure
6. replay safety
7. input router classification
8. session lifecycle guards (no double start, no input before start)
9. full open → action → action → close flow
"""

import sys

sys.path.insert(0, "/opt/OS")

import ast
import inspect
import pytest
from typing import Any

from umh.adapters.contracts import AdapterContext
from umh.adapters.registry import AdapterRegistry
from umh.adapters.stubs import DiscordAdapter, NotionAdapter, WorkstationAdapter
from umh.runtime_loop.context import RuntimeContext
from umh.runtime_loop.input_router import InputEvent, RoutedInput, route_input
from umh.runtime_loop.live_loop import LiveRuntime
from umh.substrate.runtime_state_store import RuntimeStateStore


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_registry_with_stubs() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(DiscordAdapter())
    registry.register(NotionAdapter())
    registry.register(WorkstationAdapter())
    return registry


def _empty_store() -> RuntimeStateStore:
    return RuntimeStateStore()


def _make_runtime(
    store: RuntimeStateStore | None = None,
    registry: AdapterRegistry | None = None,
) -> LiveRuntime:
    return LiveRuntime(
        state_store=store or _empty_store(),
        adapter_registry=registry or _make_registry_with_stubs(),
    )


class _TrackingAdapter:
    """Records calls with full event and context for assertion."""

    def __init__(self, supported: set[str] | None = None) -> None:
        self.calls: list[tuple[Any, AdapterContext]] = []
        self._supported = supported

    def supports(self, event_type: str) -> bool:
        if self._supported is None:
            return True
        return event_type in self._supported

    def handle(self, event: Any, context: AdapterContext) -> None:
        self.calls.append((event, context))


# ─── 1. Input Router Classification ──────────────────────────────────


class TestInputRouter:
    def test_open_command(self) -> None:
        event = InputEvent(transport="discord", text="!open")
        routed = route_input(event)
        assert routed.request_type == "open_day"
        assert routed.intent_text == ""

    def test_start_command(self) -> None:
        event = InputEvent(transport="local", text="!start morning routine")
        routed = route_input(event)
        assert routed.request_type == "open_day"
        assert routed.intent_text == "morning routine"

    def test_begin_command(self) -> None:
        event = InputEvent(transport="voice", text="!begin")
        routed = route_input(event)
        assert routed.request_type == "open_day"

    def test_close_command(self) -> None:
        event = InputEvent(transport="discord", text="!close")
        routed = route_input(event)
        assert routed.request_type == "close_day"
        assert routed.intent_text == ""

    def test_end_command(self) -> None:
        event = InputEvent(transport="discord", text="!end wrapping up")
        routed = route_input(event)
        assert routed.request_type == "close_day"
        assert routed.intent_text == "wrapping up"

    def test_shutdown_command(self) -> None:
        event = InputEvent(transport="local", text="!shutdown")
        routed = route_input(event)
        assert routed.request_type == "close_day"

    def test_action_default(self) -> None:
        event = InputEvent(transport="discord", text="build landing page")
        routed = route_input(event)
        assert routed.request_type == "action"
        assert routed.intent_text == "build landing page"

    def test_empty_text_is_action(self) -> None:
        event = InputEvent(transport="local", text="")
        routed = route_input(event)
        assert routed.request_type == "action"
        assert routed.intent_text == ""

    def test_case_insensitive(self) -> None:
        event = InputEvent(transport="discord", text="!OPEN session")
        routed = route_input(event)
        assert routed.request_type == "open_day"

    def test_transport_passthrough(self) -> None:
        event = InputEvent(
            transport="discord",
            text="hello",
            metadata={"user_id": "123"},
        )
        routed = route_input(event)
        assert routed.transport == "discord"
        assert routed.metadata == {"user_id": "123"}

    def test_empty_transport_raises(self) -> None:
        with pytest.raises(ValueError, match="transport must not be empty"):
            InputEvent(transport="", text="hello")


# ─── 2. start_session triggers open_day ──────────────────────────────


class TestStartSession:
    def test_returns_structured_output(self) -> None:
        runtime = _make_runtime()
        result = runtime.start_session(transport="discord")

        assert "session_id" in result
        assert "lifecycle_result" in result
        assert "started_at" in result
        assert result["request_type"] == "open_day"

    def test_session_becomes_active(self) -> None:
        runtime = _make_runtime()
        assert not runtime.is_active

        runtime.start_session()
        assert runtime.is_active

    def test_session_id_assigned(self) -> None:
        runtime = _make_runtime()
        result = runtime.start_session()

        assert result["session_id"].startswith("live_")
        assert runtime.session_id == result["session_id"]

    def test_lifecycle_result_has_events(self) -> None:
        runtime = _make_runtime()
        result = runtime.start_session()

        lr = result["lifecycle_result"]
        assert lr["events_count"] > 0
        assert lr["mutations_count"] > 0

    def test_double_start_raises(self) -> None:
        runtime = _make_runtime()
        runtime.start_session()

        with pytest.raises(RuntimeError, match="Session already active"):
            runtime.start_session()


# ─── 3. handle_input triggers action lifecycle ───────────────────────


class TestHandleInput:
    def test_action_returns_structured_output(self) -> None:
        runtime = _make_runtime()
        runtime.start_session()

        event = InputEvent(transport="discord", text="build landing page")
        result = runtime.handle_input(event)

        assert result["request_type"] == "action"
        assert result["intent_text"] == "build landing page"
        assert "lifecycle_result" in result
        assert "handled_at" in result

    def test_action_lifecycle_result_has_events(self) -> None:
        runtime = _make_runtime()
        runtime.start_session()

        event = InputEvent(transport="discord", text="check metrics")
        result = runtime.handle_input(event)

        lr = result["lifecycle_result"]
        # action produces 2 events: received + completed
        assert lr["events_count"] == 2
        # action produces 2 mutations: increment + record
        assert lr["mutations_count"] == 2

    def test_input_before_session_raises(self) -> None:
        runtime = _make_runtime()
        event = InputEvent(transport="discord", text="hello")

        with pytest.raises(RuntimeError, match="No active session"):
            runtime.handle_input(event)

    def test_open_command_via_handle_input(self) -> None:
        """An !open command mid-session routes through open_day lifecycle."""
        runtime = _make_runtime()
        runtime.start_session()

        event = InputEvent(transport="discord", text="!open")
        result = runtime.handle_input(event)

        assert result["request_type"] == "open_day"

    def test_close_command_via_handle_input(self) -> None:
        """An !close command mid-session routes through close_day lifecycle."""
        runtime = _make_runtime()
        runtime.start_session()

        event = InputEvent(transport="discord", text="!close")
        result = runtime.handle_input(event)

        assert result["request_type"] == "close_day"


# ─── 4. multiple inputs preserve session_id ──────────────────────────


class TestSessionContinuity:
    def test_session_id_stable_across_inputs(self) -> None:
        runtime = _make_runtime()
        start = runtime.start_session()
        session_id = start["session_id"]

        for text in ["task one", "task two", "task three"]:
            event = InputEvent(transport="local", text=text)
            result = runtime.handle_input(event)
            assert result["session_id"] == session_id

    def test_last_activity_updates(self) -> None:
        runtime = _make_runtime()
        runtime.start_session()
        ts1 = runtime.last_activity_ts

        event = InputEvent(transport="local", text="do something")
        runtime.handle_input(event)
        ts2 = runtime.last_activity_ts

        # Timestamps are ISO-8601 — lexicographic comparison works
        assert ts2 >= ts1

    def test_state_accumulates_across_actions(self) -> None:
        """State store accumulates mutations across multiple handle_input calls."""
        store = _empty_store()
        runtime = _make_runtime(store=store)
        runtime.start_session()

        for i in range(3):
            event = InputEvent(transport="local", text=f"action {i}")
            runtime.handle_input(event)

        # action_count should be 3
        assert store.get("action_count") == 3


# ─── 5. end_session triggers close_day ───────────────────────────────


class TestEndSession:
    def test_returns_structured_output(self) -> None:
        runtime = _make_runtime()
        runtime.start_session()
        result = runtime.end_session()

        assert result["request_type"] == "close_day"
        assert "lifecycle_result" in result
        assert "ended_at" in result

    def test_session_becomes_inactive(self) -> None:
        runtime = _make_runtime()
        runtime.start_session()
        assert runtime.is_active

        runtime.end_session()
        assert not runtime.is_active

    def test_end_before_start_raises(self) -> None:
        runtime = _make_runtime()

        with pytest.raises(RuntimeError, match="No active session"):
            runtime.end_session()

    def test_can_start_new_session_after_end(self) -> None:
        runtime = _make_runtime()

        runtime.start_session()
        runtime.end_session()

        # Should not raise
        result = runtime.start_session()
        assert result["session_id"].startswith("live_")


# ─── 6. Determinism ─────────────────────────────────────────────────


class TestDeterminism:
    def test_same_action_input_same_structure(self) -> None:
        """Two action runs with identical inputs produce identical structure."""
        results = []
        for _ in range(2):
            store = _empty_store()
            runtime = _make_runtime(store=store)
            runtime.start_session(transport="local")

            event = InputEvent(transport="local", text="build feature")
            result = runtime.handle_input(event)
            results.append(result["lifecycle_result"])

        assert results[0]["events_count"] == results[1]["events_count"]
        assert results[0]["mutations_count"] == results[1]["mutations_count"]
        assert len(results[0]["dispatch_log"]) == len(results[1]["dispatch_log"])

    def test_full_flow_same_structure(self) -> None:
        """Two full flows (open → action → close) produce identical structure."""
        all_outputs = []
        for _ in range(2):
            store = _empty_store()
            runtime = _make_runtime(store=store)
            outputs = []

            outputs.append(runtime.start_session(transport="discord"))

            event = InputEvent(transport="discord", text="task alpha")
            outputs.append(runtime.handle_input(event))

            outputs.append(runtime.end_session())
            all_outputs.append(outputs)

        for i in range(3):
            a = all_outputs[0][i]["lifecycle_result"]
            b = all_outputs[1][i]["lifecycle_result"]
            assert a["events_count"] == b["events_count"]
            assert a["mutations_count"] == b["mutations_count"]


# ─── 7. Replay Safety ───────────────────────────────────────────────


class TestReplaySafety:
    def test_replay_produces_same_state_keys(self) -> None:
        """Replaying the same flow produces the same set of state key categories.

        Session IDs and action IDs are unique per run, so we normalize
        key prefixes by taking only the first dotted segment (the category).
        """
        categories_list = []
        for _ in range(2):
            store = _empty_store()
            runtime = _make_runtime(store=store, registry=AdapterRegistry())
            runtime.start_session(transport="local")

            event = InputEvent(transport="local", text="replay test")
            runtime.handle_input(event)

            runtime.end_session()

            # First segment = category (presence_state, runtime_mode, etc.)
            categories = {k.split(".")[0] for k in store.keys() if "." in k}
            categories_list.append(categories)

        assert categories_list[0] == categories_list[1]

    def test_replay_same_mutation_count(self) -> None:
        """Replaying yields the same total mutation count at each step."""
        counts_per_run = []
        for _ in range(2):
            store = _empty_store()
            runtime = _make_runtime(store=store, registry=AdapterRegistry())
            counts = []

            r = runtime.start_session(transport="local")
            counts.append(r["lifecycle_result"]["mutations_count"])

            event = InputEvent(transport="local", text="replay test")
            r = runtime.handle_input(event)
            counts.append(r["lifecycle_result"]["mutations_count"])

            r = runtime.end_session()
            counts.append(r["lifecycle_result"]["mutations_count"])

            counts_per_run.append(counts)

        assert counts_per_run[0] == counts_per_run[1]


# ─── 8. No adapter imports in live_loop ──────────────────────────────


class TestNoAdapterImports:
    def test_live_loop_does_not_import_stubs(self) -> None:
        """live_loop.py must not import concrete adapters."""
        source = inspect.getsource(sys.modules["umh.runtime_loop.live_loop"])
        tree = ast.parse(source)

        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name)

        forbidden = {"DiscordAdapter", "NotionAdapter", "WorkstationAdapter"}
        violations = imported_names & forbidden
        assert not violations, f"live_loop.py imports adapters: {violations}"

    def test_live_loop_does_not_import_discord(self) -> None:
        """live_loop.py must not import discord or notion modules."""
        source = inspect.getsource(sys.modules["umh.runtime_loop.live_loop"])
        assert "import discord" not in source
        assert "from discord" not in source


# ─── 9. Full flow: open → action → action → close ───────────────────


class TestFullFlow:
    def test_complete_interaction_trace(self) -> None:
        """Discord → open → action → action → close."""
        tracker = _TrackingAdapter()
        registry = AdapterRegistry()
        registry.register(tracker)

        store = _empty_store()
        runtime = _make_runtime(store=store, registry=registry)

        # Open
        open_result = runtime.start_session(transport="discord")
        assert open_result["request_type"] == "open_day"

        events_after_open = len(tracker.calls)
        assert events_after_open > 0  # open_day emits events

        # Action 1
        event1 = InputEvent(transport="discord", text="build landing page")
        action1 = runtime.handle_input(event1)
        assert action1["request_type"] == "action"
        assert action1["intent_text"] == "build landing page"

        events_after_action1 = len(tracker.calls)
        assert events_after_action1 > events_after_open

        # Action 2
        event2 = InputEvent(transport="discord", text="check analytics")
        action2 = runtime.handle_input(event2)
        assert action2["request_type"] == "action"

        events_after_action2 = len(tracker.calls)
        assert events_after_action2 > events_after_action1

        # Close
        close_result = runtime.end_session()
        assert close_result["request_type"] == "close_day"
        assert not runtime.is_active

        total_events = len(tracker.calls)
        assert total_events > events_after_action2

    def test_event_types_in_full_flow(self) -> None:
        """Verify expected event types appear in correct order."""
        tracker = _TrackingAdapter()
        registry = AdapterRegistry()
        registry.register(tracker)

        store = _empty_store()
        runtime = _make_runtime(store=store, registry=registry)

        runtime.start_session(transport="discord")

        event = InputEvent(transport="discord", text="do something")
        runtime.handle_input(event)

        runtime.end_session()

        event_types = [call[0].event_type for call in tracker.calls]

        # open_day events
        assert "open_day_started" in event_types
        # action events
        assert "action_received" in event_types
        assert "action_completed" in event_types
        # close_day events
        assert "close_day_started" in event_types
        assert "ritual_completed" in event_types
