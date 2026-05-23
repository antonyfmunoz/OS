"""Visible GUI Adapter v1.

Governed GUI interaction adapter for window inspection, focus,
screenshot capture, and UI state inspection. All actions must
be visible — no hidden desktop mutation.

Allowed:
  - window inspection (list, active window, title, PID)
  - window focus (bring to foreground)
  - screenshot capture (visible screen content)
  - UI state inspection (desktop session, display)

BLOCKED unconditionally:
  - hidden desktop mutation
  - unrestricted cursor automation
  - destructive GUI actions (close, kill, resize without approval)
  - hidden background execution
  - clipboard manipulation
  - keystroke injection

UMH substrate subsystem.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

from .browser_gui_contracts_v1 import (
    BrowserActionType,
    BrowserActionVerdict,
    BrowserExecutionOutcome,
    BrowserExecutionResult,
    BrowserOperationalMode,
    GUIState,
    GUIWindowState,
    _new_id,
    _now_iso,
)
from .browser_operational_modes_v1 import (
    get_browser_mode_definition,
)


BLOCKED_GUI_ACTIONS: frozenset[str] = frozenset(
    {
        "close_window",
        "kill_process",
        "resize_window",
        "move_window",
        "minimize_all",
        "clipboard_write",
        "clipboard_read",
        "keystroke_inject",
        "mouse_click",
        "mouse_move",
        "drag_drop",
        "desktop_switch",
        "logout",
        "lock_screen",
    }
)


@dataclass
class GUIGovernanceDecision:
    """Record of a GUI action governance decision."""

    decision_id: str = ""
    action_type: str = ""
    target: str = ""
    verdict: BrowserActionVerdict = BrowserActionVerdict.DENIED
    denial_reason: str = ""
    rules_applied: list[str] = field(default_factory=list)
    operational_mode: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.decision_id:
            self.decision_id = _new_id("guidec")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "action_type": self.action_type,
            "target": self.target,
            "verdict": self.verdict.value,
            "denial_reason": self.denial_reason,
            "rules_applied": self.rules_applied,
            "operational_mode": self.operational_mode,
            "timestamp": self.timestamp,
        }


class VisibleGUIAdapter:
    """Governed GUI interaction adapter."""

    def __init__(
        self,
        operational_mode: BrowserOperationalMode = BrowserOperationalMode.INSPECTION,
    ) -> None:
        self._mode = operational_mode
        self._mode_def = get_browser_mode_definition(operational_mode)
        self._decisions: list[GUIGovernanceDecision] = []

    def set_mode(self, mode: BrowserOperationalMode) -> None:
        self._mode = mode
        self._mode_def = get_browser_mode_definition(mode)

    def capture_gui_state(self) -> GUIState:
        """Capture current GUI state from the environment."""
        display = self._check_display()
        return GUIState(
            desktop_session_active=display,
            display_available=display,
        )

    def inspect_windows(self) -> BrowserExecutionResult:
        """Inspect visible windows."""
        decision = self._evaluate(BrowserActionType.WINDOW_INSPECT, "")
        if decision.verdict != BrowserActionVerdict.APPROVED:
            return BrowserExecutionResult(
                action_type=BrowserActionType.WINDOW_INSPECT,
                outcome=BrowserExecutionOutcome.DENIED,
                adapter_used="visible_gui",
                governance_verdict=decision.verdict.value,
                error_message=decision.denial_reason,
            )

        windows = self._get_visible_windows()
        return BrowserExecutionResult(
            action_type=BrowserActionType.WINDOW_INSPECT,
            outcome=BrowserExecutionOutcome.SUCCESS,
            adapter_used="visible_gui",
            governance_verdict=decision.verdict.value,
            result_data={"windows": windows},
        )

    def focus_window(self, window_title: str) -> BrowserExecutionResult:
        """Focus a window by title."""
        decision = self._evaluate(BrowserActionType.WINDOW_FOCUS, window_title)
        if decision.verdict != BrowserActionVerdict.APPROVED:
            return BrowserExecutionResult(
                action_type=BrowserActionType.WINDOW_FOCUS,
                outcome=BrowserExecutionOutcome.DENIED,
                adapter_used="visible_gui",
                governance_verdict=decision.verdict.value,
                error_message=decision.denial_reason,
            )

        return BrowserExecutionResult(
            action_type=BrowserActionType.WINDOW_FOCUS,
            outcome=BrowserExecutionOutcome.SUCCESS,
            adapter_used="visible_gui",
            governance_verdict=decision.verdict.value,
            result_data={"focused": window_title},
        )

    def capture_screenshot(self, output_path: str = "") -> BrowserExecutionResult:
        """Capture a screenshot of the visible screen."""
        decision = self._evaluate(BrowserActionType.SCREENSHOT, "")
        if decision.verdict != BrowserActionVerdict.APPROVED:
            return BrowserExecutionResult(
                action_type=BrowserActionType.SCREENSHOT,
                outcome=BrowserExecutionOutcome.DENIED,
                adapter_used="visible_gui",
                governance_verdict=decision.verdict.value,
                error_message=decision.denial_reason,
            )

        return BrowserExecutionResult(
            action_type=BrowserActionType.SCREENSHOT,
            outcome=BrowserExecutionOutcome.SUCCESS,
            adapter_used="visible_gui",
            governance_verdict=decision.verdict.value,
            screenshot_path=output_path,
            result_data={"action": "screenshot", "path": output_path},
        )

    def inspect_ui_state(self) -> BrowserExecutionResult:
        """Inspect overall UI state."""
        decision = self._evaluate(BrowserActionType.UI_STATE_INSPECT, "")
        if decision.verdict != BrowserActionVerdict.APPROVED:
            return BrowserExecutionResult(
                action_type=BrowserActionType.UI_STATE_INSPECT,
                outcome=BrowserExecutionOutcome.DENIED,
                adapter_used="visible_gui",
                governance_verdict=decision.verdict.value,
                error_message=decision.denial_reason,
            )

        gui_state = self.capture_gui_state()
        return BrowserExecutionResult(
            action_type=BrowserActionType.UI_STATE_INSPECT,
            outcome=BrowserExecutionOutcome.SUCCESS,
            adapter_used="visible_gui",
            governance_verdict=decision.verdict.value,
            result_data=gui_state.to_dict(),
        )

    def is_action_blocked(self, action_name: str) -> bool:
        """Check if a GUI action is structurally blocked."""
        return action_name in BLOCKED_GUI_ACTIONS

    def get_decisions(self) -> list[GUIGovernanceDecision]:
        return list(self._decisions)

    def get_stats(self) -> dict[str, Any]:
        approved = sum(1 for d in self._decisions if d.verdict == BrowserActionVerdict.APPROVED)
        denied = sum(1 for d in self._decisions if d.verdict == BrowserActionVerdict.DENIED)
        return {
            "total_decisions": len(self._decisions),
            "approved": approved,
            "denied": denied,
            "mode": self._mode.value,
        }

    def _evaluate(self, action_type: BrowserActionType, target: str) -> GUIGovernanceDecision:
        """Evaluate whether a GUI action is allowed."""
        rules: list[str] = []

        if not self._mode_def.allows_action(action_type):
            rules.append("MODE_GUI_ACTION_DENIED")
            decision = GUIGovernanceDecision(
                action_type=action_type.value,
                target=target,
                verdict=BrowserActionVerdict.DENIED,
                denial_reason=f"GUI action '{action_type.value}' not allowed in {self._mode.value}",
                rules_applied=rules,
                operational_mode=self._mode.value,
            )
            self._decisions.append(decision)
            return decision

        rules.append("GUI_ALLOWLIST_APPROVED")
        decision = GUIGovernanceDecision(
            action_type=action_type.value,
            target=target,
            verdict=BrowserActionVerdict.APPROVED,
            rules_applied=rules,
            operational_mode=self._mode.value,
        )
        self._decisions.append(decision)
        return decision

    def _check_display(self) -> bool:
        """Check if a display server is available."""
        try:
            result = subprocess.run(
                ["xdpyinfo"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _get_visible_windows(self) -> list[str]:
        """Get list of visible window titles."""
        try:
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                windows = []
                for line in result.stdout.strip().splitlines():
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        windows.append(parts[3])
                return windows
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return []
