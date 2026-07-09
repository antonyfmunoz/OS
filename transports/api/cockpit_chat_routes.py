"""Cockpit chat routes — advisor/dex conversation + operator chat.

Extracted from cockpit_core_routes.py to bring it under the 3,000-line
quality gate. UMH transport layer.

Media / audio artifact storage law (P4S-31D1-B lane F)
------------------------------------------------------
Storage location: ``$UMH_ROOT/data/chat_media/`` (flat directory, one file
per artifact). File ids are server-generated; the client filename is never
used to derive the on-disk name.

Naming:
- image/video: ``YYYYMMDD_HHMMSS_<uuid4-hex-8><ext>`` (legacy format, kept
  for compatibility with existing chat history).
- audio (``audio/webm`` | ``audio/wav``): ``<uuid4-hex-32><ext>`` — 128 bits
  of entropy, non-guessable per the voice-message contract storage law. The
  extension is derived from the declared content type (``.weba`` / ``.wav``),
  never from the client filename, so audio/webm is never conflated with
  video/webm on retrieval.

Auth:
- ``POST /chat/upload`` — operator-role gated (route-level ``require_operator``
  dependency) in addition to the parent-router Clerk gate.
- ``GET /chat/media/{file_id}`` and ``GET /chat/attachment`` — gated by the
  parent router (``/api/umh`` carries ``Depends(require_clerk_auth)`` in
  cockpit.py); no unauthenticated retrieval path exists and ``data/chat_media``
  is never mounted as static files.
- ``DELETE /chat/media/{file_id}`` — operator-role gated; audio artifacts only.

Lifecycle / retention (audio):
- Voice-message drafts hold audio CLIENT-SIDE only; nothing is uploaded until
  the operator explicitly sends (chatStore.sendMessage uploads pendingMedia at
  send time — the single upload call site). Draft delete before send therefore
  discards a client-side blob and leaves no server artifact.
- Once sent, the artifact is operator data and lives with chat history.
- ``DELETE /chat/media/{file_id}`` exists so the client can remove an audio
  artifact if the send fails AFTER upload (orphan cleanup) — the only window
  where an artifact can exist without a chat message referencing it.

Logging law: audio bytes, transcripts, and client filenames are never logged
at INFO or above on the upload/retrieval/delete paths; previews are bounded
and DEBUG-only elsewhere in this module.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

chat_router: APIRouter = APIRouter()

# ── Media upload limits (module-level so tests can exercise them) ────────────

ALLOWED_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/webm",
    "video/quicktime",
}
# Voice-message contract (P4S-31D1-B/E): desktop records audio/webm, iOS Safari
# records audio/mp4 (AAC) — both must be accepted so voice works on mobile AND
# desktop. audio/ogg is a Firefox fallback. The voice server (#248) decodes all
# of these to canonical PCM WAV via ffmpeg.
ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/mp4",  # iOS Safari (AAC)
    "audio/ogg",  # Firefox fallback
}
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB — image/video
MAX_AUDIO_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB — audio artifacts

# Server-derived audio extensions — .weba (not .webm) keeps audio/webm
# distinguishable from video/webm at retrieval time. Must stay in lockstep with
# the client's _audioExtFor (cockpit/src/renderer/stores/voiceMessageStore.ts).
_AUDIO_EXT = {
    "audio/webm": ".weba",
    "audio/wav": ".wav",
    "audio/mp4": ".m4a",  # iOS Safari
    "audio/ogg": ".ogg",
}

_get_organism_fn: Callable[[], Any] = lambda: None
_push_chat_message_fn: Callable[[dict], None] = lambda msg: None
_configured: bool = False


def try_chat_intent_rail(content: str, conversation_id: str = "") -> dict | None:
    """P4S-31B Cockpit Chat intent rail — deterministic, no LLM.

    Doctrine: intent originates ONLY through sanctioned Cockpit conversational
    surfaces (Cockpit Chat now; Cockpit Voice later as a thin adapter into the
    same Chat channel). This rail recognizes an intent-bearing chat message
    using the EXISTING deterministic classifier
    (``substrate.workstation.command_router.classify_intent`` — keyword table,
    explicitly no LLM; ``CommandIntent.INTENT_CAPTURE``) and routes it into the
    canonical intent loop via the ONE governed submit shared with
    ``POST /intent-loop/submit`` (``governed_intent_submit`` → registered
    ``intent_loop_submit`` MutationSpec — no ungoverned path).

    The gate HOLDS: the captured loop lands at AWAITING_APPROVAL and never
    auto-advances; approve/reject flows through the governed decision seam.
    Nothing is dispatched or executed here.

    Returns a ChatResponse-shaped dict (server-truth status back into the SAME
    chat thread) when the message is intent-bearing; ``None`` otherwise so the
    normal conversation path proceeds. Runs BEFORE the daemon-backed
    conversation, so intent capture (degraded-safe, audited) works even when
    the organism is down. Never raises.
    """
    try:
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        if classify_intent(content) != CommandIntent.INTENT_CAPTURE:
            return None
    except Exception as exc:
        logger.debug("intent rail classification failed: %s", exc)
        return None

    timestamp = datetime.now(timezone.utc).isoformat()
    conv_id = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"

    try:
        from transports.api.cockpit_intent_loop_routes import governed_intent_submit

        result = governed_intent_submit(content, user_id="cockpit_chat_operator")
    except Exception as exc:
        logger.debug("intent rail governed submit failed: %s", exc)
        result = {"submitted": False, "error": str(exc)}

    if result.get("submitted"):
        draft = result.get("draft") or {}
        spec = result.get("spec") or {}
        text = (
            f"Intent captured — loop `{result.get('loop_id', '')}` is HELD at the "
            f"approval gate (awaiting_approval). Draft `{draft.get('draft_id', '')}`, "
            f"risk {spec.get('risk_level', 'unknown')}, "
            f"{'actionable' if draft.get('actionable') else 'non-actionable'}. "
            "Nothing executes until a governed approve/reject — decide in the "
            "Intent Loop panel."
        )
    else:
        text = (
            "Intent capture rejected by governance: "
            f"{result.get('error') or 'unknown'} — nothing was persisted."
        )

    # Persist the exchange as server truth in the chat thread. Governed under
    # the existing conversation_send spec (not degraded-eligible): with the
    # control plane down this fails closed — the thread still receives the
    # immediate response below, and the intent-loop read surface remains the
    # durable server truth. Non-fatal by design.
    def _persist_turn() -> tuple[str, bool]:
        from substrate.organism.store import OrganismStore

        OrganismStore().save_conversation_turn(
            content=content,
            response=text,
            origin_channel="cockpit",
            responder="dex",
        )
        return ("intent rail turn saved to chat thread", True)

    try:
        governed_mutation(
            mutation_name="conversation_send",
            intent=f"intent rail status: {content[:60]}",
            execute_fn=_persist_turn,
            source="cockpit",
        )
    except Exception as exc:
        logger.debug("intent rail turn persistence failed (non-fatal): %s", exc)

    return {
        "message_id": f"intent-rail-{uuid.uuid4().hex[:8]}",
        "text": text,
        "response": text,
        "conversation_id": conv_id,
        "intent": "intent_loop_submit",
        "suggested_actions": [
            {
                "label": "Open Intent Loop",
                "action": "navigate",
                "payload": {"panel": "intentloop"},
            },
        ],
        "metadata": {
            "surface": "intent_loop",
            "submitted": bool(result.get("submitted")),
            "loop_id": result.get("loop_id", ""),
            "stage": result.get("stage", ""),
            "intent_id": (result.get("spec") or {}).get("intent_id", ""),
            "draft_id": (result.get("draft") or {}).get("draft_id", ""),
            "error": result.get("error"),
        },
        "timestamp": timestamp,
    }


def configure(
    get_organism_fn: Callable[[], Any],
    push_chat_message_fn: Callable[[dict], None],
    require_operator_dep: Any,
) -> None:
    """Wire shared cockpit utilities and operator auth into the chat router."""
    global _get_organism_fn, _push_chat_message_fn, _configured, chat_router

    _get_organism_fn = get_organism_fn
    _push_chat_message_fn = push_chat_message_fn
    _configured = True

    chat_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    """Construct the chat router with operator auth on privileged routes."""
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    _dex_conversation = None

    def _mirror_to_discord_founders_office(text: str) -> None:
        import threading

        def _send():
            try:
                import urllib.request

                _env_path = Path("/opt/OS/services/.env")
                token = os.environ.get("DISCORD_BOT_TOKEN", "")
                channel_id = os.environ.get("DISCORD_FOUNDERS_OFFICE", "")

                if not token and _env_path.exists():
                    with open(_env_path) as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("DISCORD_BOT_TOKEN="):
                                token = line.split("=", 1)[1].strip()
                            elif line.startswith("DISCORD_FOUNDERS_OFFICE="):
                                channel_id = line.split("=", 1)[1].strip()

                if not token or not channel_id:
                    return

                truncated = text[:2000]
                url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
                payload = json.dumps({"content": truncated}).encode()
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "Authorization": f"Bot {token}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception as exc:
                logger.debug("Discord mirror failed (non-fatal): %s", exc)

        threading.Thread(target=_send, daemon=True).start()

    def _get_dex_conversation():
        nonlocal _dex_conversation
        if _dex_conversation is not None:
            return _dex_conversation
        daemon = _get_organism_fn()
        if daemon is None:
            return None
        from substrate.organism.dex_conversation import DexConversation

        _dex_conversation = DexConversation(advisor=daemon.advisor, store=daemon.store)
        return _dex_conversation

    # ── Advisor / DEX conversation endpoints ─────────────────────────────────

    @r.post("/advisor/converse")
    def advisor_converse(payload: dict):
        """Multi-turn conversational endpoint for the advisor right rail."""
        content = payload.get("content", "")
        if not content:
            return {"error": "content required"}

        # P4S-31B Cockpit Chat intent rail: deterministic (classify_intent,
        # no LLM). Intent-bearing messages become the canonical intent event
        # (governed intent_loop_submit, gate HELD at awaiting_approval) and the
        # server-truth status returns into this same thread. Runs BEFORE the
        # daemon-backed conversation so intent capture works daemon-down.
        rail = try_chat_intent_rail(content, payload.get("conversation_id", ""))
        if rail is not None:
            return rail

        conv = _get_dex_conversation()
        if conv is None:
            return {"error": "organism not running"}

        source = payload.get("source", "text")
        routing = payload.get("routing")
        voice_turn_id = payload.get("voice_turn_id", "")
        captured: dict = {}

        def _do_converse():
            response = conv.converse(
                content=content,
                conversation_id=payload.get("conversation_id", ""),
                view_context=payload.get("view_context"),
                source=source,
                routing=routing,
                voice_turn_id=voice_turn_id,
            )

            try:
                from substrate.organism.store import OrganismStore

                store = OrganismStore()
                store.save_conversation_turn(
                    content=content,
                    response=response.text,
                    origin_channel="cockpit",
                    responder="dex",
                    # Persist operator media (e.g. a voice message's audio) so the
                    # audio player survives reload via /chat/history.
                    media=payload.get("media") or None,
                )
            except Exception as exc:
                logger.debug("Failed to persist conversation to OrganismStore: %s", exc)

            if source != "discord" and response.text:
                _mirror_to_discord_founders_office(response.text)

            result: dict = {
                "message_id": f"advisor-{response.timestamp}",
                "text": response.text,
                "response": response.text,
                "conversation_id": response.conversation_id,
                "intent": response.intent,
                "suggested_actions": response.suggested_actions,
                "metadata": response.metadata,
                "timestamp": response.timestamp,
            }
            if response.spoken_text:
                result["spoken_text"] = response.spoken_text
            if response.routing:
                result["routing"] = response.routing
            captured.update(result)
            return response.text[:200] or "conversed", True

        resp = governed_mutation(
            mutation_name="conversation_send",
            intent=f"advisor converse: {content[:80]}",
            execute_fn=_do_converse,
            source="cockpit",
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @r.post("/dex/converse")
    async def dex_converse_compat(payload: dict):
        """Backward-compat shim — canonical route is /advisor/converse."""
        return await advisor_converse(payload)

    @r.get("/advisor/history")
    def advisor_history(limit: int = 50):
        """Recent advisor channel exchanges and system reports for the right-rail chat."""
        daemon = _get_organism_fn()
        if daemon is None:
            return []

        messages = daemon.store.list_messages(limit=500)

        exchanges: list[dict[str, Any]] = []

        dex_msgs = [
            m for m in messages if m.get("payload", {}).get("source") == "cockpit_advisor_channel"
        ]
        i = 0
        while i < len(dex_msgs):
            msg = dex_msgs[i]
            exchange: dict[str, Any] = {
                "id": msg.get("id", ""),
                "timestamp": msg.get("created_at", ""),
                "sender": msg.get("sender", ""),
                "content": "",
                "response": None,
            }
            if msg.get("sender") == "operator":
                exchange["content"] = msg.get("payload", {}).get("content", "")
                if i + 1 < len(dex_msgs) and dex_msgs[i + 1].get("sender") == "dex":
                    exchange["response"] = dex_msgs[i + 1].get("payload", {}).get("response")
                    exchange["timestamp"] = dex_msgs[i + 1].get("created_at", exchange["timestamp"])
                    i += 2
                    continue
            elif msg.get("sender") == "dex":
                exchange["content"] = ""
                exchange["response"] = msg.get("payload", {}).get("response")
            exchanges.append(exchange)
            i += 1

        _REPORT_SENDERS = {"system", "dex"}
        for m in messages:
            if m.get("intent") == "report" and m.get("sender", "") in _REPORT_SENDERS:
                payload = m.get("payload", {})
                title = str(payload.get("title", "Report"))[:200]
                summary = payload.get("summary", "")
                meta = payload.get("metadata", {})
                file_path = str(payload.get("file_path", ""))[:500]
                conv_id = m.get("conversation_id", "")

                provenance: dict[str, Any] = {
                    "node": "VPS",
                    "harness": "Claude Code",
                }
                if conv_id:
                    provenance["session"] = str(conv_id)[:12]
                if meta.get("phase"):
                    provenance["phase"] = str(meta["phase"])[:20]
                if meta.get("pr"):
                    provenance["pr"] = (
                        int(meta["pr"]) if str(meta["pr"]).isdigit() else str(meta["pr"])[:20]
                    )
                if meta.get("task"):
                    provenance["task"] = str(meta["task"])[:100]

                attachment = None
                if file_path:
                    attachment = {
                        "path": file_path,
                        "filename": file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path,
                    }

                exchanges.append(
                    {
                        "id": m.get("id", ""),
                        "timestamp": m.get("created_at", ""),
                        "sender": m.get("sender", "system"),
                        "content": "",
                        "response": summary,
                        "intent": "report",
                        "title": title,
                        "provenance": provenance,
                        "attachment": attachment,
                    }
                )

        exchanges.sort(key=lambda x: x.get("timestamp", ""))
        return exchanges[-limit:]

    @r.get("/dex/history")
    async def dex_history_compat(limit: int = 50):
        """Backward-compat shim — canonical route is /advisor/history."""
        return await advisor_history(limit)

    # ── Chat endpoints (operator ↔ DEX right-rail conversation) ──────────────

    @r.get("/chat/history")
    def chat_history():
        """Return chat history for the cockpit right-rail ChatDrawer."""
        try:
            from substrate.organism.store import OrganismStore

            store = OrganismStore()
            messages = store.list_messages(limit=50)
            result = []
            for m in messages:
                intent = m.get("intent", "")
                payload = m.get("payload", {})
                raw_sender = m.get("sender", "system")
                attachment = None
                if intent == "report" and raw_sender in ("system", "dex", ""):
                    meta = payload.get("metadata", {})
                    title = str(payload.get("title", "Report"))[:200]
                    summary = payload.get("summary", "")
                    file_path = str(payload.get("file_path", ""))[:500]
                    conv_id = m.get("conversation_id", "")
                    content = summary
                    sender = "assistant"
                    provenance: dict[str, Any] = {
                        "node": "VPS",
                        "harness": "Claude Code",
                    }
                    if conv_id:
                        provenance["session"] = str(conv_id)[:12]
                    if meta.get("phase"):
                        provenance["phase"] = str(meta["phase"])[:20]
                    if meta.get("pr"):
                        provenance["pr"] = (
                            int(meta["pr"]) if str(meta["pr"]).isdigit() else str(meta["pr"])[:20]
                        )
                    if meta.get("task"):
                        provenance["task"] = str(meta["task"])[:100]
                    if file_path:
                        filename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
                        attachment = {"path": file_path, "filename": filename}
                elif intent == "converse":
                    content = payload.get("content", "")
                    sender = "operator" if raw_sender == "operator" else "assistant"
                    provenance = None
                else:
                    content = (
                        payload.get("content", "") or payload.get("task", "") or str(payload)[:200]
                    )
                    sender = "operator" if raw_sender == "operator" else "assistant"
                    provenance = None
                entry: dict[str, Any] = {
                    "id": m.get("id", ""),
                    "sender": sender,
                    "content": content,
                    "timestamp": m.get("created_at", ""),
                    "origin_channel": m.get("origin_channel"),
                }
                if intent == "report":
                    entry["intent"] = "report"
                    entry["title"] = title
                    if provenance:
                        entry["provenance"] = {k: v for k, v in provenance.items() if v}
                    if attachment:
                        entry["attachment"] = attachment
                # Voice-message audio (and any operator media) persisted on the turn:
                # re-emit it so the cockpit re-renders the audio player after reload.
                if payload.get("media"):
                    entry["media"] = payload["media"]
                result.append(entry)
            return result
        except Exception as e:
            logger.error("chat_history failed: %s", e)
            return []

    @r.post("/chat/converse", dependencies=auth)
    async def chat_converse(request: Request):
        """Route operator message through organism conversation pipeline."""
        body = await request.json()
        content = (body.get("content") or "").strip()
        if not content:
            return JSONResponse({"error": "content is required"}, status_code=400)
        captured: dict = {}

        def _do_converse():
            from substrate.organism.store import OrganismStore

            store = OrganismStore()
            inbound, outbound = store.save_conversation_turn(
                content=content,
                response="Acknowledged. Processing via organism.",
                origin_channel="cockpit",
            )
            captured.update(
                {
                    "message_id": str(inbound.id),
                    "response": outbound.payload.get("content", "Acknowledged."),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return "conversation saved", True

        resp = governed_mutation(
            mutation_name="conversation_send",
            intent=f"chat converse: {content[:80]}",
            execute_fn=_do_converse,
            source="cockpit",
        )
        if not resp.success:
            return {
                "message_id": f"dex-{int(time.time() * 1000)}",
                "response": "Internal error — check server logs.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return captured

    @r.post("/chat/send", dependencies=auth)
    async def chat_send(request: Request):
        """Send a message — writes to organism store + pushes to cockpit WS."""
        body = await request.json()
        content = (body.get("content") or "").strip()
        if not content:
            return JSONResponse({"error": "content is required"}, status_code=400)
        captured: dict = {}

        def _do_send():
            from substrate.organism.store import OrganismStore

            store = OrganismStore()
            inbound, _ = store.save_conversation_turn(
                content=content,
                response="",
                origin_channel="cockpit",
            )
            _push_chat_message_fn(
                {
                    "sender": "operator",
                    "content": content,
                    "origin_channel": "cockpit",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            captured.update({"success": True, "message_id": str(inbound.id)})
            return "message sent", True

        resp = governed_mutation(
            mutation_name="conversation_send",
            intent=f"chat send: {content[:80]}",
            execute_fn=_do_send,
            source="cockpit",
        )
        if not resp.success:
            return JSONResponse({"error": "internal error"}, status_code=500)
        return captured

    @r.post("/chat/push")
    async def chat_push(request: Request):
        """Push a chat message to connected cockpit WS clients."""
        body = await request.json()

        def _do_push():
            _push_chat_message_fn(body)
            return "message pushed", True

        resp = governed_mutation(
            mutation_name="channel_message_send",
            intent="push chat message to WS clients",
            execute_fn=_do_push,
            source="cockpit",
        )
        return resp.to_http_dict()

    @r.get("/chat/attachment")
    def chat_attachment(path: str):
        """Download an attachment file referenced in a chat message."""
        from pathlib import Path as PathLib

        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        if path.startswith("/opt/OS/") and repo_root != "/opt/OS":
            path = os.path.join(repo_root, path[len("/opt/OS/") :])
        allowed_dirs = [
            PathLib(os.path.realpath(os.path.join(repo_root, "docs"))),
            PathLib(os.path.realpath(os.path.join(repo_root, "data", "audits"))),
            PathLib(os.path.realpath(os.path.join(repo_root, "data", "chat_media"))),
        ]
        resolved = PathLib(os.path.realpath(path))
        if not any(resolved.is_relative_to(d) for d in allowed_dirs):
            raise HTTPException(status_code=403, detail="Path outside allowed directories")
        if resolved.name.startswith("."):
            raise HTTPException(status_code=403, detail="Hidden files not allowed")
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(
            str(resolved), filename=resolved.name, media_type="application/octet-stream"
        )

    # ── Media upload for multimodal chat (+ voice audio artifacts) ───────────

    @r.post("/chat/upload", dependencies=auth)
    async def chat_upload(file: UploadFile = File(...)):
        """Upload an image, video, or voice-message audio artifact for chat.

        Returns a serving URL plus integrity fields (sha256, size_bytes) per
        the voice-message contract AudioArtifactRef shape. See the module
        docstring for the full storage law.
        """
        import hashlib

        # Browsers append codec parameters (e.g. "audio/webm;codecs=opus").
        base_ct = (file.content_type or "").split(";")[0].strip().lower()
        is_audio = base_ct in ALLOWED_AUDIO_TYPES

        if not is_audio and base_ct not in ALLOWED_MEDIA_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported media type: {base_ct or 'unknown'}. "
                f"Allowed: {', '.join(sorted(ALLOWED_MEDIA_TYPES | ALLOWED_AUDIO_TYPES))}",
            )

        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        media_dir = Path(repo_root) / "data" / "chat_media"
        media_dir.mkdir(parents=True, exist_ok=True)

        if is_audio:
            # Storage law: non-guessable id (128-bit), server-derived extension
            # (never the client filename — avoids audio/webm vs video/webm
            # conflation and path tricks).
            ext = _AUDIO_EXT[base_ct]
            file_id = f"{uuid.uuid4().hex}{ext}"
            max_size = MAX_AUDIO_UPLOAD_SIZE
        else:
            ext = Path(file.filename or "upload").suffix or _ext_from_content_type(base_ct)
            file_id = (
                f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                f"_{uuid.uuid4().hex[:8]}{ext}"
            )
            max_size = MAX_UPLOAD_SIZE
        dest = media_dir / file_id

        size = 0
        hasher = hashlib.sha256()
        with open(dest, "wb") as f:
            while chunk := await file.read(64 * 1024):
                size += len(chunk)
                if size > max_size:
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large (max {max_size // (1024 * 1024)} MB)",
                    )
                hasher.update(chunk)
                f.write(chunk)

        if is_audio:
            media_type = "audio"
        elif base_ct.startswith("image/"):
            media_type = "image"
        else:
            media_type = "video"

        return {
            "id": file_id,
            "url": f"/api/umh/chat/media/{file_id}",
            "filename": file.filename or file_id,
            "content_type": base_ct,
            "media_type": media_type,
            "size": size,
            "size_bytes": size,
            "sha256": hasher.hexdigest(),
        }

    @r.get("/chat/media/{file_id}")
    def chat_media(file_id: str):
        """Serve uploaded chat media.

        Auth: parent router (/api/umh) requires the authenticated operator
        session (Clerk) — see module docstring. Never mounted static.
        """
        if "/" in file_id or ".." in file_id or file_id.startswith("."):
            raise HTTPException(status_code=400, detail="Invalid file ID")

        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        media_path = Path(repo_root) / "data" / "chat_media" / file_id

        if not media_path.is_file():
            raise HTTPException(status_code=404, detail="Media not found")

        ext = media_path.suffix.lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mov": "video/quicktime",
            ".weba": "audio/webm",
            ".wav": "audio/wav",
        }
        ct = content_types.get(ext, "application/octet-stream")

        return FileResponse(str(media_path), media_type=ct)

    @r.delete("/chat/media/{file_id}", dependencies=auth)
    def chat_media_delete(file_id: str):
        """Delete a voice-message audio artifact (orphan cleanup / retention).

        Audio artifacts only (.weba/.wav) — image/video chat media may be
        referenced by persisted chat history and is out of scope for this
        route. Operator-role gated like upload. Follows the seam's existing
        direct-filesystem pattern (upload is the write precedent).
        """
        if "/" in file_id or ".." in file_id or file_id.startswith("."):
            raise HTTPException(status_code=400, detail="Invalid file ID")

        if Path(file_id).suffix.lower() not in (".weba", ".wav"):
            raise HTTPException(
                status_code=400, detail="Only audio artifacts are deletable via this route"
            )

        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        media_path = Path(repo_root) / "data" / "chat_media" / file_id

        if not media_path.is_file():
            raise HTTPException(status_code=404, detail="Media not found")

        media_path.unlink()
        logger.debug("audio artifact deleted: %s", file_id)
        return {"deleted": True, "id": file_id}

    return r


def _ext_from_content_type(ct: str) -> str:
    """Map content type to file extension."""
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "audio/webm": ".weba",
        "audio/wav": ".wav",
    }.get(ct, ".bin")
