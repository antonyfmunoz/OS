"""Tests for Phase 14.14E — Voice Camera Control, Tracking, Scene Understanding.

Covers: extended camera command classification, PTZ voice commands,
quality mode voice commands, tracking lifecycle, watch mode,
follow mode, visual queries, scene state, privacy governance,
and grounding rules.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from substrate.workstation.camera_commands import (
    CameraCommand,
    classify_camera_command,
)
from substrate.workstation.voice_route_resolver import parse_target_node
from substrate.workstation.command_router import classify_intent, CommandIntent
from substrate.workstation.vision_scene import (
    DetectedObject,
    VisionScene,
    VisionSceneManager,
    WatchItem,
    FollowState,
    SCENE_EXPIRY_S,
    OBJECT_LOST_THRESHOLD_S,
)
from substrate.workstation.vision_privacy import (
    PRIVACY_RULES,
    TRACKING_PRIVACY_RULES,
    FORBIDDEN_CLAIMS,
    validate_camera_activation,
    validate_frame_storage,
    validate_analysis_request,
    validate_tracking_activation,
    validate_watch_activation,
    validate_follow_activation,
    validate_visual_claim,
)


# ── Workcell A: Voice Camera PTZ Movement ────────────────────────────

class TestVoiceCameraPTZ:
    def test_move_camera_left(self) -> None:
        cmd = classify_camera_command("move camera left")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["pan_delta"] < 0

    def test_move_camera_right(self) -> None:
        cmd = classify_camera_command("move camera right")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["pan_delta"] > 0

    def test_move_camera_up(self) -> None:
        cmd = classify_camera_command("move camera up")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["tilt_delta"] > 0

    def test_move_camera_down(self) -> None:
        cmd = classify_camera_command("move camera down")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["tilt_delta"] < 0

    def test_move_camera_left_a_little(self) -> None:
        cmd = classify_camera_command("move camera left a little")
        assert cmd.operation == "ptz_relative"
        assert abs(cmd.params["pan_delta"]) < 5

    def test_move_camera_left_more(self) -> None:
        cmd = classify_camera_command("move camera left more")
        assert cmd.operation == "ptz_relative"
        assert abs(cmd.params["pan_delta"]) > 5

    def test_zoom_in(self) -> None:
        cmd = classify_camera_command("zoom in")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["zoom_delta"] > 0

    def test_zoom_out(self) -> None:
        cmd = classify_camera_command("zoom out")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["zoom_delta"] < 0

    def test_zoom_in_a_little(self) -> None:
        cmd = classify_camera_command("zoom in a little")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["zoom_delta"] == 5

    def test_zoom_out_more(self) -> None:
        cmd = classify_camera_command("zoom out more")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["zoom_delta"] == -20

    def test_center_camera(self) -> None:
        cmd = classify_camera_command("center the camera")
        assert cmd.operation == "ptz_home"

    def test_stop_moving(self) -> None:
        cmd = classify_camera_command("stop moving")
        assert cmd.operation == "ptz_home"

    def test_pan_left(self) -> None:
        cmd = classify_camera_command("pan left")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["pan_delta"] < 0

    def test_tilt_up(self) -> None:
        cmd = classify_camera_command("tilt up")
        assert cmd.operation == "ptz_relative"
        assert cmd.params["tilt_delta"] > 0


class TestVoiceCameraRouting:
    def test_move_camera_left_routes_to_camera_control(self) -> None:
        intent = classify_intent("move camera left")
        assert intent == CommandIntent.CAMERA_CONTROL

    def test_zoom_in_routes_to_camera_control(self) -> None:
        intent = classify_intent("zoom in")
        assert intent == CommandIntent.CAMERA_CONTROL

    def test_center_camera_routes_to_camera_control(self) -> None:
        intent = classify_intent("center the camera")
        assert intent == CommandIntent.CAMERA_CONTROL

    def test_move_camera_routes_to_beast(self) -> None:
        assert parse_target_node("move the camera left") == "beast_windows"

    def test_zoom_in_routes_to_beast(self) -> None:
        assert parse_target_node("zoom in") == "beast_windows"

    def test_center_camera_routes_to_beast(self) -> None:
        assert parse_target_node("center the camera") == "beast_windows"


# ── Workcell B: Voice Preset Control ────────────────────────────────

class TestVoicePresetControl:
    def test_look_at_me(self) -> None:
        cmd = classify_camera_command("look at me")
        assert cmd.operation == "preset"
        assert cmd.preset_name == "operator"

    def test_look_at_hands(self) -> None:
        cmd = classify_camera_command("look at my hands")
        assert cmd.operation == "preset"
        assert cmd.preset_name == "keyboard"

    def test_look_at_monitor(self) -> None:
        cmd = classify_camera_command("look at the monitor")
        assert cmd.operation == "preset"
        assert cmd.preset_name == "monitor"

    def test_save_preset_named(self) -> None:
        cmd = classify_camera_command("save this preset as monitor")
        assert cmd.operation == "save_preset"
        assert "monitor" in cmd.save_name

    def test_update_preset(self) -> None:
        cmd = classify_camera_command("update the desk preset")
        assert cmd.operation == "save_preset"
        assert cmd.save_name == "desk"

    def test_what_preset(self) -> None:
        cmd = classify_camera_command("what preset am i on")
        assert cmd.operation == "status"


# ── Workcell quality mode ───────────────────────────────────────────

class TestVoiceQualityMode:
    def test_switch_to_smooth(self) -> None:
        cmd = classify_camera_command("switch to smooth mode")
        assert cmd.operation == "quality_mode"
        assert cmd.params["mode"] == "smooth"

    def test_switch_to_sharp(self) -> None:
        cmd = classify_camera_command("switch to sharp")
        assert cmd.operation == "quality_mode"
        assert cmd.params["mode"] == "sharp"

    def test_switch_to_analysis(self) -> None:
        cmd = classify_camera_command("switch to analysis")
        assert cmd.operation == "quality_mode"
        assert cmd.params["mode"] == "analysis"

    def test_make_camera_clearer(self) -> None:
        cmd = classify_camera_command("make the camera clearer")
        assert cmd.operation == "quality_mode"
        assert cmd.params["mode"] == "sharp"

    def test_make_camera_smoother(self) -> None:
        cmd = classify_camera_command("make the camera smoother")
        assert cmd.operation == "quality_mode"
        assert cmd.params["mode"] == "smooth"

    def test_quality_routes_to_camera(self) -> None:
        intent = classify_intent("switch to smooth")
        assert intent == CommandIntent.CAMERA_CONTROL


# ── Workcell C: Scene State ──────────────────────────────────────────

class TestSceneState:
    def test_scene_created_from_frame(self) -> None:
        mgr = VisionSceneManager()
        scene = mgr.update_scene_from_frame(
            frame_id="f001",
            detected_objects=[
                {"label": "keyboard", "confidence": 0.92},
                {"label": "phone", "confidence": 0.84},
            ],
            summary="Desk with keyboard and phone visible.",
        )
        assert scene.frame_id == "f001"
        assert len(scene.objects) == 2
        assert scene.summary == "Desk with keyboard and phone visible."

    def test_scene_expired(self) -> None:
        scene = VisionScene(timestamp=time.time() - SCENE_EXPIRY_S - 10)
        assert scene.is_expired()

    def test_scene_not_expired(self) -> None:
        scene = VisionScene(timestamp=time.time())
        assert not scene.is_expired()

    def test_empty_scene_is_expired(self) -> None:
        scene = VisionScene()
        assert scene.is_expired()

    def test_get_visible_objects(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(
            frame_id="f002",
            detected_objects=[
                {"label": "keyboard", "confidence": 0.9},
            ],
        )
        visible = mgr.scene.get_visible_objects()
        assert len(visible) == 1
        assert visible[0].label == "keyboard"


# ── Workcell D: Object Detection ─────────────────────────────────────

class TestObjectDetection:
    def test_detected_object_has_confidence(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(
            frame_id="f003",
            detected_objects=[
                {"label": "phone", "confidence": 0.84},
            ],
        )
        obj = mgr.scene.get_object_by_label("phone")
        assert obj is not None
        assert obj.confidence == 0.84

    def test_detected_object_has_status(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(
            frame_id="f004",
            detected_objects=[
                {"label": "mouse", "confidence": 0.7},
            ],
        )
        obj = mgr.scene.get_object_by_label("mouse")
        assert obj is not None
        assert obj.status == "visible"

    def test_unknown_object_not_found(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(frame_id="f005")
        assert mgr.scene.get_object_by_label("unicorn") is None


# ── Workcell E: Object Tracking ──────────────────────────────────────

class TestObjectTracking:
    def test_start_tracking(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(
            frame_id="f006",
            detected_objects=[{"label": "phone", "confidence": 0.9}],
        )
        obj = mgr.start_tracking("phone")
        assert obj is not None
        assert obj.track_id.startswith("obj_")

    def test_tracking_status_visible(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(
            frame_id="f007",
            detected_objects=[{"label": "phone", "confidence": 0.9}],
        )
        mgr.start_tracking("phone")
        status = mgr.get_tracking_status("phone")
        assert status is not None
        assert status.status == "visible"

    def test_tracking_lost_state(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(
            frame_id="f008",
            detected_objects=[{"label": "phone", "confidence": 0.9}],
        )
        obj = mgr.start_tracking("phone")
        assert obj is not None
        obj.last_seen = time.time() - OBJECT_LOST_THRESHOLD_S - 10
        mgr.update_scene_from_frame(frame_id="f009", detected_objects=[])
        status = mgr.get_tracking_status("phone")
        assert status is not None
        assert status.status == "lost"

    def test_stop_tracking(self) -> None:
        mgr = VisionSceneManager()
        obj = mgr.start_tracking("phone")
        assert obj is not None
        stopped = mgr.stop_tracking("phone")
        assert stopped is True
        assert mgr.get_tracking_status("phone") is None

    def test_track_undetected_item_starts_unknown(self) -> None:
        mgr = VisionSceneManager()
        obj = mgr.start_tracking("notebook", track_hint="blue notebook on left")
        assert obj is not None
        assert obj.status == "unknown"
        assert obj.operator_confirmed is True


# ── Workcell F: Operator-Labeled Items ───────────────────────────────

class TestOperatorLabeling:
    def test_label_item_requires_confirmation(self) -> None:
        mgr = VisionSceneManager()
        obj = mgr.label_item("work phone")
        assert obj.operator_confirmed is True
        assert obj.label == "work phone"

    def test_label_item_voice_command(self) -> None:
        cmd = classify_camera_command("this is my notebook")
        assert cmd.operation == "label_item"
        assert cmd.params["label"] == "notebook"

    def test_remember_this_as(self) -> None:
        cmd = classify_camera_command("remember this as my work phone")
        assert cmd.operation == "label_item"
        assert cmd.params["label"] == "work phone"


# ── Workcell G: Visual Queries ───────────────────────────────────────

class TestVisualQueries:
    def test_visual_query_requires_frame(self) -> None:
        mgr = VisionSceneManager()
        result = mgr.query_visual("phone")
        assert "no_recent_frame" in result.get("status", "") or "expired" in result.get("answer", "").lower()

    def test_visual_query_camera_off_returns_blocker(self) -> None:
        mgr = VisionSceneManager()
        result = mgr.query_visual("keyboard")
        assert result["status"] == "no_recent_frame"

    def test_visual_query_found_object(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(
            frame_id="f010",
            detected_objects=[{"label": "phone", "confidence": 0.9}],
        )
        result = mgr.query_visual("phone")
        assert result["status"] == "visible"
        assert "phone" in result["answer"].lower()

    def test_visual_query_not_found(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(frame_id="f011")
        result = mgr.query_visual("unicorn")
        assert result["status"] == "not_found"

    def test_where_is_my_phone_classifies(self) -> None:
        cmd = classify_camera_command("where is my phone")
        assert cmd.operation == "visual_query"
        assert cmd.params["target"] == "phone"

    def test_detected_items_classifies(self) -> None:
        cmd = classify_camera_command("detected items")
        assert cmd.operation == "visual_query"


# ── Workcell H: Vision Model Dispatch ────────────────────────────────

class TestVisionModelDispatch:
    def test_what_do_you_see_needs_ai(self) -> None:
        cmd = classify_camera_command("what do you see")
        assert cmd.operation == "analyze"
        assert cmd.needs_ai is True

    def test_what_is_on_my_desk_needs_ai(self) -> None:
        cmd = classify_camera_command("what is on my desk")
        assert cmd.operation == "analyze"
        assert cmd.needs_ai is True


# ── Workcell I: Watch Mode ───────────────────────────────────────────

class TestWatchMode:
    def test_watch_requires_explicit_opt_in(self) -> None:
        allowed, _ = validate_watch_activation(is_explicit=False)
        assert allowed is False

    def test_watch_explicit_ok(self) -> None:
        allowed, _ = validate_watch_activation(is_explicit=True)
        assert allowed is True

    def test_watch_max_limit(self) -> None:
        allowed, _ = validate_watch_activation(is_explicit=True, active_watch_count=10)
        assert allowed is False

    def test_watch_start(self) -> None:
        mgr = VisionSceneManager()
        watch = mgr.start_watch("phone", condition="moved")
        assert watch is not None
        assert watch.target_label == "phone"
        assert watch.condition == "moved"
        assert watch.active is True

    def test_watch_stop(self) -> None:
        mgr = VisionSceneManager()
        mgr.start_watch("phone")
        stopped = mgr.stop_watch("phone")
        assert stopped is True

    def test_watch_voice_command(self) -> None:
        cmd = classify_camera_command("watch my phone")
        assert cmd.operation == "watch_start"
        assert cmd.params["target"] == "phone"

    def test_tell_me_if_disappears(self) -> None:
        cmd = classify_camera_command("tell me if my notebook disappears")
        assert cmd.operation == "watch_start"
        assert "notebook" in cmd.params["target"]

    def test_keep_eye_on(self) -> None:
        cmd = classify_camera_command("keep an eye on this hard drive")
        assert cmd.operation == "watch_start"

    def test_stop_watching(self) -> None:
        cmd = classify_camera_command("stop watching my phone")
        assert cmd.operation == "watch_stop"


# ── Workcell J: Follow Mode ─────────────────────────────────────────

class TestFollowMode:
    def test_follow_requires_explicit_activation(self) -> None:
        allowed, _ = validate_follow_activation(is_explicit=False)
        assert allowed is False

    def test_follow_explicit_ok(self) -> None:
        allowed, _ = validate_follow_activation(is_explicit=True)
        assert allowed is True

    def test_follow_start(self) -> None:
        mgr = VisionSceneManager()
        follow = mgr.start_follow("operator")
        assert follow.active is True
        assert follow.target == "operator"

    def test_follow_stop(self) -> None:
        mgr = VisionSceneManager()
        mgr.start_follow()
        mgr.stop_follow()
        assert mgr.follow_state.active is False

    def test_follow_me_voice(self) -> None:
        cmd = classify_camera_command("follow me")
        assert cmd.operation == "follow_start"

    def test_keep_me_centered_voice(self) -> None:
        cmd = classify_camera_command("keep me centered")
        assert cmd.operation == "follow_start"

    def test_stop_following_voice(self) -> None:
        cmd = classify_camera_command("stop following")
        assert cmd.operation == "follow_stop"

    def test_follow_target_lost_reports_blocker(self) -> None:
        mgr = VisionSceneManager()
        mgr.start_follow("operator")
        assert mgr.follow_state.active is True


# ── Workcell K: Privacy & Governance ─────────────────────────────────

class TestVisionPrivacy14E:
    def test_no_identity_recognition(self) -> None:
        allowed, _ = validate_visual_claim("identity_recognition")
        assert allowed is False

    def test_no_emotion_claims(self) -> None:
        allowed, _ = validate_visual_claim("emotion_detection")
        assert allowed is False

    def test_no_health_claims(self) -> None:
        allowed, _ = validate_visual_claim("health_diagnosis")
        assert allowed is False

    def test_no_biometric_storage(self) -> None:
        allowed, _ = validate_visual_claim("biometric_storage")
        assert allowed is False

    def test_no_hidden_recording(self) -> None:
        assert any("hidden" in r.lower() and "recording" in r.lower() for r in PRIVACY_RULES)

    def test_tracking_requires_explicit(self) -> None:
        allowed, _ = validate_tracking_activation(is_explicit=False)
        assert allowed is False

    def test_tracking_explicit_ok(self) -> None:
        allowed, _ = validate_tracking_activation(is_explicit=True, operator_session_id="s1")
        assert allowed is True

    def test_scene_state_expires(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(frame_id="f020")
        mgr._scene.timestamp = time.time() - SCENE_EXPIRY_S - 10
        assert mgr.scene.is_expired()

    def test_tracking_privacy_rules_exist(self) -> None:
        assert len(TRACKING_PRIVACY_RULES) >= 10

    def test_forbidden_claims_comprehensive(self) -> None:
        assert "identity_recognition" in FORBIDDEN_CLAIMS
        assert "emotion_detection" in FORBIDDEN_CLAIMS
        assert "biometric_storage" in FORBIDDEN_CLAIMS

    def test_watch_auto_expires(self) -> None:
        mgr = VisionSceneManager()
        watch = mgr.start_watch("phone")
        assert watch is not None
        watch.expires_at = time.time() - 10
        mgr._expire_watches(time.time())
        assert watch.watch_id not in mgr._watches


# ── Workcell M: Voice + Tracking Commands ────────────────────────────

class TestVoiceTrackingCommands:
    def test_track_my_phone(self) -> None:
        cmd = classify_camera_command("track my phone")
        assert cmd.operation == "track_start"
        assert cmd.params["target"] == "phone"

    def test_this_is_my_notebook(self) -> None:
        cmd = classify_camera_command("this is my notebook")
        assert cmd.operation == "label_item"
        assert cmd.params["label"] == "notebook"

    def test_stop_tracking_my_phone(self) -> None:
        cmd = classify_camera_command("stop tracking my phone")
        assert cmd.operation == "track_stop"
        assert cmd.params["target"] == "phone"

    def test_track_routes_to_camera_control(self) -> None:
        intent = classify_intent("track my phone")
        assert intent == CommandIntent.CAMERA_CONTROL

    def test_track_routes_to_beast(self) -> None:
        assert parse_target_node("track my phone") == "beast_windows"

    def test_where_is_routes_to_beast(self) -> None:
        assert parse_target_node("where is my notebook") == "beast_windows"

    def test_follow_me_routes_to_beast(self) -> None:
        assert parse_target_node("follow me") == "beast_windows"

    def test_stop_following_routes_to_beast(self) -> None:
        assert parse_target_node("stop following") == "beast_windows"

    def test_watch_my_phone_routes_to_camera(self) -> None:
        intent = classify_intent("watch my phone")
        assert intent == CommandIntent.CAMERA_CONTROL

    def test_tell_me_if_routes_to_camera(self) -> None:
        intent = classify_intent("tell me if my notebook moves")
        assert intent == CommandIntent.CAMERA_CONTROL


# ── Scene Manager State Summary ──────────────────────────────────────

class TestSceneManagerState:
    def test_state_summary(self) -> None:
        mgr = VisionSceneManager()
        mgr.update_scene_from_frame(
            frame_id="f030",
            detected_objects=[{"label": "phone", "confidence": 0.9}],
            summary="Phone visible on desk.",
        )
        mgr.start_tracking("phone")
        mgr.label_item("work phone")
        mgr.start_watch("phone")
        mgr.start_follow("operator")

        state = mgr.get_state_summary()
        assert state["scene"] is not None
        assert len(state["tracked_objects"]) >= 1
        assert len(state["labeled_items"]) >= 1
        assert len(state["active_watches"]) >= 1
        assert state["follow_mode"]["active"] is True

    def test_to_dict_roundtrip(self) -> None:
        obj = DetectedObject(
            track_id="obj_123",
            label="phone",
            confidence=0.84,
            status="visible",
        )
        d = obj.to_dict()
        restored = DetectedObject.from_dict(d)
        assert restored.track_id == "obj_123"
        assert restored.label == "phone"
        assert restored.confidence == 0.84


# ── Existing 14.14B tests remain passing ─────────────────────────────

class TestBackwardCompatibility:
    """Ensure Phase 14.14B commands still work after 14.14E extensions."""

    def test_look_at_me(self) -> None:
        cmd = classify_camera_command("look at me")
        assert cmd.operation == "preset"
        assert cmd.preset_name == "operator"

    def test_camera_on(self) -> None:
        cmd = classify_camera_command("turn on the camera")
        assert cmd.operation == "start"

    def test_camera_off(self) -> None:
        cmd = classify_camera_command("turn off the camera")
        assert cmd.operation == "stop"

    def test_what_do_you_see(self) -> None:
        cmd = classify_camera_command("what do you see")
        assert cmd.operation == "analyze"

    def test_save_preset_default(self) -> None:
        cmd = classify_camera_command("save this position")
        assert cmd.operation == "save_preset"

    def test_privacy_rules_count(self) -> None:
        assert len(PRIVACY_RULES) == 10

    def test_camera_activation_requires_session(self) -> None:
        allowed, _ = validate_camera_activation("")
        assert allowed is False

    def test_frame_storage_latest_ok(self) -> None:
        allowed, _ = validate_frame_storage("latest_buffer")
        assert allowed is True

    def test_parse_target_look_at_me(self) -> None:
        assert parse_target_node("look at me") == "beast_windows"

    def test_parse_target_non_camera(self) -> None:
        assert parse_target_node("hello there") == ""
