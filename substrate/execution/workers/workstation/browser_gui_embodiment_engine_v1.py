"""Browser and GUI Embodiment Engine v1.

Central orchestrator composing all browser/GUI operational modules:
  - browser/GUI contracts (data shapes)
  - browser operational modes (4 constrained modes)
  - governed browser adapter (allowlist browser interaction)
  - visible GUI adapter (governed GUI interaction)
  - browser execution orchestrator (pipeline coordination)
  - browser observability pipeline (telemetry)
  - browser replay validator (determinism verification)
  - browser continuity bridge (session lineage)

Provides:
  - Browser command dispatch (!browser-status, !browser-tabs, etc.)
  - Safe governed browser execution
  - Visible GUI interaction
  - Operational state reconstruction
  - Continuity snapshot
  - Replay validation

UMH substrate subsystem. Phase 96.8BQ.
"""

from __future__ import annotations

from typing import Any

from .browser_gui_contracts_v1 import (
    BrowserActionType,
    BrowserExecutionRequest,
    BrowserExecutionResult,
    BrowserOperationalMode,
    BrowserOperationalSnapshot,
    BrowserState,
    GUIState,
    _now_iso,
)
from .governed_browser_adapter_v1 import GovernedBrowserAdapter
from .visible_gui_adapter_v1 import VisibleGUIAdapter
from .browser_execution_orchestrator_v1 import (
    BrowserExecutionOrchestrator,
)
from .browser_observability_pipeline_v1 import (
    BrowserObservabilityPipeline,
)
from .browser_replay_validator_v1 import BrowserReplayValidator
from .browser_continuity_bridge_v1 import BrowserContinuityBridge
from .browser_operational_modes_v1 import (
    get_all_browser_modes,
    get_browser_mode_definition,
)


BROWSER_COMMANDS: dict[str, str] = {
    "browser-status": "Browser operational status and state",
    "browser-tabs": "Active browser tabs and sessions",
    "browser-inspect": "Inspect current page DOM summary",
    "browser-summary": "Browser session summary with metrics",
    "gui-state": "Current GUI/desktop state",
    "visible-actuation-log": "Recent visible actuation events",
}


