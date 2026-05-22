"""CreatorOS integration manifest — declares sockets, signals, capabilities, config."""

from __future__ import annotations

import logging
import os

from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.capability import CapabilityCategory
from services.umh.protocols.signal import SignalUrgency
from services.umh.sockets.protocols import CapabilityDescriptor, SignalDescriptor

logger = logging.getLogger(__name__)

INTEGRATION_ID = "creatoros"

SIGNAL_DESCRIPTORS: list[SignalDescriptor] = [
    SignalDescriptor(
        content_type="creatoros_content_published",
        description="New content piece published via CreatorOS",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="creatoros_analytics_updated",
        description="Content analytics metrics refreshed in CreatorOS",
        default_urgency=SignalUrgency.LOW,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="creatoros_audience_milestone",
        description="Audience growth milestone reached in CreatorOS",
        default_urgency=SignalUrgency.HIGH,
        default_risk_class=RiskClass.READ_ONLY,
    ),
]

CAPABILITY_DESCRIPTORS: list[CapabilityDescriptor] = [
    CapabilityDescriptor(
        name="noop",
        category=CapabilityCategory.RETRIEVE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={"table_name": "str", "creator_id": "str", "row_id": "str"},
        output_schema={
            "received": "bool",
            "table_name": "str",
            "creator_id": "str",
            "row_id": "str",
        },
        description="Acknowledge a polled CreatorOS signal without external action",
    ),
    CapabilityDescriptor(
        name="create_content",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "creator_id": "str",
            "platform": "str",
            "content_type": "str",
            "title": "str",
            "body": "str (optional)",
            "status": "str (optional, default draft)",
        },
        output_schema={"content_id": "str"},
        description="Create a new content piece in CreatorOS",
    ),
    CapabilityDescriptor(
        name="update_analytics",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "creator_id": "str",
            "content_id": "str",
            "views": "int (optional)",
            "likes": "int (optional)",
            "comments": "int (optional)",
            "shares": "int (optional)",
        },
        output_schema={
            "content_id": "str",
            "updated": "bool",
            "fields_changed": "list[str]",
        },
        description="Update analytics metrics for a content piece in CreatorOS",
    ),
    CapabilityDescriptor(
        name="record_audience_metric",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "creator_id": "str",
            "platform": "str",
            "metric_type": "str",
            "value": "int",
        },
        output_schema={"metric_id": "str"},
        description="Record an audience growth metric in CreatorOS",
    ),
]

POLLED_TABLES: list[str] = ["content", "analytics", "audience_metrics"]

DEFAULT_POLL_INTERVAL: float = 60.0


def load_creatoros_config() -> dict[str, str | list[str] | float]:
    """Load CreatorOS integration configuration from environment variables.

    Required:
        CREATOROS_DATABASE_URL — Postgres connection string for the CreatorOS database.

    Optional:
        CREATOROS_CREATOR_IDS — comma-separated creator UUIDs to whitelist. Empty = all.
        CREATOROS_POLL_INTERVAL — seconds between poll cycles (default 60.0).

    Returns config dict or empty dict if CREATOROS_DATABASE_URL is not set.
    """
    database_url = os.getenv("CREATOROS_DATABASE_URL", "").strip()
    if not database_url:
        return {}

    creator_ids_raw = os.getenv("CREATOROS_CREATOR_IDS", "").strip()
    creator_ids: list[str] = []
    if creator_ids_raw:
        creator_ids = [cid.strip() for cid in creator_ids_raw.split(",") if cid.strip()]

    poll_interval = DEFAULT_POLL_INTERVAL
    interval_raw = os.getenv("CREATOROS_POLL_INTERVAL", "").strip()
    if interval_raw:
        try:
            poll_interval = float(interval_raw)
        except ValueError:
            logger.warning(
                "CREATOROS_POLL_INTERVAL invalid '%s', using default %.1f",
                interval_raw,
                DEFAULT_POLL_INTERVAL,
            )

    return {
        "database_url": database_url,
        "creator_ids": creator_ids,
        "poll_interval": poll_interval,
        "tables": list(POLLED_TABLES),
    }
