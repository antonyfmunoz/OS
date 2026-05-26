"""LyfeOS signal emitter — builds SignalEnvelopes from polled LyfeOS database rows."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from substrate.types import IntegrationSignalEnvelope as SignalEnvelope, SignalDescriptor, SignalUrgency

from .correlation import LyfeOSWritebackTarget
from .manifest import INTEGRATION_ID, SIGNAL_DESCRIPTORS
from .tables import DailyLogRow, QuestRow, UserStatsRow

logger = logging.getLogger(__name__)


class LyfeOSSignalEmitter:
    """Declares signal types and builds envelopes from polled LyfeOS rows.

    Satisfies SignalEmitter Protocol structurally.
    """

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def describe_signals(self) -> list[SignalDescriptor]:
        return list(SIGNAL_DESCRIPTORS)

    def build_quest_signal(
        self,
        row: QuestRow,
    ) -> tuple[SignalEnvelope, LyfeOSWritebackTarget]:
        """Build a SignalEnvelope from a quest row."""
        correlation_id = uuid4()
        status = "completed" if row.completed else row.mission_status
        content = f"[quests] {row.title}: {status} (difficulty={row.difficulty})"
        if row.description:
            content += f" — {row.description[:80]}"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="lyfeos_quest_completed",
            payload={
                "table_name": "quests",
                "row_id": str(row.id),
                "user_id": str(row.user_id),
                "title": row.title,
                "category": row.category,
                "completed": row.completed,
                "difficulty": row.difficulty,
                "energy_cost": row.energy_cost,
                "experience_reward": row.experience_reward,
                "is_ritualized": row.is_ritualized,
                "mission_status": row.mission_status,
                "created_at": row.created_at.isoformat(),
                "adapter_name": "lyfeos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"lyfeos:quests:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={"user_id": str(row.user_id), "table_name": "quests"},
        )

        target = LyfeOSWritebackTarget(
            user_id=row.user_id,
            table_name="quests",
            row_id=str(row.id),
        )

        return envelope, target

    def build_daily_log_signal(
        self,
        row: DailyLogRow,
    ) -> tuple[SignalEnvelope, LyfeOSWritebackTarget]:
        """Build a SignalEnvelope from a daily log row."""
        correlation_id = uuid4()
        content = (
            f"[user_daily_logs] {row.date}: "
            f"mental={row.mental_state} physical={row.physical_state} "
            f"emotional={row.emotional_state}"
        )
        if row.gratitude:
            content += f" — {row.gratitude[:60]}"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="lyfeos_daily_log_created",
            payload={
                "table_name": "user_daily_logs",
                "row_id": str(row.id),
                "user_id": str(row.user_id),
                "date": row.date,
                "mental_state": row.mental_state,
                "physical_state": row.physical_state,
                "emotional_state": row.emotional_state,
                "gratitude": row.gratitude or "",
                "went_well": row.went_well or "",
                "created_at": row.created_at.isoformat(),
                "adapter_name": "lyfeos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"lyfeos:user_daily_logs:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.LOW,
            metadata={"user_id": str(row.user_id), "table_name": "user_daily_logs"},
        )

        target = LyfeOSWritebackTarget(
            user_id=row.user_id,
            table_name="user_daily_logs",
            row_id=str(row.id),
        )

        return envelope, target

    def build_stats_signal(
        self,
        row: UserStatsRow,
    ) -> tuple[SignalEnvelope, LyfeOSWritebackTarget]:
        """Build a SignalEnvelope from a user stats row."""
        correlation_id = uuid4()
        content = (
            f"[user_stats] level={row.level} "
            f"xp={row.experience_current}/{row.experience_max} "
            f"streak={row.streak_days}d"
        )

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="lyfeos_stats_updated",
            payload={
                "table_name": "user_stats",
                "row_id": str(row.id),
                "user_id": str(row.user_id),
                "level": row.level,
                "experience_current": row.experience_current,
                "experience_max": row.experience_max,
                "energy_points_current": row.energy_points_current,
                "energy_points_max": row.energy_points_max,
                "health_points_current": row.health_points_current,
                "health_points_max": row.health_points_max,
                "streak_days": row.streak_days,
                "updated_at": row.updated_at.isoformat(),
                "adapter_name": "lyfeos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"lyfeos:user_stats:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={"user_id": str(row.user_id), "table_name": "user_stats"},
        )

        target = LyfeOSWritebackTarget(
            user_id=row.user_id,
            table_name="user_stats",
            row_id=str(row.id),
        )

        return envelope, target
