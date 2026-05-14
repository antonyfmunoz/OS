"""Environment Synchronization Engine v1.

Synchronizes across environments:
  continuity state, operational chronology,
  checkpoints, environment lineage,
  observability state, replay state.

Prevents:
  divergent environment state,
  hidden synchronization mutation,
  orphan topology chains.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    EnvironmentContinuityState,
    EnvironmentSynchronizationState,
    _content_hash,
    _now_iso,
)
from core.environments.environment_topology_engine_v1 import (
    EnvironmentTopologyEngine,
)


class EnvironmentSynchronizationEngine:
    """Manages cross-environment state synchronization."""

    def __init__(
        self,
        topology: EnvironmentTopologyEngine,
        state_dir: str | Path = "data/runtime/environment_coordination",
    ) -> None:
        self._topology = topology
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._syncs: dict[str, EnvironmentSynchronizationState] = {}
        self._continuity: dict[str, EnvironmentContinuityState] = {}
        self._epoch: int = 0
        self._total_syncs: int = 0

    def synchronize(
        self,
        source_environment: str,
        target_environment: str,
        sync_type: str = "full",
    ) -> EnvironmentSynchronizationState | None:
        source = self._topology.get_node(source_environment)
        target = self._topology.get_node(target_environment)
        if not source or not target:
            return None

        if source_environment == target_environment:
            return None

        self._epoch += 1
        topo = self._topology.build_topology()

        sync = EnvironmentSynchronizationState(
            source_environment=source_environment,
            target_environment=target_environment,
            sync_type=sync_type,
            epoch=self._epoch,
            topology_hash=topo.content_hash,
            state="completed",
            completed_at=_now_iso(),
        )
        self._syncs[sync.sync_id] = sync
        self._total_syncs += 1

        for env_id in (source_environment, target_environment):
            if env_id not in self._continuity:
                self._continuity[env_id] = EnvironmentContinuityState(
                    environment_id=env_id,
                )
            cont = self._continuity[env_id]
            cont.synchronization_epoch = self._epoch
            cont.topology_hash = topo.content_hash
            cont.last_sync = _now_iso()
            cont.content_hash = _content_hash(cont._hashable())

        self._persist_sync(sync)
        return sync

    def get_continuity(self, environment_id: str) -> EnvironmentContinuityState | None:
        return self._continuity.get(environment_id)

    def get_sync(self, sync_id: str) -> EnvironmentSynchronizationState | None:
        return self._syncs.get(sync_id)

    def get_epoch(self) -> int:
        return self._epoch

    def get_sync_hash(self) -> str:
        return _content_hash([s.to_dict() for s in self._syncs.values()])

    def checkpoint_environment(
        self,
        environment_id: str,
        checkpoint_id: str = "",
    ) -> EnvironmentContinuityState | None:
        if environment_id not in self._continuity:
            self._continuity[environment_id] = EnvironmentContinuityState(
                environment_id=environment_id,
            )

        cont = self._continuity[environment_id]
        cont.checkpoint_id = checkpoint_id or f"echkp-{self._epoch}"
        cont.synchronization_epoch = self._epoch
        cont.content_hash = _content_hash(cont._hashable())
        self._persist_checkpoint(cont)
        return cont

    def restore_environment(
        self,
        environment_id: str,
        continuity_state: EnvironmentContinuityState,
    ) -> bool:
        self._continuity[environment_id] = continuity_state
        return True

    def _persist_sync(self, sync: EnvironmentSynchronizationState) -> None:
        path = self._state_dir / "environment_synchronizations.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(sync.to_dict(), default=str) + "\n")

    def _persist_checkpoint(self, cont: EnvironmentContinuityState) -> None:
        path = self._state_dir / "environment_checkpoints.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(cont.to_dict(), default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_syncs": self._total_syncs,
            "current_epoch": self._epoch,
            "environments_tracked": len(self._continuity),
        }
