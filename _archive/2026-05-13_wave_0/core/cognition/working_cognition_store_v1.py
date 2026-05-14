"""Working Cognition Store v1.

Persists and retrieves cognitive state across sessions.
Manages the durable layer beneath the cognition engine:
  - Persist cognitive snapshots to disk
  - Load latest state for session resumption
  - Track cognition history (JSONL lineage)
  - Manage checkpoint lifecycle on disk

No autonomous behavior. No self-directed persistence.
All persistence triggered by engine or operator commands.

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    CognitiveCheckpoint,
    CognitionPhase,
    OperatorMode,
    _new_id,
    _now_iso,
)


class WorkingCognitionStore:
    """Durable persistence for cognitive state.

    Reads and writes cognitive snapshots, checkpoints,
    and lineage to disk. Does not interpret or act on
    the state — that is the engine's responsibility.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/cognition_state",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_persists: int = 0
        self._total_loads: int = 0

    # ------------------------------------------------------------------
    # Snapshot persistence
    # ------------------------------------------------------------------

    def persist_snapshot(
        self,
        session_id: str,
        snapshot: dict[str, Any],
    ) -> str:
        """Persist a full cognitive snapshot to disk."""
        snapshot_id = _new_id("cogsnap")
        record = {
            "snapshot_id": snapshot_id,
            "session_id": session_id,
            "timestamp": _now_iso(),
            "snapshot": snapshot,
        }

        snapshot_path = self._state_dir / f"snapshot_{snapshot_id}.json"
        with snapshot_path.open("w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, default=str)

        lineage_path = self._state_dir / "cognition_snapshots.jsonl"
        with lineage_path.open("a", encoding="utf-8") as f:
            summary = {
                "snapshot_id": snapshot_id,
                "session_id": session_id,
                "timestamp": record["timestamp"],
                "operator_mode": snapshot.get("cognitive_state", {}).get(
                    "operator_mode", ""
                ),
                "phase": snapshot.get("cognitive_state", {}).get("phase", ""),
            }
            f.write(json.dumps(summary, default=str) + "\n")

        self._total_persists += 1
        return snapshot_id

    def load_latest_snapshot(self) -> dict[str, Any] | None:
        """Load the most recent cognitive snapshot."""
        lineage_path = self._state_dir / "cognition_snapshots.jsonl"
        if not lineage_path.exists():
            return None

        last_line = ""
        with lineage_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last_line = line

        if not last_line:
            return None

        summary = json.loads(last_line)
        snapshot_id = summary.get("snapshot_id", "")
        snapshot_path = self._state_dir / f"snapshot_{snapshot_id}.json"

        if not snapshot_path.exists():
            return None

        with snapshot_path.open("r", encoding="utf-8") as f:
            record = json.load(f)

        self._total_loads += 1
        return record.get("snapshot", None)

    def load_snapshot_by_id(self, snapshot_id: str) -> dict[str, Any] | None:
        """Load a specific snapshot by ID."""
        snapshot_path = self._state_dir / f"snapshot_{snapshot_id}.json"
        if not snapshot_path.exists():
            return None

        with snapshot_path.open("r", encoding="utf-8") as f:
            record = json.load(f)

        self._total_loads += 1
        return record.get("snapshot", None)

    def list_snapshots(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent snapshot summaries."""
        lineage_path = self._state_dir / "cognition_snapshots.jsonl"
        if not lineage_path.exists():
            return []

        entries: list[dict[str, Any]] = []
        with lineage_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        return entries[-limit:]

    # ------------------------------------------------------------------
    # Checkpoint management
    # ------------------------------------------------------------------

    def persist_checkpoint(self, checkpoint: CognitiveCheckpoint) -> str:
        """Persist a checkpoint to disk."""
        path = self._state_dir / f"checkpoint_{checkpoint.checkpoint_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

        self._total_persists += 1
        return checkpoint.checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> dict[str, Any] | None:
        """Load a checkpoint by ID."""
        path = self._state_dir / f"checkpoint_{checkpoint_id}.json"
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self._total_loads += 1
        return data

    def list_checkpoints(self) -> list[str]:
        """List all checkpoint IDs on disk."""
        return sorted([
            p.stem.replace("checkpoint_", "")
            for p in self._state_dir.glob("checkpoint_*.json")
        ])

    # ------------------------------------------------------------------
    # Session lineage
    # ------------------------------------------------------------------

    def persist_session_record(
        self,
        session_id: str,
        operator_mode: str = "",
        phase: str = "",
        focus_description: str = "",
        open_loop_count: int = 0,
    ) -> None:
        """Append a session record to the lineage."""
        record = {
            "session_id": session_id,
            "operator_mode": operator_mode,
            "phase": phase,
            "focus_description": focus_description,
            "open_loop_count": open_loop_count,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / "session_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def get_session_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent session history."""
        path = self._state_dir / "session_lineage.jsonl"
        if not path.exists():
            return []

        entries: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        return entries[-limit:]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_persists": self._total_persists,
            "total_loads": self._total_loads,
            "snapshots_on_disk": len(list(
                self._state_dir.glob("snapshot_*.json")
            )),
            "checkpoints_on_disk": len(list(
                self._state_dir.glob("checkpoint_*.json")
            )),
        }
