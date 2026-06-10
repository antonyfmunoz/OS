"""Tests for Phase 14.16 — Realtime Vision Overlay + Tracker Stack + Vision Preset Studio + Trigger Chain Engine.

Covers: tracker stack CRUD, vision preset CRUD, trigger chain lifecycle,
security harden mode, overlay/tracker/preset/chain voice commands,
privacy governance gates, command routing, and voice route resolver.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from substrate.workstation.tracker_stack import (
    TrackerConfig,
    TrackerStack,
    TrackerStackManager,
    TRACKER_CATEGORIES,
    SENSITIVE_TRACKERS,
    MAX_ACTIVE_TRACKERS,
    get_tracker_manager,
)
from substrate.workstation.vision_presets import (
    VisionPreset,
    VisionPresetManager,
    PresetZone,
    MAX_PRESETS,
    MAX_ZONES_PER_PRESET,
    MAX_PRESET_NAME_LENGTH,
    get_preset_manager,
)
from substrate.workstation.trigger_chains import (
    TriggerChain,
    TriggerChainManager,
    ChainCondition,
    ChainAction,
    ChainGovernance,
    ChainFireRecord,
    VISION_EVENTS,
    ACTION_TYPES,
    RISK_LEVELS,
    MAX_CHAINS,
    MAX_ACTIONS_PER_CHAIN,
    MAX_CONDITIONS_PER_CHAIN,
    get_chain_manager,
)
from substrate.workstation.security_mode import (
    SecurityModeManager,
    SecurityModeState,
    SecurityEvent,
    ALLOWED_SECURITY_ACTIONS,
    FORBIDDEN_SECURITY_ACTIONS,
    get_security_manager,
)
from substrate.workstation.vision_privacy import (
    OVERLAY_PRIVACY_RULES,
    FORBIDDEN_SECURITY_ACTIONS as PRIVACY_FORBIDDEN,
    validate_operator_enrollment,
    validate_gesture_control,
    validate_trigger_chain_action,
)
from substrate.workstation.camera_commands import (
    CameraCommand,
    classify_camera_command,
)
from substrate.workstation.command_router import classify_intent, CommandIntent
from substrate.workstation.voice_route_resolver import parse_target_node


# ── Tracker Stack ─────────────────────────────────────────────────

class TestTrackerStack:

    def setup_method(self):
        self.mgr = TrackerStackManager()
        self.mgr.create_stack("test", "Test Stack")
        self.mgr.activate_stack("test")

    def test_create_stack_has_all_categories(self):
        stack = self.mgr.active_stack
        assert stack is not None
        for cat in TRACKER_CATEGORIES:
            assert cat in stack.trackers

    def test_enable_disable_tracker(self):
        assert self.mgr.enable_tracker("object_detector")
        enabled = self.mgr.get_enabled_trackers()
        assert any(t.category == "object_detector" for t in enabled)

        assert self.mgr.disable_tracker("object_detector")
        enabled = self.mgr.get_enabled_trackers()
        assert not any(t.category == "object_detector" for t in enabled)

    def test_max_active_trackers_cap(self):
        for cat in TRACKER_CATEGORIES[:MAX_ACTIVE_TRACKERS]:
            self.mgr.enable_tracker(cat)
        extra = TRACKER_CATEGORIES[MAX_ACTIVE_TRACKERS] if len(TRACKER_CATEGORIES) > MAX_ACTIVE_TRACKERS else None
        if extra:
            assert not self.mgr.enable_tracker(extra)

    def test_sensitive_tracker_detection(self):
        assert not self.mgr.is_sensitive_tracker_enabled()
        self.mgr.enable_tracker("face_tracker")
        assert self.mgr.is_sensitive_tracker_enabled()

    def test_tracker_availability_gate(self):
        self.mgr.set_capabilities({"hand_tracker": False})
        self.mgr.create_stack("caps", "Caps Stack")
        self.mgr.activate_stack("caps")
        assert not self.mgr.enable_tracker("hand_tracker")

    def test_delete_active_stack(self):
        self.mgr.delete_stack("test")
        assert self.mgr.active_stack is None

    def test_total_cost(self):
        cost = self.mgr.get_total_cost()
        assert cost["cpu"] == 0.0
        assert cost["gpu"] == 0.0

    def test_state_summary(self):
        summary = self.mgr.get_state_summary()
        assert "active_stack_id" in summary
        assert "stacks" in summary
        assert "enabled_trackers" in summary

    def test_tracker_config_to_dict(self):
        cfg = TrackerConfig(tracker_id="t1", category="face_tracker")
        d = cfg.to_dict()
        assert d["tracker_id"] == "t1"
        assert d["category"] == "face_tracker"

    def test_tracker_stack_to_dict(self):
        stack = self.mgr.active_stack
        d = stack.to_dict()
        assert d["stack_id"] == "test"
        assert "trackers" in d


# ── Vision Presets ────────────────────────────────────────────────

class TestVisionPresets:

    def setup_method(self):
        self.mgr = VisionPresetManager()

    def test_create_preset(self):
        p = self.mgr.create("desk", "Desk View", "Overhead desk camera")
        assert p is not None
        assert p.label == "Desk View"

    def test_rename_preset(self):
        self.mgr.create("desk", "Desk View")
        assert self.mgr.rename("desk", "Desk Cam")
        p = self.mgr.get("desk")
        assert p.label == "Desk Cam"

    def test_delete_preset_returns_affected_chains(self):
        p = self.mgr.create("desk", "Desk View")
        p.trigger_chain_ids = ["chain_abc", "chain_def"]
        ok, affected = self.mgr.delete("desk")
        assert ok
        assert "chain_abc" in affected
        assert "chain_def" in affected

    def test_activate_preset(self):
        self.mgr.create("desk", "Desk View")
        assert self.mgr.activate("desk")
        assert self.mgr.active_preset is not None
        assert self.mgr.active_preset.preset_id == "desk"

    def test_update_ptz(self):
        self.mgr.create("desk", "Desk View")
        assert self.mgr.update_ptz("desk", {"pan": 90, "tilt": 45, "zoom": 200})
        p = self.mgr.get("desk")
        assert p.ptz["pan"] == 90

    def test_nudge_ptz(self):
        self.mgr.create("desk", "Desk View", ptz={"pan": 0, "tilt": 0, "zoom": 100})
        assert self.mgr.nudge_ptz("desk", pan_delta=10, tilt_delta=-5, zoom_delta=20)
        p = self.mgr.get("desk")
        assert p.ptz["pan"] == 10
        assert p.ptz["tilt"] == -5
        assert p.ptz["zoom"] == 120

    def test_add_and_remove_zone(self):
        self.mgr.create("desk", "Desk View")
        zone = self.mgr.add_zone("desk", "keyboard area", [[0.1, 0.5], [0.9, 0.5], [0.9, 0.9], [0.1, 0.9]])
        assert zone is not None
        assert self.mgr.remove_zone("desk", zone.zone_id)
        p = self.mgr.get("desk")
        assert len(p.zones) == 0

    def test_max_zones_cap(self):
        self.mgr.create("desk", "Desk View")
        for i in range(MAX_ZONES_PER_PRESET):
            self.mgr.add_zone("desk", f"zone_{i}", [[0, 0], [1, 1]])
        overflow = self.mgr.add_zone("desk", "overflow", [[0, 0]])
        assert overflow is None

    def test_duplicate_preset(self):
        self.mgr.create("desk", "Desk View")
        dup = self.mgr.duplicate("desk", "desk_copy")
        assert dup is not None
        assert dup.preset_id == "desk_copy"
        assert dup.label == "Desk View (copy)"

    def test_max_presets_cap(self):
        for i in range(MAX_PRESETS):
            self.mgr.create(f"p{i}", f"Preset {i}")
        overflow = self.mgr.create("overflow", "Overflow")
        assert overflow is None

    def test_preset_name_length_cap(self):
        long_id = "x" * (MAX_PRESET_NAME_LENGTH + 1)
        result = self.mgr.create(long_id, "Too Long")
        assert result is None

    def test_state_summary(self):
        self.mgr.create("desk", "Desk View")
        summary = self.mgr.get_state_summary()
        assert "presets" in summary
        assert summary["count"] == 1

    def test_preset_to_dict_roundtrip(self):
        self.mgr.create("desk", "Desk View", ptz={"pan": 10, "tilt": 20, "zoom": 150})
        p = self.mgr.get("desk")
        d = p.to_dict()
        restored = VisionPreset.from_dict(d)
        assert restored.preset_id == "desk"
        assert restored.ptz["pan"] == 10


# ── Trigger Chains ────────────────────────────────────────────────

class TestTriggerChains:

    def setup_method(self):
        self.mgr = TriggerChainManager()

    def test_create_chain(self):
        chain = self.mgr.create_chain(
            label="Lock on leave",
            trigger_event="operator_left_room",
            actions=[{"type": "notify.operator", "message": "You left!"}],
        )
        assert chain is not None
        assert chain.trigger_event == "operator_left_room"

    def test_chain_evaluate_fires(self):
        self.mgr.create_chain(
            label="Lock on leave",
            trigger_event="operator_left_room",
            actions=[{"type": "notify.operator"}],
        )
        fired = self.mgr.evaluate_event("operator_left_room")
        assert len(fired) == 1
        assert fired[0].event == "operator_left_room"

    def test_chain_debounce(self):
        self.mgr.create_chain(
            label="Lock on leave",
            trigger_event="operator_left_room",
            actions=[{"type": "notify.operator"}],
            debounce_seconds=5.0,
        )
        fired1 = self.mgr.evaluate_event("operator_left_room")
        assert len(fired1) == 1
        fired2 = self.mgr.evaluate_event("operator_left_room")
        assert len(fired2) == 0

    def test_chain_confidence_gate(self):
        self.mgr.create_chain(
            label="High conf only",
            trigger_event="unknown_person_entered",
            actions=[{"type": "notify.operator"}],
            confidence_min=0.8,
        )
        fired = self.mgr.evaluate_event("unknown_person_entered", confidence=0.5)
        assert len(fired) == 0
        fired = self.mgr.evaluate_event("unknown_person_entered", confidence=0.9)
        assert len(fired) == 1

    def test_chain_condition_evaluation(self):
        self.mgr.create_chain(
            label="Conditional chain",
            trigger_event="tracked_item_moved",
            actions=[{"type": "notify.operator"}],
            conditions=[{"field": "zone", "op": "eq", "value": "desk"}],
        )
        fired = self.mgr.evaluate_event("tracked_item_moved", context={"zone": "door"})
        assert len(fired) == 0
        fired = self.mgr.evaluate_event("tracked_item_moved", context={"zone": "desk"})
        assert len(fired) == 1

    def test_chain_zone_filter(self):
        self.mgr.create_chain(
            label="Door zone only",
            trigger_event="door_zone_motion",
            actions=[{"type": "notify.operator"}],
            trigger_zone="front_door",
        )
        fired = self.mgr.evaluate_event("door_zone_motion", zone="back_door")
        assert len(fired) == 0
        fired = self.mgr.evaluate_event("door_zone_motion", zone="front_door")
        assert len(fired) == 1

    def test_chain_requires_approval_skips_auto_fire(self):
        self.mgr.create_chain(
            label="Approval chain",
            trigger_event="unknown_person_entered",
            actions=[{"type": "mode.set", "mode": "security_harden"}],
            governance={"requires_approval": True},
        )
        fired = self.mgr.evaluate_event("unknown_person_entered")
        assert len(fired) == 0

    def test_chain_risk_auto_calculation(self):
        chain = self.mgr.create_chain(
            label="Mixed risk",
            trigger_event="operator_left_room",
            actions=[
                {"type": "notify.operator"},
                {"type": "mode.set", "mode": "away"},
            ],
        )
        assert chain.governance.risk == "medium"

    def test_chain_enable_disable(self):
        chain = self.mgr.create_chain(
            label="Toggle test",
            trigger_event="operator_left_room",
            actions=[{"type": "notify.log"}],
        )
        self.mgr.disable_chain(chain.chain_id)
        fired = self.mgr.evaluate_event("operator_left_room")
        assert len(fired) == 0
        self.mgr.enable_chain(chain.chain_id)
        fired = self.mgr.evaluate_event("operator_left_room")
        assert len(fired) == 1

    def test_chain_delete(self):
        chain = self.mgr.create_chain(
            label="Delete me",
            trigger_event="operator_left_room",
            actions=[{"type": "notify.log"}],
        )
        assert self.mgr.delete_chain(chain.chain_id)
        assert self.mgr.get_chain(chain.chain_id) is None

    def test_explain_last_fire(self):
        self.mgr.create_chain(
            label="Explain test",
            trigger_event="face_lost",
            actions=[{"type": "notify.operator"}],
        )
        self.mgr.evaluate_event("face_lost")
        explanation = self.mgr.explain_last_fire()
        assert "face_lost" in explanation
        assert "Explain test" in explanation

    def test_unknown_action_type_rejected(self):
        chain = self.mgr.create_chain(
            label="Bad action",
            trigger_event="operator_left_room",
            actions=[{"type": "launch_missiles"}],
        )
        assert chain is None

    def test_max_chains_cap(self):
        for i in range(MAX_CHAINS):
            self.mgr.create_chain(
                label=f"Chain {i}",
                trigger_event="operator_left_room",
                actions=[{"type": "notify.log"}],
            )
        overflow = self.mgr.create_chain(
            label="Overflow",
            trigger_event="operator_left_room",
            actions=[{"type": "notify.log"}],
        )
        assert overflow is None

    def test_fire_record_audit_trail(self):
        self.mgr.create_chain(
            label="Audit trail",
            trigger_event="operator_left_room",
            actions=[{"type": "notify.operator"}],
        )
        self.mgr.evaluate_event("operator_left_room", confidence=0.95, frame_id="frame_123")
        fires = self.mgr.get_recent_fires()
        assert len(fires) == 1
        assert fires[0].confidence == 0.95
        assert fires[0].frame_id == "frame_123"

    def test_state_summary(self):
        self.mgr.create_chain(
            label="Summary test",
            trigger_event="operator_left_room",
            actions=[{"type": "notify.log"}],
        )
        summary = self.mgr.get_state_summary()
        assert summary["chain_count"] == 1
        assert summary["enabled_count"] == 1

    def test_chain_to_dict_roundtrip(self):
        chain = self.mgr.create_chain(
            label="Roundtrip",
            trigger_event="face_lost",
            actions=[{"type": "notify.operator", "message": "Face lost!"}],
            conditions=[{"field": "zone", "op": "eq", "value": "desk"}],
        )
        d = chain.to_dict()
        restored = TriggerChain.from_dict(d)
        assert restored.label == "Roundtrip"
        assert restored.trigger_event == "face_lost"
        assert len(restored.conditions) == 1
        assert len(restored.actions) == 1

    def test_condition_operators(self):
        cond_eq = ChainCondition(field="a", op="eq", value=1)
        assert cond_eq.evaluate({"a": 1})
        assert not cond_eq.evaluate({"a": 2})

        cond_neq = ChainCondition(field="a", op="neq", value=1)
        assert cond_neq.evaluate({"a": 2})

        cond_gt = ChainCondition(field="a", op="gt", value=5)
        assert cond_gt.evaluate({"a": 10})
        assert not cond_gt.evaluate({"a": 3})

        cond_lt = ChainCondition(field="a", op="lt", value=5)
        assert cond_lt.evaluate({"a": 3})

        cond_in = ChainCondition(field="a", op="in", value=["x", "y"])
        assert cond_in.evaluate({"a": "x"})
        assert not cond_in.evaluate({"a": "z"})

        cond_not_in = ChainCondition(field="a", op="not_in", value=["x", "y"])
        assert cond_not_in.evaluate({"a": "z"})


# ── Security Mode ─────────────────────────────────────────────────

class TestSecurityMode:

    def setup_method(self):
        self.mgr = SecurityModeManager()

    def test_activate_and_deactivate(self):
        state = self.mgr.activate(triggered_by="unknown_person")
        assert state.active
        assert state.risk == "high"

        result = self.mgr.deactivate(resolved_by="operator")
        assert result["success"]
        assert not self.mgr.is_active

    def test_deactivate_when_not_active(self):
        result = self.mgr.deactivate()
        assert not result["success"]

    def test_activate_saves_previous_state(self):
        state = self.mgr.activate(
            triggered_by="test",
            current_profile_mode="focus",
            current_preset_id="desk",
        )
        assert state.previous_profile_mode == "focus"
        assert state.previous_preset_id == "desk"

    def test_deactivate_returns_previous_state(self):
        self.mgr.activate(
            triggered_by="test",
            current_profile_mode="focus",
            current_preset_id="desk",
        )
        result = self.mgr.deactivate()
        assert result["previous"]["profile_mode"] == "focus"
        assert result["previous"]["preset_id"] == "desk"

    def test_allowed_actions_pass(self):
        for action in ALLOWED_SECURITY_ACTIONS:
            ok, _ = self.mgr.validate_action(action)
            assert ok, f"allowed action '{action}' should pass"

    def test_forbidden_actions_blocked(self):
        for action in FORBIDDEN_SECURITY_ACTIONS:
            ok, _ = self.mgr.validate_action(action)
            assert not ok, f"forbidden action '{action}' should be blocked"

    def test_unknown_action_blocked(self):
        ok, _ = self.mgr.validate_action("launch_missiles")
        assert not ok

    def test_event_history(self):
        self.mgr.activate(triggered_by="test", confidence=0.9, frame_id="f_001")
        events = self.mgr.get_recent_events()
        assert len(events) == 1
        assert events[0].triggered_by == "test"
        assert events[0].confidence == 0.9

    def test_event_resolved_on_deactivate(self):
        self.mgr.activate(triggered_by="test")
        self.mgr.deactivate(resolved_by="admin")
        events = self.mgr.get_recent_events()
        assert events[0].resolved
        assert events[0].resolved_by == "admin"

    def test_state_summary(self):
        self.mgr.activate(triggered_by="operator_command")
        summary = self.mgr.get_state_summary()
        assert summary["active"]
        assert summary["mode"] == "security_harden"
        assert "recent_events" in summary

    def test_default_actions_on_activate(self):
        state = self.mgr.activate(triggered_by="test")
        assert "lock_sensitive_controls" in state.actions_taken
        assert "increase_audit_logging" in state.actions_taken
        assert "show_security_hud" in state.actions_taken


# ── Privacy Governance ────────────────────────────────────────────

class TestOverlayPrivacy:

    def test_overlay_privacy_rules_exist(self):
        assert len(OVERLAY_PRIVACY_RULES) >= 5

    def test_forbidden_security_actions_match(self):
        assert set(PRIVACY_FORBIDDEN) == set(FORBIDDEN_SECURITY_ACTIONS)

    def test_operator_enrollment_requires_explicit(self):
        ok, _ = validate_operator_enrollment(is_explicit=False)
        assert not ok

    def test_operator_enrollment_requires_local_only(self):
        ok, _ = validate_operator_enrollment(is_explicit=True, storage_local_only=False)
        assert not ok

    def test_operator_enrollment_passes(self):
        ok, _ = validate_operator_enrollment(is_explicit=True, storage_local_only=True)
        assert ok

    def test_gesture_control_requires_explicit(self):
        ok, _ = validate_gesture_control(is_explicit=False)
        assert not ok

    def test_gesture_control_blocks_high_risk(self):
        ok, _ = validate_gesture_control(is_explicit=True, risk_level="high")
        assert not ok

    def test_gesture_control_passes_low_risk(self):
        ok, _ = validate_gesture_control(is_explicit=True, risk_level="low")
        assert ok

    def test_trigger_chain_action_blocks_forbidden(self):
        for action in FORBIDDEN_SECURITY_ACTIONS:
            ok, _ = validate_trigger_chain_action(action)
            assert not ok

    def test_trigger_chain_action_allows_valid(self):
        ok, _ = validate_trigger_chain_action("notify_operator")
        assert ok


# ── Voice Command Classification ──────────────────────────────────

class TestOverlayVoiceCommands:

    def test_show_overlay(self):
        cmd = classify_camera_command("show the tracking overlay")
        assert cmd.operation == "overlay_show"

    def test_hide_overlay(self):
        cmd = classify_camera_command("hide the tracking overlay")
        assert cmd.operation == "overlay_hide"

    def test_enable_tracker(self):
        cmd = classify_camera_command("enable face tracking")
        assert cmd.operation == "tracker_enable"
        assert cmd.params.get("category") == "face_tracker"

    def test_disable_tracker(self):
        cmd = classify_camera_command("disable hand tracking")
        assert cmd.operation == "tracker_disable"
        assert cmd.params.get("category") == "hand_tracker"

    def test_stop_all_tracking(self):
        cmd = classify_camera_command("stop all tracking")
        assert cmd.operation == "stop_all_tracking"

    def test_what_are_you_tracking(self):
        cmd = classify_camera_command("what are you tracking")
        assert cmd.operation == "tracking_status"

    def test_create_preset_voice(self):
        cmd = classify_camera_command("create a new desk preset")
        assert cmd.operation == "preset_create"

    def test_delete_preset_voice(self):
        cmd = classify_camera_command("delete the desk preset")
        assert cmd.operation == "preset_delete"

    def test_security_harden_voice(self):
        cmd = classify_camera_command("go security harden")
        assert cmd.operation == "security_activate"

    def test_security_normal_voice(self):
        cmd = classify_camera_command("exit security mode")
        assert cmd.operation == "security_deactivate"

    def test_chain_explain_voice(self):
        cmd = classify_camera_command("why did that trigger fire")
        assert cmd.operation == "chain_explain"


# ── Command Router ────────────────────────────────────────────────

class TestOverlayCommandRouter:

    def test_overlay_signals_route_to_camera(self):
        intent = classify_intent("show tracking overlay")
        assert intent == CommandIntent.CAMERA_CONTROL

    def test_tracker_signals_route_to_camera(self):
        intent = classify_intent("enable face tracking")
        assert intent == CommandIntent.CAMERA_CONTROL

    def test_preset_signals_route_to_camera(self):
        intent = classify_intent("create a new preset")
        assert intent == CommandIntent.CAMERA_CONTROL

    def test_chain_signals_route_to_camera(self):
        intent = classify_intent("why did that trigger fire")
        assert intent == CommandIntent.CAMERA_CONTROL

    def test_security_signals_route_to_camera(self):
        intent = classify_intent("go security harden")
        assert intent == CommandIntent.CAMERA_CONTROL


# ── Voice Route Resolver ──────────────────────────────────────────

class TestOverlayVoiceRouting:

    def test_overlay_routes_to_beast(self):
        assert parse_target_node("show the tracking overlay") == "beast_windows"

    def test_tracker_routes_to_beast(self):
        assert parse_target_node("enable face tracking") == "beast_windows"

    def test_preset_routes_to_beast(self):
        assert parse_target_node("create a new preset") == "beast_windows"

    def test_chain_routes_to_beast(self):
        assert parse_target_node("why did that trigger fire") == "beast_windows"

    def test_security_routes_to_beast(self):
        assert parse_target_node("go security harden") == "beast_windows"
