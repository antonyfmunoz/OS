"""Trust Bundle Engine v1.

Bundles trust artifacts into portable, verifiable trust bundles.

UMH substrate subsystem. Phase 96.8CM.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.trust.sovereign_operational_trust_contracts_v1 import (
    TrustBundle,
    _now_iso,
    _deterministic_id,
)


MAX_BUNDLES = 100

BUNDLE_DOMAINS = [
    "runtime_attestation",
    "constitutional_audit",
    "sovereign_validation_report",
    "accountability_proof",
    "explainability_proof",
    "replay_certification",
    "continuity_certification",
    "topology_certification",
    "chronology_proof",
    "provenance_graph",
]


class TrustBundleEngine:
    """Creates and persists trust bundles."""

    def __init__(self, output_dir: str = "data/runtime/trust/bundles") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._bundles: list[TrustBundle] = []

    def create_bundle(
        self,
        artifacts: list[dict[str, Any]],
        domains_included: list[str] | None = None,
    ) -> dict[str, Any]:
        if len(self._bundles) >= MAX_BUNDLES:
            raise ValueError("Max bundles reached")
        ts = _now_iso()
        canonical = json.dumps(artifacts, sort_keys=True)
        bundle_hash = hashlib.sha256(canonical.encode()).hexdigest()
        bundle = TrustBundle(
            bundle_id=_deterministic_id("tbund-", ts),
            artifacts=artifacts,
            bundle_hash=bundle_hash,
            created_at=ts,
            domains_included=domains_included or [],
            complete=len(domains_included or []) >= len(BUNDLE_DOMAINS),
        )
        self._bundles.append(bundle)
        filepath = self._output_dir / f"{bundle.bundle_id}.json"
        with open(filepath, "w") as f:
            json.dump(bundle.to_dict(), f, indent=2)
        return bundle.to_dict()

    def all_complete(self) -> bool:
        return all(b.complete for b in self._bundles) if self._bundles else False

    def all_hashed(self) -> bool:
        return all(b.bundle_hash != "" for b in self._bundles) if self._bundles else False

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_bundles": len(self._bundles),
            "all_complete": self.all_complete() if self._bundles else False,
            "all_hashed": self.all_hashed() if self._bundles else False,
        }
