"""
EOS Channel System
==================
Adapted from OpenClaw's channel adapter pattern.

Channels are two-way execution surfaces, not notification sinks.
  Inbound: Discord message → EOS agent runs
  Outbound: EOS agent completes → Discord post

Adding a channel = one new class.
Zero changes to agent layer.
Zero changes to permission logic.

Current: Discord (bot running), Telegram (configured)
Planned: iMessage, WhatsApp, Slack

Channel priority:
1. Discord — already configured, bot running
2. Telegram — configured, token + chat_id set
3. Webhook — generic, for n8n/Make/Zapier
4. Console — always available fallback
"""

import json
import logging
import os
import urllib.request
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ChannelType(Enum):
    DISCORD = "discord"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    IMESSAGE = "imessage"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"
    CONSOLE = "console"


@dataclass
class Message:
    """Normalized message object."""
    body: str
    sender: str = ""
    channel: str = ""
    channel_id: str = ""
    thread_id: str = ""
    attachments: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ChannelConfig:
    """Configuration for a channel instance."""
    channel_type: ChannelType
    token: str = ""
    channel_id: str = ""
    webhook_url: str = ""
    enabled: bool = True


class Channel(ABC):
    """
    Abstract channel interface.
    send(): outbound notification
    send_approval_request(): outbound with approve/deny
    is_available(): check if channel configured
    """

    @abstractmethod
    def send(self, message: str,
             thread_id: str = "") -> bool:
        pass

    @abstractmethod
    def send_approval_request(
        self,
        title: str,
        body: str,
        request_id: str,
        auto_approve_after_seconds: int = 0,
    ) -> bool:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    def send_safe(self, message: str) -> bool:
        """Send with fallback to console on failure."""
        try:
            if self.is_available():
                return self.send(message)
        except Exception as e:
            logger.error(
                f"[Channel] {self.__class__.__name__} "
                f"send failed: {e}"
            )
        print(f"[Channel:console] {message}")
        return False


class DiscordChannel(Channel):
    """Discord via Bot API."""

    def __init__(self, config: ChannelConfig):
        self.config = config
        self._base_url = "https://discord.com/api/v10"

    def _post(self, endpoint: str,
              payload: dict) -> bool:
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self._base_url}{endpoint}",
                data=data,
                headers={
                    "Authorization":
                        f"Bot {self.config.token}",
                    "Content-Type":
                        "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(
                req, timeout=5
            ) as resp:
                return resp.status in (200, 201)
        except Exception as e:
            logger.error(f"[Discord] POST failed: {e}")
            return False

    def send(self, message: str,
             thread_id: str = "") -> bool:
        channel_id = thread_id or self.config.channel_id
        if not channel_id:
            return False
        return self._post(
            f"/channels/{channel_id}/messages",
            {"content": message[:2000]},
        )

    def send_approval_request(
        self,
        title: str,
        body: str,
        request_id: str,
        auto_approve_after_seconds: int = 0,
    ) -> bool:
        short_id = request_id[:8]
        embed = {
            "title": f"\U0001f510 {title}",
            "description": body[:1000],
            "color": 0xFFA500,
            "footer": {
                "text": f"ID: {short_id} | Reply approve or deny"
            },
        }
        return self._post(
            f"/channels/{self.config.channel_id}/messages",
            {"embeds": [embed]},
        )

    def is_available(self) -> bool:
        return bool(self.config.token and self.config.channel_id)


class TelegramChannel(Channel):
    """Telegram via Bot API."""

    def __init__(self, config: ChannelConfig):
        self.config = config

    def _post(self, method: str,
              payload: dict) -> bool:
        try:
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/"
                f"bot{self.config.token}/{method}",
                data=data,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception as e:
            logger.error(f"[Telegram] POST failed: {e}")
            return False

    def send(self, message: str,
             thread_id: str = "") -> bool:
        return self._post("sendMessage", {
            "chat_id": self.config.channel_id,
            "text": message[:4096],
            "parse_mode": "Markdown",
        })

    def send_approval_request(
        self,
        title: str,
        body: str,
        request_id: str,
        auto_approve_after_seconds: int = 0,
    ) -> bool:
        short_id = request_id[:8]
        msg = (
            f"\U0001f510 *{title}*\n\n"
            f"{body}\n\n"
            f"Reply:\n"
            f"approve\\_{short_id}\n"
            f"deny\\_{short_id}"
        )
        return self._post("sendMessage", {
            "chat_id": self.config.channel_id,
            "text": msg[:4096],
            "parse_mode": "Markdown",
        })

    def is_available(self) -> bool:
        return bool(self.config.token and self.config.channel_id)


