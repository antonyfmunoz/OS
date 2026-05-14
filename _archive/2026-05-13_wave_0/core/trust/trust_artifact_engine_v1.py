"""Trust Artifact Engine v1.

Generates hashed, lineage-linked trust artifacts from source evidence.

UMH substrate subsystem. Phase 96.8CM.
"""

from __future__ import annotations

import hashlib
from typing import Any

from core.trust.sovereign_operational_trust_contracts_v1 import (
    TrustArtifact,
    _now_iso,
    _deterministic_id,
)


MAX_ARTIFACTS = 500

ARTIFACT_TYPES = [
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


class TrustArtifactEngine:
    """Generates and hashes trust artifacts."""

    def __init__(self) -> None:
        self._artifacts: list[TrustArtifact] = []

    def generate_artifact(
        self,
        artifact_type: str,
        source_path: str = "",
        lineage_references: list[str] | None = None,
    ) -> dict[str, Any]:
        if len(self._artifacts) >= MAX_ARTIFACTS:
            raise ValueError("Max artifacts reached")
        ts = _now_iso()
        content = f"{artifact_type}|{source_path}|{ts}"
        digest = hashlib.sha256(content.encode()).hexdigest()
        artifact = TrustArtifact(
            artifact_id=_deterministic_id("tart-", ts, artifact_type),
            artifact_type=artifact_type,
            source_path=source_path,
            artifact_hash=digest,
            timestamp=ts,
            lineage_references=lineage_references or [],
            verification_status="hashed",
        )
        self._artifacts.append(artifact)
        return artifact.to_dict()

    def generate_all_types(self) -> dict[str, Any]:
        results = []
        for at in ARTIFACT_TYPES:
            results.append(self.generate_artifact(at, source_path=f"data/runtime/trust/{at}"))
        return {"artifacts": results, "total": len(results)}

    def all_hashed(self) -> bool:
        return all(a.artifact_hash != "" for a in self._artifacts)

    def get_artifact_hashes(self) -> list[str]:
        return [a.artifact_hash for a in self._artifacts]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_artifacts": len(self._artifacts),
            "all_hashed": self.all_hashed(),
        }
