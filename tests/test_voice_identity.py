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


class TestOrganismResponseEnvelope:
    """Phase 14.13V: OrganismResponseEnvelope type and presentation status."""

    def _repo_root(self) -> str:
        import os
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_organism_response_envelope_type(self):
        """voiceStore must export OrganismResponseEnvelope."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/stores/voiceStore.ts")
        with open(path) as f:
            content = f.read()
        assert "OrganismResponseEnvelope" in content
        assert "messageId" in content
        assert "spokenText" in content
        assert "ttsReady" in content
        assert "ttsError" in content

    def test_presentation_status_type(self):
        """voiceStore must export PresentationStatus with all states."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/stores/voiceStore.ts")
        with open(path) as f:
            content = f.read()
        assert "PresentationStatus" in content
        for state in [
            "thinking", "preparing_response", "preparing_voice",
            "ready_to_commit", "committing", "presenting", "complete",
        ]:
            assert state in content, f"Missing PresentationStatus: {state}"

    def test_voice_store_has_presentation_fields(self):
        """voiceStore must have voicePresentationStatus, activeTtsJobId, heldEnvelope."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/stores/voiceStore.ts")
        with open(path) as f:
            content = f.read()
        assert "voicePresentationStatus" in content
        assert "activeTtsJobId" in content
        assert "heldEnvelope" in content

    def test_spoken_text_used_for_tts(self):
        """voice-controller.ts must use spoken_text (not full text) for TTS."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/api/voice-controller.ts")
        with open(path) as f:
            content = f.read()
        assert "spoken_text" in content
        assert "requestTts" in content

    def test_metadata_visible_not_spoken(self):
        """AdvisorResponse.spoken_text excludes metadata."""
        from substrate.organism.advisor_conversation import AdvisorConversation

        class MockAdvisor:
            def handle_signal(self, content: str):
                return {"output": f"mock: {content}"}
            def convene_council(self, **kwargs):
                return {}

        conv = AdvisorConversation(advisor=MockAdvisor())

        text = "**Status**: operational\n```json\n{}\n```\nAll systems green."
        spoken = conv._build_spoken_text(text)
        assert "```" not in spoken
        assert "**" not in spoken

    def test_routing_preserved_in_response(self):
        """Routing metadata still flows through voice responses."""
        from substrate.organism.advisor_conversation import AdvisorResponse
        r = AdvisorResponse(
            text="Hello",
            conversation_id="c1",
            intent="chat",
            routing={"execution_target": "vps", "audio_output_session": "sess-123"},
        )
        d = r.to_api_dict()
        assert d["routing"]["execution_target"] == "vps"
        assert d["routing"]["audio_output_session"] == "sess-123"


class TestTtsPlaybackController:
    """Phase 14.13V: TTS playback controller exists."""

    def _repo_root(self) -> str:
        import os
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_tts_playback_controller_exists(self):
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/api/tts-playback-controller.ts")
        assert os.path.exists(path)

    def test_has_unlock_function(self):
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/api/tts-playback-controller.ts")
        with open(path) as f:
            content = f.read()
        assert "unlockAudioForIOS" in content
        assert "audioUnlocked" in content

    def test_has_play_function(self):
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/api/tts-playback-controller.ts")
        with open(path) as f:
            content = f.read()
        assert "playTtsAudio" in content

    def test_has_tts_playback_logs(self):
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/api/tts-playback-controller.ts")
        with open(path) as f:
            content = f.read()
        assert "[TTSPlayback]" in content

    def test_controller_uses_tts_playback(self):
        """voice-controller.ts imports tts-playback-controller."""
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/api/voice-controller.ts")
        with open(path) as f:
            content = f.read()
        assert "tts-playback-controller" in content
        assert "unlockAudioForIOS" in content
