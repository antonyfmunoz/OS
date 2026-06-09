"""Tests for substrate/workstation/device_presence.py.

Covers: registration, heartbeat, stale cleanup, multiple sessions,
default audio output, and disconnect.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.device_presence import DevicePresenceRegistry, DeviceSession


def make_session(session_id: str = "sess-001", device_id: str = "dev-a") -> DeviceSession:
    return DeviceSession(
        device_id=device_id,
        session_id=session_id,
        client_type="desktop_browser",
        control_surface="fly_cockpit",
        can_capture_audio=True,
        can_play_audio=True,
    )


class TestRegisterSession:
    def test_register_session_is_retrievable(self):
        reg = DevicePresenceRegistry()
        s = make_session("s1", "dev1")
        reg.register_session(s)
        retrieved = reg.get_session("s1")
        assert retrieved is not None
        assert retrieved.device_id == "dev1"
        assert retrieved.session_id == "s1"
        assert retrieved.status == "active"

    def test_re_register_refreshes_last_seen(self):
        reg = DevicePresenceRegistry()
        s = make_session("s2")
        reg.register_session(s)
        first_seen = reg.get_session("s2").last_seen
        time.sleep(0.01)
        reg.register_session(s)
        second_seen = reg.get_session("s2").last_seen
        assert second_seen >= first_seen


class TestHeartbeat:
    def test_heartbeat_updates_last_seen(self):
        reg = DevicePresenceRegistry()
        s = make_session("s3")
        reg.register_session(s)
        old_seen = reg.get_session("s3").last_seen
        time.sleep(0.01)
        result = reg.heartbeat("s3")
        assert result is True
        new_seen = reg.get_session("s3").last_seen
        assert new_seen >= old_seen

    def test_heartbeat_unknown_session_returns_false(self):
        reg = DevicePresenceRegistry()
        assert reg.heartbeat("unknown-session") is False

    def test_heartbeat_updates_optional_fields(self):
        reg = DevicePresenceRegistry()
        s = make_session("s4")
        reg.register_session(s)
        reg.heartbeat("s4", updates={"current_panel": "work"})
        assert reg.get_session("s4").current_panel == "work"

    def test_heartbeat_ignores_immutable_fields(self):
        reg = DevicePresenceRegistry()
        s = make_session("s5", "original-device")
        reg.register_session(s)
        reg.heartbeat("s5", updates={"device_id": "tampered"})
        # device_id must not change
        assert reg.get_session("s5").device_id == "original-device"


class TestStaleSessionCleanup:
    def test_stale_session_cleanup(self):
        reg = DevicePresenceRegistry()
        s = DeviceSession(
            device_id="dev-old",
            session_id="stale-sess",
            last_seen="2020-01-01T00:00:00+00:00",
        )
        reg._sessions["stale-sess"] = s  # inject directly to avoid __post_init__ reset
        cleaned = reg.cleanup_stale(max_age_seconds=1)
        assert cleaned >= 1
        assert reg.get_session("stale-sess").status == "disconnected"

    def test_fresh_session_not_cleaned(self):
        reg = DevicePresenceRegistry()
        s = make_session("fresh-sess")
        reg.register_session(s)
        cleaned = reg.cleanup_stale(max_age_seconds=60)
        assert cleaned == 0
        assert reg.get_session("fresh-sess").status == "active"


class TestMultipleSessions:
    def test_multiple_sessions_coexist(self):
        reg = DevicePresenceRegistry()
        reg.register_session(make_session("m1", "dev-alpha"))
        reg.register_session(make_session("m2", "dev-beta"))
        reg.register_session(make_session("m3", "dev-gamma"))
        active = reg.get_active_sessions()
        ids = {s.session_id for s in active}
        assert {"m1", "m2", "m3"} == ids

    def test_disconnected_not_in_active(self):
        reg = DevicePresenceRegistry()
        reg.register_session(make_session("d1"))
        reg.register_session(make_session("d2"))
        reg.mark_disconnected("d1")
        active = reg.get_active_sessions()
        ids = {s.session_id for s in active}
        assert "d1" not in ids
        assert "d2" in ids


class TestDefaultAudioOutput:
    def test_returns_source_session_as_audio_output(self):
        reg = DevicePresenceRegistry()
        s = make_session("audio-sess")
        reg.register_session(s)
        output = reg.get_default_audio_output("audio-sess")
        assert output == "audio-sess"

    def test_no_audio_session_returns_empty(self):
        reg = DevicePresenceRegistry()
        output = reg.get_default_audio_output("nonexistent")
        assert output == ""

    def test_no_audio_capability_falls_back(self):
        reg = DevicePresenceRegistry()
        s = DeviceSession(device_id="d", session_id="no-audio", can_play_audio=False)
        reg.register_session(s)
        # Source cannot play audio — should return "" since no other session available
        output = reg.get_default_audio_output("no-audio")
        assert output == ""

    def test_fallback_to_other_capable_session(self):
        reg = DevicePresenceRegistry()
        no_audio = DeviceSession(device_id="d1", session_id="no-audio-2", can_play_audio=False)
        has_audio = DeviceSession(device_id="d2", session_id="has-audio", can_play_audio=True)
        reg.register_session(no_audio)
        reg.register_session(has_audio)
        output = reg.get_default_audio_output("no-audio-2")
        assert output == "has-audio"


class TestDisconnect:
    def test_disconnect_marks_status(self):
        reg = DevicePresenceRegistry()
        s = make_session("dc-sess")
        reg.register_session(s)
        assert reg.get_session("dc-sess").status == "active"
        reg.mark_disconnected("dc-sess")
        assert reg.get_session("dc-sess").status == "disconnected"

    def test_disconnect_unknown_session_is_safe(self):
        reg = DevicePresenceRegistry()
        # Should not raise
        reg.mark_disconnected("phantom-session")
