"""
VoiceRuntime — continuous conversational voice loop for the immersive runtime.

Manages the full cycle: mic capture → STT → live_runtime → streaming_bridge → TTS.
Supports always-on listening, wake word activation, push-to-talk, silence
detection, and mid-speech interruption.

Design rules:
- Additive only.  Removing this file leaves the platform intact.
- Best-effort.  Audio/STT failures are logged and retried; never raised.
- Non-blocking.  Voice loop runs in a dedicated daemon thread.
- Interruptible.  Speaking while the system talks cancels TTS and starts
  a new cycle.
- Composes existing substrate modules: stt_producer, voice_wake,
  media_processor, and the streaming_bridge.
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


# ─── Constants ──────────────────────────────────────────────────────────────

_DEFAULT_SILENCE_TIMEOUT_S = 1.5
_DEFAULT_SAMPLE_RATE = 16000
_DEFAULT_CHUNK_DURATION_S = 0.5


def _log(msg: str) -> None:
    print(f"[platform.eos.voice_runtime] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "vr") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Wake Modes ─────────────────────────────────────────────────────────────


class WakeMode(str, Enum):
    """How the voice runtime activates."""

    ALWAYS_ON = "always_on"
    WAKE_WORD = "wake_word"
    PUSH_TO_TALK = "push_to_talk"


# ─── Voice Runtime State ────────────────────────────────────────────────────


class VoiceLoopState(str, Enum):
    """Internal state of the voice loop."""

    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    WAITING_FOR_WAKE = "waiting_for_wake"
    STOPPED = "stopped"


# ─── STT Provider ──────────────────────────────────────────────────────────


class STTProvider(str, Enum):
    """Speech-to-text engine to use."""

    FASTER_WHISPER = "faster_whisper"
    OPENAI = "openai"
    SIMULATED = "simulated"


# ─── Runtime State Dataclass ────────────────────────────────────────────────


@dataclass
class VoiceRuntimeState:
    """Observable state of the voice runtime."""

    is_listening: bool = False
    is_speaking: bool = False
    last_utterance: Optional[str] = None
    last_response: Optional[str] = None
    wake_mode: WakeMode = WakeMode.ALWAYS_ON
    interrupted: bool = False
    loop_state: VoiceLoopState = VoiceLoopState.IDLE
    cycle_count: int = 0
    last_cycle_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "is_listening": self.is_listening,
            "is_speaking": self.is_speaking,
            "last_utterance": self.last_utterance,
            "last_response": self.last_response,
            "wake_mode": self.wake_mode.value,
            "interrupted": self.interrupted,
            "loop_state": self.loop_state.value,
            "cycle_count": self.cycle_count,
            "last_cycle_at": self.last_cycle_at,
            "error": self.error,
        }


# ─── Audio Capture ──────────────────────────────────────────────────────────


def _capture_audio_chunk(
    duration_s: float = _DEFAULT_CHUNK_DURATION_S,
    sample_rate: int = _DEFAULT_SAMPLE_RATE,
) -> Optional[bytes]:
    """Capture a short audio chunk from the default microphone.

    Returns raw PCM bytes or None if capture fails.
    """
    try:
        import numpy as np
        import sounddevice as sd

        frames = int(duration_s * sample_rate)
        audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()
        return audio.tobytes()
    except ImportError:
        return None
    except Exception as exc:
        _log(f"audio capture failed: {exc}")
        return None


def _detect_silence(audio_bytes: bytes, threshold: int = 500) -> bool:
    """Check if audio chunk is silence based on RMS amplitude."""
    if not audio_bytes:
        return True
    try:
        import numpy as np

        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        rms = np.sqrt(np.mean(audio.astype(np.float64) ** 2))
        return rms < threshold
    except ImportError:
        return False
    except Exception:
        return False


def _detect_wake_word(audio_bytes: bytes, wake_phrase: str = "hey ea") -> bool:
    """Check if audio contains the wake phrase.

    Uses faster-whisper transcription on the chunk and checks for
    the wake phrase in the output.
    """
    if not audio_bytes:
        return False
    try:
        text = _transcribe_audio(audio_bytes)
        if text and wake_phrase.lower() in text.lower():
            _log(f"wake word detected: {text!r}")
            return True
        return False
    except Exception:
        return False


# ─── Transcription ──────────────────────────────────────────────────────────


def _transcribe_audio(
    audio_bytes: bytes,
    provider: STTProvider = STTProvider.FASTER_WHISPER,
    sample_rate: int = _DEFAULT_SAMPLE_RATE,
) -> Optional[str]:
    """Transcribe raw PCM audio bytes to text.

    Uses faster-whisper by default with fallback to whisper.
    """
    if not audio_bytes:
        return None

    if provider == STTProvider.SIMULATED:
        return "(simulated transcription)"

    # Write to temp WAV for transcription
    import tempfile
    import wave

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_bytes)

    try:
        # Try faster-whisper first
        try:
            from faster_whisper import WhisperModel

            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(tmp_path, language="en")
            text = " ".join(seg.text for seg in segments).strip()
            if text:
                return text
        except ImportError:
            pass
        except Exception as exc:
            _log(f"faster-whisper failed: {exc}")

        # Fallback to whisper
        try:
            import whisper

            model = whisper.load_model("base")
            result = model.transcribe(tmp_path, language="en")
            text = result.get("text", "").strip()
            if text:
                return text
        except ImportError:
            pass
        except Exception as exc:
            _log(f"whisper fallback failed: {exc}")

        return None

    finally:
        try:
            import os

            os.unlink(tmp_path)
        except Exception:
            pass


# ─── Voice Runtime ──────────────────────────────────────────────────────────


class VoiceRuntime:
    """Continuous conversational voice loop.

    Singleton via default().  Runs the listen→transcribe→process→speak
    loop in a dedicated daemon thread.  Thread-safe.
    """

    _default: Optional["VoiceRuntime"] = None
    _default_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = VoiceRuntimeState()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Configuration
        self._wake_mode = WakeMode.ALWAYS_ON
        self._wake_phrase = "hey ea"
        self._silence_timeout_s = _DEFAULT_SILENCE_TIMEOUT_S
        self._stt_provider = STTProvider.FASTER_WHISPER
        self._sample_rate = _DEFAULT_SAMPLE_RATE

        # Callbacks
        self._on_utterance: Optional[Callable[[str], None]] = None
        self._on_response: Optional[Callable[[str], None]] = None

    # ── Singleton ────────────────────────────────────────────────────────

    @classmethod
    def default(cls) -> "VoiceRuntime":
        """Return the process-wide singleton."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down singleton for test isolation."""
        with cls._default_lock:
            if cls._default is not None:
                cls._default.stop()
            cls._default = None

    # ── Configuration ────────────────────────────────────────────────────

    def configure(
        self,
        *,
        wake_mode: Optional[WakeMode] = None,
        wake_phrase: Optional[str] = None,
        silence_timeout_s: Optional[float] = None,
        stt_provider: Optional[STTProvider] = None,
        sample_rate: Optional[int] = None,
    ) -> None:
        """Update runtime configuration.  Can be called while running."""
        with self._lock:
            if wake_mode is not None:
                self._wake_mode = wake_mode
                self._state.wake_mode = wake_mode
            if wake_phrase is not None:
                self._wake_phrase = wake_phrase
            if silence_timeout_s is not None:
                self._silence_timeout_s = silence_timeout_s
            if stt_provider is not None:
                self._stt_provider = stt_provider
            if sample_rate is not None:
                self._sample_rate = sample_rate

    def on_utterance(self, callback: Callable[[str], None]) -> None:
        """Register callback for when user speech is transcribed."""
        self._on_utterance = callback

    def on_response(self, callback: Callable[[str], None]) -> None:
        """Register callback for when EA responds."""
        self._on_response = callback

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the voice loop in a background thread."""
        with self._lock:
            if self._running:
                _log("already running")
                return

            self._stop_event.clear()
            self._running = True
            self._state.loop_state = VoiceLoopState.IDLE
            self._state.error = None

            self._thread = threading.Thread(
                target=self._voice_loop, daemon=True, name="voice-runtime"
            )
            self._thread.start()
            _log("voice runtime started")

    def stop(self) -> None:
        """Stop the voice loop."""
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            self._running = False
            self._state.loop_state = VoiceLoopState.STOPPED

        # Cancel any active TTS
        try:
            from eos_ai.platforms.eos.streaming_bridge import cancel_speech

            cancel_speech()
        except Exception:
            pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        _log("voice runtime stopped")

    @property
    def is_running(self) -> bool:
        """True if the voice loop is active."""
        return self._running

    @property
    def state(self) -> VoiceRuntimeState:
        """Current observable state."""
        return self._state

    # ── Interrupt ────────────────────────────────────────────────────────

    def interrupt(self, new_text: Optional[str] = None) -> None:
        """Interrupt current activity.

        If new_text is provided, it's processed as a new utterance.
        Otherwise just cancels current TTS.
        """
        self._state.interrupted = True

        # Cancel TTS
        try:
            from eos_ai.platforms.eos.streaming_bridge import cancel_speech

            cancel_speech()
        except Exception:
            pass

        if new_text:
            self._process_utterance(new_text)

    # ── Voice Loop ───────────────────────────────────────────────────────

    def _voice_loop(self) -> None:
        """Main voice loop.  Runs in background thread."""
        _log("voice loop thread started")

        while not self._stop_event.is_set():
            try:
                self._single_cycle()
            except Exception as exc:
                self._state.error = str(exc)
                _log(f"voice loop error: {exc}")
                # Brief pause before retry
                self._stop_event.wait(1.0)

        self._state.loop_state = VoiceLoopState.STOPPED
        _log("voice loop thread exited")

    def _single_cycle(self) -> None:
        """Execute one listen→transcribe→process→speak cycle."""
        # Phase 1: Wait for activation based on wake mode
        if self._wake_mode == WakeMode.WAKE_WORD:
            self._state.loop_state = VoiceLoopState.WAITING_FOR_WAKE
            self._state.is_listening = False
            if not self._wait_for_wake_word():
                return

        elif self._wake_mode == WakeMode.PUSH_TO_TALK:
            # In push-to-talk, we wait for external trigger
            self._state.loop_state = VoiceLoopState.WAITING_FOR_WAKE
            self._state.is_listening = False
            self._stop_event.wait(0.5)
            return

        # Phase 2: Listen and accumulate audio until silence
        self._state.loop_state = VoiceLoopState.LISTENING
        self._state.is_listening = True
        self._state.interrupted = False

        audio_chunks = self._listen_until_silence()

        if not audio_chunks or self._stop_event.is_set():
            self._state.is_listening = False
            return

        # Phase 3: Transcribe
        self._state.loop_state = VoiceLoopState.TRANSCRIBING
        self._state.is_listening = False

        all_audio = b"".join(audio_chunks)
        text = _transcribe_audio(all_audio, self._stt_provider, self._sample_rate)

        if not text or not text.strip():
            return

        _log(f"transcribed: {text!r}")
        self._state.last_utterance = text

        if self._on_utterance:
            try:
                self._on_utterance(text)
            except Exception:
                pass

        # Phase 4: Process through live_runtime
        self._process_utterance(text)

    def _wait_for_wake_word(self) -> bool:
        """Listen for the wake phrase.  Returns True when detected."""
        while not self._stop_event.is_set():
            chunk = _capture_audio_chunk(
                duration_s=_DEFAULT_CHUNK_DURATION_S,
                sample_rate=self._sample_rate,
            )
            if chunk is None:
                self._stop_event.wait(0.5)
                continue
            if _detect_wake_word(chunk, self._wake_phrase):
                return True
        return False

    def _listen_until_silence(self) -> list[bytes]:
        """Accumulate audio chunks until silence is detected."""
        chunks: list[bytes] = []
        silence_start: Optional[float] = None
        max_duration_s = 30.0
        listen_start = time.monotonic()

        while not self._stop_event.is_set():
            # Check max duration
            if time.monotonic() - listen_start > max_duration_s:
                _log("max listen duration reached")
                break

            chunk = _capture_audio_chunk(
                duration_s=_DEFAULT_CHUNK_DURATION_S,
                sample_rate=self._sample_rate,
            )
            if chunk is None:
                self._stop_event.wait(0.1)
                continue

            is_silent = _detect_silence(chunk)

            if is_silent:
                if silence_start is None:
                    silence_start = time.monotonic()
                elif time.monotonic() - silence_start >= self._silence_timeout_s:
                    # Silence timeout reached — end of utterance
                    break
            else:
                silence_start = None
                chunks.append(chunk)

            # Check for interruption while system is speaking
            if self._state.is_speaking and not is_silent:
                self._state.interrupted = True
                try:
                    from eos_ai.platforms.eos.streaming_bridge import cancel_speech

                    cancel_speech()
                except Exception:
                    pass
                self._state.is_speaking = False
                chunks.append(chunk)

        return chunks

    def _process_utterance(self, text: str) -> None:
        """Route transcribed text through live_runtime and speak the response."""
        self._state.loop_state = VoiceLoopState.PROCESSING

        try:
            from eos_ai.platforms.eos.live_runtime import handle_live_user_utterance

            result = handle_live_user_utterance(text)
            response_text = result.spoken_text

        except Exception as exc:
            _log(f"live_runtime failed: {exc}")
            response_text = "I had trouble processing that. Could you try again?"

        self._state.last_response = response_text
        self._state.cycle_count += 1
        self._state.last_cycle_at = _utcnow()

        if self._on_response:
            try:
                self._on_response(response_text)
            except Exception:
                pass

        # Phase 5: Speak the response via streaming bridge
        if response_text:
            self._state.loop_state = VoiceLoopState.SPEAKING
            self._state.is_speaking = True

            try:
                from eos_ai.platforms.eos.streaming_bridge import (
                    StreamEventType,
                    stream_event,
                )

                stream_event(
                    StreamEventType.INFO,
                    response_text,
                    source="voice_runtime",
                    speak=True,
                )
            except Exception as exc:
                _log(f"streaming bridge speak failed: {exc}")

            self._state.is_speaking = False

        self._state.loop_state = VoiceLoopState.IDLE


# ─── Module-Level API ───────────────────────────────────────────────────────


def get_voice_runtime() -> VoiceRuntime:
    """Return the singleton VoiceRuntime."""
    return VoiceRuntime.default()


def start_voice_runtime(
    *,
    wake_mode: WakeMode = WakeMode.ALWAYS_ON,
    wake_phrase: str = "hey ea",
) -> VoiceRuntime:
    """Configure and start the voice runtime.  Returns the runtime."""
    rt = VoiceRuntime.default()
    rt.configure(wake_mode=wake_mode, wake_phrase=wake_phrase)
    rt.start()
    return rt


def stop_voice_runtime() -> None:
    """Stop the voice runtime."""
    VoiceRuntime.default().stop()


def get_voice_runtime_state() -> dict:
    """Return the current voice runtime state as a dict."""
    return VoiceRuntime.default().state.to_dict()


def interrupt_voice_runtime(new_text: Optional[str] = None) -> None:
    """Interrupt current voice activity."""
    VoiceRuntime.default().interrupt(new_text)


# ─── Exports ────────────────────────────────────────────────────────────────

__all__ = [
    "WakeMode",
    "VoiceLoopState",
    "STTProvider",
    "VoiceRuntimeState",
    "VoiceRuntime",
    "get_voice_runtime",
    "start_voice_runtime",
    "stop_voice_runtime",
    "get_voice_runtime_state",
    "interrupt_voice_runtime",
]
