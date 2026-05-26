"""LyfeOS integration manifest — declares sockets, signals, capabilities, config."""

from __future__ import annotations

import logging
import os

from substrate.types import (
    ActionRiskClass as RiskClass,
    CapabilityCategory,
    CapabilityDescriptor,
    SignalDescriptor,
    SignalUrgency,
)

logger = logging.getLogger(__name__)

INTEGRATION_ID = "lyfeos"

SIGNAL_DESCRIPTORS: list[SignalDescriptor] = [
    SignalDescriptor(
        content_type="lyfeos_quest_completed",
        description="Quest completed in LyfeOS",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="lyfeos_daily_log_created",
        description="Daily reflection logged in LyfeOS",
        default_urgency=SignalUrgency.LOW,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="lyfeos_stats_updated",
        description="User stats changed (level up, XP, streak) in LyfeOS",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
]

CAPABILITY_DESCRIPTORS: list[CapabilityDescriptor] = [
    CapabilityDescriptor(
        name="noop",
        category=CapabilityCategory.RETRIEVE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={"table_name": "str", "user_id": "int", "row_id": "str"},
        output_schema={"received": "bool", "table_name": "str", "user_id": "int", "row_id": "str"},
        description="Acknowledge a polled LyfeOS signal without external action",
    ),
    CapabilityDescriptor(
        name="create_quest",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "int",
            "title": "str",
            "description": "str (optional)",
            "category": "str (optional, default general)",
            "energy_cost": "int (optional)",
            "experience_reward": "int (optional)",
            "difficulty": "str (optional, S/A/B/C/D)",
        },
        output_schema={"quest_id": "str"},
        description="Insert a quest in LyfeOS",
    ),
    CapabilityDescriptor(
        name="complete_quest",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "int",
            "quest_id": "int",
            "mission_status": "str (optional, confirmed/pending/completed/cancelled)",
        },
        output_schema={
            "quest_id": "str",
            "updated": "bool",
            "fields_changed": "list[str]",
        },
        description="Mark a quest completed and optionally update mission status in LyfeOS",
    ),
    CapabilityDescriptor(
        name="log_daily_reflection",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "int",
            "date": "str (YYYY-MM-DD)",
            "mental_state": "int (1-10, optional)",
            "physical_state": "int (1-10, optional)",
            "emotional_state": "int (1-10, optional)",
            "gratitude": "str (optional)",
        },
        output_schema={"log_id": "str"},
        description="Insert a daily log entry in LyfeOS",
    ),
]

POLLED_TABLES: list[str] = ["quests", "user_daily_logs", "vision_goals"]

DEFAULT_POLL_INTERVAL: float = 30.0


def load_lyfeos_config() -> dict[str, str | list[str] | float]:
    """Load LyfeOS integration configuration from environment variables.

    Required:
        LYFEOS_DATABASE_URL — Postgres connection string for the LyfeOS database.

    Optional:
        LYFEOS_USER_IDS — comma-separated user IDs (integer) to whitelist. Empty = all users.
        LYFEOS_POLL_INTERVAL — seconds between poll cycles (default 30.0).

    Returns config dict or empty dict if LYFEOS_DATABASE_URL is not set.
    """
    database_url = os.getenv("LYFEOS_DATABASE_URL", "").strip()
    if not database_url:
        return {}

    user_ids_raw = os.getenv("LYFEOS_USER_IDS", "").strip()
    user_ids: list[str] = []
    if user_ids_raw:
        user_ids = [uid.strip() for uid in user_ids_raw.split(",") if uid.strip()]

    poll_interval = DEFAULT_POLL_INTERVAL
    interval_raw = os.getenv("LYFEOS_POLL_INTERVAL", "").strip()
    if interval_raw:
        try:
            poll_interval = float(interval_raw)
        except ValueError:
            logger.warning(
                "LYFEOS_POLL_INTERVAL invalid '%s', using default %.1f",
                interval_raw,
                DEFAULT_POLL_INTERVAL,
            )

    return {
        "database_url": database_url,
        "user_ids": user_ids,
        "poll_interval": poll_interval,
        "tables": list(POLLED_TABLES),
    }
