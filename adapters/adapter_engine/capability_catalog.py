"""Per-adapter capability catalog for the UMH substrate layer.

Discovery output — a third artifact alongside AdapterManifest (declaration)
and AdapterHealthRecord (runtime). The catalog stores what TME-driven
discovery found about an adapter's capabilities, gotchas, and evidence.

Slice A: all CatalogEntry fields default/empty except capability_id +
action_type. Slice B: LLM extraction populates description, evidence,
gotchas, confidence.

Layer 3 Unified Architecture §3.
UMH substrate subsystem.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CatalogEntry:
    """A single discovered capability with evidence."""

    capability_id: str
    action_type: str
    description: str = ""
    evidence: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    confidence: float = 0.0
    gotchas: list[str] = field(default_factory=list)
    requires_auth: bool | None = None
    requires_gui: bool | None = None


@dataclass
class CapabilityCatalog:
    """Discovered capabilities for a single adapter."""

    adapter_id: str
    adapter_type: str
    vendor_docs_url: str | None = None
    capabilities: list[CatalogEntry] = field(default_factory=list)
    gotchas: list[str] = field(default_factory=list)
    source_plan_notes: list[str] = field(default_factory=list)
    discovery_timestamp: str = ""
    discovery_version: str = "slice-a"
    maturity_evidence: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.capabilities

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type,
            "vendor_docs_url": self.vendor_docs_url,
            "capabilities": [asdict(c) for c in self.capabilities],
            "gotchas": self.gotchas,
            "source_plan_notes": self.source_plan_notes,
            "discovery_timestamp": self.discovery_timestamp,
            "discovery_version": self.discovery_version,
            "maturity_evidence": self.maturity_evidence,
        }
