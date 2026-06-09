"""Phase 14.13T-4: Voice identity grounding + prosody regression tests.

Tests that UMH identity is always correct, deterministic handler fires,
and voice prosody normalization works.
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS")

import pytest


class TestIdentityCorrectName:
    """Workcell A/B: Canonical identity is always 'Universal Meta Harness'."""

    def test_umh_full_name_canonical(self):
        from substrate.self_model import CANONICAL
        assert CANONICAL.system_full_name == "Universal Meta Harness"
        assert CANONICAL.system_name == "UMH"

    def test_system_identity_module(self):
        from substrate.organism.system_identity import UMH_ACRONYM, UMH_FULL_NAME
        assert UMH_ACRONYM == "UMH"
        assert UMH_FULL_NAME == "Universal Meta Harness"

    def test_identity_no_wrong_expansion(self):
        from substrate.organism.system_identity import UMH_FULL_NAME
        assert "Mastery" not in UMH_FULL_NAME
        assert "Hierarchy" not in UMH_FULL_NAME

    def test_get_system_identity_context(self):
        from substrate.organism.system_identity import get_system_identity_context
        ctx = get_system_identity_context()
        assert ctx["umh_full_name"] == "Universal Meta Harness"
        assert ctx["umh_acronym"] == "UMH"
        assert "ai_instance_name" in ctx


class TestDeterministicIdentityHandler:
    """Workcell B: Identity questions route deterministic, not LLM."""

    def test_what_is_umh(self):
        from substrate.organism.system_identity import is_identity_question, get_identity_answer
        assert is_identity_question("what is UMH?")
        answer = get_identity_answer("what is UMH?")
        assert answer is not None
        assert "Universal Meta Harness" in answer
        assert "Mastery" not in answer
        assert "Hierarchy" not in answer

    def test_what_does_umh_stand_for(self):
        from substrate.organism.system_identity import get_identity_answer
        answer = get_identity_answer("what does UMH stand for?")
        assert answer is not None
        assert "Universal Meta Harness" in answer

    def test_what_are_you(self):
        from substrate.organism.system_identity import is_identity_question, get_identity_answer
        assert is_identity_question("what are you?")
        answer = get_identity_answer("what are you?")
        assert answer is not None
        assert "Universal Meta Harness" in answer

    def test_what_is_ai_name(self):
        import os
        os.environ["UMH_AI_NAME"] = "DEX"
        try:
            from importlib import reload
            import substrate.organism.system_identity as sid
            reload(sid)
            assert sid.is_identity_question("what is DEX?")
            answer = sid.get_identity_answer("what is DEX?")
            assert answer is not None
            assert "advisor" in answer.lower()
        finally:
            os.environ.pop("UMH_AI_NAME", None)

    def test_voice_mode_shorter(self):
        from substrate.organism.system_identity import get_identity_answer
        text_answer = get_identity_answer("what is UMH?", voice=False)
        voice_answer = get_identity_answer("what is UMH?", voice=True)
        assert text_answer is not None
        assert voice_answer is not None
        assert len(voice_answer) <= len(text_answer) + 50

    def test_non_identity_returns_none(self):
        from substrate.organism.system_identity import get_identity_answer
        assert get_identity_answer("what is the weather?") is None
        assert get_identity_answer("open spotify") is None
        assert get_identity_answer("create a work packet") is None

    @pytest.mark.parametrize("question", [
        "what is UMH",
        "what does UMH stand for",
        "what are you",
        "who are you",
        "what is this system",
    ])
    def test_identity_questions_recognized(self, question):
        from substrate.organism.system_identity import is_identity_question
        assert is_identity_question(question), f"Not recognized: {question}"

    def test_identity_recognizes_dynamic_ai_name(self):
        import os
        os.environ["UMH_AI_NAME"] = "DEX"
        try:
            from importlib import reload
            import substrate.organism.system_identity as sid
            reload(sid)
            assert sid.is_identity_question("what is DEX")
        finally:
            os.environ.pop("UMH_AI_NAME", None)


class TestPromptGrounding:
    """Workcell C: Prompt grounding prevents LLM hallucination."""

    def test_grounding_contains_correct_name(self):
        from substrate.organism.system_identity import get_prompt_grounding
        grounding = get_prompt_grounding("DEX")
        assert "Universal Meta Harness" in grounding
        assert "NEVER expand as anything else" in grounding
        assert "DEX" in grounding

    def test_advisor_conversation_prompt_correct(self):
        """The system prompt in AdvisorConversation must say Universal Meta Harness."""
        import inspect
        from substrate.organism.advisor_conversation import AdvisorConversation
        source = inspect.getsource(AdvisorConversation._handle_conversation)
        assert "Universal Meta Harness" in source
        assert "Universal Mastery Hierarchy" not in source


class TestVoiceProsody:
    """Workcell H: Voice normalization for natural speech."""

    def test_normalize_acronyms(self):
        from substrate.execution.bridge.voice_first import normalize_for_speech
        result = normalize_for_speech("UMH stands for Universal Meta Harness")
        assert "Universal Meta Harness" in result

    def test_normalize_ai_name_capitalization(self):
        import os
        os.environ["UMH_AI_NAME"] = "DEX"
        try:
            from importlib import reload
            import substrate.organism.system_identity
            reload(substrate.organism.system_identity)
            from substrate.execution.bridge.voice_first import normalize_for_speech
            result = normalize_for_speech("DEX is online")
            assert "Dex" in result
        finally:
            os.environ.pop("UMH_AI_NAME", None)

    def test_strip_metadata_lines(self):
        from substrate.execution.bridge.voice_first import normalize_for_speech
        text = "target_node: beast_windows\nstatus: executed\nSpotify is open."
        result = normalize_for_speech(text)
        assert "target_node" not in result
        assert "Spotify" in result

    def test_prepare_voice_response_strips_markdown(self):
        from substrate.execution.bridge.voice_first import prepare_voice_response
        text = "**Status Report**\n\n- Item one\n- Item two\n```code```"
        result = prepare_voice_response(text)
        assert "**" not in result
        assert "```" not in result

    def test_spoken_summary_no_metadata(self):
        from substrate.execution.bridge.voice_first import prepare_voice_response
        text = '{"target_node": "beast_windows", "status": "executed"}\nSpotify is open on Beast.'
        result = prepare_voice_response(text)
        assert "target_node" not in result


class TestVoiceSourceSync:
    """Workcell D/E: Voice-originated responses use synchronized contract."""

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

    def test_voice_controller_has_generating_state(self):
        import os
        path = os.path.join(self._repo_root(), "cockpit/src/renderer/api/voice-controller.ts")
        with open(path) as f:
            content = f.read()
        assert "generating_tts" in content
        assert "tts_failed" in content
        assert "releaseHeldMessage" in content
