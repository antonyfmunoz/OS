"""Lifecycle modes — system-level cycle that governs safety and background behavior.

Lifecycle mode is orthogonal to profile/work mode. They compose:
a lifecycle mode (e.g., NIGHT_CYCLE) with a profile mode (e.g., DEVELOPER)
means "overnight autonomous work in developer context."

Phase 14.11B. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

from enum import Enum


class LifecycleMode(str, Enum):
    """System lifecycle modes governing safety and background behavior.

    DAY_CYCLE       — normal working hours, full capability
    NIGHT_CYCLE     — overnight, reduced risk ceiling, autonomous work permitted
    OVERNIGHT       — extended night, system runs queued safe work
    MAINTENANCE     — system maintenance window, restrict user-facing changes
    IDLE            — system idle, minimal background activity
    AWAY            — operator away, preserve state, pause non-essential
    REMOTE_WORK     — operator remote, reduced capabilities
    END_OF_WORKDAY  — transition period, checkpointing and handoff
    EMERGENCY       — degraded mode, critical-path-only execution
    """

    DAY_CYCLE = "day_cycle"
    NIGHT_CYCLE = "night_cycle"
    OVERNIGHT = "overnight"
    MAINTENANCE = "maintenance"
    IDLE = "idle"
    AWAY = "away"
    REMOTE_WORK = "remote_work"
    END_OF_WORKDAY = "end_of_workday"
    EMERGENCY = "emergency"


LIFECYCLE_RISK_CEILING: dict[LifecycleMode, str] = {
    LifecycleMode.DAY_CYCLE: "HIGH",
    LifecycleMode.NIGHT_CYCLE: "LOW",
    LifecycleMode.OVERNIGHT: "LOW",
    LifecycleMode.MAINTENANCE: "MEDIUM",
    LifecycleMode.IDLE: "LOW",
    LifecycleMode.AWAY: "LOW",
    LifecycleMode.REMOTE_WORK: "MEDIUM",
    LifecycleMode.END_OF_WORKDAY: "LOW",
    LifecycleMode.EMERGENCY: "CRITICAL",
}
