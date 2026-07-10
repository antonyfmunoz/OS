"""
CC Reply Webhook Receiver — receives POSTs from the CC Stop hook and
dispatches replies to Discord channels.

Architecture:
    CC session completes a turn
    → Stop hook reads last assistant message from JSONL transcript
    → POSTs {session_name, text} to http://<bind_host>:8765/cc-reply
    → This receiver maps session_name → Discord channel and sends the reply

Security (WP-P0-004):
    This surface can inject responses into tmux Claude Code sessions
    (/cc-prompt button callbacks → watcher.send_response) and relays MFA
    challenge codes (/mfa-challenge). It is therefore an authenticated,
    loopback-first control surface:
      - Binds 127.0.0.1 by default. A wider bind requires the explicit
        governed CC_WEBHOOK_BIND_HOST env override (e.g. the VPS Tailscale
        IP for the Windows→VPS MFA relay).
      - Every control endpoint (/cc-reply, /cc-prompt, /mfa-challenge)
        requires `Authorization: Bearer <CC_WEBHOOK_TOKEN>`. Missing or
        invalid tokens are rejected with 401 BEFORE any side effect.
      - FAIL CLOSED: if CC_WEBHOOK_TOKEN is unset, every control endpoint is
        rejected (503). There is no unauthenticated path.
      - The token is read from env (1Password-injected .env); never hardcoded,
        never accepted in the URL.
    /health is the only unauthenticated endpoint (liveness only, no side effect).

Started as a background task inside discord_bot.py's on_ready.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    import discord

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(_REPO_ROOT / "runtime" / ".env")

# Port for the webhook receiver
CC_WEBHOOK_PORT = int(os.getenv("CC_WEBHOOK_PORT", "8765"))

# Bind host — loopback by default. Widening the bind (e.g. to the VPS Tailscale
# IP so the Windows MFA bridge can reach it) requires an explicit governed
# override AND is only safe because bearer auth is enforced below.
CC_WEBHOOK_BIND_HOST = os.getenv("CC_WEBHOOK_BIND_HOST", "127.0.0.1")

# Control endpoints that require bearer authentication. /health is exempt
# (liveness probe, no side effect).
_AUTH_REQUIRED_PATHS = frozenset({"/cc-reply", "/cc-prompt", "/mfa-challenge"})


def _get_webhook_token() -> str:
    """Bearer token for control-endpoint auth. Env-only (1Password-injected);
    never hardcoded. Empty string means 'no token configured' → fail closed."""
    return os.getenv("CC_WEBHOOK_TOKEN", "").strip()


def _extract_bearer(request: "web.Request") -> str:
    """Extract the bearer token from the Authorization header only.

    Tokens are NEVER read from the URL/query string — header transport only.
    """
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer ") :].strip()
    return ""


@web.middleware
async def _auth_middleware(request: "web.Request", handler):
    """Fail-closed bearer auth for every control endpoint.

    Rejects BEFORE the handler runs (no side effect):
      - 503 if CC_WEBHOOK_TOKEN is not configured (fail closed).
      - 401 if the Authorization: Bearer token is missing or does not match.
    /health and any non-control path pass through unauthenticated.
    """
    if request.path in _AUTH_REQUIRED_PATHS:
        expected = _get_webhook_token()
        if not expected:
            logger.error(
                "[CCWebhook] FAIL CLOSED: CC_WEBHOOK_TOKEN unset — rejecting %s",
                request.path,
            )
            return web.Response(status=503, text="webhook auth not configured")
        presented = _extract_bearer(request)
        # Constant-time comparison; both operands are str.
        if not presented or not hmac.compare_digest(presented, expected):
            logger.warning(
                "[CCWebhook] 401 unauthenticated request to %s from %s",
                request.path,
                request.remote,
            )
            return web.Response(status=401, text="unauthorized")
    return await handler(request)


# Session name → Discord channel ID mapping.
# Built from the same env vars discord_mode_routing uses.
_SESSION_CHANNEL_MAP: dict[str, int] = {}


def _build_session_channel_map() -> dict[str, int]:
    """Build session_name → channel_id map from env vars."""
    from substrate.execution.bridge.claude_session_bridge import make_session_name

    mapping: dict[str, int] = {}

    _default_builder = make_session_name("builder", "main")
    builder_session = os.getenv("EOS_DISCORD_BUILDER_SESSION", _default_builder)
    builder_channels = os.getenv("EOS_DISCORD_BUILDER_CHANNELS", "")
    if builder_session and builder_channels:
        first = builder_channels.split(",")[0].strip()
        if first:
            mapping[builder_session] = int(first)

    _default_product = make_session_name("product", "main")
    product_session = os.getenv("EOS_DISCORD_PRODUCT_SESSION", _default_product)
    product_channels = os.getenv("EOS_DISCORD_PRODUCT_CHANNELS", "")
    if product_session and product_channels:
        first = product_channels.split(",")[0].strip()
        if first:
            mapping[product_session] = int(first)

    general_id = os.getenv("EOS_DISCORD_GENERAL_CHANNEL", "")
    if general_id:
        mapping[make_session_name("main")] = int(general_id)

    _local_key = make_session_name("local")
    if _local_key not in mapping and builder_channels:
        first = builder_channels.split(",")[0].strip()
        if first:
            mapping[_local_key] = int(first)

    return mapping


def _chunk_message(content: str, max_len: int = 1900) -> list[str]:
    """Split long messages into Discord-safe chunks."""
    if len(content) <= max_len:
        return [content]
    chunks = []
    while content:
        if len(content) <= max_len:
            chunks.append(content)
            break
        # Find a good split point
        split = content.rfind("\n", 0, max_len)
        if split < max_len // 2:
            split = content.rfind(" ", 0, max_len)
        if split < max_len // 4:
            split = max_len
        chunks.append(content[:split])
        content = content[split:].lstrip("\n")
    return chunks


async def start_webhook_server(
    bot: discord.Bot,
    ai_name: str,
    port: int = CC_WEBHOOK_PORT,
) -> web.AppRunner:
    """Start the aiohttp webhook server. Call from on_ready."""
    global _SESSION_CHANNEL_MAP
    _SESSION_CHANNEL_MAP = _build_session_channel_map()
    logger.info("[CCWebhook] Session→Channel map: %s", _SESSION_CHANNEL_MAP)

    if not _get_webhook_token():
        logger.warning(
            "[CCWebhook] CC_WEBHOOK_TOKEN is not set — control endpoints will "
            "fail closed (503) until it is configured."
        )

    app = web.Application(middlewares=[_auth_middleware])

    async def handle_cc_reply(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.Response(status=400, text="invalid json")

        session_name = data.get("session_name", "")
        text = data.get("text", "").strip()

        if not session_name or not text:
            return web.Response(status=400, text="missing session_name or text")

        channel_id = _SESSION_CHANNEL_MAP.get(session_name)
        if not channel_id:
            logger.warning(
                "[CCWebhook] No channel mapping for session '%s'",
                session_name,
            )
            return web.Response(status=404, text=f"no channel for {session_name}")

        channel = bot.get_channel(channel_id)
        if not channel:
            logger.warning(
                "[CCWebhook] Channel %d not found in bot cache",
                channel_id,
            )
            return web.Response(status=404, text="channel not found")

        # Add footer and send
        footer = f"\n\n— {ai_name}  ·  claude_cli/{session_name}"
        output = text.rstrip() + footer

        try:
            for chunk in _chunk_message(output):
                await channel.send(chunk)
            logger.info(
                "[CCWebhook] Delivered %d chars to channel %d (%s)",
                len(text),
                channel_id,
                session_name,
            )
        except Exception as exc:
            logger.error("[CCWebhook] Send failed: %s", exc)
            return web.Response(status=500, text=str(exc))

        return web.Response(status=200, text="ok")

    async def handle_cc_prompt(request: web.Request) -> web.Response:
        """Handle interactive prompts (plan mode, permission, questions).

        Expects: {session_name, text, requires_response, prompt_type}
        Sends to Discord with interactive buttons via session_discord_bridge.
        Button callbacks route back through watcher.send_response() → tmux.
        """
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.Response(status=400, text="invalid json")

        session_name = data.get("session_name", "")
        text = data.get("text", "").strip()
        prompt_type = data.get("prompt_type", "permission")

        if not session_name or not text:
            return web.Response(status=400, text="missing session_name or text")

        channel_id = _SESSION_CHANNEL_MAP.get(session_name)
        if not channel_id:
            logger.warning(
                "[CCWebhook] No channel mapping for prompt session '%s'",
                session_name,
            )
            return web.Response(status=404, text=f"no channel for {session_name}")

        channel = bot.get_channel(channel_id)
        if not channel:
            return web.Response(status=404, text="channel not found")

        # Build a WatcherEvent and format it through the bridge
        try:
            from substrate.execution.bridge.session_watcher import SessionState, WatcherEvent
            from substrate.execution.bridge.session_discord_bridge import format_event

            state_map = {
                "plan": SessionState.PLAN_MODE,
                "permission": SessionState.PERMISSION_REQUEST,
                "question": SessionState.WAITING_QUESTION,
            }
            state = state_map.get(prompt_type, SessionState.PERMISSION_REQUEST)

            event = WatcherEvent(
                session_name=session_name,
                state=state,
                text=text,
            )
            formatted = format_event(event)

            if formatted.get("content"):
                kwargs = {"content": formatted["content"]}
                if formatted.get("view"):
                    kwargs["view"] = formatted["view"]
                await channel.send(**kwargs)
                logger.info(
                    "[CCWebhook] Sent %s prompt to channel %d (%s)",
                    prompt_type,
                    channel_id,
                    session_name,
                )
        except Exception as exc:
            logger.error("[CCWebhook] Prompt send failed: %s", exc)
            return web.Response(status=500, text=str(exc))

        return web.Response(status=200, text="ok")

    async def handle_health(_request: web.Request) -> web.Response:
        return web.Response(status=200, text="ok")

    async def handle_mfa_challenge(request: web.Request) -> web.Response:
        """Receive MFA challenge from Windows bridge and surface to Discord.

        Payload: {type: "mfa_challenge", service: str, mfa_type: str, url: str, ...}
        Surfaces as a Discord message with the challenge details.
        User responds in Discord → trigger_export routes response back.
        """
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.Response(status=400, text="invalid json")

        service = data.get("service", "unknown")
        mfa_type = data.get("mfa_type", "UNKNOWN")
        url = data.get("url", "")

        # Find the builder channel (or general) for MFA notifications
        from substrate.execution.bridge.claude_session_bridge import make_session_name

        channel_id = (
            _SESSION_CHANNEL_MAP.get(make_session_name("builder", "main"))
            or _SESSION_CHANNEL_MAP.get(make_session_name("main"))
            or next(iter(_SESSION_CHANNEL_MAP.values()), None)
        )

        if not channel_id:
            logger.error("[CCWebhook] No channel available for MFA notification")
            return web.Response(status=404, text="no channel configured")

        channel = bot.get_channel(channel_id)
        if not channel:
            return web.Response(status=404, text="channel not found")

        # Build the Discord notification
        mfa_msg = (
            f"🔐 **MFA CHALLENGE — {service.upper()}**\n"
            f"```\n"
            f"Service:  {service}\n"
            f"Type:     {mfa_type}\n"
            f"URL:      {url[:100]}\n"
            f"```\n"
        )

        if mfa_type in ("TOTP", "SMS", "EMAIL_2FA"):
            mfa_msg += f"**Reply with the 6-digit code:**\n`!mfa {service} <code>`\n"
        elif mfa_type == "PUSH":
            mfa_msg += (
                f"**Approve the push notification, then reply:**\n`!mfa {service} approved`\n"
            )
        else:
            mfa_msg += f"**Check screenshot and respond:**\n`!mfa {service} <code-or-approved>`\n"

        try:
            await channel.send(mfa_msg)
            logger.info(
                "[CCWebhook] MFA challenge surfaced to Discord for %s (type=%s)",
                service,
                mfa_type,
            )
        except Exception as exc:
            logger.error("[CCWebhook] MFA Discord send failed: %s", exc)
            return web.Response(status=500, text=str(exc))

        return web.Response(status=200, text="ok")

    app.router.add_post("/cc-reply", handle_cc_reply)
    app.router.add_post("/cc-prompt", handle_cc_prompt)
    app.router.add_post("/mfa-challenge", handle_mfa_challenge)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, CC_WEBHOOK_BIND_HOST, port)
    await site.start()
    logger.info(
        "[CCWebhook] Listening on http://%s:%d/cc-reply (auth=%s)",
        CC_WEBHOOK_BIND_HOST,
        port,
        "on" if _get_webhook_token() else "FAIL-CLOSED (token unset)",
    )
    print(
        f"[CCWebhook] Listening on http://{CC_WEBHOOK_BIND_HOST}:{port}/cc-reply "
        f"(bearer auth {'enabled' if _get_webhook_token() else 'FAIL-CLOSED — token unset'})"
    )
    return runner
