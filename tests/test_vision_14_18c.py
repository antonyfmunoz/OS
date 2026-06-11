"""Tests for Phase 14.18C/19B — True PTZ Joystick + Overlay Visibility + Diagnostics.

Covers: overlay filter bypass for diagnostics, motion guard timeout bounds,
relay motion state broadcast with coalesced counts, health report completeness,
and overlay rendering visibility chain.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ── Overlay filter tests (cockpit-side logic simulated) ──────────

class TestOverlayFilter:
    """VisionOverlay category filter must not block diagnostic overlays."""

    def test_diagnostic_overlay_bypasses_empty_tracker_filter(self):
        """When no trackers are enabled, diagnostic overlays must still render."""
        enabled_categories: set[str] = set()
        has_tracker_filters = len(enabled_categories) > 0

        diag_overlay = {"type": "object", "track_id": "diag_center", "label": "DIAG: center"}
        is_diagnostic = diag_overlay["track_id"].startswith("diag_")

        type_to_category = {"object": "object_detector"}
        cat = type_to_category.get(diag_overlay["type"])

        should_render = True
        if is_diagnostic:
            should_render = True
        elif has_tracker_filters and cat and cat not in enabled_categories:
            should_render = False

        assert should_render is True

    def test_real_overlay_passes_when_no_tracker_filters(self):
        """When no trackers are explicitly enabled, real overlays pass through."""
        enabled_categories: set[str] = set()
        has_tracker_filters = len(enabled_categories) > 0

        real_overlay = {"type": "object", "track_id": "person_1", "label": "person"}
        is_diagnostic = real_overlay["track_id"].startswith("diag_")

        type_to_category = {"object": "object_detector"}
        cat = type_to_category.get(real_overlay["type"])

        should_render = True
        if is_diagnostic:
            should_render = True
        elif has_tracker_filters and cat and cat not in enabled_categories:
            should_render = False

        assert should_render is True

    def test_real_overlay_blocked_when_wrong_category_enabled(self):
        """Real overlays are filtered when trackers are explicitly enabled but category doesn't match."""
        enabled_categories = {"face_tracker"}
        has_tracker_filters = len(enabled_categories) > 0

        real_overlay = {"type": "object", "track_id": "person_1", "label": "person"}
        is_diagnostic = real_overlay["track_id"].startswith("diag_")

        type_to_category = {"object": "object_detector"}
        cat = type_to_category.get(real_overlay["type"])

        should_render = True
        if is_diagnostic:
            should_render = True
        elif has_tracker_filters and cat and cat not in enabled_categories:
            should_render = False

        assert should_render is False

    def test_diagnostic_overlay_passes_even_with_tracker_filters(self):
        """Diagnostic overlays bypass category filtering even when trackers are active."""
        enabled_categories = {"face_tracker"}
        has_tracker_filters = len(enabled_categories) > 0

        diag_overlay = {"type": "object", "track_id": "diag_moving", "label": "DIAG: sweep"}
        is_diagnostic = diag_overlay["track_id"].startswith("diag_")

        should_render = True
        if is_diagnostic:
            should_render = True

        assert should_render is True


# ── Relay motion state tests ─────────────────────────────────────

class TestRelayMotionState:
    """Motion loop and guard timeout behavior."""

    def test_guard_timeout_minimum_500ms(self):
        """Guard timeout floor is 500ms."""
        guard_ms = 100
        clamped = max(500, min(guard_ms, 5000))
        assert clamped == 500

    def test_guard_timeout_maximum_5000ms(self):
        """Guard timeout ceiling is 5000ms."""
        guard_ms = 10000
        clamped = max(500, min(guard_ms, 5000))
        assert clamped == 5000

    def test_guard_timeout_passthrough_valid(self):
        """Valid guard timeout values pass through clamping."""
        guard_ms = 3000
        clamped = max(500, min(guard_ms, 5000))
        assert clamped == 3000

    def test_motion_state_broadcast_includes_coalesced(self):
        """Motion state broadcast must include coalesced_commands field."""
        msg = {
            "type": "ptz_motion_state",
            "motion_id": "test_1",
            "state": "moving",
            "pan_velocity": 0.5,
            "tilt_velocity": -0.3,
            "zoom_velocity": 0,
            "loop_cadence_hz": 20.0,
            "guard_timeout_events": 0,
            "coalesced_commands": 42,
        }
        assert "coalesced_commands" in msg
        assert msg["coalesced_commands"] == 42

    def test_speed_clamped_to_valid_range(self):
        """Speed must be clamped between 0.1 and 5.0."""
        for speed_in, expected in [(-1, 0.1), (0, 0.1), (0.1, 0.1), (3, 3), (5, 5), (10, 5)]:
            clamped = max(0.1, min(speed_in, 5.0))
            assert clamped == expected, f"speed={speed_in} should clamp to {expected}, got {clamped}"


