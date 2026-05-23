"""Notion integration manifest — declares sockets, signals, capabilities, signal sources."""

from __future__ import annotations

import os

from substrate.governance.risk_classes import RiskClass
from substrate.types import CapabilityCategory, SignalUrgency
from substrate.sockets.protocols import CapabilityDescriptor, SignalDescriptor

from .auth import discover_database_ids

INTEGRATION_ID = "notion"

SIGNAL_DESCRIPTORS: list[SignalDescriptor] = [
    SignalDescriptor(
        content_type="page_created",
        description="New Notion page created",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="page_updated",
        description="Existing Notion page modified",
        default_urgency=SignalUrgency.LOW,
        default_risk_class=RiskClass.READ_ONLY,
    ),
    SignalDescriptor(
        content_type="database_entry_added",
        description="New row added to Notion database",
        default_urgency=SignalUrgency.NORMAL,
        default_risk_class=RiskClass.READ_ONLY,
    ),
]

CAPABILITY_DESCRIPTORS: list[CapabilityDescriptor] = [
    CapabilityDescriptor(
        name="create_page",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={"title": "str", "database_id": "str", "properties": "dict"},
        output_schema={"page_id": "str", "url": "str"},
        description="Create a new page in a Notion database",
    ),
    CapabilityDescriptor(
        name="update_page",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={"page_id": "str", "properties": "dict"},
        output_schema={"page_id": "str", "updated": "bool"},
        description="Update properties on an existing Notion page",
    ),
    CapabilityDescriptor(
        name="append_block",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={"page_id": "str", "children": "list[dict]"},
        output_schema={"block_ids": "list", "count": "int"},
        description="Append content blocks to an existing Notion page",
    ),
    CapabilityDescriptor(
        name="query_database",
        category=CapabilityCategory.RETRIEVE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={
            "database_id": "str",
            "filter": "dict",
            "sorts": "list",
            "page_size": "int",
        },
        output_schema={"results": "list", "count": "int", "has_more": "bool"},
        description="Query a Notion database with optional filter and sorts",
    ),
    CapabilityDescriptor(
        name="noop",
        category=CapabilityCategory.RETRIEVE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={"page_id": "str"},
        output_schema={"received": "bool", "page_id": "str"},
        description="Acknowledge a polled signal without external action",
    ),
]


def load_signal_sources() -> list[dict[str, str | float]]:
    """Parse NOTION_SIGNAL_SOURCES env var into signal source configs.

    Format: comma-separated database logical names.
    Example: NOTION_SIGNAL_SOURCES=empyrean_creative_tasks,lyfe_tasks

    Each entry becomes:
        {"logical_name": "...", "database_id": "UUID", "operation": "noop", "poll_interval": 30.0}

    Unknown logical names are skipped with a warning.
    """
    raw = os.getenv("NOTION_SIGNAL_SOURCES", "").strip()
    if not raw:
        return []

    databases = discover_database_ids()
    sources: list[dict[str, str | float]] = []

    for name in raw.split(","):
        name = name.strip()
        if not name:
            continue
        db_id = databases.get(name)
        if not db_id:
            import logging

            logging.getLogger(__name__).warning(
                "NOTION_SIGNAL_SOURCES: unknown logical name '%s', skipping", name
            )
            continue
        sources.append(
            {
                "logical_name": name,
                "database_id": db_id,
                "operation": "noop",
                "poll_interval": 30.0,
            }
        )

    return sources
