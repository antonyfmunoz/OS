"""Workflow Governance Bridge v1.

Governance layer for operational workflows:
  - Recursion prevention (workflow A → B → A forbidden)
  - Escalation detection (mode upgrade attempts)
  - Forbidden workflow transitions
  - Step-level governance checks
  - Workflow-level approval/denial

Sits above the spine-level governance from Phase 96.8BR.
The spine governs individual commands; this module governs
multi-step workflow orchestration patterns.

UMH substrate subsystem. Phase 96.8BS.
"""

from __future__ import annotations

from typing import Any

from core.workflows.operational_workflow_contracts_v1 import (
    OperationalWorkflow,
    SupervisedOperationalMode,
    WorkflowContext,
    WorkflowDecision,
    WorkflowDecisionType,
    WorkflowPhase,
    WorkflowStep,
    WorkflowStepType,
    WorkflowType,
    _content_hash,
    _new_id,
    _now_iso,
)


FORBIDDEN_RECURSIVE_CHAINS: list[list[str]] = [
    ["operational_briefing", "operational_briefing"],
    ["operational_resume", "operational_resume"],
    ["governed_planning", "governed_planning"],
    ["runtime_inspection", "runtime_inspection"],
]

FORBIDDEN_ESCALATION_PATHS: list[tuple[str, str]] = [
    ("inspect_only", "supervised_execution"),
    ("governed_analysis", "supervised_execution"),
]

MODE_HIERARCHY: dict[str, int] = {
    "inspect_only": 0,
    "governed_analysis": 1,
    "operational_assistance": 2,
    "supervised_execution": 3,
}

FORBIDDEN_WORKFLOW_TRANSITIONS: list[tuple[str, str]] = [
    ("workstation_inspection", "browser_inspection"),
    ("browser_inspection", "workstation_inspection"),
]


