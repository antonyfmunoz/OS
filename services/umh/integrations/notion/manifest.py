"""Notion integration manifest — declares sockets, signals, capabilities.

This is a template showing the shape. Actual Notion handler implementation
lives outside UMH. This file is UMH-owned configuration only.
"""

from __future__ import annotations

from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.capability import CapabilityCategory
from services.umh.protocols.signal import SignalUrgency
from services.umh.sockets.protocols import CapabilityDescriptor, SignalDescriptor

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
        name="query_database",
        category=CapabilityCategory.RETRIEVE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={"database_id": "str", "filter": "dict"},
        output_schema={"results": "list", "count": "int"},
        description="Query a Notion database with optional filter",
    ),
]
