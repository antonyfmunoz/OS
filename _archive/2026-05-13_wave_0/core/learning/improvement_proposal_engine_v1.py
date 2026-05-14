"""Improvement Proposal Engine v1.

Creates improvement proposals from detected patterns.
8 proposal types covering policy, template, routing, adapter,
knowledge, workflow, resilience, and scaling improvements.

Proposals require operator approval. Cannot mutate anything directly.

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from core.learning.adaptive_learning_contracts_v1 import (
    ImprovementProposal,
    ProposalType,
    _new_id,
    _now_iso,
)

MAX_PENDING_PROPOSALS = 50
MAX_TOTAL_PROPOSALS = 500
KNOWN_PROPOSAL_TYPES = {pt.value for pt in ProposalType}
MIN_CONFIDENCE_FOR_PROPOSAL = 0.3


class ImprovementProposalEngine:
    """Creates and manages improvement proposals."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._pending: list[ImprovementProposal] = []
        self._completed: list[ImprovementProposal] = []
        self._total_generated = 0
        self._total_approved = 0
        self._total_denied = 0

    def generate(
        self,
        proposal_type: str,
        description: str,
        pattern_id: str = "",
        confidence: float = 0.0,
        provenance: list[str] | None = None,
        rollback_reference: str = "",
    ) -> ImprovementProposal | None:
        if proposal_type not in KNOWN_PROPOSAL_TYPES:
            return None

        if confidence < MIN_CONFIDENCE_FOR_PROPOSAL:
            return None

        if len(self._pending) >= MAX_PENDING_PROPOSALS:
            return None

        confidence = max(0.0, min(1.0, confidence))

        raw = f"{proposal_type}:{description}:{pattern_id}"
        proposal_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

        proposal = ImprovementProposal(
            proposal_type=proposal_type,
            description=description,
            pattern_id=pattern_id,
            confidence=confidence,
            provenance=provenance or [],
            rollback_reference=rollback_reference,
            proposal_hash=proposal_hash,
        )

        self._pending.append(proposal)
        self._total_generated += 1
        return proposal

    def approve(
        self,
        proposal_id: str,
        approved_by: str = "operator",
    ) -> ImprovementProposal | None:
        if approved_by != "operator":
            raise ValueError(
                f"Only operator can approve proposals. Got: {approved_by}"
            )

        for i, proposal in enumerate(self._pending):
            if proposal.proposal_id == proposal_id:
                if not proposal.provenance:
                    return None
                if not proposal.rollback_reference:
                    return None

                proposal.approved = True
                proposal.denied = False
                self._pending.pop(i)
                self._completed.append(proposal)
                self._total_approved += 1
                return proposal

        return None

    def deny(
        self,
        proposal_id: str,
        denied_by: str = "operator",
    ) -> ImprovementProposal | None:
        if denied_by != "operator":
            raise ValueError(
                f"Only operator can deny proposals. Got: {denied_by}"
            )

        for i, proposal in enumerate(self._pending):
            if proposal.proposal_id == proposal_id:
                proposal.approved = False
                proposal.denied = True
                self._pending.pop(i)
                self._completed.append(proposal)
                self._total_denied += 1
                return proposal

        return None

    def mark_applied(self, proposal_id: str) -> ImprovementProposal | None:
        for proposal in self._completed:
            if proposal.proposal_id == proposal_id and proposal.approved:
                proposal.applied_by_operator = True
                return proposal
        return None

    def get_pending(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._pending]

    def get_completed(self, limit: int = 20) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._completed[-limit:]]

    def get_proposals_by_type(
        self,
        proposal_type: str,
    ) -> list[dict[str, Any]]:
        all_proposals = self._pending + self._completed
        return [
            p.to_dict()
            for p in all_proposals
            if p.proposal_type == proposal_type
        ]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_generated": self._total_generated,
            "total_approved": self._total_approved,
            "total_denied": self._total_denied,
            "pending_count": len(self._pending),
            "completed_count": len(self._completed),
        }
