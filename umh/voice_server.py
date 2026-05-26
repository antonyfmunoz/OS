#!/usr/bin/env python3
"""Cockpit Voice Server — real-time voice bridge for DEX conversations.

Listens on ws://0.0.0.0:8095/voice.

Features:
  - Groq Whisper STT with faster-whisper fallback
  - Kokoro TTS on Beast (GPU) with espeak fallback
  - Rolling 10-exchange conversation memory per session
  - Instant ack phrases to eliminate dead air
  - Always-on listening with silence-based turn detection

Protocol:
  Browser -> Server (JSON):
    {"type": "mic_start"}              start always-on voice session
    {"type": "mic_stop"}               stop session
  Browser -> Server (binary):
    raw PCM16 audio chunks at 16kHz
  Server -> Browser (JSON):
    {"type": "vad_status", "active": bool}
    {"type": "audio_level", "level": float}
    {"type": "transcript", "text": str, "final": bool}
    {"type": "tts_status", "speaking": bool}
    {"type": "voice_response", "text": str, "spoken_text": str, "classification": str}
  Server -> Browser (binary):
    WAV/audio bytes for TTS playback
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import random
import struct
import subprocess
import sys
import tempfile
import time
import wave
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv("/opt/OS/services/.env")
load_dotenv("/opt/OS/runtime/.env", override=True)

try:
    import websockets
    import websockets.server
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets>=13.0"])
    import websockets
    import websockets.server

logging.basicConfig(
    level=logging.INFO,
    format="[voice] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("voice_server")

HOST = os.getenv("VOICE_SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("VOICE_SERVER_PORT", "8095"))
SAMPLE_RATE = 16000
MIN_AUDIO_BYTES = int(SAMPLE_RATE * 2 * 0.3)

# Always-on listening thresholds
SILENCE_END_UTTERANCE_S = 1.8   # silence = user finished talking
SILENCE_RESET_CONTEXT_S = 8.0   # long silence = topic change
SPEECH_LEVEL_THRESHOLD = 0.02   # below this = silence

# Kokoro TTS on Beast via Tailscale
KOKORO_URL = os.getenv("KOKORO_TTS_URL", "http://100.74.199.102:8880")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "am_adam")

# Ack phrases — spoken instantly while LLM generates
_ACK_PHRASES = [
    "On it.",
    "Let me check.",
    "One sec.",
    "Looking into it.",
    "Got it.",
    "Checking.",
]
_NO_ACK_PATTERNS = {
    "hey", "hi", "hello", "yo", "sup", "morning",
    "yes", "no", "yeah", "nah", "ok", "thanks", "bye",
}


# --- STT ---

def _transcribe_groq(audio_path: str) -> str:
    try:
        from groq import Groq as GroqClient
        key = os.getenv("GROQ_API_KEY")
        if not key:
            return ""
        client = GroqClient(api_key=key)
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo", file=f, language="en",
            )
        text = result.text.strip()
        if text:
            log.info("STT (groq): %s", text[:80])
        return text
    except Exception as e:
        log.warning("Groq STT failed: %s", e)
        return ""


def _transcribe_local(audio_path: str) -> str:
    try:
        from substrate.execution.voice.voice_engine import VoiceEngine
        engine = VoiceEngine()
        return engine.intelligent.transcribe_fast(audio_path)
    except Exception as e:
        log.warning("Local STT failed: %s", e)
        return ""


def transcribe(audio_path: str) -> str:
    text = _transcribe_groq(audio_path)
    if text:
        return text
    return _transcribe_local(audio_path)


# --- Classification ---

def classify(text: str) -> tuple:
    try:
        from substrate.execution.voice.voice_engine import VoiceEngine
        engine = VoiceEngine()
        return engine.should_respond(text)
    except Exception:
        return True, "conversation"


# --- Conversation memory ---

class ConversationMemory:
    """Rolling conversation context for voice sessions."""

    def __init__(self, max_exchanges: int = 10):
        self.exchanges = deque(maxlen=max_exchanges)
        self.last_activity = time.time()

    def add(self, role: str, text: str) -> None:
        self.exchanges.append({"role": role, "text": text, "ts": time.time()})
        self.last_activity = time.time()

    def check_reset(self) -> None:
        elapsed = time.time() - self.last_activity
        if elapsed > SILENCE_RESET_CONTEXT_S and self.exchanges:
            log.info("Context reset after %.0fs silence", elapsed)
            self.exchanges.clear()

    def build_prompt(self, new_utterance: str) -> str:
        from substrate.execution.bridge.voice_first import VOICE_SYSTEM_SUFFIX

        parts = []
        for ex in self.exchanges:
            prefix = "User" if ex["role"] == "user" else "DEX"
            parts.append("%s: %s" % (prefix, ex["text"]))
        parts.append("User: %s" % new_utterance)

        conversation = "\n".join(parts)
        return conversation + VOICE_SYSTEM_SUFFIX


# --- LLM response ---

def get_response(prompt: str) -> tuple:
    """Returns (raw_response, spoken_text)."""
    from substrate.execution.bridge.voice_first import prepare_voice_response

    raw = ""
    try:
        from adapters.models.model_router import call_with_fallback
        result = call_with_fallback(prompt=prompt, task_type="conversation")
        if result:
            raw = str(result) if not isinstance(result, str) else result
    except Exception as e:
        log.warning("model_router failed: %s", e)

    if not raw:
        try:
            from substrate.execution.voice.voice_engine import VoiceEngine
            engine = VoiceEngine()
            raw = engine.query_local(prompt)
        except Exception as e:
            log.warning("Local LLM fallback failed: %s", e)

    if not raw:
        raw = "I couldn't process that right now."

    spoken = prepare_voice_response(raw)
    return raw, spoken


# --- TTS: Kokoro (Beast GPU) with espeak fallback ---

def _tts_kokoro(text: str) -> bytes:
    """Call Kokoro-FastAPI on Beast. Returns audio bytes or empty."""
    try:
        import urllib.request
        url = "%s/v1/audio/speech" % KOKORO_URL
        payload = json.dumps({
            "model": "kokoro",
            "input": text[:500],
            "voice": KOKORO_VOICE,
            "response_format": "wav",
        }).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            if len(data) > 100:
                log.info("TTS (kokoro): %d bytes", len(data))
                return data
    except Exception as e:
        log.warning("Kokoro TTS failed: %s", e)
    return b""


def _tts_espeak(text: str) -> bytes:
    """Fallback TTS via espeak."""
    try:
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="voice_tts_")
        os.close(fd)
        result = subprocess.run(
            ["espeak", "-s", "160", "-p", "40", "-w", path, text[:500]],
            capture_output=True, timeout=15,
        )
        if result.returncode == 0 and os.path.exists(path):
            with open(path, "rb") as f:
                data = f.read()
            os.unlink(path)
            return data
    except Exception as e:
        log.warning("espeak TTS failed: %s", e)
    return b""


def generate_tts(text: str) -> bytes:
    data = _tts_kokoro(text)
    if data:
        return data
    return _tts_espeak(text)


def generate_ack() -> bytes:
    """Generate a quick ack phrase audio."""
    phrase = random.choice(_ACK_PHRASES)
    return generate_tts(phrase)


def needs_ack(text: str) -> bool:
    """Short greetings and confirmations don't need an ack."""
    return text.lower().strip().rstrip(".!?") not in _NO_ACK_PATTERNS


