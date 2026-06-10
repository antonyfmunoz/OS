"""Phase 14.15 — Full Continuity Daily Driver tests.

Tests: continuity state persistence, startup/shutdown sequences, profile modes,
lifecycle modes, intent contracts, loop verification, presence detection,
wake triggers, notification cadence, and the grounding firewall constraint
(no hallucination regression).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid

import pytest

sys.path.insert(0, "/opt/OS")


# ─── Continuity State ───────────────────────────────────────────────────────


class TestContinuityStatePersistence:
    def test_state_machine_roundtrip(self):
        from substrate.workstation.continuity import (
            ContinuityState,
            ContinuityStateMachine,
        )

        sm = ContinuityStateMachine()
        assert sm.current_state == ContinuityState.ACTIVE
        sm.transition(ContinuityState.AWAY, reason="test")
        data = sm.to_dict()
        restored = ContinuityStateMachine.from_dict(data)
        assert restored.current_state == ContinuityState.AWAY
        assert len(restored.history) == 1

    def test_invalid_transition_raises(self):
        from substrate.workstation.continuity import (
            ContinuityState,
            ContinuityStateMachine,
        )

        sm = ContinuityStateMachine(ContinuityState.AWAY)
        with pytest.raises(ValueError):
            sm.transition(ContinuityState.IDLE)

    def test_composite_state_to_dict(self):
        from substrate.workstation.continuity_engine import CompositeState

        state = CompositeState(
            operator_presence="present",
            lifecycle_mode="day_cycle",
            profile_mode="developer",
        )
        d = state.to_dict()
        assert d["operator_presence"] == "present"
        assert d["lifecycle_mode"] == "day_cycle"
        assert "last_updated_at" in d

    def test_composite_state_roundtrip(self):
        from substrate.workstation.continuity_engine import CompositeState

        state = CompositeState(
            operator_presence="away",
            profile_mode="research",
            open_blockers=["test blocker"],
        )
        d = state.to_dict()
        restored = CompositeState.from_dict(d)
        assert restored.operator_presence == "away"
        assert restored.profile_mode == "research"
        assert restored.open_blockers == ["test blocker"]


# ─── Startup Sequence ───────────────────────────────────────────────────────


class TestStartupSequence:
    def test_startup_uses_grounded_data(self):
        from substrate.workstation.continuity_engine import ContinuityEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ContinuityEngine(state_dir=tmpdir)
            result = engine.startup_sequence()
            assert result.success is True
            assert result.continuity_state == "active"
            assert result.lifecycle_mode == "day_cycle"
            assert isinstance(result.provider_status, dict)
            assert isinstance(result.node_status, dict)

    def test_startup_classifies_deterministically(self):
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        assert classify_intent("start my day") == CommandIntent.STARTUP_SEQUENCE
        assert classify_intent("start work mode") == CommandIntent.STARTUP_SEQUENCE
        assert classify_intent("begin startup sequence") == CommandIntent.STARTUP_SEQUENCE
        assert classify_intent("start the day") == CommandIntent.STARTUP_SEQUENCE

    def test_startup_transitions_from_away(self):
        from substrate.workstation.continuity import (
            ContinuityState,
            ContinuityStateMachine,
        )
        from substrate.workstation.continuity_engine import ContinuityEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = ContinuityStateMachine(ContinuityState.AWAY)
            sm_path = os.path.join(tmpdir, "continuity_state_machine.json")
            with open(sm_path, "w") as f:
                json.dump(sm.to_dict(), f)

            engine = ContinuityEngine(state_dir=tmpdir)
            result = engine.startup_sequence()
            assert result.continuity_state == "active"


# ─── Shutdown / End-of-Day ────────────────────────────────────────────────


class TestShutdownSequence:
    def test_shutdown_creates_report(self):
        from substrate.workstation.continuity_engine import ContinuityEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ContinuityEngine(state_dir=tmpdir)
            result = engine.shutdown_sequence()
            assert result.success is True
            assert result.resume_point != ""

    def test_shutdown_classifies_deterministically(self):
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        assert classify_intent("end my day") == CommandIntent.SHUTDOWN_SEQUENCE
        assert classify_intent("seal the session") == CommandIntent.SHUTDOWN_SEQUENCE
        assert classify_intent("good night") == CommandIntent.SHUTDOWN_SEQUENCE


# ─── Profile Modes ──────────────────────────────────────────────────────────


class TestProfileModes:
    def test_deep_work_behavior_config(self):
        from substrate.workstation.profile_behavior import (
            DEFAULT_BEHAVIORS,
            get_behavior,
        )

        dev = get_behavior("developer")
        assert dev.voice_behavior == "minimal_interruptions"
        assert dev.notification_policy == "important_only"
        assert dev.camera_policy == "off"
        assert dev.reporting_cadence == "blocker_or_completion"

    def test_all_profiles_have_behaviors(self):
        from substrate.workstation.profile_behavior import DEFAULT_BEHAVIORS
        from substrate.workstation.profile_modes import ProfileMode

        for mode in ProfileMode:
            assert mode.value in DEFAULT_BEHAVIORS, f"No behavior for {mode.value}"

    def test_profile_switch_classifies(self):
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        assert classify_intent("enter deep work") == CommandIntent.MODE_SWITCH
        assert classify_intent("switch to creative mode") == CommandIntent.MODE_SWITCH
        assert classify_intent("start admin mode") == CommandIntent.MODE_SWITCH
        assert classify_intent("research mode") == CommandIntent.MODE_SWITCH

    def test_profile_mode_resolves(self):
        from substrate.workstation.command_router import resolve_mode_target

        assert resolve_mode_target("enter deep work") == "developer"
        assert resolve_mode_target("switch to creative mode") == "design"
        assert resolve_mode_target("start admin mode") == "command_center"
        assert resolve_mode_target("research mode") == "research"
        assert resolve_mode_target("music mode") == "music"
        assert resolve_mode_target("finance mode") == "finance"
        assert resolve_mode_target("learning mode") == "learning"

    def test_fallback_behavior(self):
        from substrate.workstation.profile_behavior import get_behavior

        unknown = get_behavior("nonexistent_mode")
        assert unknown.profile_mode == "nonexistent_mode"
        assert unknown.voice_behavior == "full"


# ─── Lifecycle Modes ────────────────────────────────────────────────────────


class TestLifecycleModes:
    def test_lifecycle_mode_away(self):
        from substrate.workstation.lifecycle_modes import (
            LIFECYCLE_RISK_CEILING,
            LifecycleMode,
        )

        assert LifecycleMode.AWAY.value == "away"
        assert LIFECYCLE_RISK_CEILING[LifecycleMode.AWAY] == "LOW"

    def test_lifecycle_risk_ceiling_day_cycle(self):
        from substrate.workstation.lifecycle_modes import (
            LIFECYCLE_RISK_CEILING,
            LifecycleMode,
        )

        assert LIFECYCLE_RISK_CEILING[LifecycleMode.DAY_CYCLE] == "HIGH"

    def test_notification_override_for_lifecycle(self):
        from substrate.workstation.profile_behavior import (
            resolve_effective_notification_policy,
        )

        policy = resolve_effective_notification_policy("developer", "night_cycle")
        assert policy == "critical_only"

        policy = resolve_effective_notification_policy("command_center", "day_cycle")
        assert policy == "all"

    def test_lifecycle_away_classifies(self):
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        assert classify_intent("i'm stepping away") == CommandIntent.CONTINUITY_TRANSITION
        assert classify_intent("pause everything") == CommandIntent.CONTINUITY_TRANSITION


# ─── Presence ───────────────────────────────────────────────────────────────


class TestPresence:
    def test_presence_remote_vs_workstation(self):
        from substrate.workstation.continuity import (
            ContinuityState,
            ContinuityStateMachine,
        )

        sm = ContinuityStateMachine()
        sm.transition(ContinuityState.REMOTE, reason="phone")
        assert sm.current_state == ContinuityState.REMOTE
        sm.transition(ContinuityState.ACTIVE, reason="back at desk")
        assert sm.current_state == ContinuityState.ACTIVE

    def test_activation_capabilities_truthful(self):
        from substrate.workstation.activation import get_activation_capabilities

        caps = get_activation_capabilities()
        assert len(caps) > 0
        wake_word = next(c for c in caps if "Wake" in c.name)
        assert wake_word.status == "not_implemented"
        assert wake_word.blocker != ""


# ─── Intent Contracts ───────────────────────────────────────────────────────


class TestIntentContract:
    def test_high_level_intent_creates_contract(self):
        from substrate.workstation.intent_contract import create_contract_from_intent

        contract = create_contract_from_intent("build the vision controller")
        assert contract.operator_intent == "build the vision controller"
        assert contract.desired_end_state != ""
        assert contract.risk_level == "medium"
        assert contract.status == "contract_created"

    def test_intent_capture_classifies(self):
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        assert classify_intent("build this") == CommandIntent.INTENT_CAPTURE
        assert classify_intent("fix this") == CommandIntent.INTENT_CAPTURE
        assert classify_intent("get this shipped") == CommandIntent.INTENT_CAPTURE
        assert classify_intent("finish the camera controller") == CommandIntent.INTENT_CAPTURE

    def test_contract_persistence(self):
        from substrate.workstation.intent_contract import (
            IntentContractManager,
            create_contract_from_intent,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = IntentContractManager(state_dir=tmpdir)
            contract = create_contract_from_intent("ship the cockpit update")
            mgr.save(contract)

            loaded = mgr.get(contract.intent_id)
            assert loaded is not None
            assert loaded.operator_intent == "ship the cockpit update"

            active = mgr.get_active()
            assert len(active) == 1

    def test_contract_lifecycle(self):
        from substrate.workstation.intent_contract import create_contract_from_intent

        contract = create_contract_from_intent("test the loop engine")
        assert not contract.is_terminal

        contract.advance("iteration 1 evidence", "executing")
        assert contract.current_iteration == 1
        assert contract.status == "executing"

        contract.mark_blocked("need approval for deployment")
        assert contract.is_blocked
        assert contract.blocker == "need approval for deployment"

        contract.mark_verified("all tests pass")
        assert contract.is_terminal
        assert contract.completed_at != ""

    def test_intent_risk_classification(self):
        from substrate.workstation.intent_contract import extract_intent_risk

        assert extract_intent_risk("build a new feature") == "medium"
        assert extract_intent_risk("deploy to production") == "high"
        assert extract_intent_risk("research market trends") == "low"
        assert extract_intent_risk("delete old data") == "high"
        assert extract_intent_risk("test the new endpoint") == "low"


# ─── Loop Engine ────────────────────────────────────────────────────────────


class TestLoopEngine:
    def test_loop_runs_until_verified(self):
        from substrate.workstation.loop_engine import LoopContract, advance_loop

        contract = LoopContract(
            task_description="Open Chrome",
            end_state_description="Chrome visible on screen",
            max_iterations=5,
        )
        _, result = advance_loop(contract, {"screenshot_taken": True, "screenshot_path": "/tmp/chrome.png"})
        assert result.verified is True
        assert contract.status.value == "verified"

    def test_loop_retries_when_not_done(self):
        from substrate.workstation.loop_engine import LoopContract, LoopStatus, advance_loop

        contract = LoopContract(
            task_description="Wait for build",
            end_state_description="Build complete",
            max_iterations=3,
        )
        _, result = advance_loop(contract, {"build_status": "running"})
        assert result.verified is False
        assert contract.status == LoopStatus.running

    def test_loop_fails_at_max_iterations(self):
        from substrate.workstation.loop_engine import LoopContract, LoopStatus, advance_loop

        contract = LoopContract(
            task_description="Wait for build",
            end_state_description="Build complete",
            max_iterations=2,
        )
        advance_loop(contract, {"status": "running"})
        _, result = advance_loop(contract, {"status": "still running"})
        assert contract.status == LoopStatus.failed
        assert contract.completed_at is not None

    def test_loop_blocks_with_exact_reason(self):
        from substrate.workstation.intent_contract import create_contract_from_intent

        contract = create_contract_from_intent("deploy cockpit")
        contract.mark_blocked("flyctl auth token expired")
        assert contract.is_blocked
        assert contract.blocker == "flyctl auth token expired"


# ─── Wake / Activation ──────────────────────────────────────────────────────


class TestWakeAndActivation:
    def test_wake_phrase_classifies(self):
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        assert classify_intent("start my day") == CommandIntent.STARTUP_SEQUENCE
        assert classify_intent("wake up the system") == CommandIntent.STARTUP_SEQUENCE

    def test_clap_trigger_unsupported_returns_blocker(self):
        from substrate.workstation.activation import (
            ActivationCapabilityStatus,
            get_activation_capabilities,
        )

        caps = get_activation_capabilities()
        clap = next(c for c in caps if "Clap" in c.name)
        assert clap.status == ActivationCapabilityStatus.NOT_IMPLEMENTED.value
        assert "not implemented" in clap.blocker.lower()

    def test_room_entry_does_not_secretly_enable_camera(self):
        from substrate.workstation.profile_behavior import get_behavior

        dev = get_behavior("developer")
        assert dev.camera_policy == "off"

        finance = get_behavior("finance")
        assert finance.camera_policy == "off"


# ─── Autonomy Governance ────────────────────────────────────────────────────


class TestAutonomyGovernance:
    def test_autonomy_respects_approval_policy(self):
        from substrate.workstation.profile_behavior import get_behavior

        dev = get_behavior("developer")
        assert dev.approval_policy == "batch_noncritical"

        finance = get_behavior("finance")
        assert finance.approval_policy == "immediate"

    def test_camera_auto_preview_requires_profile(self):
        from substrate.workstation.profile_behavior import DEFAULT_BEHAVIORS

        for name, behavior in DEFAULT_BEHAVIORS.items():
            if behavior.camera_policy == "live":
                pytest.fail(
                    f"Profile {name} has camera_policy=live — "
                    f"auto-live camera requires operator consent"
                )


# ─── Notification Cadence ───────────────────────────────────────────────────


class TestNotificationCadence:
    def test_cadence_deep_work(self):
        from substrate.workstation.profile_behavior import get_behavior

        dev = get_behavior("developer")
        assert dev.reporting_cadence == "blocker_or_completion"

    def test_cadence_night_cycle_override(self):
        from substrate.workstation.profile_behavior import (
            resolve_effective_notification_policy,
        )

        policy = resolve_effective_notification_policy("command_center", "overnight")
        assert policy == "silent"


# ─── Resume After Absence ───────────────────────────────────────────────────


class TestResumeAfterAbsence:
    def test_resume_classifies(self):
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        assert classify_intent("what changed while I was away?") == CommandIntent.RESUME_QUERY
        assert classify_intent("what happened while i was gone") == CommandIntent.RESUME_QUERY
        assert classify_intent("what have you been doing") == CommandIntent.RESUME_QUERY

    def test_resume_brief_roundtrip(self):
        from substrate.workstation.resume_brief import ReturnBrief

        brief = ReturnBrief(
            continuity_state_at_departure="away",
            continuity_state_now="active",
            what_finished=["Vision Controller"],
            what_is_blocked=["Hermes API key"],
            resume_next="Unblock Hermes API key",
        )
        d = brief.to_dict()
        restored = ReturnBrief.from_dict(d)
        assert restored.what_finished == ["Vision Controller"]
        assert restored.resume_next == "Unblock Hermes API key"

    def test_checkpoint_persistence(self):
        from substrate.workstation.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(state_dir=tmpdir)
            ckpt = mgr.create_checkpoint(
                previous_state="away",
                new_state="active",
                lifecycle_mode="day_cycle",
                transition_reason="operator returned",
            )
            loaded = mgr.latest()
            assert loaded is not None
            assert loaded.previous_continuity_state == "away"
            assert loaded.new_continuity_state == "active"


# ─── Four Surfaces Share State ──────────────────────────────────────────────


class TestFourSurfacesShareState:
    def test_composite_state_includes_all_fields(self):
        from substrate.workstation.continuity_engine import CompositeState

        state = CompositeState()
        d = state.to_dict()
        required_fields = {
            "operator_presence", "lifecycle_mode", "profile_mode",
            "execution_mode", "active_work_loops", "open_blockers",
            "pending_approvals", "last_resume_point",
        }
        assert required_fields.issubset(set(d.keys()))


# ─── No Fake Done Without Proof ─────────────────────────────────────────────


class TestNoFakeDone:
    def test_loop_cannot_mark_done_without_evidence(self):
        from substrate.workstation.loop_engine import LoopContract, advance_loop

        contract = LoopContract(
            task_description="Deploy cockpit",
            end_state_description="Cockpit deployed and healthy",
            max_iterations=3,
        )
        _, result = advance_loop(contract, {})
        assert result.verified is False

    def test_intent_contract_done_has_proof(self):
        from substrate.workstation.intent_contract import create_contract_from_intent

        contract = create_contract_from_intent("test verification")
        contract.mark_verified("test suite passed: 103/103")
        assert contract.is_terminal
        assert "103/103" in contract.evidence_log[-1]


# ─── Grounding Regression ──────────────────────────────────────────────────


class TestGroundingRegression:
    def test_status_queries_still_grounded(self):
        from substrate.organism.grounding_registry import detect_status_seeking

        assert detect_status_seeking("docker container status") is not None
        assert detect_status_seeking("what providers are online") is not None
        assert detect_status_seeking("what reports were created today") is not None

    def test_new_commands_do_not_break_grounding(self):
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        assert classify_intent("docker containers") == CommandIntent.VPS_CONTROL
        assert classify_intent("provider health") == CommandIntent.VPS_CONTROL
        assert classify_intent("what is blocked") == CommandIntent.BLOCKED_QUERY

    def test_continuity_commands_do_not_fall_to_llm(self):
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        continuity_commands = [
            "start my day",
            "end my day",
            "seal the session",
            "enter deep work",
            "i'm stepping away",
            "what changed while I was away?",
            "build this",
            "fix this",
            "get this shipped",
        ]
        for cmd in continuity_commands:
            intent = classify_intent(cmd)
            assert intent != CommandIntent.UNKNOWN, (
                f"'{cmd}' classified as UNKNOWN — would fall to LLM"
            )


# ─── Canonical Type Registration ────────────────────────────────────────────


class TestCanonicalTypes:
    def test_continuity_types_registered(self):
        from substrate.canonical_types import lookup

        registered = [
            "ContinuityState", "ContinuityStateMachine", "LifecycleMode",
            "ProfileMode", "ProfileBehavior", "IntentContract",
            "IntentContractManager", "CompositeState", "ContinuityEngine",
            "CommandIntent", "LoopContract", "ActivationSource",
            "ContinuityCheckpoint", "ReturnBrief",
        ]
        for name in registered:
            result = lookup(name)
            assert result is not None, f"{name} not registered in canonical_types"
