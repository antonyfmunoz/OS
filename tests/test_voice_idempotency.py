"""Phase 14.13V: Voice turn idempotency tests.

Tests the backend voice_turn_id cache in AdvisorConversation.
Uses monkeypatching to avoid actual LLM calls.
"""

from __future__ import annotations

import sys
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/opt/OS")

import pytest


def _mock_call_with_fallback(prompt, **kwargs):
    """Mock that returns a RoutingResult-like object."""
    mock_result = MagicMock()
    mock_result.output = f"Mock response to: {prompt[:50]}"
    mock_result.content = mock_result.output
    mock_result.provider = "mock"
    mock_result.model = "mock-1"
    mock_result.metadata = {}
    return mock_result


class TestVoiceTurnIdempotency:
    """Same voice_turn_id returns cached response, different ID creates new."""

    def _make_conversation(self):
        """Create an AdvisorConversation with a mock advisor."""
        from substrate.organism.advisor_conversation import AdvisorConversation

        class MockAdvisor:
            def handle_signal(self, content: str):
                return {"output": f"mock: {content}"}

            def convene_council(self, **kwargs):
                return {}

        return AdvisorConversation(advisor=MockAdvisor())

    @patch("adapters.models.model_router.call_with_fallback", side_effect=_mock_call_with_fallback)
    def test_same_turn_id_returns_cached(self, mock_llm):
        conv = self._make_conversation()
        turn_id = "vt-test-001"

        r1 = conv.converse(
            content="hello",
            source="voice",
            voice_turn_id=turn_id,
        )
        r2 = conv.converse(
            content="hello",
            source="voice",
            voice_turn_id=turn_id,
        )

        assert r1.text == r2.text
        assert r1.conversation_id == r2.conversation_id
        # The LLM should only be called once (first call), second returns cached
        assert mock_llm.call_count == 1

    @patch("adapters.models.model_router.call_with_fallback", side_effect=_mock_call_with_fallback)
    def test_different_turn_id_creates_new(self, mock_llm):
        conv = self._make_conversation()

        r1 = conv.converse(
            content="hello",
            source="voice",
            voice_turn_id="vt-test-002",
        )
        r2 = conv.converse(
            content="world",
            source="voice",
            voice_turn_id="vt-test-003",
        )

        # Different turn IDs create separate responses
        assert mock_llm.call_count == 2

    @patch("adapters.models.model_router.call_with_fallback", side_effect=_mock_call_with_fallback)
    def test_no_turn_id_skips_cache(self, mock_llm):
        conv = self._make_conversation()

        r1 = conv.converse(
            content="hello",
            source="voice",
            voice_turn_id="",
        )
        r2 = conv.converse(
            content="hello",
            source="voice",
            voice_turn_id="",
        )

        # Without turn ID, no caching — both hit LLM
        assert r1.text is not None
        assert r2.text is not None
        assert mock_llm.call_count == 2

    def test_text_chat_path_unchanged(self):
        """Text-only chat (no voice_turn_id) works — uses identity handler to avoid LLM."""
        conv = self._make_conversation()

        # Use an identity question that the deterministic handler catches
        r = conv.converse(
            content="what is your name",
            source="text",
        )
        assert r.text is not None
        assert len(r.text) > 0

    @patch("adapters.models.model_router.call_with_fallback", side_effect=_mock_call_with_fallback)
    def test_cache_expiry(self, mock_llm):
        conv = self._make_conversation()
        turn_id = "vt-test-expire"

        r1 = conv.converse(
            content="hello",
            source="voice",
            voice_turn_id=turn_id,
        )

        # Manually expire the cache entry
        if turn_id in conv._voice_turn_cache:
            resp, _ = conv._voice_turn_cache[turn_id]
            conv._voice_turn_cache[turn_id] = (resp, time.time() - 700)

        r2 = conv.converse(
            content="hello",
            source="voice",
            voice_turn_id=turn_id,
        )

        # After expiry, a new response is generated (LLM called twice)
        assert r2.text is not None
        assert mock_llm.call_count == 2

    def test_converse_accepts_voice_turn_id_parameter(self):
        """Verify the converse() signature includes voice_turn_id."""
        from substrate.organism.advisor_conversation import AdvisorConversation
        import inspect
        sig = inspect.signature(AdvisorConversation.converse)
        assert "voice_turn_id" in sig.parameters

    def test_cockpit_passes_voice_turn_id(self):
        """cockpit.py endpoint passes voice_turn_id to converse()."""
        import os
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(repo, "transports/api/cockpit.py")
        with open(path) as f:
            content = f.read()
        assert 'voice_turn_id' in content

    @patch("adapters.models.model_router.call_with_fallback", side_effect=_mock_call_with_fallback)
    def test_one_turn_one_response(self, mock_llm):
        """Sending same voice_turn_id 3 times produces exactly one LLM call."""
        conv = self._make_conversation()
        turn_id = "vt-test-one-turn"

        responses = []
        for _ in range(3):
            r = conv.converse(
                content="test message",
                source="voice",
                voice_turn_id=turn_id,
            )
            responses.append(r.text)

        # All responses identical
        assert responses[0] == responses[1] == responses[2]
        # Only one actual LLM call
        assert mock_llm.call_count == 1
