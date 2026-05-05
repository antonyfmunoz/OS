"""Text-to-speech engine — local TTS backends.

Provides a pluggable TTS interface with two implementations:

    Pyttsx3TTS      — production backend using pyttsx3 (offline, threaded)
    PlaceholderTTS  — fallback that logs text instead of speaking

Design rules:
- Non-blocking — speech runs on a background daemon thread
- Fail silently — never raise into caller
- Thread-safe — queue-based dispatch
- NO external API calls — local synthesis only

Public API:
    TTSEngine (Protocol)    — structural type for TTS backends
    Pyttsx3TTS              — production backend
    PlaceholderTTS          — no-op fallback
    create_tts_engine()     — factory that picks best available backend
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

_LOG_PREFIX = "[adapters.tts_engine]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ── Protocol ─────────────────────────────────────────────────────────


@runtime_checkable
class TTSEngine(Protocol):
    """Structural type for text-to-speech backends.

    Any class with a matching speak() method satisfies this protocol.
    """

    def speak(self, text: str) -> None:
        """Speak the given text.

        Must be non-blocking — returns immediately.
        Must not raise on failure.

        Args:
            text: Text to synthesize and play.
        """
        ...

    def shutdown(self) -> None:
        """Shut down the TTS engine and release resources."""
        ...


# ── pyttsx3 Backend ─────────────────────────────────────────────────

_SENTINEL = None  # Poison pill for the speech queue


class Pyttsx3TTS:
    """Local TTS using pyttsx3 with non-blocking threaded dispatch.

    Speech requests are queued and processed sequentially on a daemon
    thread. The pyttsx3 engine is initialized on the worker thread
    (required by pyttsx3 — engine must be used from the thread that
    created it).

    Args:
        rate:   Speech rate in words per minute (default 175).
        volume: Volume level 0.0 to 1.0 (default 0.9).
    """

    def __init__(self, rate: int = 175, volume: float = 0.9) -> None:
        self._rate = rate
        self._volume = volume
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._running = True
        self._thread = threading.Thread(
            target=self._worker,
            name="tts-worker",
            daemon=True,
        )
        self._thread.start()

    def _worker(self) -> None:
        """Background worker — processes speech queue sequentially."""
        engine = None
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)
            _log(f"pyttsx3 engine initialized (rate={self._rate})")
        except Exception as exc:
            _log(f"pyttsx3 init failed: {exc}")
            # Drain queue without speaking
            while self._running:
                try:
                    item = self._queue.get(timeout=1.0)
                    if item is _SENTINEL:
                        break
                except queue.Empty:
                    continue
            return

        while self._running:
            try:
                text = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if text is _SENTINEL:
                break

            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:
                logger.warning("TTS speak failed: %s", exc)

        try:
            engine.stop()
        except Exception:
            pass

    def speak(self, text: str) -> None:
        """Queue text for speech. Returns immediately.

        Args:
            text: Text to synthesize. Empty/whitespace-only is ignored.
        """
        if not text or not text.strip():
            return
        if not self._running:
            return
        self._queue.put(text.strip())

    def shutdown(self) -> None:
        """Stop the TTS worker thread."""
        self._running = False
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=5.0)
        _log("pyttsx3 TTS shutdown complete")


# ── Placeholder Backend ──────────────────────────────────────────────


class PlaceholderTTS:
    """No-op TTS backend that logs text instead of speaking.

    Used when no real TTS engine is available, or for testing.
    """

    def __init__(self) -> None:
        self._warned = False

    def speak(self, text: str) -> None:
        """Log text instead of speaking."""
        if not self._warned:
            _log("PlaceholderTTS active — logging instead of speaking")
            self._warned = True
        if text and text.strip():
            logger.info("[PlaceholderTTS] Would speak: %s", text.strip()[:100])

    def shutdown(self) -> None:
        """No-op shutdown."""
        pass


# ── Factory ──────────────────────────────────────────────────────────


def create_tts_engine(
    rate: int = 175,
    volume: float = 0.9,
) -> TTSEngine:
    """Create the best available TTS engine.

    Tries pyttsx3 first, falls back to PlaceholderTTS.

    Returns:
        A TTSEngine instance ready for use.
    """
    try:
        import pyttsx3  # noqa: F401

        _log("pyttsx3 available — using Pyttsx3TTS")
        return Pyttsx3TTS(rate=rate, volume=volume)
    except ImportError:
        _log("pyttsx3 not installed — using PlaceholderTTS")
        return PlaceholderTTS()