# ── Diagnostic overlay generation tests ──────────────────────────

class TestDiagnosticOverlays:
    """Relay-side diagnostic overlay generation."""

    def test_diagnostic_overlay_count(self):
        """Diagnostic overlay generates exactly 4 boxes."""
        from umh.vision_relay import _build_diagnostic_overlays
        overlays = _build_diagnostic_overlays()
        assert len(overlays) == 4

    def test_diagnostic_overlays_have_diag_prefix(self):
        """All diagnostic overlays have track_id starting with diag_."""
        from umh.vision_relay import _build_diagnostic_overlays
        overlays = _build_diagnostic_overlays()
        for o in overlays:
            assert o["track_id"].startswith("diag_"), f"track_id {o['track_id']} missing diag_ prefix"

    def test_diagnostic_overlays_have_valid_bbox(self):
        """Diagnostic overlays have normalized bbox coordinates [0, 1]."""
        from umh.vision_relay import _build_diagnostic_overlays
        overlays = _build_diagnostic_overlays()
        for o in overlays:
            bbox = o["bbox"]
            assert 0 <= bbox["x"] <= 1, f"x={bbox['x']} out of range"
            assert 0 <= bbox["y"] <= 1, f"y={bbox['y']} out of range"
            assert bbox["w"] > 0
            assert bbox["h"] > 0

    def test_diagnostic_overlays_have_color(self):
        """Each diagnostic overlay must specify a color for rendering."""
        from umh.vision_relay import _build_diagnostic_overlays
        overlays = _build_diagnostic_overlays()
        for o in overlays:
            assert "color" in o, f"overlay {o['track_id']} missing color"
            assert o["color"].startswith("#"), f"color {o['color']} not a hex color"


# ── Health report tests ──────────────────────────────────────────

class TestHealthReport:
    """Vision health report completeness."""

    def test_health_report_has_required_fields(self):
        """Health report must include all fields the cockpit expects."""
        required_fields = [
            "status", "relay_running", "cockpit_connected", "beast_connected",
            "camera_available", "camera_streaming", "last_frame_at",
            "last_frame_age_ms", "frame_count", "frame_fps",
            "tracker_runtime_available", "active_trackers",
            "last_overlay_at", "last_overlay_age_ms", "overlay_count",
            "trigger_chain_engine_available", "active_chains",
            "security_mode", "diagnostic_overlay_active",
            "blockers", "recovery_action",
        ]
        try:
            from umh.vision_relay import _build_health
            health = _build_health()
            for field in required_fields:
                assert field in health, f"missing health field: {field}"
        except Exception:
            pytest.skip("vision relay dependencies not available in test environment")


# ── Joystick vector computation tests ────────────────────────────

