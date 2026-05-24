"""Workstation continuity — session tracking and resume state.

Wraps the substrate WorkstationContinuityBridge for the umh CLI package.
Tracks executions, mode transitions, governance decisions, and state
changes across the interaction loop. Generates resume states for
session continuation ("Welcome back. Here's what happened.").

UMH workstation subsystem.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONTINUITY_DIR = Path("data/runtime/workstation_continuity")


def _get_bridge() -> Any:
    """Lazy-load the substrate continuity bridge."""
    try:
        from substrate.execution.workers.workstation.workstation_continuity_bridge_v1 import (
            WorkstationContinuityBridge,
        )

        return WorkstationContinuityBridge(continuity_dir=str(_CONTINUITY_DIR))
    except ImportError:
        logger.debug("WorkstationContinuityBridge not available")
        return None


class SessionContinuity:
    """Session-level continuity tracking for the workstation.

    Wraps the substrate bridge and adds convenience methods for the
    interaction loop. If the substrate bridge is unavailable, all
    methods degrade gracefully (log and return empty results).
    """

    def __init__(self, session_id: str = "") -> None:
        self._bridge = _get_bridge()
        self._session_id = session_id
        self._started = False
        self._execution_count = 0
        self._mode_transitions = 0

    def start(self, session_id: str = "") -> str:
        """Start continuity tracking for this session."""
        if self._bridge is None:
            self._session_id = session_id or "no-bridge"
            return self._session_id

        sid = self._bridge.start_session(session_id)
        self._session_id = sid
        self._started = True
        return sid

    def track_execution(
        self,
        command: str,
        outcome: str = "success",
        adapter_used: str = "gateway",
        duration_ms: float = 0.0,
        error_message: str = "",
    ) -> dict[str, Any]:
        """Track an execution through the continuity bridge."""
        self._execution_count += 1

        if self._bridge is None:
            return {"command": command, "outcome": outcome}

        try:
            from substrate.execution.workers.workstation.workstation_contracts_v1 import (
                WorkstationExecutionOutcome,
                WorkstationExecutionResult,
            )

            outcome_enum = WorkstationExecutionOutcome.SUCCESS
            for member in WorkstationExecutionOutcome:
                if member.value == outcome:
                    outcome_enum = member
                    break

            result = WorkstationExecutionResult(
                command=command,
                outcome=outcome_enum,
                adapter_used=adapter_used,
                duration_ms=duration_ms,
                error_message=error_message,
            )
            return self._bridge.bridge_execution(result)
        except Exception as exc:
            logger.debug("Continuity tracking failed: %s", exc)
            return {"command": command, "outcome": outcome}

    def track_mode_transition(
        self,
        old_mode: str,
        new_mode: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Track a mode transition through the continuity bridge."""
        self._mode_transitions += 1

        if self._bridge is None:
            return {"old_mode": old_mode, "new_mode": new_mode}

        try:
            from substrate.execution.workers.workstation.workstation_contracts_v1 import (
                OperationalMode,
            )

            old_enum = OperationalMode.DEVELOPER
            new_enum = OperationalMode.DEVELOPER
            for member in OperationalMode:
                if member.value == old_mode:
                    old_enum = member
                if member.value == new_mode:
                    new_enum = member

            return self._bridge.bridge_mode_transition(old_enum, new_enum, reason)
        except Exception as exc:
            logger.debug("Mode transition tracking failed: %s", exc)
            return {"old_mode": old_mode, "new_mode": new_mode}

    def track_governance_decision(
        self,
        command: str,
        verdict: str,
        rules: list[str] | None = None,
        risk_class: str = "safe",
        denial_reason: str = "",
    ) -> dict[str, Any]:
        """Track a governance decision."""
        if self._bridge is None:
            return {"command": command, "verdict": verdict}

        try:
            return self._bridge.bridge_governance_decision(
                command, verdict, rules or [], risk_class, denial_reason
            )
        except Exception as exc:
            logger.debug("Governance decision tracking failed: %s", exc)
            return {"command": command, "verdict": verdict}

    def generate_resume(
        self,
        active_goals: list[str] | None = None,
        next_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a resume state for session continuation."""
        if self._bridge is None:
            return {
                "session_id": self._session_id,
                "executions": self._execution_count,
                "mode_transitions": self._mode_transitions,
            }

        try:
            resume = self._bridge.generate_resume_state(
                active_goals=active_goals,
                suggested_next_actions=next_actions,
            )
            return resume.to_dict()
        except Exception as exc:
            logger.debug("Resume generation failed: %s", exc)
            return {"session_id": self._session_id}

    def load_resume(self) -> dict[str, Any] | None:
        """Load the most recent resume state from disk."""
        resume_path = _CONTINUITY_DIR / "resume_state.json"
        if not resume_path.exists():
            return None
        try:
            return json.loads(resume_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def get_resume_summary(self) -> str:
        """Build a human-readable resume summary for the boot greeting."""
        resume = self.load_resume()
        if resume is None:
            return "No previous session to resume."

        parts: list[str] = []

        last_cmd = resume.get("last_command", "")
        last_outcome = resume.get("last_outcome", "")
        if last_cmd:
            parts.append(f"Last: {last_cmd} ({last_outcome})")

        goals = resume.get("active_goals", [])
        if goals:
            parts.append(f"Active goals: {', '.join(goals[:3])}")

        next_actions = resume.get("suggested_next_actions", [])
        if next_actions:
            parts.append(f"Suggested: {next_actions[0]}")

        continuity = resume.get("continuity_state", {})
        if continuity:
            total = continuity.get("total_executions", 0)
            successes = continuity.get("total_successes", 0)
            loops = continuity.get("open_loops", [])
            if total > 0:
                parts.append(f"{total} executions ({successes} succeeded)")
            if loops:
                parts.append(f"{len(loops)} open loops")

        return ". ".join(parts) if parts else "Clean resume — no pending items."

    def get_stats(self) -> dict[str, Any]:
        """Get current session statistics."""
        if self._bridge is not None:
            try:
                return self._bridge.get_stats()
            except Exception:
                pass

        return {
            "session_id": self._session_id,
            "executions": self._execution_count,
            "mode_transitions": self._mode_transitions,
        }

    def save_on_exit(self) -> None:
        """Save continuity state before session exit."""
        if self._bridge is None:
            return

        try:
            self._bridge.generate_resume_state()
            logger.info("Continuity state saved for session %s", self._session_id)
        except Exception as exc:
            logger.debug("Continuity save failed: %s", exc)


def show_continuity() -> int:
    """Display current continuity state for the CLI."""
    continuity = SessionContinuity()
    resume = continuity.load_resume()

    print()
    print("Session Continuity")
    print("=" * 40)

    if resume is None:
        print("  No previous session data.")
        print()
        return 0

    print(f"  Session:    {resume.get('session_id', 'unknown')}")
    print(f"  Last cmd:   {resume.get('last_command', 'none')}")
    print(f"  Outcome:    {resume.get('last_outcome', 'none')}")

    goals = resume.get("active_goals", [])
    if goals:
        print(f"  Goals:      {', '.join(goals[:5])}")

    next_actions = resume.get("suggested_next_actions", [])
    if next_actions:
        print(f"  Next:       {next_actions[0]}")

    continuity_state = resume.get("continuity_state", {})
    if continuity_state:
        print(f"  Executions: {continuity_state.get('total_executions', 0)}")
        print(f"  Successes:  {continuity_state.get('total_successes', 0)}")
        print(f"  Denials:    {continuity_state.get('total_denials', 0)}")
        loops = continuity_state.get("open_loops", [])
        if loops:
            print(f"  Open loops: {len(loops)}")
            for loop in loops[:5]:
                print(f"    - {loop}")

    print()
    return 0
