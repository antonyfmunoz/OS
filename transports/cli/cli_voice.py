"""CLI voice capture — Claude-Code-style /voice push-to-talk over the governed WS.

P4S31 Voice Convergence. The CLI is a THIN capture edge on the ONE governed voice
runtime, exactly like the browser. It captures raw PCM16 mono@16kHz locally via
sounddevice, streams it over the governed voice WS using the GAP F wire protocol
(TEXT control frame → BINARY audio → terminator), and returns the transcript for
the REPL to drop into the prompt buffer. No local STT — the same server-side
faster-whisper every surface uses.

Graceful capability degradation (Deterministic-First): if sounddevice is not
installed, /voice returns a clear install hint instead of crashing the REPL.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
RAW_PCM_CONTENT_TYPE = "audio/pcm"


def _ws_url_from_base(base_url: str) -> str:
    """Derive the governed voice WS URL from the CLI's HTTP base_url.

    ``http://host:8000/api/umh`` → ``ws://host:8000/api/umh/voice/ws``.
    """
    ws = base_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    return ws.rstrip("/") + "/voice/ws"


def sounddevice_available() -> bool:
    try:
        import sounddevice  # noqa: F401

        return True
    except Exception:
        return False


def capture_ptt_pcm16(stop_check=None) -> bytes:
    """Capture raw PCM16 mono@16kHz from the default mic until Enter/stop.

    Push-to-talk: records into a buffer until ``stop_check()`` returns True (or,
    by default, until the user presses Enter). Returns the raw PCM16 bytes. Raises
    RuntimeError if sounddevice is unavailable.
    """
    if not sounddevice_available():
        raise RuntimeError(
            "voice capture needs the 'sounddevice' package — install with "
            "`pip install sounddevice` (and a PortAudio backend)"
        )
    import queue

    import sounddevice as sd

    q: "queue.Queue[bytes]" = queue.Queue()

    def _cb(indata, frames, time_info, status):  # noqa: ANN001
        if status:
            logger.debug("sounddevice status: %s", status)
        q.put(bytes(indata))

    frames: list[bytes] = []
    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        callback=_cb,
    ):
        import sys

        # Default stop: block for a line on stdin (press Enter to end capture).
        if stop_check is None:
            sys.stdin.readline()
            while not q.empty():
                frames.append(q.get_nowait())
        else:
            while not stop_check():
                try:
                    frames.append(q.get(timeout=0.1))
                except queue.Empty:
                    continue
    return b"".join(frames)


def transcribe_over_ws(
    pcm16: bytes,
    ws_url: str,
    *,
    api_key: str = "",
    device_registry_id: str = "cli",
    consent_grant_id: str = "",
    source: str = "cli",
    timeout: float = 20.0,
) -> dict:
    """Stream one utterance to the governed voice WS (GAP F) and return the result.

    Returns ``{"ok": True, "text": ...}`` on a final transcript, or
    ``{"ok": False, "code": <VoiceErrorCode>}`` on a typed error / timeout.
    """
    try:
        from websocket import create_connection  # websocket-client
    except Exception:
        return {"ok": False, "code": "RUNTIME_UNAVAILABLE"}

    header = [f"Authorization: Bearer {api_key}"] if api_key else []
    try:
        ws = create_connection(ws_url, header=header, timeout=timeout)
    except Exception as e:
        logger.debug("voice ws connect failed: %s", e)
        return {"ok": False, "code": "RUNTIME_UNAVAILABLE"}

    try:
        # 1. TEXT control frame (GAP F — must be first)
        ws.send(
            json.dumps(
                {
                    "source": source,
                    "device_registry_id": device_registry_id,
                    "consent_grant_id": consent_grant_id,
                    "content_type": RAW_PCM_CONTENT_TYPE,
                    "activation_mode": "push_to_talk",
                }
            )
        )
        # 2. BINARY audio (chunked so a large utterance streams incrementally)
        chunk = 32000  # ~1s of PCM16 @16kHz
        for i in range(0, len(pcm16), chunk):
            ws.send_binary(pcm16[i : i + chunk])
        # 3. terminator
        ws.send(json.dumps({"type": "end"}))

        # collect the first transcript / error frame
        while True:
            raw = ws.recv()
            if isinstance(raw, bytes):
                continue
            msg = json.loads(raw)
            if msg.get("type") == "transcript" and msg.get("final"):
                return {"ok": True, "text": msg.get("text", "")}
            if msg.get("type") == "error":
                return {"ok": False, "code": msg.get("code", "STT_FAILED")}
    except Exception as e:
        logger.debug("voice ws stream failed: %s", e)
        return {"ok": False, "code": "STT_FAILED"}
    finally:
        try:
            ws.close()
        except Exception:
            pass


def voice_to_transcript(base_url: str, api_key: str = "") -> Optional[str]:
    """Full CLI /voice flow: capture → governed WS → transcript string.

    Returns the transcript to inject into the prompt buffer, or None on
    capture/transcribe failure (the caller prints the reason).
    """
    pcm16 = capture_ptt_pcm16()
    if not pcm16:
        return None
    result = transcribe_over_ws(pcm16, _ws_url_from_base(base_url), api_key=api_key)
    if result.get("ok"):
        return str(result.get("text", "")).strip() or None
    return None
