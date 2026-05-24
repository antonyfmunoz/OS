"""Voice WebSocket bridge — exposes mic + TTS to the cockpit renderer.

Runs as a standalone asyncio server on ws://localhost:8095/voice.
Spawned by the Electron main process, killed on app exit.

Protocol (JSON over WebSocket):
  Client → Server: mic_start, mic_stop, tts_speak, clone_voice, set_voice
  Server → Client: transcript, vad_status, tts_status, audio_level, connected
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import threading

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

logger = logging.getLogger(__name__)

HOST = os.environ.get("VOICE_HOST", "127.0.0.1")
PORT = int(os.environ.get("VOICE_PORT", "8095"))


class VoiceBridge:
    """Wraps AmbientMic + VoiceOutput for WebSocket clients."""

    def __init__(self) -> None:
        self._mic = None
        self._voice = None
        self._clients: set[asyncio.StreamWriter] = set()
        self._poll_task: asyncio.Task | None = None

    def _ensure_mic(self):
        if self._mic is not None:
            return self._mic
        try:
            from umh.mic import AmbientMic
            self._mic = AmbientMic()
            return self._mic
        except Exception as e:
            logger.warning("Mic init failed: %s", e)
            return None

    def _ensure_voice(self):
        if self._voice is not None:
            return self._voice
        try:
            from umh.voice import VoiceOutput
            self._voice = VoiceOutput()
            return self._voice
        except Exception as e:
            logger.warning("Voice init failed: %s", e)
            return None

    async def handle_message(self, msg: dict, send_fn) -> None:
        msg_type = msg.get("type", "")

        if msg_type == "mic_start":
            mic = self._ensure_mic()
            if mic and not mic.is_listening:
                mic.start()
                await send_fn({"type": "vad_status", "active": True})
                if self._poll_task is None or self._poll_task.done():
                    self._poll_task = asyncio.create_task(
                        self._poll_transcripts(send_fn)
                    )

        elif msg_type == "mic_stop":
            if self._mic and self._mic.is_listening:
                self._mic.stop()
                await send_fn({"type": "vad_status", "active": False})

        elif msg_type == "tts_speak":
            text = msg.get("text", "")
            if text:
                voice = self._ensure_voice()
                if voice:
                    await send_fn({"type": "tts_status", "speaking": True})
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, voice.speak, text)
                    await send_fn({"type": "tts_status", "speaking": False})

    async def _poll_transcripts(self, send_fn) -> None:
        """Poll mic for transcripts every 100ms."""
        while self._mic and self._mic.is_listening:
            transcript = self._mic.get_transcript()
            if transcript:
                await send_fn({
                    "type": "transcript",
                    "text": transcript,
                    "final": True,
                })
            await asyncio.sleep(0.1)

    def shutdown(self) -> None:
        if self._mic and self._mic.is_listening:
            self._mic.stop()


bridge = VoiceBridge()


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle one WebSocket-like client (simplified TCP JSON protocol)."""
    pass


async def ws_handler(websocket):
    """Handle a websocket connection (using websockets library)."""
    logger.info("Client connected")

    async def send_fn(data: dict):
        try:
            await websocket.send(json.dumps(data))
        except Exception:
            pass

    await send_fn({"type": "connected"})

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
                await bridge.handle_message(msg, send_fn)
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.debug("Client disconnected: %s", e)
    finally:
        logger.info("Client disconnected")


async def main():
    try:
        import websockets
    except ImportError:
        logger.error("websockets package required: pip install websockets")
        sys.exit(1)

    server = await websockets.serve(ws_handler, HOST, PORT)
    logger.info("Voice server listening on ws://%s:%d/voice", HOST, PORT)
    print(f"Voice server listening on ws://{HOST}:{PORT}/voice", flush=True)

    stop = asyncio.Event()

    def signal_handler():
        stop.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    await stop.wait()
    server.close()
    await server.wait_closed()
    bridge.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(main())
