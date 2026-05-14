"""Operational Continuation Engine v1.

Restores operational campaigns, execution stages, chronology,
checkpoints, workflow state, cognition continuity, and
embodiment continuity. Binds to persistent substrate sessions.

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.operations.long_horizon_operational_contracts_v1 import (
    OperationalCheckpoint,
    OperationalContinuationState,
    _content_hash,
    _new_id,
    _now_iso,
)


class OperationalContinuationEngine:
    """Restores operational campaigns from checkpoints.

    Binds to persistent substrate sessions. Cannot execute —
    only captures and restores operational state.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/operations",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoints: dict[str, list[OperationalCheckpoint]] = {}
        self._continuations: list[OperationalContinuationState] = []
        self._total_checkpoints: int = 0
        self._total_restorations: int = 0

    def create_checkpoint(
        self,
        campaign_id: str,
        stage_index: int,
        campaign_state: str,
        stage_states: list[dict[str, Any]] | None = None,
    ) -> OperationalCheckpoint:
        """Create a deterministic operational checkpoint."""
        checkpoint = OperationalCheckpoint(
            campaign_id=campaign_id,
            stage_index=stage_index,
            campaign_state=campaign_state,
            stage_states=stage_states or [],
        )

        if campaign_id not in self._checkpoints:
            self._checkpoints[campaign_id] = []
        self._checkpoints[campaign_id].append(checkpoint)
        self._total_checkpoints += 1

        path = self._state_dir / f"op_checkpoint_{checkpoint.checkpoint_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

        ledger = self._state_dir / "operational_checkpoints.jsonl"
        with ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "checkpoint_id": checkpoint.checkpoint_id,
                "campaign_id": campaign_id,
                "stage_index": stage_index,
                "content_hash": checkpoint.content_hash,
                "timestamp": checkpoint.timestamp,
            }, default=str) + "\n")

        return checkpoint

    def create_continuation(
        self,
        campaign_id: str,
        checkpoint_id: str,
        session_id: str = "",
        stage_index: int = 0,
        continuation_type: str = "resume",
    ) -> OperationalContinuationState:
        """Create a continuation state for later restoration."""
        cont = OperationalContinuationState(
            campaign_id=campaign_id,
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            stage_index=stage_index,
            continuation_type=continuation_type,
        )
        self._continuations.append(cont)

        path = self._state_dir / "operational_continuations.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(cont.to_dict(), default=str) + "\n")

        return cont

    def restore_from_checkpoint(
        self, checkpoint_id: str,
    ) -> OperationalCheckpoint | None:
        """Restore campaign state from a checkpoint."""
        for campaign_checkpoints in self._checkpoints.values():
            for cp in campaign_checkpoints:
                if cp.checkpoint_id == checkpoint_id:
                    self._total_restorations += 1
                    return cp
        return None

    def get_latest_checkpoint(
        self, campaign_id: str,
    ) -> OperationalCheckpoint | None:
        cps = self._checkpoints.get(campaign_id, [])
        return cps[-1] if cps else None

    def get_checkpoints(
        self, campaign_id: str,
    ) -> list[dict[str, Any]]:
        return [
            cp.to_dict()
            for cp in self._checkpoints.get(campaign_id, [])
        ]

    def verify_checkpoint_hash(
        self, checkpoint: OperationalCheckpoint,
    ) -> bool:
        expected = _content_hash(checkpoint._hashable())
        return checkpoint.content_hash == expected

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checkpoints": self._total_checkpoints,
            "total_restorations": self._total_restorations,
            "campaigns_with_checkpoints": len(self._checkpoints),
            "total_continuations": len(self._continuations),
        }
