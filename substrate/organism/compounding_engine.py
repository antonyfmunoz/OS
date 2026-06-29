"""Capability Compounding Engine — turn internal learning into leverage.

Answers operator questions #9 and #13:
  "What did we learn?" and "What should I do next?"

Detects promotion candidates across 4 tiers:
  Outcome → Insight → Capability → Operationalization → Infrastructure

Every promotion requires operator approval (Human Supremacy invariant).
All scoring is deterministic — zero LLM calls.

Composes (does not replace):
  - OutcomeLearningLoop — outcomes → insights
  - CapabilityRuntime (Gate 5) — capability registry
  - OperationalizationRuntime (Gate 6) — operationalization registry
  - InfrastructureRuntime (Gate 7) — infrastructure registry
  - ExecutionGraph (Gate 8) — lineage validation
  - TemplateRegistry — template success rates
  - MemoryPromotion — evidence-based promotion
  - AgentCapabilityModel — per-agent reliability

Gate 9 — Compounding Engine. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_ENGINE_DIR = os.path.join(_REPO_ROOT, "data", "umh", "compounding")
_CANDIDATES_PATH = os.path.join(_ENGINE_DIR, "candidates.jsonl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PromotionType(str, Enum):
    OUTCOME_TO_INSIGHT = "outcome_to_insight"
    INSIGHT_TO_CAPABILITY = "insight_to_capability"
    CAPABILITY_TO_OPERATIONALIZATION = "capability_to_operationalization"
    OPERATIONALIZATION_TO_INFRASTRUCTURE = "operationalization_to_infrastructure"


class PromotionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROMOTED = "promoted"


@dataclass
class CapabilityTemplate:
    template_id: str = field(default_factory=lambda: f"cap-{uuid4().hex[:8]}")
    task_shape: str = ""
    file_patterns: list[str] = field(default_factory=list)
    code_skeleton: str = ""
    test_skeleton: str = ""
    times_extracted: int = 0
    times_reused: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "task_shape": self.task_shape,
            "file_patterns": self.file_patterns,
            "code_skeleton": self.code_skeleton,
            "test_skeleton": self.test_skeleton,
            "times_extracted": self.times_extracted,
            "times_reused": self.times_reused,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CapabilityTemplate:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class PromotionCandidate:
    candidate_id: str = field(default_factory=lambda: f"promo-{uuid4().hex[:8]}")
    promotion_type: PromotionType = PromotionType.OUTCOME_TO_INSIGHT
    source_id: str = ""
    source_description: str = ""
    proposed_target: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    status: PromotionStatus = PromotionStatus.PROPOSED
    rejection_reason: str = ""
    proposed_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["promotion_type"] = self.promotion_type.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PromotionCandidate:
        d = dict(d)
        try:
            d["promotion_type"] = PromotionType(d.get("promotion_type", "outcome_to_insight"))
        except ValueError:
            d["promotion_type"] = PromotionType.OUTCOME_TO_INSIGHT
        try:
            d["status"] = PromotionStatus(d.get("status", "proposed"))
        except ValueError:
            d["status"] = PromotionStatus.PROPOSED
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Deterministic scoring
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def score_outcome_to_insight(
    action_type: str,
    success_rate: float,
    occurrence_count: int,
    min_occurrences: int = 2,
    min_success_rate: float = 0.6,
) -> float:
    """Score whether an outcome pattern is ready to become an insight."""
    if occurrence_count < min_occurrences:
        return 0.0
    if success_rate < min_success_rate:
        return 0.0
    frequency_score = min(1.0, occurrence_count / 10.0)
    return round(frequency_score * success_rate, 4)


def score_insight_to_capability(
    evidence_count: int,
    avg_quality: float,
    diversity: int,
    min_evidence: int = 2,
) -> float:
    """Score whether an insight is ready to become a capability."""
    if evidence_count < min_evidence:
        return 0.0
    coverage = min(1.0, evidence_count / 5.0)
    diversity_bonus = min(1.0, diversity / 3.0) * 0.2
    return round(coverage * avg_quality + diversity_bonus, 4)


def score_capability_to_operationalization(
    maturity_score: float,
    reuse_potential: int,
    has_template: bool,
) -> float:
    """Score whether a capability is ready to be operationalized."""
    if maturity_score < 0.3:
        return 0.0
    base = maturity_score * 0.6
    reuse = min(1.0, reuse_potential / 5.0) * 0.2
    template_bonus = 0.2 if has_template else 0.0
    return round(base + reuse + template_bonus, 4)


def score_operationalization_to_infrastructure(
    reuse_count: int,
    success_rate: float,
    status_ordinal: int,
    min_reuse: int = 3,
    min_success_rate: float = 0.7,
) -> float:
    """Score whether an operationalization is ready to become infrastructure."""
    if reuse_count < min_reuse:
        return 0.0
    if success_rate < min_success_rate:
        return 0.0
    freq = min(1.0, reuse_count / 10.0)
    status_weight = min(1.0, status_ordinal / 2.0)
    return round(freq * 0.4 + success_rate * 0.4 + status_weight * 0.2, 4)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task shape detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK_SHAPE_PATTERNS: dict[str, list[str]] = {
    "endpoint_addition": ["route", "handler", "test", "endpoint"],
    "schema_change": ["migration", "model", "schema", "validation"],
    "adapter_integration": ["adapter", "config", "connect", "integration"],
    "bug_fix": ["fix", "patch", "repair", "regression"],
    "refactor": ["refactor", "rename", "extract", "simplify"],
}


def detect_task_shape(description: str) -> str:
    """Match a task description to a known task shape deterministically."""
    lower = description.lower()
    best_shape = "unknown"
    best_score = 0
    for shape, keywords in TASK_SHAPE_PATTERNS.items():
        hits = sum(1 for kw in keywords if kw in lower)
        if hits > best_score:
            best_score = hits
            best_shape = shape
    return best_shape if best_score > 0 else "unknown"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CompoundingEngine:
    """Detects and manages promotion candidates across the capability chain."""

    def __init__(self, store_path: str = _CANDIDATES_PATH) -> None:
        self._path = store_path
        self._lock = threading.Lock()
        self._candidates: dict[str, PromotionCandidate] = {}
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        c = PromotionCandidate.from_dict(d)
                        self._candidates[c.candidate_id] = c
                    except (json.JSONDecodeError, TypeError, KeyError) as e:
                        logger.debug("Skip malformed JSONL line: %s", e)
        except OSError as e:
            logger.debug("Cannot read %s: %s", self._path, e)

    def _append(self, candidate: PromotionCandidate) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(candidate.to_dict(), default=str) + "\n")

    def _rewrite(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for c in self._candidates.values():
                f.write(json.dumps(c.to_dict(), default=str) + "\n")

    # ── Capability persistence ────────────────────────────────────

    def _persist_capability(self, template: CapabilityTemplate) -> None:
        cap_path = os.path.join(_ENGINE_DIR, "capabilities.jsonl")
        os.makedirs(os.path.dirname(cap_path), exist_ok=True)
        with open(cap_path, "a") as f:
            f.write(json.dumps(template.to_dict(), default=str) + "\n")

    def _load_capabilities(self) -> list[CapabilityTemplate]:
        cap_path = os.path.join(_ENGINE_DIR, "capabilities.jsonl")
        templates: list[CapabilityTemplate] = []
        if not os.path.isfile(cap_path):
            return templates
        try:
            with open(cap_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        templates.append(CapabilityTemplate.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.debug("Skip malformed capability line: %s", exc)
        except OSError as exc:
            logger.debug("Cannot read capabilities: %s", exc)
        return templates

    # ── Post-cycle scan ───────────────────────────────────────────

    def scan_after_cycle(
        self,
        outcomes: list[dict[str, Any]],
        capabilities_data: list[dict[str, Any]] | None = None,
        operationalizations: list[dict[str, Any]] | None = None,
    ) -> list[PromotionCandidate]:
        """Run all detection methods after a governed cycle completes.

        Returns all newly found promotion candidates.
        """
        all_new: list[PromotionCandidate] = []

        new_insights = self.detect_outcome_to_insight(outcomes)
        all_new.extend(new_insights)

        if capabilities_data:
            all_new.extend(self.detect_insight_to_capability(capabilities_data))
            all_new.extend(self.detect_capability_to_operationalization(capabilities_data))

        if operationalizations:
            all_new.extend(self.detect_operationalization_to_infrastructure(operationalizations))

        for candidate in new_insights:
            shape = detect_task_shape(candidate.source_description)
            if shape != "unknown":
                tpl = CapabilityTemplate(
                    task_shape=shape,
                    file_patterns=[],
                    times_extracted=1,
                    success_rate=candidate.confidence,
                )
                self._persist_capability(tpl)
                logger.info(
                    "Extracted capability template %s (shape=%s) from %s",
                    tpl.template_id, shape, candidate.candidate_id,
                )

        if all_new:
            logger.info("scan_after_cycle: %d new promotion candidates", len(all_new))

        return all_new

    # ── Detection ──────────────────────────────────────────────────

    def detect_outcome_to_insight(
        self,
        outcomes: list[dict[str, Any]],
        min_occurrences: int = 2,
        min_success_rate: float = 0.6,
    ) -> list[PromotionCandidate]:
        """Detect outcome patterns that should become insights."""
        by_action: dict[str, list[dict[str, Any]]] = {}
        for o in outcomes:
            action = o.get("action_type", "")
            if action:
                by_action.setdefault(action, []).append(o)

        candidates: list[PromotionCandidate] = []
        for action, records in by_action.items():
            successes = sum(1 for r in records if r.get("status") == "success")
            rate = successes / len(records) if records else 0.0
            conf = score_outcome_to_insight(
                action, rate, len(records), min_occurrences, min_success_rate
            )
            if conf > 0.0:
                c = PromotionCandidate(
                    promotion_type=PromotionType.OUTCOME_TO_INSIGHT,
                    source_id=action,
                    source_description=f"Pattern: {action} ({len(records)} occurrences, {rate:.0%} success)",
                    proposed_target={
                        "action_type": action,
                        "occurrences": len(records),
                        "success_rate": round(rate, 3),
                    },
                    confidence=conf,
                    evidence=[r.get("id", "") for r in records[:5]],
                )
                candidates.append(c)
                with self._lock:
                    self._candidates[c.candidate_id] = c
                    self._append(c)

        return candidates

    def detect_insight_to_capability(
        self,
        capabilities_data: list[dict[str, Any]],
        min_evidence: int = 2,
    ) -> list[PromotionCandidate]:
        """Detect emerging capabilities ready for registration."""
        candidates: list[PromotionCandidate] = []
        for cap in capabilities_data:
            evidence = cap.get("evidence", [])
            if len(evidence) < min_evidence:
                continue
            qualities = [e.get("quality_score", 0.5) for e in evidence]
            avg_q = sum(qualities) / len(qualities) if qualities else 0.5
            types = set(e.get("evidence_type", "") for e in evidence)
            conf = score_insight_to_capability(len(evidence), avg_q, len(types), min_evidence)
            if conf > 0.0:
                c = PromotionCandidate(
                    promotion_type=PromotionType.INSIGHT_TO_CAPABILITY,
                    source_id=cap.get("capability_id", ""),
                    source_description=cap.get("name", ""),
                    proposed_target={
                        "maturity": "validated",
                        "evidence_count": len(evidence),
                        "avg_quality": round(avg_q, 3),
                    },
                    confidence=conf,
                    evidence=[e.get("evidence_id", "") for e in evidence[:5]],
                )
                candidates.append(c)
                with self._lock:
                    self._candidates[c.candidate_id] = c
                    self._append(c)

        return candidates

    def detect_capability_to_operationalization(
        self,
        capabilities: list[dict[str, Any]],
    ) -> list[PromotionCandidate]:
        """Detect capabilities ready to be operationalized."""
        candidates: list[PromotionCandidate] = []
        for cap in capabilities:
            maturity = cap.get("maturity_score", 0.0)
            reuse = cap.get("reuse_potential", 0)
            has_tpl = bool(cap.get("template_ids"))
            conf = score_capability_to_operationalization(maturity, reuse, has_tpl)
            if conf > 0.0:
                c = PromotionCandidate(
                    promotion_type=PromotionType.CAPABILITY_TO_OPERATIONALIZATION,
                    source_id=cap.get("capability_id", ""),
                    source_description=cap.get("name", ""),
                    proposed_target={
                        "form": "template" if has_tpl else "playbook",
                        "maturity_score": maturity,
                    },
                    confidence=conf,
                )
                candidates.append(c)
                with self._lock:
                    self._candidates[c.candidate_id] = c
                    self._append(c)

        return candidates

    def detect_operationalization_to_infrastructure(
        self,
        operationalizations: list[dict[str, Any]],
        min_reuse: int = 3,
        min_success_rate: float = 0.7,
    ) -> list[PromotionCandidate]:
        """Detect operationalizations ready to become infrastructure."""
        candidates: list[PromotionCandidate] = []
        status_map = {"draft": 0, "validated": 1, "production": 2, "deprecated": 3}
        for op in operationalizations:
            reuse = op.get("reuse_count", 0)
            rate = op.get("success_rate", 0.0)
            status_ord = status_map.get(op.get("status", "draft"), 0)
            conf = score_operationalization_to_infrastructure(
                reuse, rate, status_ord, min_reuse, min_success_rate
            )
            if conf > 0.0:
                c = PromotionCandidate(
                    promotion_type=PromotionType.OPERATIONALIZATION_TO_INFRASTRUCTURE,
                    source_id=op.get("operationalization_id", ""),
                    source_description=op.get("name", ""),
                    proposed_target={
                        "infra_type": "runtime",
                        "reuse_count": reuse,
                        "success_rate": rate,
                    },
                    confidence=conf,
                )
                candidates.append(c)
                with self._lock:
                    self._candidates[c.candidate_id] = c
                    self._append(c)

        return candidates

    # ── Promotion governance ───────────────────────────────────────

    def get(self, candidate_id: str) -> PromotionCandidate | None:
        return self._candidates.get(candidate_id)

    def list_candidates(
        self,
        promotion_type: PromotionType | None = None,
        status: PromotionStatus | None = None,
        limit: int = 100,
    ) -> list[PromotionCandidate]:
        result = list(self._candidates.values())
        if promotion_type is not None:
            result = [c for c in result if c.promotion_type == promotion_type]
        if status is not None:
            result = [c for c in result if c.status == status]
        result.sort(key=lambda c: c.confidence, reverse=True)
        return result[:limit]

    def approve(self, candidate_id: str) -> bool:
        c = self._candidates.get(candidate_id)
        if c is None or c.status != PromotionStatus.PROPOSED:
            return False
        with self._lock:
            c.status = PromotionStatus.APPROVED
            c.resolved_at = time.time()
            self._rewrite()
        return True

    def reject(self, candidate_id: str, reason: str = "") -> bool:
        c = self._candidates.get(candidate_id)
        if c is None or c.status != PromotionStatus.PROPOSED:
            return False
        with self._lock:
            c.status = PromotionStatus.REJECTED
            c.rejection_reason = reason
            c.resolved_at = time.time()
            self._rewrite()
        return True

    def promote(self, candidate_id: str) -> dict[str, Any]:
        """Execute promotion — creates the target entity.

        Must be APPROVED first (Human Supremacy invariant).
        """
        c = self._candidates.get(candidate_id)
        if c is None:
            return {"error": f"candidate {candidate_id} not found"}
        if c.status != PromotionStatus.APPROVED:
            return {"error": f"candidate must be approved first (current: {c.status.value})"}

        with self._lock:
            c.status = PromotionStatus.PROMOTED
            c.resolved_at = time.time()
            self._rewrite()

        return {
            "promoted": True,
            "candidate_id": candidate_id,
            "promotion_type": c.promotion_type.value,
            "source_id": c.source_id,
            "target": c.proposed_target,
        }

    # ── Reporting ──────────────────────────────────────────────────

    def compounding_report(self, days: int = 90) -> dict[str, Any]:
        cutoff = time.time() - (days * 86400)
        recent = [c for c in self._candidates.values() if c.proposed_at >= cutoff]
        by_type: dict[str, int] = Counter(c.promotion_type.value for c in recent)
        by_status: dict[str, int] = Counter(c.status.value for c in recent)
        promoted = [c for c in recent if c.status == PromotionStatus.PROMOTED]
        return {
            "period_days": days,
            "total_candidates": len(recent),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "promoted_count": len(promoted),
            "approval_rate": round(len(promoted) / len(recent), 3) if recent else 0.0,
            "avg_confidence": round(sum(c.confidence for c in recent) / len(recent), 4)
            if recent
            else 0.0,
        }

    def improvement_from_executions(self, n: int = 100) -> dict[str, Any]:
        """Report on improvements derived from recent executions."""
        promoted = sorted(
            [c for c in self._candidates.values() if c.status == PromotionStatus.PROMOTED],
            key=lambda c: c.resolved_at,
            reverse=True,
        )[:n]
        return {
            "recent_promotions": len(promoted),
            "by_type": dict(Counter(c.promotion_type.value for c in promoted)),
            "promotions": [c.to_dict() for c in promoted],
        }

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = Counter(c.promotion_type.value for c in self._candidates.values())
        by_status: dict[str, int] = Counter(c.status.value for c in self._candidates.values())
        pending = sum(1 for c in self._candidates.values() if c.status == PromotionStatus.PROPOSED)
        return {
            "total_candidates": len(self._candidates),
            "pending_approval": pending,
            "by_type": dict(by_type),
            "by_status": dict(by_status),
        }
