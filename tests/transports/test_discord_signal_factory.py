"""Tests for Discord signal factory."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/full-convergence")

from unittest.mock import MagicMock

from substrate.types import Modality, SignalEnvelope, SignalSource
from transports.discord.signal_factory import message_to_signal


def _make_msg(
    content: str = "hello world",
    author_id: int = 12345,
    author_name: str = "testuser",
    guild_id: int = 67890,
    channel_id: int = 11111,
    attachments: list | None = None,
) -> MagicMock:
    """Build a minimal discord.Message mock."""
    msg = MagicMock()
    msg.content = content
    msg.author.id = author_id
    msg.author.name = author_name
    msg.guild.id = guild_id
    msg.channel.id = channel_id
    msg.attachments = attachments or []
    return msg


def _make_attachment(
    filename: str = "file.txt",
    content_type: str = "text/plain",
    url: str = "https://cdn.example.com/file.txt",
) -> MagicMock:
    """Build a minimal discord.Attachment mock."""
    att = MagicMock()
    att.filename = filename
    att.content_type = content_type
    att.url = url
    return att


class TestDiscordSignalFactory:
    def test_text_message_produces_signal(self) -> None:
        msg = _make_msg()
        signal = message_to_signal(msg, organization_id="munoz-holdings")

        assert isinstance(signal, SignalEnvelope)
        assert signal.source == SignalSource.USER
        assert signal.content == "hello world"
        assert signal.modality == Modality.TEXT
        assert signal.user_id == "12345"
        assert signal.organization_id == "munoz-holdings"

    def test_voice_attachment_sets_modality(self) -> None:
        att = _make_attachment(
            filename="audio.ogg",
            content_type="audio/ogg",
            url="https://cdn.example.com/audio.ogg",
        )
        msg = _make_msg(content="", attachments=[att])

        signal = message_to_signal(msg, organization_id="munoz-holdings")
        assert signal.modality == Modality.VOICE
        assert len(signal.attachments) == 1
        assert signal.attachments[0].filename == "audio.ogg"

    def test_image_with_text_sets_multimodal(self) -> None:
        att = _make_attachment(
            filename="photo.png",
            content_type="image/png",
            url="https://cdn.example.com/photo.png",
        )
        msg = _make_msg(content="look at this", attachments=[att])

        signal = message_to_signal(msg, organization_id="munoz-holdings")
        assert signal.modality == Modality.MULTIMODAL

    def test_image_without_text_sets_image(self) -> None:
        att = _make_attachment(
            filename="photo.png",
            content_type="image/png",
            url="https://cdn.example.com/photo.png",
        )
        msg = _make_msg(content="", attachments=[att])

        signal = message_to_signal(msg, organization_id="munoz-holdings")
        assert signal.modality == Modality.IMAGE

    def test_none_content_type_handled(self) -> None:
        att = MagicMock()
        att.filename = "unknown.bin"
        att.content_type = None
        att.url = "https://cdn.example.com/unknown.bin"
        msg = _make_msg(content="here", attachments=[att])

        signal = message_to_signal(msg, organization_id="munoz-holdings")
        assert signal.modality == Modality.TEXT
        assert len(signal.attachments) == 1
        assert signal.attachments[0].mime_type == ""

    def test_no_guild_metadata(self) -> None:
        msg = _make_msg()
        msg.guild = None

        signal = message_to_signal(msg, organization_id="munoz-holdings")
        assert signal.metadata["guild_id"] is None
        assert signal.metadata["channel_id"] == "11111"

    def test_metadata_contains_author_name(self) -> None:
        msg = _make_msg(author_name="afm")
        signal = message_to_signal(msg, organization_id="munoz-holdings")
        assert signal.metadata["author_name"] == "afm"