class BrowserGUIEmbodimentEngine:
    """Central orchestrator for browser/GUI embodiment."""

    def __init__(
        self,
        operational_mode: BrowserOperationalMode = BrowserOperationalMode.INSPECTION,
    ) -> None:
        self._mode = operational_mode

        self._browser_adapter = GovernedBrowserAdapter(operational_mode)
        self._gui_adapter = VisibleGUIAdapter(operational_mode)
        self._observability = BrowserObservabilityPipeline()
        self._continuity = BrowserContinuityBridge()
        self._replay = BrowserReplayValidator(operational_mode)

        self._orchestrator = BrowserExecutionOrchestrator(
            operational_mode=operational_mode,
            browser_adapter=self._browser_adapter,
            gui_adapter=self._gui_adapter,
            observability=self._observability,
            continuity=self._continuity,
        )

        self._browser_state = BrowserState(operational_mode=operational_mode)
        self._gui_state = GUIState()
        self._session_id = ""
        self._initialized = False

    def initialize(self, session_id: str = "") -> dict[str, Any]:
        """Initialize the browser/GUI embodiment engine."""
        self._session_id = self._continuity.start_session(session_id)
        self._gui_state = self._gui_adapter.capture_gui_state()
        self._continuity.bridge_gui_state(self._gui_state)
        self._initialized = True

        return {
            "session_id": self._session_id,
            "operational_mode": self._mode.value,
            "display_available": self._gui_state.display_available,
            "browser_running": self._browser_state.is_running,
            "initialized_at": _now_iso(),
        }

    def set_mode(self, mode: BrowserOperationalMode) -> dict[str, Any]:
        """Change operational mode across all subsystems."""
        old_mode = self._mode
        self._mode = mode
        self._orchestrator.set_mode(mode)
        self._replay.set_mode(mode)
        self._browser_state.operational_mode = mode

        return {
            "old_mode": old_mode.value,
            "new_mode": mode.value,
            "timestamp": _now_iso(),
        }

    def execute(self, request: BrowserExecutionRequest) -> BrowserExecutionResult:
        """Execute through the governed pipeline."""
        return self._orchestrator.execute(request)

    def execute_browser(
        self,
        action_type: BrowserActionType,
        target_url: str = "",
        **kwargs: Any,
    ) -> BrowserExecutionResult:
        """Execute a governed browser action."""
        return self._orchestrator.execute_browser(action_type, target_url, **kwargs)

    def execute_gui(
        self,
        action_type: BrowserActionType,
        **kwargs: Any,
    ) -> BrowserExecutionResult:
        """Execute a governed GUI action."""
        return self._orchestrator.execute_gui(action_type, **kwargs)

    def dispatch_command(self, command_name: str) -> dict[str, Any]:
        """Dispatch a browser command by name."""
        handlers: dict[str, Any] = {
            "browser-status": self._cmd_browser_status,
            "browser-tabs": self._cmd_browser_tabs,
            "browser-inspect": self._cmd_browser_inspect,
            "browser-summary": self._cmd_browser_summary,
            "gui-state": self._cmd_gui_state,
            "visible-actuation-log": self._cmd_visible_actuation_log,
        }

        handler = handlers.get(command_name)
        if not handler:
            return {
                "error": f"Unknown browser command: {command_name}",
                "available_commands": list(BROWSER_COMMANDS.keys()),
            }

        return handler()

    def take_snapshot(self) -> BrowserOperationalSnapshot:
        """Take a complete browser/GUI operational snapshot."""
        recent_events_raw = self._observability.get_actuation_log(limit=10)
        return BrowserOperationalSnapshot(
            browser_state=self._browser_state,
            gui_state=self._gui_state,
            operational_mode=self._mode,
            total_actions=self._orchestrator._total_executions,
            total_denials=self._orchestrator._total_denials,
            phase="96.8BQ",
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "operational_mode": self._mode.value,
            "initialized": self._initialized,
            "orchestrator": self._orchestrator.get_stats(),
            "observability": self._observability.get_stats(),
            "continuity": self._continuity.get_stats(),
            "replay": self._replay.get_stats(),
        }

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def _cmd_browser_status(self) -> dict[str, Any]:
        mode_def = get_browser_mode_definition(self._mode)
        return {
            "command": "browser-status",
            "browser_state": self._browser_state.to_dict(),
            "operational_mode": mode_def.to_dict(),
            "stats": self._orchestrator.get_stats(),
            "timestamp": _now_iso(),
        }

    def _cmd_browser_tabs(self) -> dict[str, Any]:
        result = self.execute_browser(BrowserActionType.INSPECT_TABS)
        return {
            "command": "browser-tabs",
            "outcome": result.outcome.value,
            "tabs": result.result_data,
            "timestamp": _now_iso(),
        }

    def _cmd_browser_inspect(self) -> dict[str, Any]:
        result = self.execute_browser(BrowserActionType.INSPECT_DOM)
        return {
            "command": "browser-inspect",
            "outcome": result.outcome.value,
            "dom_summary": result.dom_summary,
            "result_data": result.result_data,
            "timestamp": _now_iso(),
        }

    def _cmd_browser_summary(self) -> dict[str, Any]:
        records = self._observability.get_recent_records(limit=20)
        denials = self._observability.get_denial_records(limit=10)
        return {
            "command": "browser-summary",
            "recent_executions": len(records),
            "recent_denials": len(denials),
            "stats": self._observability.get_stats(),
            "continuity": self._continuity.get_stats(),
            "timestamp": _now_iso(),
        }

    def _cmd_gui_state(self) -> dict[str, Any]:
        self._gui_state = self._gui_adapter.capture_gui_state()
        return {
            "command": "gui-state",
            "gui_state": self._gui_state.to_dict(),
            "timestamp": _now_iso(),
        }

    def _cmd_visible_actuation_log(self) -> dict[str, Any]:
        events = self._observability.get_actuation_log(limit=20)
        return {
            "command": "visible-actuation-log",
            "events": events,
            "total_events": len(events),
            "timestamp": _now_iso(),
        }