class WebhookChannel(Channel):
    """Generic webhook channel for n8n, Make, Zapier."""

    def __init__(self, config: ChannelConfig):
        self.config = config

    def send(self, message: str,
             thread_id: str = "") -> bool:
        if not self.config.webhook_url:
            return False
        try:
            data = json.dumps({
                "text": message,
                "source": "eos",
            }).encode()
            req = urllib.request.Request(
                self.config.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception as e:
            logger.error(f"[Webhook] POST failed: {e}")
            return False

    def send_approval_request(
        self,
        title: str,
        body: str,
        request_id: str,
        auto_approve_after_seconds: int = 0,
    ) -> bool:
        return self.send(
            f"\U0001f510 {title}\n{body}\nID: {request_id[:8]}"
        )

    def is_available(self) -> bool:
        return bool(self.config.webhook_url)


class ConsoleChannel(Channel):
    """Console fallback — always available."""

    def send(self, message: str,
             thread_id: str = "") -> bool:
        print(f"[EOS] {message}")
        return True

    def send_approval_request(
        self,
        title: str,
        body: str,
        request_id: str,
        auto_approve_after_seconds: int = 0,
    ) -> bool:
        print(f"[EOS:Permission] {title}")
        print(f"{body}")
        print(f"ID: {request_id[:8]}")
        return True

    def is_available(self) -> bool:
        return True


class ChannelRouter:
    """
    Single control plane for all channels.

    Usage:
        router = ChannelRouter.from_env()
        router.notify("Agent task complete")
        router.request_approval(
            title="Delete file?",
            body="rm /opt/OS/important.py",
            request_id="abc123",
        )

    Adding a new channel:
        1. Add ChannelType enum value
        2. Create ChannelImpl(Channel) class
        3. Add to from_env()
    """

    def __init__(self, channels: list[Channel]):
        self.channels = channels
        self._primary = self._find_primary()

    def _find_primary(self) -> Channel:
        for ch in self.channels:
            if ch.is_available():
                return ch
        return ConsoleChannel()

    @classmethod
    def from_env(cls) -> "ChannelRouter":
        """Build router from environment variables."""
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

        channels: list[Channel] = []

        # Discord — prefer webhook (no gateway needed), fall back to bot API
        discord_webhook = os.getenv(
            'DISCORD_NOTIFICATION_WEBHOOK',
            os.getenv('DISCORD_BRIEF_WEBHOOK', '')
        )
        if discord_webhook:
            channels.append(WebhookChannel(
                ChannelConfig(
                    channel_type=ChannelType.DISCORD,
                    webhook_url=discord_webhook,
                )
            ))
        else:
            discord_token = os.getenv('DISCORD_BOT_TOKEN', '')
            discord_channel = os.getenv(
                'DISCORD_NOTIFICATION_CHANNEL_ID',
                os.getenv('DISCORD_CHANNEL_GENERAL', '')
            )
            if discord_token and discord_channel:
                channels.append(DiscordChannel(
                    ChannelConfig(
                        channel_type=ChannelType.DISCORD,
                        token=discord_token,
                        channel_id=discord_channel,
                    )
                ))

        # Telegram
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        telegram_chat = os.getenv('TELEGRAM_CHAT_ID', '')
        if telegram_token and telegram_chat:
            channels.append(TelegramChannel(
                ChannelConfig(
                    channel_type=ChannelType.TELEGRAM,
                    token=telegram_token,
                    channel_id=telegram_chat,
                )
            ))

        # Generic webhook
        webhook_url = os.getenv('NOTIFICATION_WEBHOOK_URL', '')
        if webhook_url:
            channels.append(WebhookChannel(
                ChannelConfig(
                    channel_type=ChannelType.WEBHOOK,
                    webhook_url=webhook_url,
                )
            ))

        # Console always last
        channels.append(ConsoleChannel())

        return cls(channels)

    def notify(
        self,
        message: str,
        all_channels: bool = False,
    ) -> bool:
        """Send notification. Cascades through channels on failure."""
        if all_channels:
            results = [
                ch.send_safe(message)
                for ch in self.channels
                if ch.is_available()
            ]
            return any(results)
        # Cascade: try each channel until one succeeds
        for ch in self.channels:
            if ch.is_available():
                try:
                    if ch.send(message):
                        return True
                except Exception as e:
                    logger.error(
                        f"[ChannelRouter] {ch.__class__.__name__} "
                        f"failed: {e}"
                    )
        # Final fallback
        print(f"[Channel:console] {message}")
        return False

    def request_approval(
        self,
        title: str,
        body: str,
        request_id: str,
        is_safe: bool = False,
    ) -> bool:
        """Send permission approval request. Cascades on failure."""
        if is_safe:
            return self.notify(f"Auto-approved: {title}")
        for ch in self.channels:
            if ch.is_available():
                try:
                    if ch.send_approval_request(
                        title=title, body=body,
                        request_id=request_id,
                    ):
                        return True
                except Exception as e:
                    logger.error(
                        f"[ChannelRouter] {ch.__class__.__name__} "
                        f"approval failed: {e}"
                    )
        return False

    def get_status(self) -> dict:
        """Return status of all channels."""
        return {
            ch.__class__.__name__: ch.is_available()
            for ch in self.channels
        }


def get_channel_router() -> ChannelRouter:
    """Get configured channel router."""
    return ChannelRouter.from_env()
