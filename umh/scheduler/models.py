"""UMH Scheduler Models — schedule types, policies, and workflow definitions.

Defines the data structures for recurring scheduled workflows that generate
PlanObjectives and route through the existing planning pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from umh.core.clock import iso_now as _iso_now

_DAY_MAP: dict[str, int] = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


class ScheduleType(str, Enum):
    """Type of recurring schedule."""

    INTERVAL = "interval"
    DAILY = "daily"
    WEEKLY = "weekly"
    CRON_LIKE = "cron_like"


def compute_next_run(
    schedule_type: ScheduleType,
    schedule_value: str,
    from_time: datetime | None = None,
) -> str:
    """Compute the next run time as an ISO-8601 string.

    Args:
        schedule_type: The type of schedule.
        schedule_value: Schedule-specific value string.
        from_time: Base time for computation. Defaults to now (UTC).

    Returns:
        ISO-8601 formatted UTC timestamp for the next run.
    """
    now = from_time or datetime.now(timezone.utc)

    if schedule_type == ScheduleType.INTERVAL:
        minutes = int(schedule_value)
        return (now + timedelta(minutes=minutes)).isoformat()

    if schedule_type == ScheduleType.DAILY:
        hour, minute = (int(p) for p in schedule_value.strip().split(":"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target.isoformat()

    if schedule_type == ScheduleType.WEEKLY:
        parts = schedule_value.strip().lower().split()
        day_str = parts[0]
        time_str = parts[1] if len(parts) > 1 else "00:00"
        hour, minute = (int(p) for p in time_str.split(":"))
        target_dow = _DAY_MAP.get(day_str[:3], 0)
        current_dow = now.weekday()
        days_ahead = (target_dow - current_dow) % 7
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(
            days=days_ahead
        )
        if target <= now:
            target += timedelta(weeks=1)
        return target.isoformat()

    if schedule_type == ScheduleType.CRON_LIKE:
        return _compute_cron_like(schedule_value, now)

    return (now + timedelta(hours=1)).isoformat()


def _compute_cron_like(pattern: str, now: datetime) -> str:
    """Simplified cron: 'minute hour day_of_week' where * means any."""
    parts = pattern.strip().split()
    cron_min = parts[0] if len(parts) > 0 else "*"
    cron_hour = parts[1] if len(parts) > 1 else "*"
    cron_dow = parts[2] if len(parts) > 2 else "*"

    target = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # brute-force search within the next 8 days
    limit = now + timedelta(days=8)
    while target < limit:
        if cron_min != "*" and target.minute != int(cron_min):
            target += timedelta(minutes=1)
            continue
        if cron_hour != "*" and target.hour != int(cron_hour):
            target += timedelta(minutes=1)
            continue
        if cron_dow != "*":
            target_dow = target.weekday()
            allowed = _DAY_MAP.get(
                cron_dow[:3].lower(), int(cron_dow) if cron_dow.isdigit() else -1
            )
            if target_dow != allowed:
                target += timedelta(minutes=1)
                continue
        return target.isoformat()

    # fallback: 1 hour from now
    return (now + timedelta(hours=1)).isoformat()


@dataclass
class SchedulePolicy:
    """Policy constraints governing when and how a scheduled workflow runs."""

    require_approval_before_run: bool = True
    allowed_capabilities: list[str] = field(default_factory=list)
    max_runs_per_day: int = 24
    max_cost_usd: float = 0.0
    dry_run_only: bool = False
    auto_execute_safe_tasks_only: bool = True

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "require_approval_before_run": self.require_approval_before_run,
            "allowed_capabilities": self.allowed_capabilities,
            "max_runs_per_day": self.max_runs_per_day,
            "max_cost_usd": self.max_cost_usd,
            "dry_run_only": self.dry_run_only,
            "auto_execute_safe_tasks_only": self.auto_execute_safe_tasks_only,
        }


@dataclass
class ScheduledWorkflow:
    """A recurring workflow that generates PlanObjectives on schedule."""

    name: str
    objective: str
    schedule_type: ScheduleType
    schedule_value: str
    id: str = ""
    enabled: bool = False
    next_run_at: str = ""
    last_run_at: str = ""
    last_run_status: str = ""
    run_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    policy: SchedulePolicy = field(default_factory=SchedulePolicy)
    metadata: dict = field(default_factory=dict)
    created_by: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"sched_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = _iso_now()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.next_run_at:
            self.next_run_at = compute_next_run(self.schedule_type, self.schedule_value)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "objective": self.objective,
            "schedule_type": self.schedule_type.value,
            "schedule_value": self.schedule_value,
            "enabled": self.enabled,
            "next_run_at": self.next_run_at,
            "last_run_at": self.last_run_at,
            "last_run_status": self.last_run_status,
            "run_count": self.run_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "policy": self.policy.to_dict(),
            "metadata": self.metadata,
            "created_by": self.created_by,
        }
