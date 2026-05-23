"""CreatorOS integration manifest — declares sockets, signals, capabilities, config."""

from __future__ import annotations

import logging
import os

from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.capability import CapabilityCategory
from services.umh.protocols.signal import SignalUrgency
from substrate.sockets.protocols import CapabilityDescriptor, SignalDescriptor

logger = logging.getLogger(__name__)

INTEGRATION_ID = "creatoros"

SIGNAL_DESCRIPTORS: list[SignalDescriptor] = [
    SignalDescriptor(
        content_type="creatoros_post_created",
        description="New post published via CreatorOS",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="creatoros_product_listed",
        description="New product listed for sale",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="creatoros_revenue_recorded",
        description="Revenue entry recorded",
        default_urgency=SignalUrgency.HIGH,
        default_risk_class=RiskClass.READ_ONLY,
    ),
]

CAPABILITY_DESCRIPTORS: list[CapabilityDescriptor] = [
    CapabilityDescriptor(
        name="noop",
        category=CapabilityCategory.RETRIEVE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={"table_name": "str", "user_id": "int", "row_id": "str"},
        output_schema={
            "received": "bool",
            "table_name": "str",
            "user_id": "int",
            "row_id": "str",
        },
        description="Acknowledge a polled CreatorOS signal without external action",
    ),
    CapabilityDescriptor(
        name="create_post",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "int",
            "content": "str",
            "media_type": "str (optional, default text)",
        },
        output_schema={"post_id": "str"},
        description="Insert a post in CreatorOS",
    ),
    CapabilityDescriptor(
        name="create_product",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "int",
            "title": "str",
            "description": "str (optional)",
            "price": "float (optional, default 0.0)",
            "category": "str (optional)",
        },
        output_schema={"product_id": "str"},
        description="Insert a product listing in CreatorOS",
    ),
    CapabilityDescriptor(
        name="record_revenue",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "int",
            "amount": "float",
            "source": "str (optional)",
            "date": "str (optional, ISO timestamp)",
        },
        output_schema={"revenue_id": "str"},
        description="Insert a revenue entry in CreatorOS",
    ),
]

POLLED_TABLES: list[str] = ["posts", "products", "revenue"]

DEFAULT_POLL_INTERVAL: float = 60.0


def load_creatoros_config() -> dict[str, str | list[str] | float]:
    """Load CreatorOS integration configuration from environment variables.

    Required:
        CREATOROS_DATABASE_URL -- Postgres connection string for the CreatorOS database.

    Optional:
        CREATOROS_USER_IDS -- comma-separated user IDs (integer) to whitelist. Empty = all.
        CREATOROS_POLL_INTERVAL -- seconds between poll cycles (default 60.0).

    Returns config dict or empty dict if CREATOROS_DATABASE_URL is not set.
    """
    database_url = os.getenv("CREATOROS_DATABASE_URL", "").strip()
    if not database_url:
        return {}

    user_ids_raw = os.getenv("CREATOROS_USER_IDS", "").strip()
    user_ids: list[str] = []
    if user_ids_raw:
        user_ids = [uid.strip() for uid in user_ids_raw.split(",") if uid.strip()]

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
        "user_ids": user_ids,
        "poll_interval": poll_interval,
        "tables": list(POLLED_TABLES),
    }