# --- Audio helpers ---

def compute_audio_level(pcm_chunk: bytes) -> float:
    if len(pcm_chunk) < 2:
        return 0.0
    n_samples = len(pcm_chunk) // 2
    samples = struct.unpack("<%dh" % n_samples, pcm_chunk[: n_samples * 2])
    rms = math.sqrt(sum(s * s for s in samples) / n_samples)
    level = min(1.0, rms / 8000.0)
    return round(level, 3)


def save_wav(pcm_data: bytes, path: str, sample_rate: int = SAMPLE_RATE) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


# --- WebSocket session handler ---

async def handle_voice(ws):
    log.info("Client connected: %s", ws.remote_address)
    audio_buffer = bytearray()
    mic_active = False
    session_id = "voice-%d" % int(time.time())
    memory = ConversationMemory()
    last_speech_time = 0.0
    has_speech_in_buffer = False

    async def send_json(data: dict):
        try:
            await ws.send(json.dumps(data))
        except Exception:
            pass

    await send_json({"type": "connected"})

    async def process_utterance(pcm_data: bytes):
        nonlocal has_speech_in_buffer
        has_speech_in_buffer = False

        if len(pcm_data) < MIN_AUDIO_BYTES:
            return

        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="voice_utt_")
        os.close(fd)
        save_wav(pcm_data, wav_path)

        try:
            await send_json({"type": "transcript", "text": "...", "final": False})

            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, transcribe, wav_path)

            if not text or len(text.strip()) < 2:
                await send_json({"type": "transcript", "text": "", "final": True})
                return

            await send_json({"type": "transcript", "text": text, "final": True})

            should_respond, classification = await loop.run_in_executor(
                None, classify, text
            )

            if not should_respond:
                log.info("Skipping (class=%s): %s", classification, text[:50])
                return

            # Send ack immediately to kill dead air
            if needs_ack(text):
                ack_task = loop.run_in_executor(None, generate_ack)
            else:
                ack_task = None

            # Build prompt with conversation history
            memory.check_reset()
            prompt = memory.build_prompt(text)
            memory.add("user", text)

            # Fire ack while LLM generates
            if ack_task:
                ack_data = await ack_task
                if ack_data:
                    await send_json({"type": "tts_status", "speaking": True})
                    await ws.send(ack_data)
                    await send_json({"type": "tts_status", "speaking": False})

            # Get LLM response
            raw_text, spoken_text = await loop.run_in_executor(
                None, get_response, prompt
            )
            memory.add("dex", spoken_text)

            response_msg = {
                "type": "voice_response",
                "text": raw_text,
                "spoken_text": spoken_text,
                "classification": classification,
                "has_audio": False,
            }

            tts_data = await loop.run_in_executor(None, generate_tts, spoken_text)

            if tts_data:
                response_msg["has_audio"] = True
                await send_json(response_msg)
                await send_json({"type": "tts_status", "speaking": True})
                await ws.send(tts_data)
                await send_json({"type": "tts_status", "speaking": False})
            else:
                await send_json(response_msg)

        except Exception as e:
            log.error("Utterance processing error: %s", e)
        finally:
            try:
                os.unlink(wav_path)
            except Exception:
                pass

    try:
        async for message in ws:
            if isinstance(message, str):
                try:
                    msg = json.loads(message)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type", "")

                if msg_type == "mic_start":
                    mic_active = True
                    audio_buffer = bytearray()
                    has_speech_in_buffer = False
                    last_speech_time = time.time()
                    log.info("Mic started — always-on (session=%s)", session_id)
                    await send_json({"type": "vad_status", "active": True})

                elif msg_type == "mic_stop":
                    mic_active = False
                    await send_json({"type": "vad_status", "active": False})
                    await send_json({"type": "audio_level", "level": 0})
                    log.info("Mic stopped (session=%s)", session_id)

                    if audio_buffer and has_speech_in_buffer:
                        pcm = bytes(audio_buffer)
                        audio_buffer = bytearray()
                        await process_utterance(pcm)

            elif isinstance(message, bytes) and mic_active:
                level = compute_audio_level(message)
                await send_json({"type": "audio_level", "level": level})

                if level >= SPEECH_LEVEL_THRESHOLD:
                    audio_buffer.extend(message)
                    has_speech_in_buffer = True
                    last_speech_time = time.time()
                elif has_speech_in_buffer:
                    audio_buffer.extend(message)
                    silence_duration = time.time() - last_speech_time
                    if silence_duration >= SILENCE_END_UTTERANCE_S:
                        pcm = bytes(audio_buffer)
                        audio_buffer = bytearray()
                        await process_utterance(pcm)

    except websockets.exceptions.ConnectionClosed:
        log.info("Client disconnected: %s", ws.remote_address)
    except Exception as e:
        log.error("Session error: %s", e)


async def main():
    log.info("Voice server starting on ws://%s:%d/voice", HOST, PORT)
    log.info("Kokoro TTS: %s (voice=%s)", KOKORO_URL, KOKORO_VOICE)
    async with websockets.serve(
        handle_voice, HOST, PORT,
        ping_interval=20, ping_timeout=20, max_size=2**22,
    ):
        log.info("Voice server ready — always-on mode")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
