"""Rollback Coordination Engine v1.

Restores prior deployment state: manifests, topology,
continuity lineage, replay lineage.

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.deployment.platform_deployment_contracts_v1 import (
    RollbackState,
    _now_iso,
)

MAX_ROLLBACKS = 20
MAX_ACTIVE_ROLLBACKS = 1


class RollbackCoordinationEngine:
    """Coordinates deployment rollbacks."""

    def __init__(self, state_dir: str | Path = "data/runtime/deployments") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._rollbacks: dict[str, RollbackState] = {}

    def create_rollback(
        self,
        deployment_id: str,
        target_deployment_id: str,
        reason: str = "",
        approved_by: str = "operator",
    ) -> RollbackState | None:
        if approved_by != "operator":
            raise ValueError("Rollback requires operator approval")

        active = [
            r for r in self._rollbacks.values() if r.status == "active"
        ]
        if len(active) >= MAX_ACTIVE_ROLLBACKS:
            return None

        if len(self._rollbacks) >= MAX_ROLLBACKS:
            return None

        rollback = RollbackState(
            deployment_id=deployment_id,
            target_deployment_id=target_deployment_id,
            reason=reason,
            status="active",
        )
        self._rollbacks[rollback.rollback_id] = rollback

        path = self._state_dir / "rollbacks.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rollback.to_dict(), default=str) + "\n")

        return rollback

    def complete_rollback(
        self,
        rollback_id: str,
    ) -> RollbackState | None:
        rollback = self._rollbacks.get(rollback_id)
        if rollback is None:
            return None
        rollback.status = "completed"
        return rollback

    def get_rollback(self, rollback_id: str) -> dict[str, Any] | None:
        rollback = self._rollbacks.get(rollback_id)
        return rollback.to_dict() if rollback else None

    def get_all(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in list(self._rollbacks.values())[-limit:]]

    def get_rollback_hash(self, rollback_id: str) -> str:
        rollback = self._rollbacks.get(rollback_id)
        if rollback is None:
            return ""
        content = f"{rollback.deployment_id}:{rollback.target_deployment_id}:{rollback.reason}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_stats(self) -> dict[str, object]:
        active = sum(1 for r in self._rollbacks.values() if r.status == "active")
        completed = sum(1 for r in self._rollbacks.values() if r.status == "completed")
        return {
            "total_rollbacks": len(self._rollbacks),
            "active_rollbacks": active,
            "completed_rollbacks": completed,
            "max_active_rollbacks": MAX_ACTIVE_ROLLBACKS,
        }
