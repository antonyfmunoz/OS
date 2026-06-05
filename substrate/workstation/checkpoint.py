"""Continuity checkpoint — state snapshot on continuity transitions.

When a continuity transition occurs, a checkpoint captures the full
system state: modes, active work, agents, approvals, traces, and
recommended next actions. Feeds the resume endpoint and return brief.

Phase 14.11B. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContinuityCheckpoint:
    """Point-in-time system state captured on continuity transition."""

    checkpoint_id: str = ""
    timestamp: str = ""
    previous_continuity_state: str = ""
    new_continuity_state: str = ""
    lifecycle_mode: str = ""
    active_profile_modes: list[str] = field(default_factory=list)
    risk_ceiling: str = ""
    active_node: str = ""
    active_environment: str = ""
    active_work_packets: list[dict[str, Any]] = field(default_factory=list)
    active_sessions: list[dict[str, Any]] = field(default_factory=list)
    active_agents: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    recent_traces: list[dict[str, Any]] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    recommended_next_action: str = ""
    safe_work_constraints: dict[str, Any] = field(default_factory=dict)
    transition_reason: str = ""

    def __post_init__(self) -> None:
        if not self.checkpoint_id:
            self.checkpoint_id = f"ckpt_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContinuityCheckpoint:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CheckpointManager:
    """Manages checkpoint persistence and retrieval."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        if state_dir is None:
            root = os.environ.get("UMH_ROOT", "/opt/OS")
            state_dir = os.path.join(root, "data", "umh", "workstation_state")
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._current_path = self._dir / "latest_checkpoint.json"
        self._history_path = self._dir / "checkpoint_history.jsonl"

    def create_checkpoint(
        self,
        previous_state: str,
        new_state: str,
        lifecycle_mode: str = "",
        active_profile_modes: list[str] | None = None,
        risk_ceiling: str = "",
        active_node: str = "",
        active_environment: str = "",
        active_work_packets: list[dict[str, Any]] | None = None,
        active_sessions: list[dict[str, Any]] | None = None,
        active_agents: list[dict[str, Any]] | None = None,
        pending_approvals: list[dict[str, Any]] | None = None,
        recent_traces: list[dict[str, Any]] | None = None,
        open_loops: list[str] | None = None,
        recommended_next_action: str = "",
        safe_work_constraints: dict[str, Any] | None = None,
        transition_reason: str = "",
    ) -> ContinuityCheckpoint:
        """Create and persist a new checkpoint."""
        checkpoint = ContinuityCheckpoint(
            previous_continuity_state=previous_state,
            new_continuity_state=new_state,
            lifecycle_mode=lifecycle_mode,
            active_profile_modes=active_profile_modes or [],
            risk_ceiling=risk_ceiling,
            active_node=active_node,
            active_environment=active_environment,
            active_work_packets=active_work_packets or [],
            active_sessions=active_sessions or [],
            active_agents=active_agents or [],
            pending_approvals=pending_approvals or [],
            recent_traces=recent_traces or [],
            open_loops=open_loops or [],
            recommended_next_action=recommended_next_action,
            safe_work_constraints=safe_work_constraints or {},
            transition_reason=transition_reason,
        )

        self._persist(checkpoint)
        logger.info(
            "Checkpoint created: %s → %s (%s)",
            previous_state, new_state, checkpoint.checkpoint_id,
        )
        return checkpoint

    def latest(self) -> ContinuityCheckpoint | None:
        """Load the most recent checkpoint."""
        if not self._current_path.exists():
            return None
        try:
            data = json.loads(self._current_path.read_text(encoding="utf-8"))
            return ContinuityCheckpoint.from_dict(data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.debug("Failed to load checkpoint: %s", exc)
            return None

    def history(self, limit: int = 20) -> list[ContinuityCheckpoint]:
        """Load recent checkpoints from history."""
        if not self._history_path.exists():
            return []
        records: list[ContinuityCheckpoint] = []
        try:
            with open(self._history_path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        records.append(ContinuityCheckpoint.from_dict(json.loads(stripped)))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.debug("Failed to load checkpoint history: %s", exc)
        return records[-limit:]

    def _persist(self, checkpoint: ContinuityCheckpoint) -> None:
        data = checkpoint.to_dict()
        self._current_path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8",
        )
        with open(self._history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, separators=(",", ":"), default=str) + "\n")
