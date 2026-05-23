"""Workstation Continuity Bridge v1.

Bridges workstation operational state into the substrate continuity
pipeline. Feeds execution events, governance decisions, state
transitions, and session lineage into SubstrateContinuityEngine.

Responsibilities:
  - Convert workstation execution results into continuity events
  - Feed governance decisions (approvals/denials) as continuity traces
  - Track workstation state transitions (mode changes, connectivity)
  - Generate workstation continuity snapshots for session resumption
  - Maintain execution lineage across workstation sessions

Persist to: data/runtime/workstation_continuity/

UMH substrate subsystem. Phase 96.8BP.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .workstation_contracts_v1 import (
    OperationalMode,
    WorkstationContinuityState,
    WorkstationExecutionResult,
    WorkstationResumeState,
    WorkstationState,
    _new_id,
    _now_iso,
)


class WorkstationContinuityBridge:
    """Bridges workstation state into the substrate continuity pipeline."""

    def __init__(
        self,
        continuity_dir: str | Path = "data/runtime/workstation_continuity",
    ) -> None:
        self._dir = Path(continuity_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self._dir / "workstation_events.jsonl"
        self._lineage_path = self._dir / "execution_lineage.jsonl"
        self._snapshot_path = self._dir / "continuity_snapshot.json"
        self._resume_path = self._dir / "resume_state.json"

        self._session_id = ""
        self._events_bridged = 0
        self._executions_tracked = 0
        self._mode_transitions = 0
        self._current_mode = OperationalMode.DEVELOPER
        self._recent_commands: list[str] = []
        self._open_loops: list[str] = []
        self._total_successes = 0
        self._total_denials = 0
        self._last_command = ""
        self._last_outcome = ""

    def start_session(self, session_id: str = "") -> str:
        """Begin a new continuity session."""
        self._session_id = session_id or _new_id("wcsess")
        self._events_bridged = 0
        self._executions_tracked = 0
        self._mode_transitions = 0
        self._recent_commands = []
        self._open_loops = []
        self._total_successes = 0
        self._total_denials = 0
        self._last_command = ""
        self._last_outcome = ""

        self._persist_event(
            {
                "event_type": "session_started",
                "session_id": self._session_id,
                "operational_mode": self._current_mode.value,
                "timestamp": _now_iso(),
            }
        )

        return self._session_id

    def bridge_execution(
        self,
        result: WorkstationExecutionResult,
        governance_rules: list[str] | None = None,
    ) -> dict[str, Any]:
        """Bridge a workstation execution result into continuity."""
        self._executions_tracked += 1
        self._last_command = result.command
        self._last_outcome = result.outcome.value

        if len(self._recent_commands) >= 50:
            self._recent_commands = self._recent_commands[-49:]
        self._recent_commands.append(result.command)

        if result.succeeded:
            self._total_successes += 1
        elif result.outcome.value == "denied":
            self._total_denials += 1

        lineage_record = {
            "lineage_id": _new_id("wlin"),
            "session_id": self._session_id,
            "result_id": result.result_id,
            "command": result.command,
            "outcome": result.outcome.value,
            "adapter_used": result.adapter_used,
            "governance_verdict": result.governance_verdict,
            "governance_rules": governance_rules or [],
            "duration_ms": result.duration_ms,
            "exit_code": result.exit_code,
            "error_message": result.error_message,
            "correlation_id": result.correlation_id,
            "timestamp": _now_iso(),
        }
        self._persist_lineage(lineage_record)

        event = {
            "event_type": "workstation_execution",
            "session_id": self._session_id,
            "command": result.command,
            "outcome": result.outcome.value,
            "adapter_used": result.adapter_used,
            "governance_verdict": result.governance_verdict,
            "timestamp": _now_iso(),
        }
        self._persist_event(event)
        self._events_bridged += 1

        if not result.succeeded and result.outcome.value != "denied":
            self._open_loops.append(
                f"Failed: {result.command} ({result.error_message or 'unknown error'})"
            )

        return lineage_record

    def bridge_governance_decision(
        self,
        command: str,
        verdict: str,
        rules_applied: list[str],
        risk_class: str = "safe",
        denial_reason: str = "",
    ) -> dict[str, Any]:
        """Bridge a governance decision into continuity."""
        event = {
            "event_type": "governance_decision",
            "session_id": self._session_id,
            "command": command,
            "verdict": verdict,
            "rules_applied": rules_applied,
            "risk_class": risk_class,
            "denial_reason": denial_reason,
            "timestamp": _now_iso(),
        }
        self._persist_event(event)
        self._events_bridged += 1
        return event

    def bridge_mode_transition(
        self,
        old_mode: OperationalMode,
        new_mode: OperationalMode,
        reason: str = "",
    ) -> dict[str, Any]:
        """Bridge a mode transition into continuity."""
        self._mode_transitions += 1
        self._current_mode = new_mode

        event = {
            "event_type": "mode_transition",
            "session_id": self._session_id,
            "old_mode": old_mode.value,
            "new_mode": new_mode.value,
            "reason": reason,
            "timestamp": _now_iso(),
        }
        self._persist_event(event)
        self._events_bridged += 1
        return event

    def bridge_state_change(
        self,
        state: WorkstationState,
        change_type: str = "state_capture",
    ) -> dict[str, Any]:
        """Bridge a workstation state change into continuity."""
        event = {
            "event_type": change_type,
            "session_id": self._session_id,
            "state_id": state.state_id,
            "hostname": state.hostname,
            "operational_mode": state.operational_mode.value,
            "connectivity": state.connectivity.value,
            "tmux_sessions": len(state.active_tmux_sessions),
            "services": len(state.active_services),
            "content_hash": state.content_hash(),
            "timestamp": _now_iso(),
        }
        self._persist_event(event)
        self._events_bridged += 1
        return event

    def resolve_open_loop(self, loop_description: str) -> None:
        """Mark an open loop as resolved."""
        self._open_loops = [l for l in self._open_loops if l != loop_description]

    def take_snapshot(
        self,
        workstation_state: WorkstationState | None = None,
    ) -> WorkstationContinuityState:
        """Take a continuity state snapshot."""
        snapshot = WorkstationContinuityState(
            workstation_state=workstation_state,
            recent_executions=list(self._recent_commands[-20:]),
            open_loops=list(self._open_loops),
            operational_mode=self._current_mode,
            total_executions=self._executions_tracked,
            total_successes=self._total_successes,
            total_denials=self._total_denials,
        )

        self._snapshot_path.write_text(
            json.dumps(snapshot.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

        return snapshot

    def generate_resume_state(
        self,
        workstation_state: WorkstationState | None = None,
        active_goals: list[str] | None = None,
        suggested_next_actions: list[str] | None = None,
    ) -> WorkstationResumeState:
        """Generate a resume state for session continuation."""
        continuity = self.take_snapshot(workstation_state)

        resume = WorkstationResumeState(
            session_id=self._session_id,
            continuity_state=continuity,
            active_goals=active_goals or [],
            suggested_next_actions=suggested_next_actions or [],
            last_command=self._last_command,
            last_outcome=self._last_outcome,
        )

        self._resume_path.write_text(
            json.dumps(resume.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

        return resume

    def load_resume_state(self) -> WorkstationResumeState | None:
        """Load the most recent resume state."""
        if not self._resume_path.exists():
            return None
        try:
            data = json.loads(self._resume_path.read_text(encoding="utf-8"))
            return WorkstationResumeState(
                resume_id=data.get("resume_id", ""),
                session_id=data.get("session_id", ""),
                active_goals=data.get("active_goals", []),
                suggested_next_actions=data.get("suggested_next_actions", []),
                last_command=data.get("last_command", ""),
                last_outcome=data.get("last_outcome", ""),
            )
        except (json.JSONDecodeError, ValueError):
            return None

    def get_execution_lineage(self, limit: int = 20) -> list[dict[str, Any]]:
        """Load recent execution lineage records."""
        if not self._lineage_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(self._lineage_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "events_bridged": self._events_bridged,
            "executions_tracked": self._executions_tracked,
            "mode_transitions": self._mode_transitions,
            "open_loops": len(self._open_loops),
            "total_successes": self._total_successes,
            "total_denials": self._total_denials,
            "current_mode": self._current_mode.value,
        }

    def _persist_event(self, event: dict[str, Any]) -> None:
        with open(self._events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

    def _persist_lineage(self, record: dict[str, Any]) -> None:
        with open(self._lineage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
