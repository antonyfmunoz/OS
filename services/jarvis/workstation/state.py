"""Workstation state — profile, session, and resume state.

Provides a lightweight runtime snapshot of the workstation:
who's running, what mode, what recent traces show, and what
to resume next. Complements (does not replace) runtime.session_state.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class WorkstationProfile:
    """Static-ish workstation identity and environment."""

    user_id: str = ""
    session_id: str = ""
    current_mode: str = "default"
    active_environment: str = ""
    hostname: str = ""
    platform: str = ""
    detected_at: str = ""

    def __post_init__(self) -> None:
        if not self.detected_at:
            self.detected_at = datetime.now(timezone.utc).isoformat()
        if not self.hostname:
            self.hostname = os.uname().nodename
        if not self.platform:
            self.platform = os.uname().sysname

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkstationProfile:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def detect(cls, user_id: str = "", session_id: str = "") -> WorkstationProfile:
        """Auto-detect workstation profile from environment."""
        env = os.environ.get("JARVIS_ENVIRONMENT", "")
        if not env:
            env = "vps" if os.path.exists("/opt/OS") else "local"
        mode = os.environ.get("JARVIS_MODE", "default")
        return cls(
            user_id=user_id,
            session_id=session_id,
            current_mode=mode,
            active_environment=env,
        )


@dataclass
class WorkstationSessionState:
    """Dynamic session state — what's happening right now."""

    recent_trace_ids: list[str] = field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    last_activity: str = ""
    last_activity_type: str = ""
    trace_count: int = 0
    candidate_count: int = 0
    error_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkstationSessionState:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def record_activity(self, trace_id: str, activity_type: str = "") -> None:
        """Record a new trace as recent activity."""
        self.recent_trace_ids.append(trace_id)
        if len(self.recent_trace_ids) > 20:
            self.recent_trace_ids = self.recent_trace_ids[-20:]
        self.last_activity = datetime.now(timezone.utc).isoformat()
        self.last_activity_type = activity_type
        self.trace_count += 1

    def record_error(self) -> None:
        self.error_count += 1


@dataclass
class ResumeState:
    """What to show when resuming a session."""

    resume_summary: str = ""
    next_suggested_actions: list[str] = field(default_factory=list)
    last_outcome: str = ""
    last_outcome_detail: str = ""
    unresolved_count: int = 0
    generated_at: str = ""

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResumeState:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WorkstationSnapshot:
    """Complete point-in-time workstation state."""

    profile: WorkstationProfile
    session: WorkstationSessionState
    resume: ResumeState
    snapshot_at: str = ""

    def __post_init__(self) -> None:
        if not self.snapshot_at:
            self.snapshot_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.to_dict(),
            "session": self.session.to_dict(),
            "resume": self.resume.to_dict(),
            "snapshot_at": self.snapshot_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkstationSnapshot:
        return cls(
            profile=WorkstationProfile.from_dict(data.get("profile", {})),
            session=WorkstationSessionState.from_dict(data.get("session", {})),
            resume=ResumeState.from_dict(data.get("resume", {})),
            snapshot_at=data.get("snapshot_at", ""),
        )


class WorkstationStateManager:
    """Manages workstation state persistence."""

    def __init__(self, state_dir: str | Path = "data/jarvis/workstation_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_path = self.state_dir / "current_snapshot.json"
        self.history_path = self.state_dir / "snapshot_history.jsonl"

    def save_snapshot(self, snapshot: WorkstationSnapshot) -> None:
        """Save the current snapshot (overwrites) and append to history."""
        data = snapshot.to_dict()
        self.snapshot_path.write_text(json.dumps(data, indent=2))
        with open(self.history_path, "a") as f:
            f.write(json.dumps(data, separators=(",", ":")) + "\n")

    def load_snapshot(self) -> WorkstationSnapshot | None:
        """Load the most recent snapshot."""
        if not self.snapshot_path.exists():
            return None
        return WorkstationSnapshot.from_dict(json.loads(self.snapshot_path.read_text()))

    def build_snapshot(
        self,
        profile: WorkstationProfile,
        session: WorkstationSessionState,
        recent_traces: list[dict[str, Any]] | None = None,
    ) -> WorkstationSnapshot:
        """Build a complete snapshot with auto-generated resume state."""
        recent = recent_traces or []

        last_outcome = ""
        last_outcome_detail = ""
        if recent:
            last_outcome = recent[0].get("outcome", "")
            last_outcome_detail = recent[0].get("input_signal_preview", "")

        pending_count = sum(1 for t in recent if t.get("status") in ("pending", "running"))

        summary_parts: list[str] = []
        if session.trace_count:
            summary_parts.append(f"{session.trace_count} traces executed")
        if session.error_count:
            summary_parts.append(f"{session.error_count} errors")
        if session.candidate_count:
            summary_parts.append(f"{session.candidate_count} memory candidates staged")
        if pending_count:
            summary_parts.append(f"{pending_count} traces still pending")

        resume_summary = ". ".join(summary_parts) if summary_parts else "No activity yet."

        actions: list[str] = []
        if session.error_count > 0:
            actions.append("Review recent errors")
        if pending_count > 0:
            actions.append("Check pending traces")
        if session.candidate_count > 0:
            actions.append("Review staged memory candidates for promotion")
        if not actions:
            actions.append("Ready for new work")

        resume = ResumeState(
            resume_summary=resume_summary,
            next_suggested_actions=actions,
            last_outcome=last_outcome,
            last_outcome_detail=last_outcome_detail,
            unresolved_count=pending_count + session.error_count,
        )

        snapshot = WorkstationSnapshot(
            profile=profile,
            session=session,
            resume=resume,
        )
        self.save_snapshot(snapshot)
        return snapshot
