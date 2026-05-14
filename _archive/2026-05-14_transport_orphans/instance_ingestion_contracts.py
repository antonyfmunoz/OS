"""
Instance ingestion contracts for Phase 96.4.

W0-001 data is instance-specific to Antony / Empyrean.
Instance source data defaults to INSTANCE_MEMORY scope.
Global canon not allowed by default for user account data.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from runtime.transport.memory_scope_contracts import MemoryScope


@dataclass
class InstanceSourceContext:
    """Context for instance-specific source ingestion."""

    instance_id: str
    account: str
    source_system: str = ""
    source_owner: str = ""
    source_scope: str = ""
    ingestion_work_order: str = ""
    privacy_classification: str = "private"
    allowed_memory_scopes: list[MemoryScope] = field(
        default_factory=lambda: [
            MemoryScope.INSTANCE_MEMORY,
            MemoryScope.PROJECT_MEMORY,
            MemoryScope.ARCHIVE_ONLY,
        ]
    )
    default_memory_scope: MemoryScope = MemoryScope.INSTANCE_MEMORY
    global_canon_allowed_by_default: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "account": self.account,
            "source_system": self.source_system,
            "source_owner": self.source_owner,
            "source_scope": self.source_scope,
            "ingestion_work_order": self.ingestion_work_order,
            "privacy_classification": self.privacy_classification,
            "allowed_memory_scopes": [s.value for s in self.allowed_memory_scopes],
            "default_memory_scope": self.default_memory_scope.value,
            "global_canon_allowed_by_default": self.global_canon_allowed_by_default,
        }


def build_w0_001_instance_context() -> InstanceSourceContext:
    """Build the W0-001 instance context for Antony / Empyrean."""
    return InstanceSourceContext(
        instance_id="antony_empyrean",
        account="antonyfm@empyreanstudios.co",
        source_system="Google Drive / Google Docs",
        source_owner="Antony F. Munoz",
        source_scope="W0-001 tab-aware corpus",
        ingestion_work_order="W0-001",
        privacy_classification="private",
        default_memory_scope=MemoryScope.INSTANCE_MEMORY,
        global_canon_allowed_by_default=False,
    )
