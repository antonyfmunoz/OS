"""Voice wrapper — persona voice + streaming TTS + interrupt support.

Two voice profiles:
  persona_voice — AI's own voice (Coqui TTS), used for operator conversation
  cloned_voice  — operator's cloned voice (XTTS v2), used when AI speaks AS the operator

Streaming TTS: splits response into sentences and speaks them one by one.
Interrupt: if the mic detects speech during TTS playback, stop immediately.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import threading
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class VoiceOutput:
    """Wraps substrate VoiceEngine for the workstation surface."""

    def __init__(self, text_only: bool = False) -> None:
        self._text_only = text_only
        self._engine: Any = None
        self._tts_available = False
        self._speaking = False
        self._interrupted = False
        self._playback_process: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()

    def _ensure_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        if self._text_only:
            return None
        try:
            from substrate.execution.voice.voice_engine import VoiceEngine

            self._engine = VoiceEngine()
            self._tts_available = True
            return self._engine
        except ImportError:
            logger.debug("VoiceEngine not available — text-only mode")
            return None

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def interrupt(self) -> None:
        """Stop any in-progress TTS playback immediately."""
        with self._lock:
            self._interrupted = True
            if self._playback_process is not None:
                try:
                    self._playback_process.terminate()
                except Exception as exc:
                    logger.debug("Playback process terminate failed: %s", exc)
                self._playback_process = None

    def speak(self, text: str, voice_type: str = "persona") -> None:
        if self._text_only or not text:
            return
        engine = self._ensure_engine()
        if engine is None:
            return
        self._speaking = True
        self._interrupted = False
        try:
            engine.speak(text)
        except Exception as exc:
            logger.debug("TTS failed: %s", exc)
            print(f"  [TTS unavailable: {exc}]")
        finally:
            self._speaking = False

    def speak_streaming(self, text: str, voice_type: str = "persona") -> None:
        """Speak text sentence-by-sentence, checking for interrupts between sentences."""
        if self._text_only or not text:
            return

        engine = self._ensure_engine()
        if engine is None:
            return

        sentences = _SENTENCE_SPLIT.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return

        self._speaking = True
        self._interrupted = False

        try:
            for i, sentence in enumerate(sentences):
                if self._interrupted:
                    logger.debug(
                        "TTS interrupted after %d/%d sentences",
                        i,
                        len(sentences),
                    )
                    break
                try:
                    engine.speak(sentence)
                except Exception as exc:
                    logger.debug("TTS sentence failed: %s", exc)
                    print(f"  [TTS unavailable: {exc}]")
                    break
        finally:
            self._speaking = False
            self._interrupted = False

    def speak_and_print(self, text: str) -> None:
        print(text)
        self.speak_streaming(text)

    @property
    def tts_available(self) -> bool:
        self._ensure_engine()
        return self._tts_available

    def classify_speech(self, text: str) -> str:
        engine = self._ensure_engine()
        if engine is None or not hasattr(engine, "intelligent"):
            return "conversation"
        try:
            return engine.intelligent.classify_speech(text)
        except Exception as exc:
            logger.debug("Speech classification failed: %s", exc)
            return "conversation"

    def should_respond(self, text: str) -> tuple[bool, str]:
        engine = self._ensure_engine()
        if engine is None:
            return True, "text_mode"
        try:
            return engine.should_respond(text)
        except Exception as exc:
            logger.debug("should_respond check failed: %s", exc)
            return True, "fallback"

    def route_query(self, text: str) -> str:
        engine = self._ensure_engine()
        if engine is None:
            return _deterministic_response(text)
        try:
            return engine.route_query(text)
        except Exception as exc:
            logger.debug("Query routing failed: %s", exc)
            return _deterministic_response(text)


def _deterministic_response(text: str) -> str:
    text_lower = text.strip().lower()
    if text_lower in ("hello", "hi", "hey"):
        return "Hello. How can I help?"
    if text_lower in ("thanks", "thank you"):
        return "You're welcome."
    if "?" in text:
        return "I'll need an LLM connection to answer that. Check `umh diag` for provider status."
    return "Acknowledged."


def run_voice_setup() -> int:
    """Redirect to the full voice setup flow."""
    from umh.voice_setup import run_voice_setup_flow

    return run_voice_setup_flow()
