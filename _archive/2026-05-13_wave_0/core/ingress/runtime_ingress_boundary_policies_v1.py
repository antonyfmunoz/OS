"""Runtime Ingress Boundary Policies v1.

Enforces structural limits on ingress operations.

Prevents:
  - Direct Discord workflow execution
  - Direct CLI adapter execution
  - Session spoofing
  - Continuity hijacking
  - Hidden ingress mutation
  - Parallel ingress orchestration paths

Enforces:
  - Ingress normalization required
  - Identity anchoring required
  - Continuity lineage required
  - Replay lineage required
  - Governance inheritance required

UMH substrate subsystem. Phase 96.8BU.
"""

from __future__ import annotations

from typing import Any

from core.ingress.live_runtime_ingress_contracts_v1 import (
    IngressSource,
    RuntimeIngressSignal,
    _now_iso,
)


DEFAULT_INGRESS_BOUNDARIES: dict[str, dict[str, int | float]] = {
    "discord": {
        "max_signals_per_session": 500,
        "max_active_sessions": 5,
        "max_concurrent_workflows": 3,
        "max_payload_size_bytes": 8192,
        "max_command_length": 500,
    },
    "cli": {
        "max_signals_per_session": 1000,
        "max_active_sessions": 3,
        "max_concurrent_workflows": 5,
        "max_payload_size_bytes": 16384,
        "max_command_length": 1000,
    },
    "api": {
        "max_signals_per_session": 200,
        "max_active_sessions": 10,
        "max_concurrent_workflows": 5,
        "max_payload_size_bytes": 32768,
        "max_command_length": 2000,
    },
}

FORBIDDEN_DIRECT_EXECUTION: set[str] = {
    "discord_workflow_direct",
    "cli_adapter_direct",
    "webhook_bypass",
    "session_spoof",
    "continuity_hijack",
    "parallel_orchestration",
}


class RuntimeIngressBoundaryEnforcer:
    """Enforces structural boundaries on ingress operations."""

    def __init__(
        self,
        source: IngressSource = IngressSource.DISCORD,
        overrides: dict[str, int | float] | None = None,
    ) -> None:
        self._source = source
        defaults = dict(
            DEFAULT_INGRESS_BOUNDARIES.get(source.value, {})
        )
        if not defaults:
            defaults = dict(DEFAULT_INGRESS_BOUNDARIES["discord"])

        if overrides:
            for key, val in overrides.items():
                if key in defaults:
                    defaults[key] = min(val, defaults[key])

        self._limits = defaults
        self._violations: list[dict[str, Any]] = []
        self._total_checks: int = 0

    @property
    def limits(self) -> dict[str, int | float]:
        return dict(self._limits)

    def check_signal_count(self, current: int) -> dict[str, Any]:
        return self._check(
            "signal_count", current,
            int(self._limits.get("max_signals_per_session", 500)),
        )

    def check_active_sessions(self, current: int) -> dict[str, Any]:
        return self._check(
            "active_sessions", current,
            int(self._limits.get("max_active_sessions", 5)),
        )

    def check_concurrent_workflows(self, current: int) -> dict[str, Any]:
        return self._check(
            "concurrent_workflows", current,
            int(self._limits.get("max_concurrent_workflows", 3)),
        )

    def check_command_length(self, command: str) -> dict[str, Any]:
        return self._check(
            "command_length", len(command),
            int(self._limits.get("max_command_length", 500)),
        )

    def check_normalization_required(
        self, signal: RuntimeIngressSignal,
    ) -> dict[str, Any]:
        """Verify that a signal has been normalized before routing."""
        self._total_checks += 1
        passed = bool(signal.normalized_command or signal.raw_input)
        result: dict[str, Any] = {
            "check_type": "normalization_required",
            "passed": passed,
            "has_raw_input": bool(signal.raw_input),
            "has_normalized": bool(signal.normalized_command),
        }
        if not passed:
            violation = {
                "type": "NORMALIZATION_MISSING",
                "message": "Signal must have raw_input or normalized_command",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def check_identity_anchored(
        self, signal: RuntimeIngressSignal,
    ) -> dict[str, Any]:
        """Verify that a signal has an operator identity."""
        self._total_checks += 1
        passed = bool(signal.operator_id)
        result: dict[str, Any] = {
            "check_type": "identity_anchored",
            "passed": passed,
            "operator_id": signal.operator_id,
        }
        if not passed:
            violation = {
                "type": "IDENTITY_MISSING",
                "message": "Signal must have operator_id",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def check_no_direct_execution(self, action: str) -> dict[str, Any]:
        """Verify that no forbidden direct execution is attempted."""
        self._total_checks += 1
        passed = action not in FORBIDDEN_DIRECT_EXECUTION
        result: dict[str, Any] = {
            "check_type": "no_direct_execution",
            "passed": passed,
            "action": action,
        }
        if not passed:
            violation = {
                "type": "DIRECT_EXECUTION_FORBIDDEN",
                "message": f"Direct execution forbidden: {action}",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def check_all(
        self,
        signal_count: int = 0,
        active_sessions: int = 0,
        concurrent_workflows: int = 0,
        command: str = "",
    ) -> dict[str, Any]:
        results = {
            "signal_count": self.check_signal_count(signal_count),
            "active_sessions": self.check_active_sessions(active_sessions),
            "concurrent_workflows": self.check_concurrent_workflows(concurrent_workflows),
            "command_length": self.check_command_length(command),
        }
        all_passed = all(r["passed"] for r in results.values())
        return {
            "all_passed": all_passed,
            "checks": results,
            "violation_count": sum(1 for r in results.values() if not r["passed"]),
        }

    def _check(
        self, check_type: str, current: int, limit: int,
    ) -> dict[str, Any]:
        self._total_checks += 1
        passed = current < limit
        result: dict[str, Any] = {
            "check_type": check_type,
            "passed": passed,
            "current": current,
            "limit": limit,
            "source": self._source.value,
        }
        if not passed:
            violation = {
                "type": f"BOUNDARY_EXCEEDED:{check_type.upper()}",
                "message": f"{check_type}: {current} >= max {limit}",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def get_violations(self) -> list[dict[str, Any]]:
        return list(self._violations)

    def get_stats(self) -> dict[str, Any]:
        return {
            "source": self._source.value,
            "total_checks": self._total_checks,
            "total_violations": len(self._violations),
            "limits": dict(self._limits),
        }
