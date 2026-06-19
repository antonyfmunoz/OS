"""Integration tests for Campaign 20 — Voice Operations & Ambient Jarvis."""

import sys
import time
import unittest

sys.path.insert(0, "/opt/OS/.claude/worktrees/c20-voice-operations")


# ── Import coherence tests ───────────────────────────────────────────


class TestC20Imports(unittest.TestCase):
    """All C20 runtimes, types, and routes must be importable."""

    def test_import_voice_ingress_runtime(self):
        from substrate.workstation.voice_ingress_runtime import (
            ActivationMode,
            VoiceChannelContext,
            VoiceIngressEvent,
            VoiceIngressRuntime,
            VoiceIngressSnapshot,
            VoicePermissionScope,
            VoiceSourceType,
        )
        assert VoiceIngressRuntime is not None

    def test_import_voice_session_manager(self):
        from substrate.workstation.voice_session_manager import (
            ManagedVoiceSession,
            SessionConflictResolution,
            VoiceSessionManager,
            VoiceSessionManagerSnapshot,
            VoiceSessionPriority,
            VoiceSessionType,
        )
        assert VoiceSessionManager is not None

    def test_import_ambient_wake_runtime(self):
        from substrate.workstation.ambient_wake_runtime import (
            AmbientState,
            AmbientWakeRuntime,
            AmbientWakeSnapshot,
            WakeTransition,
        )
        assert AmbientWakeRuntime is not None

    def test_import_voice_output_runtime(self):
        from substrate.workstation.voice_output_runtime import (
            OutputRoutingDecision,
            VoiceOutputRuntime,
            VoiceOutputSnapshot,
            VoiceOutputTarget,
        )
        assert VoiceOutputRuntime is not None

    def test_import_voice_operations_runtime(self):
        from substrate.workstation.voice_operations_runtime import (
            VoiceCapabilityStatus,
            VoiceOperationsHealth,
            VoiceOperationsRuntime,
            VoiceOperationsSnapshot,
        )
        assert VoiceOperationsRuntime is not None

    def test_import_route_registrations(self):
        from transports.api.cockpit_voice_ingress_routes import get_router as r0
        from transports.api.cockpit_voice_session_routes import get_router as r1
        from transports.api.cockpit_ambient_wake_routes import get_router as r2
        from transports.api.cockpit_voice_output_routes import get_router as r3
        from transports.api.cockpit_voice_ops_routes import get_router as r4
        assert r0 is not None
        assert r1 is not None
        assert r2 is not None
        assert r3 is not None
        assert r4 is not None


# ── Full pipeline tests ──────────────────────────────────────────────


