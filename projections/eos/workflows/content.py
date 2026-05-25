"""Content calendar workflow — schedule and track content across channels.

Trigger: scheduled or manual
Steps: ideate → draft → schedule → publish → measure
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any


@dataclass
class ContentPiece:
    title: str = ""
    channel: str = ""
    content_type: str = ""
    scheduled_for: str = ""
    status: str = "ideated"
    draft: str = ""
    performance: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentCalendar:
    pieces: list[ContentPiece] = field(default_factory=list)
    venture_id: str = ""


class ContentCalendarWorkflow:
    """Content calendar planning and execution."""

    CHANNELS = ["instagram", "twitter", "youtube", "podcast", "newsletter"]
    CONTENT_TYPES = ["post", "story", "reel", "long_form", "thread", "episode"]

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id

    def generate_calendar(self, days: int = 7) -> ContentCalendar:
        """Generate a content calendar for the next N days."""
        pieces = []
        now = datetime.now(timezone.utc)

        for day_offset in range(days):
            target_date = now + timedelta(days=day_offset)
            date_str = target_date.strftime("%Y-%m-%d")

            pieces.append(
                ContentPiece(
                    channel="instagram",
                    content_type="post" if day_offset % 2 == 0 else "story",
                    scheduled_for=date_str,
                    status="planned",
                )
            )

            if day_offset % 3 == 0:
                pieces.append(
                    ContentPiece(
                        channel="twitter",
                        content_type="thread",
                        scheduled_for=date_str,
                        status="planned",
                    )
                )

        return ContentCalendar(pieces=pieces, venture_id=self._venture_id)

    def ideate(self, topic: str, channel: str = "instagram") -> ContentPiece:
        """Generate a content idea. Deterministic template, AI-enhanced when available."""
        piece = ContentPiece(
            title=topic[:100],
            channel=channel,
            content_type="post",
            status="ideated",
        )

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Create a {channel} content idea about: {topic}\n"
                    f"Brand: Lyfe Institute / Initiate Arena. Voice: bold, direct.\n"
                    f"Return: title + 2-sentence hook."
                ),
                system="You create content for a personal development brand targeting men 18-25.",
                task_type="fast_response",
            )
            if result.output:
                piece.draft = result.output.strip()[:500]
                lines = piece.draft.split("\n")
                if lines:
                    piece.title = lines[0][:100]
        except Exception:
            piece.draft = f"Draft about {topic} for {channel}"

        return piece
