"""Voice wrapper — persona voice + cloned voice (XTTS v2) + TTS fallback chain."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


class VoiceOutput:
    """Wraps substrate VoiceEngine for the workstation surface.

    Two voice profiles:
      persona_voice — AI's own voice (Coqui TTS), used for operator conversation
      cloned_voice  — operator's cloned voice (XTTS v2), used when AI speaks AS the operator
    """

    def __init__(self, text_only: bool = False) -> None:
        self._text_only = text_only
        self._engine: Any = None
        self._tts_available = False

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

    def speak(self, text: str, voice_type: str = "persona") -> None:
        if self._text_only:
            return

        engine = self._ensure_engine()
        if engine is None:
            return

        try:
            engine.speak(text)
        except Exception as exc:
            logger.debug("TTS failed, falling back to text: %s", exc)

    def speak_and_print(self, text: str) -> None:
        print(text)
        self.speak(text)

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
        except Exception:
            return "conversation"

    def should_respond(self, text: str) -> tuple[bool, str]:
        engine = self._ensure_engine()
        if engine is None:
            return True, "text_mode"
        try:
            return engine.should_respond(text)
        except Exception:
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
    print()
    print("Voice Setup")
    print("═" * 40)
    print()
    print("Voice cloning (XTTS v2) is not yet implemented.")
    print("This will be available in Sprint 3.")
    print()
    print("Voice cloning creates a reference of YOUR voice")
    print("for the AI to use when speaking to OTHER PEOPLE")
    print("on your behalf (calls, meetings, outreach).")
    print()
    print("The AI uses its own persona voice when talking to you.")
    print()
    return 0
