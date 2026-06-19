"""Tests for Campaign 20.4 — Voice Operations Runtime."""

import sys
import time
import unittest

sys.path.insert(0, "/opt/OS/.claude/worktrees/c20-voice-operations")

from substrate.workstation.voice_operations_runtime import (
    VoiceCapabilityStatus,
    VoiceOperationsHealth,
    VoiceOperationsRuntime,
    VoiceOperationsSnapshot,
    _is_action_intent,
)


# ── Mock helpers ──────────────────────────────────────────────────────


class MockIngressEvent:
    def __init__(self, source_type="right_rail"):
        self.source_type = source_type
        self.activation_mode = "push_to_talk"
        self.device_id = "dev1"
        self.speaker_id = "spk1"
        self.metadata = {}

    def to_dict(self):
        return {
            "source_type": self.source_type,
            "activation_mode": self.activation_mode,
            "device_id": self.device_id,
            "speaker_id": self.speaker_id,
        }


class MockIngressRuntime:
    def classify(self, raw_event):
        return MockIngressEvent(raw_event.get("source_type", "right_rail"))

    def snapshot(self):
        return type("Snap", (), {"to_dict": lambda self: {"health": "active"}})()


class MockManagedSession:
    def __init__(self):
        self.session_id = "vms_test123"
        self.session_type = "operator_chat"
        self.source_type = "right_rail"
        self.priority = "command"
        self.status = "active"

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "source_type": self.source_type,
            "priority": self.priority,
            "status": self.status,
        }


class MockSessionManager:
    def start_session(self, event):
        return MockManagedSession()

    def get_session(self, session_id):
        return MockManagedSession()

    def snapshot(self):
        return type("Snap", (), {
            "active_sessions": [MockManagedSession().to_dict()],
            "to_dict": lambda self: {"active_sessions": self.active_sessions},
        })()


class MockAmbientWake:
    def current_state(self):
        from substrate.workstation.ambient_wake_runtime import AmbientState
        return AmbientState.PASSIVE_LISTENING

    def listening_devices(self):
        return ["dev1"]

    def snapshot(self):
        return type("Snap", (), {"to_dict": lambda self: {"state": "passive_listening"}})()


class MockOutputDecision:
    def __init__(self):
        self.targets = ["spoken_reply", "right_rail_text"]
        self.rationale = "source_type=right_rail"
        self.session_id = "vms_test123"
        self.source_type = "right_rail"
        self.session_type = "operator_chat"
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "targets": self.targets,
            "rationale": self.rationale,
            "session_id": self.session_id,
            "source_type": self.source_type,
        }


class MockOutputRuntime:
    def route_output(self, session_id, response_text, source_type=""):
        return MockOutputDecision()

    def snapshot(self):
        return type("Snap", (), {"to_dict": lambda self: {"health": "idle"}})()


class MockQueryResolution:
    def to_dict(self):
        return {
            "domain": "status",
            "answer_text": "System is optimal.",
            "confidence": 0.90,
        }


class MockQueryEngine:
    def resolve(self, text):
        return MockQueryResolution()


class MockCommandResult:
    def to_dict(self):
        return {
            "command_id": "cmd_123",
            "action_type": "create_workpacket",
            "status": "routed",
        }


class MockCommandRuntime:
    def process(self, text, source="voice"):
        return MockCommandResult()


# ── Type tests ────────────────────────────────────────────────────────


class TestVoiceOperationsHealthEnum(unittest.TestCase):
    def test_values(self):
        assert VoiceOperationsHealth.OPTIMAL.value == "optimal"
        assert VoiceOperationsHealth.ACTIVE.value == "active"
        assert VoiceOperationsHealth.DEGRADED.value == "degraded"
        assert VoiceOperationsHealth.OFFLINE.value == "offline"

    def test_all_members(self):
        members = list(VoiceOperationsHealth)
        assert len(members) == 4


class TestVoiceCapabilityStatus(unittest.TestCase):
    def test_defaults(self):
        caps = VoiceCapabilityStatus()
        assert caps.stt_available is False
        assert caps.tts_available is False
        assert caps.wake_word_available is False
        assert caps.conference_available is False
        assert caps.ambient_available is False

    def test_to_dict(self):
        caps = VoiceCapabilityStatus(stt_available=True, tts_available=True)
        d = caps.to_dict()
        assert d["stt_available"] is True
        assert d["tts_available"] is True
        assert d["wake_word_available"] is False

    def test_all_true(self):
        caps = VoiceCapabilityStatus(
            stt_available=True, tts_available=True,
            wake_word_available=True, conference_available=True,
            ambient_available=True,
        )
        d = caps.to_dict()
        assert all(d.values())


