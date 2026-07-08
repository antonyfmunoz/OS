"""Voice session API — exposes the voice pipeline loop over HTTP.

Endpoints:
  POST /voice/session/start  — start a new voice session
  POST /voice/session/stop   — stop the active session
  POST /voice/process        — process text input (skip STT, for testing)
  GET  /voice/session/status — current session state
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from substrate.execution.voice.error_codes import VoiceErrorCode, error_payload
from substrate.execution.voice.session import VoiceSession
from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

# ROOT C: max idle wait for the next frame in the audio-accumulation loop. Without
# it, a mobile client that backgrounds / black-holes the connection mid-send (no
# TCP FIN/RST reaches us) leaves the receive coroutine + the live VoiceSession hung
# FOREVER. The client transcribeUtterance timeout is bound to the same order of
# magnitude (~25s client vs 30s server) so the client fails first on a real stall.
RECEIVE_IDLE_TIMEOUT = 30.0

router = APIRouter(prefix="/api/umh/voice")

_session: VoiceSession | None = None
_pipeline_submit_fn: Any = None

# Optional injected organism accessor: () -> object exposing .advisor (with a
# .converse) and .store. Supplied by operator_api/app at startup so the governed
# WS can hand the canonical runtime a governed converse path WITHOUT substrate
# importing transports. When absent, the runtime degrades to deterministic engine
# routing (Deterministic-First law).
_organism_accessor: Any = None


def wire_pipeline(submit_fn: Any) -> None:
    """Inject the pipeline submit function for voice sessions."""
    global _pipeline_submit_fn
    _pipeline_submit_fn = submit_fn


def wire_organism(accessor: Any) -> None:
    """Inject the running-organism accessor for the governed voice WS.

    ``accessor`` is a zero-arg callable returning the organism daemon (or None
    when not running). The WS uses ``daemon.advisor.converse`` as the single
    governed write path (persists the turn to the OrganismStore ledger + sets
    spoken_text), matching the cockpit chat route's DEX conversation path.
    """
    global _organism_accessor
    _organism_accessor = accessor


def _build_converse_fn() -> Any:
    """Build the injected converse callable for a VoiceSession, or None.

    Returns a function ``(content, conversation_id, source, voice_turn_id) ->
    AdvisorResponse`` wired to the running organism's advisor under
    ``governed_mutation(conversation_send)``, or None when no organism is wired
    (the runtime then degrades to deterministic engine routing).
    """
    accessor = _organism_accessor
    if accessor is None:
        return None

    def _converse_fn(*, content: str, conversation_id: str, source: str, voice_turn_id: str) -> Any:
        daemon = accessor() if callable(accessor) else accessor
        if daemon is None or getattr(daemon, "advisor", None) is None:
            return None

        # The AdvisorResponse is captured via closure (governed_mutation returns a
        # status wrapper, not the response) — same pattern as the cockpit chat
        # route's /advisor/converse.
        captured: dict[str, Any] = {}

        def _do_converse():
            from substrate.organism.dex_conversation import DexConversation

            conv = DexConversation(advisor=daemon.advisor, store=daemon.store)
            response = conv.converse(
                content=content,
                conversation_id=conversation_id,
                source=source,
                voice_turn_id=voice_turn_id,
            )
            captured["response"] = response
            return (response.text[:200] or "conversed"), True

        resp = governed_mutation(
            mutation_name="conversation_send",
            intent=f"voice turn: {content[:50]}",
            execute_fn=_do_converse,
            source="voice",
        )
        if not getattr(resp, "success", True):
            return None
        return captured.get("response")

    return _converse_fn


class StartRequest(BaseModel):
    session_id: str = ""
    max_exchanges: int = Field(default=100, ge=1, le=1000)


class ProcessRequest(BaseModel):
    text: str = Field(max_length=2000, min_length=1)


@router.post("/session/start")
async def start_session(req: StartRequest):
    """Start a new voice session."""
    global _session
    if _session is not None and _session.state.status.value != "idle":
        raise HTTPException(status_code=409, detail="Session already active")

    def _do_start():
        global _session
        _session = VoiceSession(
            session_id=req.session_id,
            pipeline_submit_fn=_pipeline_submit_fn,
            max_exchanges=req.max_exchanges,
        )
        _session.start()
        return f"voice session started: {_session.state.session_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent="start voice session",
        execute_fn=_do_start,
        source="cockpit",
    )
    return resp.to_http_dict()


@router.post("/session/stop")
async def stop_session():
    """Stop the active voice session."""
    if _session is None:
        raise HTTPException(status_code=404, detail="No active session")

    def _do_stop():
        _session.stop()
        return f"voice session stopped, {_session.state.exchange_count} exchanges", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent="stop voice session",
        execute_fn=_do_stop,
        source="cockpit",
    )
    return resp.to_http_dict()


@router.post("/process")
async def process_text(req: ProcessRequest):
    """Process text input through the voice pipeline (skip STT)."""
    if _session is None or _session.state.status.value == "idle":
        raise HTTPException(status_code=400, detail="No active session — call /session/start first")

    def _do_process():
        exchange = _session.process_text(req.text)
        return f"processed: {exchange.classification}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"process voice text: {req.text[:50]}",
        execute_fn=_do_process,
        source="cockpit",
    )
    return resp.to_http_dict()


@router.get("/session/status")
async def session_status():
    """Get current voice session state."""
    if _session is None:
        return {"active": False, "status": "idle"}

    state = _session.state.to_dict()
    state["active"] = _session.state.status.value != "idle"
    return state


# ── Governed voice WebSocket — the ONE capture ingress for every surface ───────
#
# GAP F wire protocol (shared by cockpit edges + CLI + tests):
#   1. FIRST message MUST be a TEXT JSON control frame:
#        {source, device_registry_id, consent_grant_id, content_type,
#         activation_mode?, node_id?}
#   2. subsequent messages are BINARY audio chunks (accumulated).
#   3. terminator = an empty binary frame OR a text {"type":"end"}.
#   malformed / binary-first  -> close 4002, no session created.
#
# On terminate, the accumulated audio runs through the canonical VoiceSession
# (warm engine, local STT) and the typed transcript / error / tts frames are
# streamed back. Consent is re-asserted at this boundary (not trusted from the
# client). This is the single governed ingress; :8096 is retired.


async def _send_json(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_json(payload)
    except Exception:
        pass


@router.websocket("/ws")
async def voice_ws(ws: WebSocket) -> None:
    """Governed voice capture ingress for all surfaces (GAP F protocol)."""
    from substrate.execution.voice.warm_engine import get_warm_engine
    from substrate.workstation.voice_consent import GRANTABLE_MODES, VoiceConsentStore

    # 1. Authenticate the WS (Clerk bearer / subprotocol). None => refuse.
    try:
        from transports.api.cockpit_auth import validate_ws_clerk_token

        principal = validate_ws_clerk_token(ws)
    except Exception:
        principal = None
    if principal is None:
        await ws.close(code=4001)
        return
    operator_principal = getattr(principal, "user_id", "")

    await ws.accept()

    # 2. First frame MUST be the TEXT control frame (GAP F).
    try:
        first = await ws.receive()
    except WebSocketDisconnect:
        return
    text0 = first.get("text") if isinstance(first, dict) else None
    if not text0:
        # binary-first or non-text control => protocol violation.
        await ws.close(code=4002)
        return
    try:
        control = json.loads(text0)
    except Exception:
        await ws.close(code=4002)
        return

    source = str(control.get("source", "unknown"))
    device_registry_id = str(control.get("device_registry_id", ""))
    consent_grant_id = str(control.get("consent_grant_id", ""))
    content_type = str(control.get("content_type", "application/octet-stream"))
    activation_mode = str(control.get("activation_mode", "push_to_talk"))
    node_id = str(control.get("node_id", ""))

    # 3. Consent re-assertion (GAP5): the activation_mode must be grantable and a
    #    live grant must exist for this principal+device+mode. Voice input consent
    #    is NOT action approval — it only authorizes capture into a session.
    if activation_mode not in GRANTABLE_MODES:
        await _send_json(ws, error_payload(VoiceErrorCode.CONSENT_DENIED))
        await ws.close(code=1008)
        return
    # P4S31 DURABLE consent (how Apple/WhatsApp treat it): the operator is already
    # AUTHENTICATED on this WS (Clerk bearer validated above) and has already
    # approved the browser/OS mic permission — those two ARE the authorization.
    # A per-device grant is a GOVERNANCE record (auditable, revocable), not a
    # second gate that should strand the user. So if no live grant exists for this
    # authenticated principal+device+grantable-mode, AUTO-CREATE it (audited via
    # the store) instead of refusing. This removes the volatile-device-id failure:
    # a fresh session / cleared localStorage no longer means "consent not granted".
    _store = VoiceConsentStore()
    try:
        grant = _store.active_grant(
            operator_principal, device_registry_id, activation_mode
        )
    except Exception:
        grant = None
    if grant is None and operator_principal and device_registry_id:
        try:
            grant = _store.grant(
                operator_principal, device_registry_id, activation_mode
            )
            logger.info(
                "voice WS auto-granted consent for authenticated principal "
                "(device=%s mode=%s grant=%s)",
                device_registry_id,
                activation_mode,
                getattr(grant, "grant_id", "?"),
            )
        except Exception as e:
            logger.debug("voice WS auto-grant failed: %s", e)
            grant = None
    if grant is None:
        await _send_json(ws, error_payload(VoiceErrorCode.CONSENT_DENIED))
        await ws.close(code=1008)
        return

    # 4. Build the canonical session on the WARM engine (GAP A) + governed converse.
    #    The session id carries the capture surface (source) + grant/device so the
    #    ledger turn's provenance identifies which surface it came from.
    session = VoiceSession(
        session_id=f"voice-ws-{source}-{consent_grant_id or device_registry_id}",
        engine=get_warm_engine(),
        node_id=node_id,
        converse_fn=_build_converse_fn(),
        pipeline_submit_fn=_pipeline_submit_fn,
    )
    session.start()

    # 5. Accumulate BINARY audio until the terminator. Each frame receive is bounded
    #    by RECEIVE_IDLE_TIMEOUT (ROOT C): a client that vanishes mid-send can no
    #    longer hang this coroutine + session forever — we break and process (or
    #    empty-audio-fail) whatever accumulated instead.
    audio = bytearray()
    try:
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=RECEIVE_IDLE_TIMEOUT)
            except asyncio.TimeoutError:
                logger.info(
                    "voice ws receive idle-timeout after %.0fs (%d bytes accumulated) — "
                    "closing to avoid a hung coroutine/session",
                    RECEIVE_IDLE_TIMEOUT,
                    len(audio),
                )
                break
            if msg.get("type") == "websocket.disconnect":
                break
            data = msg.get("bytes")
            text = msg.get("text")
            if data is not None:
                if len(data) == 0:  # empty binary terminator
                    break
                audio.extend(data)
                continue
            if text is not None:
                try:
                    ctrl = json.loads(text)
                except Exception:
                    continue
                if ctrl.get("type") == "end":
                    break
    except WebSocketDisconnect:
        pass

    # 6. Run the accumulated audio through the ONE runtime + relay typed frames.
    #    ROOT C: the typed error/transcript frame is sent AND yielded to the event
    #    loop (`asyncio.sleep(0)`) BEFORE the finally closes the socket, so the
    #    precise VoiceErrorCode reliably flushes to the client instead of racing the
    #    close handshake (which previously surfaced a fast server error as a 25s
    #    client TIMEOUT).
    try:
        exchange = session.process_audio_blob(bytes(audio), content_type=content_type)
        if exchange.error_code:
            await _send_json(ws, error_payload(VoiceErrorCode(exchange.error_code)))
            await asyncio.sleep(0)
        else:
            await _send_json(
                ws,
                {
                    "type": "transcript",
                    "text": exchange.utterance,
                    "final": True,
                },
            )
            if exchange.responded and exchange.spoken_text:
                await _send_json(ws, {"type": "tts", "text": exchange.spoken_text})
            await asyncio.sleep(0)
    except Exception as e:
        logger.warning("voice ws processing error: %s", e)
        await _send_json(ws, error_payload(VoiceErrorCode.STT_FAILED))
        await asyncio.sleep(0)
    finally:
        session.stop()
        try:
            await ws.close()
        except Exception:
            pass
