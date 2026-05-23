"""
Voice-first response orchestration.

Inverts the default text-first flow: voice channel responses are SPOKEN
first, with text appearing as a transcript/subtitle afterward. Adds quick
audio acknowledgments to eliminate dead air while the LLM generates.

Design rules
------------
1. Never raises. Every public function returns a result dict.
2. Reuses VoiceEngine.speak() for TTS — no parallel pipeline.
3. Acknowledgment is a pre-generated WAV played instantly (no LLM call).
4. Voice-optimized prompting strips markdown, forces concise spoken style.
5. Falls back to text-only if voice playback fails at any point.
"""

from __future__ import annotations

import asyncio
import os
import random
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


# ─── Config ──────────────────────────────────────────────────────────────────

# Where pre-generated acknowledgment WAVs live (created on first use)
_ACK_DIR = os.path.join(_REPO, "data", "voice_acks")

# Max response length for voice (shorter than text — spoken word is slower)
VOICE_MAX_CHARS = 400

# Voice-optimized system prompt injected when responding in voice mode
VOICE_SYSTEM_SUFFIX = (
    "\n\nYou are responding via VOICE in a Discord voice channel. "
    "The user is LISTENING, not reading. Rules for this reply:\n"
    "- Maximum 2-3 sentences. Be direct.\n"
    "- No markdown, no bullets, no headers, no code blocks.\n"
    "- No emojis or special characters — they sound wrong in TTS.\n"
    "- Use natural spoken English. Contractions are good.\n"
    "- Never start with 'Sure!' or 'Of course!' — just answer.\n"
    "- If the answer is complex, give the key point and offer "
    "to elaborate in text.\n"
    "- Numbers: say 'ten thousand' not '10,000'.\n"
)

# Quick verbal acknowledgments — spoken before LLM response generates
_ACK_PHRASES = [
    "On it.",
    "Let me check.",
    "One sec.",
    "Looking into it.",
    "Got it.",
    "Checking.",
]

# Phrases that don't need an ack (greetings, short confirmations)
_NO_ACK_PATTERNS = {
    "hey",
    "hi",
    "hello",
    "yo",
    "sup",
    "what's up",
    "morning",
    "yes",
    "no",
    "yeah",
    "nah",
    "ok",
    "okay",
    "sure",
    "thanks",
    "thank you",
    "bye",
    "later",
    "good night",
    "night",
}


def _log(msg: str) -> None:
    print(f"[voice_first] {msg}")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Acknowledgment WAV generation ──────────────────────────────────────────


def _ensure_ack_dir() -> str:
    os.makedirs(_ACK_DIR, exist_ok=True)
    return _ACK_DIR