class TestFullPipeline(unittest.TestCase):
    """End-to-end: raw event → classify → session → query → output."""

    @classmethod
    def setUpClass(cls):
        from substrate.workstation.voice_ingress_runtime import VoiceIngressRuntime
        from substrate.workstation.voice_session_manager import VoiceSessionManager
        from substrate.workstation.ambient_wake_runtime import AmbientWakeRuntime
        from substrate.workstation.voice_output_runtime import VoiceOutputRuntime
        from substrate.workstation.voice_operations_runtime import VoiceOperationsRuntime

        cls.ingress = VoiceIngressRuntime()
        cls.session_mgr = VoiceSessionManager(voice_ingress_runtime=cls.ingress)
        cls.ambient = AmbientWakeRuntime(voice_session_manager=cls.session_mgr)
        cls.output = VoiceOutputRuntime(voice_session_manager=cls.session_mgr)
        cls.ops = VoiceOperationsRuntime(
            voice_ingress_runtime=cls.ingress,
            voice_session_manager=cls.session_mgr,
            ambient_wake_runtime=cls.ambient,
            voice_output_runtime=cls.output,
        )

    def test_classify_right_rail(self):
        event = self.ingress.classify({
            "text": "what is blocked",
            "source_type": "right_rail",
        })
        assert event.source_type == "right_rail"
        assert event.activation_mode == "push_to_talk"
        assert event.channel_context == "operator_direct"

    def test_classify_conference(self):
        event = self.ingress.classify({
            "text": "meeting notes",
            "source_type": "conference",
        })
        assert event.source_type == "conference"
        assert event.activation_mode == "conference_listening"
        assert event.channel_context == "meeting"

    def test_classify_discord(self):
        event = self.ingress.classify({
            "text": "broadcast announcement",
            "source_type": "discord",
        })
        assert event.source_type == "discord"
        assert event.activation_mode == "broadcast_transcription"

    def test_classify_ambient(self):
        event = self.ingress.classify({
            "text": "hey jarvis",
            "source_type": "ambient",
            "wake_word": True,
        })
        assert event.source_type == "ambient"
        assert event.activation_mode == "wake_word"

    def test_session_from_ingress(self):
        event = self.ingress.classify({"text": "test", "source_type": "right_rail"})
        session = self.session_mgr.start_session(event)
        assert session.session_type == "operator_chat"
        assert session.priority == "command"
        assert session.status == "active"

    def test_full_process_utterance(self):
        result = self.ops.process_utterance(
            {"text": "what is the status", "source_type": "right_rail"},
            "what is the status",
        )
        assert result["status"] == "processed"
        assert "ingress" in result
        assert result["intent_type"] == "query"
        assert "output_routing" in result


# ── Concurrent session tests ─────────────────────────────────────────


class TestConcurrentSessions(unittest.TestCase):
    """Conference + ambient coexist without conflict."""

    @classmethod
    def setUpClass(cls):
        from substrate.workstation.voice_ingress_runtime import VoiceIngressRuntime, VoiceIngressEvent
        from substrate.workstation.voice_session_manager import VoiceSessionManager

        cls.ingress = VoiceIngressRuntime()
        cls.mgr = VoiceSessionManager(voice_ingress_runtime=cls.ingress)

    def test_conference_and_ambient_coexist(self):
        conf_event = self.ingress.classify({"source_type": "conference", "text": "meeting"})
        amb_event = self.ingress.classify({"source_type": "ambient", "text": "hey"})

        conf_session = self.mgr.start_session(conf_event)
        amb_session = self.mgr.start_session(amb_event)

        active = self.mgr.active_sessions()
        active_ids = {s.session_id for s in active}
        assert conf_session.session_id in active_ids
        assert amb_session.session_id in active_ids
        assert conf_session.session_type == "conference_transcription"
        assert amb_session.session_type == "ambient_listening"

    def test_same_source_same_device_supersedes(self):
        from substrate.workstation.voice_ingress_runtime import VoiceIngressEvent

        ev1 = VoiceIngressEvent(source_type="right_rail", device_id="dev1")
        ev2 = VoiceIngressEvent(source_type="right_rail", device_id="dev1")

        s1 = self.mgr.start_session(ev1)
        s2 = self.mgr.start_session(ev2)

        assert s1.status == "superseded"
        assert s2.status == "active"


# ── Wake word state machine tests ────────────────────────────────────


