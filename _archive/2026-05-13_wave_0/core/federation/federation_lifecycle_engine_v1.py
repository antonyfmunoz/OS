"""Federation Lifecycle Engine v1.

6-state lifecycle:
identity_created → manifest_generated → peer_received →
peer_verified/peer_rejected → interoperability_reported → archived

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    FederationPhase,
    _now_iso,
)


FEDERATION_LIFECYCLE_ORDER = [
    FederationPhase.IDENTITY_CREATED,
    FederationPhase.MANIFEST_GENERATED,
    FederationPhase.PEER_RECEIVED,
    FederationPhase.PEER_VERIFIED,
    FederationPhase.INTEROPERABILITY_REPORTED,
    FederationPhase.ARCHIVED,
]

_FEDERATION_PHASE_INDEX = {p: i for i, p in enumerate(FEDERATION_LIFECYCLE_ORDER)}

VALID_TRANSITIONS: dict[FederationPhase, set[FederationPhase]] = {
    FederationPhase.IDENTITY_CREATED: {FederationPhase.MANIFEST_GENERATED},
    FederationPhase.MANIFEST_GENERATED: {FederationPhase.PEER_RECEIVED},
    FederationPhase.PEER_RECEIVED: {FederationPhase.PEER_VERIFIED, FederationPhase.PEER_REJECTED},
    FederationPhase.PEER_VERIFIED: {FederationPhase.INTEROPERABILITY_REPORTED},
    FederationPhase.PEER_REJECTED: {FederationPhase.ARCHIVED},
    FederationPhase.INTEROPERABILITY_REPORTED: {FederationPhase.ARCHIVED},
    FederationPhase.ARCHIVED: set(),
}

TERMINAL_FEDERATION_PHASES = {FederationPhase.ARCHIVED}


class FederationLifecycleEngine:
    """Manages federation readiness lifecycle transitions."""

    def __init__(self) -> None:
        self._transitions: list[dict[str, Any]] = []

    def can_transition(self, current: FederationPhase, target: FederationPhase) -> bool:
        allowed = VALID_TRANSITIONS.get(current, set())
        return target in allowed

    def transition(self, current: FederationPhase, target: FederationPhase) -> dict[str, Any]:
        if current in TERMINAL_FEDERATION_PHASES:
            raise ValueError(f"Cannot transition from terminal phase: {current.value}")
        if not self.can_transition(current, target):
            raise ValueError(f"Invalid transition: {current.value} → {target.value}")
        entry = {
            "from": current.value,
            "to": target.value,
            "timestamp": _now_iso(),
        }
        self._transitions.append(entry)
        return entry

    def get_stats(self) -> dict[str, Any]:
        return {"total_transitions": len(self._transitions)}
