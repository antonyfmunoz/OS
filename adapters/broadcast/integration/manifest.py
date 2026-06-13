"""Broadcast integration manifest — declares capabilities for start, stop, status."""

from __future__ import annotations

from substrate.governance.risk_classes import RiskClass
from substrate.types import CapabilityCategory
from substrate.sockets.protocols import CapabilityDescriptor

INTEGRATION_ID = "broadcast"

CAPABILITY_DESCRIPTORS: list[CapabilityDescriptor] = [
    CapabilityDescriptor(
        name="start",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.EXTERNAL_COMMUNICATION,
        input_schema={
            "source_type": "str",
            "source_config": "dict",
            "output_url": "str",
            "resolution": "str",
            "video_bitrate": "str",
            "fps": "int",
        },
        output_schema={"pid": "int", "state": "str"},
        description="Start a broadcast — spawns FFmpeg subprocess pushing to RTMP/SRT",
    ),
    CapabilityDescriptor(
        name="stop",
        category=CapabilityCategory.COMMUNICATE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={},
        output_schema={"exit_code": "int", "state": "str"},
        description="Stop the active broadcast — graceful SIGTERM then SIGKILL",
    ),
    CapabilityDescriptor(
        name="status",
        category=CapabilityCategory.RETRIEVE,
        risk_class=RiskClass.READ_ONLY,
        input_schema={},
        output_schema={
            "state": "str",
            "health": "dict",
            "pid": "int",
            "config": "dict",
        },
        description="Query current broadcast state and health metrics",
    ),
]
