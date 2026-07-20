"""Return/resume brief generator — answers "what happened while I was gone?"

Reads checkpoint history, recent traces, pending approvals, active sessions,
and work packet state to produce a structured brief for the operator on return.

Phase 14.11B. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReturnBrief:
    """Structured return/resume brief for the operator."""

    generated_at: str = ""
    continuity_state_at_departure: str = ""
    continuity_state_now: str = ""
    lifecycle_mode: str = ""
    active_profile_modes: list[str] = field(default_factory=list)
    active_node: str = ""
    active_environment: str = ""

    what_happened: list[str] = field(default_factory=list)
    what_changed: list[str] = field(default_factory=list)
    what_finished: list[str] = field(default_factory=list)
    what_failed: list[str] = field(default_factory=list)
    what_is_blocked: list[str] = field(default_factory=list)
    needs_approval: list[dict[str, Any]] = field(default_factory=list)
    resume_next: str = ""
    running_agents: list[dict[str, Any]] = field(default_factory=list)
    running_sessions: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReturnBrief:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ReturnBriefGenerator:
    """Generates a return brief from available system state."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        if state_dir is None:
            root = os.environ.get("UMH_ROOT", "/opt/OS")
            state_dir = os.path.join(root, "data", "umh", "workstation_state")
        self._dir = Path(state_dir)

    def generate(
        self,
        departure_state: str = "",
        current_state: str = "active",
        lifecycle_mode: str = "day_cycle",
        active_profile_modes: list[str] | None = None,
        active_node: str = "",
        active_environment: str = "",
    ) -> ReturnBrief:
        """Generate a return brief from system state."""
        brief = ReturnBrief(
            continuity_state_at_departure=departure_state,
            continuity_state_now=current_state,
            lifecycle_mode=lifecycle_mode,
            active_profile_modes=active_profile_modes or ["developer"],
            active_node=active_node,
            active_environment=active_environment,
        )

        brief.what_happened = self._read_events_since_departure()
        brief.what_changed = self._read_changes()
        brief.what_finished = self._read_completed()
        brief.what_failed = self._read_failures()
        brief.what_is_blocked = self._read_blocked()
        brief.needs_approval = self._read_pending_approvals()
        brief.running_agents = self._read_running_agents()
        brief.running_sessions = self._read_running_sessions()
        brief.resume_next = self._derive_next_action(brief)

        self._persist(brief)
        return brief

    def latest(self) -> ReturnBrief | None:
        """Load the most recently generated brief."""
        path = self._dir / "latest_return_brief.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ReturnBrief.from_dict(data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.debug("Failed to load return brief: %s", exc)
            return None

    def _read_events_since_departure(self) -> list[str]:
        """Read organism events that occurred during absence."""
        events: list[str] = []
        path = self._dir.parent / "organism" / "events.jsonl"
        if not path.exists():
            return ["No event log available"]
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines[-20:]:
                stripped = line.strip()
                if stripped:
                    data = json.loads(stripped)
                    summary = data.get("event_type", "unknown")
                    source = data.get("source", "")
                    if source:
                        summary = f"{summary} (from {source})"
                    events.append(summary)
        except Exception as exc:
            logger.debug("Event read failed: %s", exc)
            events.append(f"Event read error: {type(exc).__name__}")
        return events or ["No events during absence"]

    def _read_changes(self) -> list[str]:
        """Read what changed during absence from checkpoint diff."""
        checkpoint_path = self._dir / "checkpoint_history.jsonl"
        if not checkpoint_path.exists():
            return ["No checkpoints recorded"]
        changes: list[str] = []
        try:
            with open(checkpoint_path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        data = json.loads(stripped)
                        prev = data.get("previous_continuity_state", "")
                        new = data.get("new_continuity_state", "")
                        reason = data.get("transition_reason", "")
                        changes.append(f"{prev} → {new}: {reason}")
        except Exception as exc:
            logger.debug("Changes read failed: %s", exc)
        return changes[-10:] or ["No state changes recorded"]

    def _read_completed(self) -> list[str]:
        """Read work packets that completed during absence."""
        from substrate.state.runtime_paths import runtime_state_path

        path = runtime_state_path("universal_work", "work_packets.jsonl", create_parent=False)
        if not path.exists():
            return []
        completed: list[str] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        data = json.loads(stripped)
                        if data.get("status") in ("completed", "delivered", "sealed"):
                            title = data.get("title", data.get("packet_id", "unknown"))
                            completed.append(title)
        except Exception as exc:
            logger.debug("Completed read failed: %s", exc)
        return completed[-10:]

    def _read_failures(self) -> list[str]:
        """Read work packets that failed during absence."""
        from substrate.state.runtime_paths import runtime_state_path

        path = runtime_state_path("universal_work", "work_packets.jsonl", create_parent=False)
        if not path.exists():
            return []
        failed: list[str] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        data = json.loads(stripped)
                        if data.get("status") == "failed":
                            title = data.get("title", data.get("packet_id", "unknown"))
                            failed.append(title)
        except Exception as exc:
            logger.debug("Failures read failed: %s", exc)
        return failed[-10:]

    def _read_blocked(self) -> list[str]:
        """Read work packets that are blocked."""
        from substrate.state.runtime_paths import runtime_state_path

        path = runtime_state_path("universal_work", "work_packets.jsonl", create_parent=False)
        if not path.exists():
            return []
        blocked: list[str] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        data = json.loads(stripped)
                        if data.get("status") in ("blocked", "paused"):
                            title = data.get("title", data.get("packet_id", "unknown"))
                            blocked.append(title)
        except Exception as exc:
            logger.debug("Blocked read failed: %s", exc)
        return blocked[-10:]

    def _read_pending_approvals(self) -> list[dict[str, Any]]:
        """Read pending approvals from governance."""
        path = self._dir.parent / "operator_acceptance" / "artifacts.jsonl"
        if not path.exists():
            return []
        pending: list[dict[str, Any]] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        data = json.loads(stripped)
                        if data.get("status") in ("pending", "awaiting_review"):
                            pending.append(
                                {
                                    "artifact_id": data.get("artifact_id", ""),
                                    "title": data.get("title", ""),
                                    "type": data.get("type", ""),
                                }
                            )
        except Exception as exc:
            logger.debug("Approvals read failed: %s", exc)
        return pending[-10:]

    def _read_running_agents(self) -> list[dict[str, Any]]:
        """Read currently running agent heartbeats."""
        agents: list[dict[str, Any]] = []
        heartbeat_dir = self._dir.parent / "organism" / "workcells"
        if not heartbeat_dir.exists():
            return []
        try:
            for hb_file in heartbeat_dir.glob("*/heartbeat.json"):
                data = json.loads(hb_file.read_text(encoding="utf-8"))
                agents.append(
                    {
                        "name": hb_file.parent.name,
                        "status": data.get("status", "unknown"),
                        "last_beat": data.get("timestamp", ""),
                    }
                )
        except Exception as exc:
            logger.debug("Agent heartbeat read failed: %s", exc)
        return agents

    def _read_running_sessions(self) -> list[dict[str, Any]]:
        """Read active runtime sessions."""
        path = self._dir.parent / "runtime_surface" / "sessions.jsonl"
        if not path.exists():
            return []
        sessions: list[dict[str, Any]] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        data = json.loads(stripped)
                        if data.get("status") in ("active", "running"):
                            sessions.append(
                                {
                                    "session_id": data.get("session_id", ""),
                                    "type": data.get("type", ""),
                                    "status": data.get("status", ""),
                                }
                            )
        except Exception as exc:
            logger.debug("Sessions read failed: %s", exc)
        return sessions[-10:]

    def _derive_next_action(self, brief: ReturnBrief) -> str:
        """Deterministically derive the recommended next action."""
        if brief.what_failed:
            return f"Review {len(brief.what_failed)} failed work packet(s)"
        if brief.needs_approval:
            return f"Review {len(brief.needs_approval)} pending approval(s)"
        if brief.what_is_blocked:
            return f"Unblock {len(brief.what_is_blocked)} blocked item(s)"
        if brief.what_finished:
            return f"Review {len(brief.what_finished)} completed item(s)"
        return "Ready for new work"

    def _persist(self, brief: ReturnBrief) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / "latest_return_brief.json"
        path.write_text(
            json.dumps(brief.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
