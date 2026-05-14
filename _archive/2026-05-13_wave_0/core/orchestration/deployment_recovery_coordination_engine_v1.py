"""Deployment Recovery Coordination Engine v1.

Coordinates recovery recommendations, rollback preparation,
degraded deployment states. Preserves governance enforcement.

NEVER auto-heals, auto-rollbacks, or auto-redeploys.

UMH substrate subsystem. Phase 96.8CF.
"""

from __future__ import annotations

from typing import Any

from core.orchestration.live_operational_deployment_contracts_v1 import (
    DeploymentRecoveryState,
    RecoveryAction,
    _now_iso,
)

MAX_PENDING_RECOMMENDATIONS = 20
MAX_HISTORY = 100

KNOWN_ACTIONS = {a.value for a in RecoveryAction}


class DeploymentRecoveryCoordinationEngine:
    """Coordinates deployment recovery — recommends, never executes."""

    def __init__(self) -> None:
        self._pending: list[DeploymentRecoveryState] = []
        self._history: list[DeploymentRecoveryState] = []

    def recommend(
        self,
        operation_id: str,
        action: str,
        reason: str = "",
    ) -> DeploymentRecoveryState | None:
        if action not in KNOWN_ACTIONS:
            return None

        if len(self._pending) >= MAX_PENDING_RECOMMENDATIONS:
            return None

        state = DeploymentRecoveryState(
            operation_id=operation_id,
            action=action,
            reason=reason,
        )
        self._pending.append(state)
        return state

    def approve(
        self,
        recovery_id: str,
        approved_by: str = "operator",
    ) -> DeploymentRecoveryState | None:
        if approved_by != "operator":
            raise ValueError("Recovery approval requires operator")

        for i, rec in enumerate(self._pending):
            if rec.recovery_id == recovery_id:
                rec.approved_by = approved_by
                self._history.append(rec)
                self._pending.pop(i)
                return rec
        return None

    def deny(
        self,
        recovery_id: str,
        denied_by: str = "operator",
    ) -> DeploymentRecoveryState | None:
        if denied_by != "operator":
            raise ValueError("Recovery denial requires operator")

        for i, rec in enumerate(self._pending):
            if rec.recovery_id == recovery_id:
                rec.approved_by = ""
                self._history.append(rec)
                self._pending.pop(i)
                return rec
        return None

    def get_pending(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._pending]

    def get_history(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history]

    def get_stats(self) -> dict[str, object]:
        return {
            "pending_count": len(self._pending),
            "history_count": len(self._history),
        }
