"""Checkpoint Integrity Engine v1.

Creates and validates checkpoints for subsystem state.
Ensures checkpoint hashes match stored state for integrity.

Cannot restore state — only creates and validates checkpoints.

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.resilience.adaptive_resilience_contracts_v1 import (
    CheckpointIntegrityState,
    ContinuityPreservationState,
    _new_id,
    _now_iso,
)


MAX_CHECKPOINTS_PER_SUBSYSTEM: int = 10
MAX_TOTAL_CHECKPOINTS: int = 100


class CheckpointIntegrityEngine:
    """Creates and validates state checkpoints for resilience."""

    def __init__(self, state_dir: str | Path = "data/runtime/resilience") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoints: dict[str, list[CheckpointIntegrityState]] = {}
        self._total_checkpoints: int = 0
        self._total_validations: int = 0
        self._total_valid: int = 0

    def create_checkpoint(
        self,
        subsystem_id: str,
        state_data: dict[str, Any],
    ) -> CheckpointIntegrityState:
        checkpoint_id = _new_id("ckpt")
        state_hash = self._compute_hash(state_data)

        checkpoint = CheckpointIntegrityState(
            checkpoint_id=checkpoint_id,
            subsystem_id=subsystem_id,
            state_hash=state_hash,
            valid=True,
        )

        if subsystem_id not in self._checkpoints:
            self._checkpoints[subsystem_id] = []

        self._checkpoints[subsystem_id].append(checkpoint)

        if len(self._checkpoints[subsystem_id]) > MAX_CHECKPOINTS_PER_SUBSYSTEM:
            self._checkpoints[subsystem_id] = self._checkpoints[subsystem_id][
                -MAX_CHECKPOINTS_PER_SUBSYSTEM:
            ]

        self._total_checkpoints += 1

        path = self._state_dir / "checkpoint_integrity.jsonl"
        with path.open("a", encoding="utf-8") as f:
            record = checkpoint.to_dict()
            record["state_data"] = state_data
            f.write(json.dumps(record, default=str) + "\n")

        return checkpoint

    def validate_checkpoint(
        self,
        subsystem_id: str,
        state_data: dict[str, Any],
    ) -> CheckpointIntegrityState | None:
        self._total_validations += 1

        if subsystem_id not in self._checkpoints:
            return None
        if not self._checkpoints[subsystem_id]:
            return None

        latest = self._checkpoints[subsystem_id][-1]
        current_hash = self._compute_hash(state_data)

        valid = current_hash == latest.state_hash
        if valid:
            self._total_valid += 1

        result = CheckpointIntegrityState(
            checkpoint_id=latest.checkpoint_id,
            subsystem_id=subsystem_id,
            state_hash=current_hash,
            valid=valid,
        )
        return result

    def get_latest_checkpoint(
        self, subsystem_id: str,
    ) -> CheckpointIntegrityState | None:
        if subsystem_id not in self._checkpoints:
            return None
        if not self._checkpoints[subsystem_id]:
            return None
        return self._checkpoints[subsystem_id][-1]

    def get_checkpoint_count(self, subsystem_id: str) -> int:
        return len(self._checkpoints.get(subsystem_id, []))

    def get_preservation_state(self) -> ContinuityPreservationState:
        preserved = list(self._checkpoints.keys())
        total = sum(len(v) for v in self._checkpoints.values())
        last = ""
        if preserved:
            last_sub = preserved[-1]
            if self._checkpoints[last_sub]:
                last = self._checkpoints[last_sub][-1].checkpoint_id

        return ContinuityPreservationState(
            preserved_subsystems=preserved,
            checkpoint_count=total,
            last_checkpoint=last,
            continuity_intact=True,
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checkpoints": self._total_checkpoints,
            "total_validations": self._total_validations,
            "total_valid": self._total_valid,
            "tracked_subsystems": len(self._checkpoints),
        }

    def _compute_hash(self, data: dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
