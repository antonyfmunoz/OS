"""Tests for substrate/workstation/voice_route_resolver.py.

Covers: target node parsing, audio override parsing, route resolution
by source session type, and display/spoken text separation.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.device_presence import DevicePresenceRegistry, DeviceSession
from substrate.workstation.voice_route_resolver import (
    VoiceRoute,
    parse_audio_override,
    parse_target_node,
    resolve_voice_route,
)


# ── parse_target_node ─────────────────────────────────────────────────────────

class TestTargetNodeParsing:
    @pytest.mark.parametrize("transcript,expected", [
        ("open spotify on the workstation", "beast_windows"),
        ("open spotify on beast", "beast_windows"),
        ("open spotify on beast pc", "beast_windows"),
        ("run this on the windows desktop", "beast_windows"),
        ("show docker containers on vps", "vps"),
        ("check the server status", "vps"),
        ("show docker ps", "vps"),
        ("what time is it", ""),
        ("start a work packet", ""),
        ("list my tasks", ""),
    ])
    def test_target_node_parsing(self, transcript: str, expected: str):
        result = parse_target_node(transcript)
        assert result == expected, f"transcript={transcript!r} expected={expected!r} got={result!r}"

    def test_vps_docker_containers(self):
        assert parse_target_node("show docker containers") == "vps"

    def test_beast_explicit(self):
        assert parse_target_node("on workstation please") == "beast_windows"

    def test_no_target_conversation(self):
        assert parse_target_node("what should I do today?") == ""


# ── parse_audio_override ──────────────────────────────────────────────────────

class TestAudioOverrideParsing:
    @pytest.mark.parametrize("transcript,expected", [
        ("speak from the workstation", "beast_windows"),
        ("speak on beast", "beast_windows"),
        ("play audio on the workstation", "beast_windows"),
        ("say it on beast", "beast_windows"),
        ("speak from my phone", "source_device"),
        ("talk to me on my phone", "source_device"),
        ("say it on my mobile", "source_device"),
        ("speak back here", "source_device"),
        ("talk back here", "source_device"),
        ("open spotify", ""),
        ("just run it", ""),
    ])
    def test_audio_override_parsing(self, transcript: str, expected: str):
        result = parse_audio_override(transcript)
        assert result == expected, f"transcript={transcript!r} expected={expected!r} got={result!r}"


# ── resolve_voice_route ───────────────────────────────────────────────────────

def _make_registry_with_session(
    session_id: str,
    device_id: str = "iphone-15-pro-max",
    can_play_audio: bool = True,
    control_surface: str = "fly_cockpit",
    client_type: str = "mobile_browser",
) -> DevicePresenceRegistry:
    reg = DevicePresenceRegistry()
    s = DeviceSession(
        device_id=device_id,
        session_id=session_id,
        client_type=client_type,
        control_surface=control_surface,
        can_play_audio=can_play_audio,
    )
    reg.register_session(s)
    return reg


class TestResolveVoiceRoute:
    def _resolve(self, transcript: str, session_id: str, can_play_audio: bool = True,
                 control_surface: str = "fly_cockpit", device_id: str = "iphone-15-pro-max",
                 requested_target: str | None = None) -> VoiceRoute:
        """Helper: patch the registry singleton then resolve."""
        import substrate.workstation.device_presence as dp_mod
        reg = _make_registry_with_session(
            session_id, device_id=device_id,
            can_play_audio=can_play_audio, control_surface=control_surface,
        )
        original = dp_mod._registry
        dp_mod._registry = reg
        try:
            return resolve_voice_route(transcript, session_id, requested_target_node=requested_target)
        finally:
            dp_mod._registry = original

    def test_phone_to_beast_audio_returns_phone(self):
        """'open spotify on workstation' from phone — execution on beast, audio stays on phone."""
        route = self._resolve("open spotify on the workstation", "phone-sess")
        assert route.execution_target == "beast_windows"
        assert route.handoff_mode == "remote_control"
        assert route.audio_output_device != "beast_windows"

    def test_workstation_audio_returns_source(self):
        """From a beast session, audio stays on beast."""
        route = self._resolve(
            "open spotify", "beast-sess",
            device_id="desktop-lvguiq9", control_surface="electron_cockpit",
        )
        assert route.audio_output_session == "beast-sess"

    def test_vps_audio_returns_source(self):
        """'show docker containers' from phone — execution on VPS, audio stays on phone."""
        route = self._resolve("show docker containers", "phone-sess-2")
        assert route.execution_target == "vps"
        assert route.handoff_mode == "remote_control"
        assert route.audio_output_device != "vps"

    def test_override_speak_from_workstation(self):
        """'speak from the workstation' explicitly reroutes audio to beast."""
        route = self._resolve("speak from the workstation", "phone-sess-3")
        assert route.audio_output_device == "beast_windows"

    def test_text_only_no_audio(self):
        """Terminal sessions get text_only audio path."""
        route = self._resolve(
            "status", "term-sess",
            can_play_audio=False, control_surface="terminal",
        )
        assert route.audio_output_device == "text_only"
        assert route.audio_output_session == ""

    def test_conversation_default(self):
        """No target node keyword → cockpit, conversation mode."""
        route = self._resolve("what should I do today?", "browser-sess")
        assert route.execution_target == "cockpit"
        assert route.handoff_mode == "conversation"

    def test_requested_target_overrides_detection(self):
        """Explicit requested_target_node takes precedence over transcript parsing."""
        route = self._resolve("just run it", "sess-x", requested_target="beast_windows")
        assert route.execution_target == "beast_windows"
        assert route.handoff_mode == "remote_control"

    def test_unknown_session_still_returns_route(self):
        """Unknown session_id: route degrades gracefully, doesn't crash."""
        import substrate.workstation.device_presence as dp_mod
        original = dp_mod._registry
        dp_mod._registry = DevicePresenceRegistry()  # empty registry
        try:
            route = resolve_voice_route("open notes", "unknown-sess")
        finally:
            dp_mod._registry = original
        assert route is not None
        assert isinstance(route, VoiceRoute)

    def test_governance_unchanged_vps_control_not_bypassed(self):
        """Voice routing does NOT bypass governance — VPS control catalog remains the gate.
        This test verifies that route.execution_target is merely a routing hint;
        the actual VPS command catalog check happens in advisor_conversation._handle_vps_control().
        The route resolver itself is governance-neutral.
        """
        route = self._resolve("restart all docker containers on vps", "sess-gov")
        # Route resolver identifies VPS target — governance check is a separate layer
        assert route.execution_target == "vps"
        # Route resolver never sets requires_approval based on content
        assert route.requires_approval is False


