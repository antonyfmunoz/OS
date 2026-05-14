"""Cognition Boundary Policies v1.

Enforces structural limits on cognition operations:
  - Max cognition depth per mode
  - Max open loops per session
  - Max attention reweights per session
  - Max focus shifts per session
  - Max checkpoint frequency
  - Max continuity chain length

Overrides cannot exceed defaults (same pattern as
workflow boundary policies from 96.8BS).

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    MODE_COGNITION_POLICIES,
    OperatorMode,
)


DEFAULT_COGNITION_BOUNDARIES: dict[str, dict[str, int | float]] = {
    "focused_execution": {
        "max_cognition_depth": 12,
        "max_open_loops": 10,
        "max_attention_reweights": 20,
        "max_focus_shifts": 15,
        "max_checkpoints_per_session": 10,
        "max_continuity_chain": 50,
        "max_working_window_items": 20,
    },
    "operational_supervision": {
        "max_cognition_depth": 20,
        "max_open_loops": 25,
        "max_attention_reweights": 30,
        "max_focus_shifts": 25,
        "max_checkpoints_per_session": 20,
        "max_continuity_chain": 100,
        "max_working_window_items": 40,
    },
    "continuity_resume": {
        "max_cognition_depth": 30,
        "max_open_loops": 50,
        "max_attention_reweights": 15,
        "max_focus_shifts": 10,
        "max_checkpoints_per_session": 30,
        "max_continuity_chain": 200,
        "max_working_window_items": 60,
    },
    "inspection_mode": {
        "max_cognition_depth": 6,
        "max_open_loops": 5,
        "max_attention_reweights": 5,
        "max_focus_shifts": 5,
        "max_checkpoints_per_session": 3,
        "max_continuity_chain": 20,
        "max_working_window_items": 10,
    },
    "planning_mode": {
        "max_cognition_depth": 16,
        "max_open_loops": 20,
        "max_attention_reweights": 25,
        "max_focus_shifts": 20,
        "max_checkpoints_per_session": 15,
        "max_continuity_chain": 80,
        "max_working_window_items": 30,
    },
}


class CognitionBoundaryEnforcer:
    """Enforces structural limits on cognition operations.

    Overrides are capped: min(override, default).
    Violations reported but do not raise — the caller
    decides whether to abort.
    """

    def __init__(
        self,
        mode: OperatorMode = OperatorMode.FOCUSED_EXECUTION,
        overrides: dict[str, int | float] | None = None,
    ) -> None:
        self._mode = mode
        defaults = dict(
            DEFAULT_COGNITION_BOUNDARIES.get(mode.value, {})
        )

        if overrides:
            for key, val in overrides.items():
                if key in defaults:
                    defaults[key] = min(val, defaults[key])

        self._limits = defaults
        self._violations: list[dict[str, Any]] = []
        self._total_checks: int = 0

    @property
    def mode(self) -> OperatorMode:
        return self._mode

    @property
    def limits(self) -> dict[str, int | float]:
        return dict(self._limits)

    # ------------------------------------------------------------------
    # Boundary checks
    # ------------------------------------------------------------------

    def check_cognition_depth(self, current_depth: int) -> dict[str, Any]:
        """Check if cognition depth is within bounds."""
        return self._check(
            "cognition_depth",
            current_depth,
            int(self._limits.get("max_cognition_depth", 12)),
        )

    def check_open_loops(self, current_count: int) -> dict[str, Any]:
        """Check if open loop count is within bounds."""
        return self._check(
            "open_loops",
            current_count,
            int(self._limits.get("max_open_loops", 10)),
        )

    def check_attention_reweights(self, current_count: int) -> dict[str, Any]:
        """Check if attention reweight count is within bounds."""
        return self._check(
            "attention_reweights",
            current_count,
            int(self._limits.get("max_attention_reweights", 20)),
        )

    def check_focus_shifts(self, current_count: int) -> dict[str, Any]:
        """Check if focus shift count is within bounds."""
        return self._check(
            "focus_shifts",
            current_count,
            int(self._limits.get("max_focus_shifts", 15)),
        )

    def check_checkpoints(self, current_count: int) -> dict[str, Any]:
        """Check if checkpoint count is within bounds."""
        return self._check(
            "checkpoints",
            current_count,
            int(self._limits.get("max_checkpoints_per_session", 10)),
        )

    def check_continuity_chain(self, chain_length: int) -> dict[str, Any]:
        """Check if continuity chain length is within bounds."""
        return self._check(
            "continuity_chain",
            chain_length,
            int(self._limits.get("max_continuity_chain", 50)),
        )

    def check_working_window(self, item_count: int) -> dict[str, Any]:
        """Check if working window item count is within bounds."""
        return self._check(
            "working_window",
            item_count,
            int(self._limits.get("max_working_window_items", 20)),
        )

    def _check(
        self,
        check_type: str,
        current: int | float,
        limit: int | float,
    ) -> dict[str, Any]:
        self._total_checks += 1
        passed = current < limit
        result = {
            "check_type": check_type,
            "passed": passed,
            "current": current,
            "limit": limit,
            "mode": self._mode.value,
        }

        if not passed:
            violation = {
                "type": f"BOUNDARY_EXCEEDED:{check_type.upper()}",
                "message": f"{check_type}: {current} >= max {limit}",
                **result,
            }
            self._violations.append(violation)
            result["violation"] = violation

        return result

    # ------------------------------------------------------------------
    # Bulk check
    # ------------------------------------------------------------------

    def check_all(
        self,
        cognition_depth: int = 0,
        open_loops: int = 0,
        attention_reweights: int = 0,
        focus_shifts: int = 0,
        checkpoints: int = 0,
        continuity_chain: int = 0,
        working_window: int = 0,
    ) -> dict[str, Any]:
        """Run all boundary checks at once."""
        results = {
            "cognition_depth": self.check_cognition_depth(cognition_depth),
            "open_loops": self.check_open_loops(open_loops),
            "attention_reweights": self.check_attention_reweights(attention_reweights),
            "focus_shifts": self.check_focus_shifts(focus_shifts),
            "checkpoints": self.check_checkpoints(checkpoints),
            "continuity_chain": self.check_continuity_chain(continuity_chain),
            "working_window": self.check_working_window(working_window),
        }
        all_passed = all(r["passed"] for r in results.values())
        return {
            "all_passed": all_passed,
            "checks": results,
            "violation_count": sum(
                1 for r in results.values() if not r["passed"]
            ),
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_violations(self) -> list[dict[str, Any]]:
        return list(self._violations)

    def get_stats(self) -> dict[str, Any]:
        return {
            "mode": self._mode.value,
            "total_checks": self._total_checks,
            "total_violations": len(self._violations),
            "limits": dict(self._limits),
        }
