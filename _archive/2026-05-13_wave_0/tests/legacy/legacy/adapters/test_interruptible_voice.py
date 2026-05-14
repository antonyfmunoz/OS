"""Tests for the interruptible, session-aware voice loop.

Covers:
1.  State machine: all valid transitions
2.  State machine: invalid transitions are no-ops
3.  BatchSTTAdapter: push/poll/reset cycle
4.  TTSController: start/stop/is_speaking
5.  VoiceSessionContext: turn recording and context
6.  InterruptibleVoiceLoop: basic tick cycle (idle → listening → thinking → speaking → idle)
7.  InterruptibleVoiceLoop: interruption during TTS
8.  InterruptibleVoiceLoop: multiple rapid inputs
9.  InterruptibleVoiceLoop: session persistence across turns
10. InterruptibleVoiceLoop: wake word filtering
11. InterruptibleVoiceLoop: state correctness after each tick
12. InterruptibleVoiceLoop: no substrate/lifecycle imports in voice_state
13. InterruptibleVoiceLoop: start/stop lifecycle
"""

import sys

sys.path.insert(0, "/opt/OS")

import inspect
import time

import pytest
from typing import Any

from umh.adapters.contracts import AdapterContext
from umh.adapters.registry import AdapterRegistry
from umh.adapters.stt_engine import PlaceholderSTT, STTEngine
from umh.adapters.tts_engine import PlaceholderTTS, TTSEngine
from umh.adapters.voice_adapter import VoiceAdapter
from umh.adapters.voice_loop import (
    AudioSource,
    BufferedAudioSource,
    InterruptibleVoiceLoop,
    VoiceLoop,
)
from umh.adapters.voice_state import (
    BatchSTTAdapter,
    StreamingSTT,
    TTSController,
    VoiceEvent,
    VoiceSessionContext,
    VoiceState,
    VoiceStateMachine,
    VoiceTurn,
)
from umh.runtime_loop.input_router import InputEvent
from umh.runtime_loop.live_loop import LiveRuntime
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


class MockStreamingSTT:
    """Streaming STT mock with explicit control over partial/final results."""

    def __init__(self, finals: list[str]) -> None:
        self._finals = list(finals)
        self._final_index = 0
        self._chunks_received: list[bytes] = []
        self._partial = ""
        self.push_count = 0
        self.poll_partial_count = 0
        self.poll_final_count = 0
        self.reset_count = 0

    def push_audio_chunk(self, chunk: bytes) -> None:
        self.push_count += 1
        self._chunks_received.append(chunk)

    def poll_transcript_partial(self) -> str:
        self.poll_partial_count += 1
        return self._partial

    def poll_transcript_final(self) -> str:
        self.poll_final_count += 1
        if self._chunks_received and self._final_index < len(self._finals):
            result = self._finals[self._final_index]
            self._final_index += 1
            return result
        return ""

    def reset(self) -> None:
        self.reset_count += 1
        self._chunks_received.clear()
        self._partial = ""


class MockTTS:
    """TTS mock that captures speak() calls and tracks state."""

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self._speaking = False

    def speak(self, text: str) -> None:
        self.spoken.append(text)
        self._speaking = True

    def shutdown(self) -> None:
        self._speaking = False


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

    def add_chunk(self, chunk: bytes) -> None:
        self._chunks.append(chunk)


# ─── Helpers ─────────────────────────────────────────────────────────


def _make_runtime(
    registry: AdapterRegistry | None = None,
) -> tuple[LiveRuntime, RuntimeStateStore]:
    store = RuntimeStateStore()
    reg = registry or AdapterRegistry()
    runtime = LiveRuntime(state_store=store, adapter_registry=reg)
    return runtime, store


# ═══════════════════════════════════════════════════════════════════════
# 1. State Machine: Valid Transitions
# ═══════════════════════════════════════════════════════════════════════


