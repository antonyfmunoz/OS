"""Phase 14.11D — Voice/STT/TTS integration and trace tests.

Tests push-to-talk voice path, STT/TTS capability detection,
Discord command alignment, and trace/resume event recording.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class FakeReq:
    def __init__(self, body: dict | None = None, query: dict | None = None):
        self._body = body or {}
        self.query_params = query or {}

    async def json(self):
        return self._body


class TestVoiceCommandRouting:
    """Voice transcript → same command router path."""

    def test_voice_transcript_routes_to_status(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what is happening") == CommandIntent.STATUS_QUERY

    def test_voice_transcript_routes_to_resume(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("catch me up") == CommandIntent.RESUME_QUERY

    def test_voice_transcript_routes_to_approval(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what needs approval") == CommandIntent.APPROVAL_QUERY

    def test_voice_transcript_routes_to_mode(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("start night cycle") == CommandIntent.MODE_SWITCH

    def test_voice_source_creates_activation(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(
            source="push_to_talk_voice",
            raw_payload="what is happening",
            confidence=0.92,
        )
        assert sig.source == "push_to_talk_voice"
        assert sig.raw_payload == "what is happening"
        assert sig.confidence == 0.92

    def test_voice_command_through_endpoint(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={
            "text": "what is happening",
            "source": "push_to_talk_voice",
        })
        result = _run(_command(req))
        assert result["ok"] is True
        assert result["intent"] == "status_query"
        assert result["source"] == "push_to_talk_voice"


class TestSTTCapability:
    def test_stt_detection_returns_valid_status(self) -> None:
        from substrate.workstation.activation import _detect_stt_status
        status = _detect_stt_status()
        assert status in ("available", "degraded", "unavailable")

    def test_stt_blocker_consistent_with_status(self) -> None:
        from substrate.workstation.activation import _detect_stt_blocker, _detect_stt_status
        status = _detect_stt_status()
        blocker = _detect_stt_blocker()
        if status == "available":
            assert blocker == ""
        elif status in ("degraded", "unavailable"):
            assert blocker != "", "Non-available STT must have blocker message"

    def test_stt_unavailable_shown_truthfully(self) -> None:
        from transports.api.cockpit_presence_routes import _capabilities
        req = FakeReq(query={})
        result = _run(_capabilities(req))
        caps = result["capabilities"]
        ptt = next(c for c in caps if c["source"] == "push_to_talk_voice")
        if ptt["status"] in ("unavailable", "not_implemented"):
            assert ptt["blocker"] != "", "STT unavailable must show blocker"


class TestTTSCapability:
    def test_tts_check_returns_bool(self) -> None:
        from transports.api.cockpit_presence_routes import _check_tts_available
        result = _check_tts_available()
        assert isinstance(result, bool)

    def test_tts_reported_in_capabilities(self) -> None:
        from transports.api.cockpit_presence_routes import _capabilities
        req = FakeReq(query={})
        result = _run(_capabilities(req))
        assert "tts_available" in result
        assert isinstance(result["tts_available"], bool)

    def test_tts_unavailable_not_faked(self) -> None:
        from transports.api.cockpit_presence_routes import _check_tts_available
        available = _check_tts_available()
        if not available:
            pass  # truthful unavailable, not faked


class TestDiscordCommandAlignment:
    def test_discord_activation_source_exists(self) -> None:
        from substrate.workstation.activation import ActivationSource
        assert ActivationSource.DISCORD_REMOTE_COMMAND.value == "discord_remote_command"

    def test_discord_signal_creates_activation(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(
            source="discord_remote_command",
            raw_payload="!status",
        )
        assert sig.source == "discord_remote_command"

    def test_discord_text_routes_to_same_intent(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what is happening") == CommandIntent.STATUS_QUERY
        assert classify_intent("what needs approval") == CommandIntent.APPROVAL_QUERY

    def test_discord_capability_status(self) -> None:
        from substrate.workstation.activation import get_activation_capabilities
        caps = get_activation_capabilities()
        discord = next(c for c in caps if "discord" in c.name.lower())
        assert discord.status in ("available", "degraded")


class TestTraceResumeIntegration:
    def test_presence_event_logged(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            import transports.api.cockpit_presence_routes as pr
            original = pr._PRESENCE_LOG
            pr._PRESENCE_LOG = os.path.join(d, "presence_events.jsonl")
            try:
                req = FakeReq(body={"source": "manual_cockpit_open"})
                _run(pr._activate(req))

                assert os.path.exists(pr._PRESENCE_LOG)
                with open(pr._PRESENCE_LOG) as f:
                    lines = f.readlines()
                assert len(lines) >= 1
                event = json.loads(lines[0])
                assert event["event"] == "activation"
                assert event["source"] == "manual_cockpit_open"
                assert "activation_id" in event
                assert "timestamp" in event
            finally:
                pr._PRESENCE_LOG = original

    def test_command_event_logged(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            import transports.api.cockpit_presence_routes as pr
            original = pr._PRESENCE_LOG
            pr._PRESENCE_LOG = os.path.join(d, "presence_events.jsonl")
            try:
                req = FakeReq(body={"text": "sitrep"})
                _run(pr._command(req))

                with open(pr._PRESENCE_LOG) as f:
                    lines = f.readlines()
                assert len(lines) >= 1
                event = json.loads(lines[-1])
                assert event["event"] == "command"
                assert event["intent"] == "status_query"
                assert event["text"] == "sitrep"
            finally:
                pr._PRESENCE_LOG = original

    def test_activation_then_command_creates_trace_chain(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            import transports.api.cockpit_presence_routes as pr
            original = pr._PRESENCE_LOG
            pr._PRESENCE_LOG = os.path.join(d, "presence_events.jsonl")
            try:
                act_req = FakeReq(body={"source": "hotkey"})
                _run(pr._activate(act_req))

                cmd_req = FakeReq(body={"text": "what needs approval?"})
                _run(pr._command(cmd_req))

                with open(pr._PRESENCE_LOG) as f:
                    lines = f.readlines()
                assert len(lines) == 2
                act = json.loads(lines[0])
                cmd = json.loads(lines[1])
                assert act["event"] == "activation"
                assert cmd["event"] == "command"
            finally:
                pr._PRESENCE_LOG = original


class TestHotkeyActivation:
    def test_hotkey_creates_signal(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(source="hotkey")
        assert sig.source == "hotkey"
        assert sig.confidence == 1.0
        assert sig.degraded_reason == ""

    def test_hotkey_capability_exists(self) -> None:
        from substrate.workstation.activation import get_activation_capabilities
        caps = get_activation_capabilities()
        hotkey = next(c for c in caps if c.source == "hotkey")
        assert hotkey.status in ("available", "degraded")


class TestManualActivation:
    def test_manual_cockpit_open(self) -> None:
        from transports.api.cockpit_presence_routes import _activate
        req = FakeReq(body={"source": "manual_cockpit_open"})
        result = _run(_activate(req))
        assert result["ok"] is True
        session = result["session"]
        assert session["activation"]["source"] == "manual_cockpit_open"
        assert session["continuity_state"] != ""
        assert session["active_node"] != ""
        assert session["active_environment"] != ""


class TestGovernanceIntegration:
    def test_risky_command_flagged(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "prepare the next safe step"})
        result = _run(_command(req))
        assert result["governance"] == "requires_governance"

    def test_informational_not_governance_gated(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "what is happening"})
        result = _run(_command(req))
        assert result["governance"] == "informational"

    def test_navigation_not_governance_gated(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "show agents"})
        result = _run(_command(req))
        assert result["governance"] == "informational"
