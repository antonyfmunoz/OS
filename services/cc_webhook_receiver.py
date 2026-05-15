"""
CC Reply Webhook Receiver — receives POSTs from the CC Stop hook and
dispatches replies to Discord channels.

Architecture:
    CC session completes a turn
    → Stop hook reads last assistant message from JSONL transcript
    → POSTs {session_name, text} to http://127.0.0.1:8765/cc-reply
    → This receiver maps session_name → Discord channel and sends the reply

Started as a background task inside discord_bot.py's on_ready.
"""

from __future__ import annotations

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

# Session name → Discord channel ID mapping.
# Built from the same env vars discord_mode_routing uses.
_SESSION_CHANNEL_MAP: dict[str, int] = {}


def _build_session_channel_map() -> dict[str, int]:
    """Build session_name → channel_id map from env vars."""
    mapping: dict[str, int] = {}

    builder_session = os.getenv("EOS_DISCORD_BUILDER_SESSION", "dex_builder_main")
    builder_channels = os.getenv("EOS_DISCORD_BUILDER_CHANNELS", "")
    if builder_session and builder_channels:
        # Use the first channel (primary)
        first = builder_channels.split(",")[0].strip()
        if first:
            mapping[builder_session] = int(first)

    product_session = os.getenv("EOS_DISCORD_PRODUCT_SESSION", "dex_product_main")
    product_channels = os.getenv("EOS_DISCORD_PRODUCT_CHANNELS", "")
    if product_session and product_channels:
        first = product_channels.split(",")[0].strip()
        if first:
            mapping[product_session] = int(first)

    # Also map dex_main as fallback to the general channel
    general_id = os.getenv("EOS_DISCORD_GENERAL_CHANNEL", "")
    if general_id:
        mapping["dex_main"] = int(general_id)

    # Local bridge sessions: dex_local maps to builder channel by default
    if "dex_local" not in mapping and builder_channels:
        first = builder_channels.split(",")[0].strip()
        if first:
            mapping["dex_local"] = int(first)

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

    app = web.Application()

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
            from execution.transport.session_watcher import SessionState, WatcherEvent
            from execution.transport.session_discord_bridge import format_event

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

    app.router.add_post("/cc-reply", handle_cc_reply)
    app.router.add_post("/cc-prompt", handle_cc_prompt)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("[CCWebhook] Listening on http://127.0.0.1:%d/cc-reply", port)
    print(f"[CCWebhook] Listening on http://127.0.0.1:{port}/cc-reply")
    return runner
