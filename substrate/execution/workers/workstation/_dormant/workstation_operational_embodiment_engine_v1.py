"""Workstation Operational Embodiment Engine v1.

Central orchestrator composing all workstation operational modules:
  - workstation contracts (data shapes)
  - workstation state registry (live state capture)
  - governed shell adapter (allowlist shell execution)
  - tmux operational adapter (governed tmux interaction)
  - workstation execution orchestrator (pipeline coordination)
  - workstation observability pipeline (telemetry)
  - workstation replay validator (determinism verification)
  - workstation continuity bridge (session lineage)
  - operational mode system (4 constrained modes)

Provides:
  - Workstation command dispatch (!workstation-status, !tmux-status, etc.)
  - Safe embodied execution (governed shell + tmux)
  - Operational state reconstruction
  - Continuity snapshot and resume
  - Replay validation

UMH substrate subsystem.
"""

from __future__ import annotations

from typing import Any

from .workstation_contracts_v1 import (
    OperationalMode,
    WorkstationContinuityState,
    WorkstationExecutionRequest,
    WorkstationExecutionResult,
    WorkstationOperationalSnapshot,
    WorkstationResumeState,
    _now_iso,
)
from .workstation_state_registry_v1 import WorkstationStateRegistry
from .governed_shell_adapter_v1 import GovernedShellAdapter
from .tmux_operational_adapter_v1 import TmuxOperationalAdapter
from .workstation_execution_orchestrator_v1 import (
    WorkstationExecutionOrchestrator,
)
from .workstation_observability_pipeline_v1 import (
    WorkstationObservabilityPipeline,
)
from .workstation_replay_validator_v1 import (
    WorkstationReplayValidator,
)
from .workstation_continuity_bridge_v1 import (
    WorkstationContinuityBridge,
)
from .workstation_operational_modes_v1 import (
    get_all_modes,
    get_mode_definition,
)


WORKSTATION_COMMANDS: dict[str, str] = {
    "workstation-status": "Full workstation operational status",
    "tmux-status": "Active tmux sessions and panes",
    "runtime-sessions": "Running services and containers",
    "resume-work": "Generate resume state for session continuation",
    "operational-state": "Current operational mode and constraints",
    "environment-health": "Workstation environment health check",
    "replay-validate": "Replay recent executions for determinism",
    "execution-history": "Recent execution history with outcomes",
    "mode-info": "Operational mode details and constraints",
}


