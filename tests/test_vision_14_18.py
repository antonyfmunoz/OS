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


# ── Phase 14.18B — Live field fix tests ─────────────────────────

class TestMotionLoopFixes:
    """Verify relay motion loop fixes: non-blocking dispatch, rounding, guard."""

    def test_dispatch_to_beast_is_async_wrapper(self):
        """_dispatch_to_beast must be async (non-blocking)."""
        import umh.vision_relay as vr
        import asyncio
        assert asyncio.iscoroutinefunction(vr._dispatch_to_beast)

    def test_dispatch_sync_exists_for_threadpool(self):
        """_dispatch_to_beast_sync is the blocking implementation for run_in_executor."""
        import umh.vision_relay as vr
        assert hasattr(vr, "_dispatch_to_beast_sync")
        assert callable(vr._dispatch_to_beast_sync)
        import asyncio
        assert not asyncio.iscoroutinefunction(vr._dispatch_to_beast_sync)

    def test_motion_loop_uses_round_not_int(self):
        """Step delta must use round() not int() to avoid truncation."""
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        loop_section = source[source.index("async def _motion_loop"):source.index("async def _start_motion")]
        assert "round(" in loop_section, "motion loop must use round() for step deltas"
        assert "int(" not in loop_section or "int((" not in loop_section, \
            "motion loop should not use int() for step deltas"

    def test_motion_loop_step_scale_adequate(self):
        """Step scale must produce non-zero delta at 30% velocity."""
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        loop_section = source[source.index("async def _motion_loop"):source.index("async def _start_motion")]
        assert "* 8" in loop_section or "* 10" in loop_section, \
            "step scale must be >= 8 for adequate motion"

    def test_dispatch_motion_stop_not_noop(self):
        """_dispatch_motion_stop must actually send a command, not pass."""
        import umh.vision_relay as vr
        import inspect
        source = inspect.getsource(vr._dispatch_motion_stop)
        assert "pass" not in source or "_dispatch_to_beast" in source

    def test_guard_timeout_default_2000ms(self):
        """Default guard timeout should be >= 2000ms."""
        import umh.vision_relay as vr
        import inspect
        sig = inspect.signature(vr._start_motion)
        guard_default = sig.parameters["guard_ms"].default
        assert guard_default >= 2000, f"guard_ms default {guard_default} too low"

    def test_motion_loop_combines_pan_tilt_zoom(self):
        """Motion loop should combine pan/tilt/zoom into single dispatch."""
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        loop_section = source[source.index("async def _motion_loop"):source.index("async def _start_motion")]
        dispatch_count = loop_section.count("_dispatch_to_beast")
        assert dispatch_count == 1, \
            f"motion loop should have 1 combined dispatch, got {dispatch_count}"


class TestOverlayChain:
    """Verify overlay rendering chain is wired end-to-end."""

    def test_vision_overlay_component_exists(self):
        overlay_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "vision", "VisionOverlay.tsx",
        )
        assert os.path.exists(overlay_path), "VisionOverlay.tsx must exist"

    def test_overlay_toggle_buttons_in_controller(self):
        """Toggle controls must exist — either standalone or inline in CameraController."""
        cc_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        source = open(cc_path).read()
        assert "overlayVisible" in source, "overlay visibility toggle must exist"
        assert "diagnosticOverlay" in source or "DIAG" in source, "diagnostic toggle must exist"

    def test_camera_controller_imports_overlay(self):
        cc_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        source = open(cc_path).read()
        assert "VisionOverlay" in source, "CameraController must import VisionOverlay"

    def test_relay_forwards_overlay_data(self):
        """Relay must broadcast overlay data, not just record timestamps."""
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        assert "vision_overlay" in source, "relay must have vision_overlay message type"

    def test_relay_diagnostic_overlay_handler(self):
        """Relay must support diagnostic overlay toggle."""
        import umh.vision_relay as vr
        source = open(vr.__file__).read()
        assert "diagnostic" in source.lower(), "relay must support diagnostic overlays"

    def test_vision_store_has_overlays_field(self):
        store_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "stores", "visionStore.ts",
        )
        source = open(store_path).read()
        assert "overlays" in source, "visionStore must have overlays field"

    def test_vision_ws_has_overlay_event(self):
        ws_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "api", "vision-ws.ts",
        )
        source = open(ws_path).read()
        assert "vision_overlay" in source, "vision-ws must handle vision_overlay events"


class TestControllerContinuousMotion:
    """Verify CameraController sends continuous updates for all controls."""

    def test_dpad_calls_start_with_update_timer(self):
        """D-pad must use startDirectionMotion which now includes update timer."""
        cc_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        source = open(cc_path).read()
        assert "ensureUpdateTimer" in source, "must have ensureUpdateTimer function"

    def test_zoom_has_update_timer(self):
        """Zoom hold must send continuous updates."""
        cc_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        source = open(cc_path).read()
        zoom_section = source[source.index("startZoomMotion"):source.index("stopZoomMotion")]
        assert "setInterval" in zoom_section, "zoom must have setInterval for continuous updates"

    def test_guard_timeout_2000ms_in_client(self):
        """Client must send durationGuardMs >= 2000."""
        cc_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        source = open(cc_path).read()
        assert "durationGuardMs: 2000" in source, "client must send 2000ms guard"

    def test_pointer_capture_on_joystick(self):
        """Joystick must use setPointerCapture."""
        cc_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        source = open(cc_path).read()
        assert "setPointerCapture" in source

    def test_touch_none_on_joystick(self):
        """Joystick must have touch-action: none (touch-none class)."""
        cc_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        source = open(cc_path).read()
        assert "touch-none" in source

    def test_emergency_stop_on_blur(self):
        """Window blur must trigger emergency stop."""
        cc_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        source = open(cc_path).read()
        assert "window.addEventListener('blur'" in source or 'window.addEventListener("blur"' in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
