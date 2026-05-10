"""Voice loop — continuous listen → transcribe → route cycle.

Runs a "Jarvis-style" continuous voice session that:
1. Captures audio from a pluggable AudioSource
2. Transcribes via STT engine (batch or streaming)
3. Optionally filters by wake word
4. Routes through LiveRuntime as InputEvent(transport="voice")

Supports two modes:
- Turn-based (original): capture → transcribe → route → repeat
- Interruptible (new): continuous capture with state machine,
  interrupt-on-speak, session-aware context, rolling buffer

Design rules:
- Runs on its own thread — does not block the caller
- Pluggable audio source — no hardcoded mic library
- Graceful shutdown via stop()
- Never crashes — all errors caught and logged
- State transitions are deterministic

Public API:
    AudioSource (Protocol)       — structural type for audio capture
    SoundDeviceSource            — real mic via sounddevice (when available)
    BufferedAudioSource          — pre-loaded audio for testing/playback
    VoiceLoop                    — the continuous voice session (turn-based)
    InterruptibleVoiceLoop       — state-machine-driven interruptible session
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Any, Protocol, runtime_checkable

from umh.adapters.stt_engine import STTEngine
from umh.adapters.tts_engine import TTSEngine
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

logger = logging.getLogger(__name__)

_LOG_PREFIX = "[adapters.voice_loop]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ── Audio Source Protocol ────────────────────────────────────────────


@runtime_checkable
class AudioSource(Protocol):
    """Structural type for audio capture backends.

    Any class with a matching capture() method satisfies this protocol.
    """

    def capture(self) -> bytes:
        """Capture a chunk of audio from the source.

        Returns:
            Raw audio bytes (WAV format, 16kHz mono recommended).
            Return empty bytes when no audio is available.
        """
        ...


# ── SoundDevice Source ───────────────────────────────────────────────


class SoundDeviceSource:
    """Real microphone capture via sounddevice.

    Args:
        duration:    Chunk duration in seconds.
        sample_rate: Audio sample rate in Hz.
    """

    def __init__(
        self,
        duration: float = 2.0,
        sample_rate: int = 16000,
    ) -> None:
        self._duration = duration
        self._sample_rate = sample_rate
        self._available = False
        try:
            import sounddevice  # noqa: F401

            self._available = True
        except ImportError:
            _log("sounddevice not available — SoundDeviceSource disabled")

    def capture(self) -> bytes:
        """Capture audio from default microphone.

        Returns WAV-formatted bytes, or empty bytes if unavailable.
        """
        if not self._available:
            return b""

        try:
            import io
            import wave

            import numpy as np
            import sounddevice as sd

            recording = sd.rec(
                int(self._duration * self._sample_rate),
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
            )
            sd.wait()

            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self._sample_rate)
                wf.writeframes(recording.tobytes())

            return buf.getvalue()

        except Exception as exc:
            logger.warning("Mic capture failed: %s", exc)
            return b""


# ── Buffered Source (Testing / Playback) ─────────────────────────────


class BufferedAudioSource:
    """Audio source that yields pre-loaded chunks, then empty bytes.

    Useful for testing and file-based playback.

    Args:
        chunks: List of audio byte chunks to yield in order.
    """

    def __init__(self, chunks: list[bytes] | None = None) -> None:
        self._chunks = list(chunks) if chunks else []
        self._index = 0

    def capture(self) -> bytes:
        """Return next buffered chunk, or empty bytes when exhausted."""
        if self._index < len(self._chunks):
            chunk = self._chunks[self._index]
            self._index += 1
            return chunk
        return b""

    def add_chunk(self, chunk: bytes) -> None:
        """Add a chunk to the buffer (for dynamic feeding)."""
        self._chunks.append(chunk)


# ── Wake Word Detection ──────────────────────────────────────────────

_DEFAULT_WAKE_WORDS = frozenset({"hey", "jarvis", "hey jarvis", "eos"})


def _check_wake_word(
    text: str,
    wake_words: frozenset[str] = _DEFAULT_WAKE_WORDS,
) -> tuple[bool, str]:
    """Check if text starts with a wake word.

    Args:
        text: Transcribed text to check.
        wake_words: Set of wake word prefixes.

    Returns:
        (triggered, remaining_text): Whether wake word was detected,
        and the text after the wake word.
    """
    lower = text.lower().strip()
    if not lower:
        return False, ""

    for word in sorted(wake_words, key=len, reverse=True):
        if lower.startswith(word):
            remaining = lower[len(word) :].strip()
            # Remove common fillers after wake word
            for filler in (",", ".", " um", " uh"):
                if remaining.startswith(filler):
                    remaining = remaining[len(filler) :].strip()
            return True, remaining

    return False, ""


# ── Voice Loop (original turn-based) ────────────────────────────────


class VoiceLoop:
    """Continuous voice session: listen → transcribe → route → speak.

    Runs on a daemon thread. Captures audio, transcribes with STT,
    filters by wake word (optional), and routes through LiveRuntime.

    Args:
        runtime:       LiveRuntime instance (must have active session).
        stt:           STTEngine for transcription.
        tts:           TTSEngine for spoken responses (optional).
        audio_source:  AudioSource for mic capture.
        wake_word_enabled: Whether to require wake word before processing.
        wake_words:    Custom wake word set (default: hey, jarvis, eos).
        silence_interval: Seconds to sleep when no audio captured.
    """

    def __init__(
        self,
        runtime: Any,  # LiveRuntime — Any to avoid circular import
        stt: STTEngine,
        audio_source: AudioSource,
        tts: TTSEngine | None = None,
        wake_word_enabled: bool = False,
        wake_words: frozenset[str] | None = None,
        silence_interval: float = 0.1,
    ) -> None:
        self._runtime = runtime
        self._stt = stt
        self._tts = tts
        self._audio_source = audio_source
        self._wake_word_enabled = wake_word_enabled
        self._wake_words = wake_words or _DEFAULT_WAKE_WORDS
        self._silence_interval = silence_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._processed_count = 0
        self._error_count = 0

    # ── Properties ───────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """Whether the voice loop is currently active."""
        return self._running

    @property
    def processed_count(self) -> int:
        """Number of successfully processed voice inputs."""
        return self._processed_count

    @property
    def error_count(self) -> int:
        """Number of errors encountered during processing."""
        return self._error_count

    # ── Lifecycle ────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the voice loop on a background daemon thread.

        Raises:
            RuntimeError: If already running.
        """
        if self._running:
            raise RuntimeError("VoiceLoop is already running")

        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="voice-loop",
            daemon=True,
        )
        self._thread.start()
        _log("Voice loop started")

    def stop(self) -> None:
        """Stop the voice loop gracefully.

        Blocks until the worker thread exits (up to 5 seconds).
        """
        if not self._running:
            return

        _log("Voice loop stopping...")
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        _log(
            f"Voice loop stopped. Processed: {self._processed_count}, "
            f"Errors: {self._error_count}"
        )

    # ── Main Loop ────────────────────────────────────────────────────

    def _loop(self) -> None:
        """Main voice loop — runs on background thread."""
        while self._running:
            try:
                self._tick()
            except Exception as exc:
                self._error_count += 1
                logger.warning("Voice loop tick error: %s", exc)
                time.sleep(self._silence_interval)

    def _tick(self) -> None:
        """Single iteration of the voice loop."""
        # 1. Capture audio
        audio = self._audio_source.capture()
        if not audio:
            time.sleep(self._silence_interval)
            return

        # 2. Transcribe
        text = self._stt.transcribe(audio)
        if not text or not text.strip():
            return

        text = text.strip()

        # 3. Wake word filter (optional)
        if self._wake_word_enabled:
            triggered, remaining = _check_wake_word(text, self._wake_words)
            if not triggered:
                return
            text = remaining
            if not text:
                # Wake word only, no command
                if self._tts:
                    self._tts.speak("Listening.")
                return

        # 4. Route through LiveRuntime
        event = InputEvent(
            transport="voice",
            text=text,
            metadata={"source": "voice_loop"},
        )

        logger.info("[VoiceLoop] Processing: %s", text[:80])

        result = self._runtime.handle_input(event)
        self._processed_count += 1

        logger.info(
            "[VoiceLoop] Handled as %s (session=%s)",
            result.get("request_type", "unknown"),
            result.get("session_id", "unknown"),
        )

    # ── Synchronous processing (for testing) ─────────────────────────

    def process_one(self) -> dict[str, Any] | None:
        """Process a single audio capture synchronously.

        Does NOT require start() — useful for testing without threads.

        Returns:
            Result dict from handle_input, or None if nothing processed.
        """
        audio = self._audio_source.capture()
        if not audio:
            return None

        text = self._stt.transcribe(audio)
        if not text or not text.strip():
            return None

        text = text.strip()

        if self._wake_word_enabled:
            triggered, remaining = _check_wake_word(text, self._wake_words)
            if not triggered:
                return None
            text = remaining
            if not text:
                return None

        event = InputEvent(
            transport="voice",
            text=text,
            metadata={"source": "voice_loop"},
        )

        result = self._runtime.handle_input(event)
        self._processed_count += 1
        return result


