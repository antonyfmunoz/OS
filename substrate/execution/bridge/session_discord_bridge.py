"""
Session Discord Bridge — routes SessionWatcher events to Discord and back.

Receives state events from SessionWatcher, formats Discord notifications with
interactive buttons, and routes Discord responses back into tmux sessions.

Design invariants:
  - No hot-path imports (gateway, cognitive_loop, model_router, agent_runtime)
  - Stateless bridge: all state lives in SessionWatcher
  - Uses py-cord discord.ui.View for interactive buttons
  - Graceful degradation: if discord bot/channel unavailable, events are logged only
  - Per-session channel routing: builder → builder channel, product → product channel
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import threading
from typing import Any

# Path bootstrap
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import discord

from substrate.execution.bridge.claude_session_bridge import make_session_name as _msn
from substrate.execution.bridge.session_watcher import (
    SessionState,
    WatcherEvent,
    get_watcher,
)

LAYER_NAME = "session_discord_bridge"
LAYER_VERSION = "v2"

# ─── Config ──────────────────────────────────────────────────────────────────

# Fallback channel (used when no per-session channel matches)
_NOTIFY_CHANNEL_NAME = os.getenv("EOS_WATCHER_CHANNEL", "agent-activity")

# Per-session channel routing (session_name → channel ID)
_BUILDER_CHANNEL_ID = os.getenv("EOS_DISCORD_BUILDER_CHANNELS", "")
_PRODUCT_CHANNEL_ID = os.getenv("EOS_DISCORD_PRODUCT_CHANNELS", "")
_BUILDER_SESSION = os.getenv("EOS_DISCORD_BUILDER_SESSION") or _msn("builder", "main")
_PRODUCT_SESSION = os.getenv("EOS_DISCORD_PRODUCT_SESSION") or _msn("product", "main")

# Max chars for plan/question text in Discord messages
_MAX_DISPLAY_CHARS = 1500

# Button timeout in seconds
_BUTTON_TIMEOUT = 60.0

# Regex for detecting numbered options (e.g. "1. Option one\n2. Option two")
_OPTION_RE = re.compile(r"^(\d+)[.)]\s+(.+)$", re.MULTILINE)


# ─── Discord UI components ───────────────────────────────────────────────────


class PlanApprovalView(discord.ui.View):
    """Buttons for approving, rejecting, or editing a CC plan."""

    def __init__(self, session_name: str, *, timeout: float = _BUTTON_TIMEOUT) -> None:
        super().__init__(timeout=timeout)
        self.session_name = session_name
        self.responded = False

    async def on_timeout(self) -> None:
        """Disable buttons and post expiration notice."""
        if not self.responded:
            try:
                self.disable_all_items()
                if self.message:
                    await self.message.edit(
                        content=self.message.content + "\n\n*Interaction expired.*",
                        view=self,
                    )
            except Exception:
                pass

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅")
    async def approve(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.responded:
            await interaction.response.send_message(
                "Already responded.", ephemeral=True
            )
            return
        self.responded = True
        watcher = get_watcher(self.session_name)
        if watcher:
            watcher.send_response("1")
        await interaction.response.edit_message(
            content=f"✅ **Plan approved** for `{self.session_name}`",
            view=None,
        )

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, emoji="❌")
    async def reject(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.responded:
            await interaction.response.send_message(
                "Already responded.", ephemeral=True
            )
            return
        self.responded = True
        watcher = get_watcher(self.session_name)
        if watcher:
            watcher.send_response("2")
        await interaction.response.edit_message(
            content=f"❌ **Plan rejected** for `{self.session_name}`",
            view=None,
        )

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.blurple, emoji="✏️")
    async def edit(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.responded:
            await interaction.response.send_message(
                "Already responded.", ephemeral=True
            )
            return
        self.responded = True
        await interaction.response.edit_message(
            content=(
                f"✏️ **Editing plan** for `{self.session_name}`\n"
                f"Reply with `!answer {self.session_name} <your instructions>`"
            ),
            view=None,
        )


class PermissionView(discord.ui.View):
    """Buttons for allowing or denying a CC permission request."""

    def __init__(self, session_name: str, *, timeout: float = _BUTTON_TIMEOUT) -> None:
        super().__init__(timeout=timeout)
        self.session_name = session_name
        self.responded = False

    async def on_timeout(self) -> None:
        if not self.responded:
            try:
                self.disable_all_items()
                if self.message:
                    await self.message.edit(
                        content=self.message.content + "\n\n*Interaction expired.*",
                        view=self,
                    )
            except Exception:
                pass

    @discord.ui.button(label="Allow", style=discord.ButtonStyle.green, emoji="✅")
    async def allow(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.responded:
            await interaction.response.send_message(
                "Already responded.", ephemeral=True
            )
            return
        self.responded = True
        watcher = get_watcher(self.session_name)
        if watcher:
            watcher.send_response("y")
        await interaction.response.edit_message(
            content=f"✅ **Permission granted** for `{self.session_name}`",
            view=None,
        )

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="❌")
    async def deny(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.responded:
            await interaction.response.send_message(
                "Already responded.", ephemeral=True
            )
            return
        self.responded = True
        watcher = get_watcher(self.session_name)
        if watcher:
            watcher.send_response("n")
        await interaction.response.edit_message(
            content=f"❌ **Permission denied** for `{self.session_name}`",
            view=None,
        )


class QuestionOptionView(discord.ui.View):
    """Buttons for answering a CC multiple-choice question (up to 4 options)."""

    def __init__(
        self,
        session_name: str,
        options: list[tuple[str, str]],
        *,
        timeout: float = _BUTTON_TIMEOUT,
    ) -> None:
        super().__init__(timeout=timeout)
        self.session_name = session_name
        self.responded = False

        # Dynamically add buttons for each option (max 4)
        for label, value in options[:4]:
            btn = discord.ui.Button(
                label=label[:80],
                style=discord.ButtonStyle.blurple,
                custom_id=f"q_{session_name}_{value}",
            )
            btn.callback = self._make_callback(value, label)
            self.add_item(btn)

    def _make_callback(self, value: str, label: str):
        async def callback(interaction: discord.Interaction) -> None:
            if self.responded:
                await interaction.response.send_message(
                    "Already responded.", ephemeral=True
                )
                return
            self.responded = True
            watcher = get_watcher(self.session_name)
            if watcher:
                watcher.send_response(value)
            await interaction.response.edit_message(
                content=f"Selected: **{label}** for `{self.session_name}`",
                view=None,
            )

        return callback

    async def on_timeout(self) -> None:
        if not self.responded:
            try:
                self.disable_all_items()
                if self.message:
                    await self.message.edit(
                        content=self.message.content + "\n\n*Interaction expired.*",
                        view=self,
                    )
            except Exception:
                pass


def _extract_options(text: str) -> list[tuple[str, str]]:
    """Extract numbered options from CC question text.

    Returns list of (display_label, send_value) tuples.
    """
    matches = _OPTION_RE.findall(text)
    if len(matches) < 2 or len(matches) > 4:
        return []
    return [(f"{num}. {desc.strip()}", num) for num, desc in matches]


# ─── Event formatting ────────────────────────────────────────────────────────


def format_event(event: WatcherEvent) -> dict[str, Any]:
    """Format a WatcherEvent into Discord message kwargs (content, view).

    Returns a dict with:
      - content: str (the message text)
      - view: discord.ui.View | None (interactive buttons if applicable)
    """
    session_label = event.session_name.replace("_", " ").title()
    text = event.text[:_MAX_DISPLAY_CHARS]

    if event.state == SessionState.WAITING_QUESTION:
        options = _extract_options(text)
        if options:
            return {
                "content": (f"🤔 **{session_label} is asking:**\n```\n{text}\n```"),
                "view": QuestionOptionView(event.session_name, options),
            }
        return {
            "content": (
                f"🤔 **{session_label} is asking:**\n"
                f"```\n{text}\n```\n"
                f"*Reply with* `!answer {event.session_name} <your response>`"
            ),
            "view": None,
        }

    elif event.state == SessionState.PLAN_MODE:
        return {
            "content": (f"📋 **{session_label} proposes a plan:**\n```\n{text}\n```"),
            "view": PlanApprovalView(event.session_name),
        }

    elif event.state == SessionState.PERMISSION_REQUEST:
        return {
            "content": (f"🔐 **{session_label} needs permission:**\n```\n{text}\n```"),
            "view": PermissionView(event.session_name),
        }

    elif event.state == SessionState.IDLE:
        return {"content": None, "view": None}

    return {"content": None, "view": None}


# ─── Channel routing ────────────────────────────────────────────────────────


def _resolve_channel_id(session_name: str) -> int | None:
    """Resolve session name to the correct Discord channel ID."""
    if session_name == _BUILDER_SESSION and _BUILDER_CHANNEL_ID:
        try:
            return int(_BUILDER_CHANNEL_ID)
        except ValueError:
            pass
    if session_name == _PRODUCT_SESSION and _PRODUCT_CHANNEL_ID:
        try:
            return int(_PRODUCT_CHANNEL_ID)
        except ValueError:
            pass
    return None


# ─── Bridge singleton ────────────────────────────────────────────────────────


class SessionDiscordBridge:
    """Bridges SessionWatcher events to a Discord bot instance.

    Call set_bot() once the discord bot is ready, then use on_watcher_event()
    as the SessionWatcher callback.
    """

    def __init__(self) -> None:
        self._bot: discord.Bot | None = None
        self._fallback_channel: discord.abc.Messageable | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_bot(self, bot: discord.Bot) -> None:
        """Register the discord bot instance. Call from on_ready."""
        self._bot = bot
        self._loop = bot.loop
        # Find the fallback notification channel by name
        for guild in bot.guilds:
            for channel in guild.text_channels:
                if channel.name == _NOTIFY_CHANNEL_NAME:
                    self._fallback_channel = channel
                    print(
                        f"[SessionDiscordBridge] Fallback channel: "
                        f"#{channel.name} in {guild.name}"
                    )
                    return
        print(
            f"[SessionDiscordBridge] Warning: channel '{_NOTIFY_CHANNEL_NAME}' "
            f"not found — notifications will be logged only"
        )

    def _get_channel(self, session_name: str) -> discord.abc.Messageable | None:
        """Get the Discord channel for a session (per-session or fallback)."""
        channel_id = _resolve_channel_id(session_name)
        if channel_id and self._bot:
            ch = self._bot.get_channel(channel_id)
            if ch:
                return ch
        return self._fallback_channel

    def on_watcher_event(self, event: WatcherEvent) -> None:
        """Callback for SessionWatcher — formats and sends Discord notification.

        This runs in the watcher's daemon thread, so we schedule the async
        send onto the bot's event loop.
        """
        if not self._bot or not self._loop:
            print(f"[SessionDiscordBridge] Event (no bot): {event.state.value}")
            return

        formatted = format_event(event)
        if not formatted.get("content"):
            return

        channel = self._get_channel(event.session_name)
        asyncio.run_coroutine_threadsafe(
            self._send_notification(formatted, channel),
            self._loop,
        )

    async def _send_notification(
        self,
        formatted: dict[str, Any],
        channel: discord.abc.Messageable | None = None,
    ) -> None:
        """Send formatted notification to Discord channel."""
        channel = channel or self._fallback_channel
        if not channel:
            print("[SessionDiscordBridge] No channel — skipping notification")
            return

        try:
            kwargs: dict[str, Any] = {"content": formatted["content"]}
            if formatted.get("view"):
                kwargs["view"] = formatted["view"]
            await channel.send(**kwargs)
        except Exception as e:
            print(f"[SessionDiscordBridge] Send error: {e}")

    async def handle_answer_command(self, session_name: str, answer_text: str) -> str:
        """Handle !answer command — pipe text back into session."""
        watcher = get_watcher(session_name)
        if not watcher:
            return f"No active watcher for `{session_name}`"

        result = watcher.send_response(answer_text)
        if result.get("ok"):
            return f"Sent to `{session_name}`: {answer_text[:100]}"
        return f"Failed to send: {result.get('reason', 'unknown')}"


# Module-level singleton
_bridge = SessionDiscordBridge()


def get_bridge() -> SessionDiscordBridge:
    """Get the module-level bridge singleton."""
    return _bridge


async def send_reply(channel, text: str) -> None:
    """Send a message to a Discord channel, splitting if over 2000 chars."""
    if not text:
        return
    # Discord limit is 2000 chars per message
    while len(text) > 2000:
        split_at = text.rfind("\n", 0, 2000)
        if split_at == -1:
            split_at = 2000
        await channel.send(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        await channel.send(text)


__all__ = [
    "LAYER_NAME",
    "LAYER_VERSION",
    "PlanApprovalView",
    "PermissionView",
    "QuestionOptionView",
    "SessionDiscordBridge",
    "format_event",
    "get_bridge",
    "send_reply",
]
