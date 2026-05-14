"""Environment Boundary Policies v1.

Prevents:
  environment-owned orchestration, uncontrolled authority,
  recursive delegation, hidden cross-environment execution,
  hidden worker spawning, environment-native execution paths,
  governance hierarchy bypass.

Enforces:
  explicit routing, explicit delegation, explicit lineage,
  explicit replay, explicit authority scope.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

from typing import Any

from core.environments.live_environment_topology_contracts_v1 import _now_iso


DEFAULT_ENVIRONMENT_BOUNDARIES: dict[str, int | float] = {
    "max_environments": 10,
    "max_delegation_depth": 3,
    "max_active_delegations": 5,
    "max_sync_epoch_gap": 10,
    "max_topology_nodes": 20,
    "max_concurrent_executions": 5,
    "max_routing_depth": 3,
}

FORBIDDEN_ENVIRONMENT_ACTIONS: set[str] = {
    "environment_owned_orchestration",
    "uncontrolled_environment_authority",
    "recursive_environment_delegation",
    "hidden_cross_environment_execution",
    "hidden_worker_spawning",
    "environment_native_execution_paths",
    "governance_hierarchy_bypass",
    "self_directed_environment_scaling",
    "autonomous_environment_creation",
    "hidden_background_workers",
}


class EnvironmentBoundaryEnforcer:
    """Enforces structural boundaries on environment coordination."""

    def __init__(
        self,
        overrides: dict[str, int | float] | None = None,
    ) -> None:
        self._limits = dict(DEFAULT_ENVIRONMENT_BOUNDARIES)
        if overrides:
            for key, val in overrides.items():
                if key in self._limits:
                    self._limits[key] = min(val, self._limits[key])

        self._violations: list[dict[str, Any]] = []
        self._total_checks: int = 0

    @property
    def limits(self) -> dict[str, int | float]:
        return dict(self._limits)

    def check_environments(self, current: int) -> dict[str, Any]:
        return self._check("environments", current,
                           int(self._limits["max_environments"]))

    def check_delegation_depth(self, current: int) -> dict[str, Any]:
        return self._check("delegation_depth", current,
                           int(self._limits["max_delegation_depth"]))

    def check_active_delegations(self, current: int) -> dict[str, Any]:
        return self._check("active_delegations", current,
                           int(self._limits["max_active_delegations"]))

    def check_routing_depth(self, current: int) -> dict[str, Any]:
        return self._check("routing_depth", current,
                           int(self._limits["max_routing_depth"]))

    def check_topology_nodes(self, current: int) -> dict[str, Any]:
        return self._check("topology_nodes", current,
                           int(self._limits["max_topology_nodes"]))

    def check_concurrent_executions(self, current: int) -> dict[str, Any]:
        return self._check("concurrent_executions", current,
                           int(self._limits["max_concurrent_executions"]))

    def check_no_forbidden_action(self, action: str) -> dict[str, Any]:
        self._total_checks += 1
        passed = action not in FORBIDDEN_ENVIRONMENT_ACTIONS
        result: dict[str, Any] = {
            "check_type": "no_forbidden_action",
            "passed": passed,
            "action": action,
        }
        if not passed:
            violation = {
                "type": "FORBIDDEN_ACTION",
                "message": f"Forbidden environment action: {action}",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def check_all(
        self,
        environments: int = 0,
        delegation_depth: int = 0,
        active_delegations: int = 0,
        routing_depth: int = 0,
        topology_nodes: int = 0,
        concurrent_executions: int = 0,
    ) -> dict[str, Any]:
        results = {
            "environments": self.check_environments(environments),
            "delegation_depth": self.check_delegation_depth(delegation_depth),
            "active_delegations": self.check_active_delegations(active_delegations),
            "routing_depth": self.check_routing_depth(routing_depth),
            "topology_nodes": self.check_topology_nodes(topology_nodes),
            "concurrent_executions": self.check_concurrent_executions(concurrent_executions),
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
