"""Phase 14.13U: Voice identity and source sync tests.

Tests voice-related modules that exist in this worktree.
Checks that the AdvisorResponse spoken contract and voice route
HUD files are present and correct.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest


class TestSelfModelCanonical:
    """self_model canonical object is importable."""

    def test_self_model_importable(self):
        from substrate.self_model import CANONICAL
        assert CANONICAL is not None
        assert hasattr(CANONICAL, "system_full_name")
        assert hasattr(CANONICAL, "system_name")

    def test_system_name_is_umh(self):
        from substrate.self_model import CANONICAL
        assert CANONICAL.system_name == "UMH"


class TestVoiceFirstBridge:
    """substrate.execution.bridge.voice_first — prepare_voice_response works."""

    def test_prepare_voice_response_importable(self):
        from substrate.execution.bridge.voice_first import prepare_voice_response
        assert callable(prepare_voice_response)

    def test_prepare_voice_response_strips_markdown(self):
        from substrate.execution.bridge.voice_first import prepare_voice_response
        text = "**Status Report**\n\n- Item one\n- Item two\n```code```"
        result = prepare_voice_response(text)
        assert "**" not in result
        assert "```" not in result

    def test_prepare_voice_response_truncates(self):
        from substrate.execution.bridge.voice_first import prepare_voice_response
        long_text = "Hello. " * 300
        result = prepare_voice_response(long_text)
        # Must be shorter than input
        assert len(result) < len(long_text)

    def test_spoken_summary_no_metadata(self):
        from substrate.execution.bridge.voice_first import prepare_voice_response
        text = '{"target_node": "beast_windows", "status": "executed"}\nSpotify is open on Beast.'
        result = prepare_voice_response(text)
        assert "target_node" not in result


class TestAdvisorResponseContract:
    """AdvisorResponse must expose display_text, spoken_text, routing."""

    def test_display_text_alias(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        r = AdvisorResponse(text="Hello", conversation_id="c1", intent="chat")
        assert r.display_text == "Hello"
        assert r.display_text == r.text

    def test_spoken_text_defaults_empty(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        r = AdvisorResponse(text="Hello", conversation_id="c1", intent="chat")
        assert r.spoken_text == ""

    def test_routing_defaults_empty(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        r = AdvisorResponse(text="Hello", conversation_id="c1", intent="chat")
        assert r.routing == {}

    def test_to_api_dict_omits_empty_spoken(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        r = AdvisorResponse(text="Hello", conversation_id="c1", intent="chat")
        d = r.to_api_dict()
        assert "spoken_text" not in d

    def test_to_api_dict_includes_spoken_when_set(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        r = AdvisorResponse(
            text="Long text with **markdown**",
            conversation_id="c1",
            intent="chat",
            spoken_text="Long text",
        )
        d = r.to_api_dict()
        assert d["spoken_text"] == "Long text"

    def test_to_api_dict_omits_empty_routing(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        r = AdvisorResponse(text="Hello", conversation_id="c1", intent="chat")
        d = r.to_api_dict()
        assert "routing" not in d

    def test_to_api_dict_includes_routing_when_set(self):
        from substrate.organism.advisor_conversation import AdvisorResponse
        r = AdvisorResponse(
            text="Hello",
            conversation_id="c1",
            intent="chat",
            routing={"execution_target": "beast_windows"},
        )
        d = r.to_api_dict()
        assert d["routing"]["execution_target"] == "beast_windows"


class TestVoiceSourceSync:
    """Frontend files must exist with required contents for voice sync."""

    def _repo_root(self) -> str:
        import os
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_voice_store_tts_states(self):
        """TtsState type includes all required states."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/stores/voiceStore.ts")
        with open(path) as f:
            content = f.read()
        assert "generating_tts" in content
        assert "tts_failed" in content
        assert "speaking" in content

    def test_voice_controller_uses_spoken_text(self):
        """voice-controller.ts must prefer spoken_text for TTS."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/api/voice-controller.ts")
        with open(path) as f:
            content = f.read()
        assert "spoken_text" in content

    def test_device_session_store_exists(self):
        """deviceSessionStore.ts must exist with required exports."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/stores/deviceSessionStore.ts")
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "useDeviceSessionStore" in content
        assert "getRoutingMetadata" in content

    def test_voice_route_hud_exists(self):
        """VoiceRouteHud.tsx must exist."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/components/VoiceRouteHud.tsx")
        assert os.path.exists(path)

    def test_device_presence_api_exists(self):
        """device-presence.ts must exist with required exports."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/api/device-presence.ts")
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "registerDevice" in content
        assert "heartbeatDevice" in content
        assert "disconnectDevice" in content