class TestVoiceOperationsSnapshot(unittest.TestCase):
    def test_defaults(self):
        snap = VoiceOperationsSnapshot()
        assert snap.health == "offline"
        assert snap.active_sessions == []
        assert snap.ambient_state == "dormant"
        assert snap.stt_available is False

    def test_to_dict(self):
        snap = VoiceOperationsSnapshot(
            health="active",
            ambient_state="passive_listening",
            stt_available=True,
        )
        d = snap.to_dict()
        assert d["health"] == "active"
        assert d["ambient_state"] == "passive_listening"
        assert d["stt_available"] is True


# ── Intent detection tests ────────────────────────────────────────────


class TestIsActionIntent(unittest.TestCase):
    def test_action_keywords(self):
        assert _is_action_intent("build LOS onboarding") is True
        assert _is_action_intent("deploy the cockpit") is True
        assert _is_action_intent("create a work packet") is True
        assert _is_action_intent("run the tests") is True
        assert _is_action_intent("execute wp-abc123") is True
        assert _is_action_intent("start execution") is True
        assert _is_action_intent("stop the service") is True
        assert _is_action_intent("restart os-discord") is True
        assert _is_action_intent("cancel the build") is True
        assert _is_action_intent("approve the packet") is True
        assert _is_action_intent("reject the plan") is True
        assert _is_action_intent("submit work") is True
        assert _is_action_intent("dispatch agent") is True
        assert _is_action_intent("schedule deployment") is True

    def test_query_keywords(self):
        assert _is_action_intent("what is blocked") is False
        assert _is_action_intent("show status") is False
        assert _is_action_intent("how many agents") is False
        assert _is_action_intent("where is the bug") is False
        assert _is_action_intent("status of services") is False

    def test_empty_string(self):
        assert _is_action_intent("") is False

    def test_case_sensitivity(self):
        assert _is_action_intent("build something") is True
        assert _is_action_intent("BUILD something") is True


# ── Runtime tests (no deps) ──────────────────────────────────────────


class TestVoiceOperationsNoDeps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = VoiceOperationsRuntime()

    def test_snapshot_no_deps(self):
        snap = self.runtime.snapshot()
        assert snap.health in ("offline", "optimal", "active", "degraded")

    def test_health_no_deps(self):
        h = self.runtime.health()
        assert isinstance(h, VoiceOperationsHealth)

    def test_capabilities_no_deps(self):
        caps = self.runtime.capabilities()
        assert hasattr(caps, "stt_available")
        assert hasattr(caps, "tts_available")

    def test_summary_no_deps(self):
        s = self.runtime.summary()
        assert "health" in s
        assert "active_sessions" in s

    def test_process_utterance_no_deps(self):
        result = self.runtime.process_utterance(
            {"text": "what is blocked"}, "what is blocked",
        )
        assert result["status"] == "processed"


# ── Runtime tests (with mocks) ───────────────────────────────────────


class TestVoiceOperationsWithMocks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = VoiceOperationsRuntime(
            voice_ingress_runtime=MockIngressRuntime(),
            voice_session_manager=MockSessionManager(),
            ambient_wake_runtime=MockAmbientWake(),
            voice_output_runtime=MockOutputRuntime(),
            voice_query_engine=MockQueryEngine(),
            command_runtime=MockCommandRuntime(),
        )

    def test_health_all_deps(self):
        h = self.runtime.health()
        assert h in (VoiceOperationsHealth.OPTIMAL, VoiceOperationsHealth.ACTIVE)

    def test_snapshot_all_deps(self):
        snap = self.runtime.snapshot()
        assert snap.health in ("optimal", "active")
        assert snap.ambient_state == "passive_listening"
        assert snap.devices_listening == ["dev1"]
        assert len(snap.query_engine_domains) > 0

    def test_capabilities_all_deps(self):
        caps = self.runtime.capabilities()
        assert caps.stt_available is True
        assert caps.tts_available is True
        assert caps.conference_available is True

    def test_summary_all_deps(self):
        s = self.runtime.summary()
        assert s["health"] in ("optimal", "active")
        assert s["query_domains"] > 0

    def test_process_query_intent(self):
        result = self.runtime.process_utterance(
            {"text": "what is blocked", "source_type": "right_rail"},
            "what is blocked",
        )
        assert result["intent_type"] == "query"
        assert result["resolution"]["domain"] == "status"
        assert "output_routing" in result

    def test_process_action_intent(self):
        result = self.runtime.process_utterance(
            {"text": "build LOS onboarding", "source_type": "right_rail"},
            "build LOS onboarding",
        )
        assert result["intent_type"] == "action"
        assert result["resolution"]["action_type"] == "create_workpacket"
        assert "output_routing" in result

    def test_process_includes_ingress(self):
        result = self.runtime.process_utterance(
            {"text": "show status", "source_type": "right_rail"},
            "show status",
        )
        assert "ingress" in result
        assert result["ingress"]["source_type"] == "right_rail"

    def test_process_includes_session(self):
        result = self.runtime.process_utterance(
            {"text": "show status"}, "show status",
        )
        assert "session" in result
        assert result["session"]["session_id"] == "vms_test123"

    def test_process_output_routing(self):
        result = self.runtime.process_utterance(
            {"text": "show status"}, "show status",
        )
        assert "output_routing" in result
        routing = result["output_routing"]
        assert "spoken_reply" in routing["targets"]


