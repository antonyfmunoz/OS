"""Operational Boundary Policies v1.

Prevents:
  self-generated objectives, autonomous campaign creation,
  recursive continuation, hidden deferred execution,
  uncontrolled execution fanout, infinite operational progression,
  orphan operational graphs, background autonomous execution

Enforces:
  operator intent anchoring, bounded execution depth,
  bounded continuation depth, bounded operational fanout,
  explicit approval checkpoints

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

from typing import Any

from core.operations.long_horizon_operational_contracts_v1 import _now_iso


DEFAULT_OPERATIONAL_BOUNDARIES: dict[str, int | float] = {
    "max_stages_per_campaign": 20,
    "max_active_campaigns": 5,
    "max_execution_depth": 10,
    "max_continuation_depth": 5,
    "max_deferred_per_campaign": 10,
    "max_fanout": 3,
    "max_approval_wait_hours": 72,
    "max_campaign_duration_hours": 168,
}

FORBIDDEN_OPERATIONAL_ACTIONS: set[str] = {
    "self_generated_objective",
    "autonomous_campaign_creation",
    "recursive_continuation",
    "hidden_deferred_execution",
    "uncontrolled_fanout",
    "infinite_progression",
    "orphan_execution_graph",
    "background_autonomous_execution",
    "self_directed_execution",
    "independent_task_spawning",
}


class OperationalBoundaryEnforcer:
    """Enforces structural boundaries on operational execution."""

    def __init__(
        self,
        overrides: dict[str, int | float] | None = None,
    ) -> None:
        self._limits = dict(DEFAULT_OPERATIONAL_BOUNDARIES)
        if overrides:
            for key, val in overrides.items():
                if key in self._limits:
                    self._limits[key] = min(val, self._limits[key])

        self._violations: list[dict[str, Any]] = []
        self._total_checks: int = 0

    @property
    def limits(self) -> dict[str, int | float]:
        return dict(self._limits)

    def check_stages(self, current: int) -> dict[str, Any]:
        return self._check("stages_per_campaign", current,
                           int(self._limits["max_stages_per_campaign"]))

    def check_active_campaigns(self, current: int) -> dict[str, Any]:
        return self._check("active_campaigns", current,
                           int(self._limits["max_active_campaigns"]))

    def check_execution_depth(self, current: int) -> dict[str, Any]:
        return self._check("execution_depth", current,
                           int(self._limits["max_execution_depth"]))

    def check_continuation_depth(self, current: int) -> dict[str, Any]:
        return self._check("continuation_depth", current,
                           int(self._limits["max_continuation_depth"]))

    def check_deferred_count(self, current: int) -> dict[str, Any]:
        return self._check("deferred_per_campaign", current,
                           int(self._limits["max_deferred_per_campaign"]))

    def check_fanout(self, current: int) -> dict[str, Any]:
        return self._check("fanout", current,
                           int(self._limits["max_fanout"]))

    def check_no_forbidden_action(self, action: str) -> dict[str, Any]:
        self._total_checks += 1
        passed = action not in FORBIDDEN_OPERATIONAL_ACTIONS
        result: dict[str, Any] = {
            "check_type": "no_forbidden_action",
            "passed": passed,
            "action": action,
        }
        if not passed:
            violation = {
                "type": "FORBIDDEN_ACTION",
                "message": f"Forbidden operational action: {action}",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def check_objective_has_operator(self, set_by: str) -> dict[str, Any]:
        self._total_checks += 1
        passed = set_by == "operator"
        result: dict[str, Any] = {
            "check_type": "objective_operator_anchored",
            "passed": passed,
            "set_by": set_by,
        }
        if not passed:
            violation = {
                "type": "OPERATOR_ANCHORING_MISSING",
                "message": f"Objective set_by must be 'operator', got '{set_by}'",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def check_all(
        self,
        stages: int = 0,
        active_campaigns: int = 0,
        execution_depth: int = 0,
        continuation_depth: int = 0,
        deferred_count: int = 0,
        fanout: int = 0,
    ) -> dict[str, Any]:
        results = {
            "stages": self.check_stages(stages),
            "active_campaigns": self.check_active_campaigns(active_campaigns),
            "execution_depth": self.check_execution_depth(execution_depth),
            "continuation_depth": self.check_continuation_depth(continuation_depth),
            "deferred_count": self.check_deferred_count(deferred_count),
            "fanout": self.check_fanout(fanout),
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
