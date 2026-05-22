"""Discord signal factory -- converts Discord messages to SignalEnvelopes.

Handles text, voice, image, and multimodal messages.
"""

from __future__ import annotations

from typing import Any

from substrate.types import (
    Attachment,
    Modality,
    SignalEnvelope,
    SignalSource,
)


_VOICE_MIMES = {"audio/ogg", "audio/mpeg", "audio/wav", "audio/mp4"}
_IMAGE_MIMES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


def message_to_signal(msg: Any, organization_id: str) -> SignalEnvelope:
    """Convert a discord.Message to a SignalEnvelope.

    Args:
        msg: A discord.py Message object (or any duck-typed equivalent).
        organization_id: The org this message belongs to.

    Returns:
        A fully-formed SignalEnvelope ready for spine routing.
    """
    content = msg.content or ""
    user_id = str(msg.author.id)
    attachments: list[Attachment] = []
    has_voice = False
    has_image = False

    for att in msg.attachments:
        mime = getattr(att, "content_type", "") or ""
        attachments.append(
            Attachment(
                filename=att.filename,
                mime_type=mime[:120],
                url=att.url,
            )
        )
        if any(mime.startswith(v.split("/")[0]) for v in _VOICE_MIMES):
            has_voice = True
        if any(mime.startswith(v.split("/")[0]) for v in _IMAGE_MIMES):
            has_image = True

    if has_voice and not content:
        modality = Modality.VOICE
    elif has_image and content:
        modality = Modality.MULTIMODAL
    elif has_image:
        modality = Modality.IMAGE
    else:
        modality = Modality.TEXT

    metadata = {
        "guild_id": str(msg.guild.id) if msg.guild else None,
        "channel_id": str(msg.channel.id),
        "author_name": msg.author.name,
    }

    return SignalEnvelope(
        source=SignalSource.USER,
        content=content,
        user_id=user_id,
        organization_id=organization_id,
        modality=modality,
        attachments=attachments,
        metadata=metadata,
    )
