"""EOS integration manifest — declares sockets, signals, capabilities, config."""

from __future__ import annotations

import logging
import os

from services.umh.governance.risk_classes import RiskClass
from substrate.types import CapabilityCategory, SignalUrgency
from substrate.sockets.protocols import CapabilityDescriptor, SignalDescriptor

logger = logging.getLogger(__name__)

INTEGRATION_ID = "eos"

SIGNAL_DESCRIPTORS: list[SignalDescriptor] = [
    SignalDescriptor(
        content_type="eos_contact_created",
        description="New CRM contact created in EntrepreneurOS",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="eos_deal_created",
        description="New CRM deal created in EntrepreneurOS",
        default_urgency=SignalUrgency.HIGH,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="eos_activity_logged",
        description="CRM activity logged in EntrepreneurOS",
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
        description="Acknowledge a polled EOS signal without external action",
    ),
    CapabilityDescriptor(
        name="create_contact",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "str",
            "name": "str",
            "email": "str",
            "status": "str (optional, default lead)",
            "company": "str (optional)",
            "title": "str (optional)",
            "phone": "str (optional)",
            "notes": "str (optional)",
        },
        output_schema={"contact_id": "str"},
        description="Insert a new CRM contact into EntrepreneurOS",
    ),
    CapabilityDescriptor(
        name="create_deal",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "str",
            "title": "str",
            "company": "str",
            "value": "decimal",
            "contact_id": "str",
            "stage": "str (optional, default discovery)",
            "probability": "int (optional, default 50)",
        },
        output_schema={"deal_id": "str"},
        description="Insert a new CRM deal into EntrepreneurOS",
    ),
    CapabilityDescriptor(
        name="update_deal_stage",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "str",
            "deal_id": "str",
            "stage": "str (optional)",
            "probability": "int (optional)",
        },
        output_schema={"deal_id": "str", "updated": "bool", "fields_changed": "list[str]"},
        description="Update a deal's stage or probability in EntrepreneurOS",
    ),
    CapabilityDescriptor(
        name="log_activity",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "user_id": "str",
            "type": "str (email|call|meeting|task|note)",
            "subject": "str",
            "date": "datetime",
            "related_to_type": "str (contact|deal)",
            "related_to_id": "str",
        },
        output_schema={"activity_id": "str"},
        description="Log a CRM activity in EntrepreneurOS",
    ),
]

POLLED_TABLES: list[str] = ["crm_contacts", "crm_deals", "crm_activities"]

DEFAULT_POLL_INTERVAL: float = 15.0


def load_eos_config() -> dict[str, str | list[str] | float]:
    """Load EOS integration configuration from environment variables.

    Required:
        EOS_DATABASE_URL — Postgres connection string for the EOS database.

    Optional:
        EOS_USER_IDS — comma-separated user IDs to whitelist. Empty/unset = all.
        EOS_POLL_INTERVAL — seconds between poll cycles (default 15.0).

    Returns config dict or empty dict if EOS_DATABASE_URL is not set.
    """
    database_url = os.getenv("EOS_DATABASE_URL", "").strip()
    if not database_url:
        return {}

    user_ids_raw = os.getenv("EOS_USER_IDS", "").strip()
    user_ids: list[str] = []
    if user_ids_raw:
        user_ids = [uid.strip() for uid in user_ids_raw.split(",") if uid.strip()]

    poll_interval = DEFAULT_POLL_INTERVAL
    interval_raw = os.getenv("EOS_POLL_INTERVAL", "").strip()
    if interval_raw:
        try:
            poll_interval = float(interval_raw)
        except ValueError:
            logger.warning(
                "EOS_POLL_INTERVAL invalid '%s', using default %.1f",
                interval_raw,
                DEFAULT_POLL_INTERVAL,
            )

    return {
        "database_url": database_url,
        "user_ids": user_ids,
        "poll_interval": poll_interval,
        "tables": list(POLLED_TABLES),
    }
