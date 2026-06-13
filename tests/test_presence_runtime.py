"""Tests for Phase 8: Presence Runtime.

Covers all components: enums, data models, DeviceRegistry, SessionRegistry,
AttentionEngine, InterruptibilityEngine, PresenceTimeline, PresenceRuntime,
singleton, integration hooks, and acceptance tests.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.presence_runtime import (
    AttentionEngine,
    DeviceInfo,
    DeviceRegistry,
    InteractionSurface,
    InterruptibilityEngine,
    InterruptionLevel,
    PresenceAttentionState,
    PresenceEvent,
    PresenceEventType,
    PresenceRuntime,
    PresenceSnapshot,
    SessionInfo,
    SessionRegistry,
    PresenceTimeline,
    get_presence_runtime,
    reset_presence_runtime,
)


# ── Enum Tests ─────────────────────────────────────────────────────


class TestPresenceAttentionState:
    def test_values(self):
        assert PresenceAttentionState.FOCUSED.value == "focused"
        assert PresenceAttentionState.AVAILABLE.value == "available"
        assert PresenceAttentionState.AWAY.value == "away"
        assert PresenceAttentionState.OFFLINE.value == "offline"
        assert PresenceAttentionState.SLEEPING.value == "sleeping"

    def test_is_present(self):
        assert PresenceAttentionState.FOCUSED.is_present is True
        assert PresenceAttentionState.AVAILABLE.is_present is True
        assert PresenceAttentionState.AWAY.is_present is False
        assert PresenceAttentionState.OFFLINE.is_present is False
        assert PresenceAttentionState.SLEEPING.is_present is False

    def test_is_absent(self):
        assert PresenceAttentionState.FOCUSED.is_absent is False
        assert PresenceAttentionState.AVAILABLE.is_absent is False
        assert PresenceAttentionState.AWAY.is_absent is True
        assert PresenceAttentionState.OFFLINE.is_absent is True
        assert PresenceAttentionState.SLEEPING.is_absent is True


class TestInterruptionLevel:
    def test_values(self):
        assert InterruptionLevel.CRITICAL_ONLY.value == "critical_only"
        assert InterruptionLevel.NORMAL.value == "normal"
        assert InterruptionLevel.QUEUE.value == "queue"
        assert InterruptionLevel.DEFER.value == "defer"


class TestPresenceEventType:
    def test_all_event_types(self):
        types = [e.value for e in PresenceEventType]
        assert "operator_present" in types
        assert "operator_absent" in types
        assert "session_started" in types
        assert "session_ended" in types
        assert "profile_changed" in types
        assert "attention_changed" in types
        assert "device_changed" in types
        assert len(types) == 10


class TestInteractionSurface:
    def test_values(self):
        assert InteractionSurface.COCKPIT_BROWSER.value == "cockpit_browser"
        assert InteractionSurface.TERMINAL_SSH.value == "terminal_ssh"
        assert InteractionSurface.NONE.value == "none"


# ── Data Model Tests ──────────────────────────────────────────────


class TestDeviceInfo:
    def test_creation(self):
        d = DeviceInfo(device_id="vps", device_type="vps", display_name="srv1500858 (VPS)")
        assert d.device_id == "vps"
        assert d.online is False

    def test_round_trip(self):
        d = DeviceInfo(device_id="beast", device_type="pc", online=True, session_count=2)
        data = d.to_dict()
        d2 = DeviceInfo.from_dict(data)
        assert d2.device_id == "beast"
        assert d2.online is True
        assert d2.session_count == 2

    def test_os_field_mapping(self):
        d = DeviceInfo.from_dict({"device_id": "x", "os": "linux"})
        assert d.os_type == "linux"


class TestSessionInfo:
    def test_creation_defaults(self):
        s = SessionInfo()
        assert s.session_id.startswith("ses-")
        assert s.status == "active"
        assert s.started_at > 0

    def test_round_trip(self):
        s = SessionInfo(
            session_id="ses-test",
            host="vps",
            device_id="vps",
            profile_mode="developer",
        )
        data = s.to_dict()
        s2 = SessionInfo.from_dict(data)
        assert s2.session_id == "ses-test"
        assert s2.profile_mode == "developer"


class TestPresenceSnapshot:
    def test_creation_defaults(self):
        snap = PresenceSnapshot()
        assert snap.snapshot_id.startswith("psnap-")
        assert snap.operator_present is False
        assert snap.attention_state == "offline"
        assert snap.interruption_budget == "defer"

    def test_round_trip(self):
        snap = PresenceSnapshot(
            operator_present=True,
            active_device="vps",
            attention_state="focused",
            interruption_budget="critical_only",
        )
        data = snap.to_dict()
        snap2 = PresenceSnapshot.from_dict(data)
        assert snap2.operator_present is True
        assert snap2.active_device == "vps"
        assert snap2.attention_state == "focused"

    def test_with_devices_and_sessions(self):
        snap = PresenceSnapshot(
            devices=[{"device_id": "vps", "online": True}],
            sessions=[{"session_id": "s1", "status": "active"}],
        )
        data = snap.to_dict()
        assert len(data["devices"]) == 1
        assert len(data["sessions"]) == 1


class TestPresenceEvent:
    def test_creation_defaults(self):
        e = PresenceEvent(event_type="test", summary="test event")
        assert e.event_id.startswith("pevt-")
        assert e.timestamp > 0

    def test_round_trip(self):
        e = PresenceEvent(
            event_type="session_started",
            summary="Session started",
            details={"session_id": "s1"},
        )
        data = e.to_dict()
        e2 = PresenceEvent.from_dict(data)
        assert e2.event_type == "session_started"
        assert e2.details["session_id"] == "s1"


# ── Session Registry Tests ────────────────────────────────────────


class TestSessionRegistry:
    def test_register_and_get(self):
        reg = SessionRegistry()
        s = reg.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        assert s.session_id == "s1"
        assert reg.get_session("s1") is not None

    def test_multiple_sessions(self):
        reg = SessionRegistry()
        reg.register_session("s0", host="vps", device_id="vps")
        reg.register_session("s1", host="beast", device_id="beast")
        reg.register_session("s2", host="vps", device_id="vps")
        assert len(reg.get_active_sessions()) == 3

    def test_end_session(self):
        reg = SessionRegistry()
        reg.register_session("s1", host="vps")
        s = reg.end_session("s1")
        assert s is not None
        assert s.status == "ended"
        assert len(reg.get_active_sessions()) == 0

    def test_primary_session_most_recent(self):
        reg = SessionRegistry()
        reg.register_session("s1", host="vps")
        time.sleep(0.01)
        reg.register_session("s2", host="beast")
        primary = reg.get_primary_session()
        assert primary is not None
        assert primary.session_id == "s2"

    def test_heartbeat(self):
        reg = SessionRegistry()
        reg.register_session("s1", host="vps", profile_mode="developer")
        result = reg.heartbeat("s1", {"profile_mode": "research"})
        assert result is True
        s = reg.get_session("s1")
        assert s is not None
        assert s.profile_mode == "research"

    def test_heartbeat_unknown(self):
        reg = SessionRegistry()
        assert reg.heartbeat("nonexistent") is False

    def test_session_history(self):
        reg = SessionRegistry()
        reg.register_session("s1", host="vps")
        reg.end_session("s1")
        history = reg.get_session_history()
        assert len(history) == 1
        assert history[0]["session_id"] == "s1"

    def test_end_nonexistent(self):
        reg = SessionRegistry()
        result = reg.end_session("nonexistent")
        assert result is None


# ── Attention Engine Tests ────────────────────────────────────────


class TestAttentionEngine:
    def test_initial_state(self):
        engine = AttentionEngine()
        assert engine.state == PresenceAttentionState.OFFLINE

    def test_record_interaction_with_profile(self):
        engine = AttentionEngine()
        state = engine.record_interaction("developer")
        assert state == PresenceAttentionState.FOCUSED

    def test_record_interaction_without_profile(self):
        engine = AttentionEngine()
        state = engine.record_interaction()
        assert state == PresenceAttentionState.AVAILABLE

    def test_update_no_sessions(self):
        engine = AttentionEngine()
        engine.record_interaction("developer")
        state = engine.update(has_active_sessions=False)
        assert state == PresenceAttentionState.OFFLINE

    def test_update_with_sessions_recent(self):
        engine = AttentionEngine()
        engine.record_interaction("developer")
        state = engine.update(has_active_sessions=True, profile_mode="developer")
        assert state == PresenceAttentionState.FOCUSED

    def test_update_available_without_profile(self):
        engine = AttentionEngine()
        engine.record_interaction()
        state = engine.update(has_active_sessions=True)
        assert state == PresenceAttentionState.AVAILABLE

    def test_away_after_threshold(self):
        engine = AttentionEngine()
        engine._last_interaction = time.time() - 400
        state = engine.update(has_active_sessions=True)
        assert state == PresenceAttentionState.AWAY

    def test_sleeping_after_threshold(self):
        engine = AttentionEngine()
        engine._last_interaction = time.time() - 25000
        state = engine.update(has_active_sessions=True)
        assert state == PresenceAttentionState.SLEEPING

    def test_to_dict(self):
        engine = AttentionEngine()
        engine.record_interaction("developer")
        d = engine.to_dict()
        assert d["state"] == "focused"
        assert d["active_profile"] == "developer"
        assert d["last_interaction"] > 0


# ── Interruptibility Engine Tests ─────────────────────────────────


class TestInterruptibilityEngine:
    def test_focused_critical_only(self):
        engine = InterruptibilityEngine()
        level = engine.get_interruption_level(PresenceAttentionState.FOCUSED)
        assert level == InterruptionLevel.CRITICAL_ONLY

    def test_available_normal(self):
        engine = InterruptibilityEngine()
        level = engine.get_interruption_level(PresenceAttentionState.AVAILABLE)
        assert level == InterruptionLevel.NORMAL

    def test_away_queue(self):
        engine = InterruptibilityEngine()
        level = engine.get_interruption_level(PresenceAttentionState.AWAY)
        assert level == InterruptionLevel.QUEUE

    def test_offline_defer(self):
        engine = InterruptibilityEngine()
        level = engine.get_interruption_level(PresenceAttentionState.OFFLINE)
        assert level == InterruptionLevel.DEFER

    def test_sleeping_defer(self):
        engine = InterruptibilityEngine()
        level = engine.get_interruption_level(PresenceAttentionState.SLEEPING)
        assert level == InterruptionLevel.DEFER

    def test_should_surface_available(self):
        engine = InterruptibilityEngine()
        assert engine.should_surface(PresenceAttentionState.AVAILABLE, False) is True
        assert engine.should_surface(PresenceAttentionState.AVAILABLE, True) is True

    def test_should_surface_focused(self):
        engine = InterruptibilityEngine()
        assert engine.should_surface(PresenceAttentionState.FOCUSED, False) is False
        assert engine.should_surface(PresenceAttentionState.FOCUSED, True) is True

    def test_should_surface_away(self):
        engine = InterruptibilityEngine()
        assert engine.should_surface(PresenceAttentionState.AWAY, False) is False
        assert engine.should_surface(PresenceAttentionState.AWAY, True) is False

    def test_recommendation_filter(self):
        engine = InterruptibilityEngine()
        assert engine.get_recommendation_filter(PresenceAttentionState.FOCUSED) == "suppress"
        assert engine.get_recommendation_filter(PresenceAttentionState.AVAILABLE) == "normal"
        assert engine.get_recommendation_filter(PresenceAttentionState.AWAY) == "accumulate"
        assert engine.get_recommendation_filter(PresenceAttentionState.OFFLINE) == "defer"


# ── Presence Timeline Tests ───────────────────────────────────────


class TestPresenceTimeline:
    def test_emit_and_get(self):
        with tempfile.TemporaryDirectory() as td:
            tl = PresenceTimeline(td)
            tl.emit("session_started", "Session started", {"session_id": "s1"})
            events = tl.get_events()
            assert len(events) == 1
            assert events[0]["event_type"] == "session_started"

    def test_filter_by_type(self):
        with tempfile.TemporaryDirectory() as td:
            tl = PresenceTimeline(td)
            tl.emit("session_started", "Start")
            tl.emit("session_ended", "End")
            tl.emit("session_started", "Start 2")
            events = tl.get_events(event_type="session_started")
            assert len(events) == 2

    def test_filter_by_time(self):
        with tempfile.TemporaryDirectory() as td:
            tl = PresenceTimeline(td)
            tl.emit("session_started", "Old")
            ts = time.time()
            time.sleep(0.01)
            tl.emit("session_started", "New")
            events = tl.get_events(since=ts)
            assert len(events) == 1
            assert events[0]["summary"] == "New"

    def test_limit(self):
        with tempfile.TemporaryDirectory() as td:
            tl = PresenceTimeline(td)
            for i in range(10):
                tl.emit("test", f"Event {i}")
            events = tl.get_events(limit=3)
            assert len(events) == 3

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            tl = PresenceTimeline(td)
            tl.emit("test", "Persisted event")
            path = os.path.join(td, "events.jsonl")
            assert os.path.exists(path)
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["summary"] == "Persisted event"

    def test_get_events_between(self):
        with tempfile.TemporaryDirectory() as td:
            tl = PresenceTimeline(td)
            t1 = time.time()
            tl.emit("a", "First")
            time.sleep(0.01)
            t2 = time.time()
            tl.emit("b", "Second")
            time.sleep(0.01)
            t3 = time.time()
            tl.emit("c", "Third")
            events = tl.get_events_between(t2, t3 + 1)
            assert len(events) >= 1


# ── Device Registry Tests ─────────────────────────────────────────


class TestDeviceRegistry:
    def test_loads_static_devices(self):
        reg = DeviceRegistry()
        devices = reg.get_all_devices()
        assert len(devices) >= 1

    def test_get_device(self):
        reg = DeviceRegistry()
        d = reg.get_device("vps")
        if d:
            assert d.device_id == "vps"
            assert d.display_name != ""


# ── Presence Runtime Tests ────────────────────────────────────────


class TestPresenceRuntime:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.rt = PresenceRuntime(data_dir=str(tmp_path))

    def test_initial_status(self):
        status = self.rt.get_status()
        assert status["operator_present"] is False
        assert status["attention_state"] == "offline"
        assert status["active_session_count"] == 0

    def test_register_session(self):
        s = self.rt.register_session(
            "s1", host="vps", device_id="vps",
            profile_mode="developer",
            interaction_surface="cockpit_browser",
        )
        assert s.session_id == "s1"
        status = self.rt.get_status()
        assert status["active_session_count"] == 1
        assert status["active_device"] == "vps"
        assert status["active_profile_mode"] == "developer"

    def test_end_session(self):
        self.rt.register_session("s1", host="vps", device_id="vps")
        self.rt.end_session("s1")
        status = self.rt.get_status()
        assert status["operator_present"] is False
        assert status["active_session_count"] == 0

    def test_multi_session(self):
        self.rt.register_session("s0", host="vps", device_id="vps")
        self.rt.register_session("s1", host="beast", device_id="beast")
        status = self.rt.get_status()
        assert status["active_session_count"] == 2
        self.rt.end_session("s0")
        status = self.rt.get_status()
        assert status["active_session_count"] == 1
        assert status["operator_present"] is True

    def test_capture_snapshot(self):
        self.rt.register_session(
            "s1", host="vps", device_id="vps",
            profile_mode="developer",
        )
        snap = self.rt.capture_snapshot()
        assert snap.operator_present is True
        assert snap.active_device == "vps"
        assert snap.attention_state == "focused"
        assert snap.interruption_budget == "critical_only"

    def test_capture_snapshot_no_sessions(self):
        snap = self.rt.capture_snapshot()
        assert snap.operator_present is False
        assert snap.attention_state == "offline"
        assert snap.interruption_budget == "defer"

    def test_record_interaction(self):
        self.rt.register_session("s1", host="vps", device_id="vps")
        result = self.rt.record_interaction("developer")
        assert result["state"] == "focused"

    def test_change_profile(self):
        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        result = self.rt.change_profile("research")
        assert result["profile_mode"] == "research"

    def test_heartbeat(self):
        self.rt.register_session("s1", host="vps", device_id="vps")
        result = self.rt.heartbeat("s1", {"profile_mode": "music"})
        assert result is True

    def test_interruptibility_focused(self):
        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        assert self.rt.should_interrupt(is_critical=False) is False
        assert self.rt.should_interrupt(is_critical=True) is True

    def test_interruptibility_no_sessions(self):
        assert self.rt.should_interrupt(is_critical=False) is False
        assert self.rt.should_interrupt(is_critical=True) is False

    def test_get_timeline(self):
        self.rt.register_session("s1", host="vps", device_id="vps")
        events = self.rt.get_timeline()
        assert len(events) >= 1
        types = [e["event_type"] for e in events]
        assert "session_started" in types

    def test_operator_present_absent_events(self):
        self.rt.register_session("s1", host="vps", device_id="vps")
        self.rt.end_session("s1")
        events = self.rt.get_timeline()
        types = [e["event_type"] for e in events]
        assert "operator_present" in types
        assert "operator_absent" in types

    def test_get_snapshot_none(self):
        assert self.rt.get_snapshot() is None

    def test_get_snapshot_after_capture(self):
        self.rt.register_session("s1", host="vps", device_id="vps")
        self.rt.capture_snapshot()
        snap = self.rt.get_snapshot()
        assert snap is not None
        assert snap["operator_present"] is True

    def test_session_history(self):
        self.rt.register_session("s1", host="vps", device_id="vps")
        self.rt.end_session("s1")
        history = self.rt.get_session_history()
        assert len(history) == 1

    def test_devices(self):
        devices = self.rt.get_devices()
        assert isinstance(devices, list)

    def test_recommendation_filter_focused(self):
        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        assert self.rt.get_recommendation_filter() == "suppress"

    def test_recommendation_filter_offline(self):
        assert self.rt.get_recommendation_filter() == "defer"


# ── Singleton Tests ───────────────────────────────────────────────


class TestSingleton:
    def test_singleton_returns_same(self):
        reset_presence_runtime()
        rt1 = get_presence_runtime()
        rt2 = get_presence_runtime()
        assert rt1 is rt2
        reset_presence_runtime()

    def test_reset_clears(self):
        reset_presence_runtime()
        rt1 = get_presence_runtime()
        reset_presence_runtime()
        rt2 = get_presence_runtime()
        assert rt1 is not rt2
        reset_presence_runtime()


# ── Integration Hook Tests ────────────────────────────────────────


class TestIntegrationHooks:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.rt = PresenceRuntime(data_dir=str(tmp_path))

    def test_continuity_presence_input(self):
        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        data = self.rt.get_continuity_presence_input()
        assert data["operator_present"] is True
        assert data["attention_state"] == "focused"
        assert data["active_profile_mode"] == "developer"
        assert data["interruption_budget"] == "critical_only"

    def test_tick_loop_filter(self):
        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        data = self.rt.get_tick_loop_filter()
        assert data["recommendation_filter"] == "suppress"
        assert data["should_surface_normal"] is False
        assert data["should_surface_critical"] is True

    def test_projection_context(self):
        self.rt.register_session(
            "s1", host="vps", device_id="vps",
            profile_mode="research",
            interaction_surface="terminal_ssh",
        )
        data = self.rt.get_projection_context()
        assert data["operator_state"] == "focused"
        assert data["profile_mode"] == "research"
        assert data["interaction_surface"] == "terminal_ssh"

    def test_integration_hooks_offline(self):
        data = self.rt.get_continuity_presence_input()
        assert data["operator_present"] is False
        assert data["interruption_budget"] == "defer"

        data = self.rt.get_tick_loop_filter()
        assert data["recommendation_filter"] == "defer"
        assert data["should_surface_normal"] is False
        assert data["should_surface_critical"] is False


# ── Acceptance Tests ──────────────────────────────────────────────


class TestAcceptance:
    """End-to-end acceptance tests verifying Phase 8 requirements."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.rt = PresenceRuntime(data_dir=str(tmp_path))

    def test_device_registration(self):
        """Requirement 2: Device registry loads and enriches static devices."""
        devices = self.rt.get_devices()
        assert isinstance(devices, list)
        if devices:
            d = devices[0]
            assert "device_id" in d
            assert "display_name" in d
            assert "online" in d

    def test_multi_session_support(self):
        """Requirement 3: Multiple concurrent sessions supported."""
        self.rt.register_session("s0", host="vps", device_id="vps", profile_mode="developer")
        self.rt.register_session("s1", host="beast", device_id="beast", profile_mode="research")
        self.rt.register_session("s2", host="vps", device_id="vps", profile_mode="content")

        sessions = self.rt.get_active_sessions()
        assert len(sessions) == 3

        status = self.rt.get_status()
        assert status["active_session_count"] == 3
        assert status["operator_present"] is True

        self.rt.end_session("s0")
        self.rt.end_session("s2")
        status = self.rt.get_status()
        assert status["active_session_count"] == 1
        assert status["operator_present"] is True

    def test_presence_transitions(self):
        """Requirement 4/8: Attention state transitions correctly."""
        assert self.rt.attention.state == PresenceAttentionState.OFFLINE

        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        assert self.rt.attention.state == PresenceAttentionState.FOCUSED

        self.rt.record_interaction()
        assert self.rt.attention.state.is_present

        self.rt.end_session("s1")
        snap = self.rt.capture_snapshot()
        assert snap.attention_state == "offline"

    def test_attention_transitions(self):
        """Requirement 4: Full lifecycle focused → available → away → sleeping → offline."""
        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        assert self.rt.attention.state == PresenceAttentionState.FOCUSED

        self.rt.attention._active_profile = ""
        self.rt.attention._last_interaction = time.time()
        self.rt.attention.update(True)
        assert self.rt.attention.state == PresenceAttentionState.AVAILABLE

        self.rt.attention._last_interaction = time.time() - 400
        self.rt.attention.update(True)
        assert self.rt.attention.state == PresenceAttentionState.AWAY

        self.rt.attention._last_interaction = time.time() - 25000
        self.rt.attention.update(True)
        assert self.rt.attention.state == PresenceAttentionState.SLEEPING

        self.rt.attention.update(False)
        assert self.rt.attention.state == PresenceAttentionState.OFFLINE

    def test_event_emission(self):
        """Requirement 8: Canonical events emitted for all state changes."""
        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        self.rt.change_profile("research")
        self.rt.end_session("s1")

        events = self.rt.get_timeline()
        types = set(e["event_type"] for e in events)

        assert "operator_present" in types
        assert "session_started" in types
        assert "profile_changed" in types
        assert "session_ended" in types
        assert "operator_absent" in types

    def test_continuity_integration(self):
        """Requirement 9: Presence feeds into continuity/tick/projection systems."""
        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")

        cont = self.rt.get_continuity_presence_input()
        assert cont["operator_present"] is True
        assert cont["attention_state"] == "focused"

        tick = self.rt.get_tick_loop_filter()
        assert tick["recommendation_filter"] == "suppress"

        proj = self.rt.get_projection_context()
        assert proj["operator_state"] == "focused"
        assert proj["profile_mode"] == "developer"

    def test_interruptibility_rules(self):
        """Requirement 5: Interruptibility follows attention state."""
        self.rt.register_session("s1", host="vps", device_id="vps", profile_mode="developer")
        assert self.rt.get_interruption_level() == "critical_only"
        assert self.rt.should_interrupt(is_critical=False) is False
        assert self.rt.should_interrupt(is_critical=True) is True

        self.rt.attention._active_profile = ""
        self.rt.attention._last_interaction = time.time()
        self.rt.attention.update(True)
        assert self.rt.get_interruption_level() == "normal"
        assert self.rt.should_interrupt(is_critical=False) is True

        self.rt.attention._last_interaction = time.time() - 400
        self.rt.attention.update(True)
        assert self.rt.get_interruption_level() == "queue"
        assert self.rt.should_interrupt(is_critical=False) is False

    def test_full_presence_lifecycle(self):
        """Full lifecycle: offline → register → interact → profile change → snapshot → end → absent."""
        assert self.rt.get_status()["operator_present"] is False

        self.rt.register_session(
            "s1", host="vps", device_id="vps",
            profile_mode="developer",
            interaction_surface="cockpit_browser",
        )
        status = self.rt.get_status()
        assert status["operator_present"] is True
        assert status["attention_state"] == "focused"

        self.rt.record_interaction("developer")
        snap = self.rt.capture_snapshot()
        assert snap.operator_present is True
        assert snap.active_device == "vps"
        assert snap.interaction_surface == "cockpit_browser"
        assert snap.interruption_budget == "critical_only"

        self.rt.change_profile("research")
        snap2 = self.rt.capture_snapshot()
        assert snap2.active_profile_mode == "research"

        self.rt.end_session("s1")
        status = self.rt.get_status()
        assert status["operator_present"] is False

        events = self.rt.get_timeline()
        types = [e["event_type"] for e in events]
        assert "operator_present" in types
        assert "session_started" in types
        assert "profile_changed" in types
        assert "session_ended" in types
        assert "operator_absent" in types

    def test_governance_boundary(self):
        """Requirement 11: Presence may observe/classify/recommend but NOT execute/approve/modify."""
        rt = self.rt
        assert hasattr(rt, "capture_snapshot")
        assert hasattr(rt, "get_status")
        assert hasattr(rt, "get_recommendation_filter")
        assert not hasattr(rt, "execute_action")
        assert not hasattr(rt, "approve_work")
        assert not hasattr(rt, "modify_goal")
