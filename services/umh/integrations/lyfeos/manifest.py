"""LyfeOS integration manifest — declares sockets, signals, capabilities, config."""

from __future__ import annotations

import logging
import os

from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.capability import CapabilityCategory
from services.umh.protocols.signal import SignalUrgency
from services.umh.sockets.protocols import CapabilityDescriptor, SignalDescriptor

logger = logging.getLogger(__name__)

INTEGRATION_ID = "lyfeos"

SIGNAL_DESCRIPTORS: list[SignalDescriptor] = [
    SignalDescriptor(
        content_type="lyfeos_habits_logged",
        description="New habit log entry recorded in LyfeOS",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="lyfeos_goals_updated",
        description="Goal progress updated in LyfeOS",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="lyfeos_health_logged",
        description="Health metric logged in LyfeOS",
        default_urgency=SignalUrgency.LOW,
        default_risk_class=RiskClass.READ_ONLY,
    ),
]

CAPABILITY_DESCRIPTORS: list[CapabilityDescriptor] = [
    CapabilityDescriptor(
        name="noop",
        category=CapabilityCategory.RETRIEVE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={"table_name": "str", "user_id": "str", "row_id": "str"},
        output_schema={"received": "bool", "table_name": "str", "user_id": "str", "row_id": "str"},
        description="Acknowledge a polled LyfeOS signal without external action",
    ),
    CapabilityDescriptor(
        name="log_habit",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "str",
            "habit_name": "str",
            "completed": "bool",
            "notes": "str (optional)",
        },
        output_schema={"log_id": "str"},
        description="Record a habit completion log in LyfeOS",
    ),
    CapabilityDescriptor(
        name="update_goal",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "str",
            "goal_id": "str",
            "progress_pct": "int (optional)",
            "status": "str (optional)",
            "notes": "str (optional)",
        },
        output_schema={"goal_id": "str", "updated": "bool", "fields_changed": "list[str]"},
        description="Update goal progress or status in LyfeOS",
    ),
    CapabilityDescriptor(
        name="log_health_metric",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "str",
            "metric_type": "str",
            "value": "float",
            "unit": "str (optional)",
            "notes": "str (optional)",
        },
        output_schema={"metric_id": "str"},
        description="Record a health metric entry in LyfeOS",
    ),
]

POLLED_TABLES: list[str] = ["habit_logs", "goals", "health_metrics"]

DEFAULT_POLL_INTERVAL: float = 30.0


def load_lyfeos_config() -> dict[str, str | list[str] | float]:
    """Load LyfeOS integration configuration from environment variables.

    Required:
        LYFEOS_DATABASE_URL — Postgres connection string for the LyfeOS database.

    Optional:
        LYFEOS_USER_IDS — comma-separated user UUIDs to whitelist. Empty = all users.
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
