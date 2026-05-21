"""Capability discovery orchestrator for the UMH substrate layer.

Drives the TME source discovery pipeline with adapter-focused output.
The orchestrator resolves adapter_id -> manifest -> vendor_docs_url and
passes it through TME's existing official_url parameter. No TME code is
modified — the existing API already handles the adapter case.

Layer 3 Unified Architecture §3.
UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from adapters.adapter_engine.adapter_manifest import AdapterManifest
from adapters.adapter_engine.capability_catalog import CapabilityCatalog
from composition.mastery.research.source_discovery import discover_sources


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CapabilityDiscoveryOrchestrator:
    """Discovers adapter capabilities by driving the TME source pipeline."""

    catalog_root: Path = Path("data/runtime/catalogs")

    def discover(self, manifest: AdapterManifest) -> CapabilityCatalog:
        """Run capability discovery for a single adapter.

        Slice A: resolves vendor docs, calls source_discovery, writes
        empty catalog. Slice B adds LLM extraction to populate capabilities.
        """
        vendor_url = manifest.vendor_docs_url
        if not vendor_url:
            catalog = CapabilityCatalog(
                adapter_id=manifest.adapter_id,
                adapter_type=manifest.adapter_type,
                source_plan_notes=[
                    "no vendor_docs_url on manifest; discovery skipped",
                ],
                discovery_timestamp=_now_iso(),
            )
            self._write(catalog)
            return catalog

        plan = discover_sources(
            tool_slug=manifest.adapter_type,
            official_url=vendor_url,
        )

        catalog = CapabilityCatalog(
            adapter_id=manifest.adapter_id,
            adapter_type=manifest.adapter_type,
            vendor_docs_url=vendor_url,
            capabilities=[],
            gotchas=[],
            source_plan_notes=list(plan.notes),
            discovery_timestamp=_now_iso(),
            discovery_version="slice-a",
        )

        self._write(catalog)
        return catalog

    def _write(self, catalog: CapabilityCatalog) -> Path:
        out_dir = self.catalog_root / catalog.adapter_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "catalog.json"
        out_path.write_text(
            json.dumps(catalog.to_dict(), indent=2),
            encoding="utf-8",
        )
        return out_path
