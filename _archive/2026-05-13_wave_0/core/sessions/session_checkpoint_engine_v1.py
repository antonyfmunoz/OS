"""Session Checkpoint Engine v1.

Creates deterministic checkpoints that snapshot the full
continuity state of a substrate session:
  continuity state, cognition state, workflow state,
  embodiment state, ingress state, chronology

Supports 3 checkpoint types:
  resumable        — can resume session from this point
  replayable       — can replay session decisions from this point
  lineage_complete — full lineage chain preserved

UMH substrate subsystem. Phase 96.8BV.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.sessions.persistent_substrate_session_contracts_v1 import (
    CheckpointType,
    SessionCheckpoint,
    SessionContinuityState,
    _content_hash,
    _now_iso,
)


class SessionCheckpointEngine:
    """Creates and restores deterministic session checkpoints.

    Checkpoints are immutable snapshots. Same continuity state
    always produces the same checkpoint hash.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/substrate_sessions",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoints: dict[str, list[SessionCheckpoint]] = {}
        self._total_checkpoints: int = 0

    def create_checkpoint(
        self,
        session_id: str,
        continuity_state: SessionContinuityState,
        chronology_snapshot: list[dict[str, Any]] | None = None,
        checkpoint_type: CheckpointType = CheckpointType.RESUMABLE,
    ) -> SessionCheckpoint:
        """Create a deterministic checkpoint for a session."""
        seq = len(self._checkpoints.get(session_id, []))

        checkpoint = SessionCheckpoint(
            session_id=session_id,
            checkpoint_type=checkpoint_type.value,
            continuity_state=continuity_state,
            chronology_snapshot=chronology_snapshot or [],
            sequence_number=seq,
        )

        if session_id not in self._checkpoints:
            self._checkpoints[session_id] = []
        self._checkpoints[session_id].append(checkpoint)
        self._total_checkpoints += 1

        path = self._state_dir / f"session_checkpoint_{checkpoint.checkpoint_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

        ledger = self._state_dir / "session_checkpoints.jsonl"
        with ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "checkpoint_id": checkpoint.checkpoint_id,
                "session_id": session_id,
                "checkpoint_type": checkpoint_type.value,
                "content_hash": checkpoint.content_hash,
                "sequence_number": seq,
                "timestamp": checkpoint.timestamp,
            }, default=str) + "\n")

        return checkpoint

    def get_latest_checkpoint(
        self, session_id: str,
    ) -> SessionCheckpoint | None:
        checkpoints = self._checkpoints.get(session_id, [])
        return checkpoints[-1] if checkpoints else None

    def get_checkpoint_by_id(
        self, checkpoint_id: str,
    ) -> SessionCheckpoint | None:
        for session_checkpoints in self._checkpoints.values():
            for cp in session_checkpoints:
                if cp.checkpoint_id == checkpoint_id:
                    return cp
        return None

    def get_checkpoints(
        self, session_id: str,
    ) -> list[dict[str, Any]]:
        return [
            cp.to_dict()
            for cp in self._checkpoints.get(session_id, [])
        ]

    def verify_checkpoint_hash(
        self, checkpoint: SessionCheckpoint,
    ) -> bool:
        """Verify that a checkpoint's content hash is deterministic."""
        expected = _content_hash(checkpoint._hashable())
        return checkpoint.content_hash == expected

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checkpoints": self._total_checkpoints,
            "sessions_with_checkpoints": len(self._checkpoints),
        }
