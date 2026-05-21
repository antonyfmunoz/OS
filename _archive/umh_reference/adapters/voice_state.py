"""Voice state machine — deterministic state transitions for the interruptible voice loop.

States:
    IDLE       — no audio processing, waiting for input
    LISTENING  — actively capturing and buffering audio
    THINKING   — STT complete, routing through lifecycle
    SPEAKING   — TTS playing response
    INTERRUPTED — user spoke during TTS, previous turn cancelled

Transitions are deterministic: every (state, event) pair maps to exactly
one next state. No implicit transitions, no timers.

Also provides:
    StreamingSTT   — protocol for push-based STT with partial/final results
    TTSController  — start/stop/is_speaking wrapper around TTSEngine
    VoiceTurn      — immutable record of a single voice interaction
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from umh.adapters.stt_engine import STTEngine
from umh.adapters.tts_engine import TTSEngine

logger = logging.getLogger(__name__)


# ── Voice Loop States ───────────────────────────────────────────────


class VoiceState(enum.Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


# ── Transition Events ───────────────────────────────────────────────


class VoiceEvent(enum.Enum):
    AUDIO_RECEIVED = "audio_received"
    SILENCE_DETECTED = "silence_detected"
    TRANSCRIPT_READY = "transcript_ready"
    RESPONSE_READY = "response_ready"
    SPEECH_FINISHED = "speech_finished"
    USER_INTERRUPTED = "user_interrupted"
    STOP = "stop"


# ── Transition Table ────────────────────────────────────────────────

_TRANSITIONS: dict[tuple[VoiceState, VoiceEvent], VoiceState] = {
    # IDLE
    (VoiceState.IDLE, VoiceEvent.AUDIO_RECEIVED): VoiceState.LISTENING,
    (VoiceState.IDLE, VoiceEvent.STOP): VoiceState.IDLE,
    # LISTENING
    (VoiceState.LISTENING, VoiceEvent.AUDIO_RECEIVED): VoiceState.LISTENING,
    (VoiceState.LISTENING, VoiceEvent.SILENCE_DETECTED): VoiceState.THINKING,
    (VoiceState.LISTENING, VoiceEvent.TRANSCRIPT_READY): VoiceState.THINKING,
    (VoiceState.LISTENING, VoiceEvent.STOP): VoiceState.IDLE,
    # THINKING
    (VoiceState.THINKING, VoiceEvent.RESPONSE_READY): VoiceState.SPEAKING,
    (VoiceState.THINKING, VoiceEvent.USER_INTERRUPTED): VoiceState.INTERRUPTED,
    (VoiceState.THINKING, VoiceEvent.STOP): VoiceState.IDLE,
    # SPEAKING
    (VoiceState.SPEAKING, VoiceEvent.SPEECH_FINISHED): VoiceState.IDLE,
    (VoiceState.SPEAKING, VoiceEvent.USER_INTERRUPTED): VoiceState.INTERRUPTED,
    (VoiceState.SPEAKING, VoiceEvent.STOP): VoiceState.IDLE,
    # INTERRUPTED
    (VoiceState.INTERRUPTED, VoiceEvent.AUDIO_RECEIVED): VoiceState.LISTENING,
    (VoiceState.INTERRUPTED, VoiceEvent.TRANSCRIPT_READY): VoiceState.THINKING,
    (VoiceState.INTERRUPTED, VoiceEvent.STOP): VoiceState.IDLE,
}


class VoiceStateMachine:
    """Deterministic state machine for voice loop control flow.

    Thread-safe: state reads/writes are protected by a lock.
    All transitions logged for debugging.
    """

    def __init__(self) -> None:
        self._state = VoiceState.IDLE
        self._lock = threading.Lock()
        self._transition_count = 0

    @property
    def state(self) -> VoiceState:
        with self._lock:
            return self._state

    @property
    def transition_count(self) -> int:
        with self._lock:
            return self._transition_count

    def transition(self, event: VoiceEvent) -> VoiceState:
        """Apply an event and return the new state.

        Returns the current state unchanged if the transition is not defined
        (invalid transitions are no-ops, not errors).
        """
        with self._lock:
            key = (self._state, event)
            new_state = _TRANSITIONS.get(key)
            if new_state is None:
                logger.debug(
                    "Voice FSM: no transition for (%s, %s) — staying in %s",
                    self._state.value,
                    event.value,
                    self._state.value,
                )
                return self._state

            old = self._state
            self._state = new_state
            self._transition_count += 1
            logger.debug(
                "Voice FSM: %s + %s → %s",
                old.value,
                event.value,
                new_state.value,
            )
            return new_state

    def reset(self) -> None:
        """Reset to IDLE."""
        with self._lock:
            self._state = VoiceState.IDLE
            self._transition_count = 0


# ── Voice Turn Record ───────────────────────────────────────────────


@dataclass(frozen=True)
class VoiceTurn:
    """Immutable record of a single voice interaction turn."""

    turn_id: int
    transcript: str
    response_text: str = ""
    request_type: str = ""
    interrupted: bool = False
    timestamp: float = field(default_factory=time.monotonic)


# ── Streaming STT Protocol ──────────────────────────────────────────


@runtime_checkable
class StreamingSTT(Protocol):
    """Protocol for push-based STT with partial and final results."""

    def push_audio_chunk(self, chunk: bytes) -> None:
        """Feed an audio chunk into the recognizer."""
        ...

    def poll_transcript_partial(self) -> str:
        """Return current partial transcript (may change). Empty if nothing yet."""
        ...

    def poll_transcript_final(self) -> str:
        """Return final transcript if utterance is complete. Empty if still listening."""
        ...

    def reset(self) -> None:
        """Clear internal state for next utterance."""
        ...


class BatchSTTAdapter:
    """Wraps a batch STTEngine to satisfy StreamingSTT interface.

    Accumulates audio chunks, then runs batch transcription when
    poll_transcript_final is called with enough audio data.

    Args:
        engine: Batch STTEngine to wrap.
        min_chunks: Minimum chunks before attempting transcription.
    """

    def __init__(self, engine: STTEngine, min_chunks: int = 1) -> None:
        self._engine = engine
        self._min_chunks = min_chunks
        self._chunks: list[bytes] = []
        self._final: str = ""
        self._finalized = False

    def push_audio_chunk(self, chunk: bytes) -> None:
        if chunk:
            self._chunks.append(chunk)

    def poll_transcript_partial(self) -> str:
        return ""

    def poll_transcript_final(self) -> str:
        if self._finalized:
            return self._final

        if len(self._chunks) < self._min_chunks:
            return ""

        audio = b"".join(self._chunks)
        self._final = self._engine.transcribe(audio)
        self._finalized = True
        return self._final

    def reset(self) -> None:
        self._chunks.clear()
        self._final = ""
        self._finalized = False


# ── TTS Controller ──────────────────────────────────────────────────


class TTSController:
    """Non-blocking TTS wrapper with start/stop/is_speaking semantics.

    Wraps a TTSEngine and tracks speaking state via a background thread.
    The main loop can check is_speaking() and call stop_speaking() to
    interrupt without blocking.

    Args:
        engine: Underlying TTSEngine.
    """

    def __init__(self, engine: TTSEngine) -> None:
        self._engine = engine
        self._speaking = False
        self._lock = threading.Lock()
        self._stop_requested = False
        self._current_thread: threading.Thread | None = None

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._speaking

    def start_speaking(self, text: str) -> None:
        """Begin speaking text on a background thread. Non-blocking."""
        if not text or not text.strip():
            return

        with self._lock:
            self._stop_requested = False
            self._speaking = True

        t = threading.Thread(
            target=self._speak_worker,
            args=(text.strip(),),
            daemon=True,
            name="tts-controller",
        )
        self._current_thread = t
        t.start()

    def _speak_worker(self, text: str) -> None:
        try:
            if not self._stop_requested:
                self._engine.speak(text)
        except Exception as exc:
            logger.warning("TTSController speak failed: %s", exc)
        finally:
            with self._lock:
                self._speaking = False

    def stop_speaking(self) -> None:
        """Request TTS to stop. Non-blocking."""
        with self._lock:
            self._stop_requested = True
            self._speaking = False

    def shutdown(self) -> None:
        """Shut down the underlying TTS engine."""
        self.stop_speaking()
        self._engine.shutdown()


# ── Session Context ─────────────────────────────────────────────────


class VoiceSessionContext:
    """Tracks session-level state across voice turns.

    Tied to a LiveRuntime session_id. Preserves last intent,
    last action result, and open execution count across turns.
    Does NOT create a new session per utterance.
    """

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._turn_counter = 0
        self._last_intent: str = ""
        self._last_action_result: dict[str, Any] = {}
        self._open_execution_count: int = 0
        self._turns: list[VoiceTurn] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def turn_count(self) -> int:
        return self._turn_counter

    @property
    def last_intent(self) -> str:
        return self._last_intent

    @property
    def last_action_result(self) -> dict[str, Any]:
        return dict(self._last_action_result)

    @property
    def open_execution_count(self) -> int:
        return self._open_execution_count

    @property
    def turns(self) -> list[VoiceTurn]:
        return list(self._turns)

    def record_turn(
        self,
        transcript: str,
        response_text: str = "",
        request_type: str = "",
        interrupted: bool = False,
    ) -> VoiceTurn:
        """Record a completed voice turn and update session state."""
        self._turn_counter += 1
        turn = VoiceTurn(
            turn_id=self._turn_counter,
            transcript=transcript,
            response_text=response_text,
            request_type=request_type,
            interrupted=interrupted,
        )
        self._turns.append(turn)
        self._last_intent = transcript
        if not interrupted:
            self._open_execution_count += 1
        return turn

    def update_action_result(self, result: dict[str, Any]) -> None:
        """Update last action result from lifecycle response."""
        self._last_action_result = dict(result)

    def get_context_for_input(self) -> dict[str, Any]:
        """Return context metadata to attach to InputEvent for continuity."""
        return {
            "source": "voice_loop",
            "session_id": self._session_id,
            "turn_number": self._turn_counter + 1,
            "last_intent": self._last_intent,
            "open_executions": self._open_execution_count,
        }
