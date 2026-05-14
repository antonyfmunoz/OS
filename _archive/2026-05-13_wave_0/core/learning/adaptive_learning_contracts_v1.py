"""Adaptive Learning Contracts v1.

Data contracts for governed adaptive learning coordination:
  learning signals, outcome learning, feedback, pattern candidates,
  improvement proposals, governance, confidence, replay, corrections,
  policy/template/routing/knowledge learning candidates.

The learning layer may learn, score, compress, and propose.
It NEVER mutates canon, policy, templates, or routing directly.
The operator approves canonical change.

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

import enum
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class LearningLifecycleState(enum.Enum):
    OBSERVED = "observed"
    CANDIDATE = "candidate"
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    DENIED = "denied"
    APPLIED_BY_OPERATOR = "applied_by_operator"
    ARCHIVED = "archived"


class LearningEventType(enum.Enum):
    LEARNING_SIGNAL_OBSERVED = "learning_signal_observed"
    PATTERN_CANDIDATE_DETECTED = "pattern_candidate_detected"
    PROPOSAL_GENERATED = "proposal_generated"
    PROPOSAL_DENIED = "proposal_denied"
    PROPOSAL_APPROVED = "proposal_approved"
    LEARNING_BOUNDARY_DENIED = "learning_boundary_denied"
    LEARNING_REPLAY_VALIDATED = "learning_replay_validated"


class LearningSignalSource(enum.Enum):
    WORKFLOW_SUCCESS = "workflow_success"
    WORKFLOW_FAILURE = "workflow_failure"
    ACTION_DENIED = "action_denied"
    REPLAY_DIVERGENCE = "replay_divergence"
    RESILIENCE_EVENT = "resilience_event"
    SCALING_PRESSURE = "scaling_pressure"
    OPERATOR_CORRECTION = "operator_correction"
    RECONCILIATION_RESULT = "reconciliation_result"


class ProposalType(enum.Enum):
    POLICY_UPDATE_CANDIDATE = "policy_update_candidate"
    TEMPLATE_UPDATE_CANDIDATE = "template_update_candidate"
    ROUTING_UPDATE_CANDIDATE = "routing_update_candidate"
    ADAPTER_MATURITY_CANDIDATE = "adapter_maturity_candidate"
    KNOWLEDGE_PROMOTION_CANDIDATE = "knowledge_promotion_candidate"
    WORKFLOW_IMPROVEMENT_CANDIDATE = "workflow_improvement_candidate"
    RESILIENCE_RULE_CANDIDATE = "resilience_rule_candidate"
    SCALING_RULE_CANDIDATE = "scaling_rule_candidate"


class PatternType(enum.Enum):
    REPEATED_FAILURE = "repeated_failure"
    REPEATED_CORRECTION = "repeated_correction"
    REPEATED_DENIAL = "repeated_denial"
    RECURRING_SUCCESS_ROUTE = "recurring_success_route"
    RECURRING_RETRIEVAL_MISS = "recurring_retrieval_miss"
    RECURRING_WORKFLOW_BOTTLENECK = "recurring_workflow_bottleneck"
    RECURRING_ENVIRONMENT_INSTABILITY = "recurring_environment_instability"


@dataclass
class LearningSignal:
    signal_id: str = field(default_factory=lambda: _new_id("lsig"))
    source: str = ""
    content: str = ""
    severity: float = 0.0
    session_id: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id, "source": self.source,
            "content": self.content, "severity": self.severity,
            "session_id": self.session_id, "timestamp": self.timestamp,
        }


@dataclass
class OutcomeLearningState:
    outcome_id: str = field(default_factory=lambda: _new_id("olrn"))
    signal_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    denial_count: int = 0
    correction_count: int = 0
    outcome_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id, "signal_count": self.signal_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "denial_count": self.denial_count,
            "correction_count": self.correction_count,
            "outcome_hash": self.outcome_hash, "timestamp": self.timestamp,
        }


@dataclass
class FeedbackLearningState:
    feedback_id: str = field(default_factory=lambda: _new_id("flrn"))
    source: str = ""
    feedback_type: str = ""
    content: str = ""
    applied: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id, "source": self.source,
            "feedback_type": self.feedback_type, "content": self.content,
            "applied": self.applied, "timestamp": self.timestamp,
        }


@dataclass
class PatternCandidate:
    pattern_id: str = field(default_factory=lambda: _new_id("pcan"))
    pattern_type: str = ""
    description: str = ""
    occurrence_count: int = 0
    confidence: float = 0.0
    signal_ids: list[str] = field(default_factory=list)
    pattern_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id, "pattern_type": self.pattern_type,
            "description": self.description,
            "occurrence_count": self.occurrence_count,
            "confidence": self.confidence, "signal_ids": self.signal_ids,
            "pattern_hash": self.pattern_hash, "timestamp": self.timestamp,
        }


@dataclass
class ImprovementProposal:
    proposal_id: str = field(default_factory=lambda: _new_id("iprop"))
    proposal_type: str = ""
    description: str = ""
    pattern_id: str = ""
    confidence: float = 0.0
    provenance: list[str] = field(default_factory=list)
    rollback_reference: str = ""
    approved: bool = False
    denied: bool = False
    applied_by_operator: bool = False
    proposal_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type,
            "description": self.description, "pattern_id": self.pattern_id,
            "confidence": self.confidence, "provenance": self.provenance,
            "rollback_reference": self.rollback_reference,
            "approved": self.approved, "denied": self.denied,
            "applied_by_operator": self.applied_by_operator,
            "proposal_hash": self.proposal_hash, "timestamp": self.timestamp,
        }


@dataclass
class LearningReceipt:
    receipt_id: str = field(default_factory=lambda: _new_id("lrcpt"))
    operation: str = ""
    proposal_id: str = ""
    from_state: str = ""
    to_state: str = ""
    approved_by: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id, "operation": self.operation,
            "proposal_id": self.proposal_id, "from_state": self.from_state,
            "to_state": self.to_state, "approved_by": self.approved_by,
            "timestamp": self.timestamp,
        }


@dataclass
class LearningConfidenceState:
    confidence_id: str = field(default_factory=lambda: _new_id("lconf"))
    pattern_id: str = ""
    confidence: float = 0.0
    evidence_count: int = 0
    last_updated: str = field(default_factory=_now_iso)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence_id": self.confidence_id,
            "pattern_id": self.pattern_id, "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "last_updated": self.last_updated, "timestamp": self.timestamp,
        }


@dataclass
class LearningBoundaryState:
    boundary_id: str = field(default_factory=lambda: _new_id("lbnd"))
    action: str = ""
    denied: bool = False
    reason: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id, "action": self.action,
            "denied": self.denied, "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class LearningReplayState:
    replay_id: str = field(default_factory=lambda: _new_id("lrply"))
    check_name: str = ""
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id, "check_name": self.check_name,
            "input_hash": self.input_hash, "output_hash": self.output_hash,
            "deterministic": self.deterministic, "timestamp": self.timestamp,
        }


@dataclass
class OperatorCorrectionState:
    correction_id: str = field(default_factory=lambda: _new_id("ocorr"))
    original_action: str = ""
    corrected_action: str = ""
    reason: str = ""
    corrected_by: str = "operator"
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correction_id": self.correction_id,
            "original_action": self.original_action,
            "corrected_action": self.corrected_action,
            "reason": self.reason, "corrected_by": self.corrected_by,
            "timestamp": self.timestamp,
        }


@dataclass
class PolicyLearningCandidate:
    candidate_id: str = field(default_factory=lambda: _new_id("plcan"))
    policy_name: str = ""
    proposed_change: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "policy_name": self.policy_name,
            "proposed_change": self.proposed_change,
            "evidence": self.evidence, "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class TemplateLearningCandidate:
    candidate_id: str = field(default_factory=lambda: _new_id("tlcan"))
    template_name: str = ""
    proposed_change: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "template_name": self.template_name,
            "proposed_change": self.proposed_change,
            "evidence": self.evidence, "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class RoutingLearningCandidate:
    candidate_id: str = field(default_factory=lambda: _new_id("rlcan"))
    route_name: str = ""
    proposed_change: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "route_name": self.route_name,
            "proposed_change": self.proposed_change,
            "evidence": self.evidence, "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class KnowledgeLearningCandidate:
    candidate_id: str = field(default_factory=lambda: _new_id("klcan"))
    concept: str = ""
    proposed_change: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id, "concept": self.concept,
            "proposed_change": self.proposed_change,
            "evidence": self.evidence, "confidence": self.confidence,
            "timestamp": self.timestamp,
        }
