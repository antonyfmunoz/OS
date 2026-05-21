"""Phase 82 memory discipline — what counts as memory vs traces/feedback/metadata.

Memory is structured durable state governed by type, scope, source,
confidence, ownership, and promotion rules.

No execution. No mutation of external state. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


class MemoryRecordType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    BEHAVIORAL = "behavioral"
    PREFERENCE = "preference"
    ERROR_PATTERN = "error_pattern"
    TOOL_OBSERVATION = "tool_observation"
    WORLD_OBSERVATION = "world_observation"
    SYSTEM_OBSERVATION = "system_observation"
    UNKNOWN = "unknown"


def normalize_memory_record_type(value: str) -> MemoryRecordType:
    v = value.strip().lower()
    for m in MemoryRecordType:
        if m.value == v:
            return m
    return MemoryRecordType.UNKNOWN


class MemoryScope(str, Enum):
    USER = "user"
    SESSION = "session"
    SYSTEM = "system"
    DOMAIN = "domain"
    WORKSPACE = "workspace"
    UNKNOWN = "unknown"


def normalize_memory_scope(value: str) -> MemoryScope:
    v = value.strip().lower()
    for m in MemoryScope:
        if m.value == v:
            return m
    return MemoryScope.UNKNOWN


class MemoryStatus(str, Enum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


def normalize_memory_status(value: str) -> MemoryStatus:
    v = value.strip().lower()
    for m in MemoryStatus:
        if m.value == v:
            return m
    return MemoryStatus.UNKNOWN


@dataclass
class MemoryWritePolicy:
    allow_auto_promotion: bool = False
    require_source: bool = True
    require_confidence: bool = True
    min_confidence: float = 0.2
    allowed_sources: list[str] = field(
        default_factory=lambda: [
            "system",
            "user",
            "feedback_loop",
            "execution",
            "observability",
        ]
    )
    requires_user_scope: bool = False
    requires_evidence: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_auto_promotion": self.allow_auto_promotion,
            "require_source": self.require_source,
            "require_confidence": self.require_confidence,
            "min_confidence": self.min_confidence,
            "allowed_sources": self.allowed_sources,
            "requires_user_scope": self.requires_user_scope,
            "requires_evidence": self.requires_evidence,
            "metadata": self.metadata,
        }


def build_default_memory_write_policy() -> MemoryWritePolicy:
    return MemoryWritePolicy()


@dataclass
class MemoryRecord:
    memory_id: str
    user_id: str = ""
    session_id: str = ""
    memory_type: MemoryRecordType = MemoryRecordType.UNKNOWN
    scope: MemoryScope = MemoryScope.UNKNOWN
    status: MemoryStatus = MemoryStatus.CANDIDATE
    content: str = ""
    source: str = ""
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    expires_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "memory_type": self.memory_type.value,
            "scope": self.scope.value,
            "status": self.status.value,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryRecord:
        return cls(
            memory_id=data.get("memory_id", f"mem_{uuid.uuid4().hex[:12]}"),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            memory_type=normalize_memory_record_type(data.get("memory_type", "unknown")),
            scope=normalize_memory_scope(data.get("scope", "unknown")),
            status=normalize_memory_status(data.get("status", "candidate")),
            content=data.get("content", ""),
            source=data.get("source", ""),
            confidence=clamp_confidence(data.get("confidence", 0.5)),
            evidence=data.get("evidence", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            expires_at=data.get("expires_at", ""),
            metadata=data.get("metadata", {}),
        )


_CANDIDATE_TYPE_MAP: dict[str, MemoryRecordType] = {
    "episodic": MemoryRecordType.EPISODIC,
    "procedural": MemoryRecordType.PROCEDURAL,
    "behavioral": MemoryRecordType.BEHAVIORAL,
    "trace_summary": MemoryRecordType.EPISODIC,
    "user_preference": MemoryRecordType.PREFERENCE,
    "error_pattern": MemoryRecordType.ERROR_PATTERN,
    "capability_observation": MemoryRecordType.TOOL_OBSERVATION,
    "adapter_observation": MemoryRecordType.TOOL_OBSERVATION,
}


def classify_memory_candidate(candidate: Any) -> MemoryRecordType:
    mt = getattr(candidate, "memory_type", None)
    if mt is None:
        return MemoryRecordType.UNKNOWN
    mt_str = mt.value if hasattr(mt, "value") else str(mt).lower()
    return _CANDIDATE_TYPE_MAP.get(mt_str, MemoryRecordType.UNKNOWN)


def create_memory_record_from_candidate(
    candidate: Any,
    status: MemoryStatus = MemoryStatus.NEEDS_REVIEW,
) -> MemoryRecord:
    now = _iso_now()
    cid = getattr(candidate, "candidate_id", "")
    mt = classify_memory_candidate(candidate)
    content = getattr(candidate, "content", "")
    conf = clamp_confidence(getattr(candidate, "confidence", 0.5))
    evidence = list(getattr(candidate, "evidence", []))
    user_id = getattr(candidate, "user_id", "")
    session_id = getattr(candidate, "session_id", "")
    reason = getattr(candidate, "reason", "")

    return MemoryRecord(
        memory_id=f"mem_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        session_id=session_id,
        memory_type=mt,
        scope=MemoryScope.USER if user_id else MemoryScope.SYSTEM,
        status=status,
        content=content,
        source="feedback_loop",
        confidence=conf,
        evidence=evidence,
        created_at=now,
        metadata={"candidate_id": cid, "reason": reason},
    )


def is_memory_promotable(
    candidate: Any,
    policy: MemoryWritePolicy | None = None,
) -> bool:
    if policy is None:
        policy = build_default_memory_write_policy()
    if policy.allow_auto_promotion:
        return False
    conf = getattr(candidate, "confidence", 0.0)
    if conf < policy.min_confidence:
        return False
    content = getattr(candidate, "content", "")
    if not content:
        return False
    evidence = getattr(candidate, "evidence", [])
    if policy.requires_evidence and not evidence:
        return False
    return True


def validate_memory_record(
    record: MemoryRecord,
    policy: MemoryWritePolicy | None = None,
) -> list[str]:
    if policy is None:
        policy = build_default_memory_write_policy()
    issues: list[str] = []

    if policy.require_source and not record.source:
        issues.append("Memory record missing source")
    if policy.require_confidence and record.confidence < policy.min_confidence:
        issues.append(f"Confidence {record.confidence} below minimum {policy.min_confidence}")
    if policy.requires_evidence and not record.evidence:
        issues.append("Memory record missing evidence")
    if record.status == MemoryStatus.PROMOTED and not policy.allow_auto_promotion:
        issues.append("Auto-promotion not allowed by policy")
    if not record.content:
        issues.append("Memory record has no content")

    return issues


def explain_memory_write_decision(
    candidate: Any,
    policy: MemoryWritePolicy | None = None,
) -> dict[str, Any]:
    if policy is None:
        policy = build_default_memory_write_policy()

    mt = classify_memory_candidate(candidate)
    promotable = is_memory_promotable(candidate, policy)
    conf = clamp_confidence(getattr(candidate, "confidence", 0.0))
    has_evidence = bool(getattr(candidate, "evidence", []))
    has_content = bool(getattr(candidate, "content", ""))

    reasons: list[str] = []
    if not has_content:
        reasons.append("No content")
    if conf < policy.min_confidence:
        reasons.append(f"Confidence {conf} below {policy.min_confidence}")
    if policy.requires_evidence and not has_evidence:
        reasons.append("No evidence")
    if not policy.allow_auto_promotion:
        reasons.append("Auto-promotion disabled")

    return {
        "memory_type": mt.value,
        "promotable": promotable,
        "confidence": conf,
        "has_evidence": has_evidence,
        "has_content": has_content,
        "auto_promotion_enabled": policy.allow_auto_promotion,
        "status": "needs_review" if promotable else "not_promotable",
        "reasons": reasons,
    }
