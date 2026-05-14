"""Scaling Boundary Policies v1.

Prevents:
  autonomous scaling, recursive scaling loops,
  hidden concurrency expansion, hidden throttling bypass,
  uncontrolled resource allocation, environment self-regulation,
  hidden degraded-mode mutation.

Enforces:
  explicit scaling lineage, explicit pressure visibility,
  explicit operator authority, deterministic regulation.

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

from typing import Any

from core.scaling.operational_scaling_contracts_v1 import _now_iso


DEFAULT_SCALING_BOUNDARIES: dict[str, int | float] = {
    "max_concurrent_global": 5,
    "max_queue_depth": 50,
    "max_throttle_delay_ms": 5000,
    "max_recovery_attempts": 3,
    "max_continuation_depth": 5,
    "max_deferred_accumulation": 20,
    "max_pressure_score": 1.0,
}

FORBIDDEN_SCALING_ACTIONS: set[str] = {
    "autonomous_scaling",
    "recursive_scaling_loops",
    "hidden_concurrency_expansion",
    "hidden_throttling_bypass",
    "uncontrolled_resource_allocation",
    "environment_self_regulation",
    "hidden_degraded_mode_mutation",
    "self_directed_optimization",
    "automatic_operational_escalation",
    "hidden_priority_mutation",
}


class ScalingBoundaryEnforcer:
    """Enforces structural boundaries on scaling coordination."""

    def __init__(
        self,
        overrides: dict[str, int | float] | None = None,
    ) -> None:
        self._limits = dict(DEFAULT_SCALING_BOUNDARIES)
        if overrides:
            for key, val in overrides.items():
                if key in self._limits:
                    self._limits[key] = min(val, self._limits[key])

        self._violations: list[dict[str, Any]] = []
        self._total_checks: int = 0

    @property
    def limits(self) -> dict[str, int | float]:
        return dict(self._limits)

    def check_concurrent(self, current: int) -> dict[str, Any]:
        return self._check("concurrent_global", current,
                           int(self._limits["max_concurrent_global"]))

    def check_queue_depth(self, current: int) -> dict[str, Any]:
        return self._check("queue_depth", current,
                           int(self._limits["max_queue_depth"]))

    def check_throttle_delay(self, current: int) -> dict[str, Any]:
        return self._check("throttle_delay_ms", current,
                           int(self._limits["max_throttle_delay_ms"]))

    def check_recovery_attempts(self, current: int) -> dict[str, Any]:
        return self._check("recovery_attempts", current,
                           int(self._limits["max_recovery_attempts"]))

    def check_continuation_depth(self, current: int) -> dict[str, Any]:
        return self._check("continuation_depth", current,
                           int(self._limits["max_continuation_depth"]))

    def check_deferred_accumulation(self, current: int) -> dict[str, Any]:
        return self._check("deferred_accumulation", current,
                           int(self._limits["max_deferred_accumulation"]))

    def check_no_forbidden_action(self, action: str) -> dict[str, Any]:
        self._total_checks += 1
        passed = action not in FORBIDDEN_SCALING_ACTIONS
        result: dict[str, Any] = {
            "check_type": "no_forbidden_action",
            "passed": passed,
            "action": action,
        }
        if not passed:
            violation = {
                "type": "FORBIDDEN_ACTION",
                "message": f"Forbidden scaling action: {action}",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def check_all(
        self,
        concurrent: int = 0,
        queue_depth: int = 0,
        throttle_delay: int = 0,
        recovery_attempts: int = 0,
        continuation_depth: int = 0,
        deferred_accumulation: int = 0,
    ) -> dict[str, Any]:
        results = {
            "concurrent": self.check_concurrent(concurrent),
            "queue_depth": self.check_queue_depth(queue_depth),
            "throttle_delay": self.check_throttle_delay(throttle_delay),
            "recovery_attempts": self.check_recovery_attempts(recovery_attempts),
            "continuation_depth": self.check_continuation_depth(continuation_depth),
            "deferred_accumulation": self.check_deferred_accumulation(deferred_accumulation),
        }
        all_passed = all(r["passed"] for r in results.values())
        return {
            "all_passed": all_passed,
            "checks": results,
            "violation_count": sum(1 for r in results.values() if not r["passed"]),
        }

    def _check(self, check_type: str, current: int, limit: int) -> dict[str, Any]:
        self._total_checks += 1
        passed = current < limit
        result: dict[str, Any] = {
            "check_type": check_type,
            "passed": passed,
            "current": current,
            "limit": limit,
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
            "total_checks": self._total_checks,
            "total_violations": len(self._violations),
            "limits": dict(self._limits),
        }
