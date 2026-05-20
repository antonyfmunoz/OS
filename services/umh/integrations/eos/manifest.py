"""EOS integration manifest — declares sockets, signals, capabilities, config."""

from __future__ import annotations

import logging
import os

from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.capability import CapabilityCategory
from services.umh.protocols.signal import SignalUrgency
from services.umh.sockets.protocols import CapabilityDescriptor, SignalDescriptor

logger = logging.getLogger(__name__)

INTEGRATION_ID = "eos"

SIGNAL_DESCRIPTORS: list[SignalDescriptor] = [
    SignalDescriptor(
        content_type="eos_events_created",
        description="New event row created in EOS events table",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
]

CAPABILITY_DESCRIPTORS: list[CapabilityDescriptor] = [
    CapabilityDescriptor(
        name="noop",
        category=CapabilityCategory.RETRIEVE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={"table_name": "str", "org_id": "str", "row_id": "str"},
        output_schema={"received": "bool", "table_name": "str", "org_id": "str", "row_id": "str"},
        description="Acknowledge a polled EOS signal without external action",
    ),
    CapabilityDescriptor(
        name="create_event",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={"org_id": "str", "event_type": "str", "payload_json": "dict"},
        output_schema={"event_id": "str"},
        description="Insert a domain event into the EOS events table",
    ),
    CapabilityDescriptor(
        name="create_client",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "org_id": "str",
            "venture_id": "str",
            "name": "str",
            "email": "str",
            "source": "str (optional)",
            "phone": "str (optional)",
            "notes": "str (optional)",
        },
        output_schema={"client_id": "str"},
        description="Insert a new client (lead) into the EOS clients table",
    ),
    CapabilityDescriptor(
        name="update_venture",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "org_id": "str",
            "venture_id": "str",
            "monthly_revenue": "str (optional)",
            "stage": "str (optional)",
        },
        output_schema={"venture_id": "str", "updated": "bool", "fields_changed": "list[str]"},
        description="Update a venture's revenue or stage in the EOS ventures table",
    ),
]

POLLED_TABLES: list[str] = ["events"]

DEFAULT_POLL_INTERVAL: float = 15.0


def load_eos_config() -> dict[str, str | list[str] | float]:
    """Load EOS integration configuration from environment variables.

    Required:
        EOS_DATABASE_URL — Postgres connection string for the EOS database.

    Optional:
        EOS_ORG_IDS — comma-separated org UUIDs to whitelist. Empty/unset = all orgs.
        EOS_POLL_INTERVAL — seconds between poll cycles (default 15.0).

    Returns config dict or empty dict if EOS_DATABASE_URL is not set.
    """
    database_url = os.getenv("EOS_DATABASE_URL", "").strip()
    if not database_url:
        return {}

    org_ids_raw = os.getenv("EOS_ORG_IDS", "").strip()
    org_ids: list[str] = []
    if org_ids_raw:
        org_ids = [oid.strip() for oid in org_ids_raw.split(",") if oid.strip()]

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
        "org_ids": org_ids,
        "poll_interval": poll_interval,
        "tables": list(POLLED_TABLES),
    }
