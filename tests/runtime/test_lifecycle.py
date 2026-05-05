"""Tests for the runtime lifecycle orchestrator.

Covers:
1. open_day full flow
2. close_day full flow
3. mutations applied before routing
4. adapters invoked
5. dispatch_log correctness
6. determinism (same input → same output structure)
7. replay idempotency
8. no direct adapter imports in lifecycle
9. correct event count per ritual (8 steps + start + complete = 10)
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
from umh.runtime_loop.lifecycle import run_lifecycle
from umh.substrate.runtime_state_store import RuntimeStateStore


# ─── Helpers ──────────────────────────────────────────────────────────

_TS = "2026-04-17T12:00:00+00:00"


def _make_context(
    session_id: str = "sess_test",
    transport: str = "discord",
    trigger: str = "manual",
    profile_id: str | None = None,
) -> RuntimeContext:
    return RuntimeContext(
        runtime_session_id=session_id,
        transport=transport,
        timestamp=_TS,
        correlation_id="cor_lifecycle_test",
        requested_profile_id=profile_id,
        trigger=trigger,
    )


def _make_registry_with_stubs() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(DiscordAdapter())
    registry.register(NotionAdapter())
    registry.register(WorkstationAdapter())
    return registry


def _empty_store() -> RuntimeStateStore:
    return RuntimeStateStore()


class _TrackingAdapter:
    """Records calls with full event and context for assertion."""

    def __init__(self, supported: set[str]) -> None:
        self.calls: list[tuple[Any, AdapterContext]] = []
        self._supported = supported

    def supports(self, event_type: str) -> bool:
        return event_type in self._supported

    def handle(self, event: Any, context: AdapterContext) -> None:
        self.calls.append((event, context))


class _OrderTracker:
    """Tracks mutation-vs-routing ordering."""

    def __init__(self) -> None:
        self.state_at_route_time: dict[str, Any] | None = None

    def supports(self, event_type: str) -> bool:
        return True

    def handle(self, event: Any, context: AdapterContext) -> None:
        # Capture the state snapshot seen by adapters
        if self.state_at_route_time is None:
            self.state_at_route_time = dict(context.state_snapshot)


# ─── 1. open_day full flow ────────────────────────────────────────────


class TestOpenDayFullFlow:
    def test_returns_structured_output(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "open_day")

        assert "result" in output
        assert "dispatch_log" in output
        assert "events_count" in output
        assert "mutations_count" in output
        assert "state_hash" in output

    def test_result_contains_plan_id(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "open_day")

        assert output["result"]["plan_id"]

    def test_result_contains_session_id(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context(session_id="sess_open")

        output = run_lifecycle(store, registry, ctx, "open_day")

        assert output["result"]["runtime_session_id"] == "sess_open"

    def test_mutations_applied(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        run_lifecycle(store, registry, ctx, "open_day")

        # After open_day, store should have state (presence, mode, etc.)
        assert len(store.keys()) > 0

    def test_invalid_request_type_raises(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        with pytest.raises(ValueError, match="Unknown request_type"):
            run_lifecycle(store, registry, ctx, "invalid_type")


# ─── 2. close_day full flow ──────────────────────────────────────────


class TestCloseDayFullFlow:
    def test_returns_structured_output(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "close_day")

        assert "result" in output
        assert "dispatch_log" in output
        assert output["events_count"] > 0
        assert output["mutations_count"] > 0

    def test_result_contains_plan_id(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "close_day")

        assert output["result"]["plan_id"]

    def test_result_presence_set(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "close_day")

        # Close day should set a presence state
        assert output["result"]["presence_after"]


# ─── 3. mutations applied before routing ──────────────────────────────


class TestMutationsBeforeRouting:
    def test_adapters_see_post_mutation_state(self) -> None:
        """Adapters must see state AFTER mutations, not before."""
        store = _empty_store()
        tracker = _OrderTracker()
        registry = AdapterRegistry()
        registry.register(tracker)
        ctx = _make_context()

        run_lifecycle(store, registry, ctx, "open_day")

        # The state snapshot the adapter saw should have keys
        # (mutations were applied before routing)
        assert tracker.state_at_route_time is not None
        assert len(tracker.state_at_route_time) > 0

    def test_state_snapshot_matches_store(self) -> None:
        """Adapter's state_snapshot should match the store's snapshot."""
        store = _empty_store()
        tracker = _OrderTracker()
        registry = AdapterRegistry()
        registry.register(tracker)
        ctx = _make_context()

        run_lifecycle(store, registry, ctx, "open_day")

        store_snapshot = store.snapshot()
        assert tracker.state_at_route_time == store_snapshot


# ─── 4. adapters invoked ─────────────────────────────────────────────


class TestAdaptersInvoked:
    def test_all_stubs_called_for_open_day(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "open_day")

        adapter_names = {d["adapter"] for d in output["dispatch_log"] if d["adapter"]}
        assert "DiscordAdapter" in adapter_names
        assert "NotionAdapter" in adapter_names
        assert "WorkstationAdapter" in adapter_names

    def test_tracking_adapter_receives_events(self) -> None:
        store = _empty_store()
        tracker = _TrackingAdapter(
            {"open_day_started", "ritual_step_executed", "ritual_completed"}
        )
        registry = AdapterRegistry()
        registry.register(tracker)
        ctx = _make_context()

        run_lifecycle(store, registry, ctx, "open_day")

        event_types = [call[0].event_type for call in tracker.calls]
        assert "open_day_started" in event_types
        assert "ritual_completed" in event_types
        assert event_types.count("ritual_step_executed") == 8


# ─── 5. dispatch_log correctness ─────────────────────────────────────


class TestDispatchLog:
    def test_log_entries_have_required_keys(self) -> None:
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "open_day")

        for entry in output["dispatch_log"]:
            assert "event_id" in entry
            assert "event_type" in entry
            assert "adapter" in entry
            assert "status" in entry

    def test_all_statuses_are_ok(self) -> None:
        """With stubs, all dispatches should succeed."""
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "open_day")

        for entry in output["dispatch_log"]:
            assert entry["status"] == "ok", f"Failed: {entry}"

    def test_no_handlers_recorded_with_empty_registry(self) -> None:
        store = _empty_store()
        registry = AdapterRegistry()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "open_day")

        for entry in output["dispatch_log"]:
            assert entry["status"] == "no_handler"
            assert entry["adapter"] is None


# ─── 6. determinism ──────────────────────────────────────────────────


class TestDeterminism:
    def test_same_input_same_structure(self) -> None:
        """Two runs with identical inputs produce identical structure.

        Note: state_hash may differ because substrate functions generate
        unique plan_ids per execution (hash of session_id + wall-clock time).
        We verify structural determinism — counts, keys, ordering — not
        bitwise hash equality.
        """
        results = []
        for _ in range(2):
            store = _empty_store()
            registry = _make_registry_with_stubs()
            ctx = _make_context()
            output = run_lifecycle(store, registry, ctx, "open_day")
            results.append(output)

        # Same event count
        assert results[0]["events_count"] == results[1]["events_count"]
        # Same mutation count
        assert results[0]["mutations_count"] == results[1]["mutations_count"]
        # Same number of dispatch entries
        assert len(results[0]["dispatch_log"]) == len(results[1]["dispatch_log"])
        # Same result keys (structural equivalence)
        assert set(results[0]["result"].keys()) == set(results[1]["result"].keys())

    def test_same_dispatch_adapter_order(self) -> None:
        """Adapter ordering in dispatch_log is deterministic."""
        logs = []
        for _ in range(3):
            store = _empty_store()
            registry = _make_registry_with_stubs()
            ctx = _make_context()
            output = run_lifecycle(store, registry, ctx, "open_day")
            logs.append(
                [(d["event_type"], d["adapter"]) for d in output["dispatch_log"]]
            )

        assert logs[0] == logs[1] == logs[2]


# ─── 7. replay idempotency ───────────────────────────────────────────


class TestReplayIdempotency:
    def test_same_state_key_pattern_on_replay(self) -> None:
        """Replaying produces the same set of state key prefixes.

        Exact hashes differ because plan_ids contain wall-clock timestamps.
        Key prefixes (presence_state., runtime_mode., etc.) are stable.
        """
        key_prefixes_list = []
        for _ in range(2):
            store = _empty_store()
            registry = AdapterRegistry()  # no adapters — isolate state
            ctx = _make_context()
            run_lifecycle(store, registry, ctx, "open_day")
            # Extract key prefixes (everything before the last '.' segment)
            prefixes = {k.rsplit(".", 1)[0] for k in store.keys() if "." in k}
            key_prefixes_list.append(prefixes)

        assert key_prefixes_list[0] == key_prefixes_list[1]

    def test_replay_produces_same_mutations(self) -> None:
        """Replaying yields the same mutation count."""
        counts = []
        for _ in range(2):
            store = _empty_store()
            registry = AdapterRegistry()
            ctx = _make_context()
            output = run_lifecycle(store, registry, ctx, "open_day")
            counts.append(output["mutations_count"])

        assert counts[0] == counts[1]


# ─── 8. no direct adapter imports in lifecycle ────────────────────────


class TestNoAdapterImports:
    def test_lifecycle_does_not_import_stubs(self) -> None:
        """lifecycle.py must not import DiscordAdapter, NotionAdapter, etc."""
        source = inspect.getsource(sys.modules["umh.runtime_loop.lifecycle"])
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
        assert not violations, f"lifecycle.py imports adapters directly: {violations}"

    def test_lifecycle_does_not_import_discord(self) -> None:
        """lifecycle.py must not import discord or notion modules."""
        source = inspect.getsource(sys.modules["umh.runtime_loop.lifecycle"])

        # Check for raw module imports
        assert "import discord" not in source
        assert "from discord" not in source
        assert "import notion" not in source
        assert "from notion" not in source


# ─── 9. correct event count (8 steps + start + complete = 10) ────────


class TestEventCount:
    def test_open_day_emits_10_events(self) -> None:
        """8 step events + 1 started + 1 completed = 10."""
        store = _empty_store()
        registry = AdapterRegistry()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "open_day")

        assert output["events_count"] == 10

    def test_close_day_emits_10_events(self) -> None:
        """8 step events + 1 started + 1 completed = 10."""
        store = _empty_store()
        registry = AdapterRegistry()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "close_day")

        assert output["events_count"] == 10

    def test_dispatch_log_matches_event_count_times_adapters(self) -> None:
        """With 3 adapters, dispatch_log has 10 * 3 = 30 entries."""
        store = _empty_store()
        registry = _make_registry_with_stubs()
        ctx = _make_context()

        output = run_lifecycle(store, registry, ctx, "open_day")

        # 10 events × 3 adapters = 30 dispatch entries
        assert len(output["dispatch_log"]) == 30
