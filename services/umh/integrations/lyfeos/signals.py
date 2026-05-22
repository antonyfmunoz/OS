"""LyfeOS signal emitter — builds SignalEnvelopes from polled LyfeOS database rows."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from services.umh.protocols.signal import SignalUrgency
from services.umh.sockets.envelopes import SignalEnvelope
from services.umh.sockets.protocols import SignalDescriptor

from .correlation import LyfeOSWritebackTarget
from .manifest import INTEGRATION_ID, SIGNAL_DESCRIPTORS
from .tables import GoalRow, HabitLogRow, HealthMetricRow

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

    def build_habit_signal(
        self,
        row: HabitLogRow,
    ) -> tuple[SignalEnvelope, LyfeOSWritebackTarget]:
        """Build a SignalEnvelope from a habit log row."""
        correlation_id = uuid4()
        status = "completed" if row.completed else "missed"
        content = f"[habit_logs] {row.habit_name}: {status}"
        if row.notes:
            content += f" — {row.notes[:80]}"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="lyfeos_habits_logged",
            payload={
                "table_name": "habit_logs",
                "row_id": row.id,
                "user_id": row.user_id,
                "habit_name": row.habit_name,
                "completed": row.completed,
                "notes": row.notes,
                "logged_at": row.logged_at.isoformat(),
                "adapter_name": "lyfeos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"lyfeos:habit_logs:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={"user_id": row.user_id, "table_name": "habit_logs"},
        )

        target = LyfeOSWritebackTarget(
            user_id=row.user_id,
            table_name="habit_logs",
            row_id=row.id,
        )

        return envelope, target

    def build_goal_signal(
        self,
        row: GoalRow,
    ) -> tuple[SignalEnvelope, LyfeOSWritebackTarget]:
        """Build a SignalEnvelope from a goal row."""
        correlation_id = uuid4()
        content = f"[goals] {row.title}: {row.status} ({row.progress_pct}%)"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="lyfeos_goals_updated",
            payload={
                "table_name": "goals",
                "row_id": row.id,
                "user_id": row.user_id,
                "title": row.title,
                "progress_pct": row.progress_pct,
                "status": row.status,
                "updated_at": row.updated_at.isoformat(),
                "adapter_name": "lyfeos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"lyfeos:goals:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={"user_id": row.user_id, "table_name": "goals"},
        )

        target = LyfeOSWritebackTarget(
            user_id=row.user_id,
            table_name="goals",
            row_id=row.id,
        )

        return envelope, target

    def build_health_signal(
        self,
        row: HealthMetricRow,
    ) -> tuple[SignalEnvelope, LyfeOSWritebackTarget]:
        """Build a SignalEnvelope from a health metric row."""
        correlation_id = uuid4()
        unit_str = f" {row.unit}" if row.unit else ""
        content = f"[health_metrics] {row.metric_type}: {row.value}{unit_str}"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="lyfeos_health_logged",
            payload={
                "table_name": "health_metrics",
                "row_id": row.id,
                "user_id": row.user_id,
                "metric_type": row.metric_type,
                "value": row.value,
                "unit": row.unit,
                "logged_at": row.logged_at.isoformat(),
                "adapter_name": "lyfeos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"lyfeos:health_metrics:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.LOW,
            metadata={"user_id": row.user_id, "table_name": "health_metrics"},
        )

        target = LyfeOSWritebackTarget(
            user_id=row.user_id,
            table_name="health_metrics",
            row_id=row.id,
        )

        return envelope, target