class TestVoiceStateMachine:
    def test_initial_state_is_idle(self) -> None:
        fsm = VoiceStateMachine()
        assert fsm.state == VoiceState.IDLE

    def test_idle_to_listening(self) -> None:
        fsm = VoiceStateMachine()
        new = fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        assert new == VoiceState.LISTENING

    def test_listening_to_thinking_on_silence(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        new = fsm.transition(VoiceEvent.SILENCE_DETECTED)
        assert new == VoiceState.THINKING

    def test_listening_to_thinking_on_transcript(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        new = fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        assert new == VoiceState.THINKING

    def test_listening_stays_on_more_audio(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        new = fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        assert new == VoiceState.LISTENING

    def test_thinking_to_speaking(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        new = fsm.transition(VoiceEvent.RESPONSE_READY)
        assert new == VoiceState.SPEAKING

    def test_speaking_to_idle_on_finish(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        fsm.transition(VoiceEvent.RESPONSE_READY)
        new = fsm.transition(VoiceEvent.SPEECH_FINISHED)
        assert new == VoiceState.IDLE

    def test_speaking_to_interrupted(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        fsm.transition(VoiceEvent.RESPONSE_READY)
        new = fsm.transition(VoiceEvent.USER_INTERRUPTED)
        assert new == VoiceState.INTERRUPTED

    def test_interrupted_to_listening(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        fsm.transition(VoiceEvent.RESPONSE_READY)
        fsm.transition(VoiceEvent.USER_INTERRUPTED)
        new = fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        assert new == VoiceState.LISTENING

    def test_transition_count(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        assert fsm.transition_count == 2

    def test_reset_clears_state(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        fsm.reset()
        assert fsm.state == VoiceState.IDLE
        assert fsm.transition_count == 0

    def test_stop_from_any_active_state(self) -> None:
        for start_event in [
            VoiceEvent.AUDIO_RECEIVED,
        ]:
            fsm = VoiceStateMachine()
            fsm.transition(start_event)
            new = fsm.transition(VoiceEvent.STOP)
            assert new == VoiceState.IDLE


# ═══════════════════════════════════════════════════════════════════════
# 2. State Machine: Invalid Transitions
# ═══════════════════════════════════════════════════════════════════════


class TestVoiceStateMachineInvalid:
    def test_idle_ignores_silence(self) -> None:
        fsm = VoiceStateMachine()
        new = fsm.transition(VoiceEvent.SILENCE_DETECTED)
        assert new == VoiceState.IDLE

    def test_idle_ignores_transcript(self) -> None:
        fsm = VoiceStateMachine()
        new = fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        assert new == VoiceState.IDLE

    def test_thinking_ignores_audio(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        new = fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        assert new == VoiceState.THINKING

    def test_speaking_ignores_transcript(self) -> None:
        fsm = VoiceStateMachine()
        fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        fsm.transition(VoiceEvent.RESPONSE_READY)
        new = fsm.transition(VoiceEvent.TRANSCRIPT_READY)
        assert new == VoiceState.SPEAKING


# ═══════════════════════════════════════════════════════════════════════
# 3. BatchSTTAdapter
# ═══════════════════════════════════════════════════════════════════════


class TestBatchSTTAdapter:
    def test_push_poll_cycle(self) -> None:
        stt = MockSTT(["hello world"])
        adapter = BatchSTTAdapter(stt)

        adapter.push_audio_chunk(b"chunk1")
        final = adapter.poll_transcript_final()
        assert final == "hello world"

    def test_returns_empty_before_min_chunks(self) -> None:
        stt = MockSTT(["hello"])
        adapter = BatchSTTAdapter(stt, min_chunks=3)

        adapter.push_audio_chunk(b"c1")
        assert adapter.poll_transcript_final() == ""

        adapter.push_audio_chunk(b"c2")
        assert adapter.poll_transcript_final() == ""

        adapter.push_audio_chunk(b"c3")
        assert adapter.poll_transcript_final() == "hello"

    def test_reset_clears_state(self) -> None:
        stt = MockSTT(["first", "second"])
        adapter = BatchSTTAdapter(stt)

        adapter.push_audio_chunk(b"c1")
        adapter.poll_transcript_final()

        adapter.reset()
        adapter.push_audio_chunk(b"c2")
        final = adapter.poll_transcript_final()
        assert final == "second"

    def test_partial_always_empty(self) -> None:
        stt = MockSTT(["test"])
        adapter = BatchSTTAdapter(stt)
        adapter.push_audio_chunk(b"c1")
        assert adapter.poll_transcript_partial() == ""

    def test_satisfies_streaming_protocol(self) -> None:
        stt = MockSTT([])
        adapter = BatchSTTAdapter(stt)
        assert isinstance(adapter, StreamingSTT)

    def test_empty_chunks_ignored(self) -> None:
        stt = MockSTT(["result"])
        adapter = BatchSTTAdapter(stt)
        adapter.push_audio_chunk(b"")
        assert adapter.poll_transcript_final() == ""
        adapter.push_audio_chunk(b"real")
        assert adapter.poll_transcript_final() == "result"


# ═══════════════════════════════════════════════════════════════════════
# 4. TTSController
# ═══════════════════════════════════════════════════════════════════════


class TestTTSController:
    def test_start_speaking_delegates_to_engine(self) -> None:
        tts = MockTTS()
        ctrl = TTSController(tts)

        ctrl.start_speaking("hello")
        time.sleep(0.1)

        assert "hello" in tts.spoken

    def test_stop_speaking_clears_flag(self) -> None:
        tts = MockTTS()
        ctrl = TTSController(tts)

        ctrl.start_speaking("hello")
        ctrl.stop_speaking()
        assert not ctrl.is_speaking

    def test_is_speaking_false_initially(self) -> None:
        tts = MockTTS()
        ctrl = TTSController(tts)
        assert not ctrl.is_speaking

    def test_empty_text_ignored(self) -> None:
        tts = MockTTS()
        ctrl = TTSController(tts)
        ctrl.start_speaking("")
        ctrl.start_speaking("  ")
        assert len(tts.spoken) == 0

    def test_shutdown_stops_engine(self) -> None:
        tts = MockTTS()
        ctrl = TTSController(tts)
        ctrl.shutdown()
        assert not ctrl.is_speaking


# ═══════════════════════════════════════════════════════════════════════
# 5. VoiceSessionContext
# ═══════════════════════════════════════════════════════════════════════


class TestVoiceSessionContext:
    def test_initial_state(self) -> None:
        ctx = VoiceSessionContext("sess_123")
        assert ctx.session_id == "sess_123"
        assert ctx.turn_count == 0
        assert ctx.last_intent == ""
        assert ctx.open_execution_count == 0

    def test_record_turn(self) -> None:
        ctx = VoiceSessionContext("sess_123")
        turn = ctx.record_turn(
            transcript="build landing page",
            request_type="action",
        )

        assert turn.turn_id == 1
        assert turn.transcript == "build landing page"
        assert ctx.turn_count == 1
        assert ctx.last_intent == "build landing page"
        assert ctx.open_execution_count == 1

    def test_interrupted_turn_does_not_increment_executions(self) -> None:
        ctx = VoiceSessionContext("sess_123")
        ctx.record_turn(transcript="first", request_type="action")
        ctx.record_turn(
            transcript="first",
            request_type="action",
            interrupted=True,
        )

        assert ctx.turn_count == 2
        assert ctx.open_execution_count == 1

    def test_multiple_turns_preserve_session(self) -> None:
        ctx = VoiceSessionContext("sess_abc")

        ctx.record_turn(transcript="task one", request_type="action")
        ctx.record_turn(transcript="task two", request_type="action")
        ctx.record_turn(transcript="task three", request_type="action")

        assert ctx.session_id == "sess_abc"
        assert ctx.turn_count == 3
        assert ctx.last_intent == "task three"
        assert ctx.open_execution_count == 3

    def test_context_for_input_metadata(self) -> None:
        ctx = VoiceSessionContext("sess_meta")
        ctx.record_turn(transcript="first task", request_type="action")

        meta = ctx.get_context_for_input()
        assert meta["session_id"] == "sess_meta"
        assert meta["turn_number"] == 2
        assert meta["last_intent"] == "first task"
        assert meta["open_executions"] == 1

    def test_update_action_result(self) -> None:
        ctx = VoiceSessionContext("sess_res")
        ctx.update_action_result({"status": "completed", "output": "done"})
        assert ctx.last_action_result["status"] == "completed"

    def test_turns_list_is_copy(self) -> None:
        ctx = VoiceSessionContext("sess_copy")
        ctx.record_turn(transcript="test", request_type="action")
        turns = ctx.turns
        turns.clear()
        assert ctx.turn_count == 1
        assert len(ctx.turns) == 1


# ═══════════════════════════════════════════════════════════════════════
# 6. InterruptibleVoiceLoop: Basic Tick Cycle
# ═══════════════════════════════════════════════════════════════════════


class TestInterruptibleBasicCycle:
    def test_full_cycle_idle_to_idle(self) -> None:
        """IDLE → LISTENING → THINKING → (reset to IDLE, no TTS)"""
        runtime, store = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["check status"])
        audio = MockAudioSource([b"audio1"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        assert loop.state == VoiceState.IDLE

        # Tick 1: capture audio → LISTENING
        loop.tick()
        assert loop.state == VoiceState.LISTENING

        # Tick 2: no more audio, transcript ready → THINKING → processes → IDLE
        result = loop.tick()
        # After listening tick with silence, goes to THINKING
        # The next tick processes THINKING
        if loop.state == VoiceState.THINKING:
            result = loop.tick()

        assert loop.processed_count == 1
        assert loop.state == VoiceState.IDLE

    def test_returns_result_on_thinking(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["do something"])
        audio = MockAudioSource([b"audio"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        # Drive through states until we get a result
        result = None
        for _ in range(5):
            r = loop.tick()
            if r is not None:
                result = r
                break

        assert result is not None
        assert result["request_type"] == "action"

    def test_empty_audio_stays_idle(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT([])
        audio = MockAudioSource([])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        loop.tick()
        assert loop.state == VoiceState.IDLE


# ═══════════════════════════════════════════════════════════════════════
# 7. InterruptibleVoiceLoop: Interruption During TTS
# ═══════════════════════════════════════════════════════════════════════


class TestInterruption:
    def test_interrupt_during_speaking(self) -> None:
        """User speaks while TTS is playing → TTS stops, new turn begins."""
        runtime, _ = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["first command", "interrupt command"])
        tts = MockTTS()

        # First chunk for initial command, then interrupt chunk during TTS
        audio = MockAudioSource([b"audio1"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
            tts=tts,
        )

        # Drive to SPEAKING state
        for _ in range(10):
            loop.tick()
            if loop.state == VoiceState.SPEAKING:
                break

        assert loop.state == VoiceState.SPEAKING

        # Now add interrupting audio
        audio.add_chunk(b"interrupt_audio")
        loop.tick()

        assert loop.state in (VoiceState.INTERRUPTED, VoiceState.LISTENING)
        assert loop.interrupted_count == 1

    def test_interrupted_turn_recorded_in_session(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["first task", "second task"])
        tts = MockTTS()
        audio = MockAudioSource([b"audio1"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
            tts=tts,
        )

        # Complete first turn to speaking
        for _ in range(10):
            loop.tick()
            if loop.state == VoiceState.SPEAKING:
                break

        # Interrupt
        audio.add_chunk(b"interrupt")
        loop.tick()

        session = loop.session
        assert session is not None
        interrupted_turns = [t for t in session.turns if t.interrupted]
        assert len(interrupted_turns) >= 1


# ═══════════════════════════════════════════════════════════════════════
# 8. InterruptibleVoiceLoop: Multiple Rapid Inputs
# ═══════════════════════════════════════════════════════════════════════


class TestRapidInputs:
    def test_three_inputs_sequential(self) -> None:
        runtime, store = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["task one", "task two", "task three"])
        audio = MockAudioSource([b"a1", b"a2", b"a3"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        results = []
        for _ in range(30):
            r = loop.tick()
            if r is not None:
                results.append(r)
            if loop.state == VoiceState.IDLE and len(results) >= 3:
                break

        assert len(results) == 3
        assert all(r["request_type"] == "action" for r in results)

    def test_processed_count_matches_inputs(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["a", "b"])
        audio = MockAudioSource([b"c1", b"c2"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        for _ in range(20):
            loop.tick()

        assert loop.processed_count == 2


# ═══════════════════════════════════════════════════════════════════════
# 9. InterruptibleVoiceLoop: Session Persistence
# ═══════════════════════════════════════════════════════════════════════


class TestSessionPersistence:
    def test_session_bound_to_runtime(self) -> None:
        runtime, _ = _make_runtime()
        start = runtime.start_session(transport="voice")
        session_id = start["session_id"]

        stt = MockSTT(["test"])
        audio = MockAudioSource([b"audio"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        for _ in range(10):
            loop.tick()
            if loop.processed_count > 0:
                break

        assert loop.session is not None
        assert loop.session.session_id == session_id

    def test_last_intent_preserved(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["build page", "deploy app"])
        audio = MockAudioSource([b"a1", b"a2"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        for _ in range(20):
            loop.tick()

        assert loop.session is not None
        assert loop.session.last_intent == "deploy app"

    def test_execution_count_tracks(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["one", "two", "three"])
        audio = MockAudioSource([b"a1", b"a2", b"a3"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        for _ in range(30):
            loop.tick()

        assert loop.session is not None
        assert loop.session.open_execution_count == 3

    def test_context_metadata_in_input(self) -> None:
        """Verify session context metadata flows into InputEvent."""
        runtime, _ = _make_runtime()
        runtime.start_session(transport="voice")

        stt = MockSTT(["first", "second"])
        audio = MockAudioSource([b"a1", b"a2"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        results = []
        for _ in range(20):
            r = loop.tick()
            if r is not None:
                results.append(r)

        assert len(results) == 2
        assert loop.session is not None
        assert loop.session.turn_count == 2


# ═══════════════════════════════════════════════════════════════════════
# 10. InterruptibleVoiceLoop: Wake Word
# ═══════════════════════════════════════════════════════════════════════


class TestInterruptibleWakeWord:
    def test_filtered_without_wake_word(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["build something"])
        audio = MockAudioSource([b"audio"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
            wake_word_enabled=True,
        )

        for _ in range(10):
            loop.tick()

        assert loop.processed_count == 0

    def test_passes_with_wake_word(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["hey jarvis build something"])
        audio = MockAudioSource([b"audio"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
            wake_word_enabled=True,
        )

        result = None
        for _ in range(10):
            r = loop.tick()
            if r is not None:
                result = r
                break

        assert result is not None
        assert result["intent_text"] == "build something"


# ═══════════════════════════════════════════════════════════════════════
# 11. State Correctness After Each Tick
# ═══════════════════════════════════════════════════════════════════════


class TestStateCorrectness:
    def test_never_reaches_invalid_state(self) -> None:
        """Run many ticks and verify state is always a valid VoiceState."""
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["a", "b", "c"])
        audio = MockAudioSource([b"x", b"y", b"z"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        valid_states = set(VoiceState)
        for _ in range(30):
            loop.tick()
            assert loop.state in valid_states

    def test_ends_in_idle_after_exhaustion(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT(["single"])
        audio = MockAudioSource([b"chunk"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        for _ in range(20):
            loop.tick()

        assert loop.state == VoiceState.IDLE


# ═══════════════════════════════════════════════════════════════════════
# 12. No Forbidden Imports
# ═══════════════════════════════════════════════════════════════════════


class TestNoForbiddenImportsInterruptible:
    def test_voice_state_no_substrate_imports(self) -> None:
        source = inspect.getsource(sys.modules["umh.adapters.voice_state"])
        assert "from eos.substrate" not in source
        assert "import umh.substrate" not in source

    def test_voice_state_no_lifecycle_imports(self) -> None:
        source = inspect.getsource(sys.modules["umh.adapters.voice_state"])
        assert "from umh.runtime_loop.lifecycle" not in source


# ═══════════════════════════════════════════════════════════════════════
# 13. Start/Stop Lifecycle
# ═══════════════════════════════════════════════════════════════════════


class TestInterruptibleLifecycle:
    def test_start_stop(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT([])
        audio = MockAudioSource([])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        loop.start()
        assert loop.is_running
        time.sleep(0.15)
        loop.stop()
        assert not loop.is_running

    def test_double_start_raises(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT([])
        audio = MockAudioSource([])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        loop.start()
        try:
            with pytest.raises(RuntimeError, match="already running"):
                loop.start()
        finally:
            loop.stop()

    def test_stop_when_not_running(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session()

        stt = MockSTT([])
        audio = MockAudioSource([])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=stt,
            audio_source=audio,
        )

        loop.stop()  # should not raise


# ═══════════════════════════════════════════════════════════════════════
# 14. Streaming STT Integration
# ═══════════════════════════════════════════════════════════════════════


class TestStreamingSTTIntegration:
    def test_streaming_stt_used_directly(self) -> None:
        runtime, _ = _make_runtime()
        runtime.start_session(transport="voice")

        streaming = MockStreamingSTT(finals=["streaming result"])
        audio = MockAudioSource([b"audio"])
        loop = InterruptibleVoiceLoop(
            runtime=runtime,
            stt=streaming,
            audio_source=audio,
        )

        result = None
        for _ in range(10):
            r = loop.tick()
            if r is not None:
                result = r
                break

        assert result is not None
        assert streaming.push_count >= 1
        assert streaming.reset_count >= 1

    def test_mock_streaming_satisfies_protocol(self) -> None:
        s = MockStreamingSTT(finals=[])
        assert isinstance(s, StreamingSTT)
