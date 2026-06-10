"""Tests for Phase 14.14B — DEX Vision Embodiment.

Covers: camera command classification, privacy governance,
voice route resolver camera patterns, device presence video capability,
and vision privacy rules.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from substrate.workstation.camera_commands import (
    CameraCommand,
    classify_camera_command,
)
from substrate.workstation.device_presence import DeviceSession
from substrate.workstation.vision_privacy import (
    CameraMode,
    PRIVACY_RULES,
    STREAM_AUTO_TIMEOUT_S,
    get_active_mode,
    validate_analysis_request,
    validate_camera_activation,
    validate_frame_storage,
)
from substrate.workstation.voice_route_resolver import parse_target_node


# ── Camera command classification ────────────────────────────────────

class TestCameraCommandClassification:
    def test_look_at_me(self) -> None:
        cmd = classify_camera_command("look at me")
        assert cmd.operation == "preset"
        assert cmd.preset_name == "operator"

    def test_look_at_keyboard(self) -> None:
        cmd = classify_camera_command("look at my keyboard")
        assert cmd.operation == "preset"
        assert cmd.preset_name == "keyboard"

    def test_look_at_desk(self) -> None:
        cmd = classify_camera_command("look at the desk")
        assert cmd.operation == "preset"
        assert cmd.preset_name == "desk"

    def test_look_at_room(self) -> None:
        cmd = classify_camera_command("look at the room")
        assert cmd.operation == "preset"
        assert cmd.preset_name == "room"

    def test_what_do_you_see(self) -> None:
        cmd = classify_camera_command("what do you see")
        assert cmd.operation == "analyze"
        assert cmd.needs_ai is True

    def test_what_can_you_see(self) -> None:
        cmd = classify_camera_command("what can you see right now")
        assert cmd.operation == "analyze"
        assert cmd.needs_ai is True

    def test_take_snapshot(self) -> None:
        cmd = classify_camera_command("take a snapshot")
        assert cmd.operation == "analyze"

    def test_camera_on(self) -> None:
        cmd = classify_camera_command("turn on the camera")
        assert cmd.operation == "start"

    def test_camera_off(self) -> None:
        cmd = classify_camera_command("turn off the camera")
        assert cmd.operation == "stop"

    def test_camera_status(self) -> None:
        cmd = classify_camera_command("camera status")
        assert cmd.operation == "status"

    def test_save_preset_named(self) -> None:
        cmd = classify_camera_command("save this camera position as monitor")
        assert cmd.operation == "save_preset"
        assert cmd.save_name == "monitor"

    def test_save_preset_default(self) -> None:
        cmd = classify_camera_command("save this position")
        assert cmd.operation == "save_preset"
        assert cmd.save_name == "custom"

    def test_am_i_at_desk(self) -> None:
        cmd = classify_camera_command("am i at my desk")
        assert cmd.operation == "analyze"
        assert cmd.needs_ai is True

    def test_describe_what_you_see(self) -> None:
        cmd = classify_camera_command("describe what you see")
        assert cmd.operation == "analyze"

    def test_fallback_snapshot(self) -> None:
        cmd = classify_camera_command("something about the camera")
        assert cmd.operation == "snapshot"

    def test_posture_check(self) -> None:
        cmd = classify_camera_command("is my posture ok")
        assert cmd.operation == "analyze"
        assert cmd.needs_ai is True


# ── Voice route resolver — camera routes to Beast ────────────────────

class TestCameraVoiceRouting:
    def test_look_at_me_routes_beast(self) -> None:
        assert parse_target_node("look at me") == "beast_windows"

    def test_what_do_you_see_routes_beast(self) -> None:
        assert parse_target_node("what do you see") == "beast_windows"

    def test_camera_on_routes_beast(self) -> None:
        assert parse_target_node("turn on the camera") == "beast_windows"

    def test_camera_off_routes_beast(self) -> None:
        assert parse_target_node("turn off camera") == "beast_windows"

    def test_take_snapshot_routes_beast(self) -> None:
        assert parse_target_node("take a snapshot") == "beast_windows"

    def test_save_position_routes_beast(self) -> None:
        assert parse_target_node("save this camera position") == "beast_windows"

    def test_am_i_at_desk_routes_beast(self) -> None:
        assert parse_target_node("am i at my desk") == "beast_windows"

    def test_non_camera_no_target(self) -> None:
        assert parse_target_node("hello there") == ""

    def test_camera_status_routes_beast(self) -> None:
        assert parse_target_node("camera status") == "beast_windows"

    def test_watch_room_routes_beast(self) -> None:
        assert parse_target_node("watch the room") == "beast_windows"

    def test_analyze_frame_routes_beast(self) -> None:
        assert parse_target_node("analyze this frame") == "beast_windows"


# ── Device presence — video capability ───────────────────────────────

class TestDevicePresenceVideo:
    def test_default_no_video(self) -> None:
        session = DeviceSession(device_id="test", session_id="s1")
        assert session.can_capture_video is False

    def test_video_enabled(self) -> None:
        session = DeviceSession(
            device_id="beast",
            session_id="s2",
            can_capture_video=True,
        )
        assert session.can_capture_video is True

    def test_from_dict_video(self) -> None:
        data = {
            "device_id": "beast",
            "session_id": "s3",
            "can_capture_video": True,
        }
        session = DeviceSession.from_dict(data)
        assert session.can_capture_video is True

    def test_to_dict_includes_video(self) -> None:
        session = DeviceSession(
            device_id="test",
            session_id="s4",
            can_capture_video=True,
        )
        d = session.to_dict()
        assert "can_capture_video" in d
        assert d["can_capture_video"] is True


# ── Privacy governance ───────────────────────────────────────────────

class TestVisionPrivacy:
    def test_ten_privacy_rules(self) -> None:
        assert len(PRIVACY_RULES) == 10

    def test_camera_off_by_default_rule(self) -> None:
        assert any("OFF by default" in r for r in PRIVACY_RULES)

    def test_no_face_recognition_rule(self) -> None:
        assert any("face recognition" in r.lower() for r in PRIVACY_RULES)

    def test_no_hidden_recording_rule(self) -> None:
        assert any("hidden" in r.lower() and "recording" in r.lower() for r in PRIVACY_RULES)

    def test_no_persistent_storage_rule(self) -> None:
        assert any("persistent" in r.lower() and "storage" in r.lower() for r in PRIVACY_RULES)

    def test_auto_timeout(self) -> None:
        assert STREAM_AUTO_TIMEOUT_S == 30 * 60

    def test_default_mode(self) -> None:
        mode = get_active_mode()
        assert mode == CameraMode.SNAPSHOT_ON_REQUEST

    def test_activation_requires_session(self) -> None:
        allowed, _ = validate_camera_activation("")
        assert allowed is False

    def test_activation_with_session(self) -> None:
        allowed, _ = validate_camera_activation("session-123")
        assert allowed is True

    def test_frame_storage_latest_ok(self) -> None:
        allowed, _ = validate_frame_storage("latest_buffer")
        assert allowed is True

    def test_frame_storage_persistent_denied(self) -> None:
        allowed, _ = validate_frame_storage("disk_archive")
        assert allowed is False

    def test_analysis_operator_initiated_ok(self) -> None:
        allowed, _ = validate_analysis_request(is_operator_initiated=True)
        assert allowed is True

    def test_analysis_ambient_denied(self) -> None:
        allowed, _ = validate_analysis_request(is_operator_initiated=False)
        assert allowed is False

    def test_tailscale_only_rule(self) -> None:
        assert any("tailscale" in r.lower() for r in PRIVACY_RULES)

    def test_camera_mode_enum_values(self) -> None:
        assert CameraMode.OFF.value == "camera_off"
        assert CameraMode.PREVIEW_ONLY.value == "preview_only"
        assert CameraMode.AMBIENT_LOW_FREQUENCY.value == "ambient_low_frequency"
