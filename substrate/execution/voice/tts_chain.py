"""TTS provider chain — free-first, graceful fallback, always produces audio.

The reply-voice quality tier, in order:

  1. Kokoro (GPU, best quality) — an OpenAI-compatible ``/v1/audio/speech`` server,
     typically the executor node. Reached via ``KOKORO_TTS_URL`` (env). FREE.
  2. OpenAI TTS (cloud, high quality) — only if ``OPENAI_API_KEY`` is set and the
     account has quota. NOT free; used only as a middle tier when Kokoro is
     unreachable.
  3. espeak (local, always available) — the deterministic floor. Robotic but never
     fails, so the voice path ALWAYS produces audio (Deterministic-First Principle).

Returns WAV bytes (iOS Safari plays WAV natively). Every tier is bounded and
degrades to the next on any error — the caller always gets audio.

Config (no hardcoded hosts — Device Naming + Instance Context laws):
  KOKORO_TTS_URL   e.g. http://<executor>:5000  (base; /v1/audio/speech appended)
  KOKORO_TTS_VOICE default af_bella
  OPENAI_API_KEY   enables the OpenAI middle tier
  OPENAI_TTS_VOICE default onyx
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_KOKORO_TIMEOUT = 12
_OPENAI_TIMEOUT = 20


def _kokoro_tts(text: str) -> bytes | None:
    """Best tier: Kokoro OpenAI-compatible speech server (GPU executor). FREE."""
    base = os.environ.get("KOKORO_TTS_URL", "").strip().rstrip("/")
    if not base:
        return None
    voice = os.environ.get("KOKORO_TTS_VOICE", "af_bella")
    try:
        import json
        import urllib.request

        req = urllib.request.Request(
            f"{base}/v1/audio/speech",
            data=json.dumps(
                {
                    "model": "kokoro",
                    "input": text,
                    "voice": voice,
                    "response_format": "wav",
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_KOKORO_TIMEOUT) as r:
            data = r.read()
        if data and len(data) > 44:  # > bare WAV header
            logger.info("[TTS] kokoro synthesized %d bytes", len(data))
            return data
        return None
    except Exception as exc:
        logger.debug("[TTS] kokoro unavailable: %s", exc)
        return None


def _openai_tts(text: str) -> bytes | None:
    """Middle tier: OpenAI TTS. Only if OPENAI_API_KEY set + account has quota."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    voice = os.environ.get("OPENAI_TTS_VOICE", "onyx")
    try:
        import json
        import urllib.request

        req = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=json.dumps(
                {"model": "tts-1", "input": text, "voice": voice, "response_format": "wav"}
            ).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_OPENAI_TIMEOUT) as r:
            data = r.read()
        if data and len(data) > 44:
            logger.info("[TTS] openai synthesized %d bytes", len(data))
            return data
        return None
    except Exception as exc:
        # 429 (quota) / auth / network — fall through to espeak, never raise.
        logger.debug("[TTS] openai unavailable: %s", exc)
        return None


def _espeak_tts(text: str) -> bytes | None:
    """Deterministic floor: local espeak via the warm VoiceEngine. Always works."""
    try:
        from pathlib import Path

        from substrate.execution.voice.warm_engine import get_warm_engine

        wav_path = get_warm_engine().speak(text)
        if not wav_path:
            return None
        p = Path(wav_path)
        data = p.read_bytes()
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
        if data:
            logger.info("[TTS] espeak synthesized %d bytes", len(data))
            return data
        return None
    except Exception as exc:
        logger.warning("[TTS] espeak failed: %s", exc)
        return None


def synthesize(text: str) -> tuple[bytes, str] | None:
    """Synthesize ``text`` to WAV bytes through the tiered chain.

    Returns ``(wav_bytes, tier)`` where tier is 'kokoro'|'openai'|'espeak', or
    None only if EVERY tier failed (espeak missing) — a near-impossible floor.
    """
    text = (text or "").strip()
    if not text:
        return None
    # Bound what any provider receives (long replies are truncated for speech).
    text = text[:2000]

    for tier, fn in (("kokoro", _kokoro_tts), ("openai", _openai_tts), ("espeak", _espeak_tts)):
        data = fn(text)
        if data:
            return data, tier
    return None