# ── spoken_text contract ──────────────────────────────────────────────────────

class TestSpokenTextContract:
    def test_spoken_text_strips_markdown(self):
        """AdvisorResponse.spoken_text must be markdown-free."""
        from substrate.organism.advisor_conversation import AdvisorConversation

        class FakeAdvisor:
            def handle_signal(self, *a, **kw):
                return {}

        conv = AdvisorConversation(FakeAdvisor())
        spoken = conv._build_spoken_text("**Status Report**\n\n- Item one\n```code block```")
        assert "**" not in spoken
        assert "```" not in spoken

    def test_spoken_text_strips_metadata_lines(self):
        from substrate.organism.advisor_conversation import AdvisorConversation

        class FakeAdvisor:
            def handle_signal(self, *a, **kw):
                return {}

        conv = AdvisorConversation(FakeAdvisor())
        spoken = conv._build_spoken_text("target_node: beast_windows\nSpotify is open.")
        assert "target_node" not in spoken
        assert "Spotify" in spoken

    def test_spoken_text_truncated_to_400(self):
        from substrate.organism.advisor_conversation import AdvisorConversation

        class FakeAdvisor:
            def handle_signal(self, *a, **kw):
                return {}

        conv = AdvisorConversation(FakeAdvisor())
        long_text = "Hello. " * 200
        result = conv._build_spoken_text(long_text)
        assert len(result) <= 400

    def test_advisor_response_display_text_alias(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        resp = AdvisorResponse(text="Hello world", conversation_id="c1", intent="chat")
        assert resp.display_text == "Hello world"
        assert resp.display_text == resp.text

    def test_advisor_response_spoken_text_defaults_empty(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        resp = AdvisorResponse(text="Hello", conversation_id="c1", intent="chat")
        assert resp.spoken_text == ""

    def test_advisor_response_routing_defaults_empty(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        resp = AdvisorResponse(text="Hello", conversation_id="c1", intent="chat")
        assert resp.routing == {}

    def test_to_api_dict_omits_empty_spoken(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        resp = AdvisorResponse(text="Hello", conversation_id="c1", intent="chat")
        d = resp.to_api_dict()
        assert "spoken_text" not in d

    def test_to_api_dict_includes_spoken_when_set(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        resp = AdvisorResponse(
            text="Long markdown **text**",
            conversation_id="c1",
            intent="chat",
            spoken_text="Long text",
        )
        d = resp.to_api_dict()
        assert d["spoken_text"] == "Long text"
