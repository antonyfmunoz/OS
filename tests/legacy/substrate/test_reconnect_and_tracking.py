"""
Tests for workstation reconnect handshake, state sync, action tracking,
ACK flow, and lifecycle event emission.

Covers Phases 2-7 of the workstation reliability pass.
"""

import sys
import time
import uuid

sys.path.insert(0, "/opt/OS")

import pytest

from umh.substrate.action_tracker import (
    ActionTracker,
    TrackedAction,
    TrackedState,
    TransitionResult,
    reset_tracker_for_tests,
)
from umh.substrate.actions import ActionKind, ActionResult, ActionStatus, SafeAction
from umh.substrate.event_spine import EventType
from umh.substrate.nodes import Node, NodeRegistry, NodeRole, NodeStatus, NodeType


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_singletons():
    """Reset singletons between tests."""
    NodeRegistry.reset_default_for_tests()
    reset_tracker_for_tests()
    yield
    NodeRegistry.reset_default_for_tests()
    reset_tracker_for_tests()


def _make_tracker() -> ActionTracker:
    """Non-persisting tracker for tests."""
    return ActionTracker(persist=False)


def _make_registry() -> NodeRegistry:
    """Non-persisting registry for tests."""
    return NodeRegistry(persist=False)


# ════════════════════════════════════════════════════════════════════════════
# Phase 1: Action Tracker — lifecycle state machine
# ════════════════════════════════════════════════════════════════════════════


class TestActionTrackerLifecycle:
    """Verify the action lifecycle state machine."""

    def test_track_creates_entry(self):
        tracker = _make_tracker()
        tracked = tracker.track("act_001", "speak_text", "ws-1")
        assert tracked.action_id == "act_001"
        assert tracked.state == TrackedState.PENDING
        assert tracked.target_node_id == "ws-1"
        assert tracked.kind == "speak_text"

    def test_full_lifecycle_happy_path(self):
        tracker = _make_tracker()
        tracker.track("act_001", "speak_text", "ws-1")

        r1 = tracker.mark_dispatched("act_001")
        assert r1.success
        assert r1.previous_state == TrackedState.PENDING
        assert r1.new_state == TrackedState.DISPATCHED

        r2 = tracker.mark_acknowledged("act_001")
        assert r2.success
        assert r2.previous_state == TrackedState.DISPATCHED

        r3 = tracker.mark_completed("act_001", detail="spoke text")
        assert r3.success
        assert r3.previous_state == TrackedState.ACKNOWLEDGED

        a = tracker.get("act_001")
        assert a is not None
        assert a.state == TrackedState.COMPLETED
        assert a.dispatched_at is not None
        assert a.acknowledged_at is not None
        assert a.completed_at is not None

    def test_skip_ack_direct_completion(self):
        """Legacy path: DISPATCHED → COMPLETED without ACK."""
        tracker = _make_tracker()
        tracker.track("act_002", "open_url", "ws-1")
        tracker.mark_dispatched("act_002")
        r = tracker.mark_completed("act_002")
        assert r.success

    def test_invalid_transition_rejected(self):
        tracker = _make_tracker()
        tracker.track("act_003", "play_sound", "ws-1")

        # PENDING → ACKNOWLEDGED is invalid (must go through DISPATCHED)
        r = tracker.mark_acknowledged("act_003")
        assert not r.success
        assert "invalid transition" in r.reason

    def test_terminal_state_blocks_further_transitions(self):
        tracker = _make_tracker()
        tracker.track("act_004", "speak_text", "ws-1")
        tracker.mark_dispatched("act_004")
        tracker.mark_completed("act_004")

        # COMPLETED → FAILED should fail
        r = tracker.mark_failed("act_004")
        assert not r.success

    def test_expired_transition(self):
        tracker = _make_tracker()
        tracker.track("act_005", "open_url", "ws-1")
        tracker.mark_dispatched("act_005")

        r = tracker.mark_expired("act_005", detail="TTL elapsed")
        assert r.success
        assert tracker.get("act_005").state == TrackedState.EXPIRED

    def test_failed_transition(self):
        tracker = _make_tracker()
        tracker.track("act_006", "launch_app", "ws-1")
        tracker.mark_dispatched("act_006")
        tracker.mark_acknowledged("act_006")

        r = tracker.mark_failed("act_006", detail="handler crashed")
        assert r.success
        assert tracker.get("act_006").state == TrackedState.FAILED

    def test_unknown_action_id(self):
        tracker = _make_tracker()
        r = tracker.mark_dispatched("nonexistent")
        assert not r.success
        assert "not tracked" in r.reason


