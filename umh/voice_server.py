#!/usr/bin/env python3
"""Cockpit Voice Server — WebSocket bridge between browser mic and UMH voice stack.

Listens on ws://0.0.0.0:8095/voice.
Protocol:
  Browser -> Server (JSON):
    {"type": "mic_start"}              start a voice session
    {"type": "mic_stop"}               stop the session
  Browser -> Server (binary):
    raw PCM16 audio chunks at 16kHz    streamed while mic is active
  Server -> Browser (JSON):
    {"type": "vad_status", "active": bool}
    {"type": "audio_level", "level": float}
    {"type": "transcript", "text": str, "final": bool}
    {"type": "tts_status", "speaking": bool}
    {"type": "voice_response", "text": str, "spoken_text": str, "classification": str}
  Server -> Browser (binary):
    WAV audio bytes for TTS playback   sent after voice_response with has_audio=true
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import struct
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv("/opt/OS/services/.env")
load_dotenv("/opt/OS/runtime/.env", override=True)

try:
    import websockets
    import websockets.server
except ImportError:
    print("[voice_server] Installing websockets...")
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
SILENCE_TIMEOUT_S = 1.8
MIN_AUDIO_BYTES = int(SAMPLE_RATE * 2 * 0.3)


def _transcribe_groq(audio_path: str) -> str:
    try:
        from groq import Groq as GroqClient

        key = os.getenv("GROQ_API_KEY")
        if not key:
            return ""
        client = GroqClient(api_key=key)
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
                language="en",
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


def classify(text: str) -> tuple:
    try:
        from substrate.execution.voice.voice_engine import VoiceEngine

        engine = VoiceEngine()
        return engine.should_respond(text)
    except Exception:
        return True, "conversation"


def _get_response(transcript: str) -> str:
    from substrate.execution.bridge.voice_first import VOICE_SYSTEM_SUFFIX

    try:
        from adapters.models.model_router import call_with_fallback

        prompt = transcript + VOICE_SYSTEM_SUFFIX
        raw = call_with_fallback(prompt=prompt, task_type="conversation")
        if raw:
            return str(raw) if not isinstance(raw, str) else raw
    except Exception as e:
        log.warning("model_router failed: %s", e)

    try:
        from substrate.execution.voice.voice_engine import VoiceEngine

        engine = VoiceEngine()
        return engine.query_local(transcript)
    except Exception as e:
        log.warning("Local LLM fallback failed: %s", e)

    return "I couldn't process that right now."


def get_response(transcript: str) -> tuple:
    """Returns (raw_response, spoken_text)."""
    from substrate.execution.bridge.voice_first import prepare_voice_response

    raw = _get_response(transcript)
    spoken = prepare_voice_response(raw)
    return raw, spoken


def generate_tts(text: str) -> bytes:
    try:
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="voice_tts_")
        os.close(fd)
        result = subprocess.run(
            ["espeak", "-s", "160", "-p", "40", "-w", path, text[:500]],
            capture_output=True,
            timeout=15,
        )
        if result.returncode == 0 and os.path.exists(path):
            with open(path, "rb") as f:
                data = f.read()
            os.unlink(path)
            return data
    except Exception as e:
        log.warning("TTS failed: %s", e)
    return b""


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


async def handle_voice(ws):
    log.info("Client connected: %s", ws.remote_address)
    audio_buffer = bytearray()
    mic_active = False
    session_id = "voice-%d" % int(time.time())

    async def send_json(data: dict):
        try:
            await ws.send(json.dumps(data))
        except Exception:
            pass

    await send_json({"type": "connected"})

    async def process_utterance(pcm_data: bytes):
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
                log.info("Skipping response (class=%s): %s", classification, text[:50])
                return

            raw_text, spoken_text = await loop.run_in_executor(
                None, get_response, text
            )

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
                    log.info("Mic started (session=%s)", session_id)
                    await send_json({"type": "vad_status", "active": True})

                elif msg_type == "mic_stop":
                    mic_active = False
                    await send_json({"type": "vad_status", "active": False})
                    await send_json({"type": "audio_level", "level": 0})
                    log.info("Mic stopped (session=%s)", session_id)

                    if audio_buffer:
                        pcm = bytes(audio_buffer)
                        audio_buffer = bytearray()
                        await process_utterance(pcm)

            elif isinstance(message, bytes) and mic_active:
                audio_buffer.extend(message)

                level = compute_audio_level(message)
                await send_json({"type": "audio_level", "level": level})

                buffer_duration = len(audio_buffer) / (SAMPLE_RATE * 2)
                if buffer_duration >= SILENCE_TIMEOUT_S and level < 0.02:
                    pcm = bytes(audio_buffer)
                    audio_buffer = bytearray()
                    await process_utterance(pcm)

    except websockets.exceptions.ConnectionClosed:
        log.info("Client disconnected: %s", ws.remote_address)
    except Exception as e:
        log.error("Session error: %s", e)


async def main():
    log.info("Voice server starting on ws://%s:%d/voice", HOST, PORT)
    async with websockets.serve(
        handle_voice,
        HOST,
        PORT,
        ping_interval=20,
        ping_timeout=20,
        max_size=2**22,
    ):
        log.info("Voice server ready")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
