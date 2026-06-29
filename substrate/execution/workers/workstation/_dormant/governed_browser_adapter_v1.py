"""Governed Browser Adapter v1.

Allowlist-based browser interaction adapter. Only explicitly approved
action types and navigation targets can execute.

Allowed:
  - inspect tabs, URLs, DOM summaries
  - open approved local/internal URLs
  - controlled navigation, scrolling
  - controlled screenshot capture
  - controlled document inspection

BLOCKED unconditionally:
  - login/auth form submission
  - payment/checkout flows
  - account mutation (settings, profile, password)
  - external posting (social media, forums, email send)
  - unrestricted/hidden browsing
  - autonomous browsing loops
  - OAuth/SSO callbacks
  - file download/upload

UMH substrate subsystem.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .browser_gui_contracts_v1 import (
    BrowserActionType,
    BrowserActionVerdict,
    BrowserExecutionOutcome,
    BrowserExecutionRequest,
    BrowserExecutionResult,
    BrowserOperationalMode,
    _new_id,
    _now_iso,
)
from .browser_operational_modes_v1 import (
    get_browser_mode_definition,
)


# ---------------------------------------------------------------------------
# Structural blocklist — these URLs NEVER navigate regardless of mode
# ---------------------------------------------------------------------------

BLOCKED_URL_PATTERNS: frozenset[str] = frozenset(
    {
        "/login",
        "/signin",
        "/sign-in",
        "/sign_in",
        "/auth",
        "/oauth",
        "/sso",
        "/callback",
        "/authorize",
        "/token",
        "/checkout",
        "/payment",
        "/pay",
        "/billing",
        "/purchase",
        "/subscribe",
        "/settings",
        "/account",
        "/profile/edit",
        "/password",
        "/reset-password",
        "/change-password",
        "/delete-account",
        "/deactivate",
        "/compose",
        "/new-post",
        "/create-post",
        "/send-message",
        "/upload",
        "/download",
        "/export",
        "/admin",
        "/dashboard/admin",
    }
)

BLOCKED_DOMAINS: frozenset[str] = frozenset(
    {
        "accounts.google.com",
        "login.microsoftonline.com",
        "auth0.com",
        "login.live.com",
        "appleid.apple.com",
        "paypal.com",
        "stripe.com",
        "venmo.com",
        "cashapp.com",
    }
)


@dataclass
class BrowserGovernanceDecision:
    """Record of a browser action governance decision."""

    decision_id: str = ""
    action_type: str = ""
    target_url: str = ""
    verdict: BrowserActionVerdict = BrowserActionVerdict.DENIED
    risk_class: str = "safe"
    denial_reason: str = ""
    rules_applied: list[str] = field(default_factory=list)
    operational_mode: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.decision_id:
            self.decision_id = _new_id("bgdec")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "action_type": self.action_type,
            "target_url": self.target_url,
            "verdict": self.verdict.value,
            "risk_class": self.risk_class,
            "denial_reason": self.denial_reason,
            "rules_applied": self.rules_applied,
            "operational_mode": self.operational_mode,
            "timestamp": self.timestamp,
        }


class GovernedBrowserAdapter:
    """Allowlist-based governed browser interaction."""

    def __init__(
        self,
        operational_mode: BrowserOperationalMode = BrowserOperationalMode.INSPECTION,
    ) -> None:
        self._mode = operational_mode
        self._mode_def = get_browser_mode_definition(operational_mode)
        self._decisions: list[BrowserGovernanceDecision] = []

    @property
    def mode(self) -> BrowserOperationalMode:
        return self._mode

    def set_mode(self, mode: BrowserOperationalMode) -> None:
        self._mode = mode
        self._mode_def = get_browser_mode_definition(mode)

    def evaluate_action(self, request: BrowserExecutionRequest) -> BrowserGovernanceDecision:
        """Evaluate whether a browser action is approved for execution."""
        rules: list[str] = []
        url = request.target_url.strip()

        # Rule 1: Blocked domain check
        if url and self._is_blocked_domain(url):
            rules.append("BLOCKED_DOMAIN")
            return self._make_decision(
                request,
                BrowserActionVerdict.DENIED,
                f"Domain is structurally blocked",
                rules,
                "forbidden",
            )

        # Rule 2: Blocked URL pattern check
        if url and self._has_blocked_pattern(url):
            rules.append("BLOCKED_URL_PATTERN")
            return self._make_decision(
                request,
                BrowserActionVerdict.DENIED,
                f"URL pattern is structurally blocked",
                rules,
                "forbidden",
            )

        # Rule 3: Action type allowed in mode
        if not self._mode_def.allows_action(request.action_type):
            rules.append("MODE_ACTION_DENIED")
            return self._make_decision(
                request,
                BrowserActionVerdict.DENIED,
                f"Action '{request.action_type.value}' not allowed in {self._mode.value}",
                rules,
                "medium",
            )

        # Rule 4: Navigation scope check (for navigate actions)
        if request.action_type == BrowserActionType.NAVIGATE:
            if not url:
                rules.append("NAVIGATE_NO_URL")
                return self._make_decision(
                    request,
                    BrowserActionVerdict.DENIED,
                    "Navigation requires a target URL",
                    rules,
                    "medium",
                )
            if not self._mode_def.allows_navigation_to(url):
                rules.append("NAVIGATION_SCOPE_DENIED")
                return self._make_decision(
                    request,
                    BrowserActionVerdict.DENIED,
                    f"URL not within {self._mode_def.navigation_scope.value} scope",
                    rules,
                    "medium",
                )

        # Rule 5: Determine risk
        risk = self._classify_risk(request)
        rules.append("BROWSER_ALLOWLIST_APPROVED")
        return self._make_decision(
            request,
            BrowserActionVerdict.APPROVED,
            "",
            rules,
            risk,
        )

    # ── §14.1 Adapter Contract ──────────────────────────────────────────────

    def translate_request(self, request: BrowserExecutionRequest) -> BrowserExecutionRequest:
        """§14.1 translate_request: input is already typed. Returns as-is."""
        return request

    def validate_operation(self, request: BrowserExecutionRequest) -> BrowserGovernanceDecision:
        """§14.1 validate_operation: governance check for the browser action."""
        return self.evaluate_action(request)

    def normalize_result(
        self,
        raw_result: BrowserExecutionResult,
        decision: BrowserGovernanceDecision,
        duration_ms: float,
    ) -> BrowserExecutionResult:
        """§14.1 normalize_result: attach governance verdict and timing."""
        raw_result.duration_ms = duration_ms
        raw_result.governance_verdict = decision.verdict.value
        return raw_result

    def observe_state(self) -> dict[str, Any]:
        """§14.1 observe_state: current adapter state for tracing."""
        return {
            "adapter_id": "governed_browser",
            "operational_mode": self._mode.value,
            "healthy": True,
            **self.get_stats(),
        }

    # ── execute (backward-compatible orchestrator) ────────────────────────

    def execute(self, request: BrowserExecutionRequest) -> BrowserExecutionResult:
        """Execute a governed browser action. Orchestrates §14.1 phases."""
        canonical_request = self.translate_request(request)
        decision = self.validate_operation(canonical_request)

        if decision.verdict != BrowserActionVerdict.APPROVED:
            return BrowserExecutionResult(
                request_id=canonical_request.request_id,
                action_type=canonical_request.action_type,
                outcome=BrowserExecutionOutcome.DENIED,
                adapter_used="governed_browser",
                governance_verdict=decision.verdict.value,
                error_message=decision.denial_reason,
                correlation_id=canonical_request.correlation_id,
            )

        start = time.monotonic()
        raw_result = self._execute_action(canonical_request)
        duration_ms = (time.monotonic() - start) * 1000
        return self.normalize_result(raw_result, decision, duration_ms)

    def get_decisions(self) -> list[BrowserGovernanceDecision]:
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

    def _execute_action(self, request: BrowserExecutionRequest) -> BrowserExecutionResult:
        """Execute browser action. Returns result based on action type.

        In a headless VPS environment, most browser actions return
        structural results (state inspection) rather than live browser
        interaction. Live browser interaction requires a display server.
        """
        if request.action_type == BrowserActionType.INSPECT_TABS:
            return BrowserExecutionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                outcome=BrowserExecutionOutcome.SUCCESS,
                adapter_used="governed_browser",
                result_data={"action": "inspect_tabs", "note": "tab inspection executed"},
                correlation_id=request.correlation_id,
            )

        if request.action_type == BrowserActionType.INSPECT_URL:
            return BrowserExecutionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                outcome=BrowserExecutionOutcome.SUCCESS,
                adapter_used="governed_browser",
                url_after=request.target_url,
                result_data={"action": "inspect_url", "url": request.target_url},
                correlation_id=request.correlation_id,
            )

        if request.action_type == BrowserActionType.INSPECT_DOM:
            return BrowserExecutionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                outcome=BrowserExecutionOutcome.SUCCESS,
                adapter_used="governed_browser",
                dom_summary="DOM inspection executed",
                result_data={"action": "inspect_dom", "selector": request.target_selector},
                correlation_id=request.correlation_id,
            )

        if request.action_type == BrowserActionType.SCREENSHOT:
            return BrowserExecutionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                outcome=BrowserExecutionOutcome.SUCCESS,
                adapter_used="governed_browser",
                screenshot_path=request.screenshot_path or "",
                result_data={"action": "screenshot"},
                correlation_id=request.correlation_id,
            )

        if request.action_type == BrowserActionType.NAVIGATE:
            return BrowserExecutionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                outcome=BrowserExecutionOutcome.SUCCESS,
                adapter_used="governed_browser",
                url_before="",
                url_after=request.target_url,
                result_data={"action": "navigate", "url": request.target_url},
                correlation_id=request.correlation_id,
            )

        if request.action_type == BrowserActionType.SCROLL:
            return BrowserExecutionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                outcome=BrowserExecutionOutcome.SUCCESS,
                adapter_used="governed_browser",
                result_data={"action": "scroll", "direction": request.scroll_direction},
                correlation_id=request.correlation_id,
            )

        if request.action_type == BrowserActionType.DOCUMENT_INSPECT:
            return BrowserExecutionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                outcome=BrowserExecutionOutcome.SUCCESS,
                adapter_used="governed_browser",
                result_data={"action": "document_inspect"},
                correlation_id=request.correlation_id,
            )

        if request.action_type in (
            BrowserActionType.WINDOW_INSPECT,
            BrowserActionType.WINDOW_FOCUS,
            BrowserActionType.UI_STATE_INSPECT,
        ):
            return BrowserExecutionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                outcome=BrowserExecutionOutcome.SUCCESS,
                adapter_used="governed_browser",
                result_data={"action": request.action_type.value},
                correlation_id=request.correlation_id,
            )

        return BrowserExecutionResult(
            request_id=request.request_id,
            action_type=request.action_type,
            outcome=BrowserExecutionOutcome.NOT_AVAILABLE,
            adapter_used="governed_browser",
            error_message=f"Unrecognized action type: {request.action_type.value}",
            correlation_id=request.correlation_id,
        )

    def _is_blocked_domain(self, url: str) -> bool:
        for domain in BLOCKED_DOMAINS:
            if domain in url:
                return True
        return False

    def _has_blocked_pattern(self, url: str) -> bool:
        url_lower = url.lower()
        for pattern in BLOCKED_URL_PATTERNS:
            if pattern in url_lower:
                return True
        return False

    def _classify_risk(self, request: BrowserExecutionRequest) -> str:
        if request.action_type in (
            BrowserActionType.INSPECT_TABS,
            BrowserActionType.INSPECT_URL,
            BrowserActionType.INSPECT_DOM,
            BrowserActionType.WINDOW_INSPECT,
            BrowserActionType.UI_STATE_INSPECT,
        ):
            return "safe"
        if request.action_type == BrowserActionType.SCREENSHOT:
            return "safe"
        if request.action_type in (
            BrowserActionType.NAVIGATE,
            BrowserActionType.SCROLL,
            BrowserActionType.WINDOW_FOCUS,
        ):
            return "low"
        if request.action_type == BrowserActionType.DOCUMENT_INSPECT:
            return "safe"
        return "medium"

    def _make_decision(
        self,
        request: BrowserExecutionRequest,
        verdict: BrowserActionVerdict,
        denial_reason: str,
        rules: list[str],
        risk: str,
    ) -> BrowserGovernanceDecision:
        decision = BrowserGovernanceDecision(
            action_type=request.action_type.value,
            target_url=request.target_url,
            verdict=verdict,
            risk_class=risk,
            denial_reason=denial_reason,
            rules_applied=rules,
            operational_mode=self._mode.value,
        )
        self._decisions.append(decision)
        return decision
