"""Sovereign Runtime Identity Engine v1.

Generates deterministic runtime identity with fingerprint,
trust bundle reference, constitutional attestation reference,
topology reference, capability manifest reference, and verification hash.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    SovereignRuntimeIdentity,
    _now_iso,
    _deterministic_id,
)


MAX_IDENTITIES = 10


class SovereignRuntimeIdentityEngine:
    """Generates and persists sovereign runtime identities."""

    def __init__(self, output_dir: str = "data/runtime/federation/identity") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._identities: list[SovereignRuntimeIdentity] = []

    def create_identity(
        self,
        runtime_id: str = "",
        trust_bundle_ref: str = "",
        constitutional_ref: str = "",
        topology_ref: str = "",
        capability_ref: str = "",
    ) -> dict[str, Any]:
        if len(self._identities) >= MAX_IDENTITIES:
            raise ValueError("Max identities reached")
        ts = _now_iso()
        if not runtime_id:
            runtime_id = _deterministic_id("srid-", ts)
        fingerprint_content = f"{runtime_id}|{trust_bundle_ref}|{constitutional_ref}|{topology_ref}|{capability_ref}"
        fingerprint = hashlib.sha256(fingerprint_content.encode()).hexdigest()
        verification_content = f"{runtime_id}|{fingerprint}|{ts}"
        verification_hash = hashlib.sha256(verification_content.encode()).hexdigest()

        identity = SovereignRuntimeIdentity(
            runtime_id=runtime_id,
            runtime_fingerprint=fingerprint,
            trust_bundle_reference=trust_bundle_ref,
            constitutional_attestation_reference=constitutional_ref,
            topology_reference=topology_ref,
            capability_manifest_reference=capability_ref,
            verification_hash=verification_hash,
            created_at=ts,
        )
        self._identities.append(identity)
        filepath = self._output_dir / f"{runtime_id}.json"
        with open(filepath, "w") as f:
            json.dump(identity.to_dict(), f, indent=2)
        return identity.to_dict()

    def get_current_identity(self) -> dict[str, Any] | None:
        if not self._identities:
            return None
        return self._identities[-1].to_dict()

    def all_fingerprinted(self) -> bool:
        return all(i.runtime_fingerprint != "" for i in self._identities)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_identities": len(self._identities),
            "all_fingerprinted": self.all_fingerprinted() if self._identities else False,
        }
