"""Phase 82 memory discipline views — read-only view models for memory state.

UI-safe, typed, no secrets. No execution. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.memory.discipline import (
    MemoryRecord,
    MemoryWritePolicy,
    build_default_memory_write_policy,
    classify_memory_candidate,
    is_memory_promotable,
)


@dataclass
class MemoryCandidateDisciplineView:
    candidate_id: str
    memory_type: str = ""
    confidence: float = 0.0
    has_evidence: bool = False
    has_content: bool = False
    promotable: bool = False
    status: str = "candidate"
    reason: str = ""
    content_preview: str = ""
    validation_issues: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "memory_type": self.memory_type,
            "confidence": self.confidence,
            "has_evidence": self.has_evidence,
            "has_content": self.has_content,
            "promotable": self.promotable,
            "status": self.status,
            "reason": self.reason,
            "content_preview": self.content_preview,
            "validation_issues": self.validation_issues,
            "metadata": self.metadata,
        }


@dataclass
class MemoryDisciplineHealthView:
    generated_at: str = ""
    total_candidates: int = 0
    total_records: int = 0
    promotable_count: int = 0
    not_promotable_count: int = 0
    candidates_by_type: dict[str, int] = field(default_factory=dict)
    records_by_status: dict[str, int] = field(default_factory=dict)
    auto_promotion_enabled: bool = False
    min_confidence: float = 0.2
    policy_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_candidates": self.total_candidates,
            "total_records": self.total_records,
            "promotable_count": self.promotable_count,
            "not_promotable_count": self.not_promotable_count,
            "candidates_by_type": self.candidates_by_type,
            "records_by_status": self.records_by_status,
            "auto_promotion_enabled": self.auto_promotion_enabled,
            "min_confidence": self.min_confidence,
            "policy_summary": self.policy_summary,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def build_candidate_discipline_view(
    candidate: Any,
    policy: MemoryWritePolicy | None = None,
) -> MemoryCandidateDisciplineView:
    if policy is None:
        policy = build_default_memory_write_policy()

    cid = getattr(candidate, "candidate_id", "")
    content = getattr(candidate, "content", "")
    conf = getattr(candidate, "confidence", 0.0)
    evidence = list(getattr(candidate, "evidence", []))
    reason = getattr(candidate, "reason", "")
    mt = classify_memory_candidate(candidate)
    promotable = is_memory_promotable(candidate, policy)

    issues: list[str] = []
    if not content:
        issues.append("No content")
    if conf < policy.min_confidence:
        issues.append(f"Confidence {conf} below {policy.min_confidence}")
    if policy.requires_evidence and not evidence:
        issues.append("No evidence")

    preview = content[:120] + "..." if len(content) > 120 else content

    return MemoryCandidateDisciplineView(
        candidate_id=cid,
        memory_type=mt.value,
        confidence=conf,
        has_evidence=bool(evidence),
        has_content=bool(content),
        promotable=promotable,
        status="promotable" if promotable else "not_promotable",
        reason=reason,
        content_preview=preview,
        validation_issues=issues,
    )


def build_memory_discipline_health_view(
    candidates: list[Any] | None = None,
    records: list[MemoryRecord] | None = None,
    policy: MemoryWritePolicy | None = None,
) -> MemoryDisciplineHealthView:
    if policy is None:
        policy = build_default_memory_write_policy()
    if candidates is None:
        candidates = []
    if records is None:
        records = []

    by_type: dict[str, int] = {}
    promotable = 0
    not_promotable = 0

    for c in candidates:
        mt = classify_memory_candidate(c)
        mv = mt.value
        by_type[mv] = by_type.get(mv, 0) + 1
        if is_memory_promotable(c, policy):
            promotable += 1
        else:
            not_promotable += 1

    by_status: dict[str, int] = {}
    for r in records:
        sv = r.status.value
        by_status[sv] = by_status.get(sv, 0) + 1

    warnings: list[str] = []
    if policy.allow_auto_promotion:
        warnings.append("Auto-promotion enabled — Phase 82 disables this by default")

    return MemoryDisciplineHealthView(
        generated_at=_iso_now(),
        total_candidates=len(candidates),
        total_records=len(records),
        promotable_count=promotable,
        not_promotable_count=not_promotable,
        candidates_by_type=by_type,
        records_by_status=by_status,
        auto_promotion_enabled=policy.allow_auto_promotion,
        min_confidence=policy.min_confidence,
        policy_summary=policy.to_dict(),
        warnings=warnings,
    )