class WorkstationOperationalEmbodimentEngine:
    """Central orchestrator for workstation operational embodiment."""

    def __init__(
        self,
        operational_mode: OperationalMode = OperationalMode.DEVELOPER,
    ) -> None:
        self._mode = operational_mode

        self._state_registry = WorkstationStateRegistry()
        self._shell = GovernedShellAdapter(operational_mode)
        self._tmux = TmuxOperationalAdapter(operational_mode, self._shell)
        self._observability = WorkstationObservabilityPipeline()
        self._continuity = WorkstationContinuityBridge()
        self._replay = WorkstationReplayValidator(operational_mode)

        self._orchestrator = WorkstationExecutionOrchestrator(
            operational_mode=operational_mode,
            shell_adapter=self._shell,
            tmux_adapter=self._tmux,
            observability=self._observability,
            continuity=self._continuity,
        )

        self._session_id = ""
        self._initialized = False

    def initialize(self, session_id: str = "") -> dict[str, Any]:
        """Initialize the embodiment engine for a session."""
        self._session_id = self._continuity.start_session(session_id)
        state = self._state_registry.capture_state()
        self._continuity.bridge_state_change(state, "session_initialization")
        self._initialized = True

        return {
            "session_id": self._session_id,
            "operational_mode": self._mode.value,
            "hostname": state.hostname,
            "tmux_sessions": len(state.active_tmux_sessions),
            "services": len(state.active_services),
            "connectivity": state.connectivity.value,
            "initialized_at": _now_iso(),
        }

    def set_mode(self, mode: OperationalMode) -> dict[str, Any]:
        """Change operational mode across all subsystems."""
        old_mode = self._mode
        self._mode = mode
        self._orchestrator.set_mode(mode)
        self._replay.set_mode(mode)
        self._state_registry.set_mode(mode)

        return {
            "old_mode": old_mode.value,
            "new_mode": mode.value,
            "timestamp": _now_iso(),
        }

    def execute(self, request: WorkstationExecutionRequest) -> WorkstationExecutionResult:
        """Execute through the governed pipeline."""
        return self._orchestrator.execute(request)

    def execute_shell(self, command: str, **kwargs: Any) -> WorkstationExecutionResult:
        """Execute a governed shell command."""
        return self._orchestrator.execute_shell(command, **kwargs)

    def execute_tmux(
        self, command: str, session_name: str, **kwargs: Any
    ) -> WorkstationExecutionResult:
        """Execute a governed command in a tmux session."""
        return self._orchestrator.execute_tmux(command, session_name, **kwargs)

    def dispatch_command(self, command_name: str) -> dict[str, Any]:
        """Dispatch a workstation command by name."""
        handlers: dict[str, Any] = {
            "workstation-status": self._cmd_workstation_status,
            "tmux-status": self._cmd_tmux_status,
            "runtime-sessions": self._cmd_runtime_sessions,
            "resume-work": self._cmd_resume_work,
            "operational-state": self._cmd_operational_state,
            "environment-health": self._cmd_environment_health,
            "replay-validate": self._cmd_replay_validate,
            "execution-history": self._cmd_execution_history,
            "mode-info": self._cmd_mode_info,
        }

        handler = handlers.get(command_name)
        if not handler:
            return {
                "error": f"Unknown workstation command: {command_name}",
                "available_commands": list(WORKSTATION_COMMANDS.keys()),
            }

        return handler()

    def take_snapshot(self) -> WorkstationOperationalSnapshot:
        """Take a complete operational snapshot."""
        state = self._state_registry.capture_state()
        env = self._state_registry.capture_environment()
        sessions = self._tmux.list_sessions()
        continuity = self._continuity.take_snapshot(state)

        return WorkstationOperationalSnapshot(
            workstation_state=state,
            environment=env,
            sessions=sessions,
            continuity=continuity,
            operational_mode=self._mode,
            phase="96.8BP",
        )

    def generate_resume_state(
        self,
        active_goals: list[str] | None = None,
        suggested_next_actions: list[str] | None = None,
    ) -> WorkstationResumeState:
        """Generate resume state for session continuation."""
        state = self._state_registry.capture_state()
        return self._continuity.generate_resume_state(
            workstation_state=state,
            active_goals=active_goals,
            suggested_next_actions=suggested_next_actions,
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "operational_mode": self._mode.value,
            "initialized": self._initialized,
            "orchestrator": self._orchestrator.get_stats(),
            "state_registry": self._state_registry.get_stats(),
            "observability": self._observability.get_stats(),
            "continuity": self._continuity.get_stats(),
            "replay": self._replay.get_stats(),
        }

    # ------------------------------------------------------------------
    # Workstation command handlers
    # ------------------------------------------------------------------

    def _cmd_workstation_status(self) -> dict[str, Any]:
        state = self._state_registry.capture_state()
        env = self._state_registry.capture_environment()
        return {
            "command": "workstation-status",
            "state": state.to_dict(),
            "environment": env.to_dict(),
            "operational_mode": self._mode.value,
            "stats": self._orchestrator.get_stats(),
            "timestamp": _now_iso(),
        }

    def _cmd_tmux_status(self) -> dict[str, Any]:
        sessions = self._tmux.list_sessions()
        panes = self._tmux.list_panes()
        return {
            "command": "tmux-status",
            "sessions": [s.to_dict() for s in sessions],
            "all_panes": panes,
            "session_count": len(sessions),
            "timestamp": _now_iso(),
        }

    def _cmd_runtime_sessions(self) -> dict[str, Any]:
        state = self._state_registry.capture_state()
        return {
            "command": "runtime-sessions",
            "services": state.active_services,
            "tmux_sessions": state.active_tmux_sessions,
            "service_count": len(state.active_services),
            "tmux_count": len(state.active_tmux_sessions),
            "timestamp": _now_iso(),
        }

    def _cmd_resume_work(self) -> dict[str, Any]:
        resume = self.generate_resume_state()
        return {
            "command": "resume-work",
            "resume_state": resume.to_dict(),
            "timestamp": _now_iso(),
        }

    def _cmd_operational_state(self) -> dict[str, Any]:
        mode_def = get_mode_definition(self._mode)
        return {
            "command": "operational-state",
            "mode": mode_def.to_dict(),
            "session_id": self._session_id,
            "initialized": self._initialized,
            "timestamp": _now_iso(),
        }

    def _cmd_environment_health(self) -> dict[str, Any]:
        env = self._state_registry.capture_environment()
        state = self._state_registry.capture_state()
        return {
            "command": "environment-health",
            "hostname": env.hostname,
            "platform": env.platform,
            "python_version": env.python_version,
            "available_tools": env.available_tools,
            "docker_containers": env.docker_containers,
            "connectivity": env.connectivity.value,
            "environment_health": state.environment_health,
            "timestamp": _now_iso(),
        }

    def _cmd_replay_validate(self) -> dict[str, Any]:
        records = self._observability.get_recent_records(limit=20)
        if not records:
            return {
                "command": "replay-validate",
                "status": "no_records",
                "message": "No execution records to replay",
                "timestamp": _now_iso(),
            }
        session_result = self._replay.replay_session(records, self._session_id)
        return {
            "command": "replay-validate",
            "all_passed": session_result.all_passed,
            "total_records": session_result.total_records,
            "passed_records": session_result.passed_records,
            "total_checks": session_result.total_checks,
            "passed_checks": session_result.passed_checks,
            "timestamp": _now_iso(),
        }

    def _cmd_execution_history(self) -> dict[str, Any]:
        records = self._observability.get_recent_records(limit=20)
        denials = self._observability.get_denial_records(limit=10)
        return {
            "command": "execution-history",
            "recent_executions": records,
            "recent_denials": denials,
            "stats": self._observability.get_stats(),
            "timestamp": _now_iso(),
        }

    def _cmd_mode_info(self) -> dict[str, Any]:
        all_modes = get_all_modes()
        return {
            "command": "mode-info",
            "current_mode": self._mode.value,
            "available_modes": [m.to_dict() for m in all_modes],
            "timestamp": _now_iso(),
        }
