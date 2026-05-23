"""Browser Execution Orchestrator v1.

Coordinates browser/GUI execution through the governed pipeline:
  1. Receive browser execution request
  2. Evaluate governance (browser adapter)
  3. Route to adapter (browser or GUI)
  4. Capture result
  5. Record observability
  6. Bridge continuity
  7. Emit visible actuation events
  8. Preserve replay determinism

No browser/GUI adapter can be called directly outside this orchestrator.

UMH substrate subsystem.
"""

from __future__ import annotations

from typing import Any

from .browser_gui_contracts_v1 import (
    BrowserActionType,
    BrowserActionVerdict,
    BrowserExecutionOutcome,
    BrowserExecutionRequest,
    BrowserExecutionResult,
    BrowserOperationalMode,
    VisibleActuationEvent,
    _now_iso,
)
from .governed_browser_adapter_v1 import GovernedBrowserAdapter
from .visible_gui_adapter_v1 import VisibleGUIAdapter
from .browser_observability_pipeline_v1 import (
    BrowserObservabilityPipeline,
)
from .browser_continuity_bridge_v1 import BrowserContinuityBridge
from .browser_operational_modes_v1 import get_browser_mode_definition


class BrowserExecutionOrchestrator:
    """Coordinates governed browser/GUI execution through a single pipeline."""

    def __init__(
        self,
        operational_mode: BrowserOperationalMode = BrowserOperationalMode.INSPECTION,
        browser_adapter: GovernedBrowserAdapter | None = None,
        gui_adapter: VisibleGUIAdapter | None = None,
        observability: BrowserObservabilityPipeline | None = None,
        continuity: BrowserContinuityBridge | None = None,
    ) -> None:
        self._mode = operational_mode
        self._mode_def = get_browser_mode_definition(operational_mode)
        self._browser = browser_adapter or GovernedBrowserAdapter(operational_mode)
        self._gui = gui_adapter or VisibleGUIAdapter(operational_mode)
        self._observability = observability or BrowserObservabilityPipeline()
        self._continuity = continuity or BrowserContinuityBridge()

        self._total_executions = 0
        self._total_successes = 0
        self._total_denials = 0
        self._total_failures = 0

    def set_mode(self, mode: BrowserOperationalMode) -> None:
        """Change operational mode across all adapters."""
        old_mode = self._mode
        self._mode = mode
        self._mode_def = get_browser_mode_definition(mode)
        self._browser.set_mode(mode)
        self._gui.set_mode(mode)
        self._continuity.bridge_mode_transition(old_mode, mode)

    def execute(self, request: BrowserExecutionRequest) -> BrowserExecutionResult:
        """Execute a browser/GUI action through the governed pipeline."""
        self._total_executions += 1

        # Step 1: Governance evaluation
        decision = self._browser.evaluate_action(request)

        # Step 2: If denied, short-circuit
        if decision.verdict != BrowserActionVerdict.APPROVED:
            self._total_denials += 1
            result = BrowserExecutionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                outcome=BrowserExecutionOutcome.DENIED,
                adapter_used="none",
                governance_verdict=decision.verdict.value,
                error_message=decision.denial_reason,
                correlation_id=request.correlation_id,
            )
            self._record(request, result, decision.rules_applied)
            return result

        # Step 3: Route to adapter
        if (
            request.action_type
            in (
                BrowserActionType.WINDOW_INSPECT,
                BrowserActionType.WINDOW_FOCUS,
                BrowserActionType.UI_STATE_INSPECT,
            )
            and request.adapter_type == "gui"
        ):
            result = self._execute_gui(request)
        else:
            result = self._execute_browser(request)

        # Step 4: Update counters
        if result.succeeded:
            self._total_successes += 1
        else:
            self._total_failures += 1

        # Step 5: Record observability + continuity + actuation event
        self._record(request, result, decision.rules_applied)

        return result

    def execute_browser(
        self,
        action_type: BrowserActionType,
        target_url: str = "",
        **kwargs: Any,
    ) -> BrowserExecutionResult:
        """Convenience: execute a browser action."""
        request = BrowserExecutionRequest(
            action_type=action_type,
            target_url=target_url,
            adapter_type="browser",
            operational_mode=self._mode,
            **kwargs,
        )
        return self.execute(request)

    def execute_gui(
        self,
        action_type: BrowserActionType,
        **kwargs: Any,
    ) -> BrowserExecutionResult:
        """Convenience: execute a GUI action."""
        request = BrowserExecutionRequest(
            action_type=action_type,
            adapter_type="gui",
            operational_mode=self._mode,
            **kwargs,
        )
        return self.execute(request)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_executions": self._total_executions,
            "total_successes": self._total_successes,
            "total_denials": self._total_denials,
            "total_failures": self._total_failures,
            "success_rate": (
                self._total_successes / self._total_executions
                if self._total_executions > 0
                else 0.0
            ),
            "operational_mode": self._mode.value,
            "browser_stats": self._browser.get_stats(),
            "gui_stats": self._gui.get_stats(),
            "observability_stats": self._observability.get_stats(),
            "continuity_stats": self._continuity.get_stats(),
        }

    def _execute_browser(self, request: BrowserExecutionRequest) -> BrowserExecutionResult:
        """Execute through the governed browser adapter."""
        return self._browser.execute(request)

    def _execute_gui(self, request: BrowserExecutionRequest) -> BrowserExecutionResult:
        """Execute through the visible GUI adapter."""
        if request.action_type == BrowserActionType.WINDOW_INSPECT:
            return self._gui.inspect_windows()
        if request.action_type == BrowserActionType.WINDOW_FOCUS:
            return self._gui.focus_window(request.target_selector or "")
        if request.action_type == BrowserActionType.UI_STATE_INSPECT:
            return self._gui.inspect_ui_state()
        if request.action_type == BrowserActionType.SCREENSHOT:
            return self._gui.capture_screenshot(request.screenshot_path)
        return BrowserExecutionResult(
            request_id=request.request_id,
            action_type=request.action_type,
            outcome=BrowserExecutionOutcome.NOT_AVAILABLE,
            adapter_used="visible_gui",
            error_message=f"GUI adapter does not handle {request.action_type.value}",
            correlation_id=request.correlation_id,
        )

    def _record(
        self,
        request: BrowserExecutionRequest,
        result: BrowserExecutionResult,
        governance_rules: list[str] | None = None,
    ) -> None:
        """Record execution to observability and continuity."""
        self._observability.record_execution(request, result)
        self._continuity.bridge_execution(result, governance_rules)

        actuation_event = VisibleActuationEvent(
            action_type=request.action_type,
            target=request.target_selector or request.target_url,
            url=result.url_after or request.target_url,
            governance_verdict=result.governance_verdict,
            governance_rules=governance_rules or [],
            outcome=result.outcome.value,
            adapter_used=result.adapter_used,
            visibility_confirmed=result.succeeded,
            screenshot_path=result.screenshot_path,
            duration_ms=result.duration_ms,
            correlation_id=request.correlation_id,
        )
        self._observability.record_actuation_event(actuation_event)
        self._continuity.bridge_actuation_event(actuation_event)

        if result.governance_verdict:
            self._continuity.bridge_governance_decision(
                action_type=request.action_type.value,
                target_url=request.target_url,
                verdict=result.governance_verdict,
                rules_applied=governance_rules or [],
                risk_class=request.risk_class,
                denial_reason=result.error_message if not result.succeeded else "",
            )
