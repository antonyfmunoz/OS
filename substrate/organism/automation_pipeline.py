"""Automation Candidate Pipeline — promote repeated interventions to automation.

When OperatorCompression detects repeated operator intervention patterns,
this pipeline creates formal automation candidates with:
  - leverage score estimation
  - risk classification
  - recommended execution mode
  - approval requirement for mutation risk

Candidates flow through:
  DETECTED → PROPOSED → APPROVED/DENIED → (if approved) ACTIVE

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine
from substrate.organism.execution_modes import ExecutionMode
from substrate.organism.operator_compression import AutomationCandidate, OperatorCompression

logger = logging.getLogger(__name__)


class CandidateStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    DENIED = "denied"
    ACTIVE = "active"
    RETIRED = "retired"


class AutomationRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AutomationProposal:
    proposal_id: str
    pattern_signature: str
    description: str
    leverage_score: float
    risk: AutomationRisk
    recommended_mode: ExecutionMode
    requires_approval: bool
    status: CandidateStatus = CandidateStatus.PROPOSED
    source_occurrences: int = 0
    operator_seconds_saved: float = 0.0
    created_at: float = field(default_factory=time.time)
    decided_at: float = 0.0
    decided_by: str = ""
    denial_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "pattern_signature": self.pattern_signature,
            "description": self.description,
            "leverage_score": round(self.leverage_score, 4),
            "risk": self.risk.value,
            "recommended_mode": self.recommended_mode.value,
            "requires_approval": self.requires_approval,
            "status": self.status.value,
            "source_occurrences": self.source_occurrences,
            "operator_seconds_saved": round(self.operator_seconds_saved, 1),
            "created_at": self.created_at,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
            "denial_reason": self.denial_reason,
        }


_MAX_PROPOSALS = 200


class AutomationPipeline:
    """Creates and manages automation candidates from compression data.

    Polls OperatorCompression for repeated intervention patterns,
    estimates leverage, classifies risk, and manages approval flow.
    """

    def __init__(
        self,
        operator_compression: OperatorCompression,
        event_spine: EventSpine,
    ) -> None:
        self._compression = operator_compression
        self._spine = event_spine
        self._proposals: dict[str, AutomationProposal] = {}
        self._seen_patterns: set[str] = set()

    def scan_for_candidates(self) -> list[AutomationProposal]:
        """Check OperatorCompression for new automation candidates."""
        candidates = self._compression.automation_candidates()
        new_proposals: list[AutomationProposal] = []

        for candidate in candidates:
            if candidate.pattern_signature in self._seen_patterns:
                continue

            proposal = self._create_proposal(candidate)
            self._proposals[proposal.proposal_id] = proposal
            self._seen_patterns.add(candidate.pattern_signature)
            new_proposals.append(proposal)

            self._spine.emit(
                EventDomain.GOVERNANCE,
                "automation_proposed",
                "automation_pipeline",
                proposal.to_dict(),
                priority=EventPriority.HIGH,
            )

        return new_proposals

    def _create_proposal(self, candidate: AutomationCandidate) -> AutomationProposal:
        leverage_score = self._estimate_leverage(candidate)
        risk = self._classify_risk(candidate)
        mode = self._recommend_mode(risk)

        return AutomationProposal(
            proposal_id=f"auto-{uuid4().hex[:8]}",
            pattern_signature=candidate.pattern_signature,
            description=candidate.suggested_automation,
            leverage_score=leverage_score,
            risk=risk,
            recommended_mode=mode,
            requires_approval=(risk != AutomationRisk.LOW),
            source_occurrences=candidate.occurrence_count,
            operator_seconds_saved=candidate.total_operator_seconds,
        )

    def _estimate_leverage(self, candidate: AutomationCandidate) -> float:
        frequency_score = min(1.0, candidate.occurrence_count / 20.0)
        time_score = min(1.0, candidate.total_operator_seconds / 3600.0)
        recency = time.time() - candidate.last_seen
        recency_score = max(0.0, 1.0 - (recency / 604800.0))
        return (0.4 * frequency_score) + (0.4 * time_score) + (0.2 * recency_score)

    def _classify_risk(self, candidate: AutomationCandidate) -> AutomationRisk:
        itype = candidate.intervention_type.value
        if itype in ("approval", "escalation_response"):
            return AutomationRisk.LOW
        elif itype in ("restart", "configuration_change"):
            return AutomationRisk.MEDIUM
        elif itype in ("override", "error_correction"):
            return AutomationRisk.HIGH
        return AutomationRisk.MEDIUM

    def _recommend_mode(self, risk: AutomationRisk) -> ExecutionMode:
        if risk == AutomationRisk.LOW:
            return ExecutionMode.RECOMMEND
        elif risk == AutomationRisk.MEDIUM:
            return ExecutionMode.ASSISTED
        return ExecutionMode.AUTONOMOUS

    def approve(self, proposal_id: str, decided_by: str = "operator") -> bool:
        proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal.status != CandidateStatus.PROPOSED:
            return False

        proposal.status = CandidateStatus.APPROVED
        proposal.decided_at = time.time()
        proposal.decided_by = decided_by

        self._spine.emit(
            EventDomain.GOVERNANCE,
            "automation_approved",
            "automation_pipeline",
            {"proposal_id": proposal_id, "pattern": proposal.pattern_signature},
            priority=EventPriority.HIGH,
        )

        return True

    def deny(
        self,
        proposal_id: str,
        reason: str = "",
        decided_by: str = "operator",
    ) -> bool:
        proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal.status != CandidateStatus.PROPOSED:
            return False

        proposal.status = CandidateStatus.DENIED
        proposal.decided_at = time.time()
        proposal.decided_by = decided_by
        proposal.denial_reason = reason

        self._spine.emit(
            EventDomain.GOVERNANCE,
            "automation_denied",
            "automation_pipeline",
            {"proposal_id": proposal_id, "reason": reason},
        )

        return True

    def get_proposal(self, proposal_id: str) -> AutomationProposal | None:
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        status: CandidateStatus | None = None,
    ) -> list[dict[str, Any]]:
        proposals = list(self._proposals.values())
        if status is not None:
            proposals = [p for p in proposals if p.status == status]
        proposals.sort(key=lambda p: p.leverage_score, reverse=True)
        return [p.to_dict() for p in proposals]

    def pending_proposals(self) -> list[dict[str, Any]]:
        return self.list_proposals(status=CandidateStatus.PROPOSED)

    def pipeline_tick(self) -> dict[str, Any]:
        """Run as part of the organism tick — scan and report."""
        new = self.scan_for_candidates()
        return {
            "new_proposals": len(new),
            "total_proposals": len(self._proposals),
            "pending": sum(1 for p in self._proposals.values() if p.status == CandidateStatus.PROPOSED),
            "approved": sum(1 for p in self._proposals.values() if p.status == CandidateStatus.APPROVED),
            "denied": sum(1 for p in self._proposals.values() if p.status == CandidateStatus.DENIED),
        }

    def to_dict(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for p in self._proposals.values():
            by_status[p.status.value] = by_status.get(p.status.value, 0) + 1

        return {
            "total_proposals": len(self._proposals),
            "by_status": by_status,
            "seen_patterns": len(self._seen_patterns),
            "pending": self.pending_proposals()[:5],
        }