# ── Interruptible Voice Loop ────────────────────────────────────────


class InterruptibleVoiceLoop:
    """State-machine-driven voice loop with interruption and session awareness.

    Unlike VoiceLoop, this loop:
    - Uses a state machine (IDLE → LISTENING → THINKING → SPEAKING)
    - Supports interruption: user speech during TTS cancels current output
    - Maintains session context across turns (last intent, action count)
    - Uses streaming STT when available, falls back to batch
    - Does not block the main thread on TTS playback

    Args:
        runtime:           LiveRuntime instance (must have active session).
        stt:               STTEngine or StreamingSTT for transcription.
        audio_source:      AudioSource for mic capture.
        tts:               TTSEngine for spoken responses (optional).
        wake_word_enabled: Whether to require wake word before processing.
        wake_words:        Custom wake word set.
        tick_interval:     Seconds between ticks when idle.
    """

    def __init__(
        self,
        runtime: Any,
        stt: STTEngine | StreamingSTT,
        audio_source: AudioSource,
        tts: TTSEngine | None = None,
        wake_word_enabled: bool = False,
        wake_words: frozenset[str] | None = None,
        tick_interval: float = 0.05,
    ) -> None:
        self._runtime = runtime
        self._audio_source = audio_source
        self._wake_word_enabled = wake_word_enabled
        self._wake_words = wake_words or _DEFAULT_WAKE_WORDS
        self._tick_interval = tick_interval

        # Wrap STT if it's batch-only
        if isinstance(stt, StreamingSTT):
            self._stt: StreamingSTT = stt
        else:
            self._stt = BatchSTTAdapter(stt)

        # Wrap TTS in controller for non-blocking start/stop
        self._tts_controller: TTSController | None = None
        if tts is not None:
            self._tts_controller = TTSController(tts)

        # State machine
        self._fsm = VoiceStateMachine()

        # Session context (bound after first tick sees runtime session_id)
        self._session: VoiceSessionContext | None = None

        # Current turn state
        self._current_transcript = ""
        self._pending_response = ""

        # Threading
        self._running = False
        self._thread: threading.Thread | None = None

        # Counters
        self._processed_count = 0
        self._interrupted_count = 0
        self._error_count = 0

    # ── Properties ───────────────────────────────────────────────────

    @property
    def state(self) -> VoiceState:
        return self._fsm.state

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def processed_count(self) -> int:
        return self._processed_count

    @property
    def interrupted_count(self) -> int:
        return self._interrupted_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def session(self) -> VoiceSessionContext | None:
        return self._session

    # ── Lifecycle ────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the interruptible voice loop on a background thread.

        Raises:
            RuntimeError: If already running.
        """
        if self._running:
            raise RuntimeError("InterruptibleVoiceLoop is already running")

        self._running = True
        self._fsm.reset()
        self._thread = threading.Thread(
            target=self._loop,
            name="voice-loop-interruptible",
            daemon=True,
        )
        self._thread.start()
        _log("Interruptible voice loop started")

    def stop(self) -> None:
        """Stop the loop and clean up."""
        if not self._running:
            return

        _log("Interruptible voice loop stopping...")
        self._running = False
        self._fsm.transition(VoiceEvent.STOP)

        if self._tts_controller is not None:
            self._tts_controller.stop_speaking()

        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

        _log(
            f"Interruptible voice loop stopped. "
            f"Processed: {self._processed_count}, "
            f"Interrupted: {self._interrupted_count}, "
            f"Errors: {self._error_count}"
        )

    # ── Main Loop ────────────────────────────────────────────────────

    def _loop(self) -> None:
        """Background loop — ticks the state machine."""
        while self._running:
            try:
                self.tick()
            except Exception as exc:
                self._error_count += 1
                logger.warning("Interruptible voice loop tick error: %s", exc)
            time.sleep(self._tick_interval)

    def _ensure_session(self) -> None:
        """Bind session context to runtime's current session_id."""
        if self._session is None and hasattr(self._runtime, "session_id"):
            sid = self._runtime.session_id
            if sid:
                self._session = VoiceSessionContext(sid)

    def tick(self) -> dict[str, Any] | None:
        """Single tick of the state machine. Public for deterministic testing.

        Returns:
            Result dict from handle_input if a turn completed, else None.
        """
        self._ensure_session()
        current = self._fsm.state

        if current == VoiceState.IDLE:
            return self._tick_idle()
        elif current == VoiceState.LISTENING:
            return self._tick_listening()
        elif current == VoiceState.THINKING:
            return self._tick_thinking()
        elif current == VoiceState.SPEAKING:
            return self._tick_speaking()
        elif current == VoiceState.INTERRUPTED:
            return self._tick_interrupted()
        return None

    # ── State Handlers ───────────────────────────────────────────────

    def _reset_to_idle(self) -> None:
        """Reset FSM and STT for a clean next turn."""
        self._fsm.reset()
        self._stt.reset()
        self._current_transcript = ""

    def _tick_idle(self) -> dict[str, Any] | None:
        audio = self._audio_source.capture()
        if not audio:
            return None

        self._stt.reset()
        self._stt.push_audio_chunk(audio)
        self._current_transcript = ""
        self._fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        return None

    def _tick_listening(self) -> dict[str, Any] | None:
        # Poll STT for final transcript from the audio already pushed
        final = self._stt.poll_transcript_final()
        if final and final.strip():
            self._current_transcript = final.strip()
            self._fsm.transition(VoiceEvent.TRANSCRIPT_READY)
            return None

        # No transcript available — treat as silence (batch had insufficient data)
        self._fsm.transition(VoiceEvent.SILENCE_DETECTED)
        return None

    def _tick_thinking(self) -> dict[str, Any] | None:
        text = self._current_transcript
        if not text:
            self._reset_to_idle()
            return None

        # Wake word filter
        if self._wake_word_enabled:
            triggered, remaining = _check_wake_word(text, self._wake_words)
            if not triggered:
                self._reset_to_idle()
                return None
            text = remaining
            if not text:
                if self._tts_controller is not None:
                    self._tts_controller.start_speaking("Listening.")
                    self._fsm.transition(VoiceEvent.RESPONSE_READY)
                    return None
                self._reset_to_idle()
                return None

        # Build metadata with session context
        metadata = {"source": "voice_loop"}
        if self._session is not None:
            metadata.update(self._session.get_context_for_input())

        event = InputEvent(transport="voice", text=text, metadata=metadata)

        logger.info("[InterruptibleVoiceLoop] Processing: %s", text[:80])

        result = self._runtime.handle_input(event)
        self._processed_count += 1

        # Record turn in session
        request_type = result.get("request_type", "action")
        if self._session is not None:
            self._session.record_turn(
                transcript=text,
                response_text=result.get("intent_text", ""),
                request_type=request_type,
            )
            self._session.update_action_result(result)

        # Speak response if TTS available
        response_text = self._extract_response_text(result)
        if response_text and self._tts_controller is not None:
            self._pending_response = response_text
            self._tts_controller.start_speaking(response_text)
            self._fsm.transition(VoiceEvent.RESPONSE_READY)
        else:
            self._reset_to_idle()

        return result

    def _tick_speaking(self) -> dict[str, Any] | None:
        # Check for user interruption
        audio = self._audio_source.capture()
        if audio:
            # User is speaking while TTS is playing — interrupt
            if self._tts_controller is not None:
                self._tts_controller.stop_speaking()

            self._interrupted_count += 1

            # Record interrupted turn
            if self._session is not None:
                last_turns = self._session.turns
                if last_turns:
                    last = last_turns[-1]
                    self._session.record_turn(
                        transcript=last.transcript,
                        response_text=last.response_text,
                        request_type=last.request_type,
                        interrupted=True,
                    )

            self._stt.reset()
            self._stt.push_audio_chunk(audio)
            self._current_transcript = ""
            self._fsm.transition(VoiceEvent.USER_INTERRUPTED)
            return None

        # Check if TTS finished
        if self._tts_controller is None or not self._tts_controller.is_speaking:
            self._fsm.transition(VoiceEvent.SPEECH_FINISHED)

        return None

    def _tick_interrupted(self) -> dict[str, Any] | None:
        # Transition to listening with the audio that caused the interrupt
        audio = self._audio_source.capture()
        if audio:
            self._stt.push_audio_chunk(audio)

        self._fsm.transition(VoiceEvent.AUDIO_RECEIVED)
        return None

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_response_text(result: dict[str, Any]) -> str:
        """Extract a speakable response from lifecycle result."""
        request_type = result.get("request_type", "")
        intent = result.get("intent_text", "")

        if request_type == "open_day":
            return "Day opened."
        elif request_type == "close_day":
            return "Day closed."
        elif intent:
            short = intent[:80] + ("..." if len(intent) > 80 else "")
            return f"Done: {short}"
        return "Done."
