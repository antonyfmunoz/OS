"""Unified adapter manifest for the UMH substrate layer.

AdapterManifest is the universal descriptor that replaces scattered
adapter type definitions. Combines modality, participant classification,
capabilities, maturity level, and health state into a single typed record.

Layer 3 Unified Architecture §2.1.
UMH substrate subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from adapters.adapter_engine.modality import ModalityType
from adapters.adapter_engine.participant import ParticipantType
from adapters.adapter_engine.adapter_registry_contracts import CapabilityDescriptor


class AdapterMaturityLevel(IntEnum):
    """How well UMH understands an adapter's capabilities.

    Modality-agnostic. Future work adds evidence models per dimension;
    the enum values are stable.
    """

    L0_REGISTERED = 0
    L1_CONNECTED = 1
    L2_CAPABILITIES_KNOWN = 2
    L3_TESTED = 3
    L4_EDGE_CASES_MAPPED = 4
    L5_OPTIMIZED = 5
    L6_EXPERT = 6
    L7_MASTERFUL = 7


@dataclass
class AdapterManifest:
    """Universal adapter descriptor.

    Extends the conceptual scope of AdapterDescriptor with modality,
    participant type, and maturity tracking. Existing AdapterDescriptor
    continues to work; AdapterManifest is the richer alternative for
    adapters that declare Layer 3 metadata.
    """

    adapter_id: str
    adapter_type: str
    modalities: list[ModalityType]
    participant_type: ParticipantType
    capabilities: list[CapabilityDescriptor] = field(default_factory=list)
    maturity: AdapterMaturityLevel = AdapterMaturityLevel.L0_REGISTERED
    version: str = "v1"
    vendor_docs_url: str | None = None
    notes: list[str] = field(default_factory=list)

    def supports(self, action_type: str) -> bool:
        return any(c.action_type == action_type for c in self.capabilities)

    def get_capability(self, action_type: str) -> CapabilityDescriptor | None:
        for c in self.capabilities:
            if c.action_type == action_type:
                return c
        return None

    def uses_modality(self, modality: ModalityType) -> bool:
        return modality in self.modalities

    @property
    def is_ecosystem(self) -> bool:
        return self.participant_type == ParticipantType.ECOSYSTEM

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type,
            "modalities": [m.value for m in self.modalities],
            "participant_type": self.participant_type.value,
            "capabilities": [
                {
                    "capability_id": c.capability_id,
                    "action_type": c.action_type,
                    "requires_gui": c.requires_gui,
                    "requires_local_shell": c.requires_local_shell,
                    "required_authority": c.required_authority.value,
                    "notes": c.notes,
                }
                for c in self.capabilities
            ],
            "maturity": self.maturity.value,
            "maturity_label": self.maturity.name,
            "version": self.version,
            "vendor_docs_url": self.vendor_docs_url,
            "notes": self.notes,
        }
