"""P4S31 Voice Convergence — the governed voice WS endpoint (Commit 3).

Covers the GAP F wire protocol (text control first → binary audio → terminator),
auth refusal (GAP13), consent re-assertion (GRANTABLE_MODES), typed error frames,
and that the injected governed converse is invoked with source + voice_turn_id.
The WS is exercised via FastAPI's TestClient (no real network, no real mic).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Repo-root-relative so the test loads THIS checkout's modules (worktree-safe),
# not whatever /opt/OS happens to hold.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from transports.api import voice as V


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(V.router)
    return app


class _Grant:
    is_active = True


@pytest.fixture(autouse=True)
def _wire(monkeypatch):
    # Authenticate every WS as a fixed principal unless a test overrides. The WS
    # imports validate_ws_clerk_token from cockpit_auth INSIDE the handler, so
    # patch it at the source module.
    import transports.api.cockpit_auth as auth

    class _User:
        user_id = "op_test"

    monkeypatch.setattr(auth, "validate_ws_clerk_token", lambda ws: _User())
    # Default: a live consent grant exists for push_to_talk.
    import substrate.workstation.voice_consent as vc

    monkeypatch.setattr(vc.VoiceConsentStore, "active_grant", lambda self, *a, **k: _Grant())
    # Warm engine → a fake that returns a canned transcript.
    from unittest.mock import MagicMock

    fake_engine = MagicMock()
    fake_engine.intelligent = MagicMock()
    fake_engine.intelligent.transcribe_fast = MagicMock(return_value="hello from ws")
    fake_engine.should_respond = MagicMock(return_value=(True, "question"))
    fake_engine.route_query = MagicMock(return_value="routed reply")
    fake_engine.speak = MagicMock(return_value="/tmp/o.wav")
    import substrate.execution.voice.warm_engine as we

    monkeypatch.setattr(we, "get_warm_engine", lambda: fake_engine)
    yield


def _control(**over):
    base = {
        "source": "web",
        "device_registry_id": "dev1",
        "consent_grant_id": "g1",
        "content_type": "audio/pcm",
        "activation_mode": "push_to_talk",
    }
    base.update(over)
    return base


def test_wire_pipeline_preserved() -> None:
    # GAP B: wire_pipeline stays callable (app import proven elsewhere).
    assert callable(V.wire_pipeline)
    assert callable(V.wire_organism)


def test_unauthenticated_ws_refused(monkeypatch) -> None:
    import transports.api.cockpit_auth as auth

    monkeypatch.setattr(auth, "validate_ws_clerk_token", lambda ws: None)
    client = TestClient(_app())
    with pytest.raises(Exception):
        with client.websocket_connect("/api/umh/voice/ws") as ws:
            ws.send_json(_control())
            ws.receive_json()


def test_malformed_control_frame_closes_4002() -> None:
    # First frame BINARY (not text control) → protocol violation, no session.
    client = TestClient(_app())
    with pytest.raises(Exception):
        with client.websocket_connect("/api/umh/voice/ws") as ws:
            ws.send_bytes(b"\x00\x01\x02")
            ws.receive_json()


def test_empty_audio_returns_typed_error() -> None:
    # GAP F: text control(audio/pcm) + zero-length binary terminator → the runtime
    # sees empty audio → EMPTY_AUDIO_BLOB relayed verbatim.
    client = TestClient(_app())
    with client.websocket_connect("/api/umh/voice/ws") as ws:
        ws.send_json(_control())
        ws.send_bytes(b"")  # empty binary terminator, no audio
        frame = ws.receive_json()
    assert frame["type"] == "error"
    assert frame["code"] == "EMPTY_AUDIO_BLOB"


def test_consent_denied_when_grant_fails(monkeypatch) -> None:
    # P4S31 DURABLE consent: an authenticated WS AUTO-GRANTS when no live grant
    # exists (the browser mic approval + Clerk auth are the authorization). So
    # denial for a grantable mode now requires BOTH: no existing grant AND the
    # auto-grant write itself failing. This proves the path is still fail-closed —
    # a grant that cannot be recorded refuses capture rather than proceeding
    # ungoverned.
    import substrate.workstation.voice_consent as vc

    monkeypatch.setattr(vc.VoiceConsentStore, "active_grant", lambda self, *a, **k: None)

    def _boom(self, *a, **k):
        raise RuntimeError("grant store unavailable")

    monkeypatch.setattr(vc.VoiceConsentStore, "grant", _boom)
    client = TestClient(_app())
    with client.websocket_connect("/api/umh/voice/ws") as ws:
        ws.send_json(_control())
        frame = ws.receive_json()
    assert frame["code"] == "CONSENT_DENIED"


def test_authenticated_ws_autogrants_when_no_existing_grant(monkeypatch) -> None:
    # The durable-consent happy path: no existing grant, but the authenticated
    # principal triggers an auto-grant and capture proceeds (no CONSENT_DENIED).
    import substrate.workstation.voice_consent as vc

    monkeypatch.setattr(vc.VoiceConsentStore, "active_grant", lambda self, *a, **k: None)
    granted = {"called": False}

    class _AutoGrant:
        grant_id = "auto-g1"

    def _grant(self, *a, **k):
        granted["called"] = True
        return _AutoGrant()

    monkeypatch.setattr(vc.VoiceConsentStore, "grant", _grant)
    client = TestClient(_app())
    with client.websocket_connect("/api/umh/voice/ws") as ws:
        ws.send_json(_control())
        # send an empty-binary terminator immediately — empty audio yields a typed
        # error, NOT a consent denial. The point: we got PAST consent via auto-grant.
        ws.send_bytes(b"")
        frame = ws.receive_json()
    assert granted["called"] is True
    assert frame["code"] != "CONSENT_DENIED"


def test_non_grantable_mode_denied() -> None:
    # wake_word is not in GRANTABLE_MODES → CONSENT_DENIED before any converse.
    client = TestClient(_app())
    with client.websocket_connect("/api/umh/voice/ws") as ws:
        ws.send_json(_control(activation_mode="wake_word"))
        frame = ws.receive_json()
    assert frame["code"] == "CONSENT_DENIED"


def test_receive_loop_has_idle_timeout() -> None:
    # ROOT C: the audio-accumulation receive loop must bound each frame receive so a
    # client that vanishes mid-send can't hang the coroutine + VoiceSession forever.
    src = (
        Path(__file__).resolve().parent.parent / "transports" / "api" / "voice.py"
    ).read_text(encoding="utf-8")
    assert "import asyncio" in src
    assert "RECEIVE_IDLE_TIMEOUT" in src
    assert "asyncio.wait_for(ws.receive()" in src
    assert "asyncio.TimeoutError" in src


def test_error_frame_flushed_before_close() -> None:
    # ROOT C: a fast server-side failure must reach the client as its precise typed
    # error frame, not race the close handshake (which previously surfaced as a 25s
    # client TIMEOUT). Source-assert the error/transcript send yields to the loop
    # (asyncio.sleep(0)) before the finally closes the socket.
    src = (
        Path(__file__).resolve().parent.parent / "transports" / "api" / "voice.py"
    ).read_text(encoding="utf-8")
    # the sleep(0) yields appear in the processing block, before the finally close.
    processing = src.split("# 6.", 1)[1]
    finally_idx = processing.index("finally:")
    before_finally = processing[:finally_idx]
    assert "asyncio.sleep(0)" in before_finally


def test_error_frame_reaches_client_before_close() -> None:
    # Behavioral: a typed error frame reliably reaches the client BEFORE the socket
    # closes (ROOT C — no more fast-server-error surfacing as a 25s client TIMEOUT).
    # Empty audio is the deterministic typed-error trigger (EMPTY_AUDIO_BLOB).
    client = TestClient(_app())
    with client.websocket_connect("/api/umh/voice/ws") as ws:
        ws.send_json(_control())
        ws.send_bytes(b"")  # empty-binary terminator → empty audio → typed error
        frame = ws.receive_json()
    # a typed error frame arrived (client is TOLD, not left to time out).
    assert frame.get("type") == "error" or "code" in frame


def test_ws_transcript_and_converse_invoked(monkeypatch) -> None:
    # A real (stubbed) transcript flows through the runtime and the injected
    # governed converse is called with source='voice' + a voice_turn_id.
    calls: list[dict] = []

    from substrate.organism.advisor_conversation import AdvisorResponse

    def fake_converse_fn(*, content, conversation_id, source, voice_turn_id):
        calls.append({"content": content, "source": source, "voice_turn_id": voice_turn_id})
        return AdvisorResponse(
            text="raw long answer",
            conversation_id=conversation_id,
            intent="q",
            spoken_text="shaped",
        )

    monkeypatch.setattr(V, "_build_converse_fn", lambda: fake_converse_fn)
    client = TestClient(_app())
    with client.websocket_connect("/api/umh/voice/ws") as ws:
        ws.send_json(_control())
        ws.send_bytes(b"\x01\x02" * 8000)  # non-empty audio
        ws.send_json({"type": "end"})
        frames = []
        for _ in range(2):
            try:
                frames.append(ws.receive_json())
            except Exception:
                break
    types = {f.get("type") for f in frames}
    assert "transcript" in types
    assert calls and calls[0]["source"] == "voice"
    assert ":" in calls[0]["voice_turn_id"]


def test_stt_crash_surfaces_stt_failed(monkeypatch) -> None:
    # PHASE 3: a genuine STT/processing crash must surface as a TYPED STT_FAILED error
    # frame, not a blank "success" (empty transcript). Previously process_audio_file
    # swallowed the exception and returned empty text with no error_code.
    import struct

    import substrate.workstation.voice_consent as vc

    monkeypatch.setattr(vc.VoiceConsentStore, "active_grant", lambda self, *a, **k: _Grant())

    # A warm engine whose STT RAISES mid-transcribe.
    from unittest.mock import MagicMock

    fake_engine = MagicMock()
    fake_engine.intelligent = MagicMock()

    def _boom(_path):
        raise RuntimeError("stt exploded")

    fake_engine.intelligent.transcribe_fast = MagicMock(side_effect=_boom)
    import substrate.execution.voice.warm_engine as we

    monkeypatch.setattr(we, "get_warm_engine", lambda: fake_engine)

    # A loud, non-silent PCM16 buffer > MIN_UTTERANCE_BYTES (9600) so it passes
    # preflight and REACHES transcribe_fast (which then raises).
    samples = 8000  # 0.5s @ 16kHz
    loud = b"".join(struct.pack("<h", 8000 if i % 2 == 0 else -8000) for i in range(samples))

    client = TestClient(_app())
    with client.websocket_connect("/api/umh/voice/ws") as ws:
        ws.send_json(_control())  # audio/pcm → raw-pcm lane → preflight → STT
        ws.send_bytes(loud)
        ws.send_bytes(b"")  # terminator
        frame = ws.receive_json()
    assert frame["type"] == "error"
    assert frame["code"] == "STT_FAILED"
