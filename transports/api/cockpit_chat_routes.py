"""Cockpit chat routes — advisor/dex conversation + operator chat.

Extracted from cockpit_core_routes.py to bring it under the 3,000-line
quality gate. UMH transport layer.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

chat_router: APIRouter = APIRouter()

_get_organism_fn: Callable[[], Any] = lambda: None
_push_chat_message_fn: Callable[[dict], None] = lambda msg: None
_configured: bool = False


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
        conv = _get_dex_conversation()
        if conv is None:
            return {"error": "organism not running"}

        content = payload.get("content", "")
        if not content:
            return {"error": "content required"}

        source = payload.get("source", "text")
        routing = payload.get("routing")
        voice_turn_id = payload.get("voice_turn_id", "")

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
        return result

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
        try:
            from substrate.organism.store import OrganismStore

            store = OrganismStore()
            inbound, outbound = store.save_conversation_turn(
                content=content,
                response="Acknowledged. Processing via organism.",
                origin_channel="cockpit",
            )
            return {
                "message_id": str(inbound.id),
                "response": outbound.payload.get("content", "Acknowledged."),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("chat_converse failed: %s", e)
            return {
                "message_id": f"dex-{int(time.time() * 1000)}",
                "response": "Internal error — check server logs.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @r.post("/chat/send", dependencies=auth)
    async def chat_send(request: Request):
        """Send a message — writes to organism store + pushes to cockpit WS."""
        body = await request.json()
        content = (body.get("content") or "").strip()
        if not content:
            return JSONResponse({"error": "content is required"}, status_code=400)
        try:
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
            return {"success": True, "message_id": str(inbound.id)}
        except Exception as e:
            logger.error("chat_send failed: %s", e)
            return JSONResponse({"error": "internal error"}, status_code=500)

    @r.post("/chat/push")
    async def chat_push(request: Request):
        """Push a chat message to connected cockpit WS clients."""
        body = await request.json()
        _push_chat_message_fn(body)
        return {"ok": True}

    @r.get("/chat/attachment")
    def chat_attachment(path: str):
        """Download an attachment file referenced in a chat message."""
        from pathlib import Path as PathLib

        from fastapi.responses import FileResponse

        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        if path.startswith("/opt/OS/") and repo_root != "/opt/OS":
            path = os.path.join(repo_root, path[len("/opt/OS/"):])
        allowed_dirs = [
            PathLib(os.path.realpath(os.path.join(repo_root, "docs"))),
            PathLib(os.path.realpath(os.path.join(repo_root, "data", "audits"))),
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

    return r