# ════════════════════════════════════════════════════════════════════════════
# Phase 2: Action Tracker — queries
# ════════════════════════════════════════════════════════════════════════════


class TestActionTrackerQueries:
    def test_by_node(self):
        tracker = _make_tracker()
        tracker.track("a1", "speak_text", "ws-1")
        tracker.track("a2", "open_url", "ws-2")
        tracker.track("a3", "play_sound", "ws-1")

        ws1_actions = tracker.by_node("ws-1")
        assert len(ws1_actions) == 2
        assert all(a.target_node_id == "ws-1" for a in ws1_actions)

    def test_by_state(self):
        tracker = _make_tracker()
        tracker.track("a1", "speak_text", "ws-1")
        tracker.track("a2", "open_url", "ws-1")
        tracker.mark_dispatched("a2")

        pending = tracker.by_state(TrackedState.PENDING)
        dispatched = tracker.by_state(TrackedState.DISPATCHED)
        assert len(pending) == 1
        assert len(dispatched) == 1

    def test_pending_for_node(self):
        tracker = _make_tracker()
        tracker.track("a1", "speak_text", "ws-1")
        tracker.mark_dispatched("a1")
        tracker.track("a2", "open_url", "ws-1")
        tracker.track("a3", "play_sound", "ws-1")
        tracker.mark_dispatched("a3")
        tracker.mark_completed("a3")

        pending = tracker.pending_for_node("ws-1")
        # a1 (dispatched) + a2 (pending) — a3 is completed
        assert len(pending) == 2
        ids = {a.action_id for a in pending}
        assert ids == {"a1", "a2"}

    def test_is_pending(self):
        tracker = _make_tracker()
        tracker.track("a1", "speak_text", "ws-1")
        assert tracker.is_pending("a1") is True

        tracker.mark_dispatched("a1")
        tracker.mark_completed("a1")
        assert tracker.is_pending("a1") is False

    def test_stats(self):
        tracker = _make_tracker()
        tracker.track("a1", "speak_text", "ws-1")
        tracker.track("a2", "open_url", "ws-1")
        tracker.mark_dispatched("a1")
        tracker.mark_completed("a1")

        stats = tracker.stats()
        assert stats["total_tracked"] == 2
        assert stats["by_state"]["completed"] == 1
        assert stats["by_state"]["pending"] == 1
        # Only non-terminal actions count in active_per_node
        assert stats["active_per_node"]["ws-1"] == 1


# ════════════════════════════════════════════════════════════════════════════
# Phase 3: Reconnect — TTL expiry on reconnect
# ════════════════════════════════════════════════════════════════════════════


