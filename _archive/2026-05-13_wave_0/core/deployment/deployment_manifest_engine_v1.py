"""Deployment Manifest Engine v1.

Tracks application projections, required capabilities,
environment/topology/observability/replay/continuity bindings.

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.deployment.platform_deployment_contracts_v1 import (
    DeploymentManifest,
    _now_iso,
)

MAX_MANIFESTS = 50
MAX_BINDINGS_PER_MANIFEST = 20


class DeploymentManifestEngine:
    """Manages deployment manifests."""

    def __init__(self, state_dir: str | Path = "data/runtime/deployments") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._manifests: dict[str, DeploymentManifest] = {}

    def create(
        self,
        application_id: str,
        required_capabilities: list[str] | None = None,
        environment_bindings: list[str] | None = None,
        topology_bindings: list[str] | None = None,
    ) -> DeploymentManifest | None:
        if len(self._manifests) >= MAX_MANIFESTS:
            return None

        manifest = DeploymentManifest(
            application_id=application_id,
            required_capabilities=required_capabilities or [],
            environment_bindings=environment_bindings or [],
            topology_bindings=topology_bindings or [],
        )
        self._manifests[manifest.manifest_id] = manifest

        path = self._state_dir / "manifests.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(manifest.to_dict(), default=str) + "\n")

        return manifest

    def get(self, manifest_id: str) -> DeploymentManifest | None:
        return self._manifests.get(manifest_id)

    def get_for_app(self, application_id: str) -> list[dict[str, Any]]:
        return [
            m.to_dict() for m in self._manifests.values()
            if m.application_id == application_id
        ]

    def get_all(self, limit: int = 50) -> list[dict[str, Any]]:
        return [m.to_dict() for m in list(self._manifests.values())[-limit:]]

    def validate_manifest(self, manifest_id: str) -> dict[str, Any]:
        manifest = self._manifests.get(manifest_id)
        if manifest is None:
            return {"valid": False, "reason": "manifest not found"}

        issues: list[str] = []
        if not manifest.application_id:
            issues.append("missing application_id")
        if not manifest.required_capabilities:
            issues.append("no required_capabilities")
        if not manifest.environment_bindings:
            issues.append("no environment_bindings")

        return {
            "valid": len(issues) == 0,
            "manifest_id": manifest_id,
            "issues": issues,
            "manifest_hash": manifest.manifest_hash,
        }

    def get_stats(self) -> dict[str, object]:
        return {
            "total_manifests": len(self._manifests),
            "max_manifests": MAX_MANIFESTS,
        }