# ── Health derivation tests ──────────────────────────────────────────


class TestHealthDerivation(unittest.TestCase):
    def test_no_explicit_subsystems(self):
        rt = VoiceOperationsRuntime()
        h = rt.health()
        assert isinstance(h, VoiceOperationsHealth)

    def test_partial_explicit_subsystems(self):
        rt = VoiceOperationsRuntime(
            voice_ingress_runtime=MockIngressRuntime(),
        )
        h = rt.health()
        assert isinstance(h, VoiceOperationsHealth)

    def test_optimal_all_subsystems_no_sessions(self):
        rt = VoiceOperationsRuntime(
            voice_ingress_runtime=MockIngressRuntime(),
            voice_session_manager=type("M", (), {
                "snapshot": lambda self: type("S", (), {
                    "active_sessions": [],
                })(),
            })(),
            voice_output_runtime=MockOutputRuntime(),
            voice_query_engine=MockQueryEngine(),
        )
        assert rt.health() == VoiceOperationsHealth.OPTIMAL

    def test_active_with_sessions(self):
        rt = VoiceOperationsRuntime(
            voice_ingress_runtime=MockIngressRuntime(),
            voice_session_manager=MockSessionManager(),
            voice_output_runtime=MockOutputRuntime(),
            voice_query_engine=MockQueryEngine(),
        )
        assert rt.health() == VoiceOperationsHealth.ACTIVE


# ── Error handling tests ─────────────────────────────────────────────


class TestErrorHandling(unittest.TestCase):
    def test_ingress_failure_graceful(self):
        class FailIngress:
            def classify(self, raw):
                raise RuntimeError("ingress down")
        rt = VoiceOperationsRuntime(
            voice_ingress_runtime=FailIngress(),
            voice_query_engine=MockQueryEngine(),
        )
        result = rt.process_utterance({"text": "test"}, "test")
        assert result["status"] == "processed"
        assert "ingress_error" in result

    def test_session_failure_graceful(self):
        class FailSession:
            def start_session(self, event):
                raise RuntimeError("session down")
        rt = VoiceOperationsRuntime(
            voice_ingress_runtime=MockIngressRuntime(),
            voice_session_manager=FailSession(),
            voice_query_engine=MockQueryEngine(),
        )
        result = rt.process_utterance({"text": "test"}, "test")
        assert result["status"] == "processed"
        assert "session_error" in result

    def test_query_engine_failure_graceful(self):
        class FailQuery:
            def resolve(self, text):
                raise RuntimeError("query down")
        rt = VoiceOperationsRuntime(
            voice_ingress_runtime=MockIngressRuntime(),
            voice_query_engine=FailQuery(),
        )
        result = rt.process_utterance({"text": "show status"}, "show status")
        assert result["status"] == "processed"
        assert result["resolution"]["domain"] == "error"

    def test_command_runtime_failure_graceful(self):
        class FailCommand:
            def process(self, text, source="voice"):
                raise RuntimeError("command down")
        rt = VoiceOperationsRuntime(
            voice_ingress_runtime=MockIngressRuntime(),
            command_runtime=FailCommand(),
        )
        result = rt.process_utterance({"text": "build X"}, "build X")
        assert result["status"] == "processed"
        assert result["resolution"]["action"] == "delegation_failed"

    def test_output_routing_failure_graceful(self):
        class FailOutput:
            def route_output(self, session_id, text, source_type=""):
                raise RuntimeError("output down")
            def snapshot(self):
                raise RuntimeError("snap down")
        rt = VoiceOperationsRuntime(
            voice_ingress_runtime=MockIngressRuntime(),
            voice_output_runtime=FailOutput(),
            voice_query_engine=MockQueryEngine(),
        )
        result = rt.process_utterance({"text": "show status"}, "show status")
        assert result["status"] == "processed"
        assert "output_error" in result


if __name__ == "__main__":
    unittest.main()
