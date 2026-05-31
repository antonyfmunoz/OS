"""Context Diagnostic — models for diagnostic reports on context state.

A ContextDiagnosticReport captures the result of analyzing ingested context:
canonical claims, contradictions, outdated claims, missing context, and
recommended updates.

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
_REPORTS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "diagnostic_reports.jsonl"
)


class ContradictionType(str, Enum):
    DIRECT_CONFLICT = "direct_conflict"
    STALE_VS_CURRENT = "stale_vs_current"
    DUPLICATE_DIFFERENT_NAME = "duplicate_different_name"
    ROADMAP_DRIFT = "roadmap_drift"
    PRODUCT_SCOPE_DRIFT = "product_scope_drift"
    ENTITY_STRUCTURE_DRIFT = "entity_structure_drift"
    SOURCE_OF_TRUTH_CONFLICT = "source_of_truth_conflict"
    OUTDATED_TOOL_ARTIFACT = "outdated_tool_artifact"
    AMBIGUOUS_INTENT = "ambiguous_intent"
    MISSING_DECISION = "missing_decision"


class DiagnosticStatus(str, Enum):
    DRAFTED = "drafted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CanonicalClaim:
    claim_id: str = ""
    claim_text: str = ""
    domain: str = ""
    entity_refs: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    freshness: str = "unknown"
    canonicality: str = "unknown"
    approved: bool = False

    def __post_init__(self) -> None:
        if not self.claim_id:
            self.claim_id = f"claim-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "domain": self.domain,
            "entity_refs": self.entity_refs,
            "source_ids": self.source_ids,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "canonicality": self.canonicality,
            "approved": self.approved,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CanonicalClaim:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ContextContradiction:
    contradiction_id: str = ""
    claim_a: str = ""
    claim_b: str = ""
    source_a: str = ""
    source_b: str = ""
    contradiction_type: str = ContradictionType.DIRECT_CONFLICT.value
    severity: str = "medium"
    confidence: float = 0.5
    recommended_resolution: str = ""
    requires_operator_decision: bool = True

    def __post_init__(self) -> None:
        if not self.contradiction_id:
            self.contradiction_id = f"ctr-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contradiction_id": self.contradiction_id,
            "claim_a": self.claim_a,
            "claim_b": self.claim_b,
            "source_a": self.source_a,
            "source_b": self.source_b,
            "contradiction_type": self.contradiction_type,
            "severity": self.severity,
            "confidence": self.confidence,
            "recommended_resolution": self.recommended_resolution,
            "requires_operator_decision": self.requires_operator_decision,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContextContradiction:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ContextDiagnosticReport:
    report_id: str = ""
    scope: str = ""
    created_at: float = 0.0
    sources_analyzed: list[str] = field(default_factory=list)
    item_count: int = 0
    canonical_claims: list[dict[str, Any]] = field(default_factory=list)
    competing_claims: list[dict[str, Any]] = field(default_factory=list)
    outdated_claims: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    entity_map: dict[str, Any] = field(default_factory=dict)
    project_map: dict[str, Any] = field(default_factory=dict)
    product_map: dict[str, Any] = field(default_factory=dict)
    roadmap_implications: list[str] = field(default_factory=list)
    work_packet_implications: list[str] = field(default_factory=list)
    memory_implications: list[str] = field(default_factory=list)
    recommended_canonical_updates: list[str] = field(default_factory=list)
    recommended_deprecations: list[str] = field(default_factory=list)
    recommended_work_packets: list[str] = field(default_factory=list)
    recommended_operator_questions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    status: str = DiagnosticStatus.DRAFTED.value

    def __post_init__(self) -> None:
        if not self.report_id:
            self.report_id = f"diag-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "scope": self.scope,
            "created_at": self.created_at,
            "sources_analyzed": self.sources_analyzed,
            "item_count": self.item_count,
            "canonical_claims": self.canonical_claims,
            "competing_claims": self.competing_claims,
            "outdated_claims": self.outdated_claims,
            "contradictions": self.contradictions,
            "missing_context": self.missing_context,
            "open_questions": self.open_questions,
            "entity_map": self.entity_map,
            "project_map": self.project_map,
            "product_map": self.product_map,
            "roadmap_implications": self.roadmap_implications,
            "work_packet_implications": self.work_packet_implications,
            "memory_implications": self.memory_implications,
            "recommended_canonical_updates": self.recommended_canonical_updates,
            "recommended_deprecations": self.recommended_deprecations,
            "recommended_work_packets": self.recommended_work_packets,
            "recommended_operator_questions": self.recommended_operator_questions,
            "confidence": self.confidence,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContextDiagnosticReport:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class DiagnosticReportStore:
    def __init__(self, path: str | None = None) -> None:
        self._path = path or _REPORTS_PATH
        self._reports: dict[str, ContextDiagnosticReport] = {}
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
                    rpt = ContextDiagnosticReport.from_dict(d)
                    self._reports[rpt.report_id] = rpt
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping malformed diagnostic report line")

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for rpt in self._reports.values():
                f.write(json.dumps(rpt.to_dict(), default=str) + "\n")

    def save_report(self, report: ContextDiagnosticReport) -> ContextDiagnosticReport:
        self._reports[report.report_id] = report
        self._save()
        return report

    def get_report(self, report_id: str) -> ContextDiagnosticReport | None:
        return self._reports.get(report_id)

    def list_reports(self, scope: str | None = None) -> list[ContextDiagnosticReport]:
        result = list(self._reports.values())
        if scope:
            result = [r for r in result if r.scope == scope]
        return result

    def count(self) -> int:
        return len(self._reports)
