"""Content calendar workflow — schedule and track content across channels.

Trigger: scheduled or manual
Steps: ideate → draft → schedule → publish → measure
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from projections.eos.workflows.types import WorkflowStep


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

    def steps(self, days: int = 7) -> list[WorkflowStep]:
        """Return governed workflow steps for the WorkflowRunner."""
        self._days = days
        self._calendar: ContentCalendar | None = None
        return [
            WorkflowStep(
                name="generate_calendar",
                mutation_name="command_submit",
                intent=f"Generate content calendar for {days} days",
                execute_fn=lambda: self._step_generate(),
            ),
            WorkflowStep(
                name="ideate_content",
                mutation_name="command_submit",
                intent=f"Ideate content for {days}-day calendar",
                execute_fn=lambda: self._step_ideate(),
            ),
        ]

    def _step_generate(self) -> tuple[str, bool]:
        self._calendar = self.generate_calendar(self._days)
        return (
            f"Calendar generated: {len(self._calendar.pieces)} pieces over {self._days} days",
            True,
        )

    def _step_ideate(self) -> tuple[str, bool]:
        if not self._calendar or not self._calendar.pieces:
            return ("No calendar to ideate for", False)
        ideated = 0
        for piece in self._calendar.pieces[:5]:
            if not piece.title:
                result = self.ideate(
                    f"{piece.channel} {piece.content_type} for {piece.scheduled_for}",
                    piece.channel,
                )
                piece.title = result.title
                piece.draft = result.draft
                ideated += 1
        return (f"Ideated {ideated} content pieces", True)

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
            from projections.eos import instance

            bis = instance.load_bis(self._org_id, self._venture_id)
            _brand = instance.brand(bis)
            _offer = instance.offer_name(bis)
            _icp = instance.icp(bis)
            result = call_with_fallback(
                prompt=(
                    f"Create a {channel} content idea about: {topic}\n"
                    f"Brand: {_brand} / {_offer}. Voice: bold, direct.\n"
                    f"Return: title + 2-sentence hook."
                ),
                system=f"You create content for {_brand} targeting {_icp}.",
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