class TestReconnectSync:
    def test_expire_stale_for_node(self):
        """Actions with elapsed TTL should expire on reconnect."""
        tracker = _make_tracker()

        # Create an action with 0-second TTL (immediately expired)
        tracker.track(
            "old_action",
            "speak_text",
            "ws-1",
            ttl_seconds=0,
            issued_at="2020-01-01T00:00:00+00:00",
        )
        tracker.mark_dispatched("old_action")

        # Also a fresh action
        tracker.track("fresh_action", "open_url", "ws-1", ttl_seconds=3600)
        tracker.mark_dispatched("fresh_action")

        expired = tracker.expire_stale_for_node("ws-1")
        assert "old_action" in expired
        assert "fresh_action" not in expired

        assert tracker.get("old_action").state == TrackedState.EXPIRED
        assert tracker.get("fresh_action").state == TrackedState.DISPATCHED

    def test_get_valid_pending_for_node(self):
        tracker = _make_tracker()

        tracker.track(
            "expired_one",
            "speak_text",
            "ws-1",
            ttl_seconds=0,
            issued_at="2020-01-01T00:00:00+00:00",
        )
        tracker.track("valid_one", "open_url", "ws-1", ttl_seconds=3600)

        valid = tracker.get_valid_pending_for_node("ws-1")
        assert len(valid) == 1
        assert valid[0].action_id == "valid_one"

    def test_expire_does_not_touch_terminal_actions(self):
        tracker = _make_tracker()

        tracker.track(
            "completed_one",
            "speak_text",
            "ws-1",
            ttl_seconds=0,
            issued_at="2020-01-01T00:00:00+00:00",
        )
        tracker.mark_dispatched("completed_one")
        tracker.mark_completed("completed_one")

        expired = tracker.expire_stale_for_node("ws-1")
        assert "completed_one" not in expired
        assert tracker.get("completed_one").state == TrackedState.COMPLETED

    def test_expire_only_affects_target_node(self):
        tracker = _make_tracker()

        tracker.track(
            "ws1_action",
            "speak_text",
            "ws-1",
            ttl_seconds=0,
            issued_at="2020-01-01T00:00:00+00:00",
        )
        tracker.track(
            "ws2_action",
            "speak_text",
            "ws-2",
            ttl_seconds=0,
            issued_at="2020-01-01T00:00:00+00:00",
        )

        expired = tracker.expire_stale_for_node("ws-1")
        assert "ws1_action" in expired
        assert "ws2_action" not in expired


# ════════════════════════════════════════════════════════════════════════════
# Phase 4: Node reconnect detection
# ════════════════════════════════════════════════════════════════════════════


class TestNodeReconnect:
    def test_first_registration_sets_registered_at(self):
        reg = _make_registry()
        node = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            role=NodeRole.WORKSTATION,
            status=NodeStatus.ONLINE,
            generation_id="gen_001",
        )
        result = reg.upsert(node)
        assert result.registered_at is not None
        assert result.previous_status is None

    def test_reconnect_from_degraded(self):
        reg = _make_registry()

        # First registration
        node1 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
            generation_id="gen_001",
        )
        reg.upsert(node1)

        # Mark degraded (simulating stale heartbeat)
        existing = reg.get("ws-test")
        existing.status = NodeStatus.DEGRADED
        reg._nodes["ws-test"] = existing

        # Re-register (reconnect)
        node2 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
            generation_id="gen_002",
        )
        result = reg.upsert(node2)

        assert result.reconnected_at is not None
        assert result.previous_status == "degraded"

    def test_reconnect_from_offline(self):
        reg = _make_registry()

        node1 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
            generation_id="gen_001",
        )
        reg.upsert(node1)

        existing = reg.get("ws-test")
        existing.status = NodeStatus.OFFLINE
        reg._nodes["ws-test"] = existing

        node2 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
            generation_id="gen_002",
        )
        result = reg.upsert(node2)
        assert result.reconnected_at is not None
        assert result.previous_status == "offline"

    def test_normal_heartbeat_is_not_reconnect(self):
        reg = _make_registry()

        node1 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
            generation_id="gen_001",
        )
        reg.upsert(node1)

        # Same generation, still ONLINE — not a reconnect
        node2 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
            generation_id="gen_001",
        )
        result = reg.upsert(node2)
        assert result.reconnected_at is None
        assert result.previous_status == "online"

    def test_generation_change_triggers_reconnect(self):
        """Different generation_id = daemon restarted = reconnect."""
        reg = _make_registry()

        node1 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
            generation_id="gen_001",
        )
        reg.upsert(node1)

        node2 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
            generation_id="gen_002",  # different!
        )
        result = reg.upsert(node2)
        assert result.reconnected_at is not None

    def test_registered_at_preserved_across_upserts(self):
        reg = _make_registry()

        node1 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
        )
        result1 = reg.upsert(node1)
        original_registered = result1.registered_at

        node2 = Node(
            node_id="ws-test",
            node_type=NodeType.LOCAL_STATION,
            status=NodeStatus.ONLINE,
        )
        result2 = reg.upsert(node2)
        assert result2.registered_at == original_registered


