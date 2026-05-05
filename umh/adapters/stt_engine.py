"""Speech-to-text engine — local transcription backends.

Provides a pluggable STT interface with two implementations:

    FasterWhisperSTT  — production backend using faster-whisper (local)
    PlaceholderSTT    — fallback that returns empty string (no-op)

Design rules:
- NO external API calls — all transcription is local
- Lazy model loading — zero cost until first transcribe() call
- Fail gracefully — never raise, return empty string on error
- Thread-safe — safe to call from voice loop thread

Public API:
    STTEngine (Protocol)     — structural type for STT backends
    FasterWhisperSTT         — production backend
    PlaceholderSTT           — no-op fallback
    create_stt_engine()      — factory that picks best available backend
"""

from __future__ import annotations

import io
import logging
import sys
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

_LOG_PREFIX = "[adapters.stt_engine]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ── Protocol ─────────────────────────────────────────────────────────


@runtime_checkable
class STTEngine(Protocol):
    """Structural type for speech-to-text backends.

    Any class with a matching transcribe() method satisfies this protocol.
    """

    def transcribe(self, audio: bytes) -> str:
        """Transcribe raw audio bytes to text.

        Args:
            audio: Raw audio data (WAV format, 16kHz mono recommended).

        Returns:
            Transcribed text, or empty string on failure/silence.
        """
        ...


# ── Faster Whisper Backend ───────────────────────────────────────────


class FasterWhisperSTT:
    """Local STT using faster-whisper with lazy model loading.

    Uses the 'tiny' model by default for low latency on CPU.
    Model is loaded on first transcribe() call, not at init time.

    Args:
        model_size: Whisper model size (tiny, base, small, medium, large-v3).
        device:     Compute device (cpu, cuda, auto).
        language:   Language hint for transcription (None = auto-detect).
    """

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        language: str | None = "en",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._language = language
        self._model = None

    def _ensure_model(self) -> bool:
        """Lazy-load the whisper model. Returns True if model is ready."""
        if self._model is not None:
            return True
        try:
            from faster_whisper import WhisperModel

            _log(f"Loading faster-whisper model: {self._model_size}")
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type="int8",
            )
            _log(f"Model loaded: {self._model_size} on {self._device}")
            return True
        except Exception as exc:
            _log(f"Failed to load faster-whisper model: {exc}")
            return False

    def transcribe(self, audio: bytes) -> str:
        """Transcribe raw audio bytes using faster-whisper.

        Args:
            audio: Raw audio data in WAV format.

        Returns:
            Transcribed text, or empty string on failure/silence.
        """
        if not audio:
            return ""

        if not self._ensure_model():
            return ""

        try:
            # faster-whisper accepts file path or BinaryIO
            # Write to temp file for compatibility
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                tmp.write(audio)
                tmp.flush()

                segments, info = self._model.transcribe(
                    tmp.name,
                    language=self._language,
                    beam_size=1,
                    vad_filter=True,
                    without_timestamps=True,
                )

                # Consume generator and join segments
                text_parts = [seg.text.strip() for seg in segments]
                result = " ".join(part for part in text_parts if part)

            return result

        except Exception as exc:
            logger.warning("STT transcription failed: %s", exc)
            return ""


# ── Placeholder Backend ──────────────────────────────────────────────


class PlaceholderSTT:
    """No-op STT backend that always returns empty string.

    Used when no real STT engine is available. Logs a warning on first use.
    """

    def __init__(self) -> None:
        self._warned = False

    def transcribe(self, audio: bytes) -> str:
        """Always returns empty string."""
        if not self._warned:
            _log("PlaceholderSTT active — no transcription available")
            self._warned = True
        return ""


# ── Factory ──────────────────────────────────────────────────────────


def create_stt_engine(
    model_size: str = "tiny",
    device: str = "cpu",
    language: str | None = "en",
) -> STTEngine:
    """Create the best available STT engine.

    Tries faster-whisper first, falls back to PlaceholderSTT.

    Returns:
        An STTEngine instance ready for use.
    """
    try:
        import faster_whisper  # noqa: F401

        _log(f"faster-whisper available — using FasterWhisperSTT ({model_size})")
        return FasterWhisperSTT(
            model_size=model_size,
            device=device,
            language=language,
        )
    except ImportError:
        _log("faster-whisper not installed — using PlaceholderSTT")
        return PlaceholderSTT()
