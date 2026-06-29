"""Adapter engine — manifest, maturity, lifecycle, and registry for UMH adapters."""

from adapters.adapter_engine.adapter_manifest import AdapterManifest, AdapterMaturityLevel
from adapters.adapter_engine.adapter_maturity import MaturityEvidence, compute_adapter_maturity
from adapters.adapter_engine.adapter_registry_contracts import (
    AdapterDescriptor,
    AdapterRegistry,
    CapabilityDescriptor,
)
from adapters.adapter_engine.modality import ModalityType
from adapters.adapter_engine.participant import ParticipantType
from adapters.adapter_engine.production_manifests import (
    ALL_PRODUCTION_MANIFESTS,
    populate_production_registry,
)

__all__ = [
    "AdapterDescriptor",
    "AdapterManifest",
    "AdapterMaturityLevel",
    "AdapterRegistry",
    "ALL_PRODUCTION_MANIFESTS",
    "CapabilityDescriptor",
    "MaturityEvidence",
    "ModalityType",
    "ParticipantType",
    "compute_adapter_maturity",
    "populate_production_registry",
]
