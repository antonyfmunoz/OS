"""Trust Lifecycle Engine v1.

7-state lifecycle: defined → collected → hashed → bundled → verified → exported → archived.

UMH substrate subsystem. Phase 96.8CM.
"""

from __future__ import annotations

from typing import Any

from core.trust.sovereign_operational_trust_contracts_v1 import (
    TrustPhase,
    _now_iso,
)


TRUST_LIFECYCLE_ORDER = [
    TrustPhase.DEFINED,
    TrustPhase.COLLECTED,
    TrustPhase.HASHED,
    TrustPhase.BUNDLED,
    TrustPhase.VERIFIED,
    TrustPhase.EXPORTED,
    TrustPhase.ARCHIVED,
]

_TRUST_PHASE_INDEX = {p: i for i, p in enumerate(TRUST_LIFECYCLE_ORDER)}

TERMINAL_TRUST_PHASES = {TrustPhase.ARCHIVED}


class TrustLifecycleEngine:
    """Manages trust proof lifecycle transitions."""

    def __init__(self) -> None:
        self._transitions: list[dict[str, Any]] = []

    def can_transition(self, current: TrustPhase, target: TrustPhase) -> bool:
        ci = _TRUST_PHASE_INDEX.get(current)
        ti = _TRUST_PHASE_INDEX.get(target)
        if ci is None or ti is None:
            return False
        return ti == ci + 1

    def transition(self, current: TrustPhase, target: TrustPhase) -> dict[str, Any]:
        if current in TERMINAL_TRUST_PHASES:
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
