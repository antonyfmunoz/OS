"""Tests for VoiceRuntime — continuous conversational voice loop."""

from __future__ import annotations

import sys
import threading
import time
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/opt/OS")

import pytest

from eos_ai.platforms.eos.voice_runtime import (
    STTProvider,
    VoiceLoopState,
    VoiceRuntime,
    VoiceRuntimeState,
    WakeMode,
    get_voice_runtime,
    get_voice_runtime_state,
)


@pytest.fixture(autouse=True)
def _reset_runtime():
    """Reset singletons before and after each test."""
    VoiceRuntime.reset_default_for_tests()
    # Also reset streaming bridge to avoid TTS calls
    try:
        from eos_ai.platforms.eos.streaming_bridge import StreamingBridge

        StreamingBridge.reset_default_for_tests()
    except Exception:
        pass
    yield
    VoiceRuntime.reset_default_for_tests()
    try:
        from eos_ai.platforms.eos.streaming_bridge import StreamingBridge

        StreamingBridge.reset_default_for_tests()
    except Exception:
        pass


# ─── Singleton ──────────────────────────────────────────────────────────────


def test_singleton_returns_same_instance():
    a = VoiceRuntime.default()
    b = VoiceRuntime.default()
    assert a is b


def test_reset_creates_new_instance():
    a = VoiceRuntime.default()
    VoiceRuntime.reset_default_for_tests()
    b = VoiceRuntime.default()
    assert a is not b


# ─── State Dataclass ────────────────────────────────────────────────────────


def test_state_defaults():
    state = VoiceRuntimeState()
    assert state.is_listening is False
    assert state.is_speaking is False
    assert state.wake_mode == WakeMode.ALWAYS_ON
    assert state.loop_state == VoiceLoopState.IDLE
    assert state.cycle_count == 0


def test_state_serialization():
    state = VoiceRuntimeState(
        is_listening=True,
        last_utterance="hello",
        wake_mode=WakeMode.WAKE_WORD,
        loop_state=VoiceLoopState.LISTENING,
        cycle_count=5,
    )
    d = state.to_dict()
    assert d["is_listening"] is True
    assert d["last_utterance"] == "hello"
    assert d["wake_mode"] == "wake_word"
    assert d["loop_state"] == "listening"
    assert d["cycle_count"] == 5


# ─── Configuration ──────────────────────────────────────────────────────────


def test_configure():
    rt = get_voice_runtime()
    rt.configure(
        wake_mode=WakeMode.WAKE_WORD,
        wake_phrase="hey assistant",
        silence_timeout_s=2.0,
        stt_provider=STTProvider.SIMULATED,
    )
    assert rt._wake_mode == WakeMode.WAKE_WORD
    assert rt._wake_phrase == "hey assistant"
    assert rt._silence_timeout_s == 2.0
    assert rt._stt_provider == STTProvider.SIMULATED
    assert rt.state.wake_mode == WakeMode.WAKE_WORD


# ─── Lifecycle ──────────────────────────────────────────────────────────────


def test_start_stop():
    """Test that start/stop transitions work without actual audio."""
    rt = get_voice_runtime()
    rt.configure(stt_provider=STTProvider.SIMULATED)

    # Mock audio capture to return None (no mic)
    with patch(
        "eos_ai.platforms.eos.voice_runtime._capture_audio_chunk", return_value=None
    ):
        rt.start()
        assert rt.is_running
        time.sleep(0.2)  # Let the loop iterate once
        rt.stop()
        assert not rt.is_running
        assert rt.state.loop_state == VoiceLoopState.STOPPED


def test_double_start():
    rt = get_voice_runtime()
    with patch(
        "eos_ai.platforms.eos.voice_runtime._capture_audio_chunk", return_value=None
    ):
        rt.start()
        rt.start()  # Should not crash
        assert rt.is_running
        rt.stop()


def test_stop_without_start():
    rt = get_voice_runtime()
    rt.stop()  # Should not crash


# ─── Interruption ───────────────────────────────────────────────────────────


