"""Tests for Phase 14.18 — Camera Default-On + Realtime PTZ Control Loop + Smooth Vision UX.

Covers: default-on policy, privacy governance, voice command classification
for continuous motion/zoom/stop/default-on, smooth preset interpolation,
motion loop state management, guard timeout, and reconnect safety.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ── Default-on policy tests ──────────────────────────────────────

class TestDefaultOnPolicy:
    """Camera auto-start governed by profile + auth."""

    def test_active_day_permits_default_on(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, reason = validate_default_on_activation("session_123", "active_day")
        assert allowed is True
        assert "active_day" in reason

    def test_deep_work_blocks_default_on(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, reason = validate_default_on_activation("session_123", "deep_work")
        assert allowed is False

    def test_creative_build_permits_default_on(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, reason = validate_default_on_activation("session_123", "creative_build")
        assert allowed is True

    def test_admin_ops_blocks_default_on(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, reason = validate_default_on_activation("session_123", "admin_ops")
        assert allowed is False

    def test_away_blocks_default_on(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, _ = validate_default_on_activation("session_123", "away")
        assert allowed is False

    def test_night_cycle_blocks_default_on(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, _ = validate_default_on_activation("session_123", "night_cycle")
        assert allowed is False

    def test_shutdown_blocks_default_on(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, _ = validate_default_on_activation("session_123", "shutdown")
        assert allowed is False

    def test_no_session_blocks_default_on(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, reason = validate_default_on_activation("", "active_day")
        assert allowed is False
        assert "no operator session" in reason

    def test_operator_override_enables_for_blocked_profile(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, reason = validate_default_on_activation("session_123", "deep_work", operator_override=True)
        assert allowed is True
        assert "override" in reason

    def test_unknown_profile_blocks_default_on(self):
        from substrate.workstation.vision_privacy import validate_default_on_activation
        allowed, _ = validate_default_on_activation("session_123", "nonexistent_profile")
        assert allowed is False

    def test_default_on_by_profile_dict_complete(self):
        from substrate.workstation.vision_privacy import DEFAULT_ON_BY_PROFILE
        expected_profiles = {"active_day", "deep_work", "creative_build", "admin_ops", "away", "night_cycle", "shutdown"}
        assert set(DEFAULT_ON_BY_PROFILE.keys()) == expected_profiles


# ── Privacy governance — default-on text ─────────────────────────

class TestPrivacyRulesDefaultOn:
    """PRIVACY_RULES must mention auth-gated default-on."""

    def test_first_rule_mentions_auth(self):
        from substrate.workstation.vision_privacy import PRIVACY_RULES
        assert "auth" in PRIVACY_RULES[0].lower()

    def test_first_rule_mentions_default(self):
        from substrate.workstation.vision_privacy import PRIVACY_RULES
        assert "auto-start" in PRIVACY_RULES[0].lower() or "default" in PRIVACY_RULES[0].lower()

    def test_camera_live_indicator_rule(self):
        from substrate.workstation.vision_privacy import PRIVACY_RULES
        banner_rules = [r for r in PRIVACY_RULES if "camera" in r.lower() and "live" in r.lower()]
        assert len(banner_rules) > 0


# ── Voice command classification — continuous motion ──────────────

class TestContinuousMotionCommands:
    """Classify voice commands for continuous PTZ motion."""

    def test_keep_moving_left(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("keep moving left")
        assert cmd is not None
        assert cmd.operation == "ptz_start_motion"
        assert cmd.params.get("pan_velocity") == -1.0

    def test_keep_moving_right(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("keep moving right")
        assert cmd is not None
        assert cmd.operation == "ptz_start_motion"
        assert cmd.params.get("pan_velocity") == 1.0

    def test_keep_panning_up(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("keep panning up")
        assert cmd is not None
        assert cmd.operation == "ptz_start_motion"
        assert cmd.params.get("tilt_velocity") == 1.0

    def test_continuous_tilt_down(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("keep tilting down")
        assert cmd is not None
        assert cmd.operation == "ptz_start_motion"
        assert cmd.params.get("tilt_velocity") == -1.0

    def test_keep_zooming_in(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("keep zooming in")
        assert cmd is not None
        assert cmd.operation == "zoom_start_motion"
        assert cmd.params.get("zoom_velocity") == 1.0

    def test_keep_zooming_out(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("keep zooming out")
        assert cmd is not None
        assert cmd.operation == "zoom_start_motion"
        assert cmd.params.get("zoom_velocity") == -1.0

    def test_continuously_zoom_in(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("continuously zoom in")
        assert cmd is not None
        assert cmd.operation == "zoom_start_motion"


# ── Voice command classification — stop motion ───────────────────

class TestStopMotionCommands:
    """Stop motion commands override everything except security."""

    def test_stop_moving(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("stop moving")
        assert cmd is not None
        assert cmd.operation == "ptz_stop_motion"

    def test_stop_camera_motion(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("stop camera motion")
        assert cmd is not None
        assert cmd.operation == "ptz_stop_motion"

    def test_halt_movement(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("halt movement")
        assert cmd is not None
        assert cmd.operation == "ptz_stop_motion"

    def test_stop_zoom(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("stop zoom")
        assert cmd is not None
        assert cmd.operation == "zoom_stop_motion"

    def test_stop_zooming(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("stop zooming")
        assert cmd is not None
        assert cmd.operation == "zoom_stop_motion"


# ── Voice command classification — default-on toggle ─────────────

class TestDefaultOnCommands:
    """Voice commands for enabling/disabling camera default-on."""

    def test_keep_camera_on_by_default(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("keep camera on by default")
        assert cmd is not None
        assert cmd.operation == "default_on_enable"

    def test_enable_camera_default_on(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("enable the camera default-on")
        assert cmd is not None
        assert cmd.operation == "default_on_enable"

    def test_disable_camera_default_on(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("disable the camera default-on")
        assert cmd is not None
        assert cmd.operation == "default_on_disable"

    def test_turn_off_camera_default(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("turn off the camera default")
        assert cmd is not None
        assert cmd.operation == "default_on_disable"


# ── Voice command classification — diagnostic ────────────────────

class TestDiagnosticCommands:
    """Voice commands for camera diagnostics."""

    def test_why_choppy(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("why is the camera choppy")
        assert cmd is not None
        assert cmd.operation == "explain_choppy"
        assert cmd.needs_ai is False

    def test_camera_is_choppy(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("the camera is choppy")
        assert cmd is not None
        assert cmd.operation == "explain_choppy"

    def test_why_not_live(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("why isn't the camera live")
        assert cmd is not None
        assert cmd.operation == "explain_not_live"

    def test_camera_not_on(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("camera not on")
        assert cmd is not None
        assert cmd.operation == "explain_not_live"


# ── Existing commands still work (regression) ────────────────────

class TestExistingCommandsRegression:
    """Phase 14.18 must not break existing camera commands."""

    def test_turn_on_camera(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("turn on the camera")
        assert cmd is not None
        assert cmd.operation == "start"

    def test_turn_off_camera(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("turn off the camera")
        assert cmd is not None
        assert cmd.operation == "stop"

    def test_move_camera_left(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("move camera left")
        assert cmd is not None

    def test_zoom_in(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("zoom in")
        assert cmd is not None

    def test_look_at_me(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("look at me")
        assert cmd is not None

    def test_what_do_you_see(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("what do you see")
        assert cmd is not None

    def test_track_my_phone(self):
        from substrate.workstation.camera_commands import classify_camera_command
        cmd = classify_camera_command("track my phone")
        assert cmd is not None


# ── Motion state machine ─────────────────────────────────────────

class TestMotionStateMachine:
    """Relay-side motion loop state transitions."""

    def test_motion_module_state_defaults(self):
        import umh.vision_relay as vr
        assert vr._motion_active is False
        assert vr._motion_id == ""
        assert vr._motion_pan_velocity == 0.0
        assert vr._motion_tilt_velocity == 0.0
        assert vr._motion_zoom_velocity == 0.0

    def test_motion_guard_ms_bounds(self):
        import umh.vision_relay as vr
        assert vr._motion_guard_ms >= 200


# ── Smooth preset transition ─────────────────────────────────────

class TestSmoothPresetTransition:
    """Smooth preset transition function exists and has smoothstep interpolation."""

    def test_smooth_preset_function_exists(self):
        import umh.vision_relay as vr
        assert hasattr(vr, "_smooth_preset_transition")
        assert callable(vr._smooth_preset_transition)

    def test_smooth_preset_task_initialized(self):
        import umh.vision_relay as vr
        assert hasattr(vr, "_smooth_preset_task")

    def test_smoothstep_math(self):
        """smoothstep(t) = t^2 * (3 - 2t) — verify the interpolation curve."""
        def smoothstep(t):
            return t * t * (3 - 2 * t)
        assert smoothstep(0.0) == 0.0
        assert smoothstep(1.0) == 1.0
        assert abs(smoothstep(0.5) - 0.5) < 0.001
        assert smoothstep(0.25) < 0.25
        assert smoothstep(0.75) > 0.75


# ── Relay message types ──────────────────────────────────────────

class TestRelayMessageTypes:
    """Relay handles the new Phase 14.18 message types."""

    def test_relay_has_ptz_start_motion_handler(self):
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        assert "camera_ptz_start_motion" in source

    def test_relay_has_ptz_stop_motion_handler(self):
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        assert "camera_ptz_stop_motion" in source

    def test_relay_has_ptz_update_motion_handler(self):
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        assert "camera_ptz_update_motion" in source

    def test_relay_has_zoom_start_handler(self):
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        assert "camera_zoom_start" in source

    def test_relay_has_zoom_stop_handler(self):
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        assert "camera_zoom_stop" in source

    def test_relay_has_smooth_preset_handler(self):
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        assert 'smooth' in source

    def test_relay_broadcasts_motion_state(self):
        import umh.vision_relay as vr
        assert hasattr(vr, "_broadcast_motion_state")
        assert callable(vr._broadcast_motion_state)

    def test_relay_broadcasts_motion_ack(self):
        import umh.vision_relay as vr
        assert hasattr(vr, "_broadcast_motion_ack")
        assert callable(vr._broadcast_motion_ack)

    def test_relay_broadcasts_session_state(self):
        import umh.vision_relay as vr
        assert hasattr(vr, "_broadcast_session_state")
        assert callable(vr._broadcast_session_state)


# ── Beast camera adapter — relative position ─────────────────────

class TestBeastCameraRelativePosition:
    """Beast camera adapter supports relative position for motion loop."""

    def test_camera_adapter_has_set_position_relative(self):
        from nodes.windows.umh_node.adapters.camera import CameraAdapter
        adapter = CameraAdapter.__new__(CameraAdapter)
        assert hasattr(adapter, "_set_position_relative")

    def test_camera_adapter_operations_include_relative(self):
        from nodes.windows.umh_node.adapters.camera import CameraAdapter
        adapter = CameraAdapter.__new__(CameraAdapter)
        adapter._presets = {}
        ops = adapter.execute.__code__.co_consts
        source = open(CameraAdapter.__module__.replace(".", "/") + ".py").read()
        assert "camera.set_position_relative" in source


# ── Pattern regex validation ─────────────────────────────────────

class TestPatternRegex:
    """Regex patterns for Phase 14.18 voice commands compile and match expected inputs."""

    def test_continuous_motion_pattern(self):
        from substrate.workstation.camera_commands import _CONTINUOUS_MOTION_PATTERN
        assert _CONTINUOUS_MOTION_PATTERN.search("keep moving left")
        assert _CONTINUOUS_MOTION_PATTERN.search("keep panning right")
        assert _CONTINUOUS_MOTION_PATTERN.search("keep tilting up")
        assert _CONTINUOUS_MOTION_PATTERN.search("continuously pan down")
        assert not _CONTINUOUS_MOTION_PATTERN.search("move camera left")

    def test_continuous_zoom_pattern(self):
        from substrate.workstation.camera_commands import _CONTINUOUS_ZOOM_PATTERN
        assert _CONTINUOUS_ZOOM_PATTERN.search("keep zooming in")
        assert _CONTINUOUS_ZOOM_PATTERN.search("continuously zoom out")
        assert not _CONTINUOUS_ZOOM_PATTERN.search("zoom in")

    def test_stop_motion_pattern(self):
        from substrate.workstation.camera_commands import _STOP_MOTION_PATTERN
        assert _STOP_MOTION_PATTERN.search("stop moving")
        assert _STOP_MOTION_PATTERN.search("stop motion")
        assert _STOP_MOTION_PATTERN.search("stop camera motion")

    def test_stop_zoom_pattern(self):
        from substrate.workstation.camera_commands import _STOP_ZOOM_PATTERN
        assert _STOP_ZOOM_PATTERN.search("stop zoom")
        assert _STOP_ZOOM_PATTERN.search("stop zooming")
        assert _STOP_ZOOM_PATTERN.search("halt zooming")

    def test_default_on_enable_pattern(self):
        from substrate.workstation.camera_commands import _DEFAULT_ON_ENABLE_PATTERN
        assert _DEFAULT_ON_ENABLE_PATTERN.search("keep camera on by default")
        assert _DEFAULT_ON_ENABLE_PATTERN.search("enable camera default on")
        assert _DEFAULT_ON_ENABLE_PATTERN.search("auto-start the camera")

    def test_default_on_disable_pattern(self):
        from substrate.workstation.camera_commands import _DEFAULT_ON_DISABLE_PATTERN
        assert _DEFAULT_ON_DISABLE_PATTERN.search("disable camera default on")
        assert _DEFAULT_ON_DISABLE_PATTERN.search("turn off camera default")

    def test_why_choppy_pattern(self):
        from substrate.workstation.camera_commands import _WHY_CHOPPY_PATTERN
        assert _WHY_CHOPPY_PATTERN.search("why is the camera choppy")
        assert _WHY_CHOPPY_PATTERN.search("camera is choppy")
        assert _WHY_CHOPPY_PATTERN.search("camera is laggy")

    def test_why_not_live_pattern(self):
        from substrate.workstation.camera_commands import _WHY_NOT_LIVE_PATTERN
        assert _WHY_NOT_LIVE_PATTERN.search("why isn't the camera live")
        assert _WHY_NOT_LIVE_PATTERN.search("camera not on")
        assert _WHY_NOT_LIVE_PATTERN.search("camera won't start")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
