"""Deployment Checkpoint Engine v1.

Checkpoints deployment states, restores deployment states,
verifies deterministic restoration, preserves continuity lineage.

UMH substrate subsystem. Phase 96.8CF.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.orchestration.live_operational_deployment_contracts_v1 import (
    DeploymentCheckpointState,
    _now_iso,
)

MAX_CHECKPOINTS = 50
MAX_CHECKPOINTS_PER_OPERATION = 10


class DeploymentCheckpointEngine:
    """Manages deployment state checkpoints."""

    def __init__(self, state_dir: str | Path = "data/runtime/orchestration") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoints: list[DeploymentCheckpointState] = []

    def create_checkpoint(
        self,
        operation_id: str,
        state_data: str,
    ) -> DeploymentCheckpointState | None:
        if len(self._checkpoints) >= MAX_CHECKPOINTS:
            return None

        per_op = sum(
            1 for c in self._checkpoints if c.operation_id == operation_id
        )
        if per_op >= MAX_CHECKPOINTS_PER_OPERATION:
            return None

        content_hash = hashlib.sha256(state_data.encode()).hexdigest()[:16]

        checkpoint = DeploymentCheckpointState(
            operation_id=operation_id,
            content_hash=content_hash,
        )
        self._checkpoints.append(checkpoint)

        path = self._state_dir / f"checkpoint_{checkpoint.checkpoint_id}.json"
        path.write_text(
            json.dumps(checkpoint.to_dict(), default=str),
            encoding="utf-8",
        )

        return checkpoint

    def restore_checkpoint(
        self,
        checkpoint_id: str,
    ) -> DeploymentCheckpointState | None:
        for c in self._checkpoints:
            if c.checkpoint_id == checkpoint_id:
                return c
        return None

    def verify_determinism(
        self,
        checkpoint_id: str,
        state_data: str,
    ) -> bool:
        checkpoint = self.restore_checkpoint(checkpoint_id)
        if checkpoint is None:
            return False
        content_hash = hashlib.sha256(state_data.encode()).hexdigest()[:16]
        return content_hash == checkpoint.content_hash

    def get_checkpoints_for_operation(
        self,
        operation_id: str,
    ) -> list[dict[str, Any]]:
        return [
            c.to_dict()
            for c in self._checkpoints
            if c.operation_id == operation_id
        ]

    def get_latest_checkpoint(
        self,
        operation_id: str,
    ) -> DeploymentCheckpointState | None:
        matches = [
            c for c in self._checkpoints if c.operation_id == operation_id
        ]
        return matches[-1] if matches else None

    def get_stats(self) -> dict[str, object]:
        return {
            "total_checkpoints": len(self._checkpoints),
        }
