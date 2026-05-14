"""Cognition Continuity Bridge v1.

Bridges cognition state across session boundaries.
Handles persistence of cognitive outcomes, checkpoint
management, and continuity restoration.

Responsibilities:
  - Persist cognitive outcomes (complete/suspended/stale/failed)
  - Create and manage cognitive checkpoints
  - Build resume packets for session restoration
  - Track open cognitive loops across sessions
  - Maintain continuity lineage

The bridge does not generate intent or take autonomous action.
It enables other components to persist and restore state.

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    CognitionPhase,
    CognitiveCheckpoint,
    ContinuityFocusState,
    OperatorMode,
    _content_hash,
    _new_id,
    _now_iso,
)


class CognitionContinuityBridge:
    """Manages cognition continuity across session boundaries.

    Persists outcomes, creates checkpoints, and builds
    resume packets. Does not execute actions.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/cognition_state",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._continuity_records: list[dict[str, Any]] = []
        self._total_persists: int = 0
        self._total_resumes: int = 0
        self._open_loops_tracked: int = 0

    # ------------------------------------------------------------------
    # Outcome persistence
    # ------------------------------------------------------------------

    def persist_outcome(
        self,
        session_id: str,
        phase: CognitionPhase,
        cognitive_snapshot: dict[str, Any],
        open_loops: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Persist a cognitive outcome at session/workflow end."""
        continuation_type = self._phase_to_continuation(phase)

        record = {
            "record_id": _new_id("cogcont"),
            "session_id": session_id,
            "phase": phase.value,
            "continuation_type": continuation_type,
            "has_checkpoint": bool(
                cognitive_snapshot.get("cognitive_state", {}).get(
                    "last_checkpoint_id", ""
                )
            ),
            "open_loop_count": len(open_loops) if open_loops else 0,
            "snapshot_hash": _content_hash(cognitive_snapshot),
            "timestamp": _now_iso(),
        }

        self._continuity_records.append(record)
        self._total_persists += 1

        if open_loops:
            self._open_loops_tracked += len(open_loops)
            self._persist_open_loops(session_id, open_loops)

        path = self._state_dir / "cognition_continuity_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

        return record

    def _phase_to_continuation(self, phase: CognitionPhase) -> str:
        mapping = {
            CognitionPhase.ARCHIVED: "complete",
            CognitionPhase.TERMINATED: "complete",
            CognitionPhase.CHECKPOINTED: "checkpointed",
            CognitionPhase.SUSPENDED: "suspended",
            CognitionPhase.STALE: "stale",
        }
        return mapping.get(phase, "active")

    def _persist_open_loops(
        self, session_id: str, loops: list[dict[str, Any]]
    ) -> None:
        path = self._state_dir / f"open_loops_{session_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump({
                "session_id": session_id,
                "loops": loops,
                "count": len(loops),
                "timestamp": _now_iso(),
            }, f, indent=2, default=str)

    # ------------------------------------------------------------------
    # Checkpoint management
    # ------------------------------------------------------------------

    def create_checkpoint(
        self,
        session_id: str,
        operator_mode: OperatorMode,
        phase: CognitionPhase,
        cognitive_state: dict[str, Any],
        focus_snapshot: dict[str, Any] | None = None,
        loops_snapshot: list[dict[str, Any]] | None = None,
        attention_snapshot: dict[str, Any] | None = None,
        chain_ids: list[str] | None = None,
    ) -> CognitiveCheckpoint:
        """Create a cognitive checkpoint."""
        checkpoint = CognitiveCheckpoint(
            session_id=session_id,
            operator_mode=operator_mode,
            phase=phase,
            cognitive_state_snapshot=cognitive_state,
            active_focus_snapshot=focus_snapshot or {},
            open_loops_snapshot=loops_snapshot or [],
            attention_snapshot=attention_snapshot or {},
            continuity_chain_ids=chain_ids or [],
        )

        path = self._state_dir / f"checkpoint_{checkpoint.checkpoint_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

        self._total_persists += 1
        return checkpoint

    def load_checkpoint(self, checkpoint_id: str) -> dict[str, Any] | None:
        """Load a checkpoint from disk."""
        path = self._state_dir / f"checkpoint_{checkpoint_id}.json"
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Resume packets
    # ------------------------------------------------------------------

    def build_resume_packet(
        self,
        previous_session_id: str,
    ) -> dict[str, Any]:
        """Build a resume packet from prior session state."""
        packet: dict[str, Any] = {
            "packet_id": _new_id("cogres"),
            "previous_session_id": previous_session_id,
            "timestamp": _now_iso(),
            "continuity_records": [],
            "open_loops": [],
            "latest_checkpoint": None,
        }

        lineage_path = self._state_dir / "cognition_continuity_lineage.jsonl"
        if lineage_path.exists():
            with lineage_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    if record.get("session_id") == previous_session_id:
                        packet["continuity_records"].append(record)

        loops_path = self._state_dir / f"open_loops_{previous_session_id}.json"
        if loops_path.exists():
            with loops_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                packet["open_loops"] = data.get("loops", [])

        checkpoints = sorted(
            self._state_dir.glob("checkpoint_*.json"),
            key=lambda p: p.stat().st_mtime,
        )
        if checkpoints:
            with checkpoints[-1].open("r", encoding="utf-8") as f:
                packet["latest_checkpoint"] = json.load(f)

        self._total_resumes += 1
        return packet

    # ------------------------------------------------------------------
    # Continuity focus restoration
    # ------------------------------------------------------------------

    def restore_focus(
        self,
        session_id: str,
        previous_session_id: str,
        resume_packet: dict[str, Any],
    ) -> ContinuityFocusState:
        """Build a continuity focus state from a resume packet."""
        checkpoint = resume_packet.get("latest_checkpoint", {})
        open_loops = resume_packet.get("open_loops", [])

        focus_ids = []
        if checkpoint:
            focus_snap = checkpoint.get("active_focus_snapshot", {})
            if focus_snap.get("focus_id"):
                focus_ids.append(focus_snap["focus_id"])

        loop_ids = [l.get("loop_id", "") for l in open_loops if l.get("loop_id")]

        workflow_ids = []
        if checkpoint:
            cog_state = checkpoint.get("cognitive_state_snapshot", {})
            workflow_ids = cog_state.get("active_workflow_ids", [])

        total_restored = len(focus_ids) + len(loop_ids) + len(workflow_ids)
        max_possible = max(total_restored, 1)
        continuity_score = total_restored / max_possible

        state = ContinuityFocusState(
            session_id=session_id,
            previous_session_id=previous_session_id,
            restored_focus_ids=focus_ids,
            restored_loop_ids=loop_ids,
            restored_workflow_ids=workflow_ids,
            continuity_score=continuity_score,
            restoration_complete=True,
        )
        return state

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_persists": self._total_persists,
            "total_resumes": self._total_resumes,
            "open_loops_tracked": self._open_loops_tracked,
            "continuity_records": len(self._continuity_records),
        }
