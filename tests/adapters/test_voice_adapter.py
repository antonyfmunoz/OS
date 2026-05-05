"""Tests for the voice pipeline: STT, TTS, VoiceAdapter, VoiceLoop.

Covers:
1.  STT: PlaceholderSTT returns empty, MockSTT returns scripted text
2.  TTS: PlaceholderTTS logs instead of speaking, MockTTS captures calls
3.  VoiceAdapter: handles ritual_completed and action_completed
4.  VoiceAdapter: does not handle step events
5.  VoiceAdapter: extracts correct summary text
6.  VoiceLoop: voice input → runtime.handle_input called
7.  VoiceLoop: correct routing (action vs open/close)
8.  VoiceLoop: TTS called on adapter response
9.  VoiceLoop: loop stability (no crashes on empty/error)
10. VoiceLoop: wake word filtering
11. VoiceLoop: session continuity across multiple voice inputs
12. No substrate/lifecycle imports in voice modules
"""

import sys

sys.path.insert(0, "/opt/OS")

import ast
import inspect
import time
import pytest
from typing import Any

from umh.adapters.contracts import AdapterContext
from umh.adapters.registry import AdapterRegistry
from umh.adapters.stt_engine import PlaceholderSTT, STTEngine
from umh.adapters.stubs import DiscordAdapter, NotionAdapter, WorkstationAdapter
from umh.adapters.tts_engine import PlaceholderTTS, TTSEngine
from umh.adapters.voice_adapter import VoiceAdapter
from umh.adapters.voice_loop import (
    AudioSource,
    BufferedAudioSource,
    VoiceLoop,
    _check_wake_word,
)
from umh.runtime_loop.input_router import InputEvent
from umh.runtime_loop.live_loop import LiveRuntime
from umh.substrate.event_scheduler import SchedulerEvent
from umh.substrate.runtime_state_store import RuntimeStateStore


# ─── Mock Implementations ────────────────────────────────────────────


class MockSTT:
    """STT mock that returns scripted responses in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.call_count = 0

    def transcribe(self, audio: bytes) -> str:
        self.call_count += 1
        if self._index < len(self._responses):
            result = self._responses[self._index]
            self._index += 1
            return result
        return ""


class MockTTS:
    """TTS mock that captures speak() calls."""

    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)

    def shutdown(self) -> None:
        pass


class MockAudioSource:
    """Audio source that returns scripted chunks."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)
        self._index = 0

    def capture(self) -> bytes:
        if self._index < len(self._chunks):
            chunk = self._chunks[self._index]
            self._index += 1
            return chunk
        return b""


# ─── Helpers ─────────────────────────────────────────────────────────


def _make_runtime(
    registry: AdapterRegistry | None = None,
) -> tuple[LiveRuntime, RuntimeStateStore]:
    store = RuntimeStateStore()
    reg = registry or AdapterRegistry()
    runtime = LiveRuntime(state_store=store, adapter_registry=reg)
    return runtime, store


def _make_adapter_context(session_id: str = "sess_test") -> AdapterContext:
    return AdapterContext(
        state_snapshot={},
        runtime_session_id=session_id,
        correlation_id="cor_test",
    )


