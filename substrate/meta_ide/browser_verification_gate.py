"""Browser Verification Gate — blocking validation for UI-bearing work.

Determines whether browser verification is required for an engineering
session, validates collected evidence against the 4-layer × 3-pass
protocol, and produces structured proof data for EngineeringProofPackage.

The gate does NOT run browsers. Executing agents collect evidence via
Playwright/DevTools MCP tools. This gate validates that evidence meets
the verification contract before allowing session completion.

Deterministic classification. No LLM calls.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

RISK_PASS_COUNT: dict[str, int] = {
    "critical": 10,
    "high": 7,
    "medium": 5,
    "low": 3,
    "negligible": 3,
}
DEFAULT_PASS_COUNT = 3


def get_pass_count(risk_class: str) -> int:
    """Return required pass count based on risk classification."""
    return RISK_PASS_COUNT.get(risk_class.lower(), DEFAULT_PASS_COUNT)


_UI_FILE_EXTENSIONS = frozenset(
    {
        ".tsx",
        ".jsx",
        ".vue",
        ".svelte",
        ".html",
        ".css",
        ".scss",
        ".less",
    }
)

_UI_PATH_PATTERNS = (
    "components/",
    "panels/",
    "pages/",
    "views/",
    "renderer/",
    "frontend/",
    "client/",
    "ui/",
    "src/app/",
    "src/routes/",
)


@dataclass
class BrowserLayerResult:
    """Evidence from Playwright DOM snapshot."""

    elements_confirmed: list[str] = field(default_factory=list)
    snapshot_summary: str = ""
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "elements_confirmed": self.elements_confirmed,
            "snapshot_summary": self.snapshot_summary,
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrowserLayerResult:
        return cls(
            elements_confirmed=data.get("elements_confirmed", []),
            snapshot_summary=data.get("snapshot_summary", ""),
            passed=data.get("passed", False),
        )


@dataclass
class NetworkLayerResult:
    """Evidence from Chrome DevTools network inspection."""

    endpoints_checked: list[dict[str, Any]] = field(default_factory=list)
    error_count: int = 0
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoints_checked": self.endpoints_checked,
            "error_count": self.error_count,
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NetworkLayerResult:
        return cls(
            endpoints_checked=data.get("endpoints_checked", []),
            error_count=data.get("error_count", 0),
            passed=data.get("passed", False),
        )


@dataclass
class ConsoleLayerResult:
    """Evidence from Chrome DevTools console inspection."""

    app_error_count: int = 0
    app_errors: list[str] = field(default_factory=list)
    ignored_errors: int = 0
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_error_count": self.app_error_count,
            "app_errors": self.app_errors,
            "ignored_errors": self.ignored_errors,
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConsoleLayerResult:
        return cls(
            app_error_count=data.get("app_error_count", 0),
            app_errors=data.get("app_errors", []),
            ignored_errors=data.get("ignored_errors", 0),
            passed=data.get("passed", False),
        )


@dataclass
class LogCrossReference:
    """Single bidirectional cross-reference between network request and server log."""

    endpoint: str = ""
    http_method: str = ""
    network_status: int = 0
    network_timestamp: float = 0.0
    log_entry_found: bool = False
    log_status: int = 0
    log_clean: bool = False
    log_errors: list[str] = field(default_factory=list)
    status_match: bool = False
    latency_ms: float = 0.0
    direction: str = "network_to_log"

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "http_method": self.http_method,
            "network_status": self.network_status,
            "network_timestamp": self.network_timestamp,
            "log_entry_found": self.log_entry_found,
            "log_status": self.log_status,
            "log_clean": self.log_clean,
            "log_errors": self.log_errors,
            "status_match": self.status_match,
            "latency_ms": self.latency_ms,
            "direction": self.direction,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogCrossReference:
        return cls(
            endpoint=data.get("endpoint", ""),
            http_method=data.get("http_method", ""),
            network_status=data.get("network_status", 0),
            network_timestamp=data.get("network_timestamp", 0.0),
            log_entry_found=data.get("log_entry_found", False),
            log_status=data.get("log_status", 0),
            log_clean=data.get("log_clean", False),
            log_errors=data.get("log_errors", []),
            status_match=data.get("status_match", False),
            latency_ms=data.get("latency_ms", 0.0),
            direction=data.get("direction", "network_to_log"),
        )


@dataclass
class LogLayerResult:
    """Evidence from server log inspection with full reconciliation."""

    service_name: str = ""
    log_lines_checked: int = 0
    tracebacks_found: int = 0
    auth_failures: int = 0
    timeouts: int = 0
    passed: bool = False
    cross_references: list[LogCrossReference] = field(default_factory=list)
    unmatched_network_requests: int = 0
    unmatched_log_errors: int = 0
    orphan_server_errors: list[str] = field(default_factory=list)
    action_traces: list[dict[str, Any]] = field(default_factory=list)
    reconciliation_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_name": self.service_name,
            "log_lines_checked": self.log_lines_checked,
            "tracebacks_found": self.tracebacks_found,
            "auth_failures": self.auth_failures,
            "timeouts": self.timeouts,
            "passed": self.passed,
            "cross_references": [cr.to_dict() for cr in self.cross_references],
            "unmatched_network_requests": self.unmatched_network_requests,
            "unmatched_log_errors": self.unmatched_log_errors,
            "orphan_server_errors": self.orphan_server_errors,
            "action_traces": self.action_traces,
            "reconciliation_score": self.reconciliation_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogLayerResult:
        return cls(
            service_name=data.get("service_name", ""),
            log_lines_checked=data.get("log_lines_checked", 0),
            tracebacks_found=data.get("tracebacks_found", 0),
            auth_failures=data.get("auth_failures", 0),
            timeouts=data.get("timeouts", 0),
            passed=data.get("passed", False),
            cross_references=[
                LogCrossReference.from_dict(cr) for cr in data.get("cross_references", [])
            ],
            unmatched_network_requests=data.get("unmatched_network_requests", 0),
            unmatched_log_errors=data.get("unmatched_log_errors", 0),
            orphan_server_errors=data.get("orphan_server_errors", []),
            action_traces=data.get("action_traces", []),
            reconciliation_score=data.get("reconciliation_score", 0.0),
        )


@dataclass
class VerificationPass:
    """Single pass of the 4-layer verification protocol."""

    pass_number: int = 0
    browser_check: BrowserLayerResult = field(default_factory=BrowserLayerResult)
    network_check: NetworkLayerResult = field(default_factory=NetworkLayerResult)
    console_check: ConsoleLayerResult = field(default_factory=ConsoleLayerResult)
    log_check: LogLayerResult = field(default_factory=LogLayerResult)
    timestamp: float = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        return all(
            [
                self.browser_check.passed,
                self.network_check.passed,
                self.console_check.passed,
                self.log_check.passed,
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_number": self.pass_number,
            "browser_check": self.browser_check.to_dict(),
            "network_check": self.network_check.to_dict(),
            "console_check": self.console_check.to_dict(),
            "log_check": self.log_check.to_dict(),
            "passed": self.passed,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationPass:
        return cls(
            pass_number=data.get("pass_number", 0),
            browser_check=BrowserLayerResult.from_dict(data.get("browser_check", {})),
            network_check=NetworkLayerResult.from_dict(data.get("network_check", {})),
            console_check=ConsoleLayerResult.from_dict(data.get("console_check", {})),
            log_check=LogLayerResult.from_dict(data.get("log_check", {})),
            timestamp=data.get("timestamp", 0.0),
        )


@dataclass
class BrowserVerificationResult:
    """Complete result of the risk-scaled verification protocol."""

    required: bool = False
    requirement_reasons: list[str] = field(default_factory=list)
    passes: list[VerificationPass] = field(default_factory=list)
    verified_at: float = 0.0
    required_passes: int = DEFAULT_PASS_COUNT

    @property
    def verified(self) -> bool:
        if not self.required:
            return True
        if len(self.passes) < self.required_passes:
            return False
        last_n = self.passes[-self.required_passes :]
        return all(p.passed for p in last_n)

    @property
    def consecutive_passing(self) -> int:
        count = 0
        for p in reversed(self.passes):
            if p.passed:
                count += 1
            else:
                break
        return count

    def to_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "requirement_reasons": self.requirement_reasons,
            "passes": [p.to_dict() for p in self.passes],
            "verified": self.verified,
            "consecutive_passing": self.consecutive_passing,
            "total_attempts": len(self.passes),
            "verified_at": self.verified_at,
            "required_passes": self.required_passes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrowserVerificationResult:
        result = cls(
            required=data.get("required", False),
            requirement_reasons=data.get("requirement_reasons", []),
            passes=[VerificationPass.from_dict(p) for p in data.get("passes", [])],
            verified_at=data.get("verified_at", 0.0),
        )
        result.required_passes = data.get("required_passes", DEFAULT_PASS_COUNT)
        return result


def _recompute_pass_verdicts(vp: VerificationPass) -> None:
    """Recompute passed flags from evidence fields — never trust submitted flags."""
    b = vp.browser_check
    b.passed = bool(b.elements_confirmed) and bool(b.snapshot_summary)

    n = vp.network_check
    n.passed = n.error_count == 0 and len(n.endpoints_checked) > 0

    c = vp.console_check
    c.passed = c.app_error_count == 0

    lg = vp.log_check
    base_ok = (
        lg.log_lines_checked > 0
        and lg.tracebacks_found == 0
        and lg.auth_failures == 0
        and lg.timeouts == 0
    )
    if not lg.cross_references:
        lg.passed = base_ok
        return
    # Full reconciliation: cross-references present
    xref_ok = all(
        cr.log_clean and cr.status_match for cr in lg.cross_references if cr.network_status == 200
    )
    orphan_ok = lg.unmatched_log_errors == 0 and len(lg.orphan_server_errors) == 0
    recon_ok = lg.reconciliation_score >= 0.8
    lg.passed = base_ok and xref_ok and orphan_ok and recon_ok


class BrowserVerificationGate:
    """Blocking gate that validates browser verification evidence.

    Deterministic: checks structured evidence, does not run browsers.
    """

    def requires_verification(
        self,
        artifact_paths: list[str],
        packet_flags: dict[str, Any] | None = None,
        proof_requirements: list[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Determine if browser verification is required.

        Returns (required, reasons).
        """
        reasons: list[str] = []
        flags = packet_flags or {}

        if flags.get("playwright_enabled"):
            reasons.append("playwright_enabled flag set on WorkPacket")

        if flags.get("cdp_enabled"):
            reasons.append("cdp_enabled flag set on WorkPacket")

        if flags.get("screenshot_capture"):
            reasons.append("screenshot_capture flag set on WorkPacket")

        reqs = proof_requirements or []
        for req in reqs:
            if req.lower() in ("browser", "ui", "visual", "playwright"):
                reasons.append(f"proof_requirement '{req}' requires browser verification")

        for path in artifact_paths:
            lower_path = path.lower()
            for ext in _UI_FILE_EXTENSIONS:
                if lower_path.endswith(ext):
                    reasons.append(f"UI file artifact: {path}")
                    break
            for pattern in _UI_PATH_PATTERNS:
                if pattern in lower_path:
                    reasons.append(f"UI path pattern '{pattern}' in artifact: {path}")
                    break

        unique_reasons = list(dict.fromkeys(reasons))
        return bool(unique_reasons), unique_reasons

    def validate_evidence(
        self,
        evidence: dict[str, Any],
        artifact_paths: list[str],
        packet_flags: dict[str, Any] | None = None,
        proof_requirements: list[str] | None = None,
        risk_class: str = "low",
    ) -> BrowserVerificationResult:
        """Validate collected browser verification evidence.

        Evidence is a dict with 'passes' key containing list of pass dicts.
        Each pass has browser_check, network_check, console_check, log_check.
        """
        required, reasons = self.requires_verification(
            artifact_paths, packet_flags, proof_requirements
        )

        if not required:
            return BrowserVerificationResult(
                required=False,
                requirement_reasons=[],
            )

        result = BrowserVerificationResult(
            required=True,
            requirement_reasons=reasons,
        )
        result.required_passes = get_pass_count(risk_class)

        raw_passes = evidence.get("passes", [])
        if not raw_passes:
            logger.info("Browser verification required but no evidence provided")
            return result

        for raw_pass in raw_passes:
            vp = VerificationPass.from_dict(raw_pass)
            _recompute_pass_verdicts(vp)
            result.passes.append(vp)

        if result.verified:
            result.verified_at = time.time()
            logger.info(
                "Browser verification passed: %d/%d consecutive passes",
                result.consecutive_passing,
                result.required_passes,
            )
        else:
            logger.info(
                "Browser verification incomplete: %d/%d consecutive passes",
                result.consecutive_passing,
                result.required_passes,
            )

        return result

    _VALID_COLLECTION_ROLES = frozenset({"executor"})

    def validate_collection_source(
        self,
        evidence: dict[str, Any],
    ) -> tuple[bool, str]:
        """Validate that evidence was collected on an executor-roled node.

        Returns (valid, message). Only executor role is accepted.
        Missing or unknown roles are rejected (fail-closed).
        """
        role = evidence.get("collection_node_role", "")
        node = evidence.get("collection_node", "")
        if not role:
            return False, (
                "Evidence missing collection_node_role — "
                "cannot verify source node. Re-collect with updated collector."
            )
        if role not in self._VALID_COLLECTION_ROLES:
            return False, (
                f"Evidence collected on '{role}' node '{node}' — "
                f"only {self._VALID_COLLECTION_ROLES} roles accepted"
            )
        return True, f"collected on {role} node '{node}'"

    def build_evidence_summary(self, result: BrowserVerificationResult) -> dict[str, Any]:
        """Build a summary suitable for inclusion in EngineeringProofPackage."""
        if not result.required:
            return {"required": False, "skipped": True}

        summary: dict[str, Any] = {
            "required": True,
            "verified": result.verified,
            "requirement_reasons": result.requirement_reasons,
            "total_attempts": len(result.passes),
            "consecutive_passing": result.consecutive_passing,
            "required_passes": result.required_passes,
        }

        if result.passes:
            last_pass = result.passes[-1]
            summary["last_pass"] = {
                "pass_number": last_pass.pass_number,
                "browser": last_pass.browser_check.passed,
                "network": last_pass.network_check.passed,
                "console": last_pass.console_check.passed,
                "logs": last_pass.log_check.passed,
                "all_passed": last_pass.passed,
            }

        if result.verified:
            summary["verified_at"] = result.verified_at

        return summary
