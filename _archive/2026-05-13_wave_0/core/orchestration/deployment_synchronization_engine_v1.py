"""Deployment Synchronization Engine v1.

Coordinates synchronization across application/runtime,
environment/runtime, deployment continuity, workflow/runtime,
and observability/runtime targets.

UMH substrate subsystem. Phase 96.8CF.
"""

from __future__ import annotations

from typing import Any

from core.orchestration.live_operational_deployment_contracts_v1 import (
    DeploymentSynchronizationState,
    SynchronizationTarget,
    _now_iso,
)

KNOWN_TARGETS = {t.value for t in SynchronizationTarget}
MAX_SYNC_OPERATIONS = 100
MAX_EPOCH_GAP = 10


class DeploymentSynchronizationEngine:
    """Coordinates deployment synchronization across targets."""

    def __init__(self) -> None:
        self._syncs: dict[str, DeploymentSynchronizationState] = {}
        self._epoch: int = 0

    def synchronize(
        self,
        target: str,
    ) -> DeploymentSynchronizationState | None:
        if target not in KNOWN_TARGETS:
            return None

        if len(self._syncs) >= MAX_SYNC_OPERATIONS and target not in self._syncs:
            return None

        self._epoch += 1

        state = DeploymentSynchronizationState(
            target=target,
            epoch=self._epoch,
            synchronized=True,
        )
        self._syncs[target] = state
        return state

    def get_sync_state(self, target: str) -> DeploymentSynchronizationState | None:
        return self._syncs.get(target)

    def check_epoch_gap(self, target_a: str, target_b: str) -> int | None:
        a = self._syncs.get(target_a)
        b = self._syncs.get(target_b)
        if a is None or b is None:
            return None
        return abs(a.epoch - b.epoch)

    def is_synchronized(self, target: str) -> bool:
        state = self._syncs.get(target)
        return state is not None and state.synchronized

    @property
    def current_epoch(self) -> int:
        return self._epoch

    def get_all_syncs(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._syncs.values()]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_syncs": len(self._syncs),
            "current_epoch": self._epoch,
            "synchronized_count": sum(
                1 for s in self._syncs.values() if s.synchronized
            ),
        }
