"""Canonical Update Proposal — proposed changes to canonical truth.

A CanonicalUpdateProposal captures a recommended change to UMH's
canonical understanding: promoting a claim, deprecating a source,
updating an entity, or creating a work packet. All proposals require
operator approval before application.

Phase 13.3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_PROPOSALS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "canonical_update_proposals.jsonl"
)


class ProposalType(str, Enum):
    PROMOTE_CLAIM = "promote_claim"
    DEPRECATE_CLAIM = "deprecate_claim"
    SUPERSEDE_CLAIM = "supersede_claim"
    MERGE_DUPLICATES = "merge_duplicates"
    UPDATE_ENTITY = "update_entity"
    UPDATE_ROADMAP = "update_roadmap"
    UPDATE_WORK_PACKET = "update_work_packet"
    UPDATE_KNOWLEDGE_MODEL = "update_knowledge_model"
    CREATE_WORK_PACKET = "create_work_packet"
    ASK_OPERATOR_QUESTION = "ask_operator_question"
    MARK_SOURCE_DEPRECATED = "mark_source_deprecated"


class ProposalStatus(str, Enum):
    DRAFTED = "drafted"
    PENDING_OPERATOR_REVIEW = "pending_operator_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    APPLIED = "applied"
    BLOCKED = "blocked"


@dataclass
class CanonicalUpdateProposal:
    proposal_id: str = ""
    report_id: str = ""
    proposal_type: str = ProposalType.PROMOTE_CLAIM.value
    title: str = ""
    description: str = ""
    current_state: str = ""
    proposed_state: str = ""
    source_ids: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    risk_class: str = "low"
    affected_entities: list[str] = field(default_factory=list)
    affected_work_packets: list[str] = field(default_factory=list)
    affected_roadmap_phases: list[str] = field(default_factory=list)
    affected_knowledge_models: list[str] = field(default_factory=list)
    propagation_preview_id: str = ""
    approval_required: bool = True
    operator_decision: str = ""
    status: str = ProposalStatus.DRAFTED.value
    created_at: float = 0.0
    decided_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.proposal_id:
            self.proposal_id = f"prop-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "report_id": self.report_id,
            "proposal_type": self.proposal_type,
            "title": self.title,
            "description": self.description,
            "current_state": self.current_state,
            "proposed_state": self.proposed_state,
            "source_ids": self.source_ids,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "risk_class": self.risk_class,
            "affected_entities": self.affected_entities,
            "affected_work_packets": self.affected_work_packets,
            "affected_roadmap_phases": self.affected_roadmap_phases,
            "affected_knowledge_models": self.affected_knowledge_models,
            "propagation_preview_id": self.propagation_preview_id,
            "approval_required": self.approval_required,
            "operator_decision": self.operator_decision,
            "status": self.status,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CanonicalUpdateProposal:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ProposalStore:
    def __init__(self, path: str | None = None) -> None:
        self._path = path or _PROPOSALS_PATH
        self._proposals: dict[str, CanonicalUpdateProposal] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    prop = CanonicalUpdateProposal.from_dict(d)
                    self._proposals[prop.proposal_id] = prop
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping malformed proposal line")

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for prop in self._proposals.values():
                f.write(json.dumps(prop.to_dict(), default=str) + "\n")

    def save_proposal(self, proposal: CanonicalUpdateProposal) -> CanonicalUpdateProposal:
        self._proposals[proposal.proposal_id] = proposal
        self._save()
        return proposal

    def get_proposal(self, proposal_id: str) -> CanonicalUpdateProposal | None:
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        report_id: str | None = None,
        status: str | None = None,
        proposal_type: str | None = None,
    ) -> list[CanonicalUpdateProposal]:
        result = list(self._proposals.values())
        if report_id:
            result = [p for p in result if p.report_id == report_id]
        if status:
            result = [p for p in result if p.status == status]
        if proposal_type:
            result = [p for p in result if p.proposal_type == proposal_type]
        return result

    def approve(self, proposal_id: str, decision: str = "approved") -> bool:
        prop = self._proposals.get(proposal_id)
        if not prop:
            return False
        prop.status = ProposalStatus.APPROVED.value
        prop.operator_decision = decision
        prop.decided_at = time.time()
        self._save()
        return True

    def reject(self, proposal_id: str, decision: str = "rejected") -> bool:
        prop = self._proposals.get(proposal_id)
        if not prop:
            return False
        prop.status = ProposalStatus.REJECTED.value
        prop.operator_decision = decision
        prop.decided_at = time.time()
        self._save()
        return True

    def count(self) -> int:
        return len(self._proposals)

    def pending_count(self) -> int:
        return sum(
            1 for p in self._proposals.values()
            if p.status == ProposalStatus.PENDING_OPERATOR_REVIEW.value
        )