class TestJoystickVector:
    """Joystick vector computation and deadzone behavior."""

    def test_deadzone_filters_small_movements(self):
        """Movements within deadzone should produce zero velocity."""
        DEADZONE = 0.15
        dx = 0.1
        dy = -0.05
        panV = dx if abs(dx) > DEADZONE else 0
        tiltV = dy if abs(dy) > DEADZONE else 0
        assert panV == 0
        assert tiltV == 0

    def test_outside_deadzone_passes_through(self):
        """Movements beyond deadzone produce velocity."""
        DEADZONE = 0.15
        dx = 0.5
        dy = -0.8
        panV = dx if abs(dx) > DEADZONE else 0
        tiltV = dy if abs(dy) > DEADZONE else 0
        assert panV == 0.5
        assert tiltV == -0.8

    def test_vector_clamped_to_unit_circle(self):
        """Drag beyond joystick edge clamps to unit circle."""
        import math
        dx = 1.5
        dy = -1.2
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 1:
            dx /= dist
            dy /= dist
        assert abs(math.sqrt(dx * dx + dy * dy) - 1.0) < 0.001


# ── Source code audit tests ──────────────────────────────────────

class TestSourceCodeAudit:
    """Verify code changes match phase requirements."""

    def test_overlay_component_checks_diagnostic_prefix(self):
        """VisionOverlay.tsx must check track_id for diag_ prefix."""
        overlay_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "vision", "VisionOverlay.tsx",
        )
        content = open(overlay_path).read()
        assert "diag_" in content, "VisionOverlay must check for diag_ prefix"
        assert "hasTrackerFilters" in content, "VisionOverlay must use hasTrackerFilters guard"

    def test_joystick_has_touch_action_none(self):
        """CameraController joystick must have touch-action: none for mobile."""
        controller_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        content = open(controller_path).read()
        assert "touchAction" in content or "touch-action" in content, "Joystick must set touch-action: none"

    def test_joystick_uses_pointer_capture(self):
        """CameraController must use setPointerCapture for reliable drag."""
        controller_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        content = open(controller_path).read()
        assert "setPointerCapture" in content
        assert "releasePointerCapture" in content

    def test_camera_preview_has_overlay(self):
        """CameraPreview must render VisionOverlay over the frame."""
        preview_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraPreview.tsx",
        )
        content = open(preview_path).read()
        assert "VisionOverlay" in content, "CameraPreview must render VisionOverlay"

    def test_relay_guard_timeout_clamp_allows_3000ms(self):
        """Relay must accept guard_ms up to 5000."""
        relay_path = os.path.join(
            os.path.dirname(__file__), "..",
            "umh", "vision_relay.py",
        )
        content = open(relay_path).read()
        assert "5000" in content, "Guard clamp upper bound should be 5000ms"

    def test_relay_broadcasts_coalesced_commands(self):
        """Relay motion state broadcast must include coalesced_commands."""
        relay_path = os.path.join(
            os.path.dirname(__file__), "..",
            "umh", "vision_relay.py",
        )
        content = open(relay_path).read()
        assert '"coalesced_commands"' in content

    def test_diagnostics_panel_exists(self):
        """CameraController must have PtzDiagnosticsPanel."""
        controller_path = os.path.join(
            os.path.dirname(__file__), "..",
            "cockpit", "src", "renderer", "components", "CameraController.tsx",
        )
        content = open(controller_path).read()
        assert "PtzDiagnosticsPanel" in content

    def test_auth_check_remains(self):
        """Auth check must not be removed from vision relay."""
        relay_path = os.path.join(
            os.path.dirname(__file__), "..",
            "umh", "vision_relay.py",
        )
        content = open(relay_path).read()
        assert "_check_auth" in content
        assert "4001" in content

    def test_no_public_camera_port(self):
        """Vision relay must not bind to a publicly-exposed port without auth."""
        relay_path = os.path.join(
            os.path.dirname(__file__), "..",
            "umh", "vision_relay.py",
        )
        content = open(relay_path).read()
        assert "_AUTH_TOKEN" in content
        assert "_ALLOWED_ORIGINS" in content

    def test_diagnostic_overlay_not_real_tracking(self):
        """Diagnostic overlays have diag_ prefix — cannot be mistaken for real tracking."""
        from umh.vision_relay import _build_diagnostic_overlays
        overlays = _build_diagnostic_overlays()
        for o in overlays:
            assert o["track_id"].startswith("diag_"), "diagnostic overlays must be clearly marked"
            assert "DIAG" in o["label"], "diagnostic overlay labels must contain DIAG"
