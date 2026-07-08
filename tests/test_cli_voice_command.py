"""P4S31 Voice Convergence — CLI /voice push-to-talk (Commit 6).

The CLI is a THIN edge on the ONE governed voice runtime: it captures raw PCM16
locally and streams it over the governed WS with the GAP F control frame. These
tests exercise the wire framing (control content_type/activation_mode) and the
graceful degradation when sounddevice is absent — no real mic, no real network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transports.cli import cli_voice


def test_ws_url_derived_from_http_base() -> None:
    assert (
        cli_voice._ws_url_from_base("http://localhost:8000/api/umh")
        == "ws://localhost:8000/api/umh/voice/ws"
    )
    assert cli_voice._ws_url_from_base("https://host/api/umh") == "wss://host/api/umh/voice/ws"


def test_voice_command_inserts_transcript(monkeypatch) -> None:
    # GAP F: the control frame carries content_type='audio/pcm' and
    # activation_mode='push_to_talk'; a final transcript is returned.
    sent: list = []

    class _FakeWs:
        def send(self, data):
            sent.append(("text", data))

        def send_binary(self, data):
            sent.append(("bin", data))

        def recv(self):
            return json.dumps({"type": "transcript", "text": "hello cli", "final": True})

        def close(self):
            pass

    import websocket

    monkeypatch.setattr(websocket, "create_connection", lambda *a, **k: _FakeWs())
    res = cli_voice.transcribe_over_ws(
        b"\x01\x02" * 100, "ws://x/api/umh/voice/ws", consent_grant_id="g1"
    )
    assert res == {"ok": True, "text": "hello cli"}
    # first text frame is the control frame with the GAP F fields
    first_text = next(d for kind, d in sent if kind == "text")
    control = json.loads(first_text)
    assert control["content_type"] == "audio/pcm"
    assert control["activation_mode"] == "push_to_talk"
    assert control["source"] == "cli"
    assert control["consent_grant_id"] == "g1"
    # a terminator frame was sent
    assert any(kind == "text" and json.loads(d).get("type") == "end" for kind, d in sent)


def test_error_frame_relayed_verbatim(monkeypatch) -> None:
    class _FakeWs:
        def send(self, data):
            pass

        def send_binary(self, data):
            pass

        def recv(self):
            return json.dumps({"type": "error", "code": "SILENT_AUDIO"})

        def close(self):
            pass

    import websocket

    monkeypatch.setattr(websocket, "create_connection", lambda *a, **k: _FakeWs())
    res = cli_voice.transcribe_over_ws(b"\x00" * 100, "ws://x/api/umh/voice/ws")
    assert res == {"ok": False, "code": "SILENT_AUDIO"}


def test_graceful_without_sounddevice(monkeypatch) -> None:
    # When sounddevice is unavailable, capture raises a clear install hint rather
    # than crashing.
    monkeypatch.setattr(cli_voice, "sounddevice_available", lambda: False)
    try:
        cli_voice.capture_ptt_pcm16()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "sounddevice" in str(e)
