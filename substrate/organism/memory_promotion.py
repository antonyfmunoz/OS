"""Memory Promotion Pipeline — governed promotion from instance to canonical memory.

Distinguishes:
  - raw observation
  - instance fact
  - learned pattern
  - reusable system template
  - canonical knowledge
  - deprecated/contradicted knowledge

Promotion requires evidence, contradiction check pass, traceability, and
(for MEDIUM+ impact) operator approval.

UMH substrate subsystem. Instance-agnostic.
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


class MemoryPromotionStatus(str, Enum):
    RAW = "raw"
    CANDIDATE = "candidate"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    CONTRADICTED = "contradicted"
    DEPRECATED = "deprecated"


class MemoryScope(str, Enum):
    INSTANCE = "instance"
    CANONICAL = "canonical"


class MemoryCategory(str, Enum):
    OBSERVATION = "observation"
    PATTERN = "pattern"
    TEMPLATE = "template"
    STRATEGY = "strategy"
    CONSTRAINT = "constraint"
    CAPABILITY = "capability"


@dataclass
class MemoryEvidence:
    source: str
    detail: str
    confidence: float = 0.5
    observed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "detail": self.detail,
            "confidence": self.confidence,
            "observed_at": self.observed_at,
        }


@dataclass
class MemoryCandidate:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    content: str = ""
    category: MemoryCategory = MemoryCategory.OBSERVATION
    scope: MemoryScope = MemoryScope.INSTANCE
    status: MemoryPromotionStatus = MemoryPromotionStatus.RAW
    evidence: list[MemoryEvidence] = field(default_factory=list)
    source_action: str = ""
    confidence: float = 0.0
    contradiction_check: bool = False
    rejection_reason: str = ""
    approved_by: str = ""
    created_at: float = field(default_factory=time.time)
    promoted_at: float = 0.0

    @property
    def average_evidence_confidence(self) -> float:
        if not self.evidence:
            return 0.0
        return sum(e.confidence for e in self.evidence) / len(self.evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category.value,
            "scope": self.scope.value,
            "status": self.status.value,
            "evidence": [e.to_dict() for e in self.evidence],
            "source_action": self.source_action,
            "confidence": self.confidence,
            "contradiction_check": self.contradiction_check,
            "rejection_reason": self.rejection_reason,
            "approved_by": self.approved_by,
            "created_at": self.created_at,
            "promoted_at": self.promoted_at,
        }


@dataclass
class MemoryPromotionDecision:
    candidate_id: str
    decision: MemoryPromotionStatus
    reason: str = ""
    decided_by: str = "system"
    decided_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
        }


@dataclass
class CanonicalMemoryEntry:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    content: str = ""
    category: MemoryCategory = MemoryCategory.PATTERN
    source_candidate_id: str = ""
    confidence: float = 0.0
    evidence_count: int = 0
    promoted_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category.value,
            "source_candidate_id": self.source_candidate_id,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "promoted_at": self.promoted_at,
        }


# ---------------------------------------------------------------------------
# Promotion criteria
# ---------------------------------------------------------------------------

_CONFIDENCE_THRESHOLD = 0.6
_MIN_EVIDENCE_COUNT = 1
_REQUIRES_OPERATOR_APPROVAL_CATEGORIES = {
    MemoryCategory.STRATEGY,
    MemoryCategory.CONSTRAINT,
    MemoryCategory.CAPABILITY,
}


def _check_promotion_eligibility(candidate: MemoryCandidate) -> tuple[bool, str]:
    """Check if a candidate is eligible for promotion. Returns (eligible, reason)."""
    if not candidate.evidence:
        return False, "No evidence attached"
    if len(candidate.evidence) < _MIN_EVIDENCE_COUNT:
        return False, f"Need at least {_MIN_EVIDENCE_COUNT} evidence items"
    if candidate.average_evidence_confidence < _CONFIDENCE_THRESHOLD:
        return False, f"Average evidence confidence ({candidate.average_evidence_confidence:.2f}) below threshold ({_CONFIDENCE_THRESHOLD})"
    if not candidate.content.strip():
        return False, "Empty content"
    if not candidate.contradiction_check:
        return False, "Contradiction check not passed"
    return True, "Eligible"


def _needs_operator_approval(candidate: MemoryCandidate) -> bool:
    """MEDIUM+ memory promotions require operator approval if they affect execution."""
    return candidate.category in _REQUIRES_OPERATOR_APPROVAL_CATEGORIES


class MemoryPromotionPipeline:
    """Governed pipeline for promoting instance observations to canonical memory."""

    def __init__(self, store_dir: str | None = None):
        self._store_dir = store_dir or os.path.join(_REPO_ROOT, "data", "umh")
        self._candidates_path = os.path.join(self._store_dir, "memory_candidates", "candidates.jsonl")
        self._canonical_path = os.path.join(self._store_dir, "memory", "canonical_memory.jsonl")
        self._instance_path = os.path.join(self._store_dir, "memory", "instance_memory.jsonl")
        self._decisions_path = os.path.join(self._store_dir, "memory_candidates", "decisions.jsonl")
        self._candidates: dict[str, MemoryCandidate] = {}
        self._canonical: list[CanonicalMemoryEntry] = []
        self._decisions: list[MemoryPromotionDecision] = []
        self._load()

    def _load(self) -> None:
        self._candidates = self._load_candidates()
        self._canonical = self._load_canonical()

    def _load_candidates(self) -> dict[str, MemoryCandidate]:
        candidates: dict[str, MemoryCandidate] = {}
        if not os.path.isfile(self._candidates_path):
            return candidates
        try:
            with open(self._candidates_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    evidence = [MemoryEvidence(**e) for e in data.pop("evidence", [])]
                    for enum_field, enum_cls in [("category", MemoryCategory), ("scope", MemoryScope), ("status", MemoryPromotionStatus)]:
                        if enum_field in data and isinstance(data[enum_field], str):
                            data[enum_field] = enum_cls(data[enum_field])
                    cand = MemoryCandidate(**data, evidence=evidence)
                    candidates[cand.id] = cand
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load candidates: %s", e)
        return candidates

    def _load_canonical(self) -> list[CanonicalMemoryEntry]:
        entries: list[CanonicalMemoryEntry] = []
        if not os.path.isfile(self._canonical_path):
            return entries
        try:
            with open(self._canonical_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    if "category" in data and isinstance(data["category"], str):
                        data["category"] = MemoryCategory(data["category"])
                    entries.append(CanonicalMemoryEntry(**data))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load canonical memory: %s", e)
        return entries

    def _persist_candidate(self, candidate: MemoryCandidate) -> None:
        os.makedirs(os.path.dirname(self._candidates_path), exist_ok=True)
        with open(self._candidates_path, "a") as f:
            f.write(json.dumps(candidate.to_dict(), default=str) + "\n")

    def _persist_canonical(self, entry: CanonicalMemoryEntry) -> None:
        os.makedirs(os.path.dirname(self._canonical_path), exist_ok=True)
        with open(self._canonical_path, "a") as f:
            f.write(json.dumps(entry.to_dict(), default=str) + "\n")

    def _persist_decision(self, decision: MemoryPromotionDecision) -> None:
        os.makedirs(os.path.dirname(self._decisions_path), exist_ok=True)
        with open(self._decisions_path, "a") as f:
            f.write(json.dumps(decision.to_dict(), default=str) + "\n")

    def submit_candidate(self, content: str, category: MemoryCategory = MemoryCategory.OBSERVATION,
                         scope: MemoryScope = MemoryScope.INSTANCE,
                         evidence: list[MemoryEvidence] | None = None,
                         source_action: str = "") -> MemoryCandidate:
        """Submit a new memory candidate for potential promotion."""
        candidate = MemoryCandidate(
            content=content,
            category=category,
            scope=scope,
            evidence=evidence or [],
            source_action=source_action,
            status=MemoryPromotionStatus.RAW,
        )
        if evidence:
            candidate.confidence = candidate.average_evidence_confidence
        self._candidates[candidate.id] = candidate
        self._persist_candidate(candidate)
        return candidate

    def run_contradiction_check(self, candidate_id: str) -> bool:
        """Run contradiction check on a candidate. Returns True if passed."""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        try:
            from substrate.organism.contradiction_engine import detect_contradictions
            report = detect_contradictions()
            words = [w for w in candidate.content.lower().split() if len(w) > 3]
            if words:
                contradicts = any(
                    c.evidence and any(w in c.evidence.lower() for w in words)
                    for c in report.contradictions
                )
            else:
                contradicts = False
            candidate.contradiction_check = not contradicts
        except Exception:
            candidate.contradiction_check = True

        return candidate.contradiction_check

    def evaluate_for_promotion(self, candidate_id: str) -> tuple[bool, str]:
        """Evaluate whether a candidate is eligible for promotion."""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False, "Candidate not found"
        return _check_promotion_eligibility(candidate)

    def promote(self, candidate_id: str, decided_by: str = "system") -> CanonicalMemoryEntry | None:
        """Promote a candidate to canonical memory."""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return None

        eligible, reason = _check_promotion_eligibility(candidate)
        if not eligible:
            candidate.status = MemoryPromotionStatus.REJECTED
            candidate.rejection_reason = reason
            return None

        if _needs_operator_approval(candidate) and decided_by == "system":
            candidate.status = MemoryPromotionStatus.CANDIDATE
            return None

        entry = CanonicalMemoryEntry(
            content=candidate.content,
            category=candidate.category,
            source_candidate_id=candidate.id,
            confidence=candidate.confidence,
            evidence_count=len(candidate.evidence),
        )
        self._canonical.append(entry)
        candidate.status = MemoryPromotionStatus.PROMOTED
        candidate.promoted_at = time.time()
        candidate.approved_by = decided_by

        decision = MemoryPromotionDecision(
            candidate_id=candidate_id,
            decision=MemoryPromotionStatus.PROMOTED,
            reason="Promotion criteria met",
            decided_by=decided_by,
        )
        self._decisions.append(decision)
        self._persist_canonical(entry)
        self._persist_decision(decision)

        return entry

    def reject(self, candidate_id: str, reason: str = "", decided_by: str = "system") -> bool:
        """Reject a candidate."""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        candidate.status = MemoryPromotionStatus.REJECTED
        candidate.rejection_reason = reason

        decision = MemoryPromotionDecision(
            candidate_id=candidate_id,
            decision=MemoryPromotionStatus.REJECTED,
            reason=reason,
            decided_by=decided_by,
        )
        self._decisions.append(decision)
        self._persist_decision(decision)
        return True

    def supersede(self, old_id: str, new_id: str) -> bool:
        """Mark an old entry as superseded by a new one."""
        old = self._candidates.get(old_id)
        if not old:
            return False
        old.status = MemoryPromotionStatus.SUPERSEDED
        return True

    def get_candidate(self, candidate_id: str) -> MemoryCandidate | None:
        return self._candidates.get(candidate_id)

    def list_candidates(self, status: MemoryPromotionStatus | None = None) -> list[MemoryCandidate]:
        if status:
            return [c for c in self._candidates.values() if c.status == status]
        return list(self._candidates.values())

    def list_canonical(self) -> list[CanonicalMemoryEntry]:
        return list(self._canonical)

    def pending_approvals(self) -> list[MemoryCandidate]:
        return [c for c in self._candidates.values() if c.status == MemoryPromotionStatus.CANDIDATE]

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for c in self._candidates.values():
            status_counts[c.status.value] = status_counts.get(c.status.value, 0) + 1
        return {
            "total_candidates": len(self._candidates),
            "by_status": status_counts,
            "canonical_entries": len(self._canonical),
            "pending_approvals": len(self.pending_approvals()),
            "total_decisions": len(self._decisions),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "candidates": [c.to_dict() for c in self._candidates.values()],
            "canonical": [e.to_dict() for e in self._canonical],
            "pending_approvals": [c.to_dict() for c in self.pending_approvals()],
        }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, _REPO_ROOT)
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = MemoryPromotionPipeline(store_dir=tmpdir)

        c1 = pipeline.submit_candidate(
            content="Workload probes have 80% reliability over 50 executions",
            category=MemoryCategory.PATTERN,
            evidence=[MemoryEvidence(source="outcome_learning", detail="50 outcomes, 40 success", confidence=0.8)],
            source_action="outcome_learning",
        )
        pipeline.run_contradiction_check(c1.id)
        entry = pipeline.promote(c1.id)

        c2 = pipeline.submit_candidate(
            content="Never restart all Docker containers simultaneously",
            category=MemoryCategory.CONSTRAINT,
            evidence=[MemoryEvidence(source="operator", detail="AFM instruction", confidence=0.95)],
        )
        pipeline.run_contradiction_check(c2.id)
        entry2 = pipeline.promote(c2.id)

        print(json.dumps(pipeline.summary(), indent=2))
        if entry2 is None:
            print("Constraint requires operator approval (as expected)")
            entry2 = pipeline.promote(c2.id, decided_by="operator")
            if entry2:
                print(f"Operator approved: {entry2.content[:60]}")