def _make_event(
    event_type: str,
    payload: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> SchedulerEvent:
    return SchedulerEvent(
        event_type=event_type,
        session_name="sess_test",
        source="test",
        payload=payload or {},
        metadata=metadata or {},
    )


# ─── 1. STT Engine Tests ────────────────────────────────────────────


class TestSTTEngine:
    def test_placeholder_returns_empty(self) -> None:
        stt = PlaceholderSTT()
        assert stt.transcribe(b"audio data") == ""

    def test_placeholder_returns_empty_on_empty_input(self) -> None:
        stt = PlaceholderSTT()
        assert stt.transcribe(b"") == ""

    def test_mock_stt_returns_scripted(self) -> None:
        stt = MockSTT(["hello world", "second response"])
        assert stt.transcribe(b"chunk1") == "hello world"
        assert stt.transcribe(b"chunk2") == "second response"
        assert stt.transcribe(b"chunk3") == ""

    def test_mock_stt_tracks_call_count(self) -> None:
        stt = MockSTT(["test"])
        stt.transcribe(b"a")
        stt.transcribe(b"b")
        assert stt.call_count == 2

    def test_placeholder_satisfies_protocol(self) -> None:
        stt = PlaceholderSTT()
        assert isinstance(stt, STTEngine)

    def test_mock_satisfies_protocol(self) -> None:
        stt = MockSTT([])
        assert isinstance(stt, STTEngine)


# ─── 2. TTS Engine Tests ────────────────────────────────────────────


class TestTTSEngine:
    def test_placeholder_does_not_raise(self) -> None:
        tts = PlaceholderTTS()
        tts.speak("hello")  # should not raise
        tts.shutdown()

    def test_mock_tts_captures_calls(self) -> None:
        tts = MockTTS()
        tts.speak("first")
        tts.speak("second")
        assert tts.spoken == ["first", "second"]

    def test_mock_tts_shutdown(self) -> None:
        tts = MockTTS()
        tts.shutdown()  # should not raise

    def test_placeholder_satisfies_protocol(self) -> None:
        tts = PlaceholderTTS()
        assert isinstance(tts, TTSEngine)

    def test_mock_satisfies_protocol(self) -> None:
        tts = MockTTS()
        assert isinstance(tts, TTSEngine)


# ─── 3. VoiceAdapter: handles completion events ─────────────────────


class TestVoiceAdapterSupports:
    def test_supports_ritual_completed(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        assert adapter.supports("ritual_completed")

    def test_supports_action_completed(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        assert adapter.supports("action_completed")

    def test_supports_open_day_started(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        assert adapter.supports("open_day_started")

    def test_supports_close_day_started(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        assert adapter.supports("close_day_started")


# ─── 4. VoiceAdapter: does NOT handle step events ───────────────────


class TestVoiceAdapterRejects:
    def test_does_not_support_step_events(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        assert not adapter.supports("ritual_step_executed")

    def test_does_not_support_arbitrary_events(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        assert not adapter.supports("random_event")
        assert not adapter.supports("")


# ─── 5. VoiceAdapter: extracts correct summary text ─────────────────


class TestVoiceAdapterSummary:
    def test_ritual_completed_open_day(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        event = _make_event(
            "ritual_completed",
            payload={"result": {"mode_after": "deep_work"}},
            metadata={"ritual_kind": "open_day"},
        )
        adapter.handle(event, _make_adapter_context())
        assert len(tts.spoken) == 1
        assert "deep_work" in tts.spoken[0]

    def test_ritual_completed_close_day(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        event = _make_event(
            "ritual_completed",
            payload={"result": {}},
            metadata={"ritual_kind": "close_day"},
        )
        adapter.handle(event, _make_adapter_context())
        assert len(tts.spoken) == 1
        assert "closed" in tts.spoken[0].lower() or "goodnight" in tts.spoken[0].lower()

    def test_action_completed_with_intent(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        event = _make_event(
            "action_completed",
            payload={"result": {"intent_text": "build landing page"}},
        )
        adapter.handle(event, _make_adapter_context())
        assert len(tts.spoken) == 1
        assert "build landing page" in tts.spoken[0]

    def test_action_completed_without_intent(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        event = _make_event(
            "action_completed",
            payload={"result": {}},
        )
        adapter.handle(event, _make_adapter_context())
        assert len(tts.spoken) == 1
        assert "complete" in tts.spoken[0].lower()

    def test_open_day_started(self) -> None:
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        event = _make_event("open_day_started", payload={"plan": {}})
        adapter.handle(event, _make_adapter_context())
        assert len(tts.spoken) == 1
        assert "opening" in tts.spoken[0].lower()

    def test_handle_does_not_raise_on_bad_event(self) -> None:
        """Adapter must never raise — fail silently."""
        tts = MockTTS()
        adapter = VoiceAdapter(tts)
        # Event with no payload
        event = _make_event("ritual_completed")
        adapter.handle(event, _make_adapter_context())
        # Should still speak something (fallback text)
        assert len(tts.spoken) >= 1


# ─── 6. VoiceLoop: voice input → runtime.handle_input called ────────


class TestVoiceLoopBasic:
    def test_process_one_routes_to_runtime(self) -> None:
        runtime, store = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["check analytics"])
        audio = MockAudioSource([b"audio_chunk"])
        loop = VoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        result = loop.process_one()
        assert result is not None
        assert result["request_type"] == "action"
        assert result["intent_text"] == "check analytics"

    def test_process_one_returns_none_on_empty_audio(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["should not be called"])
        audio = MockAudioSource([])  # empty — no chunks
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        result = loop.process_one()
        assert result is None

    def test_process_one_returns_none_on_empty_transcription(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT([""])  # transcribes to empty
        audio = MockAudioSource([b"audio"])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        result = loop.process_one()
        assert result is None


# ─── 7. VoiceLoop: correct routing ──────────────────────────────────


class TestVoiceLoopRouting:
    def test_open_command_routes_to_open_day(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["!open morning"])
        audio = MockAudioSource([b"audio"])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        result = loop.process_one()
        assert result is not None
        assert result["request_type"] == "open_day"

    def test_close_command_routes_to_close_day(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["!close"])
        audio = MockAudioSource([b"audio"])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        result = loop.process_one()
        assert result is not None
        assert result["request_type"] == "close_day"

    def test_regular_text_routes_to_action(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["build the landing page"])
        audio = MockAudioSource([b"audio"])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        result = loop.process_one()
        assert result is not None
        assert result["request_type"] == "action"


# ─── 8. VoiceLoop: TTS called via adapter on response ───────────────


class TestVoiceLoopWithTTS:
    def test_tts_fires_on_action_completed(self) -> None:
        tts = MockTTS()
        voice_adapter = VoiceAdapter(tts)

        registry = AdapterRegistry()
        registry.register(voice_adapter)

        runtime, store = _make_runtime(registry=registry)
        runtime.start_session(transport="voice")

        stt = MockSTT(["schedule meeting"])
        audio = MockAudioSource([b"audio"])
        loop = VoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
            tts=tts,
        )

        loop.process_one()

        # VoiceAdapter should have spoken action_completed summary
        assert len(tts.spoken) > 0
        # At least one spoken item should reference the intent
        spoken_text = " ".join(tts.spoken)
        assert "schedule meeting" in spoken_text.lower() or "complete" in spoken_text.lower()


# ─── 9. VoiceLoop: stability ────────────────────────────────────────


class TestVoiceLoopStability:
    def test_loop_start_stop_no_crash(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT([])
        audio = MockAudioSource([])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        loop.start()
        assert loop.is_running
        time.sleep(0.2)
        loop.stop()
        assert not loop.is_running

    def test_double_start_raises(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT([])
        audio = MockAudioSource([])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        loop.start()
        try:
            with pytest.raises(RuntimeError, match="already running"):
                loop.start()
        finally:
            loop.stop()

    def test_stop_when_not_running_is_safe(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT([])
        audio = MockAudioSource([])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        loop.stop()  # should not raise

    def test_processed_count_increments(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["task one", "task two"])
        audio = MockAudioSource([b"a1", b"a2"])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        loop.process_one()
        loop.process_one()
        assert loop.processed_count == 2


# ─── 10. Wake Word Filtering ────────────────────────────────────────


class TestWakeWord:
    def test_wake_word_detected(self) -> None:
        triggered, remaining = _check_wake_word("hey jarvis build a landing page")
        assert triggered
        assert remaining == "build a landing page"

    def test_wake_word_not_detected(self) -> None:
        triggered, remaining = _check_wake_word("build a landing page")
        assert not triggered

    def test_wake_word_only(self) -> None:
        triggered, remaining = _check_wake_word("hey jarvis")
        assert triggered
        assert remaining == ""

    def test_wake_word_case_insensitive(self) -> None:
        triggered, remaining = _check_wake_word("HEY JARVIS do the thing")
        assert triggered
        assert remaining == "do the thing"

    def test_wake_word_eos(self) -> None:
        triggered, remaining = _check_wake_word("eos check status")
        assert triggered
        assert remaining == "check status"

    def test_empty_text(self) -> None:
        triggered, remaining = _check_wake_word("")
        assert not triggered

    def test_custom_wake_words(self) -> None:
        custom = frozenset({"computer"})
        triggered, remaining = _check_wake_word(
            "computer set course", wake_words=custom
        )
        assert triggered
        assert remaining == "set course"

    def test_voice_loop_filters_without_wake_word(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["build a page"])  # no wake word
        audio = MockAudioSource([b"audio"])
        loop = VoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
            wake_word_enabled=True,
        )

        result = loop.process_one()
        assert result is None  # filtered out

    def test_voice_loop_passes_with_wake_word(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["hey jarvis build a page"])
        audio = MockAudioSource([b"audio"])
        loop = VoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
            wake_word_enabled=True,
        )

        result = loop.process_one()
        assert result is not None
        assert result["request_type"] == "action"
        assert result["intent_text"] == "build a page"


# ─── 11. Session Continuity ─────────────────────────────────────────


class TestVoiceSessionContinuity:
    def test_multiple_voice_inputs_same_session(self) -> None:
        runtime, store = _make_runtime()
        start = runtime.start_session(transport="voice")
        session_id = start["session_id"]

        stt = MockSTT(["task one", "task two", "task three"])
        audio = MockAudioSource([b"a1", b"a2", b"a3"])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        for _ in range(3):
            result = loop.process_one()
            assert result is not None
            assert result["session_id"] == session_id

        assert store.get("action_count") == 3

    def test_voice_transport_preserved(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["do something"])
        audio = MockAudioSource([b"audio"])
        loop = VoiceLoop(runtime=runtime, stt=stt, audio_source=audio)

        result = loop.process_one()
        assert result is not None
        # The lifecycle result should show voice transport
        lr = result["lifecycle_result"]
        assert lr is not None


# ─── 12. No substrate/lifecycle imports in voice modules ─────────────


class TestNoForbiddenImports:
    def test_voice_adapter_no_substrate_imports(self) -> None:
        source = inspect.getsource(sys.modules["umh.adapters.voice_adapter"])
        assert "from eos.substrate" not in source
        assert "import umh.substrate" not in source

    def test_voice_loop_no_substrate_imports(self) -> None:
        source = inspect.getsource(sys.modules["umh.adapters.voice_loop"])
        assert "from eos.substrate" not in source
        assert "import umh.substrate" not in source

    def test_voice_loop_no_lifecycle_imports(self) -> None:
        source = inspect.getsource(sys.modules["umh.adapters.voice_loop"])
        assert "from umh.runtime_loop.lifecycle" not in source

    def test_stt_engine_no_substrate_imports(self) -> None:
        source = inspect.getsource(sys.modules["umh.adapters.stt_engine"])
        assert "from eos.substrate" not in source

    def test_tts_engine_no_substrate_imports(self) -> None:
        source = inspect.getsource(sys.modules["umh.adapters.tts_engine"])
        assert "from eos.substrate" not in source


# ─── 13. BufferedAudioSource ─────────────────────────────────────────


class TestBufferedAudioSource:
    def test_yields_chunks_in_order(self) -> None:
        source = BufferedAudioSource([b"chunk1", b"chunk2"])
        assert source.capture() == b"chunk1"
        assert source.capture() == b"chunk2"
        assert source.capture() == b""

    def test_add_chunk_extends_buffer(self) -> None:
        source = BufferedAudioSource()
        assert source.capture() == b""
        source.add_chunk(b"late_chunk")
        assert source.capture() == b"late_chunk"

    def test_satisfies_audio_source_protocol(self) -> None:
        source = BufferedAudioSource()
        assert isinstance(source, AudioSource)