class TestWakeWordStateMachine(unittest.TestCase):
    """DORMANT → PASSIVE → WAKE_DETECTED → COMMAND_ACTIVE → COOLDOWN → PASSIVE."""

    def test_full_wake_cycle(self):
        from substrate.workstation.ambient_wake_runtime import (
            AmbientState,
            AmbientWakeRuntime,
            COOLDOWN_SECONDS,
        )
        from substrate.workstation.voice_session_manager import VoiceSessionManager

        mgr = VoiceSessionManager()
        rt = AmbientWakeRuntime(voice_session_manager=mgr)

        assert rt.current_state() == AmbientState.DORMANT

        rt.activate()
        assert rt.current_state() == AmbientState.PASSIVE_LISTENING

        transition = rt.on_wake_detected("dev1", "jarvis")
        assert rt._state == AmbientState.COMMAND_ACTIVE
        assert transition.session_id != ""

        complete = rt.on_command_complete(transition.session_id)
        assert rt._state == AmbientState.COOLDOWN

        rt._last_state_change = time.time() - COOLDOWN_SECONDS - 1
        state = rt.current_state()
        assert state == AmbientState.PASSIVE_LISTENING

    def test_wake_ignored_in_dormant(self):
        from substrate.workstation.ambient_wake_runtime import (
            AmbientState,
            AmbientWakeRuntime,
        )
        rt = AmbientWakeRuntime()
        assert rt.current_state() == AmbientState.DORMANT

        transition = rt.on_wake_detected("dev1", "jarvis")
        assert rt.current_state() == AmbientState.DORMANT
        assert "ignored" in transition.trigger

    def test_deactivate_from_active(self):
        from substrate.workstation.ambient_wake_runtime import (
            AmbientState,
            AmbientWakeRuntime,
        )
        from substrate.workstation.voice_session_manager import VoiceSessionManager

        rt = AmbientWakeRuntime(voice_session_manager=VoiceSessionManager())
        rt.activate()
        rt.on_wake_detected("dev1", "jarvis")
        assert rt._state == AmbientState.COMMAND_ACTIVE

        rt.deactivate()
        assert rt.current_state() == AmbientState.DORMANT


# ── Conflict resolution tests ────────────────────────────────────────


class TestConflictResolution(unittest.TestCase):
    """COMMAND > CONVERSATION > PASSIVE."""

    @classmethod
    def setUpClass(cls):
        from substrate.workstation.voice_session_manager import VoiceSessionManager
        from substrate.workstation.voice_ingress_runtime import VoiceIngressEvent

        cls.mgr = VoiceSessionManager()
        cls.VoiceIngressEvent = VoiceIngressEvent

    def test_command_beats_conversation(self):
        from substrate.workstation.voice_session_manager import VoiceSessionPriority

        ev_conv = self.VoiceIngressEvent(source_type="conference")
        ev_cmd = self.VoiceIngressEvent(source_type="right_rail", activation_mode="command_mode")

        s_conv = self.mgr.start_session(ev_conv)
        s_cmd = self.mgr.start_session(ev_cmd)

        resolution = self.mgr.resolve_conflict(s_cmd.session_id, s_conv.session_id)
        assert resolution.winner_id == s_cmd.session_id

    def test_conversation_beats_passive(self):
        ev_passive = self.VoiceIngressEvent(source_type="system_audio")
        ev_conv = self.VoiceIngressEvent(source_type="conference")

        s_passive = self.mgr.start_session(ev_passive)
        s_conv = self.mgr.start_session(ev_conv)

        resolution = self.mgr.resolve_conflict(s_conv.session_id, s_passive.session_id)
        assert resolution.winner_id == s_conv.session_id

    def test_same_priority_newer_wins(self):
        ev1 = self.VoiceIngressEvent(source_type="system_audio")
        ev2 = self.VoiceIngressEvent(source_type="system_audio")

        s1 = self.mgr.start_session(ev1)
        time.sleep(0.01)
        s2 = self.mgr.start_session(ev2)

        resolution = self.mgr.resolve_conflict(s1.session_id, s2.session_id)
        assert resolution.winner_id == s2.session_id


# ── Output routing accuracy tests ────────────────────────────────────


class TestOutputRoutingAccuracy(unittest.TestCase):
    """Each source type maps to correct output targets."""

    @classmethod
    def setUpClass(cls):
        from substrate.workstation.voice_output_runtime import VoiceOutputRuntime
        cls.output = VoiceOutputRuntime()

    def test_right_rail_targets(self):
        targets = self.output.output_targets_for_source("right_rail")
        assert "spoken_reply" in targets
        assert "right_rail_text" in targets

    def test_conference_targets(self):
        targets = self.output.output_targets_for_source("conference")
        assert "conference_log" in targets
        assert "spoken_reply" not in targets

    def test_discord_targets(self):
        targets = self.output.output_targets_for_source("discord")
        assert "discord_voice" in targets

    def test_system_audio_targets(self):
        targets = self.output.output_targets_for_source("system_audio")
        assert "silent_log" in targets

    def test_ambient_targets(self):
        targets = self.output.output_targets_for_source("ambient")
        assert "spoken_reply" in targets
        assert "right_rail_text" in targets
        assert "silent_log" in targets

    def test_unknown_source_defaults(self):
        targets = self.output.output_targets_for_source("unknown_source")
        assert "silent_log" in targets