# ════════════════════════════════════════════════════════════════════════════
# Phase 5: Event spine — new event types exist
# ════════════════════════════════════════════════════════════════════════════


class TestEventSpineTypes:
    def test_node_lifecycle_events_exist(self):
        assert EventType.NODE_REGISTERED.value == "node_registered"
        assert EventType.NODE_RECONNECTED.value == "node_reconnected"
        assert EventType.NODE_DEGRADED.value == "node_degraded"

    def test_action_lifecycle_events_exist(self):
        assert EventType.ACTION_DISPATCHED.value == "action_dispatched"
        assert EventType.ACTION_ACKNOWLEDGED.value == "action_acknowledged"
        assert EventType.ACTION_COMPLETED.value == "action_completed"
        assert EventType.ACTION_EXPIRED.value == "action_expired"
        assert EventType.ACTION_FAILED.value == "action_failed"


# ════════════════════════════════════════════════════════════════════════════
# Phase 6: TTL sweep
# ════════════════════════════════════════════════════════════════════════════


class TestTTLSweep:
    def test_sweep_expired_actions(self):
        tracker = _make_tracker()
        tracker.track(
            "old",
            "speak_text",
            "ws-1",
            ttl_seconds=0,
            issued_at="2020-01-01T00:00:00+00:00",
        )
        tracker.track("fresh", "open_url", "ws-1", ttl_seconds=9999)

        expired = tracker.sweep_expired()
        assert "old" in expired
        assert "fresh" not in expired

    def test_sweep_does_not_touch_terminal(self):
        tracker = _make_tracker()
        tracker.track(
            "done",
            "speak_text",
            "ws-1",
            ttl_seconds=0,
            issued_at="2020-01-01T00:00:00+00:00",
        )
        tracker.mark_dispatched("done")
        tracker.mark_completed("done")

        expired = tracker.sweep_expired()
        assert "done" not in expired


# ════════════════════════════════════════════════════════════════════════════
# Phase 7: Eviction
# ════════════════════════════════════════════════════════════════════════════


class TestEviction:
    def test_eviction_removes_oldest_terminal(self):
        tracker = _make_tracker()

        # Fill beyond capacity with completed actions
        for i in range(510):
            aid = f"act_{i:04d}"
            tracker.track(aid, "speak_text", "ws-1")
            tracker.mark_dispatched(aid)
            tracker.mark_completed(aid)

        # Should evict oldest terminals to stay at MAX_TRACKED_ACTIONS
        assert len(tracker._actions) <= 500


# ════════════════════════════════════════════════════════════════════════════
# Phase 8: Health summary integration
# ════════════════════════════════════════════════════════════════════════════


class TestHealthSummary:
    def test_health_summary_includes_reconnect_fields(self):
        from umh.substrate.node_controller import get_node_health_summary

        summary = get_node_health_summary()
        assert "action_tracker" in summary
        assert "nodes" in summary

        # VPS node should be in the summary
        vps_nodes = [n for n in summary["nodes"] if n["node_id"] == "vps-primary"]
        if vps_nodes:
            node = vps_nodes[0]
            assert "generation_id" in node
            assert "registered_at" in node
            assert "reconnected_at" in node
            assert "previous_status" in node
            assert "pending_actions" in node


# ════════════════════════════════════════════════════════════════════════════
# Phase 9: TrackedAction serialization
# ════════════════════════════════════════════════════════════════════════════


class TestTrackedActionSerialization:
    def test_round_trip(self):
        original = TrackedAction(
            action_id="act_001",
            kind="speak_text",
            target_node_id="ws-1",
            issued_by="ea_orchestrator",
            state=TrackedState.ACKNOWLEDGED,
            dispatched_at="2026-04-15T10:00:00+00:00",
            acknowledged_at="2026-04-15T10:00:01+00:00",
        )
        d = original.to_dict()
        restored = TrackedAction.from_dict(d)

        assert restored.action_id == original.action_id
        assert restored.kind == original.kind
        assert restored.state == original.state
        assert restored.dispatched_at == original.dispatched_at
        assert restored.acknowledged_at == original.acknowledged_at
