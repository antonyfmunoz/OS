"""Approval bridge — Discord interactive buttons for governance approvals.

Sends approval requests as Discord messages with Approve/Deny buttons.
Button callbacks route decisions back through ApprovalStore.decide().
Also pushes approval events to cockpit WS for real-time UI updates.

Registered as the concrete implementation of alert_approval() at startup.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import discord

logger = logging.getLogger(__name__)

_BUTTON_TIMEOUT = 120.0

_bot: discord.Bot | None = None
_channel_id: str = ""


def set_bot(bot: discord.Bot) -> None:
    """Register the Discord bot instance. Called once from on_ready."""
    global _bot
    _bot = bot


def set_channel(channel_id: str) -> None:
    """Set the target channel for approval notifications."""
    global _channel_id
    _channel_id = channel_id or os.getenv("DISCORD_FOUNDERS_OFFICE", "")


class GovernanceApprovalView(discord.ui.View):
    """Approve/Deny buttons for organism governance approvals."""

    def __init__(self, approval_id: str, *, timeout: float = _BUTTON_TIMEOUT) -> None:
        super().__init__(timeout=timeout)
        self.approval_id = approval_id
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

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅")
    async def approve(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.responded:
            await interaction.response.send_message("Already responded.", ephemeral=True)
            return
        self.responded = True
        decided_by = str(interaction.user)
        try:
            from substrate.organism.approval_store import ApprovalStore

            store = ApprovalStore()
            result = store.decide(self.approval_id, "approved", decided_by=decided_by)
            if result:
                await interaction.response.edit_message(
                    content=f"✅ **Approved** by {decided_by}\n`{self.approval_id}`",
                    view=None,
                )
            else:
                await interaction.response.edit_message(
                    content=f"❌ Approval `{self.approval_id}` not found.",
                    view=None,
                )
        except Exception as exc:
            logger.error("approval button callback failed: %s", exc)
            await interaction.response.edit_message(
                content=f"❌ Error processing approval: {exc}",
                view=None,
            )

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="❌")
    async def deny(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.responded:
            await interaction.response.send_message("Already responded.", ephemeral=True)
            return
        self.responded = True
        decided_by = str(interaction.user)
        try:
            from substrate.organism.approval_store import ApprovalStore

            store = ApprovalStore()
            result = store.decide(self.approval_id, "denied", decided_by=decided_by)
            if result:
                await interaction.response.edit_message(
                    content=f"❌ **Denied** by {decided_by}\n`{self.approval_id}`",
                    view=None,
                )
            else:
                await interaction.response.edit_message(
                    content=f"❌ Approval `{self.approval_id}` not found.",
                    view=None,
                )
        except Exception as exc:
            logger.error("denial button callback failed: %s", exc)
            await interaction.response.edit_message(
                content=f"❌ Error processing denial: {exc}",
                view=None,
            )


def _format_approval_message(approval: dict[str, Any]) -> str:
    """Format an approval dict into a Discord message string."""
    event = approval.get("event", "created")
    title = approval.get("title", "Unknown")
    risk = approval.get("risk_level", "medium")
    agent = approval.get("agent", "system")
    approval_id = approval.get("id", "")
    description = approval.get("description", "")

    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(
        risk, "⚪"
    )

    if event == "decided":
        status = approval.get("status", "unknown")
        decided_by = approval.get("decided_by", "unknown")
        status_emoji = "✅" if status == "approved" else "❌"
        return (
            f"{status_emoji} **Approval {status}** by {decided_by}\n"
            f"{risk_emoji} {risk.upper()} | Agent: `{agent}`\n"
            f"**{title}**"
        )

    return (
        f"🔔 **Governance Approval Required**\n"
        f"{risk_emoji} Risk: **{risk.upper()}** | Agent: `{agent}`\n"
        f"**{title}**\n"
        f"{description[:300]}"
    )


def handle_approval_alert(approval: dict[str, Any]) -> None:
    """Concrete implementation of alert_approval — sends to Discord + cockpit WS.

    Called from any thread. Schedules async Discord send on the bot's event loop.
    Also pushes to cockpit WS via push_organism_event.
    """
    try:
        from transports.api.cockpit import push_organism_event

        push_organism_event({
            "type": "approval",
            "event": approval.get("event", "created"),
            "approval": approval,
        })
    except Exception as exc:
        logger.debug("cockpit WS push for approval failed: %s", exc)

    if not _bot or not _channel_id:
        logger.debug("Discord bot not available for approval alert")
        return

    try:
        channel_id_int = int(_channel_id)
    except (ValueError, TypeError):
        logger.warning("invalid DISCORD_FOUNDERS_OFFICE channel ID: %s", _channel_id)
        return

    event = approval.get("event", "created")
    content = _format_approval_message(approval)

    async def _send() -> None:
        channel = _bot.get_channel(channel_id_int)
        if not channel:
            logger.warning("Discord channel %s not found", channel_id_int)
            return
        if event == "created":
            view = GovernanceApprovalView(approval.get("id", ""))
            await channel.send(content=content, view=view)
        else:
            await channel.send(content=content)

    try:
        loop = _bot.loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), loop)
        else:
            logger.debug("bot event loop not running, skipping Discord approval alert")
    except Exception as exc:
        logger.warning("failed to schedule Discord approval alert: %s", exc)
