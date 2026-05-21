"""Phase 82 memory promotion policy — explicit future promotion without auto-promotion.

Advisory only. No writes. No execution. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.memory.discipline import (
    MemoryWritePolicy,
    build_default_memory_write_policy,
    clamp_confidence,
)


class PromotionDecisionStatus(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass
class MemoryPromotionDecision:
    decision_id: str
    candidate_id: str = ""
    user_id: str = ""
    status: PromotionDecisionStatus = PromotionDecisionStatus.UNKNOWN
    target_memory_type: str = ""
    reason: str = ""
    confidence: float = 0.0
    required_authority: str = ""
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "candidate_id": self.candidate_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "target_memory_type": self.target_memory_type,
            "reason": self.reason,
            "confidence": self.confidence,
            "required_authority": self.required_authority,
            "evidence": self.evidence,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryPromotionDecision:
        st = data.get("status", "unknown")
        status = PromotionDecisionStatus.UNKNOWN
        for m in PromotionDecisionStatus:
            if m.value == st:
                status = m
                break
        return cls(
            decision_id=data.get("decision_id", f"mpd_{uuid.uuid4().hex[:10]}"),
            candidate_id=data.get("candidate_id", ""),
            user_id=data.get("user_id", ""),
            status=status,
            target_memory_type=data.get("target_memory_type", ""),
            reason=data.get("reason", ""),
            confidence=clamp_confidence(data.get("confidence", 0.0)),
            required_authority=data.get("required_authority", ""),
            evidence=data.get("evidence", []),
            warnings=data.get("warnings", []),
            metadata=data.get("metadata", {}),
        )


def _decision_id() -> str:
    return f"mpd_{uuid.uuid4().hex[:10]}"


def evaluate_memory_candidate_for_promotion(
    candidate: Any,
    policy: MemoryWritePolicy | None = None,
) -> MemoryPromotionDecision:
    if policy is None:
        policy = build_default_memory_write_policy()

    cid = getattr(candidate, "candidate_id", "")
    uid = getattr(candidate, "user_id", "")
    conf = clamp_confidence(getattr(candidate, "confidence", 0.0))
    evidence = list(getattr(candidate, "evidence", []))
    content = getattr(candidate, "content", "")

    if not policy.allow_auto_promotion:
        return MemoryPromotionDecision(
            decision_id=_decision_id(),
            candidate_id=cid,
            user_id=uid,
            status=PromotionDecisionStatus.DISABLED,
            reason="Auto-promotion disabled by policy",
            confidence=conf,
            evidence=evidence,
            warnings=["Promotion requires future promotion engine"],
        )

    if not evidence:
        return MemoryPromotionDecision(
            decision_id=_decision_id(),
            candidate_id=cid,
            user_id=uid,
            status=PromotionDecisionStatus.INSUFFICIENT_EVIDENCE,
            reason="No evidence provided",
            confidence=conf,
        )

    if conf < policy.min_confidence:
        return MemoryPromotionDecision(
            decision_id=_decision_id(),
            candidate_id=cid,
            user_id=uid,
            status=PromotionDecisionStatus.INSUFFICIENT_EVIDENCE,
            reason=f"Confidence {conf} below minimum {policy.min_confidence}",
            confidence=conf,
            evidence=evidence,
        )

    if not content:
        return MemoryPromotionDecision(
            decision_id=_decision_id(),
            candidate_id=cid,
            user_id=uid,
            status=PromotionDecisionStatus.DENIED,
            reason="No content to promote",
            confidence=conf,
            evidence=evidence,
        )

    return MemoryPromotionDecision(
        decision_id=_decision_id(),
        candidate_id=cid,
        user_id=uid,
        status=PromotionDecisionStatus.NEEDS_REVIEW,
        reason="Candidate meets minimum criteria but requires human review",
        confidence=conf,
        evidence=evidence,
        required_authority="human_review",
    )
