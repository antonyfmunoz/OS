"""Workflow Boundary Policies v1.

Boundary enforcement for operational workflows:
  - Max traversal depth enforcement
  - Max duration enforcement
  - Max embodiment transitions enforcement
  - Max spine traversals enforcement
  - Forbidden step sequence detection
  - Forbidden workflow combination detection
  - Duration tracking with timeout

Boundary policies are structural constraints, not governance
decisions. They cannot be overridden by mode escalation.

UMH substrate subsystem. Phase 96.8BS.
"""

from __future__ import annotations

import time
from typing import Any

from core.workflows.operational_workflow_contracts_v1 import (
    SupervisedOperationalMode,
    WorkflowBoundary,
    WorkflowContext,
    WorkflowDecision,
    WorkflowDecisionType,
    WorkflowPhase,
    WorkflowStepType,
    _content_hash,
    _new_id,
    _now_iso,
)


DEFAULT_BOUNDARIES: dict[str, dict[str, Any]] = {
    "inspect_only": {
        "max_traversal_depth": 6,
        "max_duration_seconds": 60.0,
        "max_embodiment_transitions": 2,
        "max_spine_traversals": 8,
    },
    "governed_analysis": {
        "max_traversal_depth": 8,
        "max_duration_seconds": 120.0,
        "max_embodiment_transitions": 3,
        "max_spine_traversals": 12,
    },
    "operational_assistance": {
        "max_traversal_depth": 8,
        "max_duration_seconds": 300.0,
        "max_embodiment_transitions": 4,
        "max_spine_traversals": 15,
    },
    "supervised_execution": {
        "max_traversal_depth": 10,
        "max_duration_seconds": 600.0,
        "max_embodiment_transitions": 5,
        "max_spine_traversals": 20,
    },
}


class WorkflowBoundaryEnforcer:
    """Enforces boundary policies for operational workflows.

    Structural constraints that cannot be bypassed.
    Every step checks boundaries before dispatch.
    """

    def __init__(self) -> None:
        self._violations: list[dict[str, Any]] = []
        self._checks_performed: int = 0
        self._violations_detected: int = 0

    def create_boundary(
        self,
        mode: SupervisedOperationalMode,
        overrides: dict[str, Any] | None = None,
    ) -> WorkflowBoundary:
        """Create a boundary policy for the given operational mode."""
        defaults = DEFAULT_BOUNDARIES.get(mode.value, DEFAULT_BOUNDARIES["inspect_only"])

        boundary = WorkflowBoundary(
            max_traversal_depth=defaults["max_traversal_depth"],
            max_duration_seconds=defaults["max_duration_seconds"],
            max_embodiment_transitions=defaults["max_embodiment_transitions"],
            max_spine_traversals=defaults["max_spine_traversals"],
            operational_mode=mode,
        )

        if overrides:
            if "max_traversal_depth" in overrides:
                boundary.max_traversal_depth = min(
                    overrides["max_traversal_depth"],
                    defaults["max_traversal_depth"],
                )
            if "max_duration_seconds" in overrides:
                boundary.max_duration_seconds = min(
                    overrides["max_duration_seconds"],
                    defaults["max_duration_seconds"],
                )
            if "max_embodiment_transitions" in overrides:
                boundary.max_embodiment_transitions = min(
                    overrides["max_embodiment_transitions"],
                    defaults["max_embodiment_transitions"],
                )
            if "max_spine_traversals" in overrides:
                boundary.max_spine_traversals = min(
                    overrides["max_spine_traversals"],
                    defaults["max_spine_traversals"],
                )

        return boundary

    def check_all_boundaries(
        self,
        boundary: WorkflowBoundary,
        context: WorkflowContext,
        elapsed_seconds: float = 0.0,
        recent_step_types: list[str] | None = None,
    ) -> WorkflowDecision:
        """Check all boundary policies against current context."""
        self._checks_performed += 1
        violations: list[str] = []

        if not boundary.check_depth(context.traversal_depth):
            violations.append(f"DEPTH_EXCEEDED: {context.traversal_depth} >= max")

        if not boundary.check_traversals(context.spine_traversals):
            violations.append(
                f"SPINE_TRAVERSALS_EXCEEDED: {context.spine_traversals} >= {boundary.max_spine_traversals}"
            )

        if not boundary.check_transitions(context.embodiment_transitions):
            violations.append(
                f"EMBODIMENT_TRANSITIONS_EXCEEDED: {context.embodiment_transitions} >= {boundary.max_embodiment_transitions}"
            )

        if elapsed_seconds > boundary.max_duration_seconds:
            violations.append(
                f"DURATION_EXCEEDED: {elapsed_seconds:.1f}s > {boundary.max_duration_seconds}s"
            )

        if recent_step_types:
            seq_violation = self._check_forbidden_sequences(
                recent_step_types, boundary.forbidden_step_sequences
            )
            if seq_violation:
                violations.append(f"FORBIDDEN_SEQUENCE: {seq_violation}")

        approved = len(violations) == 0

        rules = ["BOUNDARY_CHECK_PERFORMED"]
        if violations:
            rules.extend(violations)
            self._violations_detected += len(violations)
            for v in violations:
                self._violations.append(
                    {
                        "violation": v,
                        "workflow_id": context.workflow_id,
                        "depth": context.traversal_depth,
                        "traversals": context.spine_traversals,
                        "transitions": context.embodiment_transitions,
                        "elapsed": elapsed_seconds,
                        "timestamp": _now_iso(),
                    }
                )

        decision = WorkflowDecision(
            decision_type=WorkflowDecisionType.BOUNDARY_CHECK,
            workflow_id=context.workflow_id,
            phase=context.current_phase,
            input_summary=(
                f"depth:{context.traversal_depth} "
                f"traversals:{context.spine_traversals} "
                f"transitions:{context.embodiment_transitions} "
                f"elapsed:{elapsed_seconds:.1f}s"
            ),
            output_summary=f"verdict:{'approved' if approved else 'violated'} violations:{len(violations)}",
            rules_applied=rules,
            approved=approved,
            denial_reason="; ".join(violations) if violations else "",
            correlation_id=context.correlation_id,
        )

        return decision

    def _check_forbidden_sequences(
        self,
        recent: list[str],
        forbidden: list[list[str]],
    ) -> str:
        """Check if recent step types form a forbidden sequence."""
        for seq in forbidden:
            seq_len = len(seq)
            if len(recent) >= seq_len:
                tail = recent[-seq_len:]
                if tail == seq:
                    return " → ".join(seq)
        return ""

    def get_stats(self) -> dict[str, Any]:
        return {
            "checks_performed": self._checks_performed,
            "violations_detected": self._violations_detected,
            "recent_violations": self._violations[-5:],
        }

    def get_violations(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._violations[-limit:]