class WorkflowGovernanceBridge:
    """Governance bridge for operational workflow execution.

    Evaluates workflow-level governance before and during execution:
    recursion prevention, escalation detection, mode constraints,
    and forbidden transitions.
    """

    def __init__(self) -> None:
        self._active_workflow_chain: list[str] = []
        self._decisions: list[dict[str, Any]] = []
        self._denials: int = 0
        self._approvals: int = 0
        self._escalation_attempts: int = 0

    def evaluate_workflow_start(
        self,
        workflow: OperationalWorkflow,
        context: WorkflowContext,
    ) -> WorkflowDecision:
        """Evaluate governance before a workflow starts."""
        rules: list[str] = []
        denial_reason = ""

        recursion_check = self._check_recursion(workflow.workflow_type)
        if not recursion_check["allowed"]:
            denial_reason = recursion_check["reason"]
            rules.append("RECURSIVE_WORKFLOW_FORBIDDEN")

        if not denial_reason:
            escalation_check = self._check_escalation(
                workflow.operational_mode, context.operational_mode
            )
            if not escalation_check["allowed"]:
                denial_reason = escalation_check["reason"]
                rules.append("ESCALATION_FORBIDDEN")
                self._escalation_attempts += 1

        if not denial_reason:
            transition_check = self._check_workflow_transition(workflow.workflow_type)
            if not transition_check["allowed"]:
                denial_reason = transition_check["reason"]
                rules.append("WORKFLOW_TRANSITION_FORBIDDEN")

        rules.append("WORKFLOW_GOVERNANCE_EVALUATED")
        approved = not denial_reason

        decision = WorkflowDecision(
            decision_type=WorkflowDecisionType.GOVERNANCE,
            workflow_id=workflow.workflow_id,
            phase=WorkflowPhase.INITIALIZED,
            input_summary=f"workflow:{workflow.workflow_type.value} mode:{workflow.operational_mode.value}",
            output_summary=f"verdict:{'approved' if approved else 'denied'}",
            rules_applied=rules,
            approved=approved,
            denial_reason=denial_reason,
            correlation_id=context.correlation_id,
        )

        if approved:
            self._active_workflow_chain.append(workflow.workflow_type.value)
            self._approvals += 1
        else:
            self._denials += 1

        self._decisions.append(decision.to_dict())
        return decision

    def evaluate_step(
        self,
        step: WorkflowStep,
        workflow: OperationalWorkflow,
        context: WorkflowContext,
    ) -> WorkflowDecision:
        """Evaluate governance for a workflow step."""
        rules: list[str] = []
        denial_reason = ""

        if not workflow.boundary.check_step_allowed(step.step_type):
            denial_reason = (
                f"Step type {step.step_type.value} not allowed in "
                f"mode {workflow.operational_mode.value}"
            )
            rules.append("STEP_TYPE_FORBIDDEN_BY_MODE")

        if not denial_reason and not workflow.boundary.check_depth(context.traversal_depth):
            denial_reason = f"Traversal depth {context.traversal_depth} exceeds boundary"
            rules.append("TRAVERSAL_DEPTH_EXCEEDED")

        if not denial_reason and not workflow.boundary.check_traversals(context.spine_traversals):
            denial_reason = f"Spine traversals {context.spine_traversals} exceeds boundary"
            rules.append("SPINE_TRAVERSAL_LIMIT_EXCEEDED")

        if (
            not denial_reason
            and step.step_type == WorkflowStepType.SPINE_TRAVERSAL
            and not workflow.boundary.check_transitions(context.embodiment_transitions)
        ):
            denial_reason = (
                f"Embodiment transitions {context.embodiment_transitions} exceeds boundary"
            )
            rules.append("EMBODIMENT_TRANSITION_LIMIT_EXCEEDED")

        rules.append("STEP_GOVERNANCE_EVALUATED")
        approved = not denial_reason

        decision = WorkflowDecision(
            decision_type=WorkflowDecisionType.STEP_DISPATCH,
            workflow_id=workflow.workflow_id,
            step_id=step.step_id,
            phase=WorkflowPhase.ACTIVE,
            input_summary=f"step:{step.step_type.value} command:{step.command} depth:{context.traversal_depth}",
            output_summary=f"verdict:{'approved' if approved else 'denied'}",
            rules_applied=rules,
            approved=approved,
            denial_reason=denial_reason,
            correlation_id=context.correlation_id,
        )

        if approved:
            self._approvals += 1
        else:
            self._denials += 1

        self._decisions.append(decision.to_dict())
        return decision

    def evaluate_escalation_request(
        self,
        requested_mode: SupervisedOperationalMode,
        current_mode: SupervisedOperationalMode,
        workflow_id: str,
        correlation_id: str,
    ) -> WorkflowDecision:
        """Evaluate a request to escalate operational mode."""
        escalation_check = self._check_escalation(requested_mode, current_mode)
        approved = escalation_check["allowed"]

        rules = ["ESCALATION_REQUEST_EVALUATED"]
        if not approved:
            rules.append("ESCALATION_FORBIDDEN")
            self._escalation_attempts += 1

        decision = WorkflowDecision(
            decision_type=WorkflowDecisionType.ESCALATION,
            workflow_id=workflow_id,
            phase=WorkflowPhase.ACTIVE,
            input_summary=f"from:{current_mode.value} to:{requested_mode.value}",
            output_summary=f"verdict:{'approved' if approved else 'denied'}",
            rules_applied=rules,
            approved=approved,
            denial_reason="" if approved else escalation_check["reason"],
            correlation_id=correlation_id,
        )

        self._decisions.append(decision.to_dict())
        return decision

    def complete_workflow(self, workflow_type: str) -> None:
        """Remove a workflow from the active chain on completion."""
        if workflow_type in self._active_workflow_chain:
            self._active_workflow_chain.remove(workflow_type)

    def _check_recursion(self, workflow_type: WorkflowType) -> dict[str, Any]:
        """Check if starting this workflow would create a forbidden recursive chain."""
        candidate_chain = self._active_workflow_chain + [workflow_type.value]

        for forbidden in FORBIDDEN_RECURSIVE_CHAINS:
            forbidden_len = len(forbidden)
            if len(candidate_chain) >= forbidden_len:
                tail = candidate_chain[-forbidden_len:]
                if tail == forbidden:
                    return {
                        "allowed": False,
                        "reason": f"Recursive chain detected: {' → '.join(forbidden)}",
                    }

        return {"allowed": True, "reason": ""}

    def _check_escalation(
        self,
        requested: SupervisedOperationalMode,
        current: SupervisedOperationalMode,
    ) -> dict[str, Any]:
        """Check if mode escalation is allowed."""
        pair = (current.value, requested.value)
        if pair in FORBIDDEN_ESCALATION_PATHS:
            return {
                "allowed": False,
                "reason": f"Direct escalation from {current.value} to {requested.value} forbidden",
            }

        requested_level = MODE_HIERARCHY.get(requested.value, 0)
        current_level = MODE_HIERARCHY.get(current.value, 0)
        if requested_level > current_level + 1:
            return {
                "allowed": False,
                "reason": f"Escalation skips levels: {current.value}(L{current_level}) to {requested.value}(L{requested_level})",
            }

        return {"allowed": True, "reason": ""}

    def _check_workflow_transition(self, workflow_type: WorkflowType) -> dict[str, Any]:
        """Check if transitioning to this workflow type is allowed."""
        if self._active_workflow_chain:
            current_type = self._active_workflow_chain[-1]
            pair = (current_type, workflow_type.value)
            if pair in FORBIDDEN_WORKFLOW_TRANSITIONS:
                return {
                    "allowed": False,
                    "reason": f"Transition from {current_type} to {workflow_type.value} forbidden",
                }

        return {"allowed": True, "reason": ""}

    def get_stats(self) -> dict[str, Any]:
        return {
            "approvals": self._approvals,
            "denials": self._denials,
            "escalation_attempts": self._escalation_attempts,
            "active_chain_depth": len(self._active_workflow_chain),
            "active_chain": list(self._active_workflow_chain),
            "total_decisions": len(self._decisions),
        }

    def get_recent_decisions(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._decisions[-limit:]
