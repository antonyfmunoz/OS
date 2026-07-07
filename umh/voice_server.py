#!/usr/bin/env python3
"""Cockpit Voice Server — pure STT + TTS bridge for DEX conversations.

Listens on ws://0.0.0.0:8096/voice.
Plain-HTTP GET /health on the SAME port returns a 200 JSON status document
(served via the websockets ``process_request`` hook — the WS upgrade path
is untouched).

This server handles ONLY audio I/O:
  - STT: Groq Whisper with faster-whisper fallback
  - TTS: Kokoro on Beast (GPU) with espeak fallback
  - Always-on listening with silence-based turn detection

All intelligence (intent classification, conversation routing, governance)
flows through DEXConversation via the browser's POST /dex/converse endpoint.
The browser sends transcripts to DEX, receives RRIP responses, then requests
TTS playback via the tts_request message.

Protocol:
  Browser -> Server (JSON):
    {"type": "mic_start"}                           start voice session
    {"type": "mic_stop"}                            stop session
    {"type": "tts_request", "text": "..."}          generate and stream TTS
    {"type": "tts_cancel"}                          cancel current TTS
  Browser -> Server (binary):
    raw PCM16 audio chunks at 16kHz
  Server -> Browser (JSON):
    {"type": "vad_status", "active": bool}
    {"type": "audio_level", "level": float}
    {"type": "transcript", "text": str, "final": bool}
    {"type": "tts_status", "speaking": bool}
    {"type": "tts_error", "error": str}
  Server -> Browser (binary):
    WAV/audio bytes for TTS playback
  HTTP (same port):
    GET /health -> 200 {"status", "uptime_s", "stt_engine",
                        "tts_provider", "active_sessions"}

Privacy model (docs/VOICE_INTENT_CONTRACT.md — transcript-only transit):
  - Transcript text is NEVER persisted to disk, NEVER sent to any endpoint
    other than the requesting WS client, and NEVER logged at INFO or above
    (truncated <=40-char previews at DEBUG only).
  - Audio is NEVER persisted: utterance PCM is written to a temp WAV solely
    for the STT call and unlinked immediately after, success or failure.
  - This server does NOT read or write consent state
    (data/umh/voice/*). Consent (VoiceConsentGrant) is enforced on the
    client + API side; this process is a pure STT/TTS bridge.
  - espeak fallback receives text on stdin (--stdin), never in argv, so
    conversation content is not visible in the process table.

Lifecycle (infra/systemd/umh-voice-server.service):
  - Type=notify: READY=1 is sent (raw sd_notify datagram, no dependency)
    once the WS server is listening; WATCHDOG=1 keepalives are sent at half
    the WatchdogSec interval from the event loop, so a hung loop trips the
    systemd watchdog and the unit restarts.
  - SIGTERM/SIGINT trigger a graceful shutdown: active WS sessions are
    closed with code 1001 before the process exits 0.

Resource profile (measured 2026-07-06 on the VPS, plus expected fallback):
  - Groq STT path (network-bound, the default): ~26 MB RSS, ~0% CPU idle,
    <0.2 s CPU over 25 min of uptime. Negligible.
  - faster-whisper fallback (local CPU STT): model load adds roughly
    300-900 MB RSS depending on model size, with 1-1.5 core bursts during
    transcription. CPUQuota=150% / MemoryMax=1G in the unit bound exactly
    this worst case (CPU Gate Law) — do not raise without re-measuring.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import signal
import socket
import struct
import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from umh.voice_preflight import (  # noqa: E402  (after sys.path bootstrap)
    VoiceErrorCode,
    error_payload,
    preflight_pcm16,
)

load_dotenv("/opt/OS/services/.env")
load_dotenv("/opt/OS/.env", override=False)

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    # A managed systemd service must never mutate the host python env at
    # boot (no auto pip-install). Fail loudly; Restart=on-failure +
    # StartLimitBurst in the unit bound the crash loop.
    print(
        "[voice] FATAL: websockets>=13 is not installed. "
        "Install it once: /usr/bin/python3 -m pip install 'websockets>=13.0'",
        file=sys.stderr,
    )
    raise SystemExit(1)

logging.basicConfig(
    level=logging.INFO,
    format="[voice] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("voice_server")

HOST = os.getenv("VOICE_SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("VOICE_SERVER_PORT", "8096"))
SAMPLE_RATE = 16000
# Minimum-utterance / silence / duration gating now lives in the canonical
# preflight module (umh/voice_preflight.py: MIN_UTTERANCE_BYTES,
# SILENCE_MEAN_LEVEL_FLOOR, MIN_UTTERANCE_SECONDS). Do not re-derive it here.

SILENCE_END_UTTERANCE_S = 1.8
SPEECH_LEVEL_THRESHOLD = 0.02

KOKORO_URL = os.getenv("KOKORO_TTS_URL", "http://100.74.199.102:8880")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "bf_emma")
KOKORO_SPEED = float(os.getenv("KOKORO_SPEED", "1.0"))

# Max transcript characters allowed in a DEBUG-level preview (privacy bound).
TRANSCRIPT_PREVIEW_CHARS = 40

SERVER_START_MONOTONIC = time.monotonic()

# Live WS sessions — used by /health and by graceful shutdown.
ACTIVE_SESSIONS: set[Any] = set()


# --- systemd integration (raw sd_notify — no external dependency) ---


def sd_notify(state: str) -> bool:
    """Send an sd_notify state string (e.g. READY=1) to systemd.

    Implements the NOTIFY_SOCKET datagram protocol directly so no pip
    dependency is needed. No-op (returns False) when not running under a
    Type=notify systemd unit.
    """
    addr = os.environ.get("NOTIFY_SOCKET", "")
    if not addr:
        return False
    if addr.startswith("@"):
        # Abstract-namespace socket: leading '@' means a leading NUL byte.
        addr = "\0" + addr[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(addr)
            sock.sendall(state.encode("utf-8"))
        return True
    except OSError as e:
        log.debug("sd_notify(%s) failed: %s", state, e)
        return False


async def watchdog_keepalive() -> None:
    """Ping the systemd watchdog at half the WatchdogSec interval.

    systemd exports WATCHDOG_USEC when WatchdogSec= is set on the unit.
    If the event loop hangs, keepalives stop and systemd restarts us.
    """
    usec = os.environ.get("WATCHDOG_USEC", "")
    if not usec.isdigit():
        return
    watchdog_pid = os.environ.get("WATCHDOG_PID", "")
    if watchdog_pid and watchdog_pid != str(os.getpid()):
        return
    interval = max(1.0, int(usec) / 2_000_000)
    log.info("systemd watchdog active — keepalive every %.1fs", interval)
    while True:
        await asyncio.sleep(interval)
        sd_notify("WATCHDOG=1")


# --- Health endpoint (plain HTTP on the WS port) ---


def build_health_payload() -> dict[str, Any]:
    """Status document served at GET /health. Contains no conversation data."""
    return {
        "status": "ok",
        "uptime_s": round(time.monotonic() - SERVER_START_MONOTONIC, 1),
        "stt_engine": "groq" if os.getenv("GROQ_API_KEY") else "faster-whisper",
        "tts_provider": "kokoro" if KOKORO_URL else "espeak",
        "active_sessions": len(ACTIVE_SESSIONS),
    }


def process_request(connection: Any, request: Any) -> Any:
    """websockets>=14 asyncio ``process_request`` hook.

    Answers plain-HTTP GET /health with 200 JSON; returns None for every
    other path so the normal WebSocket upgrade handshake proceeds untouched
    (the cockpit client's /voice path never enters this branch's response).
    """
    path = str(getattr(request, "path", "") or "")
    if path.split("?", 1)[0] != "/health":
        return None
    from websockets.datastructures import Headers
    from websockets.http11 import Response

    body = json.dumps(build_health_payload()).encode("utf-8")
    headers = Headers()
    headers["Content-Type"] = "application/json"
    headers["Content-Length"] = str(len(body))
    return Response(200, "OK", headers, body)


# --- STT ---


# STT results distinguish three outcomes so the WS layer can emit a PRECISE
# error code (VAD_NO_SPEECH vs STT_FAILED) instead of a blanket empty transcript:
#   ok=True                -> transcription succeeded (text may still be empty
#                             if the engine genuinely found no speech).
#   ok=False, engine_error -> the engine itself failed (network/crash/timeout).
# ``text`` is the transcript (bounded logging only). ``engine`` names the STT
# path that produced the result, for diagnostics (never a secret).


class TranscribeResult:
    """Typed STT outcome. ``engine_error`` distinguishes an engine failure
    (STT_FAILED) from a genuine empty transcript (VAD_NO_SPEECH)."""

    __slots__ = ("text", "engine_error", "engine")

    def __init__(self, text: str = "", *, engine_error: bool = False, engine: str = "") -> None:
        self.text = text
        self.engine_error = engine_error
        self.engine = engine


def _transcribe_groq(audio_path: str) -> TranscribeResult:
    try:
        from groq import Groq as GroqClient

        key = os.getenv("GROQ_API_KEY")
        if not key:
            # Not configured is not an engine failure — let the chain fall
            # through to the local engine.
            return TranscribeResult("", engine_error=False, engine="groq")
        client = GroqClient(api_key=key)
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
                language="en",
            )
        text = result.text.strip()
        if text:
            # Privacy: transcript content only at DEBUG, truncated preview.
            log.info("STT (groq): %d chars", len(text))
            log.debug("STT preview: %s", text[:TRANSCRIPT_PREVIEW_CHARS])
        return TranscribeResult(text, engine_error=False, engine="groq")
    except Exception as e:
        log.warning("Groq STT failed: %s", e)
        return TranscribeResult("", engine_error=True, engine="groq")


def _transcribe_local(audio_path: str) -> TranscribeResult:
    try:
        from substrate.execution.voice.voice_engine import VoiceEngine

        engine = VoiceEngine()
        text = (engine.intelligent.transcribe_fast(audio_path) or "").strip()
        return TranscribeResult(text, engine_error=False, engine="faster-whisper")
    except Exception as e:
        log.warning("Local STT failed: %s", e)
        return TranscribeResult("", engine_error=True, engine="faster-whisper")


def transcribe(audio_path: str) -> TranscribeResult:
    """Run the STT fallback chain and return a typed result.

    Groq first; if it produced text, use it. Otherwise try the local engine.
    ``engine_error`` is True ONLY if the final engine actually failed — a clean
    engine that simply found no speech returns ok with empty text so the caller
    emits VAD_NO_SPEECH, not STT_FAILED."""
    groq_res = _transcribe_groq(audio_path)
    if groq_res.text:
        return groq_res
    local_res = _transcribe_local(audio_path)
    if local_res.text:
        return local_res
    # No text from either. If EITHER engine hard-failed, this is an engine
    # failure (STT_FAILED); if both ran cleanly with empty output, it is a
    # genuine no-speech result (VAD_NO_SPEECH).
    if groq_res.engine_error or local_res.engine_error:
        return TranscribeResult("", engine_error=True, engine=local_res.engine or groq_res.engine)
    return TranscribeResult("", engine_error=False, engine=local_res.engine)


# --- TTS: Kokoro (Beast GPU) with espeak fallback ---


def _tts_kokoro(text: str) -> tuple[bytes, dict[str, Any]]:
    meta: dict[str, Any] = {"provider": "kokoro", "voice": KOKORO_VOICE, "speed": KOKORO_SPEED}
    try:
        import urllib.request

        url = "%s/v1/audio/speech" % KOKORO_URL
        t0 = time.monotonic()
        payload = json.dumps(
            {
                "model": "kokoro",
                "input": text[:500],
                "voice": KOKORO_VOICE,
                "speed": KOKORO_SPEED,
                "response_format": "wav",
            }
        ).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            latency_ms = int((time.monotonic() - t0) * 1000)
            meta["latency_ms"] = latency_ms
            meta["audio_format"] = "wav"
            meta["audio_bytes"] = len(data)
            if len(data) > 100:
                log.info("TTS (kokoro/%s): %d bytes, %dms", KOKORO_VOICE, len(data), latency_ms)
                return data, meta
    except Exception as e:
        log.warning("Kokoro TTS failed: %s", e)
        meta["error"] = str(e)
    return b"", meta


def _tts_espeak(text: str) -> tuple[bytes, dict[str, Any]]:
    meta: dict[str, Any] = {"provider": "espeak", "voice": "default"}
    try:
        # CPU Gate Law: never a raw subprocess — the gate skips espeak when
        # the host is overloaded (returns None) and we degrade to tts_error.
        from substrate.execution.cpu_gate import gated_subprocess_run

        fd, path = tempfile.mkstemp(suffix=".wav", prefix="voice_tts_")
        os.close(fd)
        t0 = time.monotonic()
        # Privacy: --stdin keeps spoken text out of argv (visible in ps).
        result = gated_subprocess_run(
            ["espeak", "-s", "160", "-p", "40", "-w", path, "--stdin"],
            caller="voice_server.espeak_tts",
            timeout=15,
            input=text[:500].encode("utf-8"),
            capture_output=True,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        meta["latency_ms"] = latency_ms
        meta["audio_format"] = "wav"
        if result is None:
            meta["error"] = "cpu gate blocked espeak (host overloaded)"
            try:
                os.unlink(path)
            except OSError as e:
                log.debug("espeak temp cleanup failed: %s", e)
            return b"", meta
        if result.returncode == 0 and os.path.exists(path):
            with open(path, "rb") as f:
                data = f.read()
            os.unlink(path)
            meta["audio_bytes"] = len(data)
            return data, meta
    except Exception as e:
        log.warning("espeak TTS failed: %s", e)
        meta["error"] = str(e)
    return b"", meta


def generate_tts(text: str) -> tuple[bytes, dict[str, Any]]:
    data, meta = _tts_kokoro(text)
    if data:
        return data, meta
    data, meta = _tts_espeak(text)
    if data:
        return data, meta
    return b"", {"provider": "none", "error": "all TTS providers failed"}


def prepare_for_speech(text: str) -> str:
    try:
        from substrate.execution.bridge.voice_first import prepare_voice_response

        return prepare_voice_response(text)
    except Exception:
        return text[:400]


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
    ACTIVE_SESSIONS.add(ws)
    audio_buffer = bytearray()
    mic_active = False
    # session_id can be overridden by a "session_id" JSON field in mic_start or a
    # dedicated "register_session" message sent by the frontend before mic_start.
    session_id = "voice-%d" % int(time.time())
    last_speech_time = 0.0
    has_speech_in_buffer = False
    tts_cancelled = False
    chunk_count = 0

    async def send_json(data: dict):
        try:
            await ws.send(json.dumps(data))
        except Exception as e:
            log.debug("send_json failed (client gone?): %s", e)

    await send_json({"type": "connected", "server_session_id": session_id})

    async def process_utterance(pcm_data: bytes):
        """Preflight, transcribe, and emit a PRECISE typed outcome.

        Every failure resolves to exactly one typed error code — never a bare
        empty transcript. The audio buffer is NEVER discarded on failure: it is
        held by the client (which owns the artifact) and this server only writes
        a transient temp WAV for the STT call, unlinked in ``finally``.
        """
        nonlocal has_speech_in_buffer
        has_speech_in_buffer = False

        # --- Preflight the WHOLE buffer BEFORE any STT work ---
        pre = preflight_pcm16(pcm_data)
        if not pre.ok:
            # EMPTY_AUDIO_BLOB (no/too-few bytes) or SILENT_AUDIO (mic silent).
            # Distinct, typed, never collapsed into "no speech".
            assert pre.error_code is not None
            log.info(
                "Preflight rejected (session=%s code=%s bytes=%d dur=%.2fs level=%.4f)",
                session_id,
                pre.error_code.value,
                pre.n_bytes,
                pre.duration_s,
                pre.mean_level,
            )
            await send_json(error_payload(pre.error_code))
            return

        log.info(
            "Processing utterance: %d bytes (%.1fs audio, mean_level=%.4f)",
            pre.n_bytes,
            pre.duration_s,
            pre.mean_level,
        )

        # Audio is never persisted: the temp WAV exists only for the STT
        # call and is unlinked in the finally block, success or failure.
        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="voice_utt_")
        os.close(fd)
        save_wav(pcm_data, wav_path)

        try:
            await send_json({"type": "transcript", "text": "...", "final": False})

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, transcribe, wav_path)

            text = result.text.strip()
            if len(text) < 2:
                if result.engine_error:
                    # The engine itself failed — STT_FAILED, distinct from a
                    # clean "no speech" result.
                    log.info("STT engine failed (engine=%s) -> STT_FAILED", result.engine)
                    await send_json(error_payload(VoiceErrorCode.STT_FAILED))
                else:
                    # Audio was present and non-silent, but the engine found no
                    # speech in it — VAD_NO_SPEECH, distinct from SILENT_AUDIO.
                    log.info("STT clean but no speech (engine=%s) -> VAD_NO_SPEECH", result.engine)
                    await send_json(error_payload(VoiceErrorCode.VAD_NO_SPEECH))
                return

            await send_json(
                {"type": "transcript", "text": text, "final": True, "session_id": session_id}
            )
            # Privacy: transcript content only at DEBUG, truncated preview.
            log.info("Transcript delivered (session=%s, %d chars)", session_id, len(text))
            log.debug("Transcript preview: %s", text[:TRANSCRIPT_PREVIEW_CHARS])

        except Exception as e:
            log.error("Utterance processing error: %s", e)
            await send_json(
                error_payload(
                    VoiceErrorCode.STT_FAILED,
                    "Speech recognition failed — %s" % str(e)[:60],
                )
            )
        finally:
            try:
                os.unlink(wav_path)
            except OSError as e:
                log.debug("utterance temp cleanup failed: %s", e)

    async def handle_tts_request(text: str):
        nonlocal tts_cancelled
        tts_cancelled = False

        if not text:
            return

        loop = asyncio.get_event_loop()
        spoken = await loop.run_in_executor(None, prepare_for_speech, text)

        if tts_cancelled:
            return

        tts_data, tts_meta = await loop.run_in_executor(None, generate_tts, spoken)

        if tts_cancelled:
            return

        if tts_data:
            await send_json(
                {
                    "type": "tts_status",
                    "speaking": True,
                    "tts_provider": tts_meta.get("provider", "unknown"),
                    "voice": tts_meta.get("voice", ""),
                    "latency_ms": tts_meta.get("latency_ms", 0),
                    "audio_format": tts_meta.get("audio_format", "wav"),
                }
            )
            await ws.send(tts_data)
            await send_json({"type": "tts_status", "speaking": False})
        else:
            error_msg = tts_meta.get("error", "all TTS providers failed")
            await send_json({"type": "tts_error", "error": f"TTS generation failed: {error_msg}"})

    try:
        async for message in ws:
            if isinstance(message, str):
                try:
                    msg = json.loads(message)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type", "")

                if msg_type == "mic_start":
                    # Allow frontend to pass its session_id for device routing
                    client_session = msg.get("session_id", "")
                    if client_session:
                        session_id = client_session
                    mic_active = True
                    audio_buffer = bytearray()
                    has_speech_in_buffer = False
                    chunk_count = 0
                    last_speech_time = time.time()
                    log.info("Mic started (session=%s)", session_id)
                    await send_json({"type": "vad_status", "active": True})

                elif msg_type == "mic_stop":
                    mic_active = False
                    await send_json({"type": "vad_status", "active": False})
                    await send_json({"type": "audio_level", "level": 0})
                    log.info(
                        "Mic stopped (session=%s chunks=%d buf=%d speech=%s)",
                        session_id,
                        chunk_count,
                        len(audio_buffer),
                        has_speech_in_buffer,
                    )

                    if audio_buffer and has_speech_in_buffer:
                        pcm = bytes(audio_buffer)
                        audio_buffer = bytearray()
                        await process_utterance(pcm)
                    elif audio_buffer:
                        # Bytes arrived but the per-chunk VAD never crossed the
                        # speech threshold. Preflight the whole buffer so the
                        # client gets SILENT_AUDIO (mic silent) vs a real code,
                        # never a blanket empty transcript.
                        pcm = bytes(audio_buffer)
                        audio_buffer = bytearray()
                        await process_utterance(pcm)
                    else:
                        # No audio bytes at all reached the server.
                        log.info(
                            "No audio bytes buffered (session=%s) -> EMPTY_AUDIO_BLOB", session_id
                        )
                        await send_json(error_payload(VoiceErrorCode.EMPTY_AUDIO_BLOB))

                elif msg_type == "tts_request":
                    await handle_tts_request(msg.get("text", ""))

                elif msg_type == "tts_cancel":
                    tts_cancelled = True
                    log.info("TTS cancelled by client")

            elif isinstance(message, bytes) and mic_active:
                chunk_count += 1
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

    except ConnectionClosed:
        log.info("Client disconnected: %s", ws.remote_address)
    except Exception as e:
        log.error("Session error: %s", e)
    finally:
        ACTIVE_SESSIONS.discard(ws)


# --- Lifecycle ---


def install_signal_handlers(loop: asyncio.AbstractEventLoop, stop: "asyncio.Future[None]") -> None:
    """Register SIGTERM/SIGINT handlers that trigger graceful shutdown.

    Graceful path: resolve the stop future -> main() closes every active WS
    session with code 1001, sends STOPPING=1 to systemd, and exits 0 (so
    Restart=on-failure does NOT restart a deliberate stop).
    """

    def _request_shutdown(signame: str) -> None:
        log.info("Received %s — beginning graceful shutdown", signame)
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _request_shutdown, sig.name)


async def main():
    log.info(
        "Voice server starting on ws://%s:%d/voice (HTTP GET /health on same port)", HOST, PORT
    )
    log.info("Kokoro TTS: %s (voice=%s)", KOKORO_URL, KOKORO_VOICE)

    loop = asyncio.get_running_loop()
    stop: "asyncio.Future[None]" = loop.create_future()
    install_signal_handlers(loop, stop)

    async with websockets.serve(
        handle_voice,
        HOST,
        PORT,
        ping_interval=20,
        ping_timeout=20,
        max_size=2**22,
        process_request=process_request,
    ):
        sd_notify("READY=1")
        watchdog_task = asyncio.ensure_future(watchdog_keepalive())
        log.info("Voice server ready — STT + TTS bridge mode")
        await stop
        sd_notify("STOPPING=1")
        watchdog_task.cancel()
        sessions = list(ACTIVE_SESSIONS)
        if sessions:
            log.info("Closing %d active session(s)", len(sessions))
            await asyncio.gather(
                *(ws.close(code=1001, reason="server shutting down") for ws in sessions),
                return_exceptions=True,
            )
    log.info("Voice server stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
