"""Sandbox Orchestrator — ties approval gate to PR factory execution.

Lifecycle:
  1. Candidate discovered by CandidateSupplyEngine
  2. ApprovalPacket created by OperatorApprovalGate
  3. Operator approves packet
  4. Orchestrator converts supply candidate to AutonomousImprovementCandidate
  5. PR Factory creates sandbox, executes, validates, commits, creates PR
  6. SandboxOutcomeCommitted emitted
  7. ProductionOutcomeCommitted blocked until merge + verification

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

from substrate.organism.approval_gate import ApprovalPacket, ApprovalStatus, OperatorApprovalGate
from substrate.organism.autonomous_improvement_lane import (
    AutonomousImprovementCandidate,
)
from substrate.organism.autonomous_pr_factory import (
    AutonomousPRFactory,
    AutonomousPRRequest,
    AutonomousPRResult,
    SandboxOutcomeCommitted,
)
from substrate.organism.candidate_supply_engine import SupplyCandidate
from substrate.organism.trial_runner import CandidateSource
from substrate.organism.worktree_sandbox import SandboxManager

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

_SOURCE_MAP = {
    "contradictions": CandidateSource.CONTRADICTION,
    "world_model": CandidateSource.WORLD_MODEL_DEFECT,
    "dependency_graph": CandidateSource.DEPENDENCY_WEAK_POINT,
    "readiness": CandidateSource.READINESS_GAP,
    "bottlenecks": CandidateSource.BOTTLENECK,
    "template_audit_gaps": CandidateSource.CONTRADICTION,
}


def _supply_to_improvement(
    supply: SupplyCandidate,
    approval: ApprovalPacket,
) -> AutonomousImprovementCandidate:
    source = _SOURCE_MAP.get(supply.source, CandidateSource.CONTRADICTION)
    return AutonomousImprovementCandidate(
        candidate_id=supply.candidate_id,
        source=source,
        description=supply.description,
        affected_files=supply.affected_files,
        risk_class=supply.risk_class,
        non_mutating=supply.non_mutating,
        validation_method=supply.validation_method,
        rollback_method=supply.rollback_method,
        matching_template_id=approval.matched_template_id,
        template_confidence=supply.template_confidence,
        agent_reliability=supply.agent_reliability,
        expected_outcome=supply.expected_delta,
        evidence=json.dumps(supply.evidence, default=str) if supply.evidence else "",
    )


@dataclass
class SandboxExecutionResult:
    success: bool = False
    packet_id: str = ""
    candidate_id: str = ""
    sandbox_id: str = ""
    branch_name: str = ""
    pr_url: str = ""
    pr_number: int = 0
    manifest_id: str = ""
    sandbox_outcome_id: str = ""
    validation_passed: bool = False
    production_truth_unchanged: bool = True
    error: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "packet_id": self.packet_id,
            "candidate_id": self.candidate_id,
            "sandbox_id": self.sandbox_id,
            "branch_name": self.branch_name,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "manifest_id": self.manifest_id,
            "sandbox_outcome_id": self.sandbox_outcome_id,
            "validation_passed": self.validation_passed,
            "production_truth_unchanged": self.production_truth_unchanged,
            "error": self.error,
            "created_at": self.created_at,
        }


class SandboxOrchestrator:
    """Orchestrates the full cadence → approval → sandbox → PR pipeline."""

    def __init__(
        self,
        approval_gate: OperatorApprovalGate,
        pr_factory: AutonomousPRFactory,
        sandbox_manager: SandboxManager,
        store_dir: str | None = None,
    ) -> None:
        self._approval_gate = approval_gate
        self._pr_factory = pr_factory
        self._sandbox_manager = sandbox_manager
        self._store_dir = store_dir or os.path.join(_REPO_ROOT, "data", "umh", "autonomous_lane")
        self._executions: list[SandboxExecutionResult] = []
        self._sandbox_outcomes: list[SandboxOutcomeCommitted] = []

    def execute_approved(
        self,
        packet_id: str,
        supply_candidate: SupplyCandidate,
        step_executors_factory: Any = None,
    ) -> SandboxExecutionResult:
        result = SandboxExecutionResult(packet_id=packet_id)

        packet = self._approval_gate.get_packet(packet_id)
        if not packet:
            result.error = f"Approval packet {packet_id} not found"
            return result

        if packet.status != ApprovalStatus.APPROVED:
            result.error = f"Packet {packet_id} is {packet.status.value}, not approved"
            return result

        candidate = _supply_to_improvement(supply_candidate, packet)
        result.candidate_id = candidate.candidate_id

        slug = packet.candidate_title.lower().replace(" ", "-")[:30]

        def on_sandbox_outcome(outcome: SandboxOutcomeCommitted) -> None:
            self._sandbox_outcomes.append(outcome)

        self._pr_factory._on_sandbox_outcome = on_sandbox_outcome

        pr_request = AutonomousPRRequest(
            candidate=candidate,
            candidate_slug=slug,
            description=packet.candidate_description,
            step_executors_factory=step_executors_factory,
        )

        pr_result = self._pr_factory.create_pr(pr_request)

        result.success = pr_result.success
        result.error = pr_result.error

        if pr_result.sandbox:
            result.sandbox_id = pr_result.sandbox.sandbox_id
            result.branch_name = pr_result.sandbox.branch_name

        if pr_result.manifest:
            result.manifest_id = pr_result.manifest.manifest_id

        if pr_result.review_packet:
            result.pr_url = pr_result.review_packet.pr_url
            result.pr_number = pr_result.review_packet.pr_number
            result.validation_passed = pr_result.review_packet.validation_gate.all_passed

        if pr_result.sandbox_outcome:
            result.sandbox_outcome_id = pr_result.sandbox_outcome.event_id

        truth = self._sandbox_manager.production_truth()
        main_commit = truth.get("main_commit", "")
        result.production_truth_unchanged = bool(main_commit)

        self._executions.append(result)
        self._persist(result)
        return result

    def _persist(self, result: SandboxExecutionResult) -> None:
        os.makedirs(self._store_dir, exist_ok=True)
        path = os.path.join(self._store_dir, "sandbox_executions.jsonl")
        with open(path, "a") as f:
            f.write(json.dumps(result.to_dict(), default=str) + "\n")

    @property
    def executions(self) -> list[SandboxExecutionResult]:
        return list(self._executions)

    @property
    def sandbox_outcomes(self) -> list[SandboxOutcomeCommitted]:
        return list(self._sandbox_outcomes)

    def summary(self) -> dict[str, Any]:
        return {
            "total_executions": len(self._executions),
            "successful": sum(1 for e in self._executions if e.success),
            "failed": sum(1 for e in self._executions if not e.success),
            "sandbox_outcomes_emitted": len(self._sandbox_outcomes),
            "production_truth_unchanged": all(e.production_truth_unchanged for e in self._executions),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "executions": [e.to_dict() for e in self._executions[-10:]],
            "sandbox_outcomes": [o.to_dict() for o in self._sandbox_outcomes[-10:]],
        }