def _generate_ack_wav(phrase: str, output_path: str) -> bool:
    """Generate a WAV file from a short phrase using espeak."""
    try:
        result = subprocess.run(
            ["espeak", "-s", "160", "-w", output_path, phrase],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0 and Path(output_path).exists()
    except Exception:
        return False


def ensure_ack_wavs() -> list[str]:
    """Pre-generate acknowledgment WAVs. Returns list of available paths."""
    ack_dir = _ensure_ack_dir()
    paths = []
    for phrase in _ACK_PHRASES:
        slug = phrase.lower().replace(" ", "_").replace(".", "")
        wav_path = os.path.join(ack_dir, f"ack_{slug}.wav")
        if not os.path.exists(wav_path):
            if _generate_ack_wav(phrase, wav_path):
                _log(f"generated ack: {wav_path}")
            else:
                continue
        paths.append(wav_path)
    return paths


def pick_ack_wav() -> Optional[str]:
    """Return a random acknowledgment WAV path, or None if unavailable."""
    paths = ensure_ack_wavs()
    return random.choice(paths) if paths else None


def needs_ack(utterance: str) -> bool:
    """Return True if the utterance warrants an acknowledgment before response."""
    normalized = utterance.strip().lower().rstrip("!?.,'")
    if normalized in _NO_ACK_PATTERNS:
        return False
    if len(utterance.split()) < 3:
        return False
    return True


# ─── Voice-optimized prompt construction ────────────────────────────────────


def voice_system_prompt(base_system: str) -> str:
    """Append voice mode constraints to an existing system prompt."""
    return base_system.rstrip() + VOICE_SYSTEM_SUFFIX


def truncate_for_voice(text: str, max_chars: int = VOICE_MAX_CHARS) -> str:
    """Truncate response to voice-appropriate length at sentence boundary."""
    if not text or len(text) <= max_chars:
        return text

    # Try to cut at sentence boundary
    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    last_question = truncated.rfind("?")
    last_exclaim = truncated.rfind("!")
    best_cut = max(last_period, last_question, last_exclaim)

    if best_cut > max_chars // 3:
        return truncated[: best_cut + 1].strip()

    return truncated.rstrip() + "..."


def strip_markdown(text: str) -> str:
    """Remove markdown formatting that sounds wrong when spoken."""
    import re

    # Headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Bold/italic
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # Code blocks
    text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Bullet points → natural list
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    # Numbered lists → natural list
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Links
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Multiple newlines → single space
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\n", " ", text)
    # Multiple spaces
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


def prepare_voice_response(raw_response: str) -> str:
    """Full pipeline: sanitize → strip markdown → truncate for voice."""
    from substrate.execution.transport.tts_sanitize import sanitize_tts_reply

    sanitized = sanitize_tts_reply(raw_response, max_chars=VOICE_MAX_CHARS + 200)
    cleaned = strip_markdown(sanitized)
    return truncate_for_voice(cleaned)


# ─── Voice-first response orchestrator ──────────────────────────────────────


@dataclass
class VoiceFirstResult:
    """Result of a voice-first response attempt."""

    spoke: bool = False
    ack_played: bool = False
    text_sent: bool = False
    spoken_text: str = ""
    display_text: str = ""
    error: Optional[str] = None
    timing: dict[str, str] = field(default_factory=dict)


async def play_audio_on_vc(
    vc: Any,
    audio_path: str,
    *,
    wait: bool = True,
) -> bool:
    """Play a WAV/audio file on a discord.VoiceClient. Returns success."""
    try:
        import discord
    except ImportError:
        return False

    if not vc or not hasattr(vc, "is_connected") or not vc.is_connected():
        return False

    if vc.is_playing():
        if wait:
            for _ in range(30):  # max 9s wait
                await asyncio.sleep(0.3)
                if not vc.is_playing():
                    break
            else:
                return False
        else:
            return False

    if not os.path.exists(audio_path):
        return False

    try:
        vc.play(discord.FFmpegPCMAudio(audio_path))
        return True
    except Exception as e:
        _log(f"playback failed: {e}")
        return False


async def play_ack(vc: Any) -> bool:
    """Play a quick acknowledgment sound on the voice client."""
    wav = pick_ack_wav()
    if not wav:
        return False
    return await play_audio_on_vc(vc, wav, wait=False)


async def speak_response(
    vc: Any,
    text: str,
    *,
    voice_engine: Any = None,
) -> bool:
    """Generate TTS and play on voice client. Returns success."""
    if not text:
        return False

    loop = asyncio.get_event_loop()

    if voice_engine is None:
        try:
            from substrate.execution.voice.voice_engine import VoiceEngine

            voice_engine = VoiceEngine()
        except ImportError:
            _log("VoiceEngine not importable")
            return False

    audio_path = await loop.run_in_executor(None, voice_engine.speak, text)
    if not audio_path or not os.path.exists(audio_path):
        _log("TTS produced no audio")
        return False

    played = await play_audio_on_vc(vc, audio_path, wait=True)

    if played:
        # Wait for playback to finish before cleanup
        for _ in range(100):  # max 30s
            await asyncio.sleep(0.3)
            if not vc.is_playing():
                break

    try:
        os.remove(audio_path)
    except Exception:
        pass

    return played


async def voice_first_respond(
    vc: Any,
    utterance: str,
    response: str,
    *,
    voice_engine: Any = None,
    text_channel: Any = None,
    user_name: str = "You",
    ai_name: str = "DEX",
    ack_already_played: bool = False,
) -> VoiceFirstResult:
    """
    Voice-first response: speak → text transcript.

    Ack is expected to be played earlier (before LLM call) by the caller.
    Set ack_already_played=False to have this function play it instead.
    """
    result = VoiceFirstResult()
    result.timing["start"] = _utcnow()

    # 1. Quick ack if not already played by caller
    if not ack_already_played and needs_ack(utterance):
        result.ack_played = await play_ack(vc)
        result.timing["ack_done"] = _utcnow()
    else:
        result.ack_played = ack_already_played

    # 2. Prepare voice-optimized response
    voice_text = prepare_voice_response(response)
    result.spoken_text = voice_text
    result.display_text = response

    # 3. SPEAK FIRST
    if voice_text:
        result.spoke = await speak_response(vc, voice_text, voice_engine=voice_engine)
        result.timing["speak_done"] = _utcnow()

    # 4. Text as transcript/subtitle AFTER voice
    if text_channel and response:
        try:
            from substrate.execution.transport.session_discord_bridge import (
                send_reply as _send_reply,
            )

            msg = f"\U0001f3a4 **{user_name}:** {utterance}\n**{ai_name}:** {response}"
            await _send_reply(text_channel, msg)
            result.text_sent = True
        except Exception as e:
            result.error = f"text send failed: {e}"

    result.timing["end"] = _utcnow()
    return result
