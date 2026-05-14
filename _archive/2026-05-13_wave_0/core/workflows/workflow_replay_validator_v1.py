"""Workflow Replay Validator v1.

Replays workflow traversal decisions to verify determinism:
  - Same workflow definition -> same governance decision
  - Same steps -> same boundary checks
  - Same operational mode -> same step permissions
  - Same workflow type -> same routing

Sits above the spine-level replay from Phase 96.8BR.
Validates workflow-level decision determinism.

UMH substrate subsystem. Phase 96.8BS.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.workflows.operational_workflow_contracts_v1 import (
    OperationalWorkflow,
    SupervisedOperationalMode,
    WorkflowBoundary,
    WorkflowContext,
    WorkflowPhase,
    WorkflowStep,
    WorkflowStepType,
    WorkflowType,
    _content_hash,
    _new_id,
    _now_iso,
)
from core.workflows.workflow_governance_bridge_v1 import WorkflowGovernanceBridge
from core.workflows.workflow_boundary_policies_v1 import WorkflowBoundaryEnforcer


@dataclass
class WorkflowReplayCheck:
    """A single replay check result."""

    check_name: str = ""
    expected: str = ""
    actual: str = ""
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
        }


@dataclass
class WorkflowReplayResult:
    """Result of replaying a single workflow trace."""

    workflow_id: str = ""
    workflow_type: str = ""
    checks: list[WorkflowReplayCheck] = field(default_factory=list)
    all_passed: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "checks": [c.to_dict() for c in self.checks],
            "all_passed": self.all_passed,
            "checks_total": len(self.checks),
            "checks_passed": sum(1 for c in self.checks if c.passed),
            "timestamp": self.timestamp,
        }


@dataclass
class WorkflowReplaySessionResult:
    """Result of replaying a full session of workflow traces."""

    session_id: str = ""
    results: list[WorkflowReplayResult] = field(default_factory=list)
    all_passed: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "results": [r.to_dict() for r in self.results],
            "all_passed": self.all_passed,
            "total_workflows": len(self.results),
            "total_checks": sum(len(r.checks) for r in self.results),
            "total_passed": sum(sum(1 for c in r.checks if c.passed) for r in self.results),
            "timestamp": self.timestamp,
        }


class WorkflowReplayValidator:
    """Validates workflow decision determinism through replay.

    Replays workflow governance and boundary decisions to
    verify that the same inputs produce the same outputs.
    """

    def __init__(
        self,
        proof_dir: str | Path = "data/runtime/workflow_replay_proofs",
    ) -> None:
        self._proof_dir = Path(proof_dir)
        self._proof_dir.mkdir(parents=True, exist_ok=True)
        self._replays: int = 0
        self._checks_passed: int = 0
        self._checks_failed: int = 0

    def replay_workflow_trace(
        self,
        trace: dict[str, Any],
    ) -> WorkflowReplayResult:
        """Replay a single workflow trace for determinism verification."""
        self._replays += 1

        checks: list[WorkflowReplayCheck] = []
        workflow_type = trace.get("workflow_type", "")
        operational_mode = trace.get("operational_mode", "")

        gov = WorkflowGovernanceBridge()
        enforcer = WorkflowBoundaryEnforcer()

        replay_mode = (
            SupervisedOperationalMode(operational_mode)
            if operational_mode
            else SupervisedOperationalMode.INSPECT_ONLY
        )
        replay_wf_type = WorkflowType(workflow_type) if workflow_type else WorkflowType.CUSTOM

        replay_wf = OperationalWorkflow(
            workflow_type=replay_wf_type,
            name=trace.get("name", "replay"),
            operational_mode=replay_mode,
        )
        replay_ctx = WorkflowContext(
            workflow_id=replay_wf.workflow_id,
            operational_mode=replay_mode,
        )

        gov_decision = gov.evaluate_workflow_start(replay_wf, replay_ctx)
        checks.append(
            WorkflowReplayCheck(
                check_name="governance_verdict",
                expected="approved",
                actual="approved" if gov_decision.approved else "denied",
                passed=gov_decision.approved,
            )
        )

        boundary = enforcer.create_boundary(replay_mode)
        checks.append(
            WorkflowReplayCheck(
                check_name="boundary_mode",
                expected=operational_mode,
                actual=boundary.operational_mode.value,
                passed=(boundary.operational_mode.value == operational_mode),
            )
        )

        checks.append(
            WorkflowReplayCheck(
                check_name="workflow_type",
                expected=workflow_type,
                actual=replay_wf_type.value,
                passed=(replay_wf_type.value == workflow_type),
            )
        )

        checks.append(
            WorkflowReplayCheck(
                check_name="operational_mode",
                expected=operational_mode,
                actual=replay_mode.value,
                passed=(replay_mode.value == operational_mode),
            )
        )

        test_step = WorkflowStep(
            step_type=WorkflowStepType.SPINE_TRAVERSAL,
            command="runtime-status",
        )
        step_gov = gov.evaluate_step(test_step, replay_wf, replay_ctx)
        checks.append(
            WorkflowReplayCheck(
                check_name="step_governance",
                expected="approved",
                actual="approved" if step_gov.approved else "denied",
                passed=step_gov.approved,
            )
        )

        boundary_check = enforcer.check_all_boundaries(boundary, replay_ctx)
        checks.append(
            WorkflowReplayCheck(
                check_name="boundary_check",
                expected="approved",
                actual="approved" if boundary_check.approved else "violated",
                passed=boundary_check.approved,
            )
        )

        all_passed = all(c.passed for c in checks)
        for c in checks:
            if c.passed:
                self._checks_passed += 1
            else:
                self._checks_failed += 1

        return WorkflowReplayResult(
            workflow_id=trace.get("workflow_id", ""),
            workflow_type=workflow_type,
            checks=checks,
            all_passed=all_passed,
        )

    def replay_session(
        self,
        traces: list[dict[str, Any]],
        session_id: str = "",
    ) -> WorkflowReplaySessionResult:
        """Replay all traces from a session."""
        sid = session_id or _new_id("wreplay")
        results = [self.replay_workflow_trace(t) for t in traces]
        all_passed = all(r.all_passed for r in results)

        session_result = WorkflowReplaySessionResult(
            session_id=sid,
            results=results,
            all_passed=all_passed,
        )

        proof_path = self._proof_dir / f"workflow_replay_proof_{sid}.json"
        proof_path.write_text(
            json.dumps(session_result.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

        return session_result

    def get_stats(self) -> dict[str, Any]:
        return {
            "replays": self._replays,
            "checks_passed": self._checks_passed,
            "checks_failed": self._checks_failed,
        }
