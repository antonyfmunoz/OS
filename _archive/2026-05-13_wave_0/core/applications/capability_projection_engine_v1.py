"""Capability Projection Engine v1.

Exposes substrate capabilities to applications through governed
projection surfaces. Enforces domain boundaries, trust-tier
restrictions, and forbidden capability access.

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.applications.application_projection_contracts_v1 import (
    ApplicationCapabilityBinding,
    ApplicationCapabilitySurface,
    ApplicationTrustTier,
    CapabilityCategory,
    _now_iso,
)

TRUST_TIER_CAPABILITIES: dict[str, list[str]] = {
    ApplicationTrustTier.CORE.value: [c.value for c in CapabilityCategory],
    ApplicationTrustTier.GOVERNED.value: [
        CapabilityCategory.WORKFLOWS.value,
        CapabilityCategory.KNOWLEDGE.value,
        CapabilityCategory.SESSIONS.value,
        CapabilityCategory.OBSERVABILITY.value,
        CapabilityCategory.ENVIRONMENTS.value,
    ],
    ApplicationTrustTier.RESTRICTED.value: [
        CapabilityCategory.WORKFLOWS.value,
        CapabilityCategory.SESSIONS.value,
        CapabilityCategory.OBSERVABILITY.value,
    ],
    ApplicationTrustTier.SANDBOXED.value: [
        CapabilityCategory.SESSIONS.value,
        CapabilityCategory.OBSERVABILITY.value,
    ],
}

FORBIDDEN_DIRECT_CAPABILITIES: list[str] = [
    "direct_adapter_execution",
    "direct_spine_mutation",
    "direct_governance_override",
    "direct_canonical_write",
    "direct_learning_mutation",
    "direct_cognition_injection",
]

MAX_SURFACES_PER_APP = 20
MAX_BINDINGS = 200


class CapabilityProjectionEngine:
    """Projects substrate capabilities into application surfaces."""

    def __init__(self, state_dir: str | Path = "data/runtime/applications") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._surfaces: list[ApplicationCapabilitySurface] = []
        self._bindings: list[ApplicationCapabilityBinding] = []

    def project_capability(
        self,
        app_id: str,
        capability_category: str,
        trust_tier: str,
        operations: list[str] | None = None,
    ) -> ApplicationCapabilitySurface | None:
        allowed = TRUST_TIER_CAPABILITIES.get(trust_tier, [])
        if capability_category not in allowed:
            return None

        app_surfaces = [
            s for s in self._surfaces if s.application_id == app_id
        ]
        if len(app_surfaces) >= MAX_SURFACES_PER_APP:
            return None

        surface = ApplicationCapabilitySurface(
            application_id=app_id,
            capability_category=capability_category,
            exposed_operations=operations or [],
            trust_tier=trust_tier,
        )
        self._surfaces.append(surface)

        binding = ApplicationCapabilityBinding(
            application_id=app_id,
            capability_category=capability_category,
        )
        self._bindings.append(binding)

        path = self._state_dir / "capability_projections.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(surface.to_dict(), default=str) + "\n")

        return surface

    def is_capability_allowed(
        self,
        capability_category: str,
        trust_tier: str,
    ) -> bool:
        allowed = TRUST_TIER_CAPABILITIES.get(trust_tier, [])
        return capability_category in allowed

    def is_forbidden(self, action: str) -> bool:
        return action in FORBIDDEN_DIRECT_CAPABILITIES

    def get_surfaces_for_app(
        self,
        app_id: str,
    ) -> list[dict[str, Any]]:
        return [
            s.to_dict() for s in self._surfaces
            if s.application_id == app_id
        ]

    def get_bindings_for_app(
        self,
        app_id: str,
    ) -> list[dict[str, Any]]:
        return [
            b.to_dict() for b in self._bindings
            if b.application_id == app_id
        ]

    def get_binding_hash(self, app_id: str) -> str:
        cats = sorted(
            b.capability_category for b in self._bindings
            if b.application_id == app_id
        )
        content = f"{app_id}:{','.join(cats)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_surfaces": len(self._surfaces),
            "total_bindings": len(self._bindings),
            "max_surfaces_per_app": MAX_SURFACES_PER_APP,
            "forbidden_count": len(FORBIDDEN_DIRECT_CAPABILITIES),
        }
