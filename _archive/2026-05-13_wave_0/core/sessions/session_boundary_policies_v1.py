"""Session Boundary Policies v1.

Enforces structural limits on session operations.

Prevents:
  - Hidden session mutation
  - Orphaned continuity chains
  - Duplicate active sessions (per operator)
  - Recursive session restoration
  - Stale checkpoint resurrection
  - Interface-specific session ownership

Enforces:
  - Single canonical session manager
  - Lineage-complete restoration
  - Deterministic checkpoint replay
  - Explicit session lifecycle transitions

UMH substrate subsystem. Phase 96.8BV.
"""

from __future__ import annotations

from typing import Any

from core.sessions.persistent_substrate_session_contracts_v1 import (
    _now_iso,
)


DEFAULT_SESSION_BOUNDARIES: dict[str, int | float] = {
    "max_active_sessions_per_operator": 3,
    "max_checkpoints_per_session": 50,
    "max_chronology_events": 1000,
    "max_continuity_chain_depth": 20,
    "max_restoration_depth": 5,
    "max_concurrent_sessions": 10,
    "max_session_duration_hours": 72,
}

FORBIDDEN_SESSION_OPERATIONS: set[str] = {
    "interface_owned_session",
    "cognition_owned_execution",
    "workflow_owned_persistence",
    "parallel_session_manager",
    "hidden_session_mutation",
    "recursive_restoration",
    "stale_checkpoint_resurrection",
    "orphaned_continuity",
}


class SessionBoundaryEnforcer:
    """Enforces structural boundaries on session operations."""

    def __init__(
        self,
        overrides: dict[str, int | float] | None = None,
    ) -> None:
        self._limits = dict(DEFAULT_SESSION_BOUNDARIES)

        if overrides:
            for key, val in overrides.items():
                if key in self._limits:
                    self._limits[key] = min(val, self._limits[key])

        self._violations: list[dict[str, Any]] = []
        self._total_checks: int = 0

    @property
    def limits(self) -> dict[str, int | float]:
        return dict(self._limits)

    def check_active_sessions(
        self, operator_id: str, current: int,
    ) -> dict[str, Any]:
        return self._check(
            "active_sessions_per_operator", current,
            int(self._limits["max_active_sessions_per_operator"]),
        )

    def check_checkpoints(self, current: int) -> dict[str, Any]:
        return self._check(
            "checkpoints_per_session", current,
            int(self._limits["max_checkpoints_per_session"]),
        )

    def check_chronology_events(self, current: int) -> dict[str, Any]:
        return self._check(
            "chronology_events", current,
            int(self._limits["max_chronology_events"]),
        )

    def check_continuity_chain_depth(self, current: int) -> dict[str, Any]:
        return self._check(
            "continuity_chain_depth", current,
            int(self._limits["max_continuity_chain_depth"]),
        )

    def check_restoration_depth(self, current: int) -> dict[str, Any]:
        return self._check(
            "restoration_depth", current,
            int(self._limits["max_restoration_depth"]),
        )

    def check_concurrent_sessions(self, current: int) -> dict[str, Any]:
        return self._check(
            "concurrent_sessions", current,
            int(self._limits["max_concurrent_sessions"]),
        )

    def check_no_forbidden_operation(self, operation: str) -> dict[str, Any]:
        """Verify that no forbidden session operation is attempted."""
        self._total_checks += 1
        passed = operation not in FORBIDDEN_SESSION_OPERATIONS
        result: dict[str, Any] = {
            "check_type": "no_forbidden_operation",
            "passed": passed,
            "operation": operation,
        }
        if not passed:
            violation = {
                "type": "FORBIDDEN_OPERATION",
                "message": f"Forbidden session operation: {operation}",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def check_no_duplicate_active(
        self, operator_id: str, active_session_ids: list[str],
        proposed_session_id: str,
    ) -> dict[str, Any]:
        """Verify no duplicate active sessions for operator."""
        self._total_checks += 1
        passed = proposed_session_id not in active_session_ids
        result: dict[str, Any] = {
            "check_type": "no_duplicate_active",
            "passed": passed,
            "operator_id": operator_id,
            "active_count": len(active_session_ids),
        }
        if not passed:
            violation = {
                "type": "DUPLICATE_ACTIVE_SESSION",
                "message": f"Session {proposed_session_id} already active for {operator_id}",
            }
            self._violations.append(violation)
            result["violation"] = violation
        return result

    def check_all(
        self,
        active_sessions: int = 0,
        checkpoints: int = 0,
        chronology_events: int = 0,
        continuity_depth: int = 0,
        restoration_depth: int = 0,
        concurrent_sessions: int = 0,
    ) -> dict[str, Any]:
        results = {
            "active_sessions": self.check_active_sessions("", active_sessions),
            "checkpoints": self.check_checkpoints(checkpoints),
            "chronology_events": self.check_chronology_events(chronology_events),
            "continuity_depth": self.check_continuity_chain_depth(continuity_depth),
            "restoration_depth": self.check_restoration_depth(restoration_depth),
            "concurrent_sessions": self.check_concurrent_sessions(concurrent_sessions),
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