def test_interrupt_sets_flag():
    rt = get_voice_runtime()
    rt._state.is_speaking = True

    with patch(
        "eos_ai.platforms.eos.streaming_bridge.StreamingBridge.default"
    ) as mock_bridge:
        mock_bridge.return_value = MagicMock()
        rt.interrupt()

    assert rt.state.interrupted is True


def test_interrupt_with_text_processes_utterance():
    rt = get_voice_runtime()
    callback_received: list[str] = []
    rt.on_response(callback_received.append)

    # Mock live_runtime to return a result
    mock_result = MagicMock()
    mock_result.spoken_text = "Got it."

    with patch(
        "eos_ai.platforms.eos.live_runtime.handle_live_user_utterance",
        return_value=mock_result,
    ):
        with patch("eos_ai.platforms.eos.streaming_bridge.stream_event"):
            rt.interrupt("do something else")

    assert rt.state.last_response == "Got it."


# ─── Module-Level API ───────────────────────────────────────────────────────


def test_get_voice_runtime_state():
    state = get_voice_runtime_state()
    assert isinstance(state, dict)
    assert "is_listening" in state
    assert "wake_mode" in state
    assert "loop_state" in state


# ─── Callbacks ──────────────────────────────────────────────────────────────


def test_on_utterance_callback():
    rt = get_voice_runtime()
    received: list[str] = []
    rt.on_utterance(received.append)

    # Simulate processing
    mock_result = MagicMock()
    mock_result.spoken_text = "response"

    with patch(
        "eos_ai.platforms.eos.live_runtime.handle_live_user_utterance",
        return_value=mock_result,
    ):
        with patch("eos_ai.platforms.eos.streaming_bridge.stream_event"):
            # Directly call _process_utterance
            rt._state.last_utterance = "test input"
            if rt._on_utterance:
                rt._on_utterance("test input")

    assert received == ["test input"]


def test_on_response_callback():
    rt = get_voice_runtime()
    received: list[str] = []
    rt.on_response(received.append)

    mock_result = MagicMock()
    mock_result.spoken_text = "I'll do that."

    with patch(
        "eos_ai.platforms.eos.live_runtime.handle_live_user_utterance",
        return_value=mock_result,
    ):
        with patch("eos_ai.platforms.eos.streaming_bridge.stream_event"):
            rt._process_utterance("hello")

    assert received == ["I'll do that."]


# ─── Wake Modes ─────────────────────────────────────────────────────────────


def test_push_to_talk_stays_waiting():
    """In push-to-talk mode, single_cycle should just wait and return."""
    rt = get_voice_runtime()
    rt.configure(wake_mode=WakeMode.PUSH_TO_TALK)
    rt._stop_event = threading.Event()

    # Should return quickly without blocking
    rt._stop_event.set()  # Immediately trigger stop
    rt._single_cycle()
    assert rt.state.loop_state == VoiceLoopState.WAITING_FOR_WAKE


# ─── Enums ──────────────────────────────────────────────────────────────────


def test_wake_mode_values():
    assert WakeMode.ALWAYS_ON.value == "always_on"
    assert WakeMode.WAKE_WORD.value == "wake_word"
    assert WakeMode.PUSH_TO_TALK.value == "push_to_talk"


def test_voice_loop_state_values():
    assert VoiceLoopState.IDLE.value == "idle"
    assert VoiceLoopState.LISTENING.value == "listening"
    assert VoiceLoopState.TRANSCRIBING.value == "transcribing"
    assert VoiceLoopState.PROCESSING.value == "processing"
    assert VoiceLoopState.SPEAKING.value == "speaking"
    assert VoiceLoopState.WAITING_FOR_WAKE.value == "waiting_for_wake"
    assert VoiceLoopState.STOPPED.value == "stopped"


def test_stt_provider_values():
    assert STTProvider.FASTER_WHISPER.value == "faster_whisper"
    assert STTProvider.OPENAI.value == "openai"
    assert STTProvider.SIMULATED.value == "simulated"
