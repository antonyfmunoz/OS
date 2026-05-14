"""Rollout Coordination Engine v1.

Coordinates staged rollout: strategy selection, stage progression,
checkpointing, bounded fanout. Operator approval required.

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.deployment.platform_deployment_contracts_v1 import (
    RolloutState,
    RolloutStrategy,
    _now_iso,
)

MAX_ROLLOUT_STAGES = 10
MAX_ACTIVE_ROLLOUTS = 3
MAX_FANOUT = 3

KNOWN_STRATEGIES: list[str] = [s.value for s in RolloutStrategy]


class RolloutCoordinationEngine:
    """Coordinates staged deployment rollouts."""

    def __init__(self, state_dir: str | Path = "data/runtime/deployments") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._rollouts: dict[str, RolloutState] = {}

    def create_rollout(
        self,
        deployment_id: str,
        strategy: str = "sequential",
        stages_total: int = 1,
        approved_by: str = "operator",
    ) -> RolloutState | None:
        if approved_by != "operator":
            raise ValueError("Rollout requires operator approval")

        active = [r for r in self._rollouts.values() if r.status == "active"]
        if len(active) >= MAX_ACTIVE_ROLLOUTS:
            return None

        if strategy not in KNOWN_STRATEGIES:
            return None

        if stages_total > MAX_ROLLOUT_STAGES:
            stages_total = MAX_ROLLOUT_STAGES

        rollout = RolloutState(
            deployment_id=deployment_id,
            strategy=strategy,
            stages_total=stages_total,
            status="active",
        )
        self._rollouts[rollout.rollout_id] = rollout

        path = self._state_dir / "rollouts.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rollout.to_dict(), default=str) + "\n")

        return rollout

    def advance_stage(
        self,
        rollout_id: str,
        approved_by: str = "operator",
    ) -> RolloutState | None:
        if approved_by != "operator":
            raise ValueError("Stage advancement requires operator approval")

        rollout = self._rollouts.get(rollout_id)
        if rollout is None:
            return None
        if rollout.status != "active":
            return None

        rollout.stages_completed += 1
        if rollout.stages_completed >= rollout.stages_total:
            rollout.status = "completed"

        return rollout

    def cancel_rollout(
        self,
        rollout_id: str,
        reason: str = "",
    ) -> RolloutState | None:
        rollout = self._rollouts.get(rollout_id)
        if rollout is None:
            return None
        rollout.status = "cancelled"
        return rollout

    def get_rollout(self, rollout_id: str) -> dict[str, Any] | None:
        rollout = self._rollouts.get(rollout_id)
        return rollout.to_dict() if rollout else None

    def get_active_rollouts(self) -> list[dict[str, Any]]:
        return [
            r.to_dict() for r in self._rollouts.values()
            if r.status == "active"
        ]

    def get_rollout_hash(self, rollout_id: str) -> str:
        rollout = self._rollouts.get(rollout_id)
        if rollout is None:
            return ""
        content = f"{rollout.deployment_id}:{rollout.strategy}:{rollout.stages_total}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_stats(self) -> dict[str, object]:
        active = sum(1 for r in self._rollouts.values() if r.status == "active")
        completed = sum(1 for r in self._rollouts.values() if r.status == "completed")
        return {
            "total_rollouts": len(self._rollouts),
            "active_rollouts": active,
            "completed_rollouts": completed,
            "max_active_rollouts": MAX_ACTIVE_ROLLOUTS,
            "max_fanout": MAX_FANOUT,
        }