# ── Graceful degradation tests ───────────────────────────────────────


class TestGracefulDegradation(unittest.TestCase):
    """All runtimes work with None deps."""

    def test_ingress_no_deps(self):
        from substrate.workstation.voice_ingress_runtime import VoiceIngressRuntime
        rt = VoiceIngressRuntime()
        event = rt.classify({"text": "hello", "source_type": "right_rail"})
        assert event.source_type == "right_rail"

    def test_session_manager_no_deps(self):
        from substrate.workstation.voice_session_manager import VoiceSessionManager
        from substrate.workstation.voice_ingress_runtime import VoiceIngressEvent
        mgr = VoiceSessionManager()
        session = mgr.start_session(VoiceIngressEvent())
        assert session.status == "active"

    def test_ambient_no_deps(self):
        from substrate.workstation.ambient_wake_runtime import AmbientWakeRuntime, AmbientState
        rt = AmbientWakeRuntime()
        assert rt.current_state() == AmbientState.DORMANT
        snap = rt.snapshot()
        assert snap.state == "dormant"

    def test_output_no_deps(self):
        from substrate.workstation.voice_output_runtime import VoiceOutputRuntime
        rt = VoiceOutputRuntime()
        snap = rt.snapshot()
        assert snap.health == "idle"

    def test_operations_no_deps(self):
        from substrate.workstation.voice_operations_runtime import VoiceOperationsRuntime
        rt = VoiceOperationsRuntime()
        snap = rt.snapshot()
        assert snap.health in ("offline", "optimal", "active", "degraded")


# ── Cross-runtime composition tests ─────────────────────────────────


class TestCrossRuntimeComposition(unittest.TestCase):
    """VoiceOperationsRuntime properly composes all 4 sub-runtimes."""

    @classmethod
    def setUpClass(cls):
        from substrate.workstation.voice_ingress_runtime import VoiceIngressRuntime
        from substrate.workstation.voice_session_manager import VoiceSessionManager
        from substrate.workstation.ambient_wake_runtime import AmbientWakeRuntime
        from substrate.workstation.voice_output_runtime import VoiceOutputRuntime
        from substrate.workstation.voice_operations_runtime import VoiceOperationsRuntime

        ingress = VoiceIngressRuntime()
        session_mgr = VoiceSessionManager(voice_ingress_runtime=ingress)
        ambient = AmbientWakeRuntime(voice_session_manager=session_mgr)
        output = VoiceOutputRuntime(voice_session_manager=session_mgr)

        cls.ops = VoiceOperationsRuntime(
            voice_ingress_runtime=ingress,
            voice_session_manager=session_mgr,
            ambient_wake_runtime=ambient,
            voice_output_runtime=output,
        )

    def test_snapshot_has_all_sections(self):
        snap = self.ops.snapshot()
        d = snap.to_dict()
        assert "ingress_status" in d
        assert "active_sessions" in d
        assert "ambient_state" in d
        assert "output_status" in d
        assert "capabilities" in d

    def test_capabilities_reflect_composition(self):
        caps = self.ops.capabilities()
        assert caps.stt_available is True
        assert caps.tts_available is True
        assert caps.conference_available is True

    def test_health_is_not_offline(self):
        h = self.ops.health()
        from substrate.workstation.voice_operations_runtime import VoiceOperationsHealth
        assert h != VoiceOperationsHealth.OFFLINE


if __name__ == "__main__":
    unittest.main()
